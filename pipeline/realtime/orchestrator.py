"""
BeninSentinel — Orchestrateur temps réel.

Pivot central qui enchaîne, à chaque tick du scheduler :

    Streamer  →  AlertEngine  →  Notifier  →  Providers
    (GDELT)     (sentinel)      (routage)     (canal sortie)

L'orchestrateur expose une méthode unique `tick()` qui réalise un cycle
complet et retourne un résumé d'exécution. Le scheduler appelle cette
méthode à intervalle régulier (par défaut toutes les heures).

Le cycle est conçu pour être :
- **Atomique** : un tick fait UNE évaluation complète sur les dernières
  données. Si la base est encore vide, on crée le baseline. Si rien n'a
  changé, on enregistre l'état mais on ne notifie pas.
- **Robuste**  : aucune exception n'interrompt l'orchestrateur. Toute
  erreur est tracée et retournée dans le résumé.
- **Auditable**: chaque tick produit un résumé structuré (statut, score,
  transition éventuelle, notifications envoyées) pour les logs.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from .alert_engine import AlertEngine, AlertTransition
from .history      import AlertHistory
from .notifier     import Notifier
from .streamer     import SentinelStreamer
from .templates_loader import build_alert_payload


@dataclass
class TickResult:
    """Résumé structuré d'un cycle d'évaluation."""
    started_at:        datetime
    finished_at:       datetime
    status:            str               # OK / ERROR
    alert_level:       Optional[str]
    risk_score:        Optional[float]
    transition:        Optional[str]      # ESCALATION / DE_ESCALATION / STABLE / BASELINE
    notifications_sent: int
    error_message:     Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["started_at"]  = self.started_at.isoformat()
        d["finished_at"] = self.finished_at.isoformat()
        return d


class SentinelOrchestrator:
    """
    Orchestrateur principal du système BeninSentinel temps réel.

    Assemble Streamer + AlertEngine + Notifier dans une chaîne robuste,
    et expose une API minimale (`tick`, `bootstrap`).
    """

    def __init__(self,
                 streamer: SentinelStreamer,
                 engine:   AlertEngine,
                 notifier: Notifier,
                 history:  AlertHistory):
        self.streamer = streamer
        self.engine   = engine
        self.notifier = notifier
        self.history  = history

    # ─────────────────────────────────────────────────────────────
    # CYCLE PRINCIPAL
    # ─────────────────────────────────────────────────────────────

    def tick(self, days_back: int = 45) -> TickResult:
        """
        Réaliser un cycle complet d'évaluation et de notification.

        Args:
            days_back : profondeur de la fenêtre GDELT (45 jours par défaut —
                        suffit pour la référence comportementale 30 jours).

        Returns:
            TickResult avec le résumé du cycle (succès ou erreur tracée).
        """
        started_at = datetime.utcnow()

        try:
            # 1. Récupérer les données fraîches
            df = self.streamer.fetch_window(days_back=days_back)
            if df.empty:
                return TickResult(
                    started_at=started_at, finished_at=datetime.utcnow(),
                    status="ERROR", alert_level=None, risk_score=None,
                    transition=None, notifications_sent=0,
                    error_message="Streamer returned empty DataFrame.",
                )

            # 2. Évaluer le score et détecter une transition éventuelle
            transition = self.engine.evaluate(df)

            # 3. Distribuer les notifications (si transition significative)
            results = self.notifier.dispatch(
                transition,
                payload_builder=lambda t, r: build_alert_payload(t, r),
            )

            return TickResult(
                started_at=started_at, finished_at=datetime.utcnow(),
                status="OK",
                alert_level=transition.to_level,
                risk_score=transition.to_score,
                transition=transition.direction,
                notifications_sent=len(results),
            )

        except Exception as e:
            return TickResult(
                started_at=started_at, finished_at=datetime.utcnow(),
                status="ERROR", alert_level=None, risk_score=None,
                transition=None, notifications_sent=0,
                error_message=f"{type(e).__name__}: {e}",
            )

    def bootstrap(self, days_back: int = 45) -> TickResult:
        """
        Premier démarrage du système : crée un état "baseline" sans notifier.

        Équivalent à un tick(), mais l'AlertEngine reconnaît qu'il n'y a pas
        d'historique et marque la transition comme BASELINE (pas de notif).
        """
        return self.tick(days_back=days_back)

    # ─────────────────────────────────────────────────────────────
    # FACTORY — assemblage standard
    # ─────────────────────────────────────────────────────────────

    @classmethod
    def default(cls, db_path: Path,
                recipients_path: Optional[Path] = None,
                rules_path: Optional[Path] = None,
                prefer_local: bool = False,
                simulate_providers: bool = False) -> "SentinelOrchestrator":
        """
        Construire un orchestrateur prêt à l'emploi avec configuration standard.

        Args:
            db_path             : chemin de la base SQLite d'historique.
            recipients_path     : config/recipients.yaml.
            rules_path          : config/notification_rules.yaml.
            prefer_local        : forcer le mode CSV local (utile en démo).
            simulate_providers  : si True, aucun email/webhook réel n'est envoyé.

        Returns:
            SentinelOrchestrator prêt à `tick()`.
        """
        from .providers import ConsoleProvider, EmailProvider, WebhookProvider

        history  = AlertHistory(db_path)
        engine   = AlertEngine(history)
        streamer = SentinelStreamer(prefer_local=prefer_local)

        providers = {
            "console": ConsoleProvider(simulate=simulate_providers),
            "email":   EmailProvider(simulate=simulate_providers),
            "webhook": WebhookProvider(simulate=simulate_providers),
        }

        notifier = Notifier(
            history=history,
            recipients_path=recipients_path,
            rules_path=rules_path,
            providers=providers,
        )

        return cls(streamer=streamer, engine=engine,
                   notifier=notifier, history=history)

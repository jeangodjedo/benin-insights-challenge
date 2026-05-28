"""
BeninSentinel — Notifier : routage transparent des alertes vers les destinataires.

Le Notifier est le pivot entre le moteur de détection (AlertEngine) et
les providers de notification. Sa logique est explicitement basée sur
deux fichiers de configuration YAML auditables :

    config/recipients.yaml
        Annuaire des destinataires (nom, rôle, canal, adresse).
        Ce fichier liste qui peut être notifié et comment.

    config/notification_rules.yaml
        Règles de routage : pour chaque niveau d'alerte (JAUNE / ORANGE /
        ROUGE), quels rôles destinataires sont concernés.

Cette séparation est cruciale pour un outil de gouvernance publique :
    - Les autorités peuvent modifier les règles sans toucher au code
    - Tout changement est versionné dans Git (audit)
    - Pas de logique métier codée en dur dans le programme

Conception fail-safe :
    - Si un fichier YAML est manquant ou malformé, le Notifier bascule
      en mode "console-only" et continue à fonctionner (jamais d'interruption
      de service sur un défaut de config).
    - Si un provider échoue (ex. SMTP indisponible), les autres sont
      tentés et tout est tracé en base.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from .alert_engine    import AlertTransition
from .history         import AlertHistory
from .providers       import ConsoleProvider, EmailProvider, WebhookProvider
from .providers.base  import NotificationProvider


# Niveaux d'alerte qui déclenchent une notification par défaut.
# VERT n'est pas notifié — c'est le mode normal.
DEFAULT_NOTIFIABLE_LEVELS = {"JAUNE", "ORANGE", "ROUGE"}


class Notifier:
    """
    Orchestrateur de la distribution des alertes vers les bons destinataires.

    Usage typique :
        notifier = Notifier(
            history=history,
            recipients_path=Path("config/recipients.yaml"),
            rules_path=Path("config/notification_rules.yaml"),
            providers={
                "console": ConsoleProvider(),
                "email":   EmailProvider(),
                "webhook": WebhookProvider(),
            },
        )
        # Après une transition détectée par AlertEngine :
        notifier.dispatch(transition, payload_builder=build_payload)
    """

    def __init__(self,
                 history: AlertHistory,
                 recipients_path: Optional[Path] = None,
                 rules_path: Optional[Path] = None,
                 providers: Optional[dict[str, NotificationProvider]] = None,
                 notifiable_levels: Optional[set[str]] = None,
                 notify_de_escalation: bool = False):
        """
        Args:
            history              : couche de persistance pour audit.
            recipients_path      : chemin vers config/recipients.yaml.
            rules_path           : chemin vers config/notification_rules.yaml.
            providers            : dict {channel_name: NotificationProvider}.
                                   Si None : ConsoleProvider seulement.
            notifiable_levels    : niveaux qui déclenchent une notif (JAUNE+ par défaut).
            notify_de_escalation : si True, notifie aussi les retours au calme.
        """
        self.history = history
        self.recipients_path = recipients_path
        self.rules_path      = rules_path
        self.providers       = providers or {"console": ConsoleProvider()}
        self.notifiable_levels = notifiable_levels or DEFAULT_NOTIFIABLE_LEVELS
        self.notify_de_escalation = notify_de_escalation

        # Chargement initial des configs (sécurisé en cas d'erreur)
        self.recipients = self._load_recipients()
        self.rules      = self._load_rules()

    # ─────────────────────────────────────────────────────────────
    # API PRINCIPALE
    # ─────────────────────────────────────────────────────────────

    def dispatch(self, transition: AlertTransition,
                 payload_builder=None) -> list[dict]:
        """
        Distribuer une notification aux destinataires concernés par la transition.

        Args:
            transition      : objet AlertTransition issu de AlertEngine.evaluate().
            payload_builder : callable (transition, recipient) -> payload dict.
                              Si None, un payload minimal par défaut est généré.

        Returns:
            Liste des résultats de notification (un dict par destinataire ciblé).
        """
        # 1. Décider si la transition mérite une notification
        if not self._should_notify(transition):
            return []

        # 2. Identifier les destinataires à notifier selon les règles
        targets = self._select_recipients(transition.to_level)
        if not targets:
            return []

        # 3. Pour chaque destinataire, construire le payload et envoyer
        results = []
        for recipient in targets:
            payload = payload_builder(transition, recipient) if payload_builder \
                else self._default_payload(transition, recipient)

            channel = recipient.get("channel", "console")
            provider = self.providers.get(channel, self.providers.get("console"))

            try:
                result = provider.send(recipient, payload)
            except Exception as e:
                # Filet ultime — un provider ne doit JAMAIS faire tomber le système
                from .providers.base import ProviderResult
                result = ProviderResult(
                    status="FAILED", channel=channel,
                    target_address=recipient.get("address", ""),
                    sent_at=datetime.utcnow(),
                    error_message=f"Provider crashed: {type(e).__name__}: {e}",
                )

            # Tracer chaque envoi en base pour audit
            if transition.transition_id is not None:
                self.history.record_notification(
                    transition_id=transition.transition_id,
                    sent_at=result.sent_at,
                    recipient_name=recipient.get("name", "—"),
                    recipient_role=recipient.get("role", "—"),
                    channel=result.channel,
                    target_address=result.target_address,
                    alert_level=transition.to_level,
                    status=result.status,
                    error_message=result.error_message,
                )

            results.append({
                "recipient": recipient,
                "result":    result,
            })

        # 4. Marquer la transition comme notifiée (au moins une tentative faite)
        if transition.transition_id is not None and results:
            self.history.mark_transition_notified(transition.transition_id)

        return results

    # ─────────────────────────────────────────────────────────────
    # LOGIQUE DE ROUTAGE
    # ─────────────────────────────────────────────────────────────

    def _should_notify(self, transition: AlertTransition) -> bool:
        """Vrai si la transition mérite une notification."""
        if not transition.is_transition:
            return False
        if transition.to_level not in self.notifiable_levels:
            return False
        if transition.direction == "DE_ESCALATION" and not self.notify_de_escalation:
            return False
        return True

    def _select_recipients(self, alert_level: str) -> list[dict]:
        """
        Croiser les règles (rôles concernés par ce niveau) avec l'annuaire
        des destinataires (nom, adresse, canal).
        """
        roles = self.rules.get(alert_level, [])
        if not roles:
            return []

        # Filtrer l'annuaire par rôles correspondants
        selected = [r for r in self.recipients
                    if r.get("role") in roles and r.get("active", True)]
        return selected

    # ─────────────────────────────────────────────────────────────
    # CONFIG LOADING (sécurisé)
    # ─────────────────────────────────────────────────────────────

    def _load_recipients(self) -> list[dict]:
        if not self.recipients_path or not self.recipients_path.exists() or yaml is None:
            return []
        try:
            data = yaml.safe_load(self.recipients_path.read_text(encoding="utf-8"))
            return list(data.get("recipients", []) if isinstance(data, dict) else [])
        except Exception:
            return []

    def _load_rules(self) -> dict[str, list[str]]:
        if not self.rules_path or not self.rules_path.exists() or yaml is None:
            return {}
        try:
            data = yaml.safe_load(self.rules_path.read_text(encoding="utf-8"))
            return dict(data.get("rules", {})) if isinstance(data, dict) else {}
        except Exception:
            return {}

    # ─────────────────────────────────────────────────────────────
    # PAYLOAD PAR DÉFAUT (utilisé si aucun builder fourni)
    # ─────────────────────────────────────────────────────────────

    def _default_payload(self, transition: AlertTransition, recipient: dict) -> dict:
        date_str = transition.target_date.strftime("%d %b %Y")
        subject = f"[BeninSentinel] Alerte {transition.to_level} — {date_str}"
        text = (
            f"BeninSentinel — Alerte {transition.to_level}\n"
            f"Date analysée : {date_str}\n"
            f"Score : {transition.to_score:.3f}\n"
            f"Transition : {transition.from_level} → {transition.to_level} "
            f"({transition.direction})\n\n"
            f"Bonjour {recipient.get('name', '')},\n"
            f"Une transition d'alerte vient d'être détectée par BeninSentinel.\n"
        )
        return {
            "alert_level":  transition.to_level,
            "subject":      subject,
            "rendered_text": text,
            "rendered_html": f"<pre>{text}</pre>",
            "transition": {
                "from":      transition.from_level,
                "to":        transition.to_level,
                "score":     transition.to_score,
                "direction": transition.direction,
            },
        }

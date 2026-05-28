"""
BeninSentinel — Moteur de détection des transitions d'alerte.

Le moteur reçoit un nouveau score BeninSentinel (issu de pipeline.sentinel),
le compare à l'état précédent stocké en base et décide :
    1. Faut-il enregistrer une transition d'alerte ?
    2. Si oui, dans quelle direction (escalation, de-escalation) ?
    3. Faut-il déclencher des notifications ?

Règle métier centrale :
    Une transition est SIGNIFICATIVE si elle change le niveau d'alerte
    (VERT/JAUNE/ORANGE/ROUGE). Les fluctuations du score à l'intérieur
    d'un même niveau ne déclenchent pas de notification — c'est ce qui
    rend l'outil crédible auprès des décideurs (pas d'alerte tous les jours).

Conception adaptée au cas réel :
    - Premier démarrage (base vide) : on enregistre l'état initial, mais
      pas de notification ("baseline").
    - Notification immédiate sur ESCALATION (montée vers un niveau plus
      grave) — c'est le cas critique pour les décideurs.
    - Notification possible mais optionnelle sur DE_ESCALATION (retour au
      calme) — utile pour les bulletins de "fin d'alerte".
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

from pipeline.sentinel import run_sentinel
from .history import AlertHistory


# Ordre canonique des niveaux d'alerte (de moins à plus grave)
LEVEL_ORDER = ["VERT", "JAUNE", "ORANGE", "ROUGE"]


@dataclass(frozen=True)
class AlertTransition:
    """
    Résultat d'une évaluation : décrit la transition détectée (ou absence).

    `is_transition` est False quand le niveau reste identique au précédent.
    Dans ce cas, la classe sert juste à transporter le score courant.
    """
    measured_at:   datetime
    target_date:   pd.Timestamp
    from_level:    str
    to_level:      str
    from_score:    Optional[float]
    to_score:      float
    signals:       dict
    is_transition: bool
    direction:     str           # ESCALATION / DE_ESCALATION / STABLE / BASELINE
    transition_id: Optional[int] # rempli après record en base

    @property
    def is_escalation(self) -> bool:
        """True si la transition est une dégradation (vers un niveau plus grave)."""
        return self.direction == "ESCALATION"

    @property
    def severity_change(self) -> int:
        """
        Nombre de crans de niveau franchis (signé).

        Exemples : VERT → ORANGE = +2, ORANGE → VERT = -2.
        Utile pour décider si l'escalation est sévère (saut de 2+ crans).
        """
        if not self.is_transition:
            return 0
        return LEVEL_ORDER.index(self.to_level) - LEVEL_ORDER.index(self.from_level)


class AlertEngine:
    """
    Moteur de détection de transitions d'alerte.

    Encapsule la logique de comparaison avec l'historique et l'enregistrement
    des transitions. Pas de logique de notification ici (séparation des
    responsabilités) — c'est le rôle du Notifier en aval.

    Usage typique :
        engine = AlertEngine(history)
        transition = engine.evaluate(df, target_date=pd.Timestamp.today())
        if transition.is_escalation:
            notifier.notify(transition)
    """

    SIGNAL_COLUMNS = [
        "sig_tone", "sig_negative", "sig_protest",
        "sig_quad3", "sig_quad4", "sig_violence",
    ]

    def __init__(self, history: AlertHistory):
        self.history = history

    # ─────────────────────────────────────────────────────────────
    # API PRINCIPALE
    # ─────────────────────────────────────────────────────────────

    def evaluate(self, df: pd.DataFrame,
                 target_date: Optional[pd.Timestamp] = None,
                 measured_at: Optional[datetime] = None) -> AlertTransition:
        """
        Évaluer le score BeninSentinel sur un dataset à une date cible,
        comparer à l'état précédent et enregistrer la transition si elle existe.

        Args:
            df          : DataFrame GDELT nettoyé (issu du pipeline ETL).
            target_date : date à évaluer (par défaut : la dernière date du dataset).
            measured_at : horodatage de l'évaluation (par défaut : maintenant).

        Returns:
            AlertTransition décrivant le résultat (transition ou état stable).
        """
        if measured_at is None:
            measured_at = datetime.utcnow()

        # 1. Calculer le score sur les données complètes (utilise la
        #    référence comportementale 30 jours déjà intégrée à run_sentinel).
        risk_df = run_sentinel(df)

        if target_date is None:
            target_date = risk_df["date"].max()

        # 2. Extraire la ligne correspondant à la date cible.
        target_row = risk_df[risk_df["date"] == target_date]
        if target_row.empty:
            raise ValueError(
                f"Aucun score calculable pour la date {target_date.date()}. "
                "Vérifier que df contient des données récentes."
            )
        row = target_row.iloc[0]

        to_score = float(row["risk_score"])
        to_level = str(row["alert_level"])
        signals  = {col: float(row[col]) for col in self.SIGNAL_COLUMNS}

        # 3. Récupérer le dernier état en base pour comparer.
        last = self.history.last_state()
        from_level = last["alert_level"] if last else None
        from_score = float(last["risk_score"]) if last else None

        # 4. Enregistrer toujours l'état mesuré (audit complet).
        self.history.record_state(
            measured_at=measured_at,
            target_date=target_date.to_pydatetime().date(),
            risk_score=to_score,
            alert_level=to_level,
            signals=signals,
        )

        # 5. Décider de la transition.
        if last is None:
            # Premier démarrage : pas de transition à comparer.
            return AlertTransition(
                measured_at=measured_at, target_date=target_date,
                from_level="—", to_level=to_level,
                from_score=None, to_score=to_score,
                signals=signals,
                is_transition=False, direction="BASELINE",
                transition_id=None,
            )

        if to_level == from_level:
            # Pas de changement de niveau — pas de notification.
            return AlertTransition(
                measured_at=measured_at, target_date=target_date,
                from_level=from_level, to_level=to_level,
                from_score=from_score, to_score=to_score,
                signals=signals,
                is_transition=False, direction="STABLE",
                transition_id=None,
            )

        # 6. Transition détectée : enregistrer en base et retourner l'objet.
        direction = self._direction(from_level, to_level)
        transition_id = self.history.record_transition(
            detected_at=measured_at,
            target_date=target_date.to_pydatetime().date(),
            from_level=from_level, to_level=to_level,
            from_score=from_score, to_score=to_score,
        )

        return AlertTransition(
            measured_at=measured_at, target_date=target_date,
            from_level=from_level, to_level=to_level,
            from_score=from_score, to_score=to_score,
            signals=signals,
            is_transition=True, direction=direction,
            transition_id=transition_id,
        )

    # ─────────────────────────────────────────────────────────────
    # HELPERS INTERNES
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _direction(from_level: str, to_level: str) -> str:
        """Calculer la direction (ESCALATION / DE_ESCALATION) d'une transition."""
        if LEVEL_ORDER.index(to_level) > LEVEL_ORDER.index(from_level):
            return "ESCALATION"
        if LEVEL_ORDER.index(to_level) < LEVEL_ORDER.index(from_level):
            return "DE_ESCALATION"
        return "STABLE"

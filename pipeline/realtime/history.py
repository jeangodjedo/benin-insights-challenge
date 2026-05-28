"""
BeninSentinel — Persistance SQLite de l'historique des alertes.

Cette couche maintient une mémoire durable de toutes les évaluations
de score BeninSentinel et des notifications déclenchées. Elle est
fondamentale pour deux raisons opérationnelles :

1. **Détection des transitions** : pour savoir si l'alerte vient de
   passer de VERT à JAUNE (et déclencher une notification), il faut
   se souvenir de l'état précédent.

2. **Auditabilité** : les autorités doivent pouvoir consulter l'historique
   complet des alertes et des actions notifiées — exigence de gouvernance
   et de transparence pour un outil d'aide à la décision publique.

Choix techniques :
- SQLite (stdlib Python) — zéro dépendance externe, fichier portable,
  parfait pour un déploiement sur serveur ANSSI ou hébergement étatique.
- Pas de framework ORM — requêtes SQL natives, lisibles, auditables.

Schéma de la base :
- `alert_states`  : une ligne par évaluation du score (timestamp, score, niveau)
- `transitions`   : une ligne par changement de niveau d'alerte
- `notifications` : une ligne par notification envoyée (audit complet)
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS alert_states (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    measured_at     TIMESTAMP NOT NULL,
    target_date     DATE NOT NULL,
    risk_score      REAL NOT NULL,
    alert_level     TEXT NOT NULL CHECK (alert_level IN ('VERT', 'JAUNE', 'ORANGE', 'ROUGE')),
    signals_json    TEXT NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS transitions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at     TIMESTAMP NOT NULL,
    target_date     DATE NOT NULL,
    from_level      TEXT NOT NULL,
    to_level        TEXT NOT NULL,
    from_score      REAL,
    to_score        REAL NOT NULL,
    direction       TEXT NOT NULL CHECK (direction IN ('ESCALATION', 'DE_ESCALATION', 'STABLE')),
    notified        INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notifications (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    sent_at         TIMESTAMP NOT NULL,
    transition_id   INTEGER NOT NULL REFERENCES transitions(id),
    recipient_name  TEXT NOT NULL,
    recipient_role  TEXT NOT NULL,
    channel         TEXT NOT NULL,
    target_address  TEXT NOT NULL,
    alert_level     TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('SUCCESS', 'FAILED', 'SIMULATED')),
    error_message   TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_states_measured_at  ON alert_states(measured_at);
CREATE INDEX IF NOT EXISTS idx_transitions_detected ON transitions(detected_at);
CREATE INDEX IF NOT EXISTS idx_notif_transition    ON notifications(transition_id);
"""


class AlertHistory:
    """
    Couche d'accès à l'historique des alertes BeninSentinel.

    Encapsule toutes les interactions avec la base SQLite. La classe est
    conçue pour être thread-safe en mode "single-process" (le scheduler
    APScheduler tourne typiquement dans un seul processus).

    Exemple d'usage :
        history = AlertHistory(Path("data/sentinel_history.db"))
        history.record_state(measured_at=datetime.now(), target_date=date.today(),
                             risk_score=0.55, alert_level="JAUNE", signals={...})
        last = history.last_state()
    """

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    # ─────────────────────────────────────────────────────────────
    # SCHEMA & CONNECTION
    # ─────────────────────────────────────────────────────────────

    def _connect(self) -> sqlite3.Connection:
        """Ouvrir une connexion SQLite avec row_factory pratique."""
        conn = sqlite3.connect(
            self.db_path,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
        )
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _initialize_schema(self) -> None:
        """Créer les tables si elles n'existent pas (idempotent)."""
        with self._connect() as conn:
            conn.executescript(SCHEMA_SQL)

    # ─────────────────────────────────────────────────────────────
    # RECORD — écriture
    # ─────────────────────────────────────────────────────────────

    def record_state(self, measured_at: datetime, target_date,
                     risk_score: float, alert_level: str,
                     signals: dict) -> int:
        """
        Enregistrer une évaluation complète du score BeninSentinel.

        Args:
            measured_at : datetime de la mesure (UTC ou local cohérent).
            target_date : date analysée (peut être différente du `measured_at`
                          si on évalue une date passée).
            risk_score  : score composite entre 0 et 1.
            alert_level : VERT / JAUNE / ORANGE / ROUGE.
            signals     : dictionnaire des 6 signaux faibles normalisés.

        Returns:
            id (int) de la ligne insérée dans alert_states.
        """
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO alert_states
                    (measured_at, target_date, risk_score, alert_level, signals_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (measured_at, target_date, risk_score, alert_level,
                 json.dumps(signals, ensure_ascii=False)),
            )
            return int(cur.lastrowid)

    def record_transition(self, detected_at: datetime, target_date,
                          from_level: str, to_level: str,
                          from_score: Optional[float], to_score: float) -> int:
        """
        Enregistrer une transition d'alerte (changement de niveau).

        Direction calculée automatiquement :
            - ESCALATION    : niveau plus grave qu'avant
            - DE_ESCALATION : niveau moins grave qu'avant
            - STABLE        : pas de changement (cas limite, à éviter)
        """
        order = {"VERT": 0, "JAUNE": 1, "ORANGE": 2, "ROUGE": 3}
        if order[to_level] > order[from_level]:
            direction = "ESCALATION"
        elif order[to_level] < order[from_level]:
            direction = "DE_ESCALATION"
        else:
            direction = "STABLE"

        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO transitions
                    (detected_at, target_date, from_level, to_level,
                     from_score, to_score, direction)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (detected_at, target_date, from_level, to_level,
                 from_score, to_score, direction),
            )
            return int(cur.lastrowid)

    def record_notification(self, transition_id: int, sent_at: datetime,
                            recipient_name: str, recipient_role: str,
                            channel: str, target_address: str,
                            alert_level: str, status: str,
                            error_message: Optional[str] = None) -> int:
        """
        Tracer l'envoi (ou la simulation) d'une notification.

        status : SUCCESS / FAILED / SIMULATED
        Toutes les notifications sont enregistrées pour audit, y compris
        les échecs et les simulations.
        """
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO notifications
                    (sent_at, transition_id, recipient_name, recipient_role,
                     channel, target_address, alert_level, status, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (sent_at, transition_id, recipient_name, recipient_role,
                 channel, target_address, alert_level, status, error_message),
            )
            return int(cur.lastrowid)

    def mark_transition_notified(self, transition_id: int) -> None:
        """Marquer une transition comme notifiée (after fan-out complet)."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE transitions SET notified = 1 WHERE id = ?",
                (transition_id,),
            )

    # ─────────────────────────────────────────────────────────────
    # READ — lecture
    # ─────────────────────────────────────────────────────────────

    def last_state(self) -> Optional[dict]:
        """
        Récupérer le dernier état d'alerte mesuré.

        Returns:
            dict avec les colonnes de la table, ou None si la base est vide.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM alert_states ORDER BY measured_at DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None

    def recent_states(self, limit: int = 50) -> list[dict]:
        """Récupérer les N dernières évaluations (du plus récent au plus ancien)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM alert_states ORDER BY measured_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def recent_transitions(self, limit: int = 50) -> list[dict]:
        """Journal des dernières transitions (utile pour audit)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM transitions ORDER BY detected_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def recent_notifications(self, limit: int = 100) -> list[dict]:
        """Journal des dernières notifications (audit complet)."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM notifications ORDER BY sent_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def stats(self) -> dict:
        """
        Statistiques de l'historique — utile pour le tableau de bord et l'audit.

        Returns:
            dict avec :
                - n_states         : nombre total d'évaluations enregistrées
                - n_transitions    : nombre total de transitions détectées
                - n_notifications  : nombre total de notifications envoyées
                - first_recorded   : timestamp du premier enregistrement
                - last_recorded    : timestamp du plus récent
        """
        with self._connect() as conn:
            n_states = conn.execute(
                "SELECT COUNT(*) FROM alert_states"
            ).fetchone()[0]
            n_transitions = conn.execute(
                "SELECT COUNT(*) FROM transitions"
            ).fetchone()[0]
            n_notif = conn.execute(
                "SELECT COUNT(*) FROM notifications"
            ).fetchone()[0]
            first = conn.execute(
                "SELECT MIN(measured_at) FROM alert_states"
            ).fetchone()[0]
            last = conn.execute(
                "SELECT MAX(measured_at) FROM alert_states"
            ).fetchone()[0]

        return {
            "n_states":        int(n_states),
            "n_transitions":   int(n_transitions),
            "n_notifications": int(n_notif),
            "first_recorded":  first,
            "last_recorded":   last,
        }

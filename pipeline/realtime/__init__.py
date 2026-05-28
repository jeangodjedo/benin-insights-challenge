"""
BeninSentinel — Module temps réel.

Architecture du passage du prototype à l'alerte temps réel :

    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │  Streamer    │ ─→ │ Alert Engine │ ─→ │  Notifier    │ ─→ │  Providers   │
    │  (BigQuery)  │    │  (sentinel)  │    │  (routage)   │    │ console/SMTP │
    └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘
           ↓                  ↓                    ↓                    ↓
                       ┌──────────────┐
                       │   History    │
                       │   (SQLite)   │
                       └──────────────┘

Le système surveille en continu les données GDELT, recalcule le score
BeninSentinel à fréquence configurable, détecte les transitions d'alerte
(Vert → Jaune → Orange → Rouge) et notifie les bonnes personnes via les
bons canaux selon des règles transparentes.

Conçu pour une mise en production opérationnelle au sein de l'ANSSI-Bénin
ou de toute structure habilitée par la Présidence de la République.

Aligné PAG 2021-2026 — Gouvernance · Numérique · Bien-être social.

Author  : IROKO Analytics — Bénin Insights Challenge 2026
Version : 1.0 — Phase 2 (temps réel)
"""

from .history import AlertHistory
from .alert_engine import AlertEngine, AlertTransition
from .notifier import Notifier

__version__ = "1.0"
__all__ = ["AlertHistory", "AlertEngine", "AlertTransition", "Notifier"]

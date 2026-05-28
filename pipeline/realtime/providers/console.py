"""
BeninSentinel — Provider Console (toujours disponible, zéro configuration).

Ce provider est le fallback universel : il fonctionne sans aucune config
externe, ce qui en fait l'outil idéal pour les démos, les tests, et le
mode dégradé (si l'email tombe, on garde une trace visible).

Comportement :
    1. Affiche le bulletin dans la sortie standard (log)
    2. Persiste le bulletin dans un fichier JSON horodaté sous
       `data/alerts_journal/` — utile pour audit a posteriori
    3. Retourne toujours SUCCESS (sauf erreur disque)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .base import NotificationProvider, ProviderResult


class ConsoleProvider(NotificationProvider):
    """
    Provider d'affichage console + persistance fichier.

    À utiliser comme provider par défaut et comme provider de secours
    si les autres canaux sont indisponibles.
    """

    def __init__(self, journal_dir: Path = None, simulate: bool = False):
        super().__init__(simulate=simulate)
        self.journal_dir = Path(journal_dir) if journal_dir else Path("data/alerts_journal")
        self.journal_dir.mkdir(parents=True, exist_ok=True)

    @property
    def channel(self) -> str:
        return "console"

    def send(self, recipient: dict, payload: dict) -> ProviderResult:
        now = datetime.utcnow()

        if self.simulate:
            return ProviderResult(
                status="SIMULATED", channel=self.channel,
                target_address=recipient.get("address", "console"),
                sent_at=now,
            )

        try:
            # Affichage console (visible dans les logs du scheduler)
            print("=" * 70)
            print(f"[BeninSentinel] Alerte {payload.get('alert_level', 'N/A')}")
            print(f"  Destinataire : {recipient.get('name')} ({recipient.get('role')})")
            print(f"  Canal        : {self.channel}")
            print(f"  Sujet        : {payload.get('subject', 'N/A')}")
            print("-" * 70)
            print(payload.get("rendered_text", "")[:600])
            print("=" * 70)

            # Persistance fichier (audit a posteriori)
            timestamp = now.strftime("%Y%m%dT%H%M%S")
            safe_name = "".join(c if c.isalnum() else "_"
                                for c in recipient.get("name", "unknown"))
            filename = self.journal_dir / f"{timestamp}_{safe_name}.json"
            entry = {
                "sent_at":   now.isoformat(),
                "recipient": recipient,
                "payload":   {k: v for k, v in payload.items()
                              if k != "rendered_html"},  # html trop verbeux
            }
            filename.write_text(
                json.dumps(entry, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

            return ProviderResult(
                status="SUCCESS", channel=self.channel,
                target_address=str(filename),
                sent_at=now,
                extra={"journal_file": str(filename)},
            )

        except Exception as e:
            return ProviderResult(
                status="FAILED", channel=self.channel,
                target_address=recipient.get("address", "console"),
                sent_at=now,
                error_message=f"{type(e).__name__}: {e}",
            )

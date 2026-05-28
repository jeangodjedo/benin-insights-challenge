"""
BeninSentinel — Provider Webhook (HTTP POST).

Envoie le bulletin d'alerte sous forme de JSON via HTTP POST vers une
URL configurée. Permet l'intégration immédiate avec :
    - Slack       (Incoming Webhooks)
    - Microsoft Teams (Incoming Webhooks)
    - n8n / Make / Zapier (automatisations basse-config)
    - SI propre du Ministère (bus de messages interne)

L'URL cible est portée par chaque destinataire (champ `address`), ce qui
permet de configurer un webhook différent par cellule de crise (sécurité,
diplomatie, communication, etc.).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime

from .base import NotificationProvider, ProviderResult


class WebhookProvider(NotificationProvider):
    """
    Provider HTTP POST minimaliste (zéro dépendance externe — urllib stdlib).
    """

    def __init__(self, simulate: bool = False, timeout_seconds: int = 10):
        super().__init__(simulate=simulate)
        self.timeout = timeout_seconds

    @property
    def channel(self) -> str:
        return "webhook"

    def send(self, recipient: dict, payload: dict) -> ProviderResult:
        now = datetime.utcnow()
        url = recipient.get("address", "")

        if self.simulate or not url:
            return ProviderResult(
                status="SIMULATED", channel=self.channel,
                target_address=url, sent_at=now,
                extra={"reason": "simulate=True or empty URL"},
            )

        try:
            body = {
                "source":      "BeninSentinel",
                "alert_level": payload.get("alert_level"),
                "subject":     payload.get("subject"),
                "text":        payload.get("rendered_text"),
                "html":        payload.get("rendered_html"),
                "transition":  payload.get("transition"),
                "recipient":   {
                    "name": recipient.get("name"),
                    "role": recipient.get("role"),
                },
                "timestamp":   now.isoformat(),
            }
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(
                url, data=data, method="POST",
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.status
                if 200 <= status_code < 300:
                    return ProviderResult(
                        status="SUCCESS", channel=self.channel,
                        target_address=url, sent_at=now,
                        extra={"http_status": status_code},
                    )
                return ProviderResult(
                    status="FAILED", channel=self.channel,
                    target_address=url, sent_at=now,
                    error_message=f"HTTP {status_code}",
                )

        except urllib.error.HTTPError as e:
            return ProviderResult(
                status="FAILED", channel=self.channel,
                target_address=url, sent_at=now,
                error_message=f"HTTPError {e.code}: {e.reason}",
            )
        except urllib.error.URLError as e:
            return ProviderResult(
                status="FAILED", channel=self.channel,
                target_address=url, sent_at=now,
                error_message=f"URLError: {e.reason}",
            )
        except Exception as e:
            return ProviderResult(
                status="FAILED", channel=self.channel,
                target_address=url, sent_at=now,
                error_message=f"{type(e).__name__}: {e}",
            )

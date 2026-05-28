"""
BeninSentinel — Providers de notification.

Chaque provider implémente un canal de diffusion d'alerte (email, SMS,
console, webhook). Tous suivent l'interface commune `NotificationProvider`
définie dans `base.py`, ce qui permet d'en ajouter ou d'en remplacer
sans toucher au reste du système.

Providers disponibles actuellement :
    - ConsoleProvider : affiche et journalise (toujours disponible, sans config)
    - EmailProvider   : SMTP standard, configurable via .env
    - WebhookProvider : POST JSON sur une URL HTTP (intégration Slack/Teams/n8n)

Providers prêts à être branchés (interfaces définies) :
    - SMSProvider     : à câbler sur Twilio / Africa's Talking via clés API
"""

from .base    import NotificationProvider, ProviderResult
from .console import ConsoleProvider
from .email   import EmailProvider
from .webhook import WebhookProvider

__all__ = [
    "NotificationProvider",
    "ProviderResult",
    "ConsoleProvider",
    "EmailProvider",
    "WebhookProvider",
]

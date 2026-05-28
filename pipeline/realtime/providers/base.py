"""
BeninSentinel — Interface abstraite des providers de notification.

Tout nouveau canal de diffusion (Slack, Twilio, FCM, webhook custom)
implémente cette interface. Garanties contractuelles :

1. Aucun provider ne lève d'exception non maîtrisée — toute erreur
   est encapsulée dans un ProviderResult avec status="FAILED" et un
   message d'erreur explicite. Le scheduler doit pouvoir tourner même
   si un provider tombe.

2. Tous les providers gèrent un "mode simulé" (status="SIMULATED")
   activable globalement via la config. Pratique pour tester le
   système en intégration sans envoyer de vrais SMS aux préfets.

3. Le payload reçu est un dict structuré (alert, recipient, rendered_html,
   rendered_text). Le provider décide quoi en extraire selon son canal.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ProviderResult:
    """
    Résultat standardisé d'une tentative de notification.

    Tous les providers retournent ce type — uniformise le journal d'audit
    et permet au Notifier de tracer chaque envoi en base de données.
    """
    status:          str               # SUCCESS / FAILED / SIMULATED
    channel:         str               # email / sms / console / webhook
    target_address:  str               # adresse effective (email, n°, url)
    sent_at:         datetime
    error_message:   Optional[str] = None
    extra:           Optional[dict] = None

    def __post_init__(self):
        valid = {"SUCCESS", "FAILED", "SIMULATED"}
        if self.status not in valid:
            raise ValueError(f"status doit être dans {valid}, reçu {self.status!r}")


class NotificationProvider(ABC):
    """
    Interface abstraite — tout provider de notification l'implémente.

    Le contrat est délibérément minimal :
        - `channel`     (property)  : identifiant du canal ("email", "sms"...)
        - `send(...)`   (method)    : envoie la notification, retourne un ProviderResult

    Le mode simulé est géré par la classe parente — pas besoin de le
    reimplémenter dans chaque provider.
    """

    def __init__(self, simulate: bool = False):
        """
        Args:
            simulate : si True, le provider n'envoie rien réellement mais
                       retourne SIMULATED. Utile pour la mise en service.
        """
        self.simulate = simulate

    @property
    @abstractmethod
    def channel(self) -> str:
        """Identifiant unique du canal ('email', 'sms', 'console', 'webhook')."""

    @abstractmethod
    def send(self, recipient: dict, payload: dict) -> ProviderResult:
        """
        Envoyer une notification.

        Args:
            recipient : dict avec au minimum {name, role, address}.
                        address est l'identifiant cible (email, n° tél, URL...).
            payload   : dict avec au minimum {alert_level, subject,
                        rendered_text, rendered_html, transition}.

        Returns:
            ProviderResult avec status SUCCESS, FAILED ou SIMULATED.
            Ne lève jamais d'exception non maîtrisée.
        """

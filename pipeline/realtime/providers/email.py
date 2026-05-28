"""
BeninSentinel — Provider Email (SMTP).

Envoie un email HTML aux destinataires d'alerte via un serveur SMTP
standard. Configuration via variables d'environnement (.env) pour
ne jamais committer de credentials.

Variables d'environnement attendues :
    SENTINEL_SMTP_HOST       : hôte SMTP (ex : smtp.gmail.com)
    SENTINEL_SMTP_PORT       : port SMTP (587 pour TLS, 465 pour SSL)
    SENTINEL_SMTP_USER       : adresse expéditrice (login)
    SENTINEL_SMTP_PASSWORD   : mot de passe ou app-password
    SENTINEL_SMTP_FROM_NAME  : nom affiché de l'expéditeur (optionnel)
    SENTINEL_SMTP_USE_TLS    : '1' pour TLS sur port 587 (par défaut)

Si SENTINEL_SMTP_HOST n'est pas défini, le provider bascule
automatiquement en mode simulé et renvoie SIMULATED sans tenter d'envoi
— ainsi le système peut fonctionner sans interruption en démo, et
passer en production réelle simplement en ajoutant les variables .env.
"""

from __future__ import annotations

import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr

from .base import NotificationProvider, ProviderResult


class EmailProvider(NotificationProvider):
    """
    Provider SMTP standard.

    Pas de dépendance externe — utilise `smtplib` de la stdlib Python.
    Compatible avec Gmail, Outlook, Mailgun SMTP, SendGrid SMTP, Postfix,
    et tout serveur SMTP standard.
    """

    def __init__(self, simulate: bool = False):
        super().__init__(simulate=simulate)
        self.smtp_host     = os.getenv("SENTINEL_SMTP_HOST")
        self.smtp_port     = int(os.getenv("SENTINEL_SMTP_PORT", "587"))
        self.smtp_user     = os.getenv("SENTINEL_SMTP_USER", "")
        self.smtp_password = os.getenv("SENTINEL_SMTP_PASSWORD", "")
        self.from_name     = os.getenv("SENTINEL_SMTP_FROM_NAME", "BeninSentinel")
        # Adresse expéditrice — distincte du login SMTP (Brevo notamment exige
        # un sender vérifié, qui n'est PAS l'identifiant technique SMTP).
        # Fallback sur SMTP_USER si non défini (compatibilité Gmail standard).
        self.from_email    = os.getenv("SENTINEL_SMTP_FROM_EMAIL", "") or self.smtp_user
        self.use_tls       = os.getenv("SENTINEL_SMTP_USE_TLS", "1") == "1"

        # Si pas de SMTP configuré : passer en mode simulé silencieux.
        # C'est ce qui rend le système robuste en démo et en pré-production.
        if not self.smtp_host:
            self.simulate = True

    @property
    def channel(self) -> str:
        return "email"

    def send(self, recipient: dict, payload: dict) -> ProviderResult:
        now = datetime.utcnow()
        target = recipient.get("address", "")

        if self.simulate:
            return ProviderResult(
                status="SIMULATED", channel=self.channel,
                target_address=target, sent_at=now,
                extra={"reason": "no SMTP config or simulate=True"},
            )

        try:
            msg = EmailMessage()
            msg["From"]    = formataddr((self.from_name, self.from_email))
            msg["To"]      = formataddr((recipient.get("name", ""), target))
            msg["Subject"] = payload.get("subject", "Alerte BeninSentinel")
            msg.set_content(payload.get("rendered_text", ""))
            if "rendered_html" in payload:
                msg.add_alternative(payload["rendered_html"], subtype="html")

            ctx = ssl.create_default_context()
            if self.smtp_port == 465:
                # SMTPS implicite (SSL dès la connexion)
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=ctx) as server:
                    if self.smtp_user:
                        server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                # SMTP + STARTTLS (port 587 par défaut)
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.ehlo()
                    if self.use_tls:
                        server.starttls(context=ctx)
                        server.ehlo()
                    if self.smtp_user:
                        server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

            return ProviderResult(
                status="SUCCESS", channel=self.channel,
                target_address=target, sent_at=now,
            )

        except Exception as e:
            return ProviderResult(
                status="FAILED", channel=self.channel,
                target_address=target, sent_at=now,
                error_message=f"{type(e).__name__}: {e}",
            )

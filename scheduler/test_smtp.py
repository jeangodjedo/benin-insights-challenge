"""
BeninSentinel — Script de test rapide de la configuration SMTP.

Vérifie que le provider email est correctement configuré en envoyant un
bulletin de test à une adresse choisie.

Usage :
    # 1. Configurer .env (cp .env.example .env puis éditer)
    # 2. Lancer :
    python -m scheduler.test_smtp votre.email@example.com

    # Pour forcer le mode simulé (vérifier la config sans envoi réel) :
    python -m scheduler.test_smtp votre.email@example.com --simulate

Le script affiche le résultat (SUCCESS / SIMULATED / FAILED) et le
message d'erreur éventuel.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Permettre l'exécution depuis n'importe quel dossier
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv non installé : on lira directement os.environ

from pipeline.realtime.providers.email import EmailProvider


def build_test_payload() -> dict:
    """Construire un payload de bulletin de test JAUNE."""
    return {
        "alert_level":  "JAUNE",
        "subject":      "[BeninSentinel · TEST] Configuration SMTP validée",
        "rendered_text": (
            "Bonjour,\n\n"
            "Ceci est un test de configuration SMTP de BeninSentinel.\n"
            "Si vous recevez ce message, votre configuration SMTP est opérationnelle.\n\n"
            "Vous pouvez maintenant activer les notifications automatiques en\n"
            "lançant le scheduler en mode production :\n\n"
            "    python -m scheduler.run_realtime --loop\n\n"
            "Cordialement,\n"
            "BeninSentinel — IROKO Analytics\n"
            f"Test envoyé le {datetime.now().strftime('%d %B %Y à %H:%M:%S')}\n"
        ),
        "rendered_html": (
            "<html><body style='font-family:sans-serif;'>"
            "<div style='background:linear-gradient(135deg,#f59e0b 0%,#d97706 100%);"
            "color:white;padding:20px 28px;border-radius:10px;'>"
            "<h2 style='margin:0;'>BeninSentinel — Test SMTP réussi</h2>"
            "</div>"
            "<p style='padding:18px 4px;font-size:15px;'>Votre configuration SMTP "
            "est <strong>opérationnelle</strong>. Vous pouvez maintenant activer "
            "les notifications automatiques BeninSentinel.</p>"
            f"<p style='color:#6b7280;font-size:12px;'>Test envoyé le "
            f"{datetime.now().strftime('%d %B %Y à %H:%M:%S')}</p>"
            "</body></html>"
        ),
        "transition": {"from": "VERT", "to": "JAUNE",
                       "score": 0.45, "direction": "ESCALATION"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test rapide de la configuration SMTP BeninSentinel",
    )
    parser.add_argument(
        "email",
        help="Adresse email destinataire du test (ex. ton.email@gmail.com)",
    )
    parser.add_argument(
        "--simulate", action="store_true",
        help="Ne pas envoyer réellement, juste vérifier la config",
    )
    args = parser.parse_args()

    print("=" * 65)
    print("BeninSentinel — Test de configuration SMTP")
    print("=" * 65)

    provider = EmailProvider(simulate=args.simulate)

    print(f"  Host         : {provider.smtp_host or '(non configuré)'}")
    print(f"  Port         : {provider.smtp_port}")
    print(f"  User         : {provider.smtp_user or '(non configuré)'}")
    print(f"  From name    : {provider.from_name}")
    print(f"  TLS          : {'oui' if provider.use_tls else 'non'}")
    print(f"  Mode simulé  : {'OUI' if provider.simulate else 'NON (envoi réel)'}")
    print(f"  Destinataire : {args.email}")
    print("-" * 65)

    if not provider.smtp_host and not args.simulate:
        print("⚠️  SENTINEL_SMTP_HOST n'est pas défini dans l'environnement.")
        print("    Le provider basculera automatiquement en mode simulé.")
        print("    Pour un envoi réel : configurer .env (voir .env.example).")
        print("-" * 65)

    recipient = {
        "name":    "Test BeninSentinel",
        "role":    "test",
        "address": args.email,
    }
    payload = build_test_payload()

    print("Envoi en cours...")
    result = provider.send(recipient, payload)
    print("-" * 65)
    print(f"  Statut        : {result.status}")
    print(f"  Canal         : {result.channel}")
    print(f"  Adresse cible : {result.target_address}")
    print(f"  Envoyé à      : {result.sent_at}")
    if result.error_message:
        print(f"  Erreur        : {result.error_message}")
    if result.extra:
        print(f"  Détails       : {result.extra}")
    print("=" * 65)

    if result.status == "SUCCESS":
        print("✅  Email envoyé avec succès. Vérifiez votre boîte de réception")
        print("    (et le dossier Spam la première fois).")
        return 0
    if result.status == "SIMULATED":
        print("ℹ️   Mode simulé — aucun email envoyé. Pour un envoi réel,")
        print("    configurez votre .env avec les credentials SMTP.")
        return 0
    print("❌  Échec de l'envoi. Vérifiez :")
    print("    - SENTINEL_SMTP_USER et SENTINEL_SMTP_PASSWORD sont corrects")
    print("    - L'adresse expéditrice est vérifiée chez votre fournisseur")
    print("    - Le port (587 pour TLS, 465 pour SSL) correspond")
    print("    - Votre réseau autorise les connexions SMTP sortantes")
    return 1


if __name__ == "__main__":
    sys.exit(main())

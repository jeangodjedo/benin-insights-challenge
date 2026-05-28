"""
BeninSentinel — Scheduler temps réel (CLI).

Point d'entrée unique pour faire tourner le système d'alerte en continu.

Deux modes disponibles :

    # Un seul tick (pour cron système ou tâche planifiée)
    python -m scheduler.run_realtime --once

    # Boucle continue (intervalle configurable)
    python -m scheduler.run_realtime --loop --interval-minutes 60

Configuration via variables d'environnement (toutes optionnelles) :

    SENTINEL_DB_PATH         : chemin SQLite (par défaut data/sentinel_history.db)
    SENTINEL_RECIPIENTS_PATH : config/recipients.yaml par défaut
    SENTINEL_RULES_PATH      : config/notification_rules.yaml par défaut
    SENTINEL_INTERVAL_MIN    : intervalle de boucle (60 minutes par défaut)
    SENTINEL_PREFER_LOCAL    : '1' pour forcer le CSV local (démo)
    SENTINEL_SIMULATE        : '1' pour simuler les providers (pas d'envoi réel)
    SENTINEL_DAYS_BACK       : profondeur fenêtre GDELT (45 jours par défaut)

    Plus les variables SMTP de pipeline.realtime.providers.email pour
    l'envoi email réel.

Production-ready :
    - Crash-safe : un tick qui échoue est tracé, le scheduler continue
    - Logs structurés stdout (récupérables par systemd / journalctl)
    - Pas de dépendance externe (pas d'APScheduler) — time.sleep suffit
    - Compatible avec n'importe quel orchestrateur (cron, systemd, k8s CronJob)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

# Permettre l'exécution depuis n'importe quel dossier
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.realtime.orchestrator import SentinelOrchestrator


# ─────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────

def setup_logger() -> logging.Logger:
    """Configurer un logger formaté JSON-friendly pour journalctl/k8s."""
    logger = logging.getLogger("benin_sentinel_realtime")
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    ))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


# ─────────────────────────────────────────────────────────────
# CONSTRUCTION DE L'ORCHESTRATEUR
# ─────────────────────────────────────────────────────────────

def build_orchestrator() -> SentinelOrchestrator:
    """Lire la config (env vars) et construire l'orchestrateur."""
    db_path = Path(os.getenv(
        "SENTINEL_DB_PATH",
        str(PROJECT_ROOT / "data" / "sentinel_history.db"),
    ))
    recipients_path = Path(os.getenv(
        "SENTINEL_RECIPIENTS_PATH",
        str(PROJECT_ROOT / "config" / "recipients.yaml"),
    ))
    rules_path = Path(os.getenv(
        "SENTINEL_RULES_PATH",
        str(PROJECT_ROOT / "config" / "notification_rules.yaml"),
    ))
    prefer_local = os.getenv("SENTINEL_PREFER_LOCAL", "0") == "1"
    simulate     = os.getenv("SENTINEL_SIMULATE",     "0") == "1"

    return SentinelOrchestrator.default(
        db_path=db_path,
        recipients_path=recipients_path,
        rules_path=rules_path,
        prefer_local=prefer_local,
        simulate_providers=simulate,
    )


# ─────────────────────────────────────────────────────────────
# MODES D'EXÉCUTION
# ─────────────────────────────────────────────────────────────

def run_once(orchestrator: SentinelOrchestrator,
             days_back: int, logger: logging.Logger) -> int:
    """
    Exécuter un seul tick d'évaluation.

    Returns:
        0 si OK, 1 si erreur (utilisable comme exit code Unix).
    """
    logger.info("Démarrage d'un tick BeninSentinel (mode --once)")
    result = orchestrator.tick(days_back=days_back)
    logger.info(f"Tick terminé : {json.dumps(result.to_dict(), ensure_ascii=False)}")
    return 0 if result.status == "OK" else 1


def run_loop(orchestrator: SentinelOrchestrator,
             days_back: int, interval_minutes: int,
             logger: logging.Logger) -> int:
    """
    Boucle continue avec intervalle configurable.

    Reçoit SIGTERM/SIGINT proprement : sort de la boucle, ne tue pas un
    tick en cours. Compatible avec systemd, Kubernetes (rolling restart),
    Docker stop.
    """
    interval_seconds = interval_minutes * 60
    logger.info(
        f"Démarrage de la boucle BeninSentinel : "
        f"intervalle = {interval_minutes} min · fenêtre = {days_back} jours"
    )

    stop_requested = {"value": False}

    def _on_signal(signum, _frame):
        sig_name = signal.Signals(signum).name
        logger.info(f"Signal {sig_name} reçu — sortie propre demandée.")
        stop_requested["value"] = True

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT,  _on_signal)

    while not stop_requested["value"]:
        tick_started = time.time()
        try:
            result = orchestrator.tick(days_back=days_back)
            logger.info(
                f"Tick OK : level={result.alert_level} "
                f"score={result.risk_score:.3f if result.risk_score else 'N/A'} "
                f"transition={result.transition} "
                f"notifs={result.notifications_sent}"
            )
        except Exception as e:
            # Filet ultime : ne JAMAIS sortir de la boucle sur une erreur.
            logger.error(f"Erreur dans le tick : {type(e).__name__}: {e}")

        # Pause jusqu'au prochain tick, interruptible par signal
        elapsed = time.time() - tick_started
        to_sleep = max(0, interval_seconds - elapsed)
        slept = 0
        while slept < to_sleep and not stop_requested["value"]:
            chunk = min(1.0, to_sleep - slept)
            time.sleep(chunk)
            slept += chunk

    logger.info("Boucle terminée. Bye.")
    return 0


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="BeninSentinel — Scheduler temps réel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Exemples :\n"
            "  python -m scheduler.run_realtime --once\n"
            "  python -m scheduler.run_realtime --loop --interval-minutes 60\n"
            "  SENTINEL_PREFER_LOCAL=1 SENTINEL_SIMULATE=1 \\\n"
            "      python -m scheduler.run_realtime --loop\n"
        ),
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Exécuter un seul tick puis sortir (utilisable avec cron système)",
    )
    parser.add_argument(
        "--loop", action="store_true",
        help="Boucler en continu avec un intervalle configurable",
    )
    parser.add_argument(
        "--interval-minutes", type=int,
        default=int(os.getenv("SENTINEL_INTERVAL_MIN", "60")),
        help="Intervalle entre deux ticks en mode --loop (par défaut : 60 min)",
    )
    parser.add_argument(
        "--days-back", type=int,
        default=int(os.getenv("SENTINEL_DAYS_BACK", "45")),
        help="Profondeur de la fenêtre GDELT (par défaut : 45 jours)",
    )
    args = parser.parse_args()

    if not (args.once or args.loop):
        parser.print_help()
        return 1
    if args.once and args.loop:
        print("ERROR: choisir --once OU --loop, pas les deux.", file=sys.stderr)
        return 2

    logger = setup_logger()
    orchestrator = build_orchestrator()

    if args.once:
        return run_once(orchestrator, args.days_back, logger)
    return run_loop(orchestrator, args.days_back,
                    args.interval_minutes, logger)


if __name__ == "__main__":
    sys.exit(main())

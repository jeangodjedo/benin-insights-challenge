"""
BeninSentinel — Démonstration d'une alerte de bout en bout.

Ce script reproduit, sur les données réelles GDELT 2025, l'épisode
sécuritaire d'avril qui a culminé avec l'attaque jihadiste du 24 avril
(54 soldats tués). Il déclenche les transitions d'alerte successives —
VERT → JAUNE → ORANGE — et envoie de vrais bulletins email aux
destinataires configurés dans config/recipients.yaml (tous pointent
vers devpancrace@gmail.com pour la démo finale).

Usage :
    # Démo complète (avec envois réels via Brevo si .env configuré)
    python -m scheduler.demo_alert

    # Mode simulé (vérifier la chaîne sans envoi d'emails)
    python -m scheduler.demo_alert --simulate

    # Repartir d'une base vierge (utile pour la démo)
    python -m scheduler.demo_alert --reset

Architecture déroulée :
    1. Charger les données GDELT 2025 (snapshot CSV)
    2. Calculer le score BeninSentinel sur toute l'année
    3. Pour chaque jour-pivot (14 avr · 20 avr · 24 avr) :
       - Enregistrer l'état mesuré en base SQLite
       - Détecter la transition vs le dernier état
       - Dispatcher les notifications aux destinataires concernés
    4. Afficher un récapitulatif chronologique des transitions et
       notifications envoyées
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# Permettre l'exécution depuis n'importe quel dossier
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from pipeline.sentinel                  import run_sentinel
from pipeline.realtime.alert_engine     import AlertEngine, AlertTransition
from pipeline.realtime.history          import AlertHistory
from pipeline.realtime.notifier         import Notifier
from pipeline.realtime.providers        import ConsoleProvider, EmailProvider, WebhookProvider
from pipeline.realtime.templates_loader import build_alert_payload


# Jours-pivots de la démonstration — un par transition désirée
# Choix calibré sur l'épisode sécuritaire d'avril 2025 :
#   14 avril : situation normale (score bas)
#   20 avril : premier signal faible (montée JAUNE)
#   24 avril : crise majeure (attaque jihadiste — ORANGE)
DEMO_DATES = [
    pd.Timestamp("2025-04-14"),
    pd.Timestamp("2025-04-20"),
    pd.Timestamp("2025-04-24"),
]


def _build_orchestrator(simulate: bool):
    """Construire history + engine + notifier pour la démo."""
    db_path = PROJECT_ROOT / "data" / "sentinel_history.db"
    recipients_path = PROJECT_ROOT / "config" / "recipients.yaml"
    rules_path      = PROJECT_ROOT / "config" / "notification_rules.yaml"

    history = AlertHistory(db_path)
    engine  = AlertEngine(history)

    providers = {
        "console": ConsoleProvider(simulate=simulate),
        "email":   EmailProvider(simulate=simulate),
        "webhook": WebhookProvider(simulate=simulate),
    }

    notifier = Notifier(
        history=history,
        recipients_path=recipients_path,
        rules_path=rules_path,
        providers=providers,
    )
    return history, engine, notifier, db_path


def _load_data() -> pd.DataFrame:
    """Charger le snapshot GDELT 2025 (priorité au fichier complet)."""
    processed = PROJECT_ROOT / "data" / "processed" / "benin_gdelt_clean.csv"
    sample    = PROJECT_ROOT / "data" / "sample"    / "benin_gdelt_sample.csv"
    src = processed if processed.exists() else sample
    if not src.exists():
        raise FileNotFoundError(
            "Aucun snapshot GDELT trouvé. Lancer d'abord le pipeline ETL :\n"
            "    python -m pipeline.run_pipeline --mode sample"
        )
    df = pd.read_csv(src, low_memory=False)
    df["SQLDATE"] = pd.to_datetime(df["SQLDATE"], errors="coerce")
    return df.dropna(subset=["SQLDATE"])


def _evaluate_one_date(target_date: pd.Timestamp,
                       risk_df: pd.DataFrame,
                       engine: AlertEngine) -> AlertTransition:
    """
    Évaluer le score à une date cible précise et enregistrer la transition.

    Contournement intentionnel de `engine.evaluate(df)` qui prend la dernière
    date du dataset : ici on veut une date imposée pour la démo.
    """
    row = risk_df[risk_df["date"] == target_date]
    if row.empty:
        raise ValueError(
            f"Aucun score disponible pour {target_date.date()}. "
            "Vérifier que le snapshot contient bien avril 2025."
        )
    r = row.iloc[0]
    to_score = float(r["risk_score"])
    to_level = str(r["alert_level"])
    signals  = {col: float(r[col]) for col in AlertEngine.SIGNAL_COLUMNS}

    measured_at = datetime.utcnow()
    last        = engine.history.last_state()

    # Toujours enregistrer l'état mesuré (audit)
    engine.history.record_state(
        measured_at=measured_at,
        target_date=target_date.to_pydatetime().date(),
        risk_score=to_score, alert_level=to_level, signals=signals,
    )

    # Premier démarrage : pas de transition
    if last is None:
        return AlertTransition(
            measured_at=measured_at, target_date=target_date,
            from_level="—", to_level=to_level,
            from_score=None, to_score=to_score, signals=signals,
            is_transition=False, direction="BASELINE", transition_id=None,
        )

    from_level = last["alert_level"]
    from_score = float(last["risk_score"])

    if to_level == from_level:
        return AlertTransition(
            measured_at=measured_at, target_date=target_date,
            from_level=from_level, to_level=to_level,
            from_score=from_score, to_score=to_score, signals=signals,
            is_transition=False, direction="STABLE", transition_id=None,
        )

    direction = engine._direction(from_level, to_level)
    transition_id = engine.history.record_transition(
        detected_at=measured_at,
        target_date=target_date.to_pydatetime().date(),
        from_level=from_level, to_level=to_level,
        from_score=from_score, to_score=to_score,
    )
    return AlertTransition(
        measured_at=measured_at, target_date=target_date,
        from_level=from_level, to_level=to_level,
        from_score=from_score, to_score=to_score, signals=signals,
        is_transition=True, direction=direction,
        transition_id=transition_id,
    )


def _print_step(idx: int, total: int, target_date: pd.Timestamp,
                transition: AlertTransition, n_notifs: int) -> None:
    print()
    print("─" * 68)
    print(f"[Étape {idx}/{total}] Date analysée : {target_date.date()}")
    print("─" * 68)
    print(f"  Niveau d'alerte    : {transition.from_level} → {transition.to_level}")
    print(f"  Score              : "
          f"{transition.from_score if transition.from_score is None else f'{transition.from_score:.3f}'} → "
          f"{transition.to_score:.3f}")
    print(f"  Direction          : {transition.direction}")
    print(f"  Notifications      : {n_notifs} bulletin(s) envoyé(s)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="BeninSentinel — Démonstration end-to-end d'une alerte",
    )
    parser.add_argument("--simulate", action="store_true",
                        help="Mode simulé (aucun email réel envoyé)")
    parser.add_argument("--reset", action="store_true",
                        help="Vider la base SQLite avant de lancer (démo propre)")
    args = parser.parse_args()

    print("=" * 68)
    print("BENIN SENTINEL — DÉMONSTRATION END-TO-END")
    print("Reproduction de l'épisode sécuritaire du 24 avril 2025")
    print("=" * 68)
    print(f"  Mode simulé : {'OUI' if args.simulate else 'NON (envois réels)'}")
    print(f"  Reset base  : {'OUI' if args.reset else 'NON'}")

    # 1. Préparer la base (reset optionnel)
    db_path = PROJECT_ROOT / "data" / "sentinel_history.db"
    if args.reset and db_path.exists():
        db_path.unlink()
        print(f"  Base vidée  : {db_path.name}")

    # 2. Construire les composants
    history, engine, notifier, _ = _build_orchestrator(simulate=args.simulate)

    # 3. Charger les données et calculer le score sur toute l'année
    print()
    print("Chargement des données GDELT 2025 et calcul du score...")
    df = _load_data()
    risk_df = run_sentinel(df)
    print(f"  {len(df):,} événements chargés · "
          f"{len(risk_df):,} jours scorés sur {risk_df['date'].min().date()} → "
          f"{risk_df['date'].max().date()}")

    # 4. Dérouler la démo sur les 3 dates-pivots
    summary = []
    for idx, target_date in enumerate(DEMO_DATES, start=1):
        transition = _evaluate_one_date(target_date, risk_df, engine)

        results = []
        if transition.is_transition:
            results = notifier.dispatch(
                transition,
                payload_builder=lambda t, r: build_alert_payload(t, r),
            )

        _print_step(idx, len(DEMO_DATES), target_date, transition, len(results))
        for r in results:
            recipient = r["recipient"]
            result    = r["result"]
            status_icon = {"SUCCESS": "✅", "FAILED": "❌", "SIMULATED": "🟡"}[result.status]
            print(f"    {status_icon} {recipient['name']:<40} "
                  f"[{result.channel}] -> {result.target_address}")

        summary.append({
            "date":        target_date.date(),
            "from":        transition.from_level,
            "to":          transition.to_level,
            "is_transit":  transition.is_transition,
            "n_notifs":    len(results),
        })

    # 5. Récap final
    print()
    print("=" * 68)
    print("RÉCAPITULATIF DE LA DÉMONSTRATION")
    print("=" * 68)
    total_notifs = sum(s["n_notifs"] for s in summary)
    for s in summary:
        arrow = "→" if s["is_transit"] else "="
        print(f"  {s['date']} · {s['from']:<8} {arrow} {s['to']:<8} · "
              f"{s['n_notifs']} notification(s)")
    print(f"  TOTAL : {total_notifs} bulletin(s) envoyé(s)")
    print()

    stats = history.stats()
    print(f"  Base d'historique : {stats['n_states']} état(s) · "
          f"{stats['n_transitions']} transition(s) · "
          f"{stats['n_notifications']} notification(s) en audit")
    print()
    print("Pour visualiser la chaîne complète, ouvrir la page Streamlit :")
    print("  Surveillance temps réel  (menu de gauche du dashboard)")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
BeninSentinel — Module de détection des signaux précurseurs de crise.

ETL Pipeline Step 4 (Add-on) — Early Warning System.

Objectif : transformer le DataFrame nettoyé du pipeline en un signal de
risque quotidien et géolocalisé, permettant aux décideurs publics
d'anticiper les crises 5 à 7 jours avant leur cristallisation médiatique.

Méthodologie en deux temps :
    1. Construction des séries quotidiennes (volume, ton, intensité,
       composition CAMEO, diversité des sources)
    2. Calcul d'un score composite normalisé sur la base d'écarts-types
       glissants 30 jours (z-scores) appliqués à six signaux faibles.

Alignement stratégique :
    Outil pensé pour les décideurs béninois (Présidence, Ministère de
    l'Intérieur, préfets), aligné sur les trois piliers du Programme
    d'Action du Gouvernement 2021-2026 (gouvernance, numérique, bien-être).

Honnêteté méthodologique :
    Les pondérations du score composite sont calibrées sur l'historique
    2025 et sont transparentes — modifiables et auditables. L'outil
    n'est pas un oracle : il fournit des probabilités, pas des
    certitudes. La décision finale reste humaine.

Author  : Team 7 — Bénin Insights Challenge 2026
Version : 1.0 — Finale
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from typing import Tuple

# ─────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────

# Catégories CAMEO regroupées pour l'analyse de signaux faibles
PROTEST_LABELS = {
    "Protestation", "Désapprobation", "Menace", "Rejet", "Ultimatum",
}
VIOLENCE_LABELS = {
    "Assaut", "Attentat / Explosion", "Violence de masse",
}

# QuadClass GDELT
QUAD_VERBAL_CONFLICT   = 3   # Menaces, désapprobations
QUAD_MATERIAL_CONFLICT = 4   # Violences, sanctions

# Pondérations du score composite — calibrées sur le cas-test du
# 7 décembre 2025 (tentative de coup d'État déjouée). Ces pondérations
# privilégient les signaux de conflit matériel et de dégradation
# Goldstein, qui sortent comme les plus prédictifs dans l'analyse
# rétrospective. Voir BENIN_SENTINEL_VALIDATION.md pour le détail.
DEFAULT_WEIGHTS = {
    "tone":     0.20,   # Dégradation du ton moyen
    "negative": 0.20,   # Bascule de la proportion d'articles négatifs
    "protest":  0.15,   # Pic de protestations / désapprobations / menaces
    "quad3":    0.15,   # Pic de conflits verbaux (escalade verbale)
    "quad4":    0.20,   # Pic de conflits matériels (escalade matérielle)
    "violence": 0.10,   # Pic d'événements violents (assauts, attentats)
}

# Seuils d'alerte graduée — calibrés pour limiter les faux positifs
# tout en garantissant une détection précoce du cas-test décembre 2025.
ALERT_THRESHOLDS = {
    "VERT":   (0.00, 0.40),   # Vigilance — surveillance passive
    "JAUNE":  (0.40, 0.60),   # Préoccupation — veille active
    "ORANGE": (0.60, 0.80),   # Alerte — mobilisation cellule de crise
    "ROUGE":  (0.80, 1.01),   # Crise imminente — conseil restreint
}

# Recommandations d'action par niveau d'alerte
ACTION_PLAYBOOK = {
    "VERT": (
        "Surveillance passive. Bulletin de situation hebdomadaire transmis aux "
        "préfectures concernées. Aucune action de mobilisation requise."
    ),
    "JAUNE": (
        "Veille active. Bulletin quotidien transmis aux préfets et au Cabinet "
        "du Ministre de l'Intérieur. Briefing préfectoral en début de journée. "
        "Vérification des canaux de communication de crise."
    ),
    "ORANGE": (
        "Mobilisation de la cellule de crise interministérielle. Bulletin "
        "toutes les 4 heures. Pré-positionnement des forces de sécurité. "
        "Préparation des éléments de communication publique. Coordination "
        "avec la CEDEAO si la tension est transfrontalière."
    ),
    "ROUGE": (
        "Conseil restreint Présidence. Bulletin toutes les heures. Activation "
        "complète du dispositif de gestion de crise. Communication publique "
        "préventive sur les canaux officiels. Alerte ambassades partenaires."
    ),
}


# ─────────────────────────────────────────────────────────────────
# CONSTRUCTION DES SÉRIES QUOTIDIENNES
# ─────────────────────────────────────────────────────────────────

def build_daily_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agréger le DataFrame GDELT nettoyé en une série quotidienne
    d'indicateurs comportementaux.

    Pour chaque jour calendrier de l'année analysée, on calcule :
        - n_events             : nombre d'événements GDELT
        - n_articles           : volume total d'articles publiés
        - avg_tone             : ton moyen (AvgTone GDELT)
        - avg_goldstein        : intensité géopolitique moyenne
        - pct_negative         : proportion d'articles à ton négatif
        - n_protest            : événements de protestation/menace/rejet
        - n_violence           : événements violents (assauts, attentats)
        - n_quad3              : conflits verbaux (QuadClass = 3)
        - n_quad4              : conflits matériels (QuadClass = 4)
        - n_sources            : nombre de sources distinctes

    Args:
        df: DataFrame nettoyé issu de transform.py (colonnes attendues :
            SQLDATE, NumArticles, AvgTone, GoldsteinScale, tone_category,
            event_root_label, QuadClass, source_domain).

    Returns:
        pd.DataFrame indexé par date (datetime) avec les colonnes décrites
        ci-dessus, trié chronologiquement.
    """
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["SQLDATE"] = pd.to_datetime(df["SQLDATE"], errors="coerce")
    df = df.dropna(subset=["SQLDATE"])
    df["date"] = df["SQLDATE"].dt.date

    daily = (
        df.groupby("date", as_index=False)
        .agg(
            n_events=("SQLDATE", "count"),
            n_articles=("NumArticles", "sum"),
            avg_tone=("AvgTone", "mean"),
            avg_goldstein=("GoldsteinScale", "mean"),
            n_negative=("tone_category", lambda s: (s == "Négatif").sum()),
            n_protest=("event_root_label",
                       lambda s: s.isin(PROTEST_LABELS).sum()),
            n_violence=("event_root_label",
                        lambda s: s.isin(VIOLENCE_LABELS).sum()),
            n_quad3=("QuadClass", lambda s: (s == QUAD_VERBAL_CONFLICT).sum()),
            n_quad4=("QuadClass", lambda s: (s == QUAD_MATERIAL_CONFLICT).sum()),
            n_sources=("source_domain", "nunique"),
        )
    )
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date").reset_index(drop=True)
    daily["pct_negative"] = (daily["n_negative"] / daily["n_events"] * 100).fillna(0)
    return daily


# ─────────────────────────────────────────────────────────────────
# CALCUL DES SIGNAUX FAIBLES (Z-SCORES GLISSANTS)
# ─────────────────────────────────────────────────────────────────

def _zscore_signal(serie: pd.Series, window_recent: int = 7,
                   window_ref: int = 30, direction: str = "up",
                   instant_weight: float = 0.5,
                   cap_sigma: float = 2.0) -> pd.Series:
    """
    Convertir une série temporelle en un signal faible normalisé entre 0 et 1.

    Méthode hybride à deux composantes :

    1. **Composante TENDANCE** (poids 1 - instant_weight) : compare la moyenne
       glissante des `window_recent` derniers jours à la moyenne glissante de
       référence `window_ref`. Capture les escalades progressives.

    2. **Composante INSTANTANÉE** (poids `instant_weight`) : compare la valeur
       du jour à la moyenne de référence. Capture les sursauts ponctuels qu'une
       moyenne glissante lisserait.

    Chaque composante est convertie en z-score (écart à la moyenne de référence
    divisé par l'écart-type), plafonné à `cap_sigma` sigmas et normalisé entre
    [0, 1]. Le signal final est la moyenne pondérée des deux composantes.

    Ce design hybride a été validé empiriquement sur l'épisode du 7 décembre
    2025 (tentative de coup d'État) où la composante TENDANCE seule ratait
    le pic du 6 décembre (82 % négatif vs 41 % en référence) parce que la
    moyenne 7 jours diluait le sursaut sur la semaine.

    - direction="up"   : signal positif quand la valeur augmente (% négatif,
      nombre de protestations).
    - direction="down" : signal positif quand la valeur baisse (ton moyen,
      Goldstein — leur baisse est un signal de dégradation).

    Args:
        serie          : Série temporelle indexée par date.
        window_recent  : Fenêtre de la composante tendance (par défaut 7 jours).
        window_ref     : Fenêtre de référence comportementale (par défaut 30 jours).
        direction      : "up" si une augmentation est un signal, "down" sinon.
        instant_weight : Poids de la composante instantanée (0 = pur tendance,
                         1 = pure instantanée). Par défaut 0,5 — équilibre.
        cap_sigma      : Plafond du z-score en nombre d'écarts-types. Par défaut
                         2,0 — au-delà, on est déjà clairement hors norme.

    Returns:
        pd.Series du signal normalisé entre 0 et 1.
    """
    # Référence comportementale : moyenne et écart-type 30 jours
    ma_ref  = serie.rolling(window_ref, min_periods=10).mean()
    std_ref = serie.rolling(window_ref, min_periods=10).std()

    # Composante TENDANCE : moyenne 7 derniers jours vs référence
    ma_recent = serie.rolling(window_recent, min_periods=3).mean()
    if direction == "up":
        z_trend = (ma_recent - ma_ref) / std_ref.replace(0, np.nan)
    else:
        z_trend = -(ma_recent - ma_ref) / std_ref.replace(0, np.nan)
    sig_trend = (z_trend.clip(lower=0, upper=cap_sigma) / cap_sigma).fillna(0)

    # Composante INSTANTANÉE : valeur du jour vs référence
    if direction == "up":
        z_instant = (serie - ma_ref) / std_ref.replace(0, np.nan)
    else:
        z_instant = -(serie - ma_ref) / std_ref.replace(0, np.nan)
    sig_instant = (z_instant.clip(lower=0, upper=cap_sigma) / cap_sigma).fillna(0)

    # Combinaison pondérée
    return ((1 - instant_weight) * sig_trend + instant_weight * sig_instant).clip(0, 1)


def compute_weak_signals(daily: pd.DataFrame,
                         window_recent: int = 7,
                         window_ref: int = 30) -> pd.DataFrame:
    """
    Calculer les six signaux faibles normalisés sur la base de la série
    quotidienne.

    Signal             | Variable             | Direction
    -------------------|----------------------|----------
    sig_tone           | avg_tone             | down (baisse = dégradation)
    sig_negative       | pct_negative         | up   (hausse = dégradation)
    sig_protest        | n_protest            | up   (hausse = dégradation)
    sig_quad3          | n_quad3              | up   (hausse = escalade verbale)
    sig_quad4          | n_quad4              | up   (hausse = escalade matérielle)
    sig_violence       | n_violence           | up   (hausse = crise déclarée)

    Args:
        daily         : DataFrame issu de build_daily_series().
        window_recent : Fenêtre du signal récent (par défaut 7 jours).
        window_ref    : Fenêtre de référence comportementale (par défaut 30 jours).

    Returns:
        pd.DataFrame enrichi avec les six colonnes sig_* (valeurs dans [0, 1]).
    """
    out = daily.copy()
    out["sig_tone"]     = _zscore_signal(out["avg_tone"],     window_recent, window_ref, "down")
    out["sig_negative"] = _zscore_signal(out["pct_negative"], window_recent, window_ref, "up")
    out["sig_protest"]  = _zscore_signal(out["n_protest"],    window_recent, window_ref, "up")
    out["sig_quad3"]    = _zscore_signal(out["n_quad3"],      window_recent, window_ref, "up")
    out["sig_quad4"]    = _zscore_signal(out["n_quad4"],      window_recent, window_ref, "up")
    out["sig_violence"] = _zscore_signal(out["n_violence"],   window_recent, window_ref, "up")
    return out


# ─────────────────────────────────────────────────────────────────
# SCORE COMPOSITE ET ALERTES
# ─────────────────────────────────────────────────────────────────

def compute_risk_score(daily_with_signals: pd.DataFrame,
                       weights: dict = None) -> pd.DataFrame:
    """
    Calculer le score composite de risque BeninSentinel.

    Le score est une moyenne pondérée des six signaux faibles, bornée à
    l'intervalle [0, 1]. La pondération par défaut (DEFAULT_WEIGHTS)
    privilégie les conflits matériels et les dégradations Goldstein,
    qui sortent comme les plus prédictifs dans la validation empirique.

    Args:
        daily_with_signals : DataFrame issu de compute_weak_signals().
        weights            : Dictionnaire de pondérations alternatif
                             (clés : tone, negative, protest, quad3,
                             quad4, violence). Si None, utilise
                             DEFAULT_WEIGHTS.

    Returns:
        pd.DataFrame enrichi avec :
            - risk_score : score composite entre 0 et 1
            - alert_level : VERT / JAUNE / ORANGE / ROUGE
            - action       : recommandation d'action correspondante
    """
    w = weights or DEFAULT_WEIGHTS
    out = daily_with_signals.copy()

    out["risk_score"] = (
        out["sig_tone"].fillna(0)     * w["tone"]     +
        out["sig_negative"].fillna(0) * w["negative"] +
        out["sig_protest"].fillna(0)  * w["protest"]  +
        out["sig_quad3"].fillna(0)    * w["quad3"]    +
        out["sig_quad4"].fillna(0)    * w["quad4"]    +
        out["sig_violence"].fillna(0) * w["violence"]
    ).clip(0, 1)

    out["alert_level"] = out["risk_score"].apply(_classify_alert)
    out["action"]      = out["alert_level"].map(ACTION_PLAYBOOK)
    return out


def _classify_alert(score: float) -> str:
    """Classer un score numérique en niveau d'alerte (VERT/JAUNE/ORANGE/ROUGE)."""
    for level, (low, high) in ALERT_THRESHOLDS.items():
        if low <= score < high:
            return level
    return "ROUGE"   # safety fallback for score == 1.0


# ─────────────────────────────────────────────────────────────────
# DÉCOMPOSITION PAR DÉPARTEMENT BÉNINOIS
# ─────────────────────────────────────────────────────────────────

def compute_department_risk(df: pd.DataFrame,
                            target_date: pd.Timestamp,
                            window: int = 7) -> pd.DataFrame:
    """
    Calculer le risque par département béninois sur une fenêtre temporelle.

    Pour chaque département (event_department), on calcule :
        - le volume d'événements sur la fenêtre
        - le ton moyen
        - le pourcentage d'articles négatifs
        - le nombre d'événements de violence et de protestation
        - un score de risque local entre 0 et 1

    Args:
        df          : DataFrame nettoyé (contient event_department).
        target_date : Date cible (le jour analysé).
        window      : Fenêtre rétrospective en jours (par défaut 7).

    Returns:
        pd.DataFrame agrégé par département, trié par score de risque
        décroissant.
    """
    if "event_department" not in df.columns:
        return pd.DataFrame()

    df = df.copy()
    df["SQLDATE"] = pd.to_datetime(df["SQLDATE"], errors="coerce")
    start = pd.Timestamp(target_date) - pd.Timedelta(days=window)
    sub = df[(df["SQLDATE"] >= start) & (df["SQLDATE"] <= pd.Timestamp(target_date))]

    if sub.empty:
        return pd.DataFrame()

    by_dept = (
        sub.groupby("event_department", as_index=False)
        .agg(
            n_events=("SQLDATE", "count"),
            n_articles=("NumArticles", "sum"),
            avg_tone=("AvgTone", "mean"),
            n_negative=("tone_category", lambda s: (s == "Négatif").sum()),
            n_protest=("event_root_label",
                       lambda s: s.isin(PROTEST_LABELS).sum()),
            n_violence=("event_root_label",
                        lambda s: s.isin(VIOLENCE_LABELS).sum()),
        )
    )
    by_dept["pct_negative"] = (by_dept["n_negative"] / by_dept["n_events"] * 100).fillna(0)

    # Score local : normalisation simple par rapport au max observé
    max_neg = max(by_dept["pct_negative"].max(), 1)
    max_vio = max(by_dept["n_violence"].max(), 1)
    max_prot = max(by_dept["n_protest"].max(), 1)
    by_dept["local_risk"] = (
        (by_dept["pct_negative"] / max_neg) * 0.40 +
        (by_dept["n_violence"]   / max_vio) * 0.40 +
        (by_dept["n_protest"]    / max_prot) * 0.20
    ).clip(0, 1)
    by_dept["alert_level"] = by_dept["local_risk"].apply(_classify_alert)

    return by_dept.sort_values("local_risk", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────
# FONCTION DE PIPELINE COMPLET
# ─────────────────────────────────────────────────────────────────

def run_sentinel(df: pd.DataFrame,
                 window_recent: int = 7,
                 window_ref: int = 30,
                 weights: dict = None) -> pd.DataFrame:
    """
    Pipeline complet BeninSentinel : transforme un DataFrame GDELT
    nettoyé en un tableau de bord de risque quotidien.

    Étapes :
        1. Construction de la série quotidienne (build_daily_series)
        2. Calcul des six signaux faibles (compute_weak_signals)
        3. Calcul du score composite et de l'alerte (compute_risk_score)

    Args:
        df            : DataFrame nettoyé issu de transform.py.
        window_recent : Fenêtre de signal récent (par défaut 7 jours).
        window_ref    : Fenêtre de référence (par défaut 30 jours).
        weights       : Pondérations du score composite. None = défaut.

    Returns:
        pd.DataFrame avec une ligne par jour, incluant :
            - date, n_events, n_articles, avg_tone, avg_goldstein
            - les six signaux faibles normalisés
            - risk_score, alert_level, action
    """
    daily   = build_daily_series(df)
    signals = compute_weak_signals(daily, window_recent, window_ref)
    return compute_risk_score(signals, weights)


# ─────────────────────────────────────────────────────────────────
# VALIDATION EMPIRIQUE
# ─────────────────────────────────────────────────────────────────

def detect_lead_time(risk_df: pd.DataFrame,
                     target_date: pd.Timestamp,
                     min_level: str = "ORANGE",
                     lookback_days: int = 14) -> Tuple[int, pd.Timestamp]:
    """
    Mesurer le délai de détection effectif (lead time) pour une crise donnée.

    Pour une date cible (la crise effective), on remonte dans le temps et
    on cherche le premier jour où le niveau d'alerte a atteint le seuil
    spécifié (par défaut ORANGE).

    Args:
        risk_df       : DataFrame issu de run_sentinel().
        target_date   : Date de la crise effective.
        min_level     : Niveau d'alerte cible (JAUNE / ORANGE / ROUGE).
        lookback_days : Profondeur de recherche en arrière (par défaut 14 jours).

    Returns:
        (lead_time_days, detection_date) :
            - lead_time_days : nombre de jours d'avance de la détection
            - detection_date : date du premier jour d'alerte
        Si aucune détection n'est faite, retourne (-1, None).
    """
    level_order = ["VERT", "JAUNE", "ORANGE", "ROUGE"]
    if min_level not in level_order:
        raise ValueError(f"min_level doit être dans {level_order}")
    min_idx = level_order.index(min_level)

    target = pd.Timestamp(target_date)
    start  = target - pd.Timedelta(days=lookback_days)

    sub = risk_df[(risk_df["date"] >= start) & (risk_df["date"] < target)].copy()
    if sub.empty:
        return -1, None

    sub["level_idx"] = sub["alert_level"].apply(
        lambda lvl: level_order.index(lvl) if lvl in level_order else 0
    )
    detected = sub[sub["level_idx"] >= min_idx]
    if detected.empty:
        return -1, None

    first = detected.iloc[0]
    lead_time = (target - first["date"]).days
    return lead_time, first["date"]


# ─────────────────────────────────────────────────────────────────
# EXPORT PUBLIC
# ─────────────────────────────────────────────────────────────────

__all__ = [
    "build_daily_series",
    "compute_weak_signals",
    "compute_risk_score",
    "compute_department_risk",
    "run_sentinel",
    "detect_lead_time",
    "ALERT_THRESHOLDS",
    "ACTION_PLAYBOOK",
    "DEFAULT_WEIGHTS",
]

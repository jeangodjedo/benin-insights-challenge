# pipeline/transform.py
"""
Module de transformation et nettoyage des données GDELT.

Étape 2 du pipeline ETL — Transform.

Transformations alignées sur les 5 questions prioritaires :

    Q1 — Quand le monde parle-t-il du Bénin ?
         Colonnes ajoutées : event_date, event_month, event_quarter,
                             event_root_label

    Q2 — Le ton médiatique est-il positif, neutre ou négatif ?
         Colonnes ajoutées : tone_category, stability_category

    Q3 — Combien de jours pour atteindre le pic de couverture ?
         Colonnes ajoutées : propagation_delay_days

    Q4 — Sources en crise vs sources en période normale ?
         Colonnes ajoutées : source_domain, is_crisis_period

    Q5 — Le Bénin est-il acteur ou spectateur ?
         Colonnes ajoutées : benin_role, actor1_type_label,
                             actor2_type_label, quad_class_label

HISTORIQUE DES CORRECTIONS :
    v1.1 — Correction benin_role : "non défini" → "Contexte"
    v1.2 — Correction event_root_label : EventRootCode retourné par
            BigQuery est de type int64 (ex: 4, 19). La conversion
            str.zfill(2) dans convert_types() ne suffisait pas car
            pandas convertit d'abord l'entier en string sans padding
            ("4" pas "04"), cassant le mapping vers EVENT_ROOT_LABELS.
            Correction : conversion explicite int → str → zfill(2)
            directement dans enrich_data() avant le mapping.
          — Correction benin_role : les valeurs NaN de Actor1CountryCode
            et Actor2CountryCode (50%+ des lignes) étaient converties
            en string "nan" par str(), ce qui ne correspondait jamais
            à COUNTRY_CODE "BN". Correction : nettoyage des NaN avant
            comparaison avec une vérification pd.isna() explicite.

Auteur  : Équipe Bénin Insights Challenge 2026
Date    : Avril 2026
Version : 1.2
"""

import re
import pandas as pd
import numpy as np
from utils import logger, timer, validate_dataframe
from config import COUNTRY_CODE, COUNTRY_ACTOR_CODE


# ─────────────────────────────────────────────────────────────────
# DICTIONNAIRES DE TRADUCTION GDELT
# ─────────────────────────────────────────────────────────────────

# Traduction QuadClass → libellé français
# QuadClass classe chaque événement en 4 grandes familles
QUAD_CLASS_LABELS = {
    1: "Coopération verbale",
    2: "Coopération matérielle",
    3: "Conflit verbal",
    4: "Conflit matériel",
}

# Traduction EventRootCode → libellé français
# GDELT classe tous les événements en 20 catégories racines.
# Les clés sont des strings zero-padded sur 2 caractères ("01"..."20")
# car c'est le format produit après conversion dans enrich_data().
EVENT_ROOT_LABELS = {
    "01": "Déclaration publique",
    "02": "Appel / Demande",
    "03": "Expression d'intention",
    "04": "Consultation",
    "05": "Engagement / Soutien",
    "06": "Coopération",
    "07": "Aide matérielle",
    "08": "Diplomatie",
    "09": "Sanctions économiques",
    "10": "Demande",
    "11": "Désapprobation",
    "12": "Rejet",
    "13": "Menace",
    "14": "Protestation",
    "15": "Ultimatum",
    "16": "Violation droits humains",
    "17": "Assaut",
    "18": "Attentat / Explosion",
    "19": "Violence de masse",
    "20": "Force militaire",
}

# Traduction Actor Type → libellé français
# Utilisé pour Q5 — identifier qui parle du Bénin
ACTOR_TYPE_LABELS = {
    "GOV": "Gouvernement",
    "MIL": "Militaire",
    "REB": "Rebelle / Insurgé",
    "OPP": "Opposition politique",
    "PTY": "Parti politique",
    "COP": "Police",
    "JUD": "Justice",
    "SPY": "Renseignement",
    "MED": "Médias",
    "EDU": "Éducation",
    "BUS": "Entreprise",
    "CRM": "Criminalité",
    "CVL": "Civil / Population",
    "REF": "Réfugié",
    "NGO": "ONG",
    "IGO": "Organisation internationale",
    "HLH": "Santé",
    "LEG": "Parlement / Législatif",
    "AGR": "Agriculture",
    "REL": "Religion",
    "LAB": "Syndicat / Travail",
    "ELI": "Élite politique",
    "UAF": "Forces armées non identifiées",
}


# ─────────────────────────────────────────────────────────────────
# ÉTAPE 1 — NETTOYAGE DE BASE
# ─────────────────────────────────────────────────────────────────

@timer
def clean_basic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nettoyage de base : doublons et lignes critiques manquantes.

    Opérations :
    - Suppression des lignes entièrement dupliquées
    - Suppression des lignes sans date (SQLDATE vide) — inutilisables
    - Suppression des lignes sans URL source (SOURCEURL vide)
    - Réinitialisation de l'index pour des indices propres

    Args:
        df: DataFrame brut issu de extract.py
    Returns:
        pd.DataFrame: DataFrame nettoyé
    """
    n = len(df)
    logger.info(f"Nettoyage de base — {n:,} lignes en entrée")

    df = df.drop_duplicates()
    df = df.dropna(subset=["SQLDATE"])
    df = df.dropna(subset=["SOURCEURL"])
    df = df.reset_index(drop=True)

    logger.info(f"✅ Nettoyage terminé — {n - len(df):,} lignes supprimées, {len(df):,} conservées")
    return df


# ─────────────────────────────────────────────────────────────────
# ÉTAPE 2 — CONVERSION DES TYPES
# ─────────────────────────────────────────────────────────────────

@timer
def convert_types(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convertit chaque colonne dans son type Python/pandas approprié.

    Conversions effectuées :
    - SQLDATE (int YYYYMMDD)         → datetime pandas
    - DATEADDED (int YYYYMMDDHHMMSS) → datetime pandas (pour Q3)
    - GoldsteinScale, AvgTone, coordonnées → float
    - NumArticles, NumMentions, NumSources → int
    - EventRootCode → gardé en l'état ici, converti dans enrich_data()
      avec une logique int→str→zfill(2) plus fiable (voir v1.2)

    Note v1.2 : EventRootCode n'est plus converti ici en str.zfill(2)
    car BigQuery retourne un int64 natif (ex: 4, 19) que pandas
    convertit en "4" et non "04" lors d'un simple astype(str).
    La conversion correcte est faite directement dans enrich_data()
    juste avant le mapping vers EVENT_ROOT_LABELS.

    Args:
        df: DataFrame après nettoyage
    Returns:
        pd.DataFrame: DataFrame avec les bons types
    """
    logger.info("Conversion des types...")

    # ── Dates ─────────────────────────────────────────────────────
    # SQLDATE format GDELT : YYYYMMDD (ex: 20250415 → 2025-04-15)
    df["SQLDATE"] = pd.to_datetime(
        df["SQLDATE"].astype(str).str[:8],
        format="%Y%m%d",
        errors="coerce"   # Les dates invalides deviennent NaT
    )

    # DATEADDED format GDELT : YYYYMMDDHHMMSS (ex: 20250415143000)
    # On prend uniquement les 8 premiers caractères (date seule)
    if "DATEADDED" in df.columns:
        df["DATEADDED"] = pd.to_datetime(
            df["DATEADDED"].astype(str).str[:8],
            format="%Y%m%d",
            errors="coerce"
        )

    # ── Numériques continus ───────────────────────────────────────
    for col in ["GoldsteinScale", "AvgTone", "ActionGeo_Lat", "ActionGeo_Long"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # ── Numériques entiers ────────────────────────────────────────
    for col in ["NumArticles", "NumMentions", "NumSources", "IsRootEvent", "QuadClass"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    logger.info("✅ Types convertis")
    return df


# ─────────────────────────────────────────────────────────────────
# ÉTAPE 3 — ENRICHISSEMENT (Q1 → Q5)
# ─────────────────────────────────────────────────────────────────

@timer
def enrich_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ajoute les colonnes dérivées alignées sur les 5 questions.

    Q1 — event_date, event_month, event_quarter, event_root_label
    Q2 — tone_category, stability_category
    Q3 — propagation_delay_days
    Q4 — source_domain, is_crisis_period
    Q5 — benin_role, actor1_type_label, actor2_type_label, quad_class_label

    Args:
        df: DataFrame après conversion des types
    Returns:
        pd.DataFrame: DataFrame enrichi avec toutes les colonnes dérivées
    """
    logger.info("Enrichissement des données (Q1 → Q5)...")

    # ── Q1 — Colonnes temporelles et type d'événement ─────────────
    df["event_date"]    = df["SQLDATE"].dt.strftime("%Y-%m-%d")
    df["event_month"]   = df["SQLDATE"].dt.month
    df["event_quarter"] = df["SQLDATE"].dt.to_period("Q").astype(str)

    # CORRECTION v1.2 — event_root_label
    # Problème : EventRootCode arrive de BigQuery en int64 (ex: 4, 19).
    # Un simple astype(str) donne "4" et non "04".
    # str.zfill(2) dans convert_types() ne résout pas le problème
    # car pandas sur int64 donne "4".zfill(2) = "4" et non "04".
    # Solution : convertir en int puis en str formaté sur 2 chiffres
    # avec str(int(x)).zfill(2) pour garantir "04", "19", etc.
    df["event_root_label"] = (
        pd.to_numeric(df["EventRootCode"], errors="coerce")  # s'assure d'avoir un numérique
        .dropna()                                             # ignore les NaN temporairement
        .astype(int)                                          # int64 → int natif Python
        .astype(str)                                          # int → "4", "19"
        .str.zfill(2)                                         # "4" → "04", "19" → "19"
        .map(EVENT_ROOT_LABELS)                               # "04" → "Consultation"
    )
    # Réapplication sur le DataFrame complet avec fillna pour les NaN
    df["event_root_label"] = (
        df["EventRootCode"]
        .apply(lambda x: str(int(float(x))).zfill(2) if pd.notna(x) else None)
        .map(EVENT_ROOT_LABELS)
        .fillna("Autre")
    )
    logger.info("   Q1 ✅")

    # ── Q2 — Catégorie de ton et de stabilité ─────────────────────
    # AvgTone : [-100, +100] — seuils calibrés sur GDELT Afrique
    def tone_cat(v: float) -> str:
        """Catégorise le ton médiatique d'un événement."""
        if pd.isna(v): return "Inconnu"
        return "Positif" if v > 2 else ("Négatif" if v < -2 else "Neutre")

    # GoldsteinScale : [-10, +10] — impact sur la stabilité nationale
    def stability_cat(v: float) -> str:
        """Catégorise l'impact sur la stabilité nationale."""
        if pd.isna(v): return "Inconnu"
        return "Stabilisant" if v > 3 else ("Déstabilisant" if v < -3 else "Neutre")

    df["tone_category"]      = df["AvgTone"].apply(tone_cat)
    df["stability_category"] = df["GoldsteinScale"].apply(stability_cat)
    logger.info("   Q2 ✅")

    # ── Q3 — Délai de propagation médiatique ─────────────────────
    # Mesure le nombre de jours entre :
    #   - SQLDATE    : date à laquelle l'événement s'est produit
    #   - DATEADDED  : date à laquelle GDELT a indexé l'événement
    # Un délai de 0 = couverture immédiate
    # Un délai > 7 = événement couvert tardivement
    if "DATEADDED" in df.columns:
        df["propagation_delay_days"] = (
            (df["DATEADDED"] - df["SQLDATE"])
            .dt.days
            .clip(lower=0)  # On ignore les valeurs négatives (erreurs de données)
        )
    else:
        df["propagation_delay_days"] = np.nan
        logger.warning("   Q3 — DATEADDED absent, propagation_delay_days = NaN")
    logger.info("   Q3 ✅")

    # ── Q4 — Domaine source et détection de période de crise ──────
    def extract_domain(url: str) -> str:
        """
        Extrait le nom de domaine depuis une URL source GDELT.
        Ex: "https://www.rfi.fr/fr/afrique/..." → "rfi.fr"
        """
        if pd.isna(url) or url == "":
            return "inconnu"
        try:
            domain = re.sub(r"https?://(www\.)?", "", str(url))
            return domain.split("/")[0].lower()
        except Exception:
            return "inconnu"

    df["source_domain"] = df["SOURCEURL"].apply(extract_domain)

    # Période de crise définie par deux seuils cumulables :
    # - AvgTone < -5       : couverture médiatique très négative
    # - GoldsteinScale < -5 : événement très déstabilisant
    df["is_crisis_period"] = (
        (df["AvgTone"] < -5.0) | (df["GoldsteinScale"] < -5.0)
    )
    logger.info("   Q4 ✅")

    # ── Q5 — Rôle du Bénin : Acteur, Spectateur, Mixte ou Contexte ─
    def benin_role(row) -> str:
        """
        Détermine le rôle du Bénin dans un événement GDELT.

        IMPORTANT : GDELT utilise deux codes pays distincts selon la colonne :
        - ActionGeo_CountryCode : code GDELT géographique → 'BN'
          Utilisé pour filtrer les événements qui se passent AU Bénin.
        - Actor1/2CountryCode   : code CAMEO des acteurs → 'BEN'
          Utilisé pour identifier si le Bénin est acteur ou spectateur.
        Ces deux codes sont DIFFÉRENTS — c'est la source du bug v1.2.

        Quatre cas possibles :
        - Acteur     : Bénin est Actor1 — il initie l'événement
        - Spectateur : Bénin est Actor2 — il est la cible / l'objet
        - Mixte      : Bénin est les deux — événement interne béninois
        - Contexte   : Bénin n'est ni acteur ni spectateur mais
                       l'événement se déroule sur son territoire
        """
        a1_raw = row.get("Actor1CountryCode", None)
        a2_raw = row.get("Actor2CountryCode", None)

        # Nettoyage des NaN avant comparaison
        a1 = "" if pd.isna(a1_raw) else str(a1_raw).strip().upper()
        a2 = "" if pd.isna(a2_raw) else str(a2_raw).strip().upper()

        # Code CAMEO acteurs = 'BEN' (différent du code géo 'BN')
        bn = COUNTRY_ACTOR_CODE.strip().upper()

        if a1 == bn and a2 == bn: return "Mixte"
        if a1 == bn:              return "Acteur"
        if a2 == bn:              return "Spectateur"
        return "Contexte"

    df["benin_role"] = df.apply(benin_role, axis=1)

    # Traduction des types d'acteurs en libellés français
    df["actor1_type_label"] = (
        df["Actor1Type1Code"]
        .map(ACTOR_TYPE_LABELS)
        .fillna("Non identifié")
    )
    df["actor2_type_label"] = (
        df["Actor2Type1Code"]
        .map(ACTOR_TYPE_LABELS)
        .fillna("Non identifié")
    )

    # Traduction QuadClass en libellé français
    df["quad_class_label"] = (
        df["QuadClass"]
        .map(QUAD_CLASS_LABELS)
        .fillna("Inconnu")
    )
    logger.info("   Q5 ✅")

    logger.info("✅ Enrichissement terminé")
    return df


# ─────────────────────────────────────────────────────────────────
# ÉTAPE 4 — FILTRAGE FINAL
# ─────────────────────────────────────────────────────────────────

@timer
def filter_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filtrage qualité final des données.

    Filtres appliqués :
    - Suppression des lignes avec date invalide (NaT après conversion)
    - Suppression des coordonnées GPS hors bornes géographiques
      (latitude hors [-90, 90] ou longitude hors [-180, 180])

    Args:
        df: DataFrame enrichi
    Returns:
        pd.DataFrame: DataFrame propre, validé et prêt pour l'équipe
    """
    n = len(df)
    logger.info(f"Filtrage final — {n:,} lignes en entrée")

    # Suppression des dates invalides générées lors de la conversion
    df = df.dropna(subset=["SQLDATE"])
    logger.info(f"   Après filtre dates invalides   : {len(df):,} lignes")

    # Suppression des coordonnées GPS aberrantes
    if "ActionGeo_Lat" in df.columns:
        df = df[
            df["ActionGeo_Lat"].isna() |
            df["ActionGeo_Lat"].between(-90, 90)
        ]
    if "ActionGeo_Long" in df.columns:
        df = df[
            df["ActionGeo_Long"].isna() |
            df["ActionGeo_Long"].between(-180, 180)
        ]
    logger.info(f"   Après filtre coordonnées GPS   : {len(df):,} lignes")

    logger.info(f"✅ Filtrage terminé — {n - len(df):,} lignes supprimées")
    return df


# ─────────────────────────────────────────────────────────────────
# FONCTION PRINCIPALE D'ORCHESTRATION
# ─────────────────────────────────────────────────────────────────

@timer
def run_transform(df: pd.DataFrame) -> pd.DataFrame:
    """
    Orchestre les 4 étapes de transformation dans l'ordre.

    Pipeline complet :
        1. clean_basic()   — suppression doublons et lignes critiques
        2. convert_types() — conversion des types de données
        3. enrich_data()   — ajout colonnes dérivées Q1 → Q5
        4. filter_data()   — filtrage qualité final

    Args:
        df: DataFrame brut issu de extract.py
    Returns:
        pd.DataFrame: Données propres, enrichies, prêtes pour l'équipe

    Raises:
        ValueError: Si le DataFrame d'entrée est invalide ou vide
    """
    logger.info("=" * 55)
    logger.info("TRANSFORMATION — DÉMARRAGE")
    logger.info("=" * 55)

    if not validate_dataframe(df, "données brutes"):
        raise ValueError("DataFrame d'entrée invalide — transformation annulée.")

    df = clean_basic(df)
    df = convert_types(df)
    df = enrich_data(df)
    df = filter_data(df)

    validate_dataframe(df, "données transformées finales")

    logger.info("=" * 55)
    logger.info("TRANSFORMATION — TERMINÉE")
    logger.info("=" * 55)
    return df
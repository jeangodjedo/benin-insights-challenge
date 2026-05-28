"""
BeninSentinel — Streamer GDELT incrémental.

Cette couche est responsable de l'alimentation continue du système en
données fraîches GDELT. Elle expose une seule méthode publique :

    streamer.fetch_window(days_back=45) -> pd.DataFrame

qui retourne un DataFrame contenant les événements GDELT du Bénin sur la
fenêtre demandée (typiquement les 30 à 45 derniers jours, suffisant pour
calculer la référence comportementale du score BeninSentinel).

Conception adaptée au contexte hackathon → production :

1. **Mode `live`** : interroge BigQuery (gdelt-bq.gdeltv2.events) sur la
   fenêtre récente, applique le même nettoyage que `pipeline.transform`,
   et retourne un DataFrame prêt pour `run_sentinel()`. Recommandé en
   production sur un serveur disposant des credentials Google Cloud.

2. **Mode `local`** : utilise le snapshot CSV statique
   `data/processed/benin_gdelt_clean.csv` issu du pipeline ETL. Utile
   pour la démo, les tests, et le développement sans réseau.

Le mode est choisi automatiquement selon la disponibilité de
`google-cloud-bigquery` et des credentials. Bascule transparente.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd


class SentinelStreamer:
    """
    Récupération de données GDELT pour le calcul du score BeninSentinel.

    Cette classe encapsule la complexité du chargement (BigQuery réel vs
    snapshot local) pour que le reste du système (AlertEngine, Notifier)
    n'ait pas à s'en soucier.
    """

    def __init__(self, local_csv_path: Optional[Path] = None,
                 prefer_local: bool = False):
        """
        Args:
            local_csv_path : chemin du CSV nettoyé (snapshot du pipeline ETL).
                             Si None : data/processed/benin_gdelt_clean.csv.
            prefer_local   : si True, utilise toujours le CSV local même si
                             BigQuery est dispo (utile pour tests reproductibles).
        """
        if local_csv_path is None:
            project_root = Path(__file__).resolve().parents[2]
            local_csv_path = project_root / "data" / "processed" / "benin_gdelt_clean.csv"
        self.local_csv_path = Path(local_csv_path)
        self.prefer_local   = prefer_local

    # ─────────────────────────────────────────────────────────────
    # API PUBLIQUE
    # ─────────────────────────────────────────────────────────────

    def fetch_window(self, days_back: int = 45,
                     reference_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Retourne les événements GDELT du Bénin sur les N derniers jours.

        Args:
            days_back      : profondeur de la fenêtre (jours).
            reference_date : date de fin de fenêtre (par défaut : aujourd'hui).

        Returns:
            pd.DataFrame nettoyé, prêt pour `pipeline.sentinel.run_sentinel()`.
        """
        if not self.prefer_local and self._bigquery_available():
            try:
                return self._fetch_from_bigquery(days_back, reference_date)
            except Exception:
                # Fallback transparent vers le CSV local en cas d'échec
                return self._fetch_from_local(days_back, reference_date)
        return self._fetch_from_local(days_back, reference_date)

    # ─────────────────────────────────────────────────────────────
    # IMPLÉMENTATIONS INTERNES
    # ─────────────────────────────────────────────────────────────

    def _bigquery_available(self) -> bool:
        """Détecte la disponibilité de BigQuery (lib + credentials)."""
        try:
            import google.cloud.bigquery  # noqa: F401
        except ImportError:
            return False
        # Credentials disponibles ?
        # Variable d'env GOOGLE_APPLICATION_CREDENTIALS ou ADC configurées.
        return bool(os.getenv("GCP_PROJECT_ID"))

    def _fetch_from_local(self, days_back: int,
                          reference_date: Optional[datetime]) -> pd.DataFrame:
        """
        Charger le CSV local et filtrer sur la fenêtre demandée.

        Mode "snapshot" — utilisé en démo et en développement.
        """
        if not self.local_csv_path.exists():
            raise FileNotFoundError(
                f"Snapshot local introuvable : {self.local_csv_path}. "
                "Lancer d'abord le pipeline ETL : "
                "`python -m pipeline.run_pipeline --mode sample`."
            )

        df = pd.read_csv(self.local_csv_path, low_memory=False)
        df["SQLDATE"] = pd.to_datetime(df["SQLDATE"], errors="coerce")
        df = df.dropna(subset=["SQLDATE"])

        if reference_date is None:
            reference_date = df["SQLDATE"].max().to_pydatetime()

        start = pd.Timestamp(reference_date) - pd.Timedelta(days=days_back)
        return df[df["SQLDATE"] >= start].copy()

    def _fetch_from_bigquery(self, days_back: int,
                             reference_date: Optional[datetime]) -> pd.DataFrame:
        """
        Interroger BigQuery sur la fenêtre récente avec le filtre Bénin
        complet (mêmes règles que pipeline.extract).

        Utilise le client `google.cloud.bigquery` et applique en post-traitement
        le nettoyage du module transform (clean_basic + convert_types +
        enrich_data + filter_data).
        """
        from google.cloud import bigquery

        from pipeline.config    import GCP_PROJECT_ID
        from pipeline.transform import run_transform

        if reference_date is None:
            reference_date = datetime.utcnow()
        start = reference_date - timedelta(days=days_back)

        # Filtre date au format YYYYMMDD attendu par GDELT
        start_int = int(start.strftime("%Y%m%d"))
        end_int   = int(reference_date.strftime("%Y%m%d"))

        # Filtre identique au pipeline principal — code BN géographique +
        # codes BEN acteurs + filtre anti-bruit Benin City
        query = f"""
        SELECT
            GLOBALEVENTID, SQLDATE, DATEADDED, MonthYear, Year,
            Actor1Name, Actor1Code, Actor1CountryCode, Actor1Type1Code,
            Actor2Name, Actor2Code, Actor2CountryCode, Actor2Type1Code,
            IsRootEvent, EventCode, EventBaseCode, EventRootCode, QuadClass,
            GoldsteinScale, AvgTone, NumMentions, NumSources, NumArticles,
            ActionGeo_FullName, ActionGeo_CountryCode, ActionGeo_Type,
            ActionGeo_ADM1Code, ActionGeo_Lat, ActionGeo_Long, SOURCEURL
        FROM `gdelt-bq.gdeltv2.events`
        WHERE
            SQLDATE BETWEEN {start_int} AND {end_int}
            AND (
                Actor1CountryCode = 'BEN'
                OR Actor2CountryCode = 'BEN'
                OR (
                    ActionGeo_CountryCode = 'BN'
                    AND LOWER(ActionGeo_FullName) NOT LIKE '%nigeria%'
                    AND LOWER(ActionGeo_FullName) NOT LIKE '%edo%'
                    AND LOWER(ActionGeo_FullName) NOT LIKE '%benin city%'
                )
            )
        """

        client = bigquery.Client(project=GCP_PROJECT_ID)
        df_raw = client.query(query).to_dataframe()
        if df_raw.empty:
            return df_raw
        return run_transform(df_raw)

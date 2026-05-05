# Bénin Insights Challenge 2026

Projet réalisé dans le cadre du hackathon **iSHEERO × DataCamp Donates — Bénin Insights Challenge 2026**.

## Objectif du projet

Extraire, nettoyer, organiser et analyser les données **GDELT** liées au Bénin sur l'année 2025
afin de produire des insights utiles pour :

- les journalistes ;
- les chercheurs ;
- les décideurs publics.

Le projet vise à transformer des données mondiales en connaissances locales exploitables.

## Source de données

Les données proviennent de **GDELT — Global Database of Events, Language and Tone**.

```text
Google BigQuery : gdelt-bq.gdeltv2.events
```

GDELT fournit des informations sur :

- les événements géopolitiques (conflits, diplomatie, coopération) ;
- les acteurs impliqués (gouvernements, ONG, médias, militaires...) ;
- les lieux associés aux événements ;
- le volume de couverture médiatique (articles, mentions, sources) ;
- le ton moyen des articles (positif, neutre, négatif).

## Questions analytiques

Les cinq questions prioritaires qui guident l'ensemble du pipeline :

| # | Question | Colonnes GDELT mobilisées |
|---|---|---|
| Q1 | Quand le monde parle-t-il du Bénin, et quels événements provoquent les pics de couverture ? | SQLDATE, NumArticles, NumMentions, EventRootCode |
| Q2 | Le ton médiatique mondial sur le Bénin est-il positif, neutre ou négatif, et comment évolue-t-il ? | AvgTone, GoldsteinScale |
| Q3 | Combien de jours faut-il pour que la couverture médiatique atteigne son pic après un événement ? | SQLDATE, DATEADDED |
| Q4 | Les sources qui couvrent le Bénin en période de crise sont-elles différentes de celles en période normale ? | SOURCEURL, NumArticles, NumSources |
| Q5 | Le Bénin est-il acteur ou spectateur de sa propre histoire internationale ? | Actor1CountryCode, Actor2CountryCode, IsRootEvent |

## Structure du dépôt

```text
benin-insights-challenge/
│
├── data/
│   ├── raw/          # Données brutes extraites de BigQuery (non versionnées)
│   ├── processed/    # Données nettoyées et enrichies (non versionnées)
│   └── sample/       # Échantillons de test 5 000 lignes (non versionnés)
│
├── pipeline/      # Pipeline ETL GDELT (Data Engineer)
│   ├── __init__.py
│   ├── config.py        # Configuration centralisée
│   ├── extract.py       # Extraction BigQuery
│   ├── transform.py     # Nettoyage et enrichissement
│   ├── load.py          # Sauvegarde CSV / Parquet / JSON
│   ├── run_pipeline.py  # Orchestrateur principal
│   └── utils.py         # Utilitaires transversaux
│
├── tests/
│   ├── test_extract.py    # Tests sur build_query() — aucune connexion BigQuery requise
│   ├── test_transform.py  # Tests sur clean_basic(), convert_types(), enrich_data(), filter_data()
│   └── test_load.py       # Tests sur save_to_csv(), save_to_parquet(), save_to_json(), generate_quality_report()
│
├── notebooks/     # Analyses exploratoires (Data Analyst / Data Scientist)
├── models/        # Modèles de machine learning (ML Engineer)
├── dashboard/     # Dashboard interactif Streamlit (Data Analyst)
│
├── .env.example   # Template de configuration (à copier en .env)
├── .gitignore
├── LICENSE
├── README.md
└── requirements.txt
```

## Installation

### 1. Cloner le dépôt

```bash
git clone https://github.com/jeangodjedo/benin-insights-challenge.git
cd benin-insights-challenge
```

### 2. Créer et activer l'environnement virtuel

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement

```bash
cp .env.example .env
```

Ouvrez `.env` et renseignez votre Project ID Google Cloud :

```text
GCP_PROJECT_ID=votre-project-id
```

Votre Project ID est visible sur [console.cloud.google.com](https://console.cloud.google.com)
en haut à gauche dans la barre de navigation.

### 5. Authentification Google Cloud (une seule fois)

```bash
gcloud auth application-default login
```

Cette commande ouvre le navigateur. Connectez-vous avec le compte Google
qui a accès au projet BigQuery.

## Utilisation du pipeline

### Mode test — 5 000 lignes (à faire en premier)

```bash
python/python3 -m pipeline.run_pipeline --mode sample
```

Valide que le pipeline fonctionne sans consommer de quota BigQuery significatif.
Durée : moins d'une minute.

### Mode production — toutes les données disponibles

```bash
python/python3 -m pipeline.run_pipeline --mode full
```

Récupère **TOUS** les événements GDELT du Bénin pour 2025, sans limite de lignes.
Durée : plusieurs minutes selon le volume.

### Fichiers produits (dans `data/clean/`)

| Fichier | Format | Destinataire |
|---|---|---|
| `benin_gdelt_clean.csv` | CSV UTF-8 | Data Analyst (Tableau, Power BI, Excel) |
| `benin_gdelt_clean.parquet` | Parquet (snappy) | ML Engineer (scikit-learn, HuggingFace) |
| `benin_gdelt_clean.json` | JSON records | Data Scientist (notebooks, API) |
| `quality_report.json` | JSON | Toute l'équipe |

## Tests unitaires

Les tests sont organisés en 3 fichiers distincts, un par module testé :

```text
tests/
├── test_extract.py    # Tests sur build_query() — aucune connexion BigQuery requise
├── test_transform.py  # Tests sur clean_basic(), convert_types(), enrich_data(), filter_data()
└── test_load.py       # Tests sur save_to_csv(), save_to_parquet(), save_to_json(), generate_quality_report()
```

### Lancer tous les tests

```bash
pytest tests/ -v
```

### Lancer un fichier spécifique

```bash
pytest tests/test_extract.py -v
pytest tests/test_transform.py -v
pytest tests/test_load.py -v
```

### Lancer avec couverture de code

```bash
pytest tests/ -v --cov=pipeline --cov-report=term-missing
```

### Ce qui est testé

| Fichier | Fonctions testées | Cas couverts |
|---|---|---|
| `test_extract.py` | `build_query()` | LIMIT sample vs full, codes pays BN vs BEN, ordre des filtres SQL, filtre anti-bruit Benin City |
| `test_transform.py` | `clean_basic()`, `convert_types()`, `enrich_data()`, `filter_data()` | Doublons, NaN, types datetime, benin_role Q5, event_root_label Q1, tone_category Q2, propagation_delay Q3, source_domain Q4 |
| `test_load.py` | `save_to_csv()`, `save_to_parquet()`, `save_to_json()`, `generate_quality_report()` | Création fichiers, intégrité des données, encodage UTF-8, rapport de qualité Q1→Q5 |
## Notes techniques importantes

### Codes pays GDELT

GDELT utilise **deux systèmes de codes pays différents** selon la colonne :

| Colonne | Format | Code Bénin | Usage |
|---|---|---|---|
| `ActionGeo_CountryCode` | GDELT géographique (2 lettres) | `BN` | Événements qui se passent au Bénin |
| `Actor1/2CountryCode` | CAMEO (3 lettres) | `BEN` | Bénin comme acteur ou cible |

Confondre ces deux codes est une source fréquente d'erreur dans GDELT.

### Filtre anti-bruit Benin City (Nigeria)

GDELT tague parfois des événements de **Benin City** (Nigeria, État d'Edo)
avec `ActionGeo_CountryCode = 'BN'`. Le pipeline exclut ces faux positifs
en vérifiant que le nom du lieu ne contient pas `nigeria`, `edo` ou `benin city`.

### Quota BigQuery

Le quota gratuit est de **1 TB de données scannées par mois**.
Toujours tester en mode `sample` avant de lancer le mode `full`.
Ne jamais utiliser `SELECT *` — sélectionner uniquement les colonnes nécessaires.

## Rôles dans l'équipe

| Profil | Responsabilités |
|---|---|
| **Data Engineer** | Pipeline ETL, extraction BigQuery, nettoyage, structuration |
| **Data Analyst** | Visualisations, dashboard Streamlit, analyse descriptive |
| **ML Engineer** | Modèles ML, analyse de sentiment, clustering |
| **Data Scientist** | Questions analytiques, interprétation, rapport final, storytelling |

## Utilisation de l'IA

L'IA est utilisée comme outil d'assistance pour structurer le dépôt, concevoir le pipeline,
améliorer la documentation et guider les choix techniques.
Les décisions finales, validations, analyses et interprétations restent réalisées par l'équipe.
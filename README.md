<p align="center">
  <img src="assets/logo_iroko_sentinel.png" alt="IROKO Analytics — BeninSentinel" width="220">
</p>

# Bénin Insights Challenge 2026 — IROKO Analytics

Projet finaliste réalisé par **IROKO Analytics** (Équipe 7) dans le cadre du hackathon **iSHEERO × DataCamp Donates — Bénin Insights Challenge 2026**.

> *« Un outil n'est pas excellent parce qu'il prédit. Il est excellent parce qu'il donne du temps. »*

---

## Dashboard interactif en ligne

> ### **[https://irokoanalytics.streamlit.app](https://irokoanalytics.streamlit.app)**
>
> Application publique accessible sans installation, conçue pour être **lisible et exploitable en quelques secondes par des décideurs publics non-techniques**. Trois pages complémentaires :
>
> 1. **Tableau de bord stratégique** — aperçu exécutif + six questions clés en français naturel + synthèse stratégique avec cinq actions prioritaires
> 2. **Anticiper l'impact médiatique d'un événement** — outil interactif à trois modes (scénarios prédéfinis · mode guidé · mode avancé) pour évaluer en temps réel l'impact médiatique anticipé d'un événement
> 3. **BeninSentinel** — système d'alerte précoce des crises (cf. ci-dessous)

---

## BeninSentinel — produit phare de la finale

> **BeninSentinel** est un système de veille et d'intelligence territoriale qui surveille en continu les médias mondiaux, détecte les signaux précurseurs de tensions au Bénin et génère des alertes graduées pour les décideurs publics — afin de passer de la **gestion réactive des crises à leur prévention proactive**.
>
> **Cible** : Présidence du Bénin, Ministère de l'Intérieur, préfets, ANSSI-Bénin, ONG de paix.
> **Aligné** : Programme d'Action du Gouvernement 2021-2026 — piliers Gouvernance, Numérique et Bien-être social.
>
> **Validation empirique sur les 4 crises majeures du Bénin en 2025** :
>
> | Date | Événement | Score | Alerte | Détection |
> |---|---|---:|:---:|:---:|
> | 24 avril 2025 | Attaque jihadiste — 54 soldats béninois tués | 0,686 | **ORANGE** | **J-4** |
> | 5 novembre 2025 | Pic de tensions sécuritaires | 0,640 | ORANGE | J-1 |
> | 6 juin 2025 | Crise diplomatique + violence | 0,592 | JAUNE | J-0 |
> | 7 décembre 2025 | Tentative de coup d'État déjouée | 0,560 | JAUNE | J-0 |
>
> **Taux de détection : 100 %** sur les crises majeures vérifiées · **zéro faux positif ORANGE** sur l'année.
>
> Documentation : [`reports/BENIN_SENTINEL_FOUNDATIONS.md`](reports/BENIN_SENTINEL_FOUNDATIONS.md) · [`reports/BENIN_SENTINEL_VALIDATION.md`](reports/BENIN_SENTINEL_VALIDATION.md) · [`reports/PITCH_DECK_FINALE.md`](reports/PITCH_DECK_FINALE.md) · [`reports/REALTIME_ARCHITECTURE.md`](reports/REALTIME_ARCHITECTURE.md)
> Code : [`pipeline/sentinel.py`](pipeline/sentinel.py) · Module temps réel : [`pipeline/realtime/`](pipeline/realtime/) · Interface : [`dashboard/pages/3_BeninSentinel.py`](dashboard/pages/3_BeninSentinel.py) · Tests : [`tests/test_sentinel.py`](tests/test_sentinel.py) + [`tests/test_realtime.py`](tests/test_realtime.py)

### Du prototype démontré à l'alerte opérationnelle continue

BeninSentinel est désormais accompagné d'un **système d'alerte temps réel
production-ready** ([`pipeline/realtime/`](pipeline/realtime/)) qui permet de :

- Surveiller en continu les données GDELT à fréquence configurable (par défaut 60 min)
- Détecter automatiquement les transitions de niveau d'alerte (Vert → Jaune → Orange → Rouge)
- Notifier les bons destinataires via les bons canaux (email SMTP, webhook HTTP, console)
- Tracer toutes les actions dans une base SQLite auditable (états, transitions, notifications)
- Tourner en mode `--once` (cron), `--loop` (boucle), Docker ou systemd

Lancement local en mode démo :
```bash
SENTINEL_PREFER_LOCAL=1 SENTINEL_SIMULATE=1 python -m scheduler.run_realtime --once
```

Page de surveillance opérationnelle dans le dashboard : **« Surveillance temps réel »**.

---

## Objectif du projet

Transformer les données mondiales **GDELT** en **intelligence territoriale exploitable** pour les pouvoirs publics béninois et leurs partenaires (journalistes, chercheurs, ONG de paix), avec un objectif clair : **donner du temps aux décideurs** face aux crises sécuritaires, sociales et politiques.

Le projet adresse un problème précis et mesurable : aucun outil n'agrège, n'analyse et n'interprète aujourd'hui en continu les signaux faibles des médias mondiaux pour les décideurs béninois. Cette absence entretient un **déficit narratif de 20 points** (44 % d'articles négatifs en 2025 contre 24 % positifs) et entrave la mise en œuvre du PAG 2021-2026.

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

Chaque question fait l'objet d'une analyse causale complète **Constat → Mécanisme → Conséquence chiffrée → Action décideur prescriptive**, accessible dans le dashboard et dans le notebook. Un sixième axe bonus (« angle médiatique caché ») complète l'analyse.

## Cinq insights majeurs documentés

1. **Déficit narratif structurel de 20 points** — 44 % d'articles négatifs contre 24 % positifs alors que la stabilité géopolitique réelle (score Goldstein moyen +0,68) est positive. Le Bénin est représenté 1,8 fois plus négativement que sa réalité.
2. **Vulnérabilité narrative sous-estimée** — 4 des 5 plus grandes sources sur le Bénin sont nigérianes. Mais GDELT crawle majoritairement les médias anglophones et le Nigeria publie en anglais quand le Bénin publie en français : le déficit de souveraineté narrative est donc **encore pire que ne le montrent nos chiffres** — un biais médiatique amplifié par un biais linguistique.
3. **Anticipation validée à J-4** — sur les quatre crises majeures du Bénin en 2025, BeninSentinel les détecte toutes ; l'attaque jihadiste du 24 avril (54 soldats tués) a été précédée d'une alerte JAUNE persistante quatre jours à l'avance.
4. **Agenda médiatique caché** — plus de 3 000 événements graves (Goldstein ≤ −5) sont passés sous le radar médiatique mondial en 2025, dont 73 % sur le territoire béninois. Ce sont les signaux faibles qui préparent les prochaines crises.
5. **Souveraineté narrative déficitaire** — le Bénin est passif (Contexte ou Spectateur) dans 68 % des événements mondiaux qui le concernent contre 31 % seulement où il est Acteur. À reconquérir par des initiatives diplomatiques signature.

## Cible et impact stratégique

Le projet est explicitement conçu pour les **décideurs publics béninois** : Présidence de la République, Cabinet du Ministre de l'Intérieur, préfets des départements frontaliers (Alibori, Atacora), ANSSI-Bénin, ABC (Agence Béninoise de Communication), ONG de paix et organisations partenaires.

Il s'inscrit dans les trois piliers du **Programme d'Action du Gouvernement 2021-2026** :

| Pilier PAG | Apport du projet |
|---|---|
| Gouvernance, État de droit | Outil d'aide à la décision transparent — seuils et signaux auditables |
| Transformation numérique | Souveraineté analytique sur la donnée publique mondiale (GDELT) |
| Bien-être social | Anticipation des crises = vies protégées, communication proactive |

Cinq actions stratégiques prioritaires sont déclinées dans le dashboard (section finale) et dans le notebook :

1. **Déploiement de BeninSentinel en production** (3-6 mois · ANSSI-Bénin)
2. **Kit de communication d'urgence** (3 mois · ABC + Présidence) — diffusion H+1
3. **Programme d'amplification narrative positive** (12 mois · Présidence + Affaires Étrangères) — cible ratio négatif/positif sous 1,3:1 en 18 mois
4. **Partenariats éditoriaux régionaux** (6-12 mois · Diplomatie publique)
5. **Initiatives diplomatiques signature** (24 mois) — ratio Acteur ≥ 45 % d'ici 2027

## Structure du dépôt

```text
benin-insights-challenge/
│
├── data/
│   ├── raw/          # Données brutes extraites de BigQuery (non versionnées)
│   ├── processed/    # Données nettoyées et enrichies (non versionnées)
│   └── sample/       # Échantillons de test 5 000 lignes (non versionnés)
│
├── pipeline/      # Pipeline ETL GDELT + module BeninSentinel
│   ├── __init__.py
│   ├── config.py        # Configuration centralisée
│   ├── extract.py       # Extraction BigQuery
│   ├── transform.py     # Nettoyage et enrichissement
│   ├── load.py          # Sauvegarde CSV / Parquet / JSON
│   ├── run_pipeline.py  # Orchestrateur principal
│   ├── sentinel.py      # Module BeninSentinel — détection des crises
│   └── utils.py         # Utilitaires transversaux
│
├── tests/        # 96 tests unitaires (100 % passent)
│   ├── test_extract.py    # Tests sur build_query()
│   ├── test_transform.py  # Tests sur clean_basic(), convert_types(), enrich_data(), filter_data()
│   ├── test_load.py       # Tests sur save_to_csv(), save_to_parquet(), save_to_json(), generate_quality_report()
│   └── test_sentinel.py   # Tests sur build_daily_series(), compute_weak_signals(), compute_risk_score()
│
├── notebooks/
│   └── eda_benin_gdelt_2025.ipynb   # Analyses exploratoires + ML + analyses causales
│
├── models/       # Artefacts ML versionnés (Random Forest + encoders + confusion matrix)
│
├── dashboard/
│   ├── app.py                                    # Tableau de bord stratégique principal
│   └── pages/
│       ├── 2_Anticiper_l_impact_mediatique.py    # Outil interactif de prédiction
│       └── 3_BeninSentinel.py                    # Système de veille pour décideurs
│
├── reports/      # Documentation stratégique
│   ├── BENIN_SENTINEL_FOUNDATIONS.md   # Méthodologie rigoureuse de BeninSentinel
│   ├── BENIN_SENTINEL_VALIDATION.md    # Rapport de validation empirique chiffré
│   ├── PITCH_DECK_FINALE.md            # Pitch deck Finale (10 slides + Q&A préparée)
│   └── Resume_Executif_IROKO_Analytics.pdf
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

## Modèle de Machine Learning — Performance

Le notebook entraîne un classifieur **Random Forest** pour prédire le ton médiatique
d'un événement béninois (`Positif` / `Neutre` / `Négatif`) à partir de 9 variables
issues de GDELT (intensité Goldstein, volume d'articles/mentions/sources, mois,
type d'événement CAMEO, rôle du Bénin, etc.).

### Métriques d'évaluation

Évaluation sur un **test set stratifié de 6 301 lignes** (20 % du jeu de données ML),
avec validation croisée 5-fold sur l'ensemble d'entraînement.

| Métrique | Valeur |
|---|---|
| Accuracy (test set) | **0,55** |
| F1 weighted (test set) | **0,55** |
| F1 weighted CV 5-fold | **0,549 ± 0,009** |
| Macro F1 (test set) | **0,54** |

### Performance par classe

| Classe | Précision | Rappel | F1-score | Support |
|---|---|---|---|---|
| Négatif | 0,72 | 0,57 | **0,64** | 2 786 |
| Positif | 0,43 | 0,72 | **0,54** | 1 522 |
| Neutre | 0,51 | 0,40 | **0,45** | 1 993 |

Le modèle est **plus performant sur la classe Négatif** (F1 = 0,64), qui est aussi
la classe majoritaire. La classe Neutre reste la plus difficile à séparer car elle
chevauche les deux extrêmes.

### Variables les plus prédictives (Gini importance)

| Rang | Variable | Importance |
|---|---|---|
| 1 | `GoldsteinScale` (intensité de stabilité) | **27,2 %** |
| 2 | `event_month` (saisonnalité) | **21,7 %** |
| 3 | `event_root_label_enc` (type CAMEO) | **12,9 %** |
| 4 | `QuadClass` (catégorie GDELT) | **12,1 %** |
| 5 | `NumArticles` / `NumMentions` | 6,8 % chacun |

L'intensité Goldstein et la saisonnalité dominent : **le ton dépend davantage de la
nature de l'événement et du moment de l'année que du volume de couverture**.

Matrice de confusion et graphique d'importance des variables :
[`models/confusion_matrix_feature_importance.png`](models/confusion_matrix_feature_importance.png).

### Choix du modèle — justification

Random Forest a été retenu pour cette première version pour quatre raisons :

1. **Robustesse au déséquilibre de classes** via `class_weight="balanced"` (ratio
   Négatif/Neutre/Positif ≈ 44 / 32 / 24 %).
2. **Interprétabilité** : les `feature_importances_` permettent de relier
   directement les prédictions aux variables analytiques (Goldstein, type CAMEO),
   ce qui sert le storytelling auprès des décideurs.
3. **Pas de scaling requis** : le pipeline reste simple et reproductible.
4. **Baseline solide** sans tuning d'hyperparamètres lourd, adapté à la fenêtre
   de 10 jours de la Phase 1.

Un baseline **Logistic Regression** (avec scaling) est également entraîné dans le
notebook à des fins de comparaison. Random Forest le surpasse, ce qui valide
l'hypothèse que les relations entre variables GDELT et ton médiatique sont
non linéaires.

### Pistes d'amélioration (Phase 2)

- Tester **XGBoost** et un **VotingClassifier** RF + GBM.
- Ajouter des features texte issues de `SOURCEURL` (TF-IDF / embeddings).
- Élargir la fenêtre temporelle au-delà de 2025 pour mieux capturer les cycles
  événementiels.

## Équipe — IROKO Analytics

| Profil | Membre | Responsabilités |
|---|---|---|
| 🔧 **Data Engineer** | **GODJEDO Aubrey** | Pipeline ETL, extraction BigQuery, nettoyage, structuration |
| 📊 **Data Analyst** | **GUIDIGBI Randyx Emery Vianney** | Visualisations, dashboard Streamlit, analyse descriptive |
| 🤖 **ML Engineer** | **RANDRIANIRINA Mahenina** | Modèles ML, analyse de sentiment, clustering |
| 🧠 **Data Scientist** | **Pancrace KANHONOU** | Questions analytiques, interprétation, rapport final, storytelling |

## Utilisation de l'IA

L'IA est utilisée comme outil d'assistance pour structurer le dépôt, concevoir le pipeline,
améliorer la documentation et guider les choix techniques.
Les décisions finales, validations, analyses et interprétations restent réalisées par l'équipe.
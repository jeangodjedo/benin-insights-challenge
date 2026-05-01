# Bénin Insights Challenge 2026

Projet réalisé dans le cadre du hackathon **iSHEERO × DataCamp Donates — Bénin Insights Challenge 2026**.

## Objectif du projet

L’objectif est d’extraire, nettoyer, organiser et analyser les données GDELT liées au Bénin sur les 12 derniers mois afin de produire des insights utiles pour :

- les journalistes ;
- les chercheurs ;
- les décideurs publics.

Le projet vise à transformer des données mondiales en connaissances locales exploitables.

## Source de données

Les données utilisées proviennent de **GDELT — Global Database of Events, Language and Tone**.

Source principale :

```text
Google BigQuery : gdelt-bq.gdeltv2.events
```

GDELT fournit des informations sur :

- les événements géopolitiques ;
- les acteurs impliqués ;
- les lieux associés aux événements ;
- le volume de couverture médiatique ;
- le ton moyen des articles.

## Règles importantes d’extraction

Pour préserver le quota BigQuery et éviter les requêtes trop lourdes :

- toujours filtrer d’abord sur `Year` ;
- toujours tester les requêtes sur un petit échantillon ;
- ne pas extraire toutes les colonnes sans besoin clair ;
- documenter les choix de filtrage et de nettoyage.

## Structure du dépôt

```text
benin-insights-challenge/
│
├── data/              # Données du projet
├── notebooks/         # Notebooks d’extraction, nettoyage et analyse
├── models/            # Modèles de machine learning
├── dashboard/         # Dashboard interactif
│
├── README.md
├── requirements.txt
└── .gitignore
```

## Rôles dans l’équipe

- **Data Engineer** : extraction, nettoyage et structuration des données.
- **Data Analyst** : visualisations, dashboard et analyse descriptive.
- **ML Engineer** : première version d’un modèle de machine learning.
- **Data Scientist** : questions analytiques, interprétation des résultats, rapport final et storytelling.

## Pipeline de données prévu

```text
GDELT BigQuery
   ↓
Extraction des événements liés au Bénin
   ↓
Nettoyage des données
   ↓
Structuration des données exploitables
   ↓
Analyse exploratoire
   ↓
Dashboard interactif
   ↓
Modèle de machine learning
   ↓
Insights et recommandations
```

## Questions analytiques envisagées

Les questions qui guident le projet :

**Question 1** — Quand le monde parle-t-il du Benin, et quels evenements provoquent les pics de couverture sur 12 mois ?
Cette question vise a identifier les periodes de forte attention mediatique internationale ainsi que les evenements declencheurs (crises politiques, attaques terroristes, elections, visites diplomatiques, performances economiques, etc.).

**Question 2** — Le ton mediatique mondial sur le Benin est-il positif, neutre ou negatif, et comment evolue-t-il dans le temps ?
L'objectif ici est d'analyser la perception internationale du pays a travers le sentiment mediatique dominant et son evolution selon les contextes.

**Question 3** — Lorsqu'un evenement majeur se produit au Benin, combien de jours faut-il pour que la couverture mediatique mondiale atteigne son pic, puis retombe ?
Cette question cherche a mesurer la vitesse de propagation et la duree de vie mediatique des evenements lies au Benin.

**Question 4** — Les sources mediatiques qui couvrent le Benin lors des crises sont-elles differentes de celles qui le couvrent en periode normale ?
Il s'agit ici d'identifier les medias dominants selon les contextes : presse internationale generaliste, medias africains, agences de presse, medias specialises, etc.

**Question 5** — Le Benin est-il acteur ou spectateur de sa propre histoire internationale ?
Cette question constitue la synthese strategique du projet : elle vise a determiner si le pays influence activement son image internationale ou si celle-ci est principalement faconnagee par des acteurs exterieurs.

## Installation du projet

Créer un environnement virtuel :

```bash
python -m venv venv
```

Activer l’environnement virtuel :

Sur macOS / Linux :

```bash
source venv/bin/activate
```

Sur Windows :

```bash
venv\Scripts\activate
```

Installer les dépendances :

```bash
pip install -r requirements.txt
```

## Lancement du dashboard

Le dashboard sera développé avec Streamlit.

Commande prévue :

```bash
streamlit run dashboard/app.py
```

## Livrables attendus

Le projet doit produire :

- un dépôt GitHub public et organisé ;
- un notebook d’analyse exploratoire avec pipeline GDELT ;
- au moins cinq visualisations commentées ;
- une première version d’un modèle de machine learning ;
- un dashboard interactif accessible en ligne ;
- une vidéo pitch de 3 minutes ;
- un résumé d’une page avec cinq insights clés.

## Utilisation de l’IA

L’IA est utilisée comme outil d’assistance pour :

- structurer le dépôt ;
- aider à la conception du pipeline de données ;
- améliorer la documentation ;
- guider les choix techniques ;
- appuyer la rédaction et la relecture.

Les décisions finales, les validations, les analyses et les interprétations restent réalisées par l’équipe.

## État actuel du projet

Phase actuelle : initialisation du dépôt et préparation du pipeline GDELT.
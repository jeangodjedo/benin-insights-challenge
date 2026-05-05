
# Comment le monde voit le Bénin : ce que révèlent 31 504 événements médiatiques

**Bénin Insights Challenge 2026** — Équipe 7 | iSHEERO x DataCamp Donates
Phase 1 — Sprint Qualification | Mai 2026

---

## Qui sommes-nous ?

Quatre profils, une seule mission : transformer les données mondiales en connaissances locales exploitables pour le Bénin.

- **Data Engineer** — Construction du pipeline d'extraction et de nettoyage des données GDELT (72 tests unitaires, 100 % de réussite).
- **Data Analyst** — Création du dashboard interactif avec 12 visualisations et analyse descriptive approfondie.
- **ML Engineer** — Développement d'un modèle prédictif du ton médiatique (Random Forest, cross-validation F1 5-fold).
- **Data Scientist** — Formulation des questions, interprétation des résultats, rédaction du rapport et storytelling.

## Notre démarche

Nous avons exploité **GDELT** (Global Database of Events, Language and Tone), la plus grande base de données ouverte d'événements géopolitiques au monde. Notre pipeline automatisé a extrait, nettoyé et enrichi **31 504 événements** et plus de **168 000 articles de presse** couvrant le Bénin entre janvier et décembre 2025, directement depuis Google BigQuery.

Cinq questions analytiques ont guidé notre travail. Voici ce que les données nous apprennent.

---

## Cinq insights pour comprendre l'image internationale du Bénin

### 1 — Décembre concentre le double de la couverture habituelle

Le mois de décembre 2025 totalise **30 785 articles**, soit près du double de la moyenne mensuelle. Ce pic est lié aux consultations diplomatiques régionales impliquant la CEDEAO, aux déclarations publiques d'acteurs nigérians concernant le Bénin et à des événements sécuritaires. Cette saisonnalité médiatique est prévisible et exploitable.

> *Les décideurs béninois peuvent anticiper ces périodes d'attention intense pour y positionner une communication institutionnelle proactive.*

### 2 — L'image du Bénin est dominée par les crises

**44 % des articles** ont un ton négatif, contre seulement **24 % de couverture positive**. Le ton moyen est de **−1,37** (sur une échelle où zéro est neutre). Le Bénin est couvert quand il y a des tensions — rarement quand il progresse.

> *Un effort systématique de communication positive (accords économiques, avancées sociales, coopération internationale) est nécessaire pour rééquilibrer cette image.*

### 3 — 99 % des événements sont repris en moins de 24 heures

La couverture est **quasi instantanée** : un événement à Cotonou ou Porto-Novo est visible dans les rédactions du monde entier le jour même. Les responsables béninois ne disposent d'aucun délai pour préparer une réponse avant que l'information ne circule à l'international.

> *GDELT peut servir d'outil de veille en temps réel. Une cellule de monitoring automatisée alerterait les communicants dès qu'un seuil critique de couverture est franchi.*

### 4 — Ce sont les médias nigérians qui racontent le Bénin au monde

**7 des 10 premières sources** couvrant le Bénin sont nigérianes (punchng.com, dailypost.ng, guardian.ng, etc.). Ce constat reflète la proximité géographique et les liens économiques forts entre les deux pays. La première source béninoise — **lanouvelletribune.info** — n'arrive qu'en sixième position. En période de crise, **saharareporters.com** apparaît comme source spécifique, absente de la couverture normale.

> *Le Bénin devrait engager un dialogue éditorial direct avec les rédactions nigérianes — ses premiers « ambassadeurs médiatiques » — et investir dans la visibilité internationale de sa propre presse.*

### 5 — Le Bénin subit plus qu'il n'agit sur la scène internationale

Dans **41 % des événements**, le Bénin est un simple cadre géographique. Il n'est véritablement **acteur** que dans **31 %** des cas, principalement via son gouvernement (788 événements) et ses forces armées (153). Le Bénin est davantage un terrain d'événements qu'un acteur géopolitique proactif.

> *Multiplier les initiatives diplomatiques visibles — sommets, accords bilatéraux, prises de position à l'ONU, à l'UA et à la CEDEAO — permettrait de transformer cette image.*

---

## Et aussi : 3 025 événements graves passent sous les radars

Notre analyse bonus révèle **3 025 événements très négatifs** (Goldstein inférieur ou égal à −5) qui n'ont été couverts que par 1 à 5 articles. **73 %** se sont produits au Bénin. Il s'agit principalement de violences de masse (1 012), d'assauts (913) et d'attentats (318). Ces situations pourraient devenir des crises médiatiques majeures si un grand média international les reprend.

---

## Notre modèle prédictif

Un classificateur **Random Forest** prédit le ton médiatique d'un événement béninois à partir de ses caractéristiques. La variable la plus déterminante : **l'échelle de Goldstein** (intensité géopolitique). Ce modèle permet d'identifier en amont les types d'événements qui génèrent une couverture négative — et d'anticiper.

---

## Nos livrables

| Livrable | Accès |
|---|---|
| Dépôt GitHub public | [github.com/jeangodjedo/benin-insights-challenge](https://github.com/jeangodjedo/benin-insights-challenge) |
| Notebook EDA (10+ visualisations) | `notebooks/eda_benin_gdelt_2025.ipynb` |
| Dashboard interactif Streamlit | `dashboard/app.py` |
| Pipeline ETL testé (72 tests) | `pipeline/` |
| Modèle ML sauvegardé | `models/tone_classifier_rf.pkl` |

---

**Bénin Insights Challenge 2026** · iSHEERO x DataCamp Donates · Équipe 7
Données : GDELT Project (`gdelt-bq.gdeltv2.events`) · Période : janvier–décembre 2025

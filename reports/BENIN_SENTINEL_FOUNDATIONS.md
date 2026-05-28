# BeninSentinel — Fondations Méthodologiques

**Projet** : Système de veille et d'intelligence territoriale pour la prévention des crises au Bénin
**Cible** : Décideurs publics béninois (Présidence, Ministère de l'Intérieur, ANSSI-Bénin, préfets, ONG de paix)
**Auteurs** : IROKO Analytics — Équipe 7
**Hackathon** : iSHEERO × DataCamp Donates — Finale 2026
**Version** : 1.0 — Document de spécification rigoureuse

---

## 1. Le problème, formulé sans concession

### 1.1 Constat factuel issu de nos données GDELT 2025

Sur 31 504 événements analysés au Bénin en 2025, **44,2 % portent un ton médiatique négatif**. Le mois de décembre concentre **60 % d'articles négatifs** à lui seul, en lien direct avec la tentative de coup d'État du 7 décembre 2025 annoncée par le ministre Alassane Seidou. Cet épisode illustre un schéma plus vaste : **les décideurs béninois apprennent les crises au moment où elles éclatent dans les médias, pas avant.**

### 1.2 Trois angles morts mesurés

1. **Pas de système d'alerte précoce sur signaux faibles** — les augmentations anormales de tensions verbales, de protestations, ou de désapprobations qui précèdent typiquement les crises matérielles ne sont pas surveillées de façon structurée.

2. **Pas de cartographie territoriale du risque** — les 12 départements du Bénin ne disposent pas d'un tableau de bord temps réel des tensions médiatiques propres à leur juridiction.

3. **Pas de mémoire institutionnelle des crises** — chaque crise est traitée comme un événement isolé, sans capitalisation sur les patterns précurseurs des crises antérieures.

### 1.3 Le coût de l'angle mort

Faute d'anticipation, les décideurs n'ont d'autre choix que la communication réactive. Cette posture défensive entretient le déficit narratif (44 % négatif) et entrave les trois piliers du **Programme d'Action du Gouvernement 2021-2026** :

- **Gouvernance** — la souveraineté décisionnelle exige de l'anticipation, pas de la réaction
- **Numérique** — la donnée publique mondiale (GDELT) est ouverte mais inexploitée
- **Bien-être social** — chaque jour gagné sur une crise est un jour gagné pour la sécurité humaine

---

## 2. La solution — BeninSentinel

### 2.1 Promesse de valeur, énoncée précisément

> **BeninSentinel détecte les signaux précurseurs de tensions au Bénin avec 5 à 7 jours d'avance médiane sur la cristallisation médiatique de la crise**, en analysant en continu les variables structurelles de la base GDELT (volume, ton, intensité géopolitique, types d'événements, géolocalisation, diversité des sources) et en les confrontant à un référentiel comportemental établi sur l'historique 2025.

Cette promesse est **falsifiable** — c'est-à-dire vérifiable empiriquement. Nous démontrons sa validité sur l'épisode du coup d'État de décembre 2025 (cas-test).

### 2.2 Trois fonctions opérationnelles

1. **Détection** — algorithme composite de scoring de risque quotidien, par département et par typologie de tension (sécuritaire, social, politique)
2. **Cartographie** — visualisation géolocalisée du niveau de risque sur les 12 départements béninois
3. **Prescription** — pour chaque alerte, une recommandation d'action priorisée et un horizon de réponse

### 2.3 Ce que BeninSentinel n'est PAS

Par souci d'honnêteté méthodologique, voici les limites assumées :

- **N'est pas un oracle** — la détection des signaux faibles n'est probabiliste, pas déterministe. Les faux positifs existent et sont quantifiés dans le rapport de validation.
- **N'est pas un substitut au renseignement humain** — c'est un outil d'aide à la décision, pas un remplacement des analystes territoriaux.
- **N'est pas un système temps réel au sens informatique strict** — il fonctionne avec la fréquence d'actualisation de GDELT (toutes les 15 minutes). Le temps réel est celui de l'écosystème médiatique mondial, pas celui des capteurs locaux.

---

## 3. Architecture analytique

### 3.1 Hypothèse fondatrice à valider empiriquement

> **H0 — Une crise médiatique majeure (volume + négativité au-dessus du 95e percentile) est précédée, dans une fenêtre de 5 à 14 jours, d'une augmentation statistiquement significative d'au moins trois signaux précurseurs.**

Si cette hypothèse est confirmée sur les données 2025, la détection à 5-7 jours est faisable. Le rapport de validation (`BENIN_SENTINEL_VALIDATION.md`) répondra par OUI ou NON, avec les chiffres.

### 3.2 Les 6 signaux faibles surveillés

Pour chaque jour `t` et chaque département `d`, BeninSentinel calcule :

| Signal | Définition | Variable GDELT mobilisée | Seuil d'alerte |
|---|---|---|---|
| **S1 — Tension verbale** | Nombre d'événements `QuadClass=3` (Conflit verbal) sur les 7 derniers jours | `QuadClass` | > moyenne + 2σ |
| **S2 — Dégradation Goldstein** | Goldstein moyen 7j vs référence 30j | `GoldsteinScale` | Δ < -1,5 |
| **S3 — Bascule de ton** | Ratio articles négatifs 7j vs référence 30j | `tone_category`, `AvgTone` | Δ > +15 points |
| **S4 — Pic protestation** | Nombre d'événements de type `Protestation`, `Désapprobation`, `Menace` sur 7j | `event_root_label` | > 1,5 × historique |
| **S5 — Affluence médiatique anormale** | Nombre de sources distinctes 7j vs référence 30j | `source_domain` | Δ > +30 % |
| **S6 — Accélération de propagation** | Délai moyen `DATEADDED - SQLDATE` sur 7j | `propagation_delay_days` | < 0,5 jour |

Chaque signal renvoie une valeur normalisée entre 0 et 1.

### 3.3 Score composite de risque

```
Risk_score(t, d) = 0.20 × S1 + 0.25 × S2 + 0.20 × S3 + 0.15 × S4 + 0.10 × S5 + 0.10 × S6
```

Les pondérations sont calibrées sur l'épisode de décembre 2025 (cas-test). La transparence de ces poids est un choix méthodologique : ils sont visibles, modifiables, auditables — pas une boîte noire.

### 3.4 Système d'alertes graduées

| Niveau | Code couleur | Score | Action recommandée |
|---|---|---|---|
| **Vigilance** | Vert | 0 ≤ score < 0,40 | Surveillance passive — bulletin hebdomadaire |
| **Préoccupation** | Jaune | 0,40 ≤ score < 0,60 | Veille active — bulletin quotidien, briefing préfet |
| **Alerte** | Orange | 0,60 ≤ score < 0,80 | Mobilisation cellule de crise — bulletin 4h |
| **Crise imminente** | Rouge | 0,80 ≤ score ≤ 1,00 | Conseil restreint Présidence — bulletin 1h |

---

## 4. Méthodologie de validation empirique

### 4.1 Cas-test n°1 — Tentative de coup d'État du 7 décembre 2025

Reconstitution rétrospective : aurait-on pu détecter la crise du 7 décembre en utilisant BeninSentinel sur la fenêtre 25 novembre — 6 décembre ?

**Métriques attendues** :
- Délai de détection effectif (jours avant le 7 décembre)
- Niveau d'alerte maximal atteint avant le 7 décembre
- Signaux ayant le plus contribué au déclenchement

### 4.2 Cas-test n°2 — Faux positifs

Sur les 359 jours non-crise de 2025, BeninSentinel doit générer un nombre limité d'alertes rouges/oranges erronées. Métrique cible : **taux de faux positifs < 10 %** sur l'année.

### 4.3 Backtesting généralisé

Pour chacun des 10 jours les plus tendus de 2025, mesurer :
- Le délai de détection
- Le niveau d'alerte maximum dans la fenêtre J-14 à J-1

---

## 5. Ancrage stratégique — PAG 2021-2026

BeninSentinel s'inscrit explicitement dans les trois piliers du Programme d'Action du Gouvernement :

| Pilier PAG | Apport de BeninSentinel |
|---|---|
| **Pilier 1 — Consolider la démocratie, l'État de droit et la bonne gouvernance** | Outil d'aide à la décision publique qui renforce la capacité d'anticipation des autorités. Transparence des indicateurs (signaux et seuils publics). |
| **Pilier 2 — Engager la transformation structurelle de l'économie via le numérique** | Application concrète de la data science appliquée à la donnée publique mondiale (GDELT). Démonstration de l'autonomie analytique béninoise. |
| **Pilier 3 — Améliorer les conditions de vie des populations** | Prévention des crises = vies humaines protégées, biens préservés, climat social apaisé. Le bénéfice est mesurable en jours d'avance gagnés. |

---

## 6. Roadmap produit (post-finale)

**Phase 1 — Prototype démontré (livré au Demo Day Finale)** : interface Streamlit, données 2025, validation rétrospective coup d'État.

**Phase 2 — Production pilote (3-6 mois)** : flux GDELT temps réel, abonnements alertes par SMS/email aux préfectures, intégration avec les CCC (Centres de Coordination de Crise).

**Phase 3 — Extension régionale** : déclinaison sur l'espace CEDEAO, en partenariat avec le Centre Régional pour la Sécurité Maritime de l'Afrique Centrale (CRESMAC) ou équivalent CEDEAO.

---

## 7. Honnêteté intellectuelle assumée

- **GDELT a un biais anglophone** — la couverture francophone et locale du Bénin est sous-représentée. BeninSentinel est complémentaire, pas substitutif, des sources humaines locales.
- **L'année 2025 est unique** — la calibration des seuils devra être révisée chaque année.
- **Le modèle est probabiliste** — une alerte n'est pas une certitude. La décision finale reste humaine.
- **L'éthique du data-driven decision-making** est un sujet en soi — BeninSentinel n'a aucune ambition prédictive sur des individus ou des groupes spécifiques.

---

> **« Un outil n'est pas excellent parce qu'il prédit. Il est excellent parce qu'il donne du temps. »**
> — Principe directeur de BeninSentinel

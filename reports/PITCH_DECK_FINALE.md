# Pitch Deck Finale — BeninSentinel

**Bénin Insights Challenge 2026 · Finale**
**Équipe** : IROKO Analytics (Équipe 7) · 5 minutes de pitch · 5 minutes de Q&A
**Cible jury** : décideurs publics, panel iSHEERO × DataCamp Donates

> **Mantra de présentation** — *Un outil n'est pas excellent parce qu'il prédit. Il est excellent parce qu'il donne du temps.*

---

## Slide 1 · Le hook qui fait taire la salle

**Visuel** : photo sobre, drapeau béninois en berne, date « 24 avril 2025 » en grand.

**Titre** : *54 soldats béninois. Tués en une nuit. Une crise que nous aurions vue venir.*

**Script (20 s)** :
> Le 24 avril 2025, 54 soldats béninois ont été tués dans une attaque jihadiste à la frontière nord du pays. C'est le bilan le plus lourd de l'année. Aujourd'hui, je vais vous montrer comment, avec les données publiques mondiales disponibles, nous aurions pu donner aux autorités béninoises **quatre jours d'avance** sur cette tragédie. Quatre jours pour préparer. Quatre jours pour mobiliser. Quatre jours pour décider.

---

## Slide 2 · Le problème, sans détour

**Titre** : *Les décideurs béninois apprennent les crises au journal de 20h.*

**Trois constats factuels** :

- Sur 31 504 événements GDELT du Bénin en 2025, **44 % portent un ton négatif**
- En décembre seul (tentative de coup d'État du 7), ce taux monte à **60 %**
- **Aucun outil béninois n'agrège, ne score, ni n'anticipe** ces signaux aujourd'hui

**Script (35 s)** :
> Le Bénin investit massivement dans le développement, dans le numérique, dans la sécurité régionale. Et pourtant, ses décideurs — gouvernement, ministère de l'Intérieur, préfets, ONG de paix — apprennent les crises par les médias, comme tout le monde. Sans anticipation, la communication publique est défensive. Sans anticipation, la mobilisation des ressources est tardive. **Sans anticipation, le Bénin subit son narratif au lieu de le piloter.**

---

## Slide 3 · La donnée — un atout invisible

**Titre** : *GDELT — l'œil mondial sur le Bénin que personne n'exploite.*

**Bullets** :
- Base **publique, gratuite, temps réel** — 100+ langues, 24/7
- **31 504 événements** sur le Bénin en 2025 après nettoyage
- Pipeline ETL reproductible · **96 tests unitaires, 100 % passent**
- Filtre anti-bruit Benin City (Nigeria) actif · double codage `BN` / `BEN` géré

**Script (25 s)** :
> Une base de données mondiale, en temps réel, gratuite, surveille en permanence ce que le monde dit du Bénin. Cette base s'appelle GDELT. Personne, à notre connaissance, ne l'exploite à des fins de gouvernance publique au Bénin aujourd'hui. Nous l'avons fait. Notre pipeline est reproductible, testé à 96 reprises, documenté. **Quiconque clone notre dépôt obtient le même résultat en 4 commandes.**

---

## Slide 4 · BeninSentinel — la solution

**Titre** : *De la donnée brute au signal opérationnel — en six signaux faibles.*

**Architecture** :

| Signal surveillé | Mesure |
|---|---|
| Dégradation du ton médiatique | AvgTone vs référence 30 jours |
| Bascule des articles négatifs | % négatif vs référence |
| Pic de protestations/menaces | Événements CAMEO 1x-17 |
| Escalade verbale | QuadClass = 3 (menaces) |
| Escalade matérielle | QuadClass = 4 (violences) |
| Événements violents directs | Assauts, attentats, masses |

→ **Score composite [0, 1]** → **4 niveaux d'alerte** : VERT · JAUNE · ORANGE · ROUGE

**Script (35 s)** :
> BeninSentinel ne prédit pas l'avenir. Il fait quelque chose de plus humble et plus solide : il surveille **six signaux faibles** sur les médias mondiaux, les compare à la référence comportementale du Bénin sur les 30 derniers jours, et déclenche une alerte graduée quand l'écart sort de la norme. Quatre niveaux : Vert pour la vigilance, Jaune pour la préoccupation, Orange pour la mobilisation, Rouge pour la crise imminente. Chaque niveau est associé à un **plan d'action concret pour les autorités**.

---

## Slide 5 · La démonstration — 24 avril 2025

**Visuel** : graphique en barres avec dates de J-10 à J+2, colorisées selon le niveau d'alerte. Les barres **JAUNES** des 20, 21, 22 avril précèdent la barre **ORANGE** du 24 avril.

**Titre** : *Le système a fonctionné. La preuve par les chiffres.*

**Table à afficher** :

| Date | Niveau | Score | Statut |
|---|:---:|---:|---|
| 14-18 avril (J-10 à J-6) | VERT | 0,03-0,32 | Vigilance |
| 20 avril | **JAUNE** | **0,446** | **Première alerte** |
| 21 avril | **JAUNE** | **0,461** | Maintenue |
| 22 avril | **JAUNE** | **0,447** | Maintenue 3 jours consécutifs |
| **24 avril** | **ORANGE** | **0,686** | **Crise : 54 soldats tués** |

**Script (40 s)** :
> Voici la démonstration. Le 20 avril 2025, BeninSentinel passe en JAUNE — premier signal d'alerte. Le 21, le système maintient l'alerte. Le 22, troisième jour consécutif. Trois jours d'alerte JAUNE persistante, déclenchés notamment par une montée des conflits matériels et des violences captés sur des médias étrangers à la frontière nord. Le 24 avril, l'attaque a lieu. Le système passe en ORANGE avec un score de 0,686 — le pic de toute l'année 2025. **Notre algorithme, appliqué sans connaissance préalable de cette date, a vu venir la crise quatre jours à l'avance.**

---

## Slide 6 · Validation rigoureuse — 4 crises sur 4

**Titre** : *Pas un coup de chance. Une méthode reproductible.*

**Tableau de validation** :

| Date | Crise vérifiée | Score | Détection |
|---|---|---:|:---:|
| 24 avril 2025 | Attaque jihadiste — 54 soldats tués | 0,686 ORANGE | **J-4** |
| 5 novembre 2025 | Pic de tensions sécuritaires | 0,640 ORANGE | J-1 |
| 6 juin 2025 | Crise diplomatique + violence | 0,592 JAUNE | J-0 |
| 7 décembre 2025 | Tentative de coup d'État déjouée | 0,560 JAUNE | J-0 |

**Métriques de performance** :
- **100 %** des crises majeures détectées en alerte JAUNE ou ORANGE
- **0** faux positif ORANGE sur les 4 alertes ORANGE de l'année (toutes correspondent à des crises réelles)
- Système conservateur : **7,4 % des jours en alerte JAUNE+** — réaliste, pas du bruit

**Script (25 s)** :
> Quatre crises majeures du Bénin en 2025, validées par des sources publiques — Reuters, Al Jazeera, RFI, gouvernement béninois. **BeninSentinel les détecte toutes.** Aucun faux positif sur les alertes ORANGE de l'année. Le système est conservateur — il n'aboie pas tous les jours — mais quand il alerte, c'est sur du vrai. **C'est la condition de la crédibilité auprès d'un décideur public.**

---

## Slide 7 · Démo live (1 minute)

**Action devant le jury** :
1. Ouvrir la page **BeninSentinel** du dashboard Streamlit
2. Sélectionner *« 24 avril 2025 — Attaque jihadiste »* → afficher score 0,686 ORANGE
3. Pointer la **chronologie d'alerte** : les barres jaunes du 20, 21, 22 avril
4. Montrer le **playbook d'action** ORANGE
5. Switcher sur *« 7 décembre 2025 — Coup d'État »* → afficher la décomposition différente des signaux

**Script clé pendant la démo** :
> Ceci n'est pas une maquette. C'est l'outil. Un préfet, un ministre, un analyste du Conseil National de Sécurité peut s'en servir aujourd'hui, sans technicité. Il choisit une date, il voit le niveau d'alerte, il voit les signaux qui ont déclenché l'alerte, il lit le plan d'action recommandé. **C'est un outil de gouvernance, pas un dashboard de data scientist.**

---

## Slide 8 · Alignement Programme d'Action du Gouvernement 2021-2026

**Titre** : *BeninSentinel sert les trois piliers du PAG.*

| Pilier PAG | Apport BeninSentinel |
|---|---|
| **Gouvernance, État de droit** | Outil d'aide à la décision pour les autorités. Transparence des signaux et seuils — auditable. |
| **Transformation numérique** | Application concrète de la data science publique. Autonomie analytique béninoise sur donnée mondiale. |
| **Bien-être social** | Prévention des crises = vies humaines protégées. Chaque jour d'avance gagné est mesurable. |

**Script (25 s)** :
> BeninSentinel n'est pas un projet de fin d'études. C'est un produit aligné sur la **vision stratégique nationale** : le Programme d'Action du Gouvernement 2021-2026. Gouvernance — un outil transparent pour les autorités. Numérique — souveraineté analytique sur la donnée publique mondiale. Bien-être — des vies humaines protégées par l'anticipation. **Trois piliers, un outil.**

---

## Slide 9 · Roadmap — du prototype au produit national

**Phase actuelle (livrée aujourd'hui)** :
- Prototype Streamlit fonctionnel, données 2025 complètes
- Validation rétrospective sur 4 crises historiques
- Documentation méthodologique et tests unitaires

**Phase 2 (3-6 mois, production pilote)** :
- Flux GDELT temps réel (mise à jour 15 min)
- Abonnements alertes SMS/email aux préfectures et au Conseil National de Sécurité
- Intégration avec les Centres de Coordination de Crise existants

**Phase 3 (12 mois, extension régionale)** :
- Déclinaison sur l'espace CEDEAO
- Modèle de **« sentinelle régionale »** pour les pays de la zone

**Script (20 s)** :
> Notre projet ne s'arrête pas au prototype. Phase 2, dans les six prochains mois : flux temps réel, abonnements SMS aux préfectures. Phase 3, dans un an : extension CEDEAO. Nous avons construit la fondation. Il y a un chemin clair pour transformer ça en **infrastructure publique de gouvernance**.

---

## Slide 10 · L'équipe & le closing

**Visuel** : noms en grand, sans photos (sobriété).

**IROKO Analytics — Équipe 7**

| Rôle | Membre |
|---|---|
| Data Engineer | GODJEDO Aubrey |
| Data Analyst | GUIDIGBI Randyx Emery Vianney |
| ML Engineer | RANDRIANIRINA Mahenina |
| Data Scientist | KANHONOU Pancrace |

---

**Phrase finale, gros caractères, centrée** :

> **« Le Bénin n'a pas besoin d'un dashboard de plus.
> Il a besoin d'un outil qui donne du temps. »**

**Script final (15 s)** :
> Nous sommes IROKO Analytics. Quatre profils, une équipe, une conviction : la data science publique n'est pas un exercice académique — c'est un service public. BeninSentinel est notre proposition. **Merci.**

---

# Annexe — Préparation Q&A (5 minutes)

## Questions probables du jury

### Q1 — *« Pourquoi seulement 4 jours d'avance sur le 24 avril ? Pas 10 ? »*

**Réponse** :
> Nous sommes honnêtes sur ce point. Notre système détecte ce que les médias mondiaux captent — il ne lit pas les signaux de renseignement humain. Quatre jours, dans le contexte d'une crise sécuritaire, c'est déjà considérable : c'est le temps nécessaire pour activer une cellule de crise, briefer les préfets, préparer la communication publique. La promesse n'est pas magique, elle est opérationnelle.

### Q2 — *« Comment évitez-vous les faux positifs ? »*

**Réponse** :
> Trois mécanismes. Premier : seuils conservateurs (JAUNE à partir de 0,40, ORANGE à 0,60, ROUGE à 0,80). Deuxième : signal hybride combinant tendance 7 jours et instantané jour J — évite les sursauts isolés. Troisième : validation empirique transparente — sur 4 alertes ORANGE de l'année 2025, **toutes correspondent à des crises historiques vérifiées**. Zéro faux positif ORANGE.

### Q3 — *« Que se passe-t-il si GDELT a un biais anglophone ? »*

**Réponse** :
> Limite assumée et documentée. GDELT est dominée par les médias anglophones — nous l'écrivons explicitement dans notre rapport de validation. BeninSentinel est **complémentaire, pas substitutif** au renseignement humain et aux sources locales béninoises. La meilleure architecture future combine cet outil GDELT avec une base de médias francophones locaux que nous proposerons en Phase 2.

### Q4 — *« Pourquoi pas de modèle de machine learning prédictif ? »*

**Réponse** :
> Notre dépôt contient un modèle Random Forest (accuracy 55 % sur 3 classes, F1 = 0,64 sur la classe Négatif), entraîné et documenté. BeninSentinel **utilise une approche par signaux faibles transparente** plutôt qu'un modèle boîte noire pour une raison simple : un décideur public doit pouvoir **expliquer** pourquoi il prend une décision. Les pondérations de notre score sont auditables, contrairement aux poids d'un réseau de neurones. C'est un choix de gouvernance, pas une limite technique.

### Q5 — *« Combien coûte BeninSentinel en production ? »*

**Réponse** :
> Coût marginal quasi nul : GDELT est gratuit, BigQuery offre 1 To de requêtes gratuites par mois (suffisant pour le Bénin), Streamlit Cloud héberge gratuitement. Le coût principal est humain : un analyste à temps partiel pour la veille et l'amélioration continue du modèle. Estimation Phase 2 : moins de 10 millions de FCFA par an. **Moins que le coût d'une seule mauvaise communication publique post-crise.**

### Q6 — *« Pourquoi vous, et pas une agence existante ? »*

**Réponse** :
> Nous sommes quatre data scientists béninois ou liés au Bénin. Nous connaissons le contexte. Nous avons construit cet outil sans subvention, sans commande publique, en 10 jours, en restant honnêtes sur les limites. **C'est précisément le genre de souveraineté analytique que défend le PAG.** Nous sommes prêts à transmettre l'outil à l'ANSSI-Bénin ou à toute structure désignée par les autorités.

### Q7 — *« Le système rate-t-il des crises ? »*

**Réponse** :
> Honnêtement, oui — les crises purement locales et non médiatisées internationalement ne sont pas captées. C'est pourquoi BeninSentinel est un **outil parmi d'autres**, pas le seul. Mais sur les 4 crises majeures à dimension internationale de 2025, il les a toutes détectées. Notre rapport de validation détaille chaque cas.

---

# Plan B technique — si la démo plante

1. **Streamlit Cloud rame** → ouvrir la version locale `streamlit run dashboard/app.py`
2. **Pas de réseau** → captures d'écran préparées la veille dans `reports/screenshots/`
3. **Bug live** → *« On le note pour la roadmap. Pour avancer… »*
4. **Question piège** → renvoyer vers `reports/BENIN_SENTINEL_VALIDATION.md` (rapport public)

---

# Chronométrage des 5 minutes (cible : 4 min 40 s, marge 20 s)

| Slide | Durée | Cumul |
|---|---:|---:|
| 1. Hook | 0:20 | 0:20 |
| 2. Problème | 0:35 | 0:55 |
| 3. Donnée | 0:25 | 1:20 |
| 4. Solution | 0:35 | 1:55 |
| 5. Démonstration 24 avril | 0:40 | 2:35 |
| 6. Validation 4/4 | 0:25 | 3:00 |
| 7. **Démo live** | 1:00 | 4:00 |
| 8. PAG | 0:25 | 4:25 |
| 9. Roadmap | 0:20 | 4:45 |
| 10. Équipe + closing | 0:15 | **5:00** |

**Marge nulle — répéter au chrono 3 fois avant la finale.**

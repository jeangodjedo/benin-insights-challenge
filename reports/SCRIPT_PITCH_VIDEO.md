# Script du Pitch Video — 3 minutes
## Benin Insights Challenge 2026 — Equipe 7

---

## Guide technique

- **Duree cible** : 2 minutes 50 secondes (marge de 10 secondes)
- **Format** : MP4, lien YouTube ou Google Drive public
- **Intervenants** : Data Scientist (voix principale), equipe en introduction
- **Support visuel** : ecran partage sur le dashboard Streamlit pendant les insights

---

## SEQUENCE 1 — Presentation (0:00 a 0:35)

**[Camera : visages de l equipe, ou mosaique des 4 membres]**

Bonjour, nous sommes l Equipe 7 du Benin Insights Challenge 2026, organise par iSHEERO et DataCamp Donates.

Notre equipe reunit quatre competences complementaires : un Data Engineer, un Data Analyst, un ML Engineer et un Data Scientist.

Nous nous sommes poses une question simple mais fondamentale : comment le monde voit-il le Benin ? 

Pour y repondre, nous avons analyse la base de donnees GDELT, qui recense les evenements geopolitiques mondiaux a partir de milliers de sources de presse. Nous avons extrait et analyse 31 504 evenements et plus de 168 000 articles couvrant le Benin tout au long de l annee 2025.

---

## SEQUENCE 2 — Notre methode (0:35 a 1:10)

**[Ecran partage : montrer le depot GitHub, puis le notebook brievement]**

Notre pipeline est entierement automatise et reproductible.

Le Data Engineer a construit un systeme d extraction depuis Google BigQuery avec un filtre intelligent qui separe les evenements du Benin de ceux de Benin City au Nigeria — un defi technique majeur que nous avons resolu grace a un filtrage multi-criteres sur les codes geographiques et les noms d acteurs.

Le pipeline est couvert par 72 tests unitaires — tous reussis.

Le Data Analyst a ensuite produit un dashboard interactif Streamlit avec 12 visualisations et des filtres temporels. Chaque graphique est accompagne d un insight automatique genere a partir des donnees.

Enfin, le ML Engineer a entraine un modele Random Forest qui predit si un evenement beninois generera une couverture positive, neutre ou negative — un outil concret pour les decideurs.

---

## SEQUENCE 3 — Trois resultats cles (1:10 a 2:25)

**[Ecran partage : naviguer dans le dashboard, montrer chaque visualisation]**

Voici nos trois decouvertes les plus importantes.

### Resultat 1 — Le Benin est percu negativement

**[Montrer le graphique Q2 : donut chart du ton mediatique]**

44 pourcent de la couverture internationale du Benin a un ton negatif. Seulement 24 pourcent est positive. Le monde parle du Benin quand il y a des tensions — rarement quand le pays progresse. Le ton moyen global est de moins 1 virgule 37 sur une echelle ou zero est neutre.

C est un signal clair : l image internationale du Benin ne reflete pas ses avancees reelles.

### Resultat 2 — Ce sont les medias nigerians qui racontent le Benin

**[Montrer le graphique Q4 : comparaison sources crise vs normale]**

7 des 10 premieres sources qui couvrent le Benin sont nigerianes : Punch, DailyPost, Guardian Nigeria. La premiere source beninoise — La Nouvelle Tribune — n arrive qu en sixieme position.

Ce n est pas une erreur. C est la realite de la geographie mediatique ouest-africaine. Les redactions de Lagos et Abuja sont les premiers ambassadeurs mediatiques du Benin dans le monde. Le gouvernement beninois doit engager un dialogue editorial avec ces redactions.

### Resultat 3 — Le Benin subit plus qu il n agit

**[Montrer le graphique Q5 : donut chart des roles]**

Dans 41 pourcent des evenements, le Benin est un simple decor geographique : les choses se passent au Benin sans que le pays en soit l initiateur. Il n est veritablement acteur que dans 31 pourcent des cas, principalement via son gouvernement et ses forces armees.

Le Benin est encore un terrain d evenements plutot qu un acteur geopolitique proactif.

---

## SEQUENCE 4 — Ce que ca change (2:25 a 3:00)

**[Camera : retour face camera, ton conclusif et determine]**

Que doivent retenir les decideurs beninois ?

Premierement : la couverture est instantanee. 99 pourcent des evenements sont repris en moins de 24 heures. Il n y a aucune marge pour reagir apres coup. Une cellule de veille mediatique automatisee est indispensable.

Deuxiemement : ce sont les medias nigerians qui faconnent l image du Benin. Il faut les considerer comme des partenaires strategiques et engager un dialogue editorial direct.

Troisiemement : le Benin doit passer de terrain d evenements a acteur de son propre recit. Plus d initiatives diplomatiques visibles, plus de communication proactive.

Les donnees nous montrent le chemin. A nous de le suivre.

Merci pour votre attention. Nous sommes l Equipe 7, et nous croyons que les donnees peuvent changer la facon dont un pays se voit — et dont le monde le voit.

---

## Checklist avant soumission

- [ ] Duree inferieure ou egale a 3 minutes
- [ ] Qualite audio claire, pas de bruit de fond
- [ ] Les 3 insights les plus marquants sont presentes avec les graphiques
- [ ] Le dashboard est montre en action avec les filtres
- [ ] Le ton est professionnel et accessible
- [ ] Heberge sur YouTube ou Google Drive avec lien public
- [ ] Lien soumis via le formulaire officiel du hackathon

---

Benin Insights Challenge 2026 — Equipe 7 — iSHEERO x DataCamp Donates

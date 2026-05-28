# BeninSentinel — Déploiement en production temps réel

Ce document décrit la mise en service du système d'alerte temps réel
**BeninSentinel** sans intervention manuelle, en interrogeant la base
GDELT en direct toutes les 15 minutes.

Trois options de déploiement sont décrites. **La première (GitHub Actions)
est celle recommandée pour la finale du hackathon** : 100 % gratuite,
sans serveur, auditable publiquement.

---

## Option 1 — GitHub Actions ⭐ recommandée pour la finale

### Pourquoi
- **Gratuit** — sous la limite des 2 000 minutes/mois pour repos privés (et illimité pour repos publics)
- **Sans serveur** — GitHub exécute, on n'a rien à maintenir
- **Logs publics auditables** dans l'onglet **Actions** du dépôt — démontrable au jury et conforme au PAG (transparence de la décision publique)
- **Configurable en 15 minutes**
- **Persistance via cache GitHub Actions** — l'historique SQLite est conservé entre les runs

### Setup en 4 étapes

#### 1. Workload Identity Federation (WIF) — auth GCP sans clé JSON

GitHub Actions s'authentifie à BigQuery via **OIDC** et **Workload Identity Federation** —
pas de clé JSON longue durée stockée nulle part. À chaque run, GitHub présente un
token éphémère, GCP le vérifie cryptographiquement et émet un token temporaire
d'accès BigQuery. Conforme aux meilleures pratiques 2024+ Google Cloud.

Setup en une seule séquence de commandes (`gcloud` + `gh` requis) :

```bash
# Service account dédié (déjà créé : benin-sentinel-bigquery)
SA_EMAIL="benin-sentinel-bigquery@alex-495410.iam.gserviceaccount.com"
PROJECT="alex-495410"
REPO="jeangodjedo/benin-insights-challenge"

# Activer les API nécessaires
gcloud services enable iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com bigquery.googleapis.com --project=$PROJECT

# Créer le Workload Identity Pool
gcloud iam workload-identity-pools create "github-actions-pool" \
    --project=$PROJECT --location="global" \
    --display-name="GitHub Actions Pool"

# Créer le Provider OIDC pour GitHub (restreint au seul owner du repo)
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
    --project=$PROJECT --location="global" \
    --workload-identity-pool="github-actions-pool" \
    --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
    --attribute-condition="assertion.repository_owner == 'jeangodjedo'" \
    --issuer-uri="https://token.actions.githubusercontent.com"

# Récupérer le nom complet du pool
POOL_NAME=$(gcloud iam workload-identity-pools describe "github-actions-pool" \
    --project=$PROJECT --location="global" --format="value(name)")

# Lier le pool au service account, restreint au repo cible
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
    --project=$PROJECT \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${REPO}"
```

#### 2. Configurer les secrets GitHub (2 min)

Aller dans **Settings → Secrets and variables → Actions → New repository secret** ou
utiliser la CLI `gh secret set`. Créer ces 8 secrets :

| Nom du secret | Valeur |
|---|---|
| `GCP_PROJECT_ID` | `alex-495410` |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | sortie de `gcloud iam workload-identity-pools providers describe github-provider --workload-identity-pool=github-actions-pool --project=alex-495410 --location=global --format="value(name)"` |
| `GCP_SERVICE_ACCOUNT` | `benin-sentinel-bigquery@alex-495410.iam.gserviceaccount.com` |
| `SENTINEL_SMTP_HOST` | `smtp-relay.brevo.com` |
| `SENTINEL_SMTP_PORT` | `587` |
| `SENTINEL_SMTP_USER` | `acd483001@smtp-brevo.com` |
| `SENTINEL_SMTP_PASSWORD` | clé Brevo (`xsmtpsib-...`) |
| `SENTINEL_SMTP_FROM_EMAIL` | `devpancrace@gmail.com` |

#### 3. Activer le workflow (1 clic)

Le fichier `.github/workflows/realtime_sentinel.yml` est déjà présent dans le repo. Une fois mergé sur `main`, le workflow s'active automatiquement.

GitHub Actions exécutera le tick **toutes les 15 minutes** sans intervention.

#### 4. Vérifier que ça tourne

Aller sur **github.com/jeangodjedo/benin-insights-challenge/actions** → onglet **« BeninSentinel — Surveillance temps réel »**.

À chaque run on doit voir :
- ✅ Restauration de l'historique depuis le cache
- ✅ Authentification GCP
- ✅ Exécution du tick avec succès
- 📦 Sauvegarde de l'historique dans le cache

Pour **forcer un run immédiat** (sans attendre 15 min) : cliquer sur **« Run workflow »**.

### Limites GitHub Actions à connaître
- Le cron `*/15 * * * *` est **best-effort** : GitHub peut retarder de quelques minutes en cas de charge globale (rare). C'est acceptable pour une veille — on n'est pas dans du temps-réel haute fréquence.
- Le cache GitHub a une durée de vie de **7 jours sans accès** — comme on accède toutes les 15 minutes, on est largement dans les clous.
- Le cache est limité à **10 GB par dépôt** — la base SQLite fait quelques KB, aucun risque.

---

## Option 2 — Serveur dédié avec systemd (production institutionnelle)

### Pourquoi
- **Contrôle total** — adapté à un déploiement chez l'ANSSI-Bénin
- **Logs centralisés** dans `journalctl`
- **Reprise automatique** sur erreur
- **Plus rapide** que GitHub Actions (pas de cold start)

### Setup sur Ubuntu 22.04

```bash
# 1. Cloner le code et installer les dépendances
sudo useradd -m -s /bin/bash sentinel
sudo -u sentinel git clone https://github.com/jeangodjedo/benin-insights-challenge.git /home/sentinel/benin-insights-challenge
cd /home/sentinel/benin-insights-challenge
sudo -u sentinel python3.12 -m venv venv
sudo -u sentinel ./venv/bin/pip install -r requirements.txt

# 2. Configurer l'environnement (clé service account + Brevo)
sudo mkdir -p /etc/benin-sentinel
sudo nano /etc/benin-sentinel/env
# (remplir avec les variables — voir .env.example)
sudo chmod 600 /etc/benin-sentinel/env
sudo chown sentinel:sentinel /etc/benin-sentinel/env

# 3. Créer le service systemd
sudo nano /etc/systemd/system/benin-sentinel.service
```

Contenu du service :
```ini
[Unit]
Description=BeninSentinel — Système de veille temps réel
After=network.target

[Service]
Type=simple
User=sentinel
WorkingDirectory=/home/sentinel/benin-insights-challenge
EnvironmentFile=/etc/benin-sentinel/env
ExecStart=/home/sentinel/benin-insights-challenge/venv/bin/python -m scheduler.run_realtime --loop --interval-minutes 15
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Activation :
```bash
sudo systemctl daemon-reload
sudo systemctl enable benin-sentinel
sudo systemctl start benin-sentinel
sudo journalctl -u benin-sentinel -f
```

Coût indicatif d'un VPS adapté : **~5 €/mois** (Hetzner CX11, OVH Eco, Scaleway Stardust).

---

## Option 3 — Cron Linux sur machine perso (démo locale)

### Quand utiliser
Pendant la phase de tests, sur ton ordinateur personnel. Attention : ta machine doit rester allumée.

### Setup
```bash
crontab -e
```

Ajouter cette ligne :
```cron
*/15 * * * * cd /home/pancrace/Bureau/development/benin-insights-challenge && \
             ./venv/bin/python -m scheduler.run_realtime --once \
             >> /tmp/sentinel.log 2>&1
```

---

## Vérification du bon fonctionnement

Quelle que soit l'option choisie, la **page « Surveillance temps réel »** du dashboard Streamlit lit directement la base SQLite et affiche en continu :

- L'état courant (dernier tick enregistré, niveau, score, date analysée)
- Le journal chronologique des transitions
- L'évolution du score sur l'historique disponible
- L'audit complet des notifications envoyées (qui, quand, par quel canal, statut)

Pour un audit indépendant, on peut aussi consulter directement la base SQLite :

```bash
sqlite3 data/sentinel_history.db "SELECT * FROM transitions ORDER BY detected_at DESC LIMIT 10;"
sqlite3 data/sentinel_history.db "SELECT * FROM notifications ORDER BY sent_at DESC LIMIT 20;"
```

---

## Coûts d'exploitation estimés

| Composant | Coût mensuel |
|---|---|
| GitHub Actions (Option 1) | **0 €** |
| Brevo SMTP (300 emails/jour gratuits) | **0 €** |
| BigQuery (quota gratuit 1 To/mois — on en consomme ~30 Go avec un tick toutes les 15 min) | **0 €** |
| **Total** | **0 €** |

Le système est conçu pour rester **gratuit à l'usage** tant que :
- les alertes restent rares (~10 emails/mois × 9 destinataires = 90 envois, vs 9 000 inclus chez Brevo)
- le volume GDELT extrait reste sous la barre du teraoctet par mois (cf. requête filtrée Bénin + 45 jours)

---

## Sécurité et conformité

- **Aucun credential dans le code** — tout passe par variables d'environnement (`.env` localement, secrets GitHub en production)
- **Service account GCP au moindre privilège** — uniquement les rôles BigQuery nécessaires
- **Audit complet en base SQLite** — chaque envoi tracé avec horodatage et statut
- **Logs publics** sur GitHub Actions — auditabilité conforme aux exigences PAG 2021-2026
- **Rotation possible des clés** — clé Brevo régénérable en un clic, service account révocable

---

## En cas d'incident

Le workflow GitHub Actions enregistre automatiquement les **logs complets** et la **base SQLite** à chaque run, conservés en artifact pendant **30 jours**. Cela permet de diagnostiquer toute anomalie a posteriori sans aucun accès privilégié à l'infrastructure.

Pour reprendre proprement après un incident, il suffit de relancer manuellement le workflow depuis l'onglet **Actions → Run workflow**.

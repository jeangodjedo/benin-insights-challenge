# BeninSentinel — Architecture Temps Réel

**Du prototype démontré à l'alerte opérationnelle continue.**

Ce document décrit l'architecture technique du système d'alerte temps réel
BeninSentinel — la brique Phase 2 qui transforme le prototype démontré en
finale du hackathon en outil opérationnel déployable en production au sein
de l'ANSSI-Bénin ou d'une structure habilitée par la Présidence.

---

## 1. Vue d'ensemble

```
        ┌──────────────┐
        │  Scheduler   │   tous les N minutes (60 par défaut)
        │  (cron / sys │   → orchestrator.tick()
        │   temd / k8s)│
        └──────┬───────┘
               │
               ▼
        ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
        │  Streamer    │ ─→ │ Alert Engine │ ─→ │  Notifier    │ ─→ │  Providers   │
        │  (BigQuery   │    │  (sentinel + │    │  (routage    │    │ console/SMTP │
        │   ou local)  │    │   transition │    │   YAML)      │    │  webhook/SMS │
        └──────┬───────┘    │   detection) │    └──────┬───────┘    └──────────────┘
               │            └──────┬───────┘           │
               │                   │                   │
               └───────────────────┼───────────────────┘
                                   ▼
                          ┌──────────────┐
                          │   History    │
                          │   SQLite     │    audit complet : états, transitions, notifications
                          │ (sentinel.db)│
                          └──────┬───────┘
                                 │
                                 ▼
                          ┌──────────────┐
                          │  Dashboard   │   page Streamlit "Surveillance temps réel"
                          │   (lecture)  │   consultable par la cellule de veille
                          └──────────────┘
```

---

## 2. Modules

### `pipeline/realtime/streamer.py`
Récupération incrémentale des données GDELT sur les 45 derniers jours
(profondeur configurable). Mode `live` via BigQuery, mode `local` via le
snapshot CSV. Bascule transparente si BigQuery indisponible.

### `pipeline/realtime/alert_engine.py`
Calcule le score BeninSentinel (via `pipeline.sentinel.run_sentinel`)
sur les données fraîches, compare au dernier état en base et décide
si une transition de niveau (VERT/JAUNE/ORANGE/ROUGE) doit être enregistrée.
Pas de logique de notification ici — séparation des responsabilités.

### `pipeline/realtime/history.py`
Persistance SQLite — trois tables : `alert_states`, `transitions`,
`notifications`. Pas de dépendance ORM, SQL natif lisible et auditable.
Indexée pour des requêtes rapides.

### `pipeline/realtime/notifier.py`
Routage des transitions vers les destinataires selon des règles définies
dans `config/notification_rules.yaml` croisées avec l'annuaire
`config/recipients.yaml`. Fail-safe : si un fichier YAML manque, le système
bascule en mode "console seulement" sans interruption.

### `pipeline/realtime/providers/`
Quatre providers de notification, tous dérivés de l'interface abstraite
`NotificationProvider`. Mode simulé partout (status="SIMULATED") activable
globalement pour les tests d'intégration.

| Provider | Canal | Statut |
|---|---|---|
| `ConsoleProvider` | Console + fichier JSON | Toujours disponible (zéro config) |
| `EmailProvider`   | SMTP (Gmail, Outlook, SendGrid…) | Activé via `.env` (SMTP_HOST + USER + PASSWORD) |
| `WebhookProvider` | HTTP POST JSON | Activé par destinataire (URL Slack/Teams/n8n) |
| `SMSProvider`     | Twilio / Africa's Talking | Interface définie (à câbler en production) |

### `pipeline/realtime/orchestrator.py`
Assemble Streamer + AlertEngine + Notifier dans un cycle `tick()` atomique
et crash-safe. Toute exception est tracée dans un `TickResult` structuré,
le scheduler peut continuer même si un tick échoue.

### `pipeline/realtime/templates_loader.py`
Rendu HTML des bulletins par niveau d'alerte. Utilise Jinja2 si dispo,
sinon un moteur de templating minimaliste embarqué (fallback zéro
dépendance).

### `scheduler/run_realtime.py`
Point d'entrée CLI. Deux modes :
- `--once` : un seul tick (utilisable avec cron système)
- `--loop` : boucle continue avec intervalle configurable

Gestion propre des signaux SIGTERM/SIGINT — compatible systemd, Docker,
Kubernetes (rolling restart, scale-down).

### `dashboard/pages/4_Surveillance_temps_reel.py`
Centre opérationnel pour l'opérateur du système. Affiche l'état courant,
le journal des transitions, l'évolution du score, l'audit des notifications.
Lecture uniquement depuis SQLite (ultra-rapide).

---

## 3. Configuration

### `config/recipients.yaml` — annuaire des destinataires
```yaml
recipients:
  - name: Préfecture Alibori
    role: prefecture_frontaliere
    channel: email
    address: prefet-alibori@example-benin.gov.bj
    active: true
```

### `config/notification_rules.yaml` — règles de routage
```yaml
rules:
  JAUNE:
    - presidence_veille
    - anssi_porteur
  ORANGE:
    - interieur_cabinet
    - prefecture_frontaliere
    - ...
  ROUGE:
    - presidence_cabinet
    - ...
```

Les deux fichiers sont **versionnés dans Git** — toute modification de la
liste des destinataires ou des règles de routage est traçable et auditable.

---

## 4. Variables d'environnement

Toutes optionnelles. Le système fonctionne sans aucune en mode simulé.

| Variable | Effet |
|---|---|
| `SENTINEL_DB_PATH` | Chemin SQLite (par défaut `data/sentinel_history.db`) |
| `SENTINEL_RECIPIENTS_PATH` | YAML annuaire (par défaut `config/recipients.yaml`) |
| `SENTINEL_RULES_PATH` | YAML règles (par défaut `config/notification_rules.yaml`) |
| `SENTINEL_INTERVAL_MIN` | Intervalle de boucle en minutes (par défaut 60) |
| `SENTINEL_DAYS_BACK` | Profondeur fenêtre GDELT (par défaut 45) |
| `SENTINEL_PREFER_LOCAL` | `1` pour forcer le CSV local (démo) |
| `SENTINEL_SIMULATE` | `1` pour simuler les providers (test d'intégration) |
| `SENTINEL_SMTP_HOST` | Hôte SMTP pour les emails (sans ça : mode simulé) |
| `SENTINEL_SMTP_PORT` | Port SMTP (587 par défaut) |
| `SENTINEL_SMTP_USER` | Login SMTP |
| `SENTINEL_SMTP_PASSWORD` | Mot de passe SMTP |
| `SENTINEL_SMTP_FROM_NAME` | Nom expéditeur affiché |
| `SENTINEL_SMTP_USE_TLS` | `1` pour TLS sur port 587 (par défaut) |

---

## 5. Déploiement

### Démo locale (mode simulé)
```bash
SENTINEL_PREFER_LOCAL=1 SENTINEL_SIMULATE=1 \
    python -m scheduler.run_realtime --once
```

### Cron système (production)
```cron
# Toutes les heures à 5 minutes après l'heure
5 * * * * cd /opt/benin-sentinel && \
          /opt/benin-sentinel/venv/bin/python -m scheduler.run_realtime --once \
          >> /var/log/sentinel.log 2>&1
```

### Systemd service (production)
```ini
# /etc/systemd/system/benin-sentinel.service
[Unit]
Description=BeninSentinel — Système de veille temps réel
After=network.target

[Service]
Type=simple
User=sentinel
WorkingDirectory=/opt/benin-sentinel
EnvironmentFile=/etc/benin-sentinel/env
ExecStart=/opt/benin-sentinel/venv/bin/python -m scheduler.run_realtime --loop
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable benin-sentinel
sudo systemctl start benin-sentinel
sudo journalctl -u benin-sentinel -f
```

### Docker (option)
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV SENTINEL_DB_PATH=/data/sentinel_history.db
CMD ["python", "-m", "scheduler.run_realtime", "--loop"]
```

---

## 6. Sécurité et conformité

- **Pas de credentials en dur** — toujours via variables d'environnement
- **Audit complet** — chaque notification (y compris simulée) est tracée
  dans la table `notifications` avec horodatage, statut, et erreur éventuelle
- **Aucune donnée personnelle dans GDELT** — données publiques exclusivement
- **Auditabilité** — règles de notification versionnées dans Git
- **Fail-safe** — toute panne provider n'interrompt jamais le scheduler

---

## 7. Tests

Le module temps réel est couvert par **24 tests unitaires** dans
`tests/test_realtime.py`, organisés en 6 classes :

- `TestAlertHistory`        — persistance SQLite
- `TestAlertTransitionLogic` — calcul des transitions
- `TestConsoleProvider`     — provider console
- `TestEmailProvider`       — provider email (mode simulé)
- `TestWebhookProvider`     — provider webhook (mode simulé)
- `TestNotifier`            — routage par règles
- `TestTemplates`           — rendu HTML des bulletins

Tous les tests utilisent des bases SQLite temporaires (`tmp_path` pytest)
et le mode simulé des providers — aucun envoi réel, aucune dépendance externe.

Lancement :
```bash
pytest tests/test_realtime.py -v
```

---

## 8. Limites et prochaines étapes

### Limites assumées
- **GDELT a un biais anglophone** documenté — médias francophones locaux du
  Bénin sous-représentés. Mitigation : ajouter une source francophone
  complémentaire (à câbler comme un second `Streamer`).
- **Pas d'authentification multi-utilisateurs** sur la page de surveillance.
  En production : déployer derrière un reverse proxy avec auth (Nginx + LDAP
  étatique, ou Streamlit-Auth).
- **SMS et appels téléphoniques** : interfaces définies (Twilio / Africa's
  Talking), à câbler avec un fournisseur et un budget opérationnel.

### Prochaines étapes (post-finale)
1. **Câbler le provider SMS** (Africa's Talking) pour les alertes
   ORANGE/ROUGE aux préfets
2. **Authentification utilisateurs** sur le dashboard via OAuth ou LDAP étatique
3. **Source francophone complémentaire** (presse béninoise + RFI + Reuters FR)
4. **Persistance Postgres** au lieu de SQLite pour un déploiement multi-instances
5. **Pages préfectorales dédiées** — un dashboard par département frontalier

---

## 9. Glossaire

| Terme | Définition |
|---|---|
| **Tick** | Un cycle complet d'évaluation : Streamer → Engine → Notifier |
| **Transition** | Changement de niveau d'alerte (ex. VERT → JAUNE) |
| **Escalation** | Transition vers un niveau plus grave |
| **De-escalation** | Transition vers un niveau moins grave (retour au calme) |
| **Provider** | Implémentation d'un canal de notification (email, SMS, webhook) |
| **Recipient** | Destinataire d'une notification — défini dans recipients.yaml |
| **Rule** | Règle de routage — quel rôle reçoit quel niveau d'alerte |
| **Simulate mode** | Mode où aucun envoi réel n'est effectué (test d'intégration) |

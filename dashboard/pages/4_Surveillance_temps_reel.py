"""
BeninSentinel — Surveillance temps réel (tableau de bord opérationnel).

Cette page expose l'état courant et l'historique du système d'alerte
temps réel à destination de l'opérateur du système (typiquement l'analyste
de la cellule de veille ANSSI-Bénin / Ministère de l'Intérieur).

Ce qu'elle montre :
    1. État courant — niveau d'alerte du dernier tick + score composite
    2. Historique des transitions — journal chronologique des changements
    3. Journal des notifications — audit complet des bulletins envoyés
    4. Statistiques d'exploitation — fiabilité du système au quotidien

Le contenu est lu uniquement depuis la base SQLite (data/sentinel_history.db)
— aucun appel API, aucun rechargement de données lourdes. La page reste
ultra-rapide même si le scheduler tourne en parallèle.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import plotly.express as px

from pipeline.realtime.history import AlertHistory


# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Surveillance temps réel · BeninSentinel",
    page_icon="BJ",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Reprendre la même charte visuelle que les autres pages
ALERT_COLORS = {
    "VERT":   "#10b981",
    "JAUNE":  "#f59e0b",
    "ORANGE": "#f97316",
    "ROUGE":  "#dc2626",
}
ALERT_BG = {
    "VERT":   "#ecfdf5",
    "JAUNE":  "#fffbeb",
    "ORANGE": "#fff7ed",
    "ROUGE":  "#fef2f2",
}

st.markdown("""
<style>
.page-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    color: white; padding: 1.8rem 2.2rem; border-radius: 14px;
    margin-bottom: 1.4rem;
}
.page-header .label {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.16em;
    opacity: 0.75;
}
.page-header h1 { margin: 0.3rem 0 0; font-size: 1.85rem; font-weight: 800; }
.page-header p  { margin: 0.45rem 0 0; opacity: 0.88; font-size: 0.95rem; line-height: 1.55; }

.alert-card {
    border-radius: 14px; padding: 1.4rem 1.6rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    border-left: 5px solid;
}
.alert-card .level-label {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em;
    font-weight: 700; opacity: 0.7;
}
.alert-card .level-value {
    font-size: 2.4rem; font-weight: 800; line-height: 1.05; margin-top: 0.3rem;
}
.alert-card .score-line {
    font-size: 0.95rem; color: #374151; margin-top: 0.45rem;
}

.section-title {
    font-size: 1.1rem; font-weight: 700; color: #111827;
    border-left: 4px solid #1e3a8a; padding-left: 0.75rem;
    margin: 1.8rem 0 0.9rem;
}
.empty-state {
    background:#f9fafb; border:1px dashed #d1d5db; border-radius:10px;
    padding:1.4rem 1.6rem; color:#6b7280; font-size:0.92rem; line-height:1.6;
}
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────

st.markdown("""
<div class="page-header">
    <div class="label">BeninSentinel · Centre opérationnel</div>
    <h1>Surveillance temps réel</h1>
    <p>État courant du système d'alerte, historique des transitions et journal
    d'audit complet des notifications envoyées. À destination de l'opérateur de
    la cellule de veille (ANSSI-Bénin, Ministère de l'Intérieur).</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# CHARGEMENT DE L'HISTORIQUE
# ─────────────────────────────────────────────────────────────────

db_path = ROOT / "data" / "sentinel_history.db"
if not db_path.exists():
    st.markdown(f"""
    <div class="empty-state">
    <b>Aucune base d'historique trouvée.</b><br>
    Lancez d'abord le scheduler temps réel pour créer la base et alimenter
    l'historique :<br><br>
    <code>SENTINEL_PREFER_LOCAL=1 SENTINEL_SIMULATE=1 python -m scheduler.run_realtime --once</code>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

history = AlertHistory(db_path)
stats = history.stats()

if stats["n_states"] == 0:
    st.markdown("""
    <div class="empty-state">
    Base d'historique présente mais vide. Lancer un tick :
    <code>python -m scheduler.run_realtime --once</code>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ─────────────────────────────────────────────────────────────────
# 1 · ÉTAT COURANT
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">État courant — dernier tick enregistré</div>',
            unsafe_allow_html=True)

last = history.last_state()
level = last["alert_level"]
score = last["risk_score"]
color = ALERT_COLORS[level]
bg    = ALERT_BG[level]

col_a, col_b, col_c, col_d = st.columns([3, 2, 2, 2])

with col_a:
    st.markdown(f"""
    <div class="alert-card" style="background:{bg}; border-left-color:{color};">
        <div class="level-label" style="color:{color};">
            Niveau d'alerte au {last['measured_at']}
        </div>
        <div class="level-value" style="color:{color};">{level}</div>
        <div class="score-line">
            Score composite : <b>{score:.3f}</b> / 1,000 · Date analysée : {last['target_date']}
        </div>
    </div>
    """, unsafe_allow_html=True)

with col_b:
    st.metric("États enregistrés", f"{stats['n_states']:,}",
              help="Nombre total de ticks d'évaluation enregistrés en base")
with col_c:
    st.metric("Transitions détectées", f"{stats['n_transitions']:,}",
              help="Nombre de changements de niveau d'alerte historisés")
with col_d:
    st.metric("Notifications envoyées", f"{stats['n_notifications']:,}",
              help="Bulletins distribués via tous canaux (audit complet)")


# ─────────────────────────────────────────────────────────────────
# 2 · HISTORIQUE DES TRANSITIONS
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">Journal des transitions d\'alerte</div>',
            unsafe_allow_html=True)
st.caption(
    "Chaque ligne correspond à un changement de niveau d'alerte détecté par "
    "le système — c'est le déclencheur des notifications automatiques."
)

transitions = history.recent_transitions(limit=50)
if transitions:
    tr_df = pd.DataFrame(transitions)
    show_cols = ["detected_at", "target_date", "from_level", "to_level",
                 "from_score", "to_score", "direction", "notified"]
    tr_show = tr_df[show_cols].copy()
    tr_show["notified"] = tr_show["notified"].map({1: "Oui", 0: "Non"})
    tr_show.columns = ["Détectée le", "Date analysée", "Niveau avant",
                       "Niveau après", "Score avant", "Score après",
                       "Direction", "Notifiée"]
    st.dataframe(tr_show, use_container_width=True, hide_index=True,
                 column_config={
                     "Score avant": st.column_config.NumberColumn(format="%.3f"),
                     "Score après": st.column_config.NumberColumn(format="%.3f"),
                 })
else:
    st.markdown(
        '<div class="empty-state">Aucune transition détectée pour le moment '
        '(le système est en mode VERT stable ou vient juste de démarrer).</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────
# 3 · ÉVOLUTION DU SCORE — graphique chronologique
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">Évolution du score de risque dans le temps</div>',
            unsafe_allow_html=True)

states = history.recent_states(limit=500)
if len(states) >= 2:
    sdf = pd.DataFrame(states).sort_values("measured_at")
    sdf["measured_at"] = pd.to_datetime(sdf["measured_at"])
    sdf["color"] = sdf["alert_level"].map(ALERT_COLORS)

    fig = px.scatter(
        sdf, x="measured_at", y="risk_score",
        color="alert_level",
        color_discrete_map=ALERT_COLORS,
        category_orders={"alert_level": ["VERT", "JAUNE", "ORANGE", "ROUGE"]},
        hover_data={"target_date": True, "risk_score": ":.3f"},
        labels={"measured_at": "", "risk_score": "Score composite",
                "alert_level": "Niveau"},
    )
    fig.add_hline(y=0.40, line_dash="dot", line_color=ALERT_COLORS["JAUNE"],
                  annotation_text="Seuil JAUNE", annotation_position="right")
    fig.add_hline(y=0.60, line_dash="dot", line_color=ALERT_COLORS["ORANGE"],
                  annotation_text="Seuil ORANGE", annotation_position="right")
    fig.add_hline(y=0.80, line_dash="dot", line_color=ALERT_COLORS["ROUGE"],
                  annotation_text="Seuil ROUGE", annotation_position="right")
    fig.update_layout(
        height=380, plot_bgcolor="white", paper_bgcolor="white",
        margin=dict(t=20, b=10, l=10, r=10),
        yaxis=dict(range=[0, 1.05], gridcolor="#f0f0f0"),
        xaxis=dict(gridcolor="#f0f0f0"),
        legend=dict(orientation="h", y=-0.18),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
else:
    st.markdown(
        '<div class="empty-state">Pas encore assez d\'évaluations pour tracer '
        'une évolution (au moins 2 ticks nécessaires).</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────
# 4 · JOURNAL D'AUDIT DES NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">Journal d\'audit — notifications envoyées</div>',
            unsafe_allow_html=True)
st.caption(
    "Trace complète des bulletins distribués — qui a été notifié, quand, "
    "par quel canal, avec quel statut (SUCCESS / FAILED / SIMULATED). "
    "Exigence d'auditabilité pour un outil d'aide à la décision publique."
)

notifications = history.recent_notifications(limit=100)
if notifications:
    n_df = pd.DataFrame(notifications)
    show_cols = ["sent_at", "recipient_name", "recipient_role",
                 "channel", "alert_level", "status", "error_message"]
    n_show = n_df[show_cols].copy()
    n_show.columns = ["Envoyée le", "Destinataire", "Rôle", "Canal",
                      "Niveau", "Statut", "Erreur éventuelle"]
    st.dataframe(n_show, use_container_width=True, hide_index=True)
else:
    st.markdown(
        '<div class="empty-state">Aucune notification envoyée pour le moment.</div>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────
# 5 · INSTRUCTIONS OPÉRATIONNELLES
# ─────────────────────────────────────────────────────────────────

with st.expander("Comment exploiter ce centre opérationnel ?"):
    st.markdown("""
**Cette page est conçue pour l'opérateur du système temps réel** (cellule de veille
ANSSI-Bénin ou équivalent). Elle est mise à jour à chaque tick du scheduler.

**Pour lancer un cycle ponctuel** :
```bash
SENTINEL_PREFER_LOCAL=1 SENTINEL_SIMULATE=1 \\
    python -m scheduler.run_realtime --once
```

**Pour lancer la surveillance continue** (toutes les 60 minutes par défaut) :
```bash
SENTINEL_PREFER_LOCAL=1 python -m scheduler.run_realtime --loop --interval-minutes 60
```

**Pour activer l'envoi réel des emails** (à faire uniquement en production) :
```bash
export SENTINEL_SMTP_HOST=smtp.example.com
export SENTINEL_SMTP_USER=alerte@example.bj
export SENTINEL_SMTP_PASSWORD=*****
python -m scheduler.run_realtime --loop
```

**Pour modifier les destinataires ou les règles** :
- Éditer `config/recipients.yaml` (annuaire)
- Éditer `config/notification_rules.yaml` (règles de routage)
- Les fichiers sont versionnés dans Git — toute modification est auditable.

**Architecture complète** : voir `pipeline/realtime/` (modules) et
`reports/REALTIME_ARCHITECTURE.md` (documentation détaillée).
""")


# ─────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<center style='color:#9ca3af; font-size:0.8rem;'>"
    "BeninSentinel · Surveillance temps réel · IROKO Analytics · "
    "Aligné PAG 2021-2026 · Base d'historique : "
    f"<code>{db_path.relative_to(ROOT)}</code>"
    "</center>",
    unsafe_allow_html=True,
)

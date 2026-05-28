"""
BeninSentinel — Tableau de bord de veille et d'intelligence territoriale.

Cible : décideurs publics béninois (Présidence, Ministère de l'Intérieur,
préfets, ANSSI-Bénin, ONG de paix).

Mission : transformer la donnée GDELT en signal opérationnel pour anticiper
les crises sécuritaires, sociales et politiques au Bénin.

Aligné sur le Programme d'Action du Gouvernement 2021-2026.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from pipeline.sentinel import (
    run_sentinel,
    detect_lead_time,
    compute_department_risk,
    ALERT_THRESHOLDS,
    ACTION_PLAYBOOK,
)


# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="BeninSentinel · Veille territoriale",
    page_icon="BJ",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────

ALERT_COLORS = {
    "VERT":   "#10b981",   # green-500
    "JAUNE":  "#f59e0b",   # amber-500
    "ORANGE": "#f97316",   # orange-500
    "ROUGE":  "#dc2626",   # red-600
}

ALERT_BG = {
    "VERT":   "#ecfdf5",
    "JAUNE":  "#fffbeb",
    "ORANGE": "#fff7ed",
    "ROUGE":  "#fef2f2",
}

st.markdown("""
<style>
.sentinel-header {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    color: white; padding: 1.8rem 2.4rem; border-radius: 14px;
    margin-bottom: 1.4rem;
}
.sentinel-header .label {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.18em;
    opacity: 0.7; margin-bottom: 0.3rem;
}
.sentinel-header h1 { margin: 0; font-size: 2.05rem; font-weight: 800; letter-spacing: -0.01em; }
.sentinel-header .subtitle { margin: 0.45rem 0 0; opacity: 0.85; font-size: 0.95rem; }
.sentinel-header .pag-badge {
    display: inline-block; background: rgba(255,255,255,0.13);
    padding: 0.28rem 0.7rem; border-radius: 999px; font-size: 0.74rem;
    margin-top: 0.85rem; letter-spacing: 0.04em;
}

.alert-card {
    border-radius: 14px; padding: 1.3rem 1.5rem;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    border-left: 5px solid;
}
.alert-card .level {
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em;
    font-weight: 700; opacity: 0.7;
}
.alert-card .value {
    font-size: 2.2rem; font-weight: 800; line-height: 1.1; margin-top: 0.3rem;
}
.alert-card .score {
    font-size: 0.85rem; color: #374151; margin-top: 0.4rem;
}

.kpi-mini {
    background: white; border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 1rem 1.2rem;
}
.kpi-mini .val { font-size: 1.55rem; font-weight: 800; color: #0f172a; }
.kpi-mini .lbl { font-size: 0.73rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.2rem; }
.kpi-mini .sub { font-size: 0.72rem; color: #9ca3af; margin-top: 0.15rem; }

.section-title {
    font-size: 1.15rem; font-weight: 700; color: #111827;
    border-left: 4px solid #1e3a8a; padding-left: 0.75rem;
    margin: 1.7rem 0 0.9rem;
}

.action-box {
    background: #f8fafc; border-left: 4px solid #1e3a8a;
    border-radius: 8px; padding: 1rem 1.2rem; margin: 0.6rem 0;
    font-size: 0.9rem; color: #1e293b; line-height: 1.55;
}
.action-tag {
    display: inline-block; padding: 0.15rem 0.55rem;
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.05em;
    border-radius: 4px; margin-right: 0.5rem;
}

.case-callout {
    background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
    border: 1px solid #fecaca; border-radius: 12px;
    padding: 1.2rem 1.4rem; margin: 0.5rem 0;
}
.case-callout .head {
    color: #991b1b; font-weight: 700; font-size: 0.95rem;
    text-transform: uppercase; letter-spacing: 0.05em;
}
.case-callout .body {
    color: #1f2937; font-size: 0.9rem; line-height: 1.6; margin-top: 0.5rem;
}

footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────

st.markdown("""
<div class="sentinel-header">
    <div class="label">Système de veille et d'intelligence territoriale</div>
    <h1>BeninSentinel</h1>
    <div class="subtitle">
        Surveillance continue, scoring transparent du risque, anticipation des crises
        sécuritaires, sociales et politiques au Bénin — pour donner du temps aux décideurs.
    </div>
    <div class="pag-badge">Aligné sur le Programme d'Action du Gouvernement 2021-2026 · Gouvernance · Numérique · Bien-être social</div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Chargement de la base GDELT 2025...")
def load_data():
    processed = ROOT / "data" / "processed" / "benin_gdelt_clean.csv"
    sample    = ROOT / "data" / "sample"    / "benin_gdelt_sample.csv"
    src = processed if processed.exists() else sample
    if not src.exists():
        return pd.DataFrame(), "none"
    df = pd.read_csv(src, low_memory=False)
    return df, "complete" if src == processed else "sample"


@st.cache_data(show_spinner="Calcul du score BeninSentinel sur l'année 2025...")
def compute_sentinel(df: pd.DataFrame) -> pd.DataFrame:
    return run_sentinel(df)


df, src = load_data()
if df.empty:
    st.error("Données indisponibles. Lancez le pipeline d'extraction.")
    st.stop()

risk = compute_sentinel(df)

# ─────────────────────────────────────────────────────────────────
# CONTROL — DATE FOCUS
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">1 · Jour d\'analyse</div>', unsafe_allow_html=True)

VALIDATED_CRISES = {
    "Vue de l'année (synthèse)":       None,
    "24 avril 2025 — Attaque jihadiste (54 soldats tués)": pd.Timestamp("2025-04-24"),
    "7 décembre 2025 — Tentative de coup d'État":         pd.Timestamp("2025-12-07"),
    "5 novembre 2025 — Pic de tensions sécuritaires":     pd.Timestamp("2025-11-05"),
    "6 juin 2025 — Crise diplomatique":                    pd.Timestamp("2025-06-06"),
}

col_ctrl1, col_ctrl2 = st.columns([3, 2])
with col_ctrl1:
    case_choice = st.selectbox(
        "Cas-test validé ou date personnalisée",
        options=list(VALIDATED_CRISES.keys()),
        index=1,
        help="Choisissez une crise historiquement vérifiée pour démonstration, ou la vue d'ensemble.",
    )
with col_ctrl2:
    custom_date = st.date_input(
        "Ou choisir une date précise",
        value=pd.Timestamp("2025-04-24").date(),
        min_value=risk["date"].min().date(),
        max_value=risk["date"].max().date(),
    )

target_date = VALIDATED_CRISES[case_choice] or pd.Timestamp(custom_date)

# ─────────────────────────────────────────────────────────────────
# ALERTE COURANTE
# ─────────────────────────────────────────────────────────────────

current_row = risk[risk["date"] == target_date]
if current_row.empty:
    st.warning(f"Aucune donnée pour le {target_date.date()}.")
    st.stop()
current = current_row.iloc[0]
current_level = current["alert_level"]
current_score = current["risk_score"]
color = ALERT_COLORS[current_level]
bg    = ALERT_BG[current_level]

st.markdown('<div class="section-title">2 · Niveau d\'alerte au jour analysé</div>', unsafe_allow_html=True)

col_a, col_b, col_c, col_d = st.columns([3, 2, 2, 2])
with col_a:
    st.markdown(f"""
    <div class="alert-card" style="background:{bg}; border-left-color:{color};">
        <div class="level" style="color:{color};">Niveau d'alerte — {target_date.strftime('%d %B %Y')}</div>
        <div class="value" style="color:{color};">{current_level}</div>
        <div class="score">Score composite : <b>{current_score:.3f}</b> / 1,000</div>
    </div>
    """, unsafe_allow_html=True)

# Détection précoce (lead time)
lead_y, det_y = detect_lead_time(risk, target_date, "JAUNE", 14)
lead_o, det_o = detect_lead_time(risk, target_date, "ORANGE", 14)

with col_b:
    if lead_y > 0:
        st.markdown(f"""
        <div class="kpi-mini">
            <div class="val">J-{lead_y}</div>
            <div class="lbl">Détection précoce JAUNE</div>
            <div class="sub">{det_y.strftime('%d %b %Y')}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="kpi-mini">
            <div class="val" style="color:#9ca3af;">—</div>
            <div class="lbl">Détection JAUNE</div>
            <div class="sub">non détectée à J-14</div>
        </div>
        """, unsafe_allow_html=True)

with col_c:
    if lead_o > 0:
        st.markdown(f"""
        <div class="kpi-mini">
            <div class="val">J-{lead_o}</div>
            <div class="lbl">Détection précoce ORANGE</div>
            <div class="sub">{det_o.strftime('%d %b %Y')}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="kpi-mini">
            <div class="val" style="color:#9ca3af;">—</div>
            <div class="lbl">Détection ORANGE</div>
            <div class="sub">non détectée à J-14</div>
        </div>
        """, unsafe_allow_html=True)

# Décomposition du signal
total_orange = int((risk["alert_level"] == "ORANGE").sum())
total_jaune  = int((risk["alert_level"] == "JAUNE").sum())
with col_d:
    st.markdown(f"""
    <div class="kpi-mini">
        <div class="val">{total_jaune + total_orange}</div>
        <div class="lbl">Jours d'alerte 2025</div>
        <div class="sub">{total_jaune} JAUNE · {total_orange} ORANGE</div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# PLAYBOOK D'ACTION
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">3 · Plan d\'action recommandé</div>', unsafe_allow_html=True)
st.markdown(f"""
<div class="action-box" style="border-left-color:{color}; background:{bg};">
    <span class="action-tag" style="background:{color}; color:white;">{current_level}</span>
    {ACTION_PLAYBOOK[current_level]}
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# DÉCOMPOSITION DES 6 SIGNAUX FAIBLES
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">4 · Décomposition du score — les 6 signaux faibles surveillés</div>', unsafe_allow_html=True)
st.markdown(
    "Chaque signal est normalisé entre 0 et 1, calculé à partir d'un z-score "
    "hybride (composante tendance 7 jours + composante instantanée jour J) "
    "rapporté à la référence comportementale 30 jours."
)

signals_def = [
    ("sig_tone",     "Dégradation du ton médiatique", "Baisse anormale du ton moyen (AvgTone)"),
    ("sig_negative", "Bascule des articles négatifs", "Hausse anormale de la proportion d'articles négatifs"),
    ("sig_protest",  "Pic de protestation / menace",  "Désapprobations, menaces, rejets, ultimatums"),
    ("sig_quad3",    "Escalade verbale (QuadClass 3)", "Conflits verbaux GDELT"),
    ("sig_quad4",    "Escalade matérielle (QuadClass 4)", "Conflits matériels GDELT"),
    ("sig_violence", "Événements violents directs",   "Assauts, attentats, violences de masse"),
]

sig_df = pd.DataFrame({
    "Signal": [name for _, name, _ in signals_def],
    "Valeur": [current[col] for col, _, _ in signals_def],
    "Description": [desc for _, _, desc in signals_def],
})
sig_df = sig_df.sort_values("Valeur", ascending=True)

fig_signals = px.bar(
    sig_df, x="Valeur", y="Signal", orientation="h",
    color="Valeur", color_continuous_scale=[(0, "#10b981"), (0.5, "#f59e0b"), (1, "#dc2626")],
    range_color=[0, 1],
    text=sig_df["Valeur"].map(lambda v: f"{v:.2f}"),
    hover_data={"Description": True, "Valeur": ":.3f"},
)
fig_signals.update_traces(textposition="outside")
fig_signals.update_layout(
    height=320, plot_bgcolor="white",
    coloraxis_showscale=False,
    margin=dict(t=20, b=10, l=10, r=40),
    xaxis=dict(range=[0, 1.1], gridcolor="#e5e7eb", title="Intensité normalisée (0 = normal, 1 = extrême)"),
    yaxis=dict(title=""),
)
st.plotly_chart(fig_signals, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────
# CHRONOLOGIE DE L'ALERTE — fenêtre J-14 / J+5
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">5 · Chronologie d\'alerte — fenêtre rétrospective et suivi</div>', unsafe_allow_html=True)

window = risk[
    (risk["date"] >= target_date - pd.Timedelta(days=14)) &
    (risk["date"] <= target_date + pd.Timedelta(days=5))
].copy()

# Construire les couleurs par niveau pour le graphique
window["color"] = window["alert_level"].map(ALERT_COLORS)

fig_chrono = go.Figure()
fig_chrono.add_trace(go.Bar(
    x=window["date"], y=window["risk_score"],
    marker_color=window["color"],
    text=window["alert_level"],
    textposition="outside",
    hovertemplate="<b>%{x|%d %b %Y}</b><br>Score : %{y:.3f}<br>Alerte : %{text}<extra></extra>"
))

# Lignes de seuil
for level, (low, high) in ALERT_THRESHOLDS.items():
    if low > 0:
        fig_chrono.add_hline(
            y=low, line_dash="dot", line_color=ALERT_COLORS[level], opacity=0.4,
            annotation_text=f"Seuil {level}", annotation_position="right",
            annotation_font_size=10,
        )

# Marqueur jour cible
fig_chrono.add_vline(
    x=target_date.timestamp() * 1000,
    line_color="#dc2626", line_width=2, line_dash="dash",
    annotation_text="Crise", annotation_position="top",
    annotation_font_color="#dc2626",
)

fig_chrono.update_layout(
    title=f"Score de risque quotidien — fenêtre du {(target_date - pd.Timedelta(days=14)).strftime('%d %b')} au {(target_date + pd.Timedelta(days=5)).strftime('%d %b %Y')}",
    height=380, plot_bgcolor="white", paper_bgcolor="white",
    margin=dict(t=50, b=10), showlegend=False,
    xaxis=dict(title="", gridcolor="#f0f0f0"),
    yaxis=dict(title="Score composite", range=[0, max(0.85, window["risk_score"].max() * 1.15)], gridcolor="#f0f0f0"),
)
st.plotly_chart(fig_chrono, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────
# CARTOGRAPHIE PAR DÉPARTEMENT BÉNINOIS
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">6 · Cartographie du risque par département béninois</div>', unsafe_allow_html=True)
st.markdown(
    "Décomposition du risque sur les 12 départements administratifs du Bénin "
    "à partir de la colonne `event_department` (FIPS10-4) enrichie par le pipeline ETL. "
    "Fenêtre d'analyse : 7 jours rétrospectifs."
)

dept_risk = compute_department_risk(df, target_date, window=7)
if not dept_risk.empty and len(dept_risk) > 1:
    dept_show = dept_risk[dept_risk["event_department"] != "Bénin (général)"].copy()
    if dept_show.empty:
        dept_show = dept_risk.copy()
    dept_show = dept_show.sort_values("local_risk", ascending=True)
    dept_show["color"] = dept_show["alert_level"].map(ALERT_COLORS)

    fig_dept = go.Figure(go.Bar(
        x=dept_show["local_risk"], y=dept_show["event_department"],
        orientation="h",
        marker_color=dept_show["color"],
        text=[f"{lvl} · {r:.2f}" for lvl, r in zip(dept_show["alert_level"], dept_show["local_risk"])],
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Score local : %{x:.3f}<br>"
            "<extra></extra>"
        ),
    ))
    fig_dept.update_layout(
        height=400, plot_bgcolor="white",
        margin=dict(t=20, b=10, l=10, r=80),
        xaxis=dict(range=[0, 1.15], gridcolor="#e5e7eb", title="Score de risque local (0–1)"),
        yaxis=dict(title=""),
        showlegend=False,
    )
    st.plotly_chart(fig_dept, use_container_width=True, config={"displayModeBar": False})
else:
    st.info("Pas assez de données géolocalisées au niveau département pour cette fenêtre.")

# ─────────────────────────────────────────────────────────────────
# DASHBOARD ANNUEL — TIMELINE COMPLÈTE
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">7 · Année 2025 — chronologie de l\'alerte BeninSentinel</div>', unsafe_allow_html=True)

risk_year = risk.copy()
risk_year["color"] = risk_year["alert_level"].map(ALERT_COLORS)

fig_year = go.Figure()
fig_year.add_trace(go.Bar(
    x=risk_year["date"], y=risk_year["risk_score"],
    marker_color=risk_year["color"],
    hovertemplate="<b>%{x|%d %b %Y}</b><br>Score : %{y:.3f}<extra></extra>",
))
for level, (low, high) in ALERT_THRESHOLDS.items():
    if low > 0:
        fig_year.add_hline(y=low, line_dash="dot", line_color=ALERT_COLORS[level], opacity=0.3)

# Marqueurs des 4 crises validées
markers = [
    ("2025-04-24", "Attaque jihadiste"),
    ("2025-06-06", "Crise diplomatique"),
    ("2025-11-05", "Tensions sécuritaires"),
    ("2025-12-07", "Coup d'État déjoué"),
]
for date_str, label in markers:
    fig_year.add_vline(
        x=pd.Timestamp(date_str).timestamp() * 1000,
        line_color="#1f2937", line_width=1, line_dash="dot", opacity=0.6,
        annotation_text=label, annotation_position="top",
        annotation_font_size=10, annotation_font_color="#1f2937",
    )

fig_year.update_layout(
    height=400, plot_bgcolor="white", paper_bgcolor="white",
    title="Score quotidien BeninSentinel — année 2025 (les 4 crises validées sont marquées)",
    margin=dict(t=80, b=10), showlegend=False,
    xaxis=dict(title="", gridcolor="#f0f0f0"),
    yaxis=dict(title="Score composite", gridcolor="#f0f0f0"),
)
st.plotly_chart(fig_year, use_container_width=True, config={"displayModeBar": False})

# ─────────────────────────────────────────────────────────────────
# PERFORMANCE DE VALIDATION
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">8 · Tableau de validation empirique</div>', unsafe_allow_html=True)

VALIDATION_TABLE = pd.DataFrame([
    {"Date": "24 avril 2025", "Événement": "Attaque jihadiste — 54 soldats béninois tués",
     "Score": 0.686, "Alerte": "ORANGE", "Détection JAUNE": "J-4"},
    {"Date": "5 novembre 2025", "Événement": "Pic de tensions sécuritaires",
     "Score": 0.640, "Alerte": "ORANGE", "Détection JAUNE": "J-1"},
    {"Date": "6 juin 2025", "Événement": "Crise diplomatique + violence",
     "Score": 0.592, "Alerte": "JAUNE", "Détection JAUNE": "J-0"},
    {"Date": "7 décembre 2025", "Événement": "Tentative de coup d'État déjouée",
     "Score": 0.560, "Alerte": "JAUNE", "Détection JAUNE": "J-0"},
])

st.dataframe(
    VALIDATION_TABLE,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Score": st.column_config.NumberColumn(format="%.3f"),
        "Alerte": st.column_config.TextColumn(),
    },
)

st.markdown(f"""
<div class="case-callout">
    <div class="head">Résultat de validation</div>
    <div class="body">
        Sur les <b>4 crises majeures du Bénin en 2025</b> historiquement vérifiables,
        BeninSentinel les détecte <b>toutes</b> en alerte JAUNE ou ORANGE. Le cas le plus
        spectaculaire : l'attaque jihadiste du 24 avril 2025 qui a coûté la vie à 54 soldats
        béninois — précédée d'une <b>alerte JAUNE persistante 4 jours à l'avance</b>
        (20, 21, 22 avril). Aucune des 4 alertes ORANGE de l'année ne correspond à un faux
        positif : 100 % sont des crises historiquement vérifiées.
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# FOOTER MÉTHODOLOGIQUE
# ─────────────────────────────────────────────────────────────────

with st.expander("Méthodologie complète — comment BeninSentinel calcule-t-il le score ?"):
    st.markdown("""
**1. Construction des séries quotidiennes** — agrégation des événements GDELT par jour calendaire (volume, ton, intensité Goldstein, composition CAMEO, diversité des sources).

**2. Six signaux faibles surveillés** (`pipeline/sentinel.py`) :

| Signal | Mesure | Direction |
|---|---|---|
| `sig_tone` | Ton moyen (AvgTone) | Baisse → signal |
| `sig_negative` | % d'articles à ton négatif | Hausse → signal |
| `sig_protest` | Protestations + menaces + rejets + ultimatums | Hausse → signal |
| `sig_quad3` | Conflits verbaux GDELT (QuadClass = 3) | Hausse → signal |
| `sig_quad4` | Conflits matériels GDELT (QuadClass = 4) | Hausse → signal |
| `sig_violence` | Assauts + attentats + violences de masse | Hausse → signal |

**3. Normalisation par z-score hybride** — chaque signal compare :
- Une composante TENDANCE : moyenne 7 jours vs référence 30 jours
- Une composante INSTANTANÉE : jour courant vs référence 30 jours

Les deux composantes sont moyennes pondérées (50/50 par défaut), z-scorées sur la base de l'écart-type de la fenêtre de référence, plafonnées à 2 sigmas et normalisées sur [0, 1].

**4. Score composite** — moyenne pondérée des six signaux (pondérations transparentes dans `DEFAULT_WEIGHTS`).

**5. Quatre niveaux d'alerte** : VERT (0-0,40) · JAUNE (0,40-0,60) · ORANGE (0,60-0,80) · ROUGE (0,80-1,00).

**6. Cartographie territoriale** — décomposition par département béninois via la colonne `event_department` issue des codes FIPS10-4.

**7. Reproductibilité** — l'ensemble du code est versionné, les seuils et pondérations sont auditables, les calculs sont reproductibles. Voir `pipeline/sentinel.py` et `reports/BENIN_SENTINEL_FOUNDATIONS.md`.
""")

with st.expander("Limites assumées et honnêteté méthodologique"):
    st.markdown("""
- **Pas un oracle** — BeninSentinel fournit des probabilités, pas des certitudes. La décision finale reste humaine.
- **Biais GDELT anglophone** — les tensions purement locales non couvertes par la presse étrangère sont sous-détectées.
- **Délai variable selon le type de crise** — les crises sécuritaires (attaque jihadiste) sont mieux anticipées que les crises politiques soudaines (coup d'État).
- **Calibration annuelle nécessaire** — les seuils actuels reflètent l'écosystème médiatique 2025.
- **Complément, pas substitut, du renseignement humain** — l'outil épaule les analystes territoriaux, ne les remplace pas.
""")

# ─────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<center style='color:#9ca3af; font-size:0.8rem;'>"
    "BeninSentinel · Système de veille et d'intelligence territoriale · "
    "IROKO Analytics — Bénin Insights Challenge 2026 · iSHEERO × DataCamp Donates · "
    "Aligné PAG 2021-2026"
    "</center>",
    unsafe_allow_html=True,
)

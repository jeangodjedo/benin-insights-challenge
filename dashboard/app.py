# dashboard/app.py
"""
Bénin Insights Challenge 2026 — Interactive Dashboard
iSHEERO × DataCamp Donates — Équipe 7

Analytical questions answered:
    Q1 — When does the world talk about Benin?
    Q2 — Is the media tone positive, neutral or negative?
    Q3 — How fast does coverage of a Beninese event spread globally?
    Q4 — Do media sources change during crisis periods?
    Q5 — Is Benin an actor or a bystander in international events?

Deployment:
    Local  : streamlit run dashboard/app.py
    Cloud  : https://share.streamlit.io — connect repo, point to dashboard/app.py

Author  : Team 7 — Bénin Insights Challenge 2026
Version : 1.0
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Bénin Insights 2026",
    page_icon="🇧🇯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

MONTH_LABELS = {
    1: "Janvier",  2: "Février", 3: "Mars",     4: "Avril",
    5: "Mai",      6: "Juin",    7: "Juillet",   8: "Août",
    9: "Septembre",10: "Octobre",11: "Novembre", 12: "Décembre"
}

ROLE_COLORS = {
    "Acteur":     "#1a56db",
    "Spectateur": "#7e3af2",
    "Mixte":      "#f59e0b",
    "Contexte":   "#6b7280"
}

TONE_COLORS = {
    "Positif": "#00b894",
    "Neutre":  "#fdcb6e",
    "Négatif": "#d63031",
    "Inconnu": "#b2bec3"
}

CHART_CONFIG = {"displayModeBar": False}

# ─────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.dashboard-header {
    background: linear-gradient(135deg, #1a56db 0%, #7e3af2 100%);
    color: white; padding: 2rem 2.5rem; border-radius: 12px; margin-bottom: 1.5rem;
}
.dashboard-header h1 { margin: 0; font-size: 2rem; font-weight: 700; }
.dashboard-header p  { margin: 0.4rem 0 0; opacity: 0.88; font-size: 1rem; }

.kpi-card {
    background: white; border: 1px solid #e5e7eb; border-radius: 10px;
    padding: 1.2rem 1.4rem; text-align: center;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.kpi-value { font-size: 1.9rem; font-weight: 700; color: #1a56db; line-height: 1.1; }
.kpi-label { font-size: 0.78rem; color: #6b7280; margin-top: 0.3rem;
             text-transform: uppercase; letter-spacing: 0.05em; }
.kpi-sub   { font-size: 0.72rem; color: #9ca3af; margin-top: 0.2rem; }

.section-title {
    font-size: 1.15rem; font-weight: 700; color: #111827;
    border-left: 4px solid #1a56db; padding-left: 0.75rem;
    margin: 1.6rem 0 0.8rem;
}
.insight-box {
    background: #f8fafc; border-left: 4px solid #7e3af2;
    border-radius: 6px; padding: 0.9rem 1.1rem; margin: 0.5rem 0;
    font-size: 0.88rem; color: #374151; line-height: 1.5;
}
.insight-num { font-weight: 700; color: #7e3af2; }
.sample-banner {
    background: #fffbeb; border: 1px solid #f59e0b; border-radius: 8px;
    padding: 0.6rem 1rem; font-size: 0.83rem; color: #92400e; margin-bottom: 1rem;
}
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner="Chargement des données GDELT...")
def load_data():
    try:
        from pipeline.config import PROCESSED_DIR, SAMPLES_DIR
        processed = PROCESSED_DIR / "benin_gdelt_clean.csv"
        sample    = SAMPLES_DIR   / "benin_gdelt_sample.csv"
    except Exception:
        processed = ROOT / "data" / "processed" / "benin_gdelt_clean.csv"
        sample    = ROOT / "data" / "sample"    / "benin_gdelt_sample.csv"

    if processed.exists():
        df = pd.read_csv(processed, low_memory=False)
        source = "complete"
    elif sample.exists():
        df = pd.read_csv(sample, low_memory=False)
        source = "sample"
    else:
        return pd.DataFrame(), "none"

    for col in ["SQLDATE", "DATEADDED", "event_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    if "event_month" in df.columns:
        df["event_month"] = pd.to_numeric(df["event_month"], errors="coerce").astype("Int64")

    df["month_label"] = df["event_month"].map(MONTH_LABELS)
    return df, source


df_full, data_source = load_data()

if isinstance(df_full, pd.DataFrame) and df_full.empty:
    st.error(
        "Aucune donnée trouvée. Lancez d'abord le pipeline :\n"
        "```\npython -m pipeline.run_pipeline --mode sample\n```"
    )
    st.stop()

# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────

st.markdown("""
<div class="dashboard-header">
    <h1>🇧🇯 Bénin Insights Challenge 2026</h1>
    <p>Analyse GDELT · Couverture médiatique mondiale du Bénin · Janvier – Décembre 2025</p>
</div>
""", unsafe_allow_html=True)

if data_source == "sample":
    st.markdown("""<div class="sample-banner">
    Données d'aperçu (5 000 lignes). Pour l'analyse complète :
    <code>python -m pipeline.run_pipeline --mode full</code>
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# SIDEBAR — FILTERS
# ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## Filtres")
    st.markdown("---")

    # ── Temporal filter
    st.markdown("### Période")
    all_months = sorted([int(m) for m in df_full["event_month"].dropna().unique()])
    month_options = {MONTH_LABELS.get(m, str(m)): m for m in all_months}
    selected_month_labels = st.multiselect(
        "Mois de l'année 2025",
        options=list(month_options.keys()),
        default=list(month_options.keys()),
        help="Filtrez les données par mois pour observer l'évolution temporelle."
    )
    selected_months = [month_options[lbl] for lbl in selected_month_labels]

    st.markdown("---")
    st.markdown("### Thématique")

    all_tones = sorted(df_full["tone_category"].dropna().unique().tolist())
    selected_tones = st.multiselect(
        "Ton médiatique",
        options=all_tones,
        default=all_tones,
        help="Positif, Neutre ou Négatif selon le score AvgTone GDELT."
    )

    all_roles = sorted(df_full["benin_role"].dropna().unique().tolist())
    selected_roles = st.multiselect(
        "Rôle du Bénin",
        options=all_roles,
        default=all_roles,
        help="Acteur (initiateur), Spectateur (cible), Mixte ou Contexte."
    )

    if "event_root_label" in df_full.columns:
        all_events = sorted(df_full["event_root_label"].dropna().unique().tolist())
        selected_events = st.multiselect(
            "Type d'événement",
            options=all_events,
            default=all_events,
        )
    else:
        selected_events = []

    st.markdown("---")
    st.caption("Bénin Insights Challenge 2026\niSHEERO × DataCamp · Équipe 7\nPipeline v1.3")

# ─────────────────────────────────────────────────────────────────
# APPLY FILTERS
# ─────────────────────────────────────────────────────────────────

df = df_full.copy()
if selected_months:
    df = df[df["event_month"].isin(selected_months)]
if selected_tones:
    df = df[df["tone_category"].isin(selected_tones)]
if selected_roles:
    df = df[df["benin_role"].isin(selected_roles)]
if selected_events and "event_root_label" in df.columns:
    df = df[df["event_root_label"].isin(selected_events)]

if df.empty:
    st.warning("Aucun événement ne correspond aux filtres sélectionnés.")
    st.stop()

# ─────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────

c1, c2, c3, c4, c5 = st.columns(5)
kpis = [
    (f"{len(df):,}", "Événements", "enregistrés par GDELT"),
    (f"{int(df['NumArticles'].sum()):,}", "Articles", "publiés dans le monde"),
    (f"{df['source_domain'].nunique():,}", "Sources médias", "domaines uniques"),
    (f"{(df['tone_category']=='Négatif').mean()*100:.0f}%", "Ton négatif", "des articles"),
    (f"{(df['benin_role']=='Acteur').mean()*100:.0f}%", "Bénin acteur", "initiateur de l'événement"),
]
for col, (val, lbl, sub) in zip([c1, c2, c3, c4, c5], kpis):
    with col:
        st.markdown(f"""<div class="kpi-card">
            <div class="kpi-value">{val}</div>
            <div class="kpi-label">{lbl}</div>
            <div class="kpi-sub">{sub}</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# Q1 — MEDIA VOLUME OVER TIME
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">Q1 — Quand le monde parle-t-il du Bénin ?</div>',
            unsafe_allow_html=True)

monthly = (
    df.groupby("event_month", as_index=False)
    .agg(nb_articles=("NumArticles", "sum"), nb_events=("SQLDATE", "count"))
    .sort_values("event_month")
)
monthly["month_label"] = monthly["event_month"].map(MONTH_LABELS)

col_q1a, col_q1b = st.columns([3, 2])
with col_q1a:
    fig_q1 = go.Figure()
    fig_q1.add_trace(go.Bar(
        x=monthly["month_label"], y=monthly["nb_articles"],
        name="Articles", marker_color="#1a56db",
        text=monthly["nb_articles"].apply(lambda v: f"{v:,}"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Articles : %{y:,}<extra></extra>"
    ))
    fig_q1.add_trace(go.Scatter(
        x=monthly["month_label"], y=monthly["nb_events"],
        name="Événements", mode="lines+markers", yaxis="y2",
        line=dict(color="#7e3af2", width=2), marker=dict(size=6),
        hovertemplate="<b>%{x}</b><br>Événements : %{y:,}<extra></extra>"
    ))
    fig_q1.update_layout(
        title="Volume mensuel de couverture médiatique",
        yaxis=dict(title="Nombre d'articles", gridcolor="#f0f0f0"),
        yaxis2=dict(title="Événements", overlaying="y", side="right", showgrid=False),
        plot_bgcolor="white", paper_bgcolor="white",
        legend=dict(orientation="h", y=-0.18),
        height=360, margin=dict(t=50, b=10)
    )
    st.plotly_chart(fig_q1, use_container_width=True, config=CHART_CONFIG)

with col_q1b:
    if "event_root_label" in df.columns:
        top_ev = (
            df.groupby("event_root_label").size()
            .sort_values(ascending=True).tail(8)
            .reset_index(name="count")
        )
        fig_ev = px.bar(
            top_ev, x="count", y="event_root_label", orientation="h",
            title="Top 8 — Types d'événements",
            color="count", color_continuous_scale="Blues",
            labels={"count": "Événements", "event_root_label": ""},
            text="count"
        )
        fig_ev.update_traces(textposition="outside")
        fig_ev.update_layout(
            coloraxis_showscale=False, plot_bgcolor="white",
            height=360, margin=dict(t=50, b=10)
        )
        st.plotly_chart(fig_ev, use_container_width=True, config=CHART_CONFIG)

peak_month = monthly.loc[monthly["nb_articles"].idxmax(), "month_label"]
peak_val   = monthly["nb_articles"].max()
st.markdown(f"""<div class="insight-box">
    <span class="insight-num">Insight Q1</span> — Le mois de <b>{peak_month}</b> concentre
    le plus grand nombre d'articles publiés dans le monde (<b>{peak_val:,}</b>).
    Ce pic marque la période où l'attention internationale sur le Bénin est la plus forte en 2025.
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# Q2 — MEDIA TONE
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">Q2 — Quel est le ton de la couverture médiatique ?</div>',
            unsafe_allow_html=True)

col_q2a, col_q2b = st.columns([2, 3])
with col_q2a:
    tone_dist = df["tone_category"].value_counts().reset_index()
    tone_dist.columns = ["tone_category", "count"]
    fig_pie = go.Figure(go.Pie(
        labels=tone_dist["tone_category"], values=tone_dist["count"],
        hole=0.5,
        marker_colors=[TONE_COLORS.get(t, "#aaa") for t in tone_dist["tone_category"]],
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value:,} événements (%{percent})<extra></extra>"
    ))
    fig_pie.update_layout(
        title="Répartition globale du ton",
        height=330, margin=dict(t=50, b=10), showlegend=False
    )
    st.plotly_chart(fig_pie, use_container_width=True, config=CHART_CONFIG)

with col_q2b:
    tone_m = (
        df.groupby("event_month", as_index=False)
        .agg(avg_tone=("AvgTone", "mean"))
        .sort_values("event_month")
    )
    tone_m["month_label"] = tone_m["event_month"].map(MONTH_LABELS)
    tone_m["color"] = tone_m["avg_tone"].apply(
        lambda v: "#d63031" if v < -2 else ("#00b894" if v > 2 else "#fdcb6e")
    )
    fig_tone = go.Figure()
    fig_tone.add_trace(go.Bar(
        x=tone_m["month_label"], y=tone_m["avg_tone"].round(2),
        marker_color=tone_m["color"],
        hovertemplate="<b>%{x}</b><br>Ton moyen : %{y:.2f}<extra></extra>"
    ))
    fig_tone.add_hline(y=2,  line_dash="dot", line_color="#00b894",
                       annotation_text="Seuil positif (+2)")
    fig_tone.add_hline(y=-2, line_dash="dot", line_color="#d63031",
                       annotation_text="Seuil négatif (−2)")
    fig_tone.add_hline(y=0,  line_dash="dash", line_color="gray")
    fig_tone.update_layout(
        title="Ton médiatique moyen par mois (AvgTone GDELT)",
        yaxis=dict(title="Ton moyen", gridcolor="#f0f0f0"),
        plot_bgcolor="white", paper_bgcolor="white",
        height=330, margin=dict(t=50, b=10), showlegend=False
    )
    st.plotly_chart(fig_tone, use_container_width=True, config=CHART_CONFIG)

neg_pct_total  = (df["tone_category"] == "Négatif").mean() * 100
most_neg_month = tone_m.loc[tone_m["avg_tone"].idxmin(), "month_label"]
st.markdown(f"""<div class="insight-box">
    <span class="insight-num">Insight Q2</span> — <b>{neg_pct_total:.0f}%</b> des événements
    ont un ton négatif. Le mois de <b>{most_neg_month}</b> enregistre le ton médiatique le plus
    bas de l'année, signalant une période de tension ou de crise particulièrement couverte à l'international.
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# Q3 — PROPAGATION DELAY
# ─────────────────────────────────────────────────────────────────

if "propagation_delay_days" in df.columns:
    st.markdown('<div class="section-title">Q3 — En combien de temps la couverture atteint-elle le monde ?</div>',
                unsafe_allow_html=True)

    delay = df["propagation_delay_days"].dropna()
    delay = delay[delay >= 0]
    med_delay = delay.median()
    fast_pct  = (delay <= 1).mean() * 100

    col_q3a, col_q3b, col_q3c = st.columns([2, 2, 1])
    with col_q3a:
        fig_hist = px.histogram(
            delay.clip(upper=30), nbins=31,
            title="Distribution du délai d'indexation (jours)",
            labels={"value": "Délai (jours, max 30)", "count": "Événements"},
            color_discrete_sequence=["#1a56db"]
        )
        fig_hist.update_layout(
            plot_bgcolor="white", showlegend=False,
            height=300, margin=dict(t=50, b=10)
        )
        st.plotly_chart(fig_hist, use_container_width=True, config=CHART_CONFIG)

    with col_q3b:
        dm = (
            df.groupby("event_month")["propagation_delay_days"]
            .median().reset_index().sort_values("event_month")
        )
        dm["month_label"] = dm["event_month"].map(MONTH_LABELS)
        fig_dm = px.bar(
            dm, x="month_label", y="propagation_delay_days",
            title="Délai médian par mois (jours)",
            color="propagation_delay_days", color_continuous_scale="Blues",
            labels={"propagation_delay_days": "Délai médian (j)", "month_label": ""}
        )
        fig_dm.update_layout(
            coloraxis_showscale=False, plot_bgcolor="white",
            height=300, margin=dict(t=50, b=10)
        )
        st.plotly_chart(fig_dm, use_container_width=True, config=CHART_CONFIG)

    with col_q3c:
        st.markdown(f"""
        <div class="kpi-card" style="margin-top:40px">
            <div class="kpi-value">{med_delay:.0f}j</div>
            <div class="kpi-label">Délai médian</div>
        </div><br>
        <div class="kpi-card">
            <div class="kpi-value">{fast_pct:.0f}%</div>
            <div class="kpi-label">Couverture &lt; 24h</div>
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""<div class="insight-box">
        <span class="insight-num">Insight Q3</span> — <b>{fast_pct:.0f}%</b> des événements
        béninois sont indexés en moins de 24 heures. Délai médian : <b>{med_delay:.0f} jour(s)</b>.
        GDELT est utilisable comme outil de veille en temps réel de l'image internationale du Bénin.
    </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# Q4 — SOURCES CRISIS VS NORMAL
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">Q4 — Les sources médiatiques changent-elles en période de crise ?</div>',
            unsafe_allow_html=True)

crisis_df = df[df["is_crisis_period"] == True]
normal_df = df[df["is_crisis_period"] == False]

def src_fig(data, title, color):
    src = data["source_domain"].value_counts().head(8).reset_index()
    src.columns = ["Domaine", "Occurrences"]
    fig = px.bar(
        src, x="Occurrences", y="Domaine", orientation="h",
        title=title, color_discrete_sequence=[color], text="Occurrences"
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(
        plot_bgcolor="white", height=340,
        margin=dict(t=50, b=10), showlegend=False,
        yaxis=dict(autorange="reversed")
    )
    return fig

col_q4a, col_q4b = st.columns(2)
with col_q4a:
    st.plotly_chart(
        src_fig(normal_df, f"Période normale ({len(normal_df):,} événements)", "#00b894"),
        use_container_width=True, config=CHART_CONFIG
    )
with col_q4b:
    st.plotly_chart(
        src_fig(crisis_df, f"Période de crise ({len(crisis_df):,} événements)", "#d63031"),
        use_container_width=True, config=CHART_CONFIG
    )

crisis_pct    = len(crisis_df) / len(df) * 100
top_src_crisis = crisis_df["source_domain"].value_counts().index[0] if len(crisis_df) > 0 else "N/A"
st.markdown(f"""<div class="insight-box">
    <span class="insight-num">Insight Q4</span> — <b>{crisis_pct:.0f}%</b> des événements
    se déroulent en contexte de crise (ton &lt; −5 ou Goldstein &lt; −5).
    En période de crise, <b>{top_src_crisis}</b> est la source la plus active.
    Comparer les deux colonnes révèle si certains médias n'apparaissent qu'en situation d'urgence.
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# Q5 — BENIN ROLE
# ─────────────────────────────────────────────────────────────────

st.markdown('<div class="section-title">Q5 — Le Bénin est-il acteur ou spectateur international ?</div>',
            unsafe_allow_html=True)

col_q5a, col_q5b = st.columns([2, 3])
with col_q5a:
    rd = df["benin_role"].value_counts().reset_index()
    rd.columns = ["benin_role", "count"]
    fig_role = go.Figure(go.Pie(
        labels=rd["benin_role"], values=rd["count"], hole=0.5,
        marker_colors=[ROLE_COLORS.get(r, "#aaa") for r in rd["benin_role"]],
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{value:,} événements (%{percent})<extra></extra>"
    ))
    fig_role.update_layout(
        title="Rôle du Bénin dans les événements",
        height=340, margin=dict(t=50, b=10), showlegend=False
    )
    st.plotly_chart(fig_role, use_container_width=True, config=CHART_CONFIG)

with col_q5b:
    if "event_root_label" in df.columns:
        re_df = (
            df.groupby(["event_root_label", "benin_role"])
            .size().reset_index(name="count")
        )
        top7 = df["event_root_label"].value_counts().head(7).index.tolist()
        re_df = re_df[re_df["event_root_label"].isin(top7)]
        fig_stack = px.bar(
            re_df, x="event_root_label", y="count",
            color="benin_role", barmode="stack",
            title="Rôle du Bénin par type d'événement (Top 7)",
            color_discrete_map=ROLE_COLORS,
            labels={"event_root_label": "", "count": "Événements", "benin_role": "Rôle"}
        )
        fig_stack.update_layout(
            plot_bgcolor="white", height=340,
            margin=dict(t=50, b=10), xaxis_tickangle=-30,
            legend=dict(orientation="h", y=-0.28)
        )
        st.plotly_chart(fig_stack, use_container_width=True, config=CHART_CONFIG)

role_pct = df["benin_role"].value_counts(normalize=True).mul(100)
actor_p  = role_pct.get("Acteur",   0)
ctx_p    = role_pct.get("Contexte", 0)
st.markdown(f"""<div class="insight-box">
    <span class="insight-num">Insight Q5</span> — Le Bénin est en position
    <b>Contexte</b> dans <b>{ctx_p:.0f}%</b> des cas (cadre géographique, non initiateur)
    et <b>Acteur</b> dans <b>{actor_p:.0f}%</b> des événements.
    Cela indique une couverture internationale réactive plutôt qu'une diplomatie proactive.
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# BONUS — GEOGRAPHIC BREAKDOWN (if available)
# ─────────────────────────────────────────────────────────────────

if "event_department" in df.columns:
    st.markdown('<div class="section-title">Répartition géographique — Départements du Bénin</div>',
                unsafe_allow_html=True)

    dept = (
        df.groupby("event_department", as_index=False)
        .agg(events=("SQLDATE", "count"), articles=("NumArticles", "sum"))
        .sort_values("events", ascending=False)
    )
    fig_dept = px.bar(
        dept, x="events", y="event_department", orientation="h",
        title="Nombre d'événements par département béninois",
        color="events", color_continuous_scale="Blues",
        text="events",
        labels={"events": "Événements", "event_department": ""}
    )
    fig_dept.update_traces(textposition="outside")
    fig_dept.update_layout(
        coloraxis_showscale=False, plot_bgcolor="white",
        height=430, margin=dict(t=50, b=10)
    )
    st.plotly_chart(fig_dept, use_container_width=True, config=CHART_CONFIG)

# ─────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<center style='color:#9ca3af; font-size:0.8rem;'>"
    "Bénin Insights Challenge 2026 · iSHEERO × DataCamp Donates · Équipe 7 · "
    "Données : GDELT Project (gdelt-bq.gdeltv2.events) · Période : Jan–Déc 2025"
    "</center>",
    unsafe_allow_html=True
)

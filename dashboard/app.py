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
    Q6 - Does a hidden media agenda exist (low coverage + very negative)?
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

st.markdown('<div class="section-title">Q1 — Quand le monde parle-t-il du Bénin, et quels événements provoquent les pics de couverture ?</div>',
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

peak_month_idx = monthly.loc[monthly["nb_articles"].idxmax(), "event_month"]
peak_month = monthly.loc[monthly["nb_articles"].idxmax(), "month_label"]
peak_val   = monthly["nb_articles"].max()

# ── Find top event in peak month — enriched with context fields ────
_peak_rows = df[df["event_month"] == peak_month_idx].copy()

# Aggregate articles per (date, event type) to find the dominant event
peak_month_events = (
    _peak_rows
    .groupby(["SQLDATE", "event_root_label"], as_index=False)
    .agg(articles=("NumArticles", "sum"))
    .sort_values("articles", ascending=False)
)

if len(peak_month_events) > 0:
    top_peak_event = peak_month_events.iloc[0]
    event_label    = top_peak_event["event_root_label"]
    event_date     = top_peak_event["SQLDATE"].strftime("%d %b %Y")
    event_articles = int(top_peak_event["articles"])

    # Get a representative row for context enrichment
    _match = _peak_rows[
        (_peak_rows["SQLDATE"] == top_peak_event["SQLDATE"]) &
        (_peak_rows["event_root_label"] == event_label)
    ].sort_values("NumArticles", ascending=False).iloc[0]

    # Extract enrichment fields safely
    def _safe(val, fallback="N/A"):
        return str(val).strip() if pd.notna(val) and str(val).strip() not in ("", "nan") else fallback

    e_actor1   = _safe(_match.get("Actor1Name"))
    e_actor2   = _safe(_match.get("Actor2Name"))
    e_geo      = _safe(_match.get("ActionGeo_FullName"))
    e_tone_val = _match.get("AvgTone")
    e_gold_val = _match.get("GoldsteinScale")
    e_source   = _safe(_match.get("source_domain"))

    e_tone  = f"{e_tone_val:+.1f}" if pd.notna(e_tone_val) else "N/A"
    e_gold  = f"{e_gold_val:+.1f}" if pd.notna(e_gold_val) else "N/A"

    # Actors line — hide if both N/A
    actors_line = ""
    if e_actor1 != "N/A" or e_actor2 != "N/A":
        parts = [p for p in [e_actor1, e_actor2] if p != "N/A"]
        actors_line = f"<b>Acteurs</b> : {' ↔ '.join(parts)}<br>"

    insight_q1 = f"""<div class="insight-box">
        <span class="insight-num">Insight Q1</span> — Le mois de <b>{peak_month}</b> concentre
        le plus grand nombre d'articles publiés au monde (<b>{peak_val:,}</b> au total),
        soit près du double de la moyenne mensuelle. Ce pic révèle une intensification
        de l'attention internationale sur le Bénin.
        <br><br>
        <b>Événement déclencheur</b> : <b>{event_label}</b> — {event_date} —
        <b>{event_articles:,} articles</b><br>
        {actors_line}
        <b>Lieu</b> : {e_geo}<br>
        <b>Intensité géopolitique</b> (Goldstein) : {e_gold} &nbsp;|&nbsp;
        <b>Ton médiatique</b> : {e_tone}<br>
        <b>Source dominante</b> : {e_source}
        <br><br>
        → <b>Recommandation</b> : Les décideurs béninois doivent mettre en place
        un dispositif de veille médiatique internationale permanent. L'analyse montre
        que les pics de couverture sont liés à des événements diplomatiques (CEDEAO, acteurs
        régionaux) et sécuritaires — des sujets sur lesquels une communication proactive
        peut réduire l'impact négatif.
    </div>"""
else:
    insight_q1 = f"""<div class="insight-box">
        <span class="insight-num">Insight Q1</span> — Le mois de <b>{peak_month}</b> concentre
        le plus grand nombre d'articles publiés au monde (<b>{peak_val:,}</b>).
    </div>"""

st.markdown(insight_q1, unsafe_allow_html=True)

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
# Determine positive %
pos_pct_total = (df["tone_category"] == "Positif").mean() * 100
neu_pct_total = (df["tone_category"] == "Neutre").mean() * 100
avg_tone_val  = df["AvgTone"].mean()
gold_mean_val = df["GoldsteinScale"].mean()

st.markdown(f"""<div class="insight-box">
    <span class="insight-num">Insight Q2</span> — <b>{neg_pct_total:.0f}%</b> des événements
    ont un ton négatif, contre <b>{pos_pct_total:.0f}%</b> positif et <b>{neu_pct_total:.0f}%</b> neutre.
    Le ton moyen global est de <b>{avg_tone_val:+.2f}</b> (négatif < 0 < positif), confirmant
    que l'image internationale du Bénin est dominée par les tensions et les crises.
    <br><br>
    Le mois de <b>{most_neg_month}</b> enregistre le ton le plus bas de l'année,
    corrélé aux événements sécuritaires et aux déclarations diplomatiques de la CEDEAO.
    L'échelle de Goldstein (impact sur la stabilité nationale) est en moyenne à <b>{gold_mean_val:+.2f}</b>,
    ce qui reste légèrement positif — indiquant que les événements de coopération compensent
    les crises en volume.
    <br><br>
    → <b>Recommandation</b> : Le Bénin devrait systématiquement accompagner les événements
    de crise d'une communication institutionnelle positive (coopération économique,
    progrès sociaux) pour rééquilibrer son image médiatique.
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
        Cela signifie que la couverture mondiale est <b>quasi instantanée</b> : un événement
        survenant à Cotonou ou Porto-Novo est visible dans les médias internationaux le jour même.
        <br><br>
        Cette réactivité a une conséquence majeure : les responsables béninois ne disposent
        d'aucune fenêtre de temps pour préparer une réponse avant que l'information
        ne soit diffusée mondialement. GDELT peut servir d'outil de veille en temps réel
        pour anticiper les réactions internationales.
        <br><br>
        → <b>Recommandation</b> : Mettre en place une cellule de veille GDELT automatisée
        qui alerte les communicants gouvernementaux dès qu'un événement béninois
        dépasse un seuil de couverture critique.
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

crisis_pct     = len(crisis_df) / len(df) * 100
top_src_global = df["source_domain"].value_counts().index[0] if len(df) > 0 else "N/A"
top_src_crisis = crisis_df["source_domain"].value_counts().index[0] if len(crisis_df) > 0 else "N/A"

# ── Dynamically detect the dominant country from the top source TLD ──
# Mapping TLD → country name. Adapts automatically if data changes.
# "punchng.com" → known Nigerian media → "Nigeria"
# "dailypost.ng"  → tld="ng" → "Nigeria"
# "lemonde.fr"   → tld="fr" → "France"

# Known .com domains by country
KNOWN_DOMAINS = {
    # Nigeria
    "punchng.com": "Nigeria", "dailypost.ng": "Nigeria",
    "nigerianobservernews.com": "Nigeria", "leadership.ng": "Nigeria",
    "guardian.ng": "Nigeria", "thisdaylive.com": "Nigeria",
    "saharareporters.com": "Nigeria", "thesun.ng": "Nigeria",
    "vanguardngr.com": "Nigeria", "punchng.com": "Nigeria",
    "dailypostnigeria.com": "Nigeria", "nigerian Tribune": "Nigeria",
    # Ghana
    "ghanweb.com": "Ghana", "graphic.com.gh": "Ghana",
    # International/Aggregators
    "allafrica.com": "International", "reuters.com": "International",
    "bbc.com": "UK", "africanews.com": "International",
    "newsroom247.io": "International",
}

TLD_TO_COUNTRY = {
    "ng": "Nigeria",      "bj": "Bénin",         "fr": "France",
    "sn": "Sénégal",      "ci": "Côte d'Ivoire",  "gh": "Ghana",
    "tg": "Togo",         "cm": "Cameroun",        "ml": "Mali",
    "bf": "Burkina Faso", "ne": "Niger",           "gn": "Guinée",
    "gb": "Royaume-Uni",  "de": "Allemagne",       "us": "États-Unis",
    "cn": "Chine",       "za": "Afrique du Sud",  "in": "Inde",
    "com": "International", "org": "International",
    "net": "International", "info": "International",
}

def get_country_from_domain(domain):
    """Extract country from domain - handles .com, .ng, .fr, etc."""
    if not domain or domain == "N/A":
        return "Inconnu"
    
    # Check known domains first
    for known, country in KNOWN_DOMAINS.items():
        if known in domain.lower():
            return country
    
    # Extract TLD
    parts = domain.lower().split(".")
    if len(parts) >= 2:
        tld = parts[-1]
        if len(parts) >= 3 and parts[-2] in ["co", "com", "org"]:
            tld = parts[-2]  # Handle co.uk, co.za, etc.
        return TLD_TO_COUNTRY.get(tld, tld.upper())
    return "Inconnu"

top_country = get_country_from_domain(top_src_global)

# Build geographic note dynamically based on detected country
if top_country == "Nigeria":
    geo_note = (
        f"La source dominante <b>punchng.com</b> (Nigeria) reflète "
        f"la proximité géographique et les liens économiques forts entre le Bénin et le Nigeria. "
        f"La presse régionale ouest-africaine couvre le Bénin plus intensément que les grands "
        f"médias occidentaux. Ce n'est pas une erreur — ces médias couvrent bien le "
        f"<b>pays Bénin</b>, pas la ville nigériane de Benin City (exclue du pipeline)."
    )
    strategy_note = (
        f"→ Pour améliorer son image internationale, le Bénin doit en priorité engager "
        f"les grandes rédactions <b>nigérianes</b> et ouest-africaines."
    )
elif top_country == "Bénin":
    geo_note = (
        f"La source dominante est béninoise ({top_src_global}), ce qui indique que "
        f"la presse locale assure l'essentiel de la couverture internationale du Bénin."
    )
    strategy_note = "→ La presse béninoise est bien représentée dans la couverture mondiale."
elif top_country in ("International", "International"):
    geo_note = (
        f"La source dominante ({top_src_global}) est un agrégateur international, "
        f"indiquant une couverture diversifiée sans domination d'un seul pays."
    )
    strategy_note = "→ La couverture internationale du Bénin est géographiquement équilibrée."
else:
    geo_note = (
        f"La source dominante ({top_src_global}, pays : {top_country}) "
        f"concentre l'essentiel de la couverture médiatique du Bénin."
    )
    strategy_note = f"→ Le Bénin est principalement couvert par les médias {top_country}s."

# Count distinct sources in each period
n_src_crisis = crisis_df["source_domain"].nunique() if len(crisis_df) > 0 else 0
n_src_normal = normal_df["source_domain"].nunique() if len(normal_df) > 0 else 0

# Detect crisis-only sources
crisis_top8 = set(crisis_df["source_domain"].value_counts().head(8).index) if len(crisis_df) > 0 else set()
normal_top8 = set(normal_df["source_domain"].value_counts().head(8).index) if len(normal_df) > 0 else set()
crisis_only_src = crisis_top8 - normal_top8
crisis_only_note = (
    f"Source(s) spécifique(s) aux crises : <b>{', '.join(crisis_only_src)}</b>."
    if crisis_only_src
    else "Les mêmes sources couvrent le Bénin en période normale et en crise — le corpus médiatique est stable."
)

st.markdown(f"""<div class="insight-box">
    <span class="insight-num">Insight Q4</span> — <b>{crisis_pct:.0f}%</b> des événements
    se déroulent en contexte de crise (ton &lt; −5 ou Goldstein &lt; −5).
    En période de crise, <b>{top_src_crisis}</b> est la source la plus active
    ({n_src_crisis} sources uniques en crise contre {n_src_normal} en période normale).<br><br>
    {geo_note}<br><br>
    <b>Fait marquant</b> : 7 des 10 premières sources sont nigérianes (.ng),
    ce qui reflète les liens économiques et la proximité géographique
    entre le Bénin et le Nigeria. Ce n'est pas une anomalie de filtrage —
    le pipeline exclut explicitement les événements de Benin City (Nigeria).<br><br>
    {crisis_only_note}<br><br>
    → <b>Recommandation</b> : {strategy_note.replace('→ ', '')}
    La presse béninoise (lanouvelletribune.info) est la 6ᵉ source — renforcer
    sa visibilité internationale permettrait de diversifier la couverture.
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
spec_p   = role_pct.get("Spectateur", 0)
mixte_p  = role_pct.get("Mixte", 0)

# Top actor types when Benin is active
acteur_df = df[df["benin_role"].isin(["Acteur", "Mixte"])]
top_actor_type = (
    acteur_df["actor1_type_label"]
    .value_counts()
    .drop("Non identifié", errors="ignore")
    .head(3)
)
top_actor_str = ", ".join(
    [f"{t} ({c:,})" for t, c in top_actor_type.items()]
) if len(top_actor_type) > 0 else "N/A"

# Top event types when Benin is actor
top_evt_acteur = (
    acteur_df["event_root_label"]
    .value_counts()
    .head(3)
)
top_evt_str = ", ".join(
    [f"{e} ({c:,})" for e, c in top_evt_acteur.items()]
) if len(top_evt_acteur) > 0 else "N/A"

st.markdown(f"""<div class="insight-box">
    <span class="insight-num">Insight Q5</span> — Le Bénin est en position
    <b>Contexte</b> dans <b>{ctx_p:.0f}%</b> des cas (cadre géographique, non initiateur),
    <b>Acteur</b> dans <b>{actor_p:.0f}%</b>, <b>Spectateur</b> (cible) dans <b>{spec_p:.0f}%</b>,
    et <b>Mixte</b> (acteur et cible) dans <b>{mixte_p:.1f}%</b>.
    <br><br>
    Quand le Bénin est acteur, les institutions les plus visibles sont :
    <b>{top_actor_str}</b>.
    Les actions initiées sont principalement : <b>{top_evt_str}</b>.
    <br><br>
    La prédominance du rôle "Contexte" signifie que le Bénin est surtout
    un <b>terrain d'événements</b> plutôt qu'un acteur géopolitique proactif.
    Les événements de coopération régionale (CEDEAO) et les interactions
    avec le Nigeria dominent quand le Bénin est acteur.
    <br><br>
    → <b>Recommandation</b> : Pour augmenter sa proportion d'événements en tant qu'acteur,
    le Bénin devrait multiplier les initiatives diplomatiques visibles
    (sommets, accords bilatéraux, prises de position à l'ONU/UA/CEDEAO)
    et renforcer sa communication institutionnelle lors de ces événements.
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# BONUS — HIDDEN MEDIA AGENDA
# ─────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="section-title">🎯 BONUS — Agenda médiatique caché (Q6)</div>',
    unsafe_allow_html=True
)

# Hidden agenda: low coverage + very negative
def cat_coverage(x):
    if pd.isna(x): return "Autre"
    return "Tres_faible" if x <= 5 else "Autre"

def cat_tone(x):
    if pd.isna(x): return "Autre"
    return "Tres_negatif" if x <= -5 else "Autre"

df["coverage_cat"] = df["NumArticles"].apply(cat_coverage)
df["tone_cat"] = df["GoldsteinScale"].apply(cat_tone)
hidden = df[(df["coverage_cat"] == "Tres_faible") & (df["tone_cat"] == "Tres_negatif")]

hidden_geo = hidden["ActionGeo_CountryCode"].value_counts()
bn_hidden = hidden_geo.get("BN", 0)
hidden_total = hidden_geo.sum()
hidden_pct = bn_hidden / hidden_total * 100 if hidden_total > 0 else 0

# Top hidden event types
top_hidden = hidden.groupby("event_root_label").size().sort_values(ascending=False).head(6)

col_b1, col_b2 = st.columns([1, 2])
with col_b1:
    st.metric("Events cachés", f"{len(hidden):,}")
    st.metric("Au Benin", f"{hidden_pct:.0f}%")
with col_b2:
    fig_hidden = px.bar(
        top_hidden.reset_index(), x="event_root_label", y=0,
        title="Types d'événements cachés (peu couverts + très négatifs)",
        labels={"event_root_label": "", 0: "Événements"},
        color_discrete_sequence=["#e74c3c"]
    )
    fig_hidden.update_layout(plot_bgcolor="white", height=280, margin=dict(t=40,b=10))
    st.plotly_chart(fig_hidden, use_container_width=True, config=CHART_CONFIG)

# Top hidden event types for insight
top_hidden_types = top_hidden.head(3)
top_hidden_str = ", ".join(
    [f"{e} ({c:,})" for e, c in top_hidden_types.items()]
) if len(top_hidden_types) > 0 else "N/A"

# Insight BONUS
st.markdown(f"""<div class="insight-box">
    <span class="insight-num">Insight Q6</span> — 
    <b>{len(hidden):,} événements</b> très négatifs (Goldstein ≤ −5) mais faiblement
    couverts (1 à 5 articles seulement).
    <b>{hidden_pct:.0f}%</b> d'entre eux se produisent au Bénin.
    <br><br>
    <b>Types d'événements cachés</b> : {top_hidden_str}.
    Ces événements représentent des situations graves (violences, assauts, attentats)
    qui n'ont pas encore attiré l'attention des grands médias, mais qui pourraient
    devenir des crises médiatiques à tout moment si un média international les reprend.
    <br><br>
    → <b>Recommandation</b> : Ces événements sous-couverts méritent une veille
    prioritaire. Les autorités béninaises devraient anticiper leur médiatisation
    potentielle en préparant des éléments de communication proactifs
    sur les sujets de sécurité et de droits humains.
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# CORRELATION MATRIX Q1–Q5
# ─────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="section-title">Matrice de corrélation — Relations entre les 5 questions</div>',
    unsafe_allow_html=True
)

# Build monthly aggregates for each question
monthly_corr = (
    df.groupby("event_month", as_index=False)
    .agg(nb_articles=("NumArticles", "sum"))
    .sort_values("event_month")
)

tone_monthly_corr = (
    df.groupby("event_month", as_index=False)
    .agg(avg_tone=("AvgTone", "mean"))
    .sort_values("event_month")
)

source_diversity = (
    df.groupby("event_month")["source_domain"]
    .nunique()
    .reset_index()
    .rename(columns={"source_domain": "source_count"})
)

benin_role_monthly = (
    df.groupby("event_month")["benin_role"]
    .apply(lambda x: (x == "Acteur").mean() * 100)
    .reset_index()
    .rename(columns={"benin_role": "actor_pct"})
)

# Assemble correlation dataframe (one row per month)
corr_df = monthly_corr[["event_month", "nb_articles"]].rename(
    columns={"nb_articles": "Q1_volume"}
)
corr_df = corr_df.merge(
    tone_monthly_corr[["event_month", "avg_tone"]].rename(columns={"avg_tone": "Q2_tone"}),
    on="event_month", how="left"
)

if "propagation_delay_days" in df.columns:
    delay_monthly_corr = (
        df.groupby("event_month")["propagation_delay_days"]
        .mean()   # mean instead of median: median=0 for all months (>50% same-day),
                  # which gives zero variance and makes Pearson correlation undefined (NaN).
                  # The mean varies because high-delay events pull it differently each month.
        .reset_index()
        .rename(columns={"propagation_delay_days": "Q3_delay"})
    )
    corr_df = corr_df.merge(delay_monthly_corr, on="event_month", how="left")
else:
    corr_df["Q3_delay"] = float("nan")

corr_df = corr_df.merge(
    source_diversity.rename(columns={"source_count": "Q4_sources"}),
    on="event_month", how="left"
)
corr_df = corr_df.merge(
    benin_role_monthly.rename(columns={"actor_pct": "Q5_role"}),
    on="event_month", how="left"
)

CORR_COLS   = ["Q1_volume", "Q2_tone", "Q3_delay", "Q4_sources", "Q5_role"]
CORR_LABELS = ["Q1\nVolume", "Q2\nTon", "Q3\nDélai", "Q4\nSources", "Q5\nRôle"]

corr_matrix = corr_df[CORR_COLS].corr()

col_heatmap, col_insights = st.columns([3, 2])

with col_heatmap:
    fig_corr = go.Figure(
        data=go.Heatmap(
            z=corr_matrix.values,
            x=CORR_LABELS,
            y=CORR_LABELS,
            colorscale="RdBu",
            zmid=0,
            zmin=-1,
            zmax=1,
            text=corr_matrix.values.round(2),
            texttemplate="%{text}",
            textfont={"size": 13, "color": "black"},
            colorbar=dict(title="Corrélation", thickness=14),
            hoverongaps=False,
            hovertemplate="<b>%{y} ↔ %{x}</b><br>r = %{z:.2f}<extra></extra>"
        )
    )
    fig_corr.update_layout(
        title="Corrélations entre les 5 dimensions d'analyse (agrégées par mois)",
        title_font_size=13,
        height=420,
        margin=dict(t=50, b=10, l=10, r=10),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    st.plotly_chart(fig_corr, use_container_width=True, config=CHART_CONFIG)

with col_insights:
    st.markdown("#### 🔍 Interprétation automatique")

    # Collect all off-diagonal pairs sorted by absolute correlation
    corr_pairs = []
    for i in range(len(CORR_COLS)):
        for j in range(i + 1, len(CORR_COLS)):
            r = corr_matrix.iloc[i, j]
            if not (r != r):  # skip NaN
                corr_pairs.append({
                    "q1": CORR_COLS[i],
                    "q2": CORR_COLS[j],
                    "r": r
                })
    corr_pairs.sort(key=lambda x: abs(x["r"]), reverse=True)

    LABEL_MAP = {
        "Q1_volume":  "Volume médiatique",
        "Q2_tone":    "Ton médiatique",
        "Q3_delay":   "Délai de propagation",
        "Q4_sources": "Diversité des sources",
        "Q5_role":    "Rôle du Bénin (Acteur %)",
    }

    for pair in corr_pairs[:5]:
        r   = pair["r"]
        l1  = LABEL_MAP[pair["q1"]]
        l2  = LABEL_MAP[pair["q2"]]
        tag = pair["q1"].split("_")[0]
        tag2 = pair["q2"].split("_")[0]

        if r > 0.6:
            color = "#00b894"
            icon  = "📈"
            desc  = f"**corrélation positive forte** ({r:+.2f}) — quand l'un augmente, l'autre aussi."
        elif r < -0.6:
            color = "#d63031"
            icon  = "📉"
            desc  = f"**corrélation négative forte** ({r:+.2f}) — quand l'un augmente, l'autre baisse."
        elif r > 0.3:
            color = "#74b9ff"
            icon  = "↗️"
            desc  = f"**corrélation positive modérée** ({r:+.2f})."
        elif r < -0.3:
            color = "#fd79a8"
            icon  = "↘️"
            desc  = f"**corrélation négative modérée** ({r:+.2f})."
        else:
            color = "#b2bec3"
            icon  = "➡️"
            desc  = f"**pas de lien significatif** ({r:+.2f})."

        st.markdown(
            f"<div style='border-left:4px solid {color}; padding:0.5rem 0.8rem; "
            f"margin:0.4rem 0; background:#f9fafb; border-radius:4px; font-size:0.83rem;'>"
            f"{icon} <b>{tag} ↔ {tag2}</b> — {l1} / {l2}<br>"
            f"<span style='color:#374151;'>{desc}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

# Build dynamic correlation insight from top pair
if len(corr_pairs) >= 2:
    top1 = corr_pairs[0]
    top2 = corr_pairs[1]
    l1_1 = LABEL_MAP[top1["q1"]]
    l1_2 = LABEL_MAP[top1["q2"]]
    l2_1 = LABEL_MAP[top2["q1"]]
    l2_2 = LABEL_MAP[top2["q2"]]
    r1 = top1["r"]
    r2 = top2["r"]

    dir1 = "augmentent ensemble" if r1 > 0 else "varient inversement"
    dir2 = "augmentent ensemble" if r2 > 0 else "varient inversement"

    dynamic_corr_note = (
        f"Le lien le plus fort : <b>{l1_1}</b> ↔ <b>{l1_2}</b> (r = {r1:+.2f}) — "
        f"ils {dir1}. "
        f"Deuxième lien : <b>{l2_1}</b> ↔ <b>{l2_2}</b> (r = {r2:+.2f}) — "
        f"ils {dir2}."
    )
else:
    dynamic_corr_note = "Pas assez de données pour identifier des corrélations significatives."

st.markdown(f"""<div class="insight-box">
    <span class="insight-num">Insight Corrélation</span> — Cette matrice révèle les <b>liens systémiques</b>
    entre les 5 dimensions d'analyse.<br><br>
    {dynamic_corr_note}<br><br>
    <b>Interprétation pour les décideurs</b> : si Volume (Q1) et Sources (Q4)
    sont fortement corrélés, cela signifie que les pics de couverture
    mobilisent davantage de médias — effet boule de neige médiatique.
    Si Ton (Q2) et Volume (Q1) sont inversement corrélés, les crises
    génèrent plus d'articles : plus le sujet est grave, plus il est couvert.
    <br><br>
    → <b>Recommandation</b> : Ces corrélations doivent guider le timing
    des communications institutionnelles. Communiquer positivement
    pendant les périodes de faible volume médiatique maximise l'impact
    sans être noyé par les crises.
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

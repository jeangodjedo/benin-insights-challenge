# dashboard/app.py
"""
Bénin Insights Challenge 2026 — Interactive Dashboard
iSHEERO × DataCamp Donates — IROKO Analytics (Équipe 7)

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
.audience-grid {
    display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.7rem;
    margin-top: 0.8rem;
}
.audience-card {
    border-radius: 8px; padding: 0.7rem 0.9rem;
    font-size: 0.82rem; line-height: 1.45;
}
.audience-card.decideurs {
    background: #eef2ff; border-left: 3px solid #1a56db;
}
.audience-card.journalistes {
    background: #fef3c7; border-left: 3px solid #f59e0b;
}
.audience-card.chercheurs {
    background: #ecfdf5; border-left: 3px solid #10b981;
}
.audience-tag {
    font-weight: 700; font-size: 0.78rem; text-transform: uppercase;
    letter-spacing: 0.04em; margin-bottom: 0.3rem;
}
.audience-tag.decideurs   { color: #1a56db; }
.audience-tag.journalistes { color: #b45309; }
.audience-tag.chercheurs   { color: #059669; }
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

TEMPORAL_PRESETS = {
    "Année complète 2025":              list(range(1, 13)),
    "T1 (jan – mar)":                   [1, 2, 3],
    "T2 (avr – juin)":                  [4, 5, 6],
    "T3 (juil – sept)":                 [7, 8, 9],
    "T4 (oct – déc)":                   [10, 11, 12],
    "Pic de crise (décembre)":          [12],
    "Avant le coup d'État (jan – nov)": list(range(1, 12)),
    "Personnalisé":                     None,
}

with st.sidebar:
    st.markdown("## Filtres")
    st.markdown("---")

    # ── Temporal filter — presets + multiselect + optional date range ──
    st.markdown("### Période")

    preset = st.selectbox(
        "Préréglage temporel",
        options=list(TEMPORAL_PRESETS.keys()),
        index=0,
        help="Sélection rapide d'une période d'intérêt. "
             "Choisissez 'Personnalisé' pour cocher les mois manuellement.",
    )

    all_months = sorted([int(m) for m in df_full["event_month"].dropna().unique()])
    month_options = {MONTH_LABELS.get(m, str(m)): m for m in all_months}

    if TEMPORAL_PRESETS[preset] is not None:
        default_month_labels = [
            MONTH_LABELS[m] for m in TEMPORAL_PRESETS[preset] if m in all_months
        ]
    else:
        default_month_labels = list(month_options.keys())

    # Key tied to preset → multiselect re-initializes when preset changes,
    # so the default is reliably re-applied.
    multiselect_key = f"_month_select_{preset}"
    selected_month_labels = st.multiselect(
        "Affiner par mois",
        options=list(month_options.keys()),
        default=default_month_labels,
        key=multiselect_key,
        help="Vous pouvez ajouter ou retirer manuellement des mois.",
    )
    selected_months = [month_options[lbl] for lbl in selected_month_labels]

    use_date_range = st.toggle(
        "Filtre date précis (jour à jour)",
        value=False,
        help="Zoomer sur une plage de dates précise (ex. 1–15 décembre 2025 "
             "autour du coup d'État du 7 décembre). Lorsqu'activé, ce filtre "
             "remplace la sélection par mois ci-dessus.",
    )

    date_range = None
    if use_date_range and "SQLDATE" in df_full.columns:
        sqldates = pd.to_datetime(df_full["SQLDATE"], errors="coerce").dropna()
        min_date = sqldates.min().date()
        max_date = sqldates.max().date()
        date_range = st.date_input(
            "Période précise",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )

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

# ─────────────────────────────────────────────────────────────────
# APPLY FILTERS
# ─────────────────────────────────────────────────────────────────

df = df_full.copy()

# Temporal filter — date range takes precedence if active
if use_date_range:
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_d, end_d = date_range
        df = df[
            (pd.to_datetime(df["SQLDATE"]) >= pd.Timestamp(start_d)) &
            (pd.to_datetime(df["SQLDATE"]) <= pd.Timestamp(end_d))
        ]
        active_period_label = (
            f"Du {pd.Timestamp(start_d).strftime('%d %b %Y')} "
            f"au {pd.Timestamp(end_d).strftime('%d %b %Y')}"
        )
    else:
        with st.sidebar:
            st.warning(
                "Sélectionnez une date de **début** et une date de **fin** "
                "pour activer le filtre date précis."
            )
        st.stop()
elif not selected_months:
    # User has unchecked all months: stop with an explicit message
    # rather than silently re-showing the full dataset.
    with st.sidebar:
        st.warning(
            "Aucun mois sélectionné. Choisissez un préréglage ou cochez "
            "au moins un mois pour afficher les données."
        )
    st.stop()
else:
    df = df[df["event_month"].isin(selected_months)]
    # Prefer the preset name when the manual selection still matches it exactly
    preset_months = TEMPORAL_PRESETS.get(preset)
    if preset_months is not None and set(selected_months) == set(preset_months):
        active_period_label = preset
    elif len(selected_months) == 12:
        active_period_label = "Année complète 2025"
    elif len(selected_months) == 1:
        active_period_label = MONTH_LABELS[selected_months[0]]
    else:
        active_period_label = f"{len(selected_months)} mois sélectionnés"

if selected_tones:
    df = df[df["tone_category"].isin(selected_tones)]
if selected_roles:
    df = df[df["benin_role"].isin(selected_roles)]
if selected_events and "event_root_label" in df.columns:
    df = df[df["event_root_label"].isin(selected_events)]

if df.empty:
    st.warning(
        "Aucun événement ne correspond aux filtres sélectionnés. "
        "Essayez d'élargir la période ou de réinitialiser les filtres thématiques."
    )
    st.stop()

# ── Live counter pinned at the bottom of the sidebar ──────────
total_events = len(df_full)
filtered_events = len(df)
pct_kept = (filtered_events / total_events * 100) if total_events else 0
with st.sidebar:
    st.markdown("---")
    st.markdown(f"""
    <div style='background:#eff6ff; border:1px solid #bfdbfe; border-radius:8px;
                padding:0.75rem 0.9rem; margin-bottom:0.6rem;'>
        <div style='font-size:0.72rem; text-transform:uppercase; letter-spacing:0.05em;
                    color:#6b7280; font-weight:700;'>Événements affichés</div>
        <div style='font-size:1.55rem; font-weight:800; color:#1a56db; line-height:1.1;'>
            {filtered_events:,}
        </div>
        <div style='font-size:0.78rem; color:#6b7280; margin-top:0.15rem;'>
            sur {total_events:,} ({pct_kept:.1f} %)
        </div>
        <div style='font-size:0.78rem; color:#1e3a8a; margin-top:0.4rem;
                    border-top:1px solid #bfdbfe; padding-top:0.35rem;'>
            <b>Période :</b> {active_period_label}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Bénin Insights Challenge 2026\nIROKO Analytics (Équipe 7)\niSHEERO × DataCamp Donates")

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
    # Compute y-axis max with padding for text labels
    _q1_ymax = monthly["nb_articles"].max() * 1.2
    fig_q1.update_layout(
        title="Volume mensuel de couverture médiatique",
        yaxis=dict(title="Nombre d'articles", gridcolor="#f0f0f0", range=[0, _q1_ymax]),
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

    # Real-world context for the December peak
    _context_note = ""
    if peak_month_idx == 12:
        _context_note = (
            "<br><br>"
            "<b>🔴 Contexte réel</b> : Le 7 décembre 2025, le ministre de l'Intérieur "
            "<b>Alassane Seidou</b> a officiellement annoncé qu'une <b>tentative de coup d'État</b> "
            "avait été déjouée au Bénin après une brève occupation de la télévision nationale. "
            "Cet événement explique le pic massif de couverture et le ton très négatif du mois."
        )

    # Note: HTML must NOT be indented inside the f-string — Markdown treats lines
    # starting with 4+ spaces as code blocks, which breaks rendering when
    # _context_note is empty (non-December peaks).
    insight_q1 = (
        f'<div class="insight-box">'
        f'<span class="insight-num">Insight Q1</span> — Le mois de <b>{peak_month}</b> concentre '
        f"le plus grand nombre d'articles publiés au monde (<b>{peak_val:,}</b> au total), "
        f"soit près du double de la moyenne mensuelle. Ce pic révèle une intensification "
        f"de l'attention internationale sur le Bénin."
        f"{_context_note}"
        f"<br><br>"
        f"<b>Événement déclencheur</b> : <b>{event_label}</b> — {event_date} — "
        f"<b>{event_articles:,} articles</b><br>"
        f"{actors_line}"
        f"<b>Lieu</b> : {e_geo}<br>"
        f"<b>Intensité géopolitique</b> (Goldstein) : {e_gold} &nbsp;|&nbsp; "
        f"<b>Ton médiatique</b> : {e_tone}<br>"
        f"<b>Source dominante</b> : {e_source}"
        f'<div class="audience-grid">'
        f'<div class="audience-card decideurs">'
        f'<div class="audience-tag decideurs">🏛️ Décideurs</div>'
        f"Mettre en place un <b>dispositif de veille médiatique</b> permanent. "
        f"Les pics sont liés aux événements diplomatiques (CEDEAO) et sécuritaires — "
        f"une communication proactive peut réduire l'impact négatif."
        f"</div>"
        f'<div class="audience-card journalistes">'
        f'<div class="audience-tag journalistes">📰 Journalistes</div>'
        f"<b>Angle éditorial</b> : Pourquoi {peak_month} ? Investiguer les événements "
        f"de type <b>{event_label}</b> qui déclenchent l'attention mondiale. "
        f"Les médias nigérians couvrent le Bénin plus que les médias occidentaux — un sujet en soi."
        f"</div>"
        f'<div class="audience-card chercheurs">'
        f'<div class="audience-tag chercheurs">🔬 Chercheurs</div>'
        f"<b>Hypothèse</b> : Les pics de couverture suivent-ils un modèle saisonnier "
        f"ou sont-ils purement événementiels ? Analyser la corrélation entre "
        f"calendrier politique régional (sommets CEDEAO/UA) et volume médiatique."
        f"</div>"
        f"</div>"
        f"</div>"
    )
else:
    insight_q1 = (
        f'<div class="insight-box">'
        f'<span class="insight-num">Insight Q1</span> — Le mois de <b>{peak_month}</b> concentre '
        f"le plus grand nombre d'articles publiés au monde (<b>{peak_val:,}</b>)."
        f"</div>"
    )

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
    # Stacked bar: distribution Positif / Neutre / Négatif per month
    tone_m = (
        df.groupby(["event_month", "tone_category"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values("event_month")
    )
    tone_m["month_label"] = tone_m["event_month"].map(MONTH_LABELS)

    fig_tone = go.Figure()
    for tone_cat in ["Positif", "Neutre", "Négatif"]:
        subset = tone_m[tone_m["tone_category"] == tone_cat]
        fig_tone.add_trace(go.Bar(
            x=subset["month_label"], y=subset["count"],
            name=tone_cat,
            marker_color=TONE_COLORS.get(tone_cat, "#aaa"),
            hovertemplate="<b>%{x}</b><br>" + tone_cat + " : %{y:,}<extra></extra>"
        ))
    fig_tone.update_layout(
        title="Répartition du ton médiatique par mois",
        barmode="stack",
        yaxis=dict(title="Nombre d'événements", gridcolor="#f0f0f0"),
        plot_bgcolor="white", paper_bgcolor="white",
        height=330, margin=dict(t=50, b=10),
        legend=dict(orientation="h", y=-0.18)
    )
    st.plotly_chart(fig_tone, use_container_width=True, config=CHART_CONFIG)

    # Keep avg_tone per month for insight text
    tone_m_avg = (
        df.groupby("event_month", as_index=False)
        .agg(avg_tone=("AvgTone", "mean"))
        .sort_values("event_month")
    )
    tone_m_avg["month_label"] = tone_m_avg["event_month"].map(MONTH_LABELS)

neg_pct_total  = (df["tone_category"] == "Négatif").mean() * 100
most_neg_month = tone_m_avg.loc[tone_m_avg["avg_tone"].idxmin(), "month_label"]
# Determine positive %
pos_pct_total = (df["tone_category"] == "Positif").mean() * 100
neu_pct_total = (df["tone_category"] == "Neutre").mean() * 100
avg_tone_val  = df["AvgTone"].mean()
gold_mean_val = df["GoldsteinScale"].mean()

st.markdown(f"""<div class="insight-box">
    <span class="insight-num">Insight Q2</span> — <b>{neg_pct_total:.0f}%</b> des événements
    ont un ton négatif, contre <b>{pos_pct_total:.0f}%</b> positif et <b>{neu_pct_total:.0f}%</b> neutre.
    Le ton moyen global est de <b>{avg_tone_val:+.2f}</b> (négatif &lt; 0 &lt; positif), confirmant
    que l'image internationale du Bénin est dominée par les tensions et les crises.
    Le mois de <b>{most_neg_month}</b> enregistre le ton le plus bas de l'année.
    L'échelle de Goldstein est en moyenne à <b>{gold_mean_val:+.2f}</b>.
    <div class="audience-grid">
        <div class="audience-card decideurs">
            <div class="audience-tag decideurs">🏛️ Décideurs</div>
            Accompagner systématiquement les crises d'une <b>communication positive</b>
            (coopération économique, progrès sociaux) pour rééquilibrer l'image.
            Cibler les mois à ton négatif pour des contre-narratifs.
        </div>
        <div class="audience-card journalistes">
            <div class="audience-tag journalistes">📰 Journalistes</div>
            <b>Angle</b> : Le ton négatif dominant ({neg_pct_total:.0f}%) reflète-t-il
            la réalité ou un <b>biais éditorial</b> des médias internationaux ?
            Comparer avec le ton des pays voisins (Togo, Ghana) pour mesurer ce biais.
        </div>
        <div class="audience-card chercheurs">
            <div class="audience-tag chercheurs">🔬 Chercheurs</div>
            <b>Piste</b> : Étudier la relation entre le score Goldstein ({gold_mean_val:+.2f})
            et AvgTone ({avg_tone_val:+.2f}). La divergence suggère que la stabilité
            géopolitique réelle diffère de la perception médiatique — un cas d'étude
            en <i>framing theory</i>.
        </div>
    </div>
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
        La couverture mondiale est <b>quasi instantanée</b> : un événement
        survenant à Cotonou ou Porto-Novo est visible dans les médias internationaux le jour même.
        <div class="audience-grid">
            <div class="audience-card decideurs">
                <div class="audience-tag decideurs">🏛️ Décideurs</div>
                Mettre en place une <b>cellule de veille GDELT automatisée</b>
                qui alerte dès qu'un événement béninois dépasse un seuil critique.
                Aucune fenêtre de temps n'existe pour préparer une réponse.
            </div>
            <div class="audience-card journalistes">
                <div class="audience-tag journalistes">📰 Journalistes</div>
                <b>Outil</b> : GDELT peut servir de <b>système d'alerte</b> pour les rédactions.
                {fast_pct:.0f}% des événements sont indexés en &lt;24h —
                idéal pour du fact-checking en temps réel et la détection de breaking news.
            </div>
            <div class="audience-card chercheurs">
                <div class="audience-tag chercheurs">🔬 Chercheurs</div>
                <b>Question</b> : Le délai de propagation varie-t-il selon le <b>type d'événement</b>
                (conflit vs coopération) ou la <b>source</b> (presse locale vs internationale) ?
                Étudier l'effet de la langue de publication sur la vitesse de diffusion.
            </div>
        </div>
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
    # Get max value to set proper xaxis range
    max_val = src["Occurrences"].max() if len(src) > 0 else 100
    fig.update_layout(
        plot_bgcolor="white", height=340,
        margin=dict(t=50, b=10, r=10), showlegend=False,
        yaxis=dict(autorange="reversed"),
        xaxis=dict(range=[0, max_val * 1.4])  # 40% padding for text
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
    ({n_src_crisis} sources uniques en crise contre {n_src_normal} en période normale).<br>
    {geo_note}<br>
    {crisis_only_note}
    <div class="audience-grid">
        <div class="audience-card decideurs">
            <div class="audience-tag decideurs">🏛️ Décideurs</div>
            {strategy_note.replace('→ ', '')}
            Renforcer la visibilité internationale de la <b>presse béninoise</b>
            pour diversifier la couverture et réduire la dépendance aux médias étrangers.
        </div>
        <div class="audience-card journalistes">
            <div class="audience-tag journalistes">📰 Journalistes</div>
            <b>Enquête</b> : Pourquoi 7/10 des sources sont nigérianes ?
            Investiguer l'<b>écosystème médiatique régional</b> et le rôle
            de la proximité géographique dans la couverture du Bénin.
            La presse béninoise est sous-représentée internationalement.
        </div>
        <div class="audience-card chercheurs">
            <div class="audience-tag chercheurs">🔬 Chercheurs</div>
            <b>Méthodologie</b> : Appliquer l'analyse de réseau (<i>network analysis</i>)
            aux flux d'information entre sources pour cartographier les
            <b>gatekeepers médiatiques</b> du Bénin. Comparer périodes normale/crise.
        </div>
    </div>
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
    <b>Contexte</b> dans <b>{ctx_p:.0f}%</b> des cas, <b>Acteur</b> dans <b>{actor_p:.0f}%</b>,
    <b>Spectateur</b> dans <b>{spec_p:.0f}%</b>, et <b>Mixte</b> dans <b>{mixte_p:.1f}%</b>.
    Quand le Bénin est acteur : <b>{top_actor_str}</b>. Actions : <b>{top_evt_str}</b>.
    <div class="audience-grid">
        <div class="audience-card decideurs">
            <div class="audience-tag decideurs">🏛️ Décideurs</div>
            Pour augmenter la proportion "Acteur", multiplier les
            <b>initiatives diplomatiques visibles</b> (sommets, accords bilatéraux,
            prises de position à l'ONU/UA/CEDEAO) et communiquer activement.
        </div>
        <div class="audience-card journalistes">
            <div class="audience-tag journalistes">📰 Journalistes</div>
            <b>Récit</b> : Le Bénin est surtout un <b>terrain d'événements</b> ({ctx_p:.0f}%)
            plutôt qu'un acteur. Quel impact sur la <b>souveraineté narrative</b>
            du pays ? Qui parle à la place du Bénin dans les médias mondiaux ?
        </div>
        <div class="audience-card chercheurs">
            <div class="audience-tag chercheurs">🔬 Chercheurs</div>
            <b>Cadre théorique</b> : Appliquer le concept de <i>media agency</i> —
            un pays "Contexte" subit sa représentation. Comparer le ratio
            Acteur/Contexte du Bénin avec d'autres pays ouest-africains.
        </div>
    </div>
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
    Types cachés : {top_hidden_str}.
    <div class="audience-grid">
        <div class="audience-card decideurs">
            <div class="audience-tag decideurs">🏛️ Décideurs</div>
            Ces événements sous-couverts méritent une <b>veille prioritaire</b>.
            Anticiper leur médiatisation potentielle en préparant des
            éléments de communication proactifs sur la sécurité et les droits humains.
        </div>
        <div class="audience-card journalistes">
            <div class="audience-tag journalistes">📰 Journalistes</div>
            <b>Exclusivité</b> : {len(hidden):,} événements graves non couverts par les
            grands médias. Ce sont des <b>sujets d'enquête</b> potentiels —
            violences et tensions ignorées par la presse internationale.
        </div>
        <div class="audience-card chercheurs">
            <div class="audience-tag chercheurs">🔬 Chercheurs</div>
            <b>Phénomène</b> : Pourquoi certains événements graves restent invisibles ?
            Étudier les facteurs d'<i>agenda-setting</i> et de <i>gatekeeping</i>
            qui déterminent la couverture médiatique internationale du Bénin.
        </div>
    </div>
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
    entre les 5 dimensions d'analyse.<br>
    {dynamic_corr_note}
    <div class="audience-grid">
        <div class="audience-card decideurs">
            <div class="audience-tag decideurs">🏛️ Décideurs</div>
            Ces corrélations guident le <b>timing des communications</b>.
            Communiquer positivement pendant les périodes de faible
            volume médiatique maximise l'impact sans être noyé par les crises.
        </div>
        <div class="audience-card journalistes">
            <div class="audience-tag journalistes">📰 Journalistes</div>
            <b>Data-journalisme</b> : Ces corrélations permettent de
            <b>prédire</b> quand un sujet béninois va exploser médiatiquement.
            L'effet boule de neige (Volume ↔ Sources) est un signal d'alerte.
        </div>
        <div class="audience-card chercheurs">
            <div class="audience-tag chercheurs">🔬 Chercheurs</div>
            <b>Modélisation</b> : Ces corrélations mensuelles valident
            un modèle de <i>media cascade</i> pour le Bénin.
            Tester avec des données journalières pour affiner la granularité.
        </div>
    </div>
</div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# NEW — GEOGRAPHIC MAP OF MEDIA COVERAGE
# ─────────────────────────────────────────────────────────────────

if "ActionGeo_Lat" in df.columns and "ActionGeo_Long" in df.columns:
    st.markdown(
        '<div class="section-title">🗺️ Carte géographique — Couverture médiatique mondiale du Bénin</div>',
        unsafe_allow_html=True
    )

    geo_df = df.dropna(subset=["ActionGeo_Lat", "ActionGeo_Long"]).copy()
    geo_df = geo_df[
        (geo_df["ActionGeo_Lat"].between(-90, 90)) &
        (geo_df["ActionGeo_Long"].between(-180, 180))
    ]

    if len(geo_df) > 0:
        # Aggregate by country for choropleth
        country_agg = (
            geo_df.groupby("ActionGeo_CountryCode", as_index=False)
            .agg(
                events=("SQLDATE", "count"),
                articles=("NumArticles", "sum"),
                avg_tone=("AvgTone", "mean")
            )
            .sort_values("events", ascending=False)
        )

        col_map, col_map_info = st.columns([3, 1])
        with col_map:
            # Scatter geo map with bubble sizes
            geo_agg = (
                geo_df.groupby(
                    ["ActionGeo_FullName", "ActionGeo_Lat", "ActionGeo_Long", "ActionGeo_CountryCode"],
                    as_index=False
                )
                .agg(events=("SQLDATE", "count"), articles=("NumArticles", "sum"))
                .sort_values("events", ascending=False)
                .head(100)  # Top 100 locations for performance
            )

            fig_map = px.scatter_geo(
                geo_agg,
                lat="ActionGeo_Lat",
                lon="ActionGeo_Long",
                size="events",
                color="events",
                hover_name="ActionGeo_FullName",
                hover_data={"articles": ":,", "events": ":,", "ActionGeo_Lat": False, "ActionGeo_Long": False},
                color_continuous_scale="YlOrRd",
                size_max=30,
                title="Localisation des événements médiatiques liés au Bénin",
                projection="natural earth"
            )
            fig_map.update_layout(
                height=500,
                margin=dict(t=50, b=10, l=0, r=0),
                coloraxis_colorbar=dict(title="Événements"),
                geo=dict(
                    showland=True, landcolor="#f0f0f0",
                    showocean=True, oceancolor="#e8f4f8",
                    showcountries=True, countrycolor="#d0d0d0",
                    showframe=False
                )
            )
            st.plotly_chart(fig_map, use_container_width=True, config=CHART_CONFIG)

        with col_map_info:
            st.markdown("#### 🌍 Top pays couverts")
            # Full country names for readability
            COUNTRY_NAMES = {
                "BN": "Bénin", "NI": "Nigeria", "NG": "Nigeria",
                "FR": "France", "GH": "Ghana", "TO": "Togo",
                "US": "États-Unis", "UK": "Royaume-Uni", "GB": "Royaume-Uni",
                "CH": "Chine", "CI": "Côte d'Ivoire", "SN": "Sénégal",
                "UV": "Burkina Faso", "DE": "Allemagne", "CA": "Canada",
                "SF": "Afrique du Sud", "ZA": "Afrique du Sud",
                "CM": "Cameroun", "ML": "Mali", "NE": "Niger",
                "IN": "Inde", "BR": "Brésil", "JP": "Japon",
                "BE": "Belgique", "IT": "Italie", "ES": "Espagne",
            }
            top_countries = country_agg.head(10)
            for _, row in top_countries.iterrows():
                cc = row["ActionGeo_CountryCode"]
                name = COUNTRY_NAMES.get(cc, cc)
                ev = int(row["events"])
                tone_val = row["avg_tone"]
                tone_icon = "🟢" if tone_val > 0 else "🔴"
                st.markdown(
                    f"**{name}** — {ev:,} év. {tone_icon} ({tone_val:+.1f})"
                )

        # Timeline: cumulative daily events showing how coverage spreads
        st.markdown("##### ⏳ Propagation de la couverture médiatique dans le temps")

        geo_df["event_date"] = pd.to_datetime(geo_df["SQLDATE"], errors="coerce")
        daily_coverage = (
            geo_df.dropna(subset=["event_date"])
            .groupby("event_date", as_index=False)
            .agg(
                events=("GLOBALEVENTID", "count"),
                countries=("ActionGeo_CountryCode", "nunique"),
                sources=("source_domain", "nunique"),
                articles=("NumArticles", "sum")
            )
            .sort_values("event_date")
        )
        daily_coverage["cumul_events"] = daily_coverage["events"].cumsum()
        daily_coverage["cumul_countries"] = daily_coverage["countries"].cummax()

        fig_timeline = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.6, 0.4],
            subplot_titles=(
                "Événements par jour (volume brut)",
                "Nombre de pays couverts par jour"
            ),
            vertical_spacing=0.12
        )

        fig_timeline.add_trace(
            go.Bar(
                x=daily_coverage["event_date"],
                y=daily_coverage["events"],
                marker_color="#1a56db",
                name="Événements/jour",
                hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y} événements<extra></extra>"
            ), row=1, col=1
        )

        fig_timeline.add_trace(
            go.Scatter(
                x=daily_coverage["event_date"],
                y=daily_coverage["countries"],
                mode="lines+markers",
                marker=dict(size=3, color="#7e3af2"),
                line=dict(color="#7e3af2", width=1.5),
                name="Pays touchés/jour",
                hovertemplate="<b>%{x|%d %b %Y}</b><br>%{y} pays<extra></extra>"
            ), row=2, col=1
        )

        fig_timeline.update_layout(
            height=450,
            plot_bgcolor="white", paper_bgcolor="white",
            margin=dict(t=50, b=10),
            showlegend=False
        )
        fig_timeline.update_xaxes(gridcolor="#f0f0f0")
        fig_timeline.update_yaxes(gridcolor="#f0f0f0")
        st.plotly_chart(fig_timeline, use_container_width=True, config=CHART_CONFIG)

        st.markdown(f"""<div class="insight-box">
            <span class="insight-num">Insight Géo</span> — La couverture médiatique du Bénin
            est concentrée dans <b>{len(country_agg)} pays</b>.
            Les 3 premiers pays ({', '.join(country_agg['ActionGeo_CountryCode'].head(3).tolist())})
            représentent la majorité des événements.
            <div class="audience-grid">
                <div class="audience-card decideurs">
                    <div class="audience-tag decideurs">🏛️ Décideurs</div>
                    La carte révèle les <b>zones de couverture</b> les plus denses.
                    Cibler la communication vers les pays qui couvrent le plus le Bénin.
                </div>
                <div class="audience-card journalistes">
                    <div class="audience-tag journalistes">📰 Journalistes</div>
                    <b>Géographie de l'information</b> : d'où viennent les événements couverts ?
                    Les zones blanches sont des <b>angles morts médiatiques</b> à explorer.
                </div>
                <div class="audience-card chercheurs">
                    <div class="audience-tag chercheurs">🔬 Chercheurs</div>
                    <b>Analyse spatiale</b> : la couverture suit-elle les flux économiques,
                    les diasporas ou les alliances géopolitiques ?
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# NEW — DOMINANT TOPICS FOR JOURNALISTS
# ─────────────────────────────────────────────────────────────────

if "event_root_label" in df.columns:
    st.markdown(
        '<div class="section-title">📰 Sujets dominants — Thématiques clés pour les journalistes</div>',
        unsafe_allow_html=True
    )

    col_topics1, col_topics2 = st.columns(2)

    with col_topics1:
        # Top subjects per month (heatmap)
        topic_month = (
            df.groupby(["event_month", "event_root_label"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
        )
        top_topics = df["event_root_label"].value_counts().head(8).index.tolist()
        topic_month = topic_month[topic_month["event_root_label"].isin(top_topics)]
        topic_pivot = topic_month.pivot_table(
            index="event_root_label", columns="event_month", values="count", fill_value=0
        )
        topic_pivot.columns = [MONTH_LABELS.get(m, str(m)) for m in topic_pivot.columns]

        fig_heatmap = go.Figure(data=go.Heatmap(
            z=topic_pivot.values,
            x=topic_pivot.columns.tolist(),
            y=topic_pivot.index.tolist(),
            colorscale="YlOrRd",
            hoverongaps=False,
            hovertemplate="<b>%{y}</b><br>%{x}<br>%{z} événements<extra></extra>"
        ))
        fig_heatmap.update_layout(
            title="Heatmap — Sujets dominants par mois",
            height=380, margin=dict(t=50, b=10),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(tickangle=-45)
        )
        st.plotly_chart(fig_heatmap, use_container_width=True, config=CHART_CONFIG)

    with col_topics2:
        # Emerging/trending topics: month-over-month growth
        topic_growth = (
            df.groupby(["event_month", "event_root_label"], as_index=False)
            .size()
            .rename(columns={"size": "count"})
        )
        # Compare last month to previous
        last_month = df["event_month"].max()
        prev_month = last_month - 1 if last_month > 1 else 1

        last_topics = topic_growth[topic_growth["event_month"] == last_month].set_index("event_root_label")["count"]
        prev_topics = topic_growth[topic_growth["event_month"] == prev_month].set_index("event_root_label")["count"]

        growth_df = pd.DataFrame({
            "last": last_topics,
            "prev": prev_topics
        }).fillna(0)
        growth_df["change"] = growth_df["last"] - growth_df["prev"]
        growth_df["pct_change"] = (growth_df["change"] / growth_df["prev"].replace(0, 1) * 100).round(0)
        growth_df = growth_df.sort_values("change", ascending=True).tail(10).reset_index()
        growth_df.columns = ["Sujet", "Dernier mois", "Mois précédent", "Variation", "Variation %"]

        colors = ["#d63031" if v < 0 else "#00b894" for v in growth_df["Variation"]]
        fig_growth = go.Figure(go.Bar(
            x=growth_df["Variation"],
            y=growth_df["Sujet"],
            orientation="h",
            marker_color=colors,
            text=growth_df["Variation"].apply(lambda v: f"{v:+.0f}"),
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Variation : %{x:+,}<extra></extra>"
        ))
        last_month_name = MONTH_LABELS.get(int(last_month), str(last_month))
        prev_month_name = MONTH_LABELS.get(int(prev_month), str(prev_month))
        fig_growth.update_layout(
            title=f"Sujets émergents ({prev_month_name} → {last_month_name})",
            height=380, margin=dict(t=50, b=10, r=50),
            plot_bgcolor="white", paper_bgcolor="white",
            xaxis=dict(title="Variation (événements)"),
            showlegend=False
        )
        st.plotly_chart(fig_growth, use_container_width=True, config=CHART_CONFIG)

    # Under-covered topics (many events, few articles)
    topic_coverage = (
        df.groupby("event_root_label", as_index=False)
        .agg(events=("SQLDATE", "count"), articles=("NumArticles", "sum"))
    )
    topic_coverage["articles_per_event"] = (topic_coverage["articles"] / topic_coverage["events"]).round(1)
    under_covered = topic_coverage[topic_coverage["events"] >= 50].nsmallest(5, "articles_per_event")
    under_str = ", ".join(
        [f"**{r['event_root_label']}** ({r['articles_per_event']:.1f} art/év)" for _, r in under_covered.iterrows()]
    ) if len(under_covered) > 0 else "N/A"

    top_subject = df["event_root_label"].value_counts().head(1)
    top_name = top_subject.index[0] if len(top_subject) > 0 else "N/A"
    top_count = int(top_subject.values[0]) if len(top_subject) > 0 else 0

    # Glossary of GDELT event types for clarity
    EVENT_GLOSSARY = {
        "Consultation": "discussions diplomatiques, négociations, réunions formelles entre États",
        "Déclaration publique": "annonces officielles, discours, communiqués de presse",
        "Engagement / Soutien": "aide, coopération, accords, partenariats",
        "Appel": "demandes publiques, appels à l'action, requêtes diplomatiques",
        "Violence de masse": "conflits armés, attaques, violences collectives",
        "Expression d'intention": "intentions déclarées de coopérer, de négocier ou d'agir",
        "Désapprobation": "critiques, condamnations, réprobations officielles",
        "Assaut": "attaques physiques, agressions, opérations militaires",
        "Protestation": "manifestations, grèves, mouvements sociaux",
        "Menace": "menaces verbales, intimidations, avertissements",
        "Aide matérielle": "dons, aide humanitaire, fourniture de matériel",
        "Attentat": "attentats à la bombe, actes terroristes",
    }
    top_glossary = EVENT_GLOSSARY.get(top_name, "")
    top_explain = f" (<i>{top_glossary}</i>)" if top_glossary else ""

    st.markdown(f"""<div class="insight-box">
        <span class="insight-num">Insight Sujets</span> — Le sujet dominant est
        <b>{top_name}</b>{top_explain} avec {top_count:,} événements.
        Les sujets les moins couverts proportionnellement : {under_str}.
        <br><br>
        <b>📚 Glossaire des types d'événements GDELT</b> :<br>
        <small>
        • <b>Consultation</b> = discussions diplomatiques, négociations, réunions entre États<br>
        • <b>Déclaration publique</b> = annonces officielles, discours, communiqués<br>
        • <b>Engagement / Soutien</b> = aide, coopération, accords, partenariats<br>
        • <b>Violence de masse</b> = conflits armés, violences collectives<br>
        • <b>Assaut</b> = attaques physiques, opérations militaires<br>
        • <b>Désapprobation</b> = critiques, condamnations officielles<br>
        • <b>Protestation</b> = manifestations, grèves, mouvements sociaux
        </small>
        <div class="audience-grid">
            <div class="audience-card decideurs">
                <div class="audience-tag decideurs">🏛️ Décideurs</div>
                La heatmap révèle la <b>saisonnalité thématique</b> : certains sujets
                culminent à des mois précis. Utile pour planifier les réponses institutionnelles.
            </div>
            <div class="audience-card journalistes">
                <div class="audience-tag journalistes">📰 Journalistes</div>
                <b>Sujets émergents</b> : le graphique de droite montre les thèmes en
                <b>forte hausse</b> ce mois — des angles d'actualité à investiguer.
                Les sujets sous-couverts sont des <b>exclusivités potentielles</b>.
            </div>
            <div class="audience-card chercheurs">
                <div class="audience-tag chercheurs">🔬 Chercheurs</div>
                <b>Topic modeling</b> : la heatmap valide l'existence de cycles thématiques.
                Appliquer LDA ou BERTopic sur les titres d'articles pour affiner la classification.
            </div>
        </div>
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
# MODÈLE ML — Performance du classifieur de ton
# ─────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="section-title">Modèle ML — Prédiction du ton médiatique</div>',
    unsafe_allow_html=True
)

st.markdown(
    "Un classifieur **Random Forest** prédit le ton (Positif / Neutre / Négatif) "
    "d'un événement béninois à partir de 9 variables GDELT (intensité Goldstein, "
    "volume d'articles, mois, type CAMEO, rôle du Bénin, etc.). "
    "Évalué sur un test set stratifié de **6 301 lignes** (20 % du jeu de données ML)."
)

col_ml1, col_ml2, col_ml3, col_ml4 = st.columns(4)
with col_ml1:
    st.metric("Accuracy (test)", "55 %", help="Taux de prédictions correctes sur le test set")
with col_ml2:
    st.metric("F1 weighted (test)", "0,55", help="F1-score pondéré par le support des classes")
with col_ml3:
    st.metric("F1 CV 5-fold", "0,549 ± 0,009", help="Validation croisée 5-fold sur le train set")
with col_ml4:
    st.metric("F1 classe Négatif", "0,64", help="Meilleure performance — classe majoritaire")

col_cm, col_fi = st.columns([3, 2])

with col_cm:
    st.markdown("**Matrice de confusion & importance des variables**")
    cm_path = ROOT / "models" / "confusion_matrix_feature_importance.png"
    if cm_path.exists():
        st.image(str(cm_path), use_column_width=True)
    else:
        st.info("Image non disponible. Régénérer via le notebook.")

with col_fi:
    st.markdown("**Top des variables prédictives (Gini)**")
    feature_importance = pd.DataFrame({
        "Variable": [
            "GoldsteinScale",
            "event_month",
            "event_root_label",
            "QuadClass",
            "NumArticles",
            "NumMentions",
            "benin_role",
            "IsRootEvent",
            "NumSources",
        ],
        "Importance": [0.272, 0.217, 0.129, 0.121, 0.068, 0.068, 0.063, 0.060, 0.003],
    }).sort_values("Importance", ascending=True)

    fig_fi = px.bar(
        feature_importance,
        x="Importance", y="Variable",
        orientation="h",
        text=feature_importance["Importance"].map(lambda v: f"{v*100:.1f} %"),
        color="Importance",
        color_continuous_scale="Blues",
    )
    fig_fi.update_traces(textposition="outside")
    fig_fi.update_layout(
        height=380, plot_bgcolor="white",
        coloraxis_showscale=False,
        margin=dict(t=10, b=10, l=10, r=40),
        xaxis=dict(showgrid=True, gridcolor="#e5e7eb", tickformat=".0%"),
        yaxis=dict(title=""),
    )
    st.plotly_chart(fig_fi, use_container_width=True, config=CHART_CONFIG)

st.markdown("""
<div class="insight-box">
<span class="insight-num">Lecture du modèle.</span>
L'<b>intensité Goldstein</b> (stabilité de l'événement) et la <b>saisonnalité</b>
expliquent à elles seules près de la moitié du pouvoir prédictif. Autrement dit,
<b>la nature de l'événement et le moment de l'année comptent davantage que le volume
de couverture médiatique</b> pour anticiper le ton. Le modèle reconnaît particulièrement
bien la classe <b>Négatif</b> (F1 = 0,64), la plus utile pour anticiper les crises
de communication. La classe Neutre, plus floue par définition, reste le défi.
</div>
""", unsafe_allow_html=True)

cta_left, cta_right = st.columns([3, 2])
with cta_left:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a56db 0%, #7e3af2 100%);
                color: white; padding: 1.1rem 1.4rem; border-radius: 10px;
                margin: 0.5rem 0;">
        <div style="font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.06em; opacity: 0.9;">
            Anticipez la couverture médiatique
        </div>
        <div style="font-size: 1.05rem; font-weight: 600; margin-top: 0.3rem; line-height: 1.4;">
            Décrivez un événement et voyez comment les médias mondiaux sont
            susceptibles d'en parler — avant même qu'il ne soit public.
        </div>
    </div>
    """, unsafe_allow_html=True)
with cta_right:
    st.write("")
    try:
        st.page_link(
            "pages/2_Anticiper_la_couverture.py",
            label="Anticiper la couverture d'un événement →",
            use_container_width=True,
        )
    except Exception:
        st.info("Ouvrez la page **Anticiper la couverture** dans le menu de gauche pour tester le modèle.")

with st.expander("Pourquoi Random Forest plutôt qu'un autre modèle ?"):
    st.markdown("""
- **Robuste au déséquilibre de classes** (44 % Négatif / 32 % Neutre / 24 % Positif) via `class_weight="balanced"`.
- **Interprétable** : `feature_importances_` permet de relier les prédictions à des variables analytiques claires (Goldstein, CAMEO) — utile pour le storytelling auprès des décideurs.
- **Pas de scaling requis** → pipeline simple et reproductible.
- **Baseline Logistic Regression** également entraîné dans le notebook : Random Forest le surpasse, validant l'hypothèse que les relations entre variables GDELT et ton sont non linéaires.
- **Pistes Phase 2** : XGBoost, ensembling RF + GBM, embeddings de texte sur les `SOURCEURL`.
""")

# ─────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<center style='color:#9ca3af; font-size:0.8rem;'>"
    "Bénin Insights Challenge 2026 · IROKO Analytics (Équipe 7) · iSHEERO × DataCamp Donates · "
    "Données : GDELT Project (gdelt-bq.gdeltv2.events) · Période : Jan–Déc 2025"
    "</center>",
    unsafe_allow_html=True
)


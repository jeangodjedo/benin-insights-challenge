"""
Bénin Insights Challenge 2026 — Anticiper la couverture médiatique
IROKO Analytics (Équipe 7)

Page interactive accessible aux 3 publics cibles (décideurs, journalistes, chercheurs)
via 3 modes d'utilisation :
  1. Scénarios prédéfinis    — clic sur un cas concret (le plus accessible)
  2. Mode guidé              — 5 questions en langage naturel
  3. Mode avancé             — formulaire technique GDELT (data scientists)
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import joblib

# ─────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Anticiper la couverture · Bénin Insights",
    page_icon="BJ",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
.page-header {
    background: linear-gradient(135deg, #1a56db 0%, #7e3af2 100%);
    color: white; padding: 1.8rem 2.2rem; border-radius: 12px; margin-bottom: 1.5rem;
}
.page-header h1 { margin: 0; font-size: 1.8rem; font-weight: 700; }
.page-header p  { margin: 0.4rem 0 0; opacity: 0.9; font-size: 0.95rem; }

.section-title {
    font-size: 1.1rem; font-weight: 700; color: #111827;
    border-left: 4px solid #1a56db; padding-left: 0.75rem;
    margin: 1.5rem 0 0.8rem;
}

.scenario-num {
    display: inline-block; background: #1a56db; color: white;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.05em;
    padding: 0.15rem 0.5rem; border-radius: 4px; margin-right: 0.5rem;
}

.prediction-card {
    border-radius: 14px; padding: 1.6rem 1.8rem; text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.08);
    margin-bottom: 1rem;
}
.prediction-card.positif  { background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%); border: 2px solid #00b894; }
.prediction-card.neutre   { background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border: 2px solid #fdcb6e; }
.prediction-card.negatif  { background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); border: 2px solid #d63031; }

.prediction-label { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.06em;
                    color: #6b7280; margin-bottom: 0.4rem; font-weight: 600; }
.prediction-value { font-size: 2.6rem; font-weight: 800; line-height: 1; }
.prediction-value.positif  { color: #047857; }
.prediction-value.neutre   { color: #92400e; }
.prediction-value.negatif  { color: #991b1b; }
.prediction-conf  { font-size: 0.95rem; color: #374151; margin-top: 0.5rem; }

.interpretation-box {
    background: #f8fafc; border-left: 4px solid #7e3af2;
    border-radius: 6px; padding: 0.95rem 1.15rem; margin: 0.6rem 0;
    font-size: 0.9rem; color: #374151; line-height: 1.55;
}

.summary-box {
    background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px;
    padding: 0.8rem 1rem; font-size: 0.85rem; color: #1e3a8a; line-height: 1.5;
    margin-bottom: 0.6rem;
}

footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# MODEL + ENCODERS LOADING
# ─────────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Chargement du modèle Random Forest...")
def load_model_artifacts():
    model_path = ROOT / "models" / "tone_classifier_rf.pkl"
    role_path  = ROOT / "models" / "encoder_benin_role.pkl"
    event_path = ROOT / "models" / "encoder_event_root.pkl"

    if not model_path.exists():
        return None, None, None
    return (
        joblib.load(model_path),
        joblib.load(role_path),
        joblib.load(event_path),
    )


model, le_role, le_event = load_model_artifacts()

if model is None:
    st.error("Modèle non trouvé. Lancez d'abord le notebook pour générer `models/tone_classifier_rf.pkl`.")
    st.stop()

# ─────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────

MONTH_LABELS = {
    1: "Janvier",  2: "Février", 3: "Mars",      4: "Avril",
    5: "Mai",      6: "Juin",    7: "Juillet",   8: "Août",
    9: "Septembre",10: "Octobre",11: "Novembre", 12: "Décembre"
}

QUADCLASS_LABELS = {
    1: "Coopération verbale (déclarations, accords verbaux)",
    2: "Coopération matérielle (signatures, aide concrète)",
    3: "Conflit verbal (menaces, désapprobations)",
    4: "Conflit matériel (violences, sanctions)",
}

TONE_COLORS_HEX = {"Positif": "#00b894", "Neutre": "#fdcb6e", "Négatif": "#d63031"}
TONE_CSS_CLASS  = {"Positif": "positif", "Neutre": "neutre", "Négatif": "negatif"}

# Feature order MUST match training order
FEATURE_COLS = [
    "GoldsteinScale", "NumArticles", "NumMentions", "NumSources",
    "event_month", "IsRootEvent", "QuadClass",
    "benin_role_enc", "event_root_label_enc",
]

# ─────────────────────────────────────────────────────────────────
# MAPPINGS — natural language → technical features
# ─────────────────────────────────────────────────────────────────

ATTENTION_MAP = {
    "Faible (sujet local, peu repris)":          {"NumArticles":   5, "NumMentions":   8, "NumSources":   3},
    "Moyenne (sujet régional, quelques médias)": {"NumArticles":  30, "NumMentions":  50, "NumSources":  12},
    "Forte (sujet international, large reprise)":{"NumArticles": 100, "NumMentions": 150, "NumSources":  40},
    "Virale (couverture mondiale massive)":      {"NumArticles": 500, "NumMentions": 800, "NumSources": 150},
}

GRAVITY_MAP = {
    "Très grave (violence, crise humanitaire, drame)":         -8.0,
    "Grave (tension, conflit, désaccord important)":           -4.0,
    "Neutre (information factuelle sans charge particulière)":  0.0,
    "Positif (accord, progrès, succès)":                       +4.0,
    "Très positif (accord historique, exploit, paix)":         +7.5,
}

SCENARIOS = [
    {
        "id": "diplo_accord",
        "num": "01",
        "title": "Signature d'un accord de coopération internationale",
        "desc": "Le Bénin signe un accord avec un partenaire étranger (économique, sécuritaire, culturel).",
        "params": {
            "event_label": "Coopération", "benin_role": "Acteur",
            "event_month": 6, "goldstein": 6.0, "quadclass": 2,
            "is_root": True, "attention": "Moyenne (sujet régional, quelques médias)",
        },
    },
    {
        "id": "visite_diplomatique",
        "num": "02",
        "title": "Visite officielle d'un chef d'État étranger",
        "desc": "Réception d'un haut dignitaire étranger à Cotonou.",
        "params": {
            "event_label": "Diplomatie", "benin_role": "Spectateur",
            "event_month": 5, "goldstein": 5.0, "quadclass": 1,
            "is_root": True, "attention": "Moyenne (sujet régional, quelques médias)",
        },
    },
    {
        "id": "declaration",
        "num": "03",
        "title": "Déclaration officielle du gouvernement",
        "desc": "Communiqué présidentiel ou ministériel sur un sujet d'intérêt national.",
        "params": {
            "event_label": "Déclaration publique", "benin_role": "Acteur",
            "event_month": 5, "goldstein": 0.0, "quadclass": 1,
            "is_root": True, "attention": "Faible (sujet local, peu repris)",
        },
    },
    {
        "id": "operation_securite",
        "num": "04",
        "title": "Réussite d'une opération de sécurité",
        "desc": "Démantèlement d'un groupe armé, arrestation de cybercriminels, etc.",
        "params": {
            "event_label": "Aide matérielle", "benin_role": "Acteur",
            "event_month": 7, "goldstein": 3.0, "quadclass": 2,
            "is_root": True, "attention": "Moyenne (sujet régional, quelques médias)",
        },
    },
    {
        "id": "coup_etat",
        "num": "05",
        "title": "Tentative de coup d'État ou trouble politique majeur",
        "desc": "Crise politique grave — type décembre 2025.",
        "params": {
            "event_label": "Assaut", "benin_role": "Spectateur",
            "event_month": 12, "goldstein": -8.0, "quadclass": 4,
            "is_root": True, "attention": "Virale (couverture mondiale massive)",
        },
    },
    {
        "id": "attentat",
        "num": "06",
        "title": "Attentat ou attaque armée contre des civils",
        "desc": "Action terroriste ou violence armée ciblée.",
        "params": {
            "event_label": "Attentat / Explosion", "benin_role": "Spectateur",
            "event_month": 3, "goldstein": -9.0, "quadclass": 4,
            "is_root": True, "attention": "Forte (sujet international, large reprise)",
        },
    },
    {
        "id": "manifestation",
        "num": "07",
        "title": "Manifestation ou mouvement de protestation",
        "desc": "Mobilisation populaire contre une décision publique.",
        "params": {
            "event_label": "Protestation", "benin_role": "Spectateur",
            "event_month": 4, "goldstein": -4.0, "quadclass": 3,
            "is_root": True, "attention": "Moyenne (sujet régional, quelques médias)",
        },
    },
    {
        "id": "infrastructure",
        "num": "08",
        "title": "Inauguration d'une infrastructure majeure",
        "desc": "Port, aéroport, route, hôpital, école — investissement public visible.",
        "params": {
            "event_label": "Engagement / Soutien", "benin_role": "Acteur",
            "event_month": 9, "goldstein": 5.0, "quadclass": 2,
            "is_root": True, "attention": "Faible (sujet local, peu repris)",
        },
    },
    {
        "id": "sanctions",
        "num": "09",
        "title": "Sanctions économiques ou diplomatiques (subies)",
        "desc": "Le Bénin se retrouve sous sanctions internationales.",
        "params": {
            "event_label": "Sanctions économiques", "benin_role": "Spectateur",
            "event_month": 10, "goldstein": -6.0, "quadclass": 3,
            "is_root": True, "attention": "Forte (sujet international, large reprise)",
        },
    },
    {
        "id": "droits_humains",
        "num": "10",
        "title": "Polémique autour des droits humains",
        "desc": "ONG ou organisme international met en cause des pratiques au Bénin.",
        "params": {
            "event_label": "Violation droits humains", "benin_role": "Spectateur",
            "event_month": 8, "goldstein": -5.0, "quadclass": 3,
            "is_root": True, "attention": "Moyenne (sujet régional, quelques médias)",
        },
    },
    {
        "id": "menace_externe",
        "num": "11",
        "title": "Menace ou ultimatum d'un acteur externe",
        "desc": "Pays voisin ou groupe armé menace la stabilité béninoise.",
        "params": {
            "event_label": "Menace", "benin_role": "Spectateur",
            "event_month": 11, "goldstein": -6.5, "quadclass": 3,
            "is_root": True, "attention": "Forte (sujet international, large reprise)",
        },
    },
    {
        "id": "consultation_inter",
        "num": "12",
        "title": "Consultation ou sommet international",
        "desc": "Le Bénin participe à un sommet régional (CEDEAO, UA, ONU).",
        "params": {
            "event_label": "Consultation", "benin_role": "Mixte",
            "event_month": 6, "goldstein": 3.0, "quadclass": 1,
            "is_root": True, "attention": "Moyenne (sujet régional, quelques médias)",
        },
    },
]


def predict_from_params(event_label, benin_role, event_month, goldstein,
                        quadclass, is_root, num_articles, num_mentions, num_sources):
    """Run the model prediction from a fully-specified parameter set."""
    benin_role_enc       = int(le_role.transform([benin_role])[0])
    event_root_label_enc = int(le_event.transform([event_label])[0])

    X_input = pd.DataFrame([[
        float(goldstein), int(num_articles), int(num_mentions), int(num_sources),
        int(event_month), int(is_root), int(quadclass),
        benin_role_enc, event_root_label_enc,
    ]], columns=FEATURE_COLS)

    pred_class = model.predict(X_input)[0]
    pred_proba = model.predict_proba(X_input)[0]
    return pred_class, dict(zip(model.classes_, pred_proba))


def render_prediction(pred_class, proba_by_class, summary_lines):
    """Render the prediction card + probability chart + interpretation."""
    confidence = proba_by_class[pred_class]
    css_class = TONE_CSS_CLASS.get(pred_class, "neutre")

    st.markdown(f"""
    <div class="prediction-card {css_class}">
        <div class="prediction-label">Ton médiatique prédit</div>
        <div class="prediction-value {css_class}">{pred_class}</div>
        <div class="prediction-conf">Confiance du modèle : <b>{confidence*100:.1f} %</b></div>
    </div>
    """, unsafe_allow_html=True)

    col_p1, col_p2 = st.columns([3, 2])
    with col_p1:
        proba_df = pd.DataFrame({
            "Classe": list(proba_by_class.keys()),
            "Probabilité": [p * 100 for p in proba_by_class.values()],
        })
        fig = go.Figure(go.Bar(
            x=proba_df["Probabilité"], y=proba_df["Classe"], orientation="h",
            text=[f"{p:.1f} %" for p in proba_df["Probabilité"]],
            textposition="outside",
            marker_color=[TONE_COLORS_HEX.get(c, "#9ca3af") for c in proba_df["Classe"]],
        ))
        fig.update_layout(
            title="Probabilité par classe",
            xaxis=dict(title="Probabilité (%)", range=[0, 110], showgrid=True, gridcolor="#e5e7eb"),
            yaxis=dict(title=""),
            height=260, margin=dict(t=50, b=20, l=10, r=40),
            plot_bgcolor="white",
        )
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with col_p2:
        st.markdown("**Récapitulatif de l'événement**")
        st.markdown(
            "<div class='summary-box'>" + "<br>".join(summary_lines) + "</div>",
            unsafe_allow_html=True,
        )

    if pred_class == "Négatif":
        msg = ("Le modèle anticipe une couverture **majoritairement négative**. "
               "Pour un décideur, ce type d'événement appelle une **communication "
               "proactive** et une stratégie de gestion de crise pour rééquilibrer "
               "le narratif international.")
    elif pred_class == "Positif":
        msg = ("Le modèle anticipe une couverture **majoritairement positive**. "
               "C'est une **fenêtre d'opportunité** pour amplifier le message via "
               "communiqués officiels, interviews et relais diplomatiques.")
    else:
        msg = ("Le modèle anticipe une couverture **plutôt neutre** — l'événement "
               "est susceptible d'être traité de façon factuelle. Aucune action "
               "communicationnelle particulière n'est suggérée.")

    st.markdown(f"""
    <div class="interpretation-box">
        <b>Lecture analytique.</b> {msg}
        <br><br>
        <i>Méthodologie : modèle Random Forest entraîné sur 31 505 événements GDELT 2025
        (accuracy 55 %, F1 weighted 0,55, classe Négatif F1 = 0,64). Cette prédiction
        repose sur les caractéristiques structurelles de l'événement, sans analyse
        textuelle des articles.</i>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────

st.markdown("""
<div class="page-header">
    <h1>Anticiper la couverture médiatique d'un événement</h1>
    <p>Décrivez un événement au Bénin. Le modèle vous indique en temps réel comment
    les médias mondiaux sont susceptibles d'en parler. Trois modes selon votre profil.</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────
# MODE SELECTION
# ─────────────────────────────────────────────────────────────────

tab_scenarios, tab_guided, tab_advanced = st.tabs([
    "Scénarios prédéfinis",
    "Mode guidé (langage naturel)",
    "Mode avancé (technique)",
])

# ─────────────────────────────────────────────────────────────────
# TAB 1 — SCENARIOS
# ─────────────────────────────────────────────────────────────────

with tab_scenarios:
    st.markdown(
        "Cliquez sur le scénario qui ressemble le plus à votre situation. "
        "L'outil fait toute la traduction technique pour vous."
    )

    cols = st.columns(3)
    for i, sc in enumerate(SCENARIOS):
        with cols[i % 3]:
            if st.button(
                f"**{sc['num']}**  ·  **{sc['title']}**\n\n*{sc['desc']}*",
                key=f"sc_{sc['id']}",
                use_container_width=True,
            ):
                st.session_state["selected_scenario"] = sc

    sc = st.session_state.get("selected_scenario")
    if sc:
        st.markdown('<div class="section-title">Résultat de la prédiction</div>', unsafe_allow_html=True)
        p = sc["params"]
        att = ATTENTION_MAP[p["attention"]]
        pred_class, proba_by_class = predict_from_params(
            event_label=p["event_label"], benin_role=p["benin_role"],
            event_month=p["event_month"], goldstein=p["goldstein"],
            quadclass=p["quadclass"], is_root=p["is_root"],
            num_articles=att["NumArticles"], num_mentions=att["NumMentions"],
            num_sources=att["NumSources"],
        )
        summary = [
            f"<b>Scénario {sc['num']} :</b> {sc['title']}",
            f"<b>Type :</b> {p['event_label']} · <b>Rôle Bénin :</b> {p['benin_role']}",
            f"<b>Mois :</b> {MONTH_LABELS[p['event_month']]} · <b>Attention :</b> {p['attention'].split(' (')[0]}",
        ]
        render_prediction(pred_class, proba_by_class, summary)

# ─────────────────────────────────────────────────────────────────
# TAB 2 — GUIDED MODE (5 questions in plain French)
# ─────────────────────────────────────────────────────────────────

with tab_guided:
    st.markdown(
        "Répondez à 5 questions simples. Aucune connaissance technique requise."
    )

    col_g1, col_g2 = st.columns(2)

    with col_g1:
        g_event = st.selectbox(
            "1. Quel type d'événement décrivez-vous ?",
            options=sorted(le_event.classes_),
            help="Catégorie qui décrit le mieux l'action principale.",
        )
        g_role = st.selectbox(
            "2. Quel est le rôle du Bénin dans cet événement ?",
            options=["Acteur", "Spectateur", "Mixte", "Contexte"],
            format_func=lambda x: {
                "Acteur": "Acteur — le Bénin initie l'action",
                "Spectateur": "Spectateur — le Bénin est ciblé / subit l'action",
                "Mixte": "Mixte — interaction multi-acteurs",
                "Contexte": "Contexte — l'événement se passe juste sur le territoire",
            }[x],
        )
        g_month = st.selectbox(
            "3. À quel mois cet événement aurait-il lieu ?",
            options=list(range(1, 13)),
            format_func=lambda m: MONTH_LABELS[m],
        )

    with col_g2:
        g_gravity = st.selectbox(
            "4. Quelle est la gravité ressentie de l'événement ?",
            options=list(GRAVITY_MAP.keys()),
            index=2,
        )
        g_attention = st.selectbox(
            "5. Quelle attention médiatique attendez-vous ?",
            options=list(ATTENTION_MAP.keys()),
            index=1,
        )
        g_is_root = True
        if g_gravity in ["Très grave (violence, crise humanitaire, drame)",
                         "Grave (tension, conflit, désaccord important)"]:
            g_quadclass = 4 if "Très grave" in g_gravity else 3
        elif g_gravity == "Neutre (information factuelle sans charge particulière)":
            g_quadclass = 1
        else:
            g_quadclass = 2

    if st.button("Lancer la prédiction", type="primary", use_container_width=True, key="guided_btn"):
        att = ATTENTION_MAP[g_attention]
        pred_class, proba_by_class = predict_from_params(
            event_label=g_event, benin_role=g_role,
            event_month=g_month, goldstein=GRAVITY_MAP[g_gravity],
            quadclass=g_quadclass, is_root=g_is_root,
            num_articles=att["NumArticles"], num_mentions=att["NumMentions"],
            num_sources=att["NumSources"],
        )
        st.markdown('<div class="section-title">Résultat de la prédiction</div>', unsafe_allow_html=True)
        summary = [
            f"<b>Type :</b> {g_event}",
            f"<b>Rôle Bénin :</b> {g_role}",
            f"<b>Mois :</b> {MONTH_LABELS[g_month]}",
            f"<b>Gravité :</b> {g_gravity.split(' (')[0]}",
            f"<b>Attention :</b> {g_attention.split(' (')[0]}",
        ]
        render_prediction(pred_class, proba_by_class, summary)

# ─────────────────────────────────────────────────────────────────
# TAB 3 — ADVANCED MODE (raw GDELT features)
# ─────────────────────────────────────────────────────────────────

with tab_advanced:
    st.markdown(
        "Mode pour data scientists et chercheurs : contrôle direct des 9 variables "
        "GDELT utilisées par le modèle Random Forest."
    )

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        a_event = st.selectbox(
            "Type d'événement (CAMEO)",
            options=sorted(le_event.classes_),
            key="adv_event",
            help="Catégorie CAMEO de l'événement (19 catégories).",
        )
        a_role = st.selectbox(
            "Rôle du Bénin", options=list(le_role.classes_), key="adv_role"
        )
        a_month = st.selectbox(
            "Mois", options=list(range(1, 13)),
            format_func=lambda m: f"{m} — {MONTH_LABELS[m]}",
            index=4, key="adv_month",
        )

    with col_b:
        a_gold = st.slider(
            "GoldsteinScale", -10.0, 10.0, 0.0, 0.1, key="adv_gold",
            help="-10 = très déstabilisant, +10 = très stabilisant. Variable la plus prédictive (27 %).",
        )
        a_quad = st.selectbox(
            "QuadClass", options=[1, 2, 3, 4],
            format_func=lambda q: f"{q} — {QUADCLASS_LABELS[q]}",
            index=0, key="adv_quad",
        )
        a_root = st.toggle("IsRootEvent", value=True, key="adv_root")

    with col_c:
        a_articles = st.number_input(
            "NumArticles", 1, 10000, 50, 1, key="adv_articles"
        )
        a_mentions = st.number_input(
            "NumMentions", 1, 20000, 80, 1, key="adv_mentions"
        )
        a_sources = st.number_input(
            "NumSources", 1, 2000, 20, 1, key="adv_sources"
        )

    if st.button("Prédire", type="primary", use_container_width=True, key="adv_btn"):
        pred_class, proba_by_class = predict_from_params(
            event_label=a_event, benin_role=a_role,
            event_month=a_month, goldstein=a_gold,
            quadclass=a_quad, is_root=a_root,
            num_articles=a_articles, num_mentions=a_mentions, num_sources=a_sources,
        )
        st.markdown('<div class="section-title">Résultat de la prédiction</div>', unsafe_allow_html=True)
        summary = [
            f"<b>Type :</b> {a_event} · <b>Rôle :</b> {a_role}",
            f"<b>Mois :</b> {MONTH_LABELS[a_month]} · <b>Goldstein :</b> {a_gold:.1f} · <b>QuadClass :</b> {a_quad}",
            f"<b>IsRoot :</b> {'Oui' if a_root else 'Non'} · <b>Articles/Mentions/Sources :</b> {a_articles}/{a_mentions}/{a_sources}",
        ]
        render_prediction(pred_class, proba_by_class, summary)

# ─────────────────────────────────────────────────────────────────
# DISCLAIMER
# ─────────────────────────────────────────────────────────────────

with st.expander("Comment lire ces résultats ? Limites du modèle"):
    st.markdown("""
**Comment ça marche.** Le modèle Random Forest a été entraîné sur **31 505 événements
GDELT 2025** au Bénin. Il a appris les associations entre les caractéristiques d'un
événement (type, gravité, mois, rôle du Bénin, attention médiatique) et le ton
moyen des articles publiés. Il prédit la **classe la plus probable** parmi
*Positif* / *Neutre* / *Négatif*.

**Performance globale.**
- Accuracy 55 % (vs 33 % aléatoire pour 3 classes)
- F1 weighted 0,55
- Meilleur sur la classe **Négatif** (F1 = 0,64) — la plus utile pour anticiper les crises
- Plus difficile sur la classe **Neutre** (F1 = 0,45) — frontière floue

**Limites à connaître.**
1. **Pas d'analyse textuelle** : le modèle ne lit pas le contenu des articles, seulement les métadonnées.
2. **Biais GDELT** : sur-représentation des médias anglophones, sous-représentation des médias francophones et locaux du Bénin.
3. **Année unique** : entraîné uniquement sur 2025, ne capture pas les cycles longs.
4. **Outil d'aide à la décision** : à utiliser avec votre expertise contextuelle, pas comme un oracle.
""")

# ─────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown(
    "<center style='color:#9ca3af; font-size:0.8rem;'>"
    "Anticipation de la couverture médiatique · Modèle Random Forest entraîné sur GDELT 2025 · "
    "IROKO Analytics — Bénin Insights Challenge 2026"
    "</center>",
    unsafe_allow_html=True
)

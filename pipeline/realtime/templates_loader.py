"""
BeninSentinel — Rendu des bulletins HTML par niveau d'alerte.

Charge les templates HTML statiques (templates/bulletins/) et y injecte
les données contextuelles d'une transition d'alerte. Utilise un moteur
de templating minimaliste (substitution {{ var }} et boucles
{% for ... %} simples) — pas de dépendance Jinja2 obligatoire.

Si `jinja2` est installé (généralement déjà tiré par FastAPI ou par
streamlit), il est utilisé en priorité pour des templates plus riches.
Sinon, le moteur de secours intégré garantit que les bulletins se
rendent toujours, même sans dépendance supplémentaire.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

try:
    from jinja2 import Template  # type: ignore
    _HAS_JINJA = True
except ImportError:
    _HAS_JINJA = False


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates" / "bulletins"

SIGNAL_LABELS = {
    "sig_tone":     "Dégradation du ton médiatique",
    "sig_negative": "Multiplication des articles négatifs",
    "sig_protest":  "Montée des tensions verbales",
    "sig_quad3":    "Conflits verbaux (menaces, désaccords)",
    "sig_quad4":    "Conflits matériels (violences)",
    "sig_violence": "Attaques majeures déclarées",
}

TEXT_BLURB = {
    "JAUNE": (
        "Le niveau d'alerte BeninSentinel est passé en JAUNE — préoccupation. "
        "Bulletin quotidien recommandé pour les préfets et le Cabinet du Ministre. "
        "Vérifier les canaux de communication de crise."
    ),
    "ORANGE": (
        "ALERTE ORANGE — mobilisation requise. Activation de la cellule de crise "
        "interministérielle. Bulletin toutes les 4 heures. Pré-positionnement des "
        "forces de sécurité. Préparation des éléments de communication publique."
    ),
    "ROUGE": (
        "ALERTE ROUGE — crise imminente. Convocation du Conseil restreint Présidence. "
        "Bulletin toutes les heures. Activation complète du dispositif de gestion "
        "de crise. Communication publique préventive."
    ),
    "VERT": (
        "Retour au niveau VERT — situation normalisée. Désactivation progressive "
        "du dispositif d'alerte. Reprise du mode surveillance passive."
    ),
}


def _render_minimal(template_str: str, context: dict) -> str:
    """
    Moteur de templating minimaliste (fallback sans Jinja2).

    Supporte :
      - {{ var }}            : substitution simple
      - {% for k, v in xs %} : boucle simple sur liste de tuples
        ... {{ k }} ... {{ v }} ...
        {% endfor %}
    """
    # 1. Boucles {% for k, v in name %}...{% endfor %}
    def repl_for(match):
        var_a, var_b, list_name, body = match.group(1), match.group(2), match.group(3), match.group(4)
        items = context.get(list_name, [])
        rendered = []
        for tup in items:
            if isinstance(tup, (list, tuple)) and len(tup) == 2:
                inner = body.replace("{{ " + var_a + " }}", str(tup[0]))
                inner = inner.replace("{{ " + var_b + " }}", str(tup[1]))
                rendered.append(inner)
            else:
                rendered.append(body.replace("{{ " + var_a + " }}", str(tup)))
        return "".join(rendered)

    pattern = r"\{% for (\w+),\s*(\w+) in (\w+) %\}(.*?)\{% endfor %\}"
    out = re.sub(pattern, repl_for, template_str, flags=re.DOTALL)

    # 2. Substitution simple {{ var }}
    def repl_var(match):
        key = match.group(1).strip()
        return str(context.get(key, ""))

    out = re.sub(r"\{\{\s*(\w+)\s*\}\}", repl_var, out)
    return out


def render_bulletin(alert_level: str, context: dict) -> str:
    """
    Rendre le bulletin HTML pour un niveau d'alerte donné.

    Args:
        alert_level : VERT / JAUNE / ORANGE / ROUGE.
        context     : variables à injecter (recipient_name, score, signals, etc.).

    Returns:
        Le HTML du bulletin, prêt à être envoyé par email ou affiché.
        Si le template est introuvable, retourne un fallback texte minimal.
    """
    template_path = TEMPLATES_DIR / f"bulletin_{alert_level.lower()}.html"
    if not template_path.exists():
        return (
            f"<html><body><h1>Alerte {alert_level}</h1>"
            f"<p>{TEXT_BLURB.get(alert_level, '')}</p></body></html>"
        )

    raw = template_path.read_text(encoding="utf-8")
    if _HAS_JINJA:
        return Template(raw).render(**context)
    return _render_minimal(raw, context)


def build_alert_payload(transition, recipient: dict) -> dict:
    """
    Construire le payload complet à passer à un provider de notification.

    Combine : sujet email, texte plain, HTML rendu depuis template, métadonnées.

    Args:
        transition : objet AlertTransition issu de AlertEngine.evaluate().
        recipient  : dict du destinataire (name, role, channel, address).

    Returns:
        dict prêt à passer à provider.send(recipient, payload).
    """
    level     = transition.to_level
    date_str  = transition.target_date.strftime("%d %B %Y")
    score_str = f"{transition.to_score:.3f}".replace(".", ",")

    # Préparer la liste des signaux pour le template
    signals_list = [
        (SIGNAL_LABELS.get(k, k), f"{v:.2f}".replace(".", ","))
        for k, v in transition.signals.items()
    ]

    context = {
        "recipient_name": recipient.get("name", ""),
        "recipient_role": recipient.get("role", ""),
        "target_date":    date_str,
        "score":          score_str,
        "from_level":     transition.from_level,
        "to_level":       level,
        "signals":        signals_list,
    }

    rendered_html = render_bulletin(level, context)
    rendered_text = (
        f"BeninSentinel — Alerte {level}\n"
        f"Date analysée : {date_str}\n"
        f"Score : {score_str} / 1,000\n"
        f"Transition : {transition.from_level} → {level} ({transition.direction})\n\n"
        f"Bonjour {recipient.get('name', '')} ({recipient.get('role', '')}),\n\n"
        f"{TEXT_BLURB.get(level, '')}\n\n"
        f"Indicateurs surveillés :\n"
        + "\n".join(f"  - {lbl} : {val}" for lbl, val in signals_list)
        + "\n\nBulletin généré automatiquement par BeninSentinel — IROKO Analytics."
    )

    return {
        "alert_level":   level,
        "subject":       f"[BeninSentinel] Alerte {level} — {date_str}",
        "rendered_text": rendered_text,
        "rendered_html": rendered_html,
        "transition": {
            "from":      transition.from_level,
            "to":        level,
            "score":     transition.to_score,
            "direction": transition.direction,
        },
    }

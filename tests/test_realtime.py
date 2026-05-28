"""
Tests unitaires du système BeninSentinel temps réel.

Couvre la persistance SQLite, le moteur de détection des transitions,
le routage par règles, les providers (en mode simulé) et les templates.

Tous les tests utilisent des bases SQLite temporaires (`tmp_path` pytest)
et le mode simulé des providers — aucun envoi réel, aucune dépendance
externe (pas de BigQuery, pas de SMTP).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from pipeline.realtime.alert_engine    import AlertEngine, AlertTransition, LEVEL_ORDER
from pipeline.realtime.history         import AlertHistory
from pipeline.realtime.notifier        import Notifier
from pipeline.realtime.providers       import ConsoleProvider, EmailProvider, WebhookProvider
from pipeline.realtime.providers.base  import NotificationProvider, ProviderResult
from pipeline.realtime.templates_loader import build_alert_payload, render_bulletin


# ─────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────

@pytest.fixture
def history(tmp_path):
    """Base SQLite d'historique fraîche pour chaque test."""
    return AlertHistory(tmp_path / "test_history.db")


@pytest.fixture
def transition_jaune():
    """Transition fictive VERT → JAUNE pour tester le routage."""
    return AlertTransition(
        measured_at=datetime(2025, 4, 20, 12, 0),
        target_date=pd.Timestamp("2025-04-20"),
        from_level="VERT", to_level="JAUNE",
        from_score=0.30, to_score=0.45,
        signals={"sig_tone": 0.4, "sig_negative": 0.5, "sig_protest": 0.2,
                 "sig_quad3": 0.1, "sig_quad4": 0.7, "sig_violence": 0.7},
        is_transition=True, direction="ESCALATION", transition_id=1,
    )


@pytest.fixture
def transition_orange_to_vert():
    """Transition de retour ORANGE → VERT (DE_ESCALATION)."""
    return AlertTransition(
        measured_at=datetime(2025, 4, 25, 12, 0),
        target_date=pd.Timestamp("2025-04-25"),
        from_level="ORANGE", to_level="VERT",
        from_score=0.70, to_score=0.20,
        signals={"sig_tone": 0.1, "sig_negative": 0.1, "sig_protest": 0.0,
                 "sig_quad3": 0.0, "sig_quad4": 0.1, "sig_violence": 0.0},
        is_transition=True, direction="DE_ESCALATION", transition_id=2,
    )


# ─────────────────────────────────────────────────────────────
# TESTS — AlertHistory (persistance SQLite)
# ─────────────────────────────────────────────────────────────

class TestAlertHistory:
    def test_schema_created_on_init(self, history):
        """Le constructeur doit créer le schéma SQLite si absent."""
        stats = history.stats()
        assert stats["n_states"]        == 0
        assert stats["n_transitions"]   == 0
        assert stats["n_notifications"] == 0

    def test_record_state_returns_id(self, history):
        state_id = history.record_state(
            measured_at=datetime.utcnow(),
            target_date=date(2025, 4, 20),
            risk_score=0.45,
            alert_level="JAUNE",
            signals={"sig_tone": 0.4},
        )
        assert isinstance(state_id, int)
        assert state_id > 0

    def test_last_state_returns_most_recent(self, history):
        history.record_state(datetime(2025, 1, 1), date(2025, 1, 1),
                             0.10, "VERT", {})
        history.record_state(datetime(2025, 4, 20), date(2025, 4, 20),
                             0.45, "JAUNE", {})
        last = history.last_state()
        assert last["alert_level"] == "JAUNE"

    def test_record_transition_detects_escalation(self, history):
        tid = history.record_transition(
            detected_at=datetime.utcnow(), target_date=date(2025, 4, 20),
            from_level="VERT", to_level="ORANGE",
            from_score=0.30, to_score=0.65,
        )
        rows = history.recent_transitions(1)
        assert rows[0]["direction"] == "ESCALATION"
        assert rows[0]["id"] == tid

    def test_record_transition_detects_de_escalation(self, history):
        history.record_transition(
            detected_at=datetime.utcnow(), target_date=date(2025, 4, 25),
            from_level="ORANGE", to_level="VERT",
            from_score=0.65, to_score=0.20,
        )
        rows = history.recent_transitions(1)
        assert rows[0]["direction"] == "DE_ESCALATION"

    def test_record_notification_traces_audit(self, history):
        tid = history.record_transition(
            detected_at=datetime.utcnow(), target_date=date(2025, 4, 20),
            from_level="VERT", to_level="JAUNE",
            from_score=0.30, to_score=0.45,
        )
        history.record_notification(
            transition_id=tid, sent_at=datetime.utcnow(),
            recipient_name="Test", recipient_role="test_role",
            channel="console", target_address="stdout",
            alert_level="JAUNE", status="SIMULATED",
        )
        rows = history.recent_notifications(1)
        assert rows[0]["recipient_name"] == "Test"
        assert rows[0]["status"]         == "SIMULATED"


# ─────────────────────────────────────────────────────────────
# TESTS — AlertTransition (méthodes calculées)
# ─────────────────────────────────────────────────────────────

class TestAlertTransitionLogic:
    def test_severity_change_escalation(self, transition_jaune):
        # VERT (0) → JAUNE (1) = +1
        assert transition_jaune.severity_change == 1
        assert transition_jaune.is_escalation is True

    def test_severity_change_de_escalation(self, transition_orange_to_vert):
        # ORANGE (2) → VERT (0) = -2
        assert transition_orange_to_vert.severity_change == -2
        assert transition_orange_to_vert.is_escalation is False

    def test_level_order_complete(self):
        assert LEVEL_ORDER == ["VERT", "JAUNE", "ORANGE", "ROUGE"]


# ─────────────────────────────────────────────────────────────
# TESTS — ConsoleProvider (toujours dispo)
# ─────────────────────────────────────────────────────────────

class TestConsoleProvider:
    def test_send_returns_success(self, tmp_path):
        provider = ConsoleProvider(journal_dir=tmp_path / "journal")
        recipient = {"name": "Préfet Alibori", "role": "prefet",
                     "address": "stdout"}
        payload = {"alert_level": "ORANGE", "subject": "Test",
                   "rendered_text": "Bulletin test"}
        result = provider.send(recipient, payload)
        assert result.status == "SUCCESS"
        assert result.channel == "console"

    def test_simulate_mode(self, tmp_path):
        provider = ConsoleProvider(journal_dir=tmp_path / "journal",
                                   simulate=True)
        result = provider.send({"name": "X"}, {"alert_level": "ROUGE"})
        assert result.status == "SIMULATED"

    def test_journal_file_created(self, tmp_path):
        journal = tmp_path / "journal"
        provider = ConsoleProvider(journal_dir=journal)
        provider.send({"name": "Y", "role": "test"},
                      {"alert_level": "JAUNE", "subject": "S",
                       "rendered_text": "T"})
        files = list(journal.glob("*.json"))
        assert len(files) == 1


# ─────────────────────────────────────────────────────────────
# TESTS — EmailProvider (fallback simulé sans config SMTP)
# ─────────────────────────────────────────────────────────────

class TestEmailProvider:
    def test_no_smtp_config_simulates(self, monkeypatch):
        # Pas de SENTINEL_SMTP_HOST → le provider passe en mode simulé
        monkeypatch.delenv("SENTINEL_SMTP_HOST", raising=False)
        provider = EmailProvider()
        result = provider.send(
            {"name": "Test", "address": "test@example.com"},
            {"alert_level": "JAUNE", "subject": "S", "rendered_text": "T"},
        )
        assert result.status == "SIMULATED"

    def test_provider_channel_is_email(self):
        provider = EmailProvider(simulate=True)
        assert provider.channel == "email"


# ─────────────────────────────────────────────────────────────
# TESTS — WebhookProvider (HTTP POST, simulé sans URL)
# ─────────────────────────────────────────────────────────────

class TestWebhookProvider:
    def test_empty_url_simulates(self):
        provider = WebhookProvider()
        result = provider.send({"name": "X", "address": ""},
                               {"alert_level": "ORANGE"})
        assert result.status == "SIMULATED"

    def test_simulate_mode_explicit(self):
        provider = WebhookProvider(simulate=True)
        result = provider.send(
            {"name": "X", "address": "https://example.com/hook"},
            {"alert_level": "ORANGE"},
        )
        assert result.status == "SIMULATED"


# ─────────────────────────────────────────────────────────────
# TESTS — Notifier (routage par règles)
# ─────────────────────────────────────────────────────────────

class TestNotifier:
    def test_should_not_notify_baseline(self, history, tmp_path):
        notifier = Notifier(history=history,
                            providers={"console": ConsoleProvider(
                                journal_dir=tmp_path / "j", simulate=True)})
        baseline = AlertTransition(
            measured_at=datetime.utcnow(), target_date=pd.Timestamp.today(),
            from_level="—", to_level="VERT",
            from_score=None, to_score=0.1, signals={},
            is_transition=False, direction="BASELINE", transition_id=None,
        )
        results = notifier.dispatch(baseline)
        assert results == []

    def test_should_not_notify_stable(self, history, tmp_path):
        notifier = Notifier(history=history,
                            providers={"console": ConsoleProvider(
                                journal_dir=tmp_path / "j", simulate=True)})
        stable = AlertTransition(
            measured_at=datetime.utcnow(), target_date=pd.Timestamp.today(),
            from_level="VERT", to_level="VERT",
            from_score=0.1, to_score=0.15, signals={},
            is_transition=False, direction="STABLE", transition_id=None,
        )
        results = notifier.dispatch(stable)
        assert results == []

    def _make_transition_in_history(self, history, transition):
        """Insère une transition réelle dans l'historique et retourne un nouvel
        AlertTransition portant l'ID effectif (pour respecter la foreign key)."""
        tid = history.record_transition(
            detected_at=transition.measured_at,
            target_date=transition.target_date.to_pydatetime().date(),
            from_level=transition.from_level, to_level=transition.to_level,
            from_score=transition.from_score, to_score=transition.to_score,
        )
        # Remplacer le transition_id par celui réellement inséré
        from dataclasses import replace
        return replace(transition, transition_id=tid)

    def test_dispatch_to_recipients(self, history, tmp_path, transition_jaune):
        # Préparer un YAML de destinataires minimal
        recipients_yaml = tmp_path / "recipients.yaml"
        recipients_yaml.write_text("""
recipients:
  - name: Préfet Alibori
    role: prefet_frontaliere
    channel: console
    address: stdout
    active: true
  - name: Préfet Borgou
    role: prefet_frontaliere
    channel: console
    address: stdout
    active: true
""", encoding="utf-8")

        rules_yaml = tmp_path / "rules.yaml"
        rules_yaml.write_text("""
rules:
  JAUNE:
    - prefet_frontaliere
""", encoding="utf-8")

        notifier = Notifier(
            history=history,
            recipients_path=recipients_yaml,
            rules_path=rules_yaml,
            providers={"console": ConsoleProvider(
                journal_dir=tmp_path / "j", simulate=True)},
        )

        # Enregistrer une vraie transition pour respecter la foreign key
        transition = self._make_transition_in_history(history, transition_jaune)
        results = notifier.dispatch(transition)
        assert len(results) == 2  # Les deux préfets sont notifiés

    def test_inactive_recipients_skipped(self, history, tmp_path, transition_jaune):
        recipients_yaml = tmp_path / "recipients.yaml"
        recipients_yaml.write_text("""
recipients:
  - name: Préfet Actif
    role: test_role
    channel: console
    active: true
  - name: Préfet Désactivé
    role: test_role
    channel: console
    active: false
""", encoding="utf-8")
        rules_yaml = tmp_path / "rules.yaml"
        rules_yaml.write_text("""
rules:
  JAUNE:
    - test_role
""", encoding="utf-8")

        notifier = Notifier(
            history=history,
            recipients_path=recipients_yaml,
            rules_path=rules_yaml,
            providers={"console": ConsoleProvider(
                journal_dir=tmp_path / "j", simulate=True)},
        )
        transition = self._make_transition_in_history(history, transition_jaune)
        results = notifier.dispatch(transition)
        assert len(results) == 1
        assert results[0]["recipient"]["name"] == "Préfet Actif"


# ─────────────────────────────────────────────────────────────
# TESTS — Templates loader
# ─────────────────────────────────────────────────────────────

class TestTemplates:
    def test_render_bulletin_jaune(self):
        html = render_bulletin("JAUNE", {
            "recipient_name": "Préfet",
            "recipient_role": "préfecture",
            "target_date": "24 avril 2025",
            "score": "0,686",
            "from_level": "VERT",
            "signals": [("Tension verbale", "0,45")],
        })
        assert "JAUNE" in html
        assert "Préfet" in html

    def test_render_bulletin_orange(self):
        html = render_bulletin("ORANGE", {
            "recipient_name": "Cabinet", "recipient_role": "interieur",
            "target_date": "24 avril 2025", "score": "0,686",
            "from_level": "JAUNE",
            "signals": [("Violence", "0,81")],
        })
        assert "ORANGE" in html

    def test_render_bulletin_unknown_level(self):
        # Fallback si template manquant
        html = render_bulletin("INCONNU", {})
        assert "INCONNU" in html

    def test_build_alert_payload_complete(self, transition_jaune):
        recipient = {"name": "Test", "role": "test_role"}
        payload = build_alert_payload(transition_jaune, recipient)
        assert payload["alert_level"] == "JAUNE"
        assert "rendered_text" in payload
        assert "rendered_html" in payload
        assert payload["transition"]["from"] == "VERT"
        assert payload["transition"]["to"]   == "JAUNE"

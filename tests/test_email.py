import pytest
from phase67_support import (  # noqa: F401  (the fixtures must be imported to be active)
    NOTIFICATIONS_URL,
    clean_notifications,
    make_complaint,
    make_worker,
    seeded,
    set_status,
)
from pydantic import SecretStr

from app.core.config import Settings, settings
from app.services import email_service


class FakeSMTP:
    """Replaces smtplib.SMTP: remembers what would have been sent instead of connecting."""

    sent = []
    logins = []
    fail = False

    def __init__(self, host, port, timeout=None):
        if FakeSMTP.fail:
            raise ConnectionRefusedError("mail server is down")
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def starttls(self):
        pass

    def login(self, user, password):
        FakeSMTP.logins.append((user, password))

    def send_message(self, message):
        FakeSMTP.sent.append(message)


@pytest.fixture
def smtp(monkeypatch):
    FakeSMTP.sent, FakeSMTP.logins, FakeSMTP.fail = [], [], False
    monkeypatch.setattr(email_service.smtplib, "SMTP", FakeSMTP)
    monkeypatch.setattr(settings, "smtp_host", "smtp.test")
    monkeypatch.setattr(settings, "smtp_port", 587)
    monkeypatch.setattr(settings, "smtp_user", "mailer@example.com")
    monkeypatch.setattr(settings, "smtp_password", SecretStr("app-password"))
    monkeypatch.setattr(settings, "smtp_from", "Civic Issues <noreply@example.com>")
    return FakeSMTP


def test_no_email_when_smtp_is_not_configured(client, create_user, sync_db, monkeypatch):
    monkeypatch.setattr(settings, "smtp_host", "")
    called = []
    monkeypatch.setattr(email_service.smtplib, "SMTP", lambda *a, **k: called.append(1))

    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    assert set_status(client, worker, complaint_id, "IN_PROGRESS").status_code == 200

    assert called == []
    assert not email_service.is_email_enabled()
    # The in-app notification is created anyway
    assert client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]["total"] == 1


def test_email_is_sent_to_the_reporter(client, create_user, sync_db, smtp):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    set_status(client, worker, complaint_id, "IN_PROGRESS", note="Crew assigned")

    assert len(smtp.sent) == 1
    message = smtp.sent[0]
    assert message["To"] == "citizen@example.com"
    assert message["From"] == "Civic Issues <noreply@example.com>"
    assert message["Subject"].startswith("[CIV-")
    assert "Work has started" in message["Subject"]
    body = message.get_content()
    assert "Crew assigned" in body
    assert "Hello Test User" in body
    assert smtp.logins == [("mailer@example.com", "app-password")]


def test_one_email_per_status_change(client, create_user, sync_db, smtp):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    set_status(client, worker, complaint_id, "IN_PROGRESS")
    set_status(client, worker, complaint_id, "RESOLVED")
    set_status(client, worker, complaint_id, "RESOLVED")  # rejected: no extra email
    assert len(smtp.sent) == 2
    assert "resolved" in smtp.sent[1]["Subject"].lower()


def test_no_email_for_a_deactivated_reporter(client, create_user, sync_db, smtp):
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)
    sync_db["users"].update_one({"email": "citizen@example.com"}, {"$set": {"isActive": False}})
    assert set_status(client, worker, complaint_id, "IN_PROGRESS").status_code == 200
    assert smtp.sent == []


def test_mail_server_down_does_not_break_the_status_change(client, create_user, sync_db, smtp):
    smtp.fail = True
    citizen = create_user(email="citizen@example.com")
    complaint_id = make_complaint(client, citizen, sync_db)
    worker = make_worker(create_user, sync_db)

    response = set_status(client, worker, complaint_id, "IN_PROGRESS")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "IN_PROGRESS"
    assert client.get(NOTIFICATIONS_URL, headers=citizen).json()["data"]["total"] == 1


def test_send_email_returns_false_on_failure_and_true_on_success(smtp):
    assert email_service.send_email("a@example.com", "Hi", "Body") is True
    smtp.fail = True
    assert email_service.send_email("a@example.com", "Hi", "Body") is False


def test_smtp_from_falls_back_to_smtp_user(smtp, monkeypatch):
    monkeypatch.setattr(settings, "smtp_from", "")
    assert email_service.is_email_enabled()
    email_service.send_email("a@example.com", "Hi", "Body")
    assert smtp.sent[0]["From"] == "mailer@example.com"


def test_empty_values_in_env_file_do_not_crash_settings(tmp_path, monkeypatch):
    """A line like 'SMTP_PORT=' in .env used to crash the app. It must use the default instead."""
    env_file = tmp_path / ".env"
    env_file.write_text("SMTP_HOST=\nSMTP_PORT=\nSMTP_USER=\nSMTP_PASSWORD=\nSMTP_FROM=\n")
    for name in ("SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"):
        monkeypatch.delenv(name, raising=False)
    loaded = Settings(_env_file=str(env_file))
    assert loaded.smtp_port == 587
    assert loaded.smtp_host == ""


def test_smtp_password_is_not_shown_when_settings_are_printed():
    assert "app-password" not in repr(Settings(smtp_password="app-password"))

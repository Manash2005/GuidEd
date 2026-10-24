import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from utils.auth import create_access_token
from templates.email_templates import (
    render_booking_confirmation_email,
    render_booking_cancellation_email
)
from services.email_service import (
    send_email_idempotent,
    send_booking_confirmation,
    send_booking_cancellation
)

client = TestClient(app)

class InMemoryCollection:
    def __init__(self):
        self.docs = []

    def _matches(self, doc, filter_dict):
        for k, v in filter_dict.items():
            if isinstance(v, dict):
                val = doc.get(k)
                if val is None:
                    return False
                if "$lt" in v and not (val < v["$lt"]): return False
                if "$gt" in v and not (val > v["$gt"]): return False
            elif doc.get(k) != v:
                return False
        return True

    async def find_one(self, filter_dict, projection=None):
        for doc in self.docs:
            if self._matches(doc, filter_dict):
                return doc.copy()
        return None

    async def insert_one(self, doc):
        self.docs.append(doc.copy())
        return MagicMock(inserted_id="mock_id")

    async def update_one(self, filter_dict, update_dict, upsert=False):
        for doc in self.docs:
            if self._matches(doc, filter_dict):
                if "$set" in update_dict:
                    for field, val in update_dict["$set"].items():
                        doc[field] = val
                return MagicMock(modified_count=1)

        if upsert:
            new_doc = filter_dict.copy()
            if "$set" in update_dict:
                new_doc.update(update_dict["$set"])
            self.docs.append(new_doc)
            return MagicMock(upserted_id="mock_upsert_id")

        return MagicMock(modified_count=0)

class MockDB:
    def __init__(self):
        self.users = InMemoryCollection()
        self.mentors = InMemoryCollection()
        self.bookings = InMemoryCollection()
        self.notifications = InMemoryCollection()

        now = datetime.now(timezone.utc)
        self.users.docs.append({
            "userId": "usr_email_test",
            "email": "student@example.com",
            "fullName": "Student Test",
            "createdAt": now
        })
        self.mentors.docs.append({
            "mentorId": "M033",
            "name": "Mentor 033"
        })

    def __getitem__(self, name):
        return getattr(self, name, MagicMock())

mock_db = MockDB()

def get_mock_db():
    return mock_db

auth_header = {"Authorization": f"Bearer {create_access_token({'sub': 'usr_email_test', 'email': 'student@example.com'})}"}


# --- Unit Tests: Template Rendering ---

def test_render_confirmation_template():
    booking = {
        "bookingId": "bk_abc123",
        "mentorName": "Dr. Sarah",
        "userName": "Jane Doe",
        "slotStart": datetime(2026, 11, 15, 14, 0, tzinfo=timezone.utc),
        "durationMinutes": 45,
        "topic": "Switching to Deep Learning Product Management",
        "meetingLink": "https://meet.google.com/abc-defg-hij"
    }
    subject, html = render_booking_confirmation_email(booking)
    assert "Dr. Sarah" in subject
    assert "Confirmed" in subject
    assert "Jane Doe" in html
    assert "45 minutes" in html
    assert "https://meet.google.com/abc-defg-hij" in html
    assert "bk_abc123" in html

def test_render_cancellation_template():
    booking = {
        "bookingId": "bk_abc123",
        "mentorName": "Dr. Sarah",
        "userName": "Jane Doe",
        "slotStart": datetime(2026, 11, 15, 14, 0, tzinfo=timezone.utc)
    }
    subject, html = render_booking_cancellation_email(booking)
    assert "Dr. Sarah" in subject
    assert "Cancelled" in subject
    assert "Jane Doe" in html
    assert "released" in html


# --- Unit Tests: Idempotency & Duplicate Prevention ---

@pytest.mark.anyio
@patch("services.email_service.get_database", side_effect=get_mock_db)
async def test_email_idempotency(mock_db_call):
    key = "email_test_idempotent_123"
    recipient = "test@example.com"
    subject = "Test Notification"
    body = "<p>Test</p>"

    # First send: should succeed and persist notification
    res1 = await send_email_idempotent(recipient, subject, body, key, "bk_123")
    assert res1["status"] == "sent"

    # Second send with identical key: should be skipped
    res2 = await send_email_idempotent(recipient, subject, body, key, "bk_123")
    assert res2["status"] == "skipped"
    assert res2["reason"] == "already_sent"


@pytest.mark.anyio
@patch("services.email_service.get_database", side_effect=get_mock_db)
async def test_high_level_helpers_idempotency(mock_db_call):
    booking = {
        "bookingId": "bk_helper_test",
        "userEmail": "student@example.com",
        "userName": "Student",
        "mentorName": "Mentor 033",
        "slotStart": datetime(2026, 11, 20, 10, 0, tzinfo=timezone.utc),
        "durationMinutes": 30,
        "topic": "Mentorship",
        "meetingLink": "https://meet.google.com/test"
    }

    # 1. Send confirmation
    confirm_res1 = await send_booking_confirmation(booking)
    assert confirm_res1["status"] == "sent"

    # Duplicate confirmation call
    confirm_res2 = await send_booking_confirmation(booking)
    assert confirm_res2["status"] == "skipped"

    # 2. Send cancellation
    cancel_res1 = await send_booking_cancellation(booking)
    assert cancel_res1["status"] == "sent"

    # Duplicate cancellation call
    cancel_res2 = await send_booking_cancellation(booking)
    assert cancel_res2["status"] == "skipped"


# --- Integration Test: Booking Endpoints Trigger Emails ---

@patch("routes.booking_routes.get_database", side_effect=get_mock_db)
@patch("utils.auth.get_database", side_effect=get_mock_db)
@patch("services.email_service.get_database", side_effect=get_mock_db)
def test_booking_endpoints_dispatch_notifications(mock_email_db, mock_auth_db, mock_b_db):
    target_dt = datetime.now(timezone.utc) + timedelta(days=4)
    slot_start = target_dt.replace(hour=11, minute=0, second=0, microsecond=0)

    # 1. Create booking
    res = client.post("/api/bookings", json={
        "mentorId": "M033",
        "slotStart": slot_start.isoformat(),
        "durationMinutes": 30,
        "topic": "Career Roadmap"
    }, headers=auth_header)

    assert res.status_code == 201
    booking_id = res.json()["bookingId"]

    # Verify notification recorded
    confirm_key = f"email_confirm_{booking_id}"
    confirm_notif = next((n for n in mock_db.notifications.docs if n.get("idempotencyKey") == confirm_key), None)
    assert confirm_notif is not None
    assert confirm_notif["status"] == "sent"

    # 2. Cancel booking
    cancel_res = client.post(f"/api/bookings/{booking_id}/cancel", headers=auth_header)
    assert cancel_res.status_code == 200

    # Verify cancellation notification recorded
    cancel_key = f"email_cancel_{booking_id}"
    cancel_notif = next((n for n in mock_db.notifications.docs if n.get("idempotencyKey") == cancel_key), None)
    assert cancel_notif is not None
    assert cancel_notif["status"] == "sent"

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from main import app
from utils.auth import create_access_token
from services.google_calendar import (
    is_google_calendar_configured,
    get_google_access_token,
    create_calendar_event,
    delete_calendar_event
)

client = TestClient(app)

class MockAsyncCursor:
    def __init__(self, data):
        self.data = data
    async def to_list(self, length=None):
        return self.data[:length] if length is not None else self.data

class InMemoryCollection:
    def __init__(self):
        self.docs = []
    async def find_one(self, filter_dict, projection=None):
        for doc in self.docs:
            matched = True
            for k, v in filter_dict.items():
                if isinstance(v, dict):
                    val = doc.get(k)
                    if "$lt" in v and not (val < v["$lt"]): matched = False
                    if "$gt" in v and not (val > v["$gt"]): matched = False
                elif doc.get(k) != v:
                    matched = False
            if matched:
                return doc.copy()
        return None
    def find(self, filter_dict, projection=None):
        return MockAsyncCursor([d.copy() for d in self.docs])
    async def insert_one(self, doc):
        self.docs.append(doc.copy())
        return MagicMock(inserted_id="mock_id")
    async def update_one(self, filter_dict, update_dict):
        for doc in self.docs:
            matched = True
            for k, v in filter_dict.items():
                if doc.get(k) != v: matched = False
            if matched:
                if "$set" in update_dict:
                    for field, val in update_dict["$set"].items():
                        doc[field] = val
                return MagicMock(modified_count=1)
        return MagicMock(modified_count=0)

class MockDB:
    def __init__(self):
        self.users = InMemoryCollection()
        self.mentors = InMemoryCollection()
        self.bookings = InMemoryCollection()

        now = datetime.now(timezone.utc)
        self.users.docs.append({"userId": "usr_cal_user", "email": "cal@example.com", "fullName": "Cal User", "createdAt": now})
        self.mentors.docs.append({"mentorId": "M033", "name": "Mentor 033"})
    def __getitem__(self, name):
        return getattr(self, name, MagicMock())

mock_db = MockDB()
def get_mock_db():
    return mock_db

auth_header = {"Authorization": f"Bearer {create_access_token({'sub': 'usr_cal_user', 'email': 'cal@example.com'})}"}


# --- Unit Tests: Google Calendar Service ---

def test_is_google_calendar_configured():
    with patch("services.google_calendar.GOOGLE_CLIENT_ID", ""), \
         patch("services.google_calendar.GOOGLE_CLIENT_SECRET", ""), \
         patch("services.google_calendar.GOOGLE_REFRESH_TOKEN", ""):
        assert is_google_calendar_configured() is False

    with patch("services.google_calendar.GOOGLE_CLIENT_ID", "mock_id"), \
         patch("services.google_calendar.GOOGLE_CLIENT_SECRET", "mock_secret"), \
         patch("services.google_calendar.GOOGLE_REFRESH_TOKEN", "mock_refresh"):
        assert is_google_calendar_configured() is True


@pytest.mark.anyio
async def test_unconfigured_fallback():
    with patch("services.google_calendar.is_google_calendar_configured", return_value=False):
        now = datetime.now(timezone.utc)
        res = await create_calendar_event(
            booking_id="bk_12345678",
            mentor_id="M033",
            mentor_name="Mentor 033",
            student_name="Student Test",
            student_email="student@test.com",
            slot_start=now,
            slot_end=now + timedelta(minutes=30),
            topic="Discussion"
        )
        assert res["calendarEventId"] is None
        assert "meet.google.com/lookup/guided-" in res["meetingLink"]


@pytest.mark.anyio
async def test_configured_event_creation_success():
    mock_token_resp = MagicMock(status_code=200)
    mock_token_resp.json.return_value = {"access_token": "mock_google_access_token"}

    mock_event_resp = MagicMock(status_code=201)
    mock_event_resp.json.return_value = {
        "id": "gcal_event_999",
        "hangoutLink": "https://meet.google.com/xyz-uvwx-rst"
    }

    with patch("services.google_calendar.is_google_calendar_configured", return_value=True), \
         patch("httpx.AsyncClient.post", side_effect=[mock_token_resp, mock_event_resp]):
        now = datetime.now(timezone.utc)
        res = await create_calendar_event(
            booking_id="bk_87654321",
            mentor_id="M033",
            mentor_name="Mentor 033",
            student_name="Student Test",
            student_email="student@test.com",
            slot_start=now,
            slot_end=now + timedelta(minutes=30),
            topic="Discussion"
        )
        assert res["calendarEventId"] == "gcal_event_999"
        assert res["meetingLink"] == "https://meet.google.com/xyz-uvwx-rst"


@pytest.mark.anyio
async def test_api_failure_graceful_fallback():
    mock_token_resp = MagicMock(status_code=200)
    mock_token_resp.json.return_value = {"access_token": "mock_google_access_token"}

    mock_event_resp = MagicMock(status_code=500, text="Internal Google Error")

    with patch("services.google_calendar.is_google_calendar_configured", return_value=True), \
         patch("httpx.AsyncClient.post", side_effect=[mock_token_resp, mock_event_resp]):
        now = datetime.now(timezone.utc)
        res = await create_calendar_event(
            booking_id="bk_failed_api",
            mentor_id="M033",
            mentor_name="Mentor 033",
            student_name="Student Test",
            student_email="student@test.com",
            slot_start=now,
            slot_end=now + timedelta(minutes=30),
            topic="Discussion"
        )
        assert res["calendarEventId"] is None
        assert "meet.google.com/lookup/guided-" in res["meetingLink"]


@pytest.mark.anyio
async def test_delete_calendar_event():
    mock_token_resp = MagicMock(status_code=200)
    mock_token_resp.json.return_value = {"access_token": "mock_access_token"}

    mock_del_resp = MagicMock(status_code=204)

    with patch("services.google_calendar.is_google_calendar_configured", return_value=True), \
         patch("httpx.AsyncClient.post", return_value=mock_token_resp), \
         patch("httpx.AsyncClient.delete", return_value=mock_del_resp):
        deleted = await delete_calendar_event("gcal_event_to_delete")
        assert deleted is True


# --- Integration Test: Booking with Calendar Event Creation ---

@patch("routes.booking_routes.get_database", side_effect=get_mock_db)
@patch("utils.auth.get_database", side_effect=get_mock_db)
def test_booking_endpoint_creates_meeting_link(mock_auth_db, mock_b_db):
    target_start = datetime.now(timezone.utc) + timedelta(days=2)

    res = client.post("/api/bookings", json={
        "mentorId": "M033",
        "slotStart": target_start.isoformat(),
        "durationMinutes": 30,
        "topic": "Career advice session"
    }, headers=auth_header)

    assert res.status_code == 201
    data = res.json()
    assert data["meetingLink"] is not None
    assert "meet.google.com" in data["meetingLink"]
    booking_id = data["bookingId"]

    # Cancel booking
    cancel_res = client.post(f"/api/bookings/{booking_id}/cancel", headers=auth_header)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

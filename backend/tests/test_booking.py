import pytest
from datetime import datetime, timedelta, timezone, date
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app
from utils.auth import create_access_token

client = TestClient(app)

class MockAsyncCursor:
    def __init__(self, data):
        self.data = data

    def sort(self, field, direction=1):
        self.data.sort(key=lambda x: x.get(field, ""), reverse=(direction == -1))
        return self

    def skip(self, n):
        self.data = self.data[n:]
        return self

    def limit(self, n):
        self.data = self.data[:n]
        return self

    async def to_list(self, length=None):
        return self.data[:length] if length is not None else self.data


class InMemoryCollection:
    def __init__(self):
        self.docs = []

    def _matches(self, doc, filter_dict):
        for k, v in filter_dict.items():
            if isinstance(v, dict):
                val = doc.get(k)
                if val is None:
                    return False
                if "$lt" in v and not (val < v["$lt"]):
                    return False
                if "$gt" in v and not (val > v["$gt"]):
                    return False
                if "$lte" in v and not (val <= v["$lte"]):
                    return False
                if "$gte" in v and not (val >= v["$gte"]):
                    return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    async def find_one(self, filter_dict, projection=None):
        for doc in self.docs:
            if self._matches(doc, filter_dict):
                res = doc.copy()
                if projection:
                    for p, val in projection.items():
                        if val == 0:
                            res.pop(p, None)
                return res
        return None

    def find(self, filter_dict, projection=None):
        matched_docs = [doc.copy() for doc in self.docs if self._matches(doc, filter_dict)]
        return MockAsyncCursor(matched_docs)

    async def insert_one(self, doc):
        self.docs.append(doc.copy())
        return MagicMock(inserted_id="mock_id")

    async def update_one(self, filter_dict, update_dict):
        for doc in self.docs:
            if self._matches(doc, filter_dict):
                if "$set" in update_dict:
                    for field, val in update_dict["$set"].items():
                        doc[field] = val
                return MagicMock(modified_count=1)
        return MagicMock(modified_count=0)


class MockBookingDB:
    def __init__(self):
        self.users = InMemoryCollection()
        self.mentors = InMemoryCollection()
        self.bookings = InMemoryCollection()

        now = datetime.now(timezone.utc)
        self.users.docs.append({
            "userId": "usr_alice",
            "email": "alice@example.com",
            "fullName": "Alice Student",
            "createdAt": now
        })
        self.users.docs.append({
            "userId": "usr_bob",
            "email": "bob@example.com",
            "fullName": "Bob Student",
            "role": "student",
            "createdAt": now
        })
        self.users.docs.append({
            "userId": "usr_admin",
            "email": "admin@guided.app",
            "fullName": "Admin User",
            "role": "admin",
            "createdAt": now
        })
        self.mentors.docs.append({
            "mentorId": "M033",
            "name": "Mentor 033",
            "domain": "AI",
            "city": "Bengaluru"
        })
        self.mentors.docs.append({
            "mentorId": "M013",
            "name": "Mentor 013",
            "domain": "Product Management",
            "city": "Bengaluru"
        })

    def __getitem__(self, name):
        if name == "users":
            return self.users
        if name == "mentors":
            return self.mentors
        if name == "bookings":
            return self.bookings
        return MagicMock()


mock_db = MockBookingDB()

def get_mock_db():
    return mock_db

token_alice = create_access_token({"sub": "usr_alice", "email": "alice@example.com", "role": "student"})
token_bob = create_access_token({"sub": "usr_bob", "email": "bob@example.com", "role": "student"})
token_admin = create_access_token({"sub": "usr_admin", "email": "admin@guided.app", "role": "admin"})
auth_alice = {"Authorization": f"Bearer {token_alice}"}
auth_bob = {"Authorization": f"Bearer {token_bob}"}
auth_admin = {"Authorization": f"Bearer {token_admin}"}


@patch("routes.booking_routes.get_database", side_effect=get_mock_db)
def test_get_mentor_slots(mock_b_db):
    future_date = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    res = client.get(f"/api/bookings/mentors/M033/slots?target_date={future_date}")
    assert res.status_code == 200
    slots = res.json()
    assert len(slots) > 0
    assert all(s["isAvailable"] is True for s in slots)


@patch("routes.booking_routes.get_database", side_effect=get_mock_db)
@patch("routes.admin_routes.get_database", side_effect=get_mock_db)
@patch("utils.auth.get_database", side_effect=get_mock_db)
def test_successful_booking_and_double_booking_prevention(mock_auth_db, mock_admin_db, mock_b_db):
    target_dt = datetime.now(timezone.utc) + timedelta(days=3)
    slot_start = target_dt.replace(hour=10, minute=0, second=0, microsecond=0)

    # 1. Alice books M033 for 10:00 - 10:30 UTC
    payload = {
        "mentorId": "M033",
        "slotStart": slot_start.isoformat(),
        "durationMinutes": 30,
        "topic": "Career path in Generative AI"
    }
    res1 = client.post("/api/bookings", json=payload, headers=auth_alice)
    assert res1.status_code == 201
    b_data = res1.json()
    assert b_data["status"] == "pending"
    assert b_data["mentorId"] == "M033"
    assert b_data["mentorName"] == "Mentor 033"
    assert b_data["userId"] == "usr_alice"
    booking_id = b_data["bookingId"]

    # 2. Bob attempts to book the EXACT SAME slot with M033 -> 409 Conflict (Pending blocks overlap)
    res2 = client.post("/api/bookings", json=payload, headers=auth_bob)
    assert res2.status_code == 409
    assert "already has an active or pending booking" in res2.json()["detail"].lower()

    # 3. Bob attempts to book an OVERLAPPING slot (10:15 - 10:45) with M033 -> 409 Conflict
    overlap_start = slot_start + timedelta(minutes=15)
    overlap_payload = {
        "mentorId": "M033",
        "slotStart": overlap_start.isoformat(),
        "durationMinutes": 30,
        "topic": "Overlapping booking attempt"
    }
    res3 = client.post("/api/bookings", json=overlap_payload, headers=auth_bob)
    assert res3.status_code == 409

    # 4. Alice attempts to book a different mentor (M013) at the same time -> 409 Conflict (Student overlap)
    alice_conflict_payload = {
        "mentorId": "M013",
        "slotStart": slot_start.isoformat(),
        "durationMinutes": 30,
        "topic": "Student schedule collision"
    }
    res4 = client.post("/api/bookings", json=alice_conflict_payload, headers=auth_alice)
    assert res4.status_code == 409
    assert "you already have an active mentorship booking" in res4.json()["detail"].lower()

    # 5. Check slots API reflects booked status (pending bookings block slot)
    slot_date = slot_start.strftime("%Y-%m-%d")
    slots_res = client.get(f"/api/bookings/mentors/M033/slots?target_date={slot_date}")
    assert slots_res.status_code == 200
    booked_slot = next((s for s in slots_res.json() if datetime.fromisoformat(s["slotStart"].replace("Z", "+00:00")) == slot_start), None)
    assert booked_slot is not None
    assert booked_slot["isAvailable"] is False

    # 6. Admin approves the pending booking -> transitions to confirmed
    appr_res = client.post(f"/api/admin/bookings/{booking_id}/approve", headers=auth_admin)
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] == "confirmed"

    # 6. Alice cancels her booking
    cancel_res = client.post(f"/api/bookings/{booking_id}/cancel", headers=auth_alice)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancelled"

    # 7. Bob can now book the freed slot successfully (creates pending booking)!
    res5 = client.post("/api/bookings", json=payload, headers=auth_bob)
    assert res5.status_code == 201
    assert res5.json()["status"] == "pending"


@patch("routes.booking_routes.get_database", side_effect=get_mock_db)
@patch("utils.auth.get_database", side_effect=get_mock_db)
def test_cross_user_booking_security(mock_auth_db, mock_b_db):
    target_dt = datetime.now(timezone.utc) + timedelta(days=5)
    slot_start = target_dt.replace(hour=14, minute=0, second=0, microsecond=0)

    # Alice creates a booking
    res = client.post("/api/bookings", json={
        "mentorId": "M013",
        "slotStart": slot_start.isoformat(),
        "durationMinutes": 30,
        "topic": "Product Roadmap Discussion"
    }, headers=auth_alice)
    assert res.status_code == 201
    booking_id = res.json()["bookingId"]

    # Bob attempts to view Alice's booking -> 403 Forbidden
    view_res = client.get(f"/api/bookings/{booking_id}", headers=auth_bob)
    assert view_res.status_code == 403

    # Bob attempts to cancel Alice's booking -> 403 Forbidden
    cancel_res = client.post(f"/api/bookings/{booking_id}/cancel", headers=auth_bob)
    assert cancel_res.status_code == 403

    # Alice views her own booking list
    list_res = client.get("/api/bookings", headers=auth_alice)
    assert list_res.status_code == 200
    alice_bookings = list_res.json()
    assert any(b["bookingId"] == booking_id for b in alice_bookings)


@patch("routes.booking_routes.get_database", side_effect=get_mock_db)
@patch("utils.auth.get_database", side_effect=get_mock_db)
def test_booking_validation_errors(mock_auth_db, mock_b_db):
    # 1. Past date rejection
    past_dt = datetime.now(timezone.utc) - timedelta(days=1)
    past_res = client.post("/api/bookings", json={
        "mentorId": "M033",
        "slotStart": past_dt.isoformat(),
        "durationMinutes": 30,
        "topic": "Past session"
    }, headers=auth_alice)
    assert past_res.status_code == 400
    assert "in the past" in past_res.json()["detail"].lower()

    # 2. Non-existent mentor
    future_dt = datetime.now(timezone.utc) + timedelta(days=2)
    no_mentor_res = client.post("/api/bookings", json={
        "mentorId": "M999",
        "slotStart": future_dt.isoformat(),
        "durationMinutes": 30,
        "topic": "Fake mentor"
    }, headers=auth_alice)
    assert no_mentor_res.status_code == 404

    # 3. Invalid date query in slots
    inv_date_res = client.get("/api/bookings/mentors/M033/slots?target_date=invalid-date")
    assert inv_date_res.status_code == 400

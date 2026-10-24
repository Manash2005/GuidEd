import pytest
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from fastapi.testclient import TestClient

from main import app
from db.mongo import db_instance
from utils.auth import create_access_token, hash_password

class MockCursor:
    def __init__(self, docs):
        self.docs = docs
    def sort(self, key, direction=1):
        # basic sort support
        reverse = (direction == -1)
        try:
            self.docs = sorted(self.docs, key=lambda x: x.get(key) or "", reverse=reverse)
        except Exception:
            pass
        return self
    def skip(self, count):
        self.docs = self.docs[count:]
        return self
    def limit(self, count):
        self.docs = self.docs[:count]
        return self
    async def to_list(self, length=100):
        return self.docs[:length]

class MockCollection:
    def __init__(self):
        self.docs = []

    async def count_documents(self, filter_dict):
        count = 0
        for doc in self.docs:
            if self._matches(doc, filter_dict):
                count += 1
        return count

    def _matches(self, doc, filter_dict):
        for k, v in filter_dict.items():
            if k == "$or":
                if not any(all(doc.get(sub_k) == sub_v for sub_k, sub_v in cond.items()) for cond in v):
                    return False
            elif isinstance(v, dict):
                if "$gte" in v and not (doc.get(k) is not None and doc.get(k) >= v["$gte"]):
                    return False
                if "$lt" in v and not (doc.get(k) is not None and doc.get(k) < v["$lt"]):
                    return False
                if "$gt" in v and not (doc.get(k) is not None and doc.get(k) > v["$gt"]):
                    return False
            elif doc.get(k) != v:
                return False
        return True

    async def find_one(self, filter_dict, projection=None, sort=None):
        matching = [d for d in self.docs if self._matches(d, filter_dict)]
        if not matching:
            return None
        res = dict(matching[0])
        if projection and "_id" in projection and projection["_id"] == 0:
            res.pop("_id", None)
        return res

    def find(self, filter_dict=None, projection=None):
        filter_dict = filter_dict or {}
        matching = [dict(d) for d in self.docs if self._matches(d, filter_dict)]
        if projection and "_id" in projection and projection["_id"] == 0:
            for item in matching:
                item.pop("_id", None)
        return MockCursor(matching)

    async def insert_one(self, doc):
        stored = dict(doc)
        if "_id" not in stored:
            stored["_id"] = str(uuid.uuid4())
        self.docs.append(stored)
        return type("InsertResult", (), {"inserted_id": stored["_id"]})()

    async def update_one(self, filter_dict, update_dict, upsert=False):
        for doc in self.docs:
            if self._matches(doc, filter_dict):
                if "$set" in update_dict:
                    doc.update(update_dict["$set"])
                return
        if upsert:
            new_doc = dict(filter_dict)
            if "$set" in update_dict:
                new_doc.update(update_dict["$set"])
            await self.insert_one(new_doc)

    def aggregate(self, pipeline):
        # Lightweight in-memory aggregation support for common pipelines
        return MockCursor([])

class MockDatabase:
    def __init__(self):
        self.collections = {}

    def __getitem__(self, name):
        if name not in self.collections:
            self.collections[name] = MockCollection()
        return self.collections[name]

    async def list_collection_names(self):
        return list(self.collections.keys())

@pytest.fixture(autouse=True)
def mock_db_fixture(monkeypatch):
    fake_db = MockDatabase()
    now = datetime.now(timezone.utc)

    # Seed users
    fake_db["users"].docs.extend([
        {
            "_id": "u1",
            "userId": "usr_student_1",
            "email": "student1@example.com",
            "fullName": "Student One",
            "role": "student",
            "status": "active",
            "createdAt": now
        },
        {
            "_id": "u2",
            "userId": "usr_student_2",
            "email": "student2@example.com",
            "fullName": "Student Two",
            "role": "student",
            "status": "active",
            "createdAt": now
        },
        {
            "_id": "u3",
            "userId": "usr_mentor_1",
            "email": "mentor1@example.com",
            "fullName": "Mentor Alpha",
            "role": "mentor",
            "status": "active",
            "mentorId": "M001",
            "createdAt": now
        },
        {
            "_id": "u4",
            "userId": "usr_mentor_2",
            "email": "mentor2@example.com",
            "fullName": "Mentor Beta",
            "role": "mentor",
            "status": "active",
            "mentorId": "M002",
            "createdAt": now
        },
        {
            "_id": "u5",
            "userId": "usr_admin_1",
            "email": "admin@example.com",
            "fullName": "Super Admin",
            "role": "admin",
            "status": "active",
            "createdAt": now
        },
        {
            "_id": "u6",
            "userId": "usr_disabled_1",
            "email": "disabled@example.com",
            "fullName": "Disabled User",
            "role": "student",
            "status": "suspended",
            "createdAt": now
        }
    ])

    # Seed bookings
    fake_db["bookings"].docs.extend([
        {
            "_id": "b1",
            "bookingId": "bk_001",
            "userId": "usr_student_1",
            "userName": "Student One",
            "userEmail": "student1@example.com",
            "mentorId": "M001",
            "mentorName": "Mentor Alpha",
            "slotStart": now + timedelta(days=1),
            "slotEnd": now + timedelta(days=1, minutes=30),
            "durationMinutes": 30,
            "status": "confirmed",
            "topic": "Career Roadmap",
            "meetingLink": "https://meet.google.com/abc-defg-hij",
            "createdAt": now,
            "updatedAt": now
        },
        {
            "_id": "b2",
            "bookingId": "bk_002",
            "userId": "usr_student_2",
            "userName": "Student Two",
            "userEmail": "student2@example.com",
            "mentorId": "M002",
            "mentorName": "Mentor Beta",
            "slotStart": now + timedelta(days=2),
            "slotEnd": now + timedelta(days=2, minutes=30),
            "durationMinutes": 30,
            "status": "confirmed",
            "topic": "Resume Review",
            "meetingLink": "https://meet.google.com/xyz-uvwx-rst",
            "createdAt": now,
            "updatedAt": now
        }
    ])

    # Seed conversations
    fake_db["conversations"].docs.extend([
        {
            "_id": "c1",
            "conversationId": "conv_001",
            "userId": "usr_student_1",
            "title": "AI Transition",
            "messages": [{"messageId": "m1", "role": "user", "content": "How do I become an AI PM?"}],
            "createdAt": now,
            "updatedAt": now
        },
        {
            "_id": "c2",
            "conversationId": "conv_002",
            "userId": "usr_student_2",
            "title": "Private Chat",
            "messages": [{"messageId": "m2", "role": "user", "content": "Confidential Career Question"}],
            "createdAt": now,
            "updatedAt": now
        }
    ])

    monkeypatch.setattr(db_instance, "db", fake_db)
    yield fake_db

@pytest.fixture
def client():
    return TestClient(app)

def make_headers(user_id: str, email: str, role: str):
    token = create_access_token({"sub": user_id, "email": email, "role": role})
    return {"Authorization": f"Bearer {token}", "x-skip-rate-limit": "true"}


# --- 1. Student Access & Isolation ---

def test_student_can_access_own_dashboard_and_bookings(client):
    headers = make_headers("usr_student_1", "student1@example.com", "student")
    # Dashboard
    res = client.get("/api/student/dashboard", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["userId"] == "usr_student_1"
    assert data["stats"]["totalBookings"] >= 1

    # Bookings
    b_res = client.get("/api/student/bookings", headers=headers)
    assert b_res.status_code == 200
    bookings = b_res.json()
    assert len(bookings) == 1
    assert bookings[0]["bookingId"] == "bk_001"

def test_student_cannot_access_another_students_data(client):
    headers = make_headers("usr_student_1", "student1@example.com", "student")

    # Cannot view student 2's booking directly
    res_booking = client.get("/api/bookings/bk_002", headers=headers)
    assert res_booking.status_code == 403
    assert "Access denied" in res_booking.json()["detail"]

    # Cannot view student 2's private conversation
    res_conv = client.get("/api/chat/conversations/conv_002", headers=headers)
    assert res_conv.status_code == 403
    assert "Access denied" in res_conv.json()["detail"]

def test_student_cannot_access_mentor_or_admin_endpoints(client):
    headers = make_headers("usr_student_1", "student1@example.com", "student")

    # Mentor dashboard
    res_mentor = client.get("/api/mentor/dashboard", headers=headers)
    assert res_mentor.status_code == 403
    assert "not authorized" in res_mentor.json()["detail"]

    # Admin dashboard stats
    res_admin = client.get("/api/admin/dashboard/stats", headers=headers)
    assert res_admin.status_code == 403
    assert "not authorized" in res_admin.json()["detail"]

    # Admin user list
    res_users = client.get("/api/admin/users", headers=headers)
    assert res_users.status_code == 403


# --- 2. Mentor Access & Isolation ---

def test_mentor_can_access_own_bookings_and_student_context(client):
    headers = make_headers("usr_mentor_1", "mentor1@example.com", "mentor")

    # Mentor dashboard
    dash_res = client.get("/api/mentor/dashboard", headers=headers)
    assert dash_res.status_code == 200
    assert dash_res.json()["mentorId"] == "M001"

    # Mentor bookings list
    b_res = client.get("/api/mentor/bookings", headers=headers)
    assert b_res.status_code == 200
    bookings = b_res.json()
    assert len(bookings) == 1
    assert bookings[0]["bookingId"] == "bk_001"

    # Authorized student context for scheduled call
    ctx_res = client.get("/api/mentor/bookings/bk_001/student-context", headers=headers)
    assert ctx_res.status_code == 200
    ctx = ctx_res.json()
    assert ctx["topic"] == "Career Roadmap"
    assert ctx["student"]["name"] == "Student One"

def test_mentor_cannot_access_another_mentors_bookings(client):
    headers = make_headers("usr_mentor_1", "mentor1@example.com", "mentor")

    # Mentor 1 tries to access Mentor 2's booking (bk_002)
    res = client.get("/api/mentor/bookings/bk_002", headers=headers)
    assert res.status_code == 403
    assert "belongs to another mentor" in res.json()["detail"]

    res_ctx = client.get("/api/mentor/bookings/bk_002/student-context", headers=headers)
    assert res_ctx.status_code == 403

def test_mentor_cannot_browse_unrelated_student_conversations(client):
    headers = make_headers("usr_mentor_1", "mentor1@example.com", "mentor")

    # Mentor tries to directly access private conversation
    res = client.get("/api/chat/conversations/conv_001", headers=headers)
    assert res.status_code == 403

def test_mentor_cannot_access_admin_or_change_own_role(client):
    headers = make_headers("usr_mentor_1", "mentor1@example.com", "mentor")

    # Admin stats
    res_stats = client.get("/api/admin/dashboard/stats", headers=headers)
    assert res_stats.status_code == 403

    # Attempt to change own role to admin
    res_role = client.patch(
        "/api/admin/users/usr_mentor_1/role",
        json={"role": "admin"},
        headers=headers
    )
    assert res_role.status_code == 403


# --- 3. Admin Capabilities & Role Assignment ---

def test_admin_can_access_administrative_endpoints(client):
    headers = make_headers("usr_admin_1", "admin@example.com", "admin")

    stats_res = client.get("/api/admin/dashboard/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()["stats"]
    assert stats["totalStudents"] >= 2
    assert stats["totalBookings"] >= 2

    users_res = client.get("/api/admin/users", headers=headers)
    assert users_res.status_code == 200
    assert users_res.json()["total"] >= 5

    health_res = client.get("/api/admin/health", headers=headers)
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "operational"

def test_admin_can_change_user_role_and_status_with_audit_log(client, mock_db_fixture):
    headers = make_headers("usr_admin_1", "admin@example.com", "admin")

    # Promote student to mentor
    role_res = client.patch(
        "/api/admin/users/usr_student_2/role",
        json={"role": "mentor"},
        headers=headers
    )
    assert role_res.status_code == 200
    assert role_res.json()["role"] == "mentor"

    # Suspend a user
    status_res = client.patch(
        "/api/admin/users/usr_student_2/status",
        json={"status": "suspended"},
        headers=headers
    )
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "suspended"

    # Verify audit log was recorded
    audit_res = client.get("/api/admin/audit-logs", headers=headers)
    assert audit_res.status_code == 200
    logs = audit_res.json()["logs"]
    assert len(logs) >= 2
    actions = [l["action"] for l in logs]
    assert "UPDATE_USER_ROLE" in actions
    assert "UPDATE_USER_STATUS" in actions


# --- 4. Registration & Token Security ---

def test_public_registration_cannot_create_admin(client):
    reg_payload = {
        "email": "hacker@example.com",
        "password": "Password123!",
        "fullName": "Sneaky User",
        "role": "admin"
    }
    res = client.post("/api/auth/register", json=reg_payload)
    # Pydantic or endpoint rejects invalid role
    assert res.status_code in (400, 422)

def test_public_registration_accepts_student_and_mentor(client):
    # Student registration
    res1 = client.post("/api/auth/register", json={
        "email": "newstudent@example.com",
        "password": "Password123!",
        "fullName": "New Student",
        "role": "student"
    })
    assert res1.status_code == 201
    assert res1.json()["role"] == "student"

    # Mentor registration
    res2 = client.post("/api/auth/register", json={
        "email": "newmentor@example.com",
        "password": "Password123!",
        "fullName": "New Mentor",
        "role": "mentor",
        "mentorId": "M999"
    })
    assert res2.status_code == 201
    assert res2.json()["role"] == "mentor"
    assert res2.json()["mentorId"] == "M999"

def test_forged_or_expired_jwt_rejected(client):
    # Forged signature
    res1 = client.get("/api/auth/me", headers={"Authorization": "Bearer fake.tampered.token"})
    assert res1.status_code == 401

    # Expired token
    expired_token = create_access_token({"sub": "usr_student_1"}, expires_delta=timedelta(minutes=-10))
    res2 = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert res2.status_code == 401
    assert "expired" in res2.json()["detail"].lower()

def test_disabled_account_cannot_access_protected_endpoints(client):
    # Token issued for suspended user
    headers = make_headers("usr_disabled_1", "disabled@example.com", "student")
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 403
    assert "suspended" in res.json()["detail"].lower()


# --- 5. Token Revalidation Strategy on Role Change ---

def test_server_side_role_revocation_enforced_immediately(client, mock_db_fixture):
    # User was issued a token with role: "admin"
    admin_headers = make_headers("usr_student_1", "student1@example.com", "admin")

    # In database, user's real role is "student"
    # Even though token claim says admin, server-side get_current_user reads database!
    res = client.get("/api/admin/dashboard/stats", headers=admin_headers)
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"]


# --- 6. Admin Statistics with Empty & Populated Datasets ---

def test_admin_stats_empty_dataset(client, monkeypatch):
    empty_db = MockDatabase()
    monkeypatch.setattr(db_instance, "db", empty_db)
    # Seed only admin
    empty_db["users"].docs.append({
        "userId": "usr_admin_1",
        "email": "admin@example.com",
        "fullName": "Super Admin",
        "role": "admin",
        "status": "active",
        "createdAt": datetime.now(timezone.utc)
    })

    headers = make_headers("usr_admin_1", "admin@example.com", "admin")
    res = client.get("/api/admin/dashboard/stats", headers=headers)
    assert res.status_code == 200
    stats = res.json()["stats"]
    assert stats["totalStudents"] == 0
    assert stats["totalBookings"] == 0
    assert stats["cancellationRatePercent"] == 0.0
    assert stats["completionRatePercent"] == 0.0

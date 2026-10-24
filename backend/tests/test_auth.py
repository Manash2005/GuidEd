import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException

from main import app
from utils.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token
)

client = TestClient(app)

class MockAsyncCursor:
    def __init__(self, data):
        self.data = data

    def skip(self, n):
        self.data = self.data[n:]
        return self

    def limit(self, n):
        self.data = self.data[:n]
        return self

    async def to_list(self, length):
        return self.data[:length]

class InMemoryUsersCollection:
    def __init__(self):
        self.docs = []

    async def find_one(self, filter_dict, projection=None):
        for doc in self.docs:
            matched = True
            for k, v in filter_dict.items():
                if doc.get(k) != v:
                    matched = False
                    break
            if matched:
                res = doc.copy()
                if projection:
                    for p, val in projection.items():
                        if val == 0:
                            res.pop(p, None)
                return res
        return None

    async def insert_one(self, doc):
        self.docs.append(doc.copy())
        return MagicMock(inserted_id="mock_id")

class MockDB:
    def __init__(self):
        self.users_col = InMemoryUsersCollection()
        self.mentors_col = InMemoryUsersCollection()
        # Seed a sample mentor with private fields
        self.mentors_col.docs.append({
            "mentorId": "M001",
            "name": "Alex Smith",
            "contact": "+1234567890",
            "email": "alex@secret.com",
            "linkedin": "https://linkedin.com/in/alex",
            "domain": "Product Management",
            "sectorsOfExpertise": ["SaaS"],
            "seniority": "Senior"
        })

    def __getitem__(self, name):
        if name == "users":
            return self.users_col
        if name == "mentors":
            return self.mentors_col
        return MagicMock()


# --- Unit Tests: Cryptography & JWT ---

def test_password_hashing_and_verification():
    raw_password = "supersecretpassword123"
    hashed = hash_password(raw_password)

    assert hashed != raw_password
    assert verify_password(raw_password, hashed) is True
    assert verify_password("wrongpassword", hashed) is False

def test_token_creation_and_decoding():
    data = {"sub": "usr_test123", "email": "test@example.com"}
    token = create_access_token(data)

    payload = decode_access_token(token)
    assert payload["sub"] == "usr_test123"
    assert payload["email"] == "test@example.com"
    assert "exp" in payload

def test_expired_token_raises_401():
    data = {"sub": "usr_expired", "email": "expired@example.com"}
    expired_token = create_access_token(data, expires_delta=timedelta(seconds=-10))

    with pytest.raises(HTTPException) as exc:
        decode_access_token(expired_token)
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()

def test_tampered_token_raises_401():
    data = {"sub": "usr_valid", "email": "valid@example.com"}
    token = create_access_token(data)
    tampered_token = token[:-5] + "abcde"

    with pytest.raises(HTTPException) as exc:
        decode_access_token(tampered_token)
    assert exc.value.status_code == 401


# --- Integration Tests: Auth Endpoints ---

mock_database = MockDB()

def get_mock_db():
    return mock_database

@patch("routes.auth_routes.get_database", side_effect=get_mock_db)
@patch("utils.auth.get_database", side_effect=get_mock_db)
def test_full_auth_flow(mock_auth_db, mock_routes_db):
    test_email = "student@career.com"
    test_password = "StrongPassword123!"

    # 1. Register
    reg_payload = {
        "email": test_email,
        "password": test_password,
        "fullName": "Student Jane"
    }
    reg_res = client.post("/api/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["email"] == test_email
    assert reg_data["fullName"] == "Student Jane"
    assert "userId" in reg_data
    assert "password" not in reg_data
    assert "hashedPassword" not in reg_data

    # 2. Duplicate Registration Rejection
    dup_res = client.post("/api/auth/register", json=reg_payload)
    assert dup_res.status_code == 409

    # 3. Weak Password Rejection
    weak_res = client.post("/api/auth/register", json={
        "email": "weak@example.com",
        "password": "short",
        "fullName": "Weak User"
    })
    assert weak_res.status_code == 422

    # 4. Login with Wrong Password
    bad_login = client.post("/api/auth/login", json={
        "email": test_email,
        "password": "WrongPassword!"
    })
    assert bad_login.status_code == 401

    # 5. Successful Login
    login_res = client.post("/api/auth/login", json={
        "email": test_email,
        "password": test_password
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    token = token_data["access_token"]

    # 6. Access /api/auth/me with valid Bearer token
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == test_email
    assert me_data["userId"] == reg_data["userId"]

    # 7. Access /api/auth/me without token
    unauth_res = client.get("/api/auth/me")
    assert unauth_res.status_code == 401


# --- Mentor PII Masking & Regex Sanitization Test ---

@patch("routes.mentors_routes.get_database", side_effect=get_mock_db)
def test_mentor_pii_masked(mock_m_db):
    # Fetch single mentor by ID
    res = client.get("/api/mentors/M001")
    assert res.status_code == 200
    data = res.json()
    assert data["mentorId"] == "M001"
    assert data["name"] == "Alex Smith"
    # Ensure sensitive PII fields are completely omitted from public response
    assert "contact" not in data
    assert "email" not in data
    assert "linkedin" not in data

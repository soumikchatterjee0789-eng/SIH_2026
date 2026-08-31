"""
Shared pytest fixtures.

Uses a fresh SQLite file per test session (not the dev DB) and overrides
the get_db dependency so tests never touch real data.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["DATABASE_URL"] = "sqlite:///./test_s41.db"
os.environ["SECRET_KEY"] = "test-secret-key"

import app.models  # noqa: E402, F401 (register models before importing `app` the FastAPI instance)
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402  (must be last: rebinds name `app` to the FastAPI instance)

TEST_DB_URL = "sqlite:///./test_s41.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    if os.path.exists("test_s41.db"):
        os.remove("test_s41.db")
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("test_s41.db"):
        os.remove("test_s41.db")


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def auth_client(client):
    """Returns (client, auth_headers) for a freshly registered user."""
    import uuid

    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": "password123", "full_name": "Test User", "user_type": "student"},
    )
    token = resp.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return client, headers

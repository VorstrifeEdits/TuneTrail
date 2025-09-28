"""Pytest configuration and fixtures for TuneTrail API tests."""

import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from main import app
from database import Base
from models import User, Organization, Track, APIKey

# Use in-memory SQLite for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)

    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_org(db_session: Session) -> Organization:
    """Create a sample organization for testing."""
    org = Organization(
        name="Test Organization",
        slug="test-org",
        plan="free",
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


@pytest.fixture
def sample_user(db_session: Session, sample_org: Organization) -> User:
    """Create a sample user for testing."""
    user = User(
        email="test@example.com",
        username="testuser",
        org_id=sample_org.id,
    )
    user.set_password("testpassword123")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
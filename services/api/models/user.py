from datetime import datetime
from uuid import uuid4, UUID
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext

from database import Base

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "users"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    org_id = Column(PGUUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"))

    # Identity
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)

    # Name fields (enhanced)
    first_name = Column(String(255), nullable=True, index=True)
    last_name = Column(String(255), nullable=True, index=True)
    full_name = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    pronouns = Column(String(50), nullable=True)

    # Profile
    avatar_url = Column(String, nullable=True)
    banner_url = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    location = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)

    # Demographics (optional, for ML)
    birth_date = Column(DateTime(timezone=True), nullable=True)
    gender = Column(String(50), nullable=True)
    country_code = Column(String(2), nullable=True, index=True)
    language_code = Column(String(5), default="en")
    timezone = Column(String(100), nullable=True)

    # Account settings
    role = Column(String(50), default="user", nullable=False)
    account_type = Column(String(50), default="free", index=True)
    subscription_status = Column(String(50), default="active")
    is_active = Column(Boolean, default=True)
    email_verified = Column(Boolean, default=False)

    # Privacy & consent
    public_profile = Column(Boolean, default=False)
    show_listening_history = Column(Boolean, default=False)
    discoverable = Column(Boolean, default=True)
    marketing_emails_consent = Column(Boolean, default=False)
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    last_login = Column(DateTime(timezone=True), nullable=True)
    last_active_at = Column(DateTime(timezone=True), nullable=True)
    onboarding_step = Column(String(50), nullable=True, index=True)
    profile_completed_at = Column(DateTime(timezone=True), nullable=True)

    preferences = Column(JSON, default={})

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    organization = relationship("Organization", back_populates="users")
    api_keys = relationship("APIKey", back_populates="user")
    playlists = relationship("Playlist", back_populates="user")
    interactions = relationship("Interaction", back_populates="user")
    player_state = relationship("PlayerState", back_populates="user", uselist=False)
    queue_items = relationship("Queue", back_populates="user")
    listening_sessions = relationship("ListeningSession", back_populates="user")
    saved_albums = relationship("SavedAlbum", back_populates="user")
    followed_artists = relationship("ArtistFollow", back_populates="user")

    def set_password(self, password: str) -> None:
        """Hash and set the user's password."""
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        """Verify a password against the hash."""
        if not self.password_hash:
            return False
        return pwd_context.verify(password, self.password_hash)


# Pydantic schemas
class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    first_name: Optional[str] = Field(None, max_length=255, example="John")
    last_name: Optional[str] = Field(None, max_length=255, example="Doe")
    display_name: Optional[str] = Field(None, max_length=255, example="Johnny")


class UserCreate(BaseModel):
    """Enhanced user registration with comprehensive data collection."""
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=8, example="SecurePass123!")
    username: Optional[str] = Field(None, min_length=3, max_length=100, example="musiclover")

    first_name: str = Field(..., min_length=1, max_length=255, example="John")
    last_name: str = Field(..., min_length=1, max_length=255, example="Doe")
    display_name: Optional[str] = Field(None, example="Johnny")

    birth_date: Optional[str] = Field(None, example="1990-01-15", description="YYYY-MM-DD format")
    country_code: Optional[str] = Field(None, min_length=2, max_length=2, example="US")
    language_code: str = Field(default="en", example="en")
    timezone: Optional[str] = Field(None, example="America/Los_Angeles")

    terms_accepted: bool = Field(..., description="Must accept terms of service")
    privacy_accepted: bool = Field(..., description="Must accept privacy policy")
    marketing_consent: Optional[bool] = Field(default=False)

    signup_source: Optional[str] = Field(None, example="web")
    referral_code: Optional[str] = Field(None, example="FRIEND123")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Complete user profile response."""
    id: UUID
    email: EmailStr
    username: Optional[str]

    first_name: Optional[str]
    last_name: Optional[str]
    display_name: Optional[str]
    full_name: Optional[str]
    pronouns: Optional[str]

    avatar_url: Optional[str]
    banner_url: Optional[str]
    bio: Optional[str]
    location: Optional[str]
    website: Optional[str]

    country_code: Optional[str]
    language_code: str
    timezone: Optional[str]

    role: str
    account_type: str
    is_active: bool
    email_verified: bool
    public_profile: bool
    discoverable: bool

    onboarding_step: Optional[str]
    profile_completed_at: Optional[datetime]

    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=255)
    last_name: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    pronouns: Optional[str] = Field(None, example="they/them")

    avatar_url: Optional[str] = None
    banner_url: Optional[str] = None
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = None

    country_code: Optional[str] = Field(None, min_length=2, max_length=2)
    language_code: Optional[str] = Field(None, min_length=2, max_length=5)
    timezone: Optional[str] = None

    public_profile: Optional[bool] = None
    show_listening_history: Optional[bool] = None
    discoverable: Optional[bool] = None

    preferences: Optional[dict] = None
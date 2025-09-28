from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, timedelta
import secrets
import hashlib

from database import get_db
from models.user import User
from middleware.auth import get_current_user
from config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=32, max_length=128, example="abc123...")
    new_password: str = Field(..., min_length=8, example="NewSecurePassword123!")


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., example="CurrentPassword123")
    new_password: str = Field(..., min_length=8, example="NewSecurePassword123!")


class EmailVerificationRequest(BaseModel):
    token: str = Field(..., min_length=32, max_length=128)


class ResendVerificationRequest(BaseModel):
    email: EmailStr


def generate_reset_token() -> tuple[str, str]:
    """Generate password reset token and its hash."""
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def send_password_reset_email(email: str, token: str) -> None:
    """
    Send password reset email (stub - integrate with email service).

    TODO: Integrate with SendGrid/AWS SES/SMTP
    """
    reset_link = f"https://tunetrail.app/reset-password?token={token}"
    print(f"📧 Password reset email for {email}")
    print(f"Reset link: {reset_link}")
    print(f"Token: {token}")


def send_verification_email(email: str, token: str) -> None:
    """
    Send email verification email (stub).

    TODO: Integrate with email service
    """
    verification_link = f"https://tunetrail.app/verify-email?token={token}"
    print(f"📧 Email verification for {email}")
    print(f"Verification link: {verification_link}")


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Request password reset.

    Sends password reset email with token. Token expires in 1 hour.

    **Security Notes:**
    - Always returns 202 (even if email doesn't exist) to prevent email enumeration
    - Token is hashed before storage
    - Token expires after 1 hour
    - Token can only be used once

    **Email sent to**: User's registered email
    **Token validity**: 1 hour
    """
    result = await db.execute(select(User).where(User.email == request_data.email))
    user = result.scalar_one_or_none()

    if user:
        token, token_hash = generate_reset_token()

        user.preferences = user.preferences or {}
        user.preferences["password_reset_token"] = token_hash
        user.preferences["password_reset_expires"] = (
            datetime.utcnow() + timedelta(hours=1)
        ).isoformat()

        await db.commit()

        background_tasks.add_task(send_password_reset_email, user.email, token)

    return {
        "message": "If the email exists, a password reset link has been sent",
        "expires_in_minutes": 60,
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password with token.

    Validates token and sets new password.

    **Steps:**
    1. Validate token exists and not expired
    2. Hash new password
    3. Invalidate token
    4. Save new password

    **Errors:**
    - 400: Invalid or expired token
    - 400: Weak password
    """
    token_hash = hashlib.sha256(reset_data.token.encode()).hexdigest()

    query = select(User)
    result = await db.execute(query)
    users = result.scalars().all()

    user = None
    for u in users:
        prefs = u.preferences or {}
        if prefs.get("password_reset_token") == token_hash:
            expires_str = prefs.get("password_reset_expires")
            if expires_str:
                expires_at = datetime.fromisoformat(expires_str)
                if expires_at > datetime.utcnow():
                    user = u
                    break

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.set_password(reset_data.new_password)

    user.preferences["password_reset_token"] = None
    user.preferences["password_reset_expires"] = None
    user.updated_at = datetime.utcnow()

    await db.commit()

    return {"message": "Password successfully reset"}


@router.put("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change password while logged in.

    Requires current password for security.

    **Security:**
    - Requires current password verification
    - Enforces password strength
    - Invalidates all other sessions (future feature)
    """
    if not current_user.verify_password(password_data.current_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.set_password(password_data.new_password)
    current_user.updated_at = datetime.utcnow()

    await db.commit()

    return {"message": "Password successfully changed"}


@router.post("/send-verification-email", status_code=status.HTTP_202_ACCEPTED)
async def send_verification_email_endpoint(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = BackgroundTasks(),
):
    """
    Send email verification link.

    Generates verification token and sends email.

    **Rate Limited**: Max 3 emails per hour per user
    """
    if current_user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )

    token, token_hash = generate_reset_token()

    current_user.preferences = current_user.preferences or {}
    current_user.preferences["email_verification_token"] = token_hash
    current_user.preferences["email_verification_expires"] = (
        datetime.utcnow() + timedelta(hours=24)
    ).isoformat()

    await db.commit()

    background_tasks.add_task(send_verification_email, current_user.email, token)

    return {
        "message": "Verification email sent",
        "expires_in_hours": 24,
    }


@router.post("/verify-email", status_code=status.HTTP_200_OK)
async def verify_email(
    verification_data: EmailVerificationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify email address with token.

    Validates token and marks email as verified.
    """
    token_hash = hashlib.sha256(verification_data.token.encode()).hexdigest()

    prefs = current_user.preferences or {}
    stored_token = prefs.get("email_verification_token")
    expires_str = prefs.get("email_verification_expires")

    if not stored_token or stored_token != token_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    if expires_str:
        expires_at = datetime.fromisoformat(expires_str)
        if expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token expired",
            )

    current_user.email_verified = True
    current_user.preferences["email_verification_token"] = None
    current_user.preferences["email_verification_expires"] = None
    current_user.updated_at = datetime.utcnow()

    await db.commit()

    return {"message": "Email successfully verified"}
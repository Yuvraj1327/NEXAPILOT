"""
JWT issuance/verification for session auth.

NOTE on scope: NexaPilot's real identity model is the user's wallet, and
in later phases the frontend uses Privy to establish that a user actually
controls the wallet address they claim (via signature verification / SIWE).
Phase 1 only builds the session-token plumbing: given an already-known
wallet address, issue and verify a JWT. Wiring in real signature
verification at /api/v1/auth/connect is deliberately deferred to the
frontend/wallet integration phase and is called out there as a TODO —
this file has nothing to do with that decision.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import UUID

import jwt

from app.core.config import settings
from app.core.exceptions import UnauthorizedError

JWT_SUBJECT_CLAIM = "sub"


def create_access_token(user_id: UUID) -> str:
    """Create a signed JWT for the given user id."""
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        JWT_SUBJECT_CLAIM: str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> UUID:
    """Decode and validate a JWT, returning the user id it was issued for.

    Raises UnauthorizedError on any invalid/expired/malformed token so
    callers don't need to know about PyJWT's exception types.
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Session token has expired.") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError("Invalid session token.") from exc

    subject = payload.get(JWT_SUBJECT_CLAIM)
    if subject is None:
        raise UnauthorizedError("Session token is missing its subject claim.")

    try:
        return UUID(subject)
    except (ValueError, TypeError) as exc:
        raise UnauthorizedError("Session token subject is malformed.") from exc

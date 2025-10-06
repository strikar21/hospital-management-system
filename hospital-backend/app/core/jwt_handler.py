"""
JWT Token Handler for Hospital Management System
Handles token generation, validation, and refresh
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import HTTPException, status
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Token configuration
ALGORITHM = settings.algorithm
SECRET_KEY = settings.secretKey
ACCESS_TOKEN_EXPIRE_MINUTES = settings.accessTokenExpireMinutes


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT access token

    Args:
        data: Payload data to encode in token (should include 'sub' for user ID)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # Add standard claims
    to_encode.update({
        "exp": expire,  # Expiration time
        "iat": datetime.utcnow(),  # Issued at
        "type": "access"  # Token type
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    logger.info(f"Created access token for user: {data.get('sub')}")
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create JWT refresh token (longer expiration)

    Args:
        data: Payload data (should include 'sub' for user ID)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Refresh tokens last 7 days by default
        expire = datetime.utcnow() + timedelta(days=7)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"  # Mark as refresh token
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    logger.info(f"Created refresh token for user: {data.get('sub')}")
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.error(f"Invalid token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """
    Verify token and check token type

    Args:
        token: JWT token string
        token_type: Expected token type ('access' or 'refresh')

    Returns:
        Decoded token payload

    Raises:
        HTTPException: If token is invalid, expired, or wrong type
    """
    payload = decode_token(token)

    # Verify token type
    if payload.get("type") != token_type:
        logger.warning(f"Wrong token type: expected {token_type}, got {payload.get('type')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token type. Expected {token_type} token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify subject (user ID) exists
    user_id = payload.get("sub")
    if not user_id:
        logger.error("Token missing subject (user ID)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


def get_user_from_token(token: str) -> Dict[str, Any]:
    """
    Extract user information from token

    Args:
        token: JWT access token string

    Returns:
        User information dict with id, role, etc.

    Raises:
        HTTPException: If token is invalid
    """
    payload = verify_token(token, token_type="access")

    return {
        "id": payload.get("sub"),
        "role": payload.get("role"),
        "department": payload.get("department"),
        "permissions": payload.get("permissions", [])
    }


def check_token_expiry(token: str) -> Dict[str, Any]:
    """
    Check token expiration without raising exception

    Args:
        token: JWT token string

    Returns:
        Dict with 'valid', 'expired', 'expires_at' info
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")

        if exp_timestamp:
            expires_at = datetime.fromtimestamp(exp_timestamp)
            is_expired = datetime.utcnow() > expires_at

            return {
                "valid": True,
                "expired": is_expired,
                "expires_at": expires_at.isoformat(),
                "time_remaining": str(expires_at - datetime.utcnow()) if not is_expired else "0"
            }
        else:
            return {
                "valid": False,
                "expired": True,
                "expires_at": None,
                "time_remaining": "0"
            }

    except JWTError:
        return {
            "valid": False,
            "expired": True,
            "expires_at": None,
            "time_remaining": "0"
        }

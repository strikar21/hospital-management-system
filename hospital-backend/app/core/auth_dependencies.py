"""
Authentication Dependencies for FastAPI
Used to protect endpoints and enforce role-based access control
"""

from typing import Optional, List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging

from .jwt_handler import get_user_from_token
from ..core.database import getDbConnection

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Get current authenticated user from JWT token

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        User information dict

    Raises:
        HTTPException: If token is invalid or user not found

    Usage:
        @router.get("/protected")
        async def protected_endpoint(current_user: dict = Depends(get_current_user)):
            return {"user": current_user}
    """
    token = credentials.credentials

    # Check if token is blacklisted
    async with getDbConnection() as conn:
        is_blacklisted = await conn.fetchval(
            'SELECT EXISTS(SELECT 1 FROM token_blacklist WHERE token = $1 AND expires_at > NOW())',
            token
        )

        if is_blacklisted:
            logger.warning(f"Blacklisted token attempted use")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Decode and validate token
    user_info = get_user_from_token(token)
    user_id = user_info.get("id")

    # Verify user still exists and is active
    async with getDbConnection() as conn:
        query = 'SELECT id, "firstName", "lastName", role, department, "isActive" FROM staff WHERE id = $1'
        staff_row = await conn.fetchrow(query, user_id)

        if not staff_row:
            logger.warning(f"User not found: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        staff_dict = dict(staff_row)

        if not staff_dict.get("isActive"):
            logger.warning(f"Inactive user attempted access: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        # Return user info
        return {
            "id": staff_dict["id"],
            "firstName": staff_dict["firstName"],
            "lastName": staff_dict["lastName"],
            "role": staff_dict["role"],
            "department": staff_dict.get("department"),
        }


async def get_current_active_user(
    current_user: dict = Depends(get_current_user)
) -> dict:
    """
    Get current active user (alias for get_current_user)

    This is included for compatibility with common FastAPI patterns
    """
    return current_user


class RoleChecker:
    """
    Dependency class to check if user has required role(s)

    Usage:
        # Single role:
        @router.get("/admin-only", dependencies=[Depends(RoleChecker(["Administrator"]))])

        # Multiple roles:
        @router.get("/doctors-nurses", dependencies=[Depends(RoleChecker(["Doctor", "Nurse"]))])

        # Or use in parameter:
        @router.get("/protected")
        async def protected(user: dict = Depends(RoleChecker(["Doctor"]))):
            return {"user": user}
    """

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, current_user: dict = Depends(get_current_user)) -> dict:
        user_role = current_user.get("role")

        if user_role not in self.allowed_roles:
            logger.warning(
                f"Access denied for user {current_user.get('id')} "
                f"with role {user_role}. Required: {self.allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {', '.join(self.allowed_roles)}",
            )

        return current_user


# Convenience role checker functions
async def require_doctor(current_user: dict = Depends(get_current_user)) -> dict:
    """Require Doctor role"""
    if current_user.get("role") != "Doctor":
        logger.warning(f"Access denied: {current_user.get('id')} with role {current_user.get('role')}, required Doctor")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required role: Doctor"
        )
    return current_user

async def require_nurse(current_user: dict = Depends(get_current_user)) -> dict:
    """Require Nurse role"""
    if current_user.get("role") != "Nurse":
        logger.warning(f"Access denied: {current_user.get('id')} with role {current_user.get('role')}, required Nurse")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required role: Nurse"
        )
    return current_user

async def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """Require Administrator role"""
    if current_user.get("role") != "Administrator":
        logger.warning(f"Access denied: {current_user.get('id')} with role {current_user.get('role')}, required Administrator")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required role: Administrator"
        )
    return current_user

async def require_medical_staff(current_user: dict = Depends(get_current_user)) -> dict:
    """Require Doctor or Nurse role"""
    if current_user.get("role") not in ["Doctor", "Nurse"]:
        logger.warning(f"Access denied: {current_user.get('id')} with role {current_user.get('role')}, required Doctor or Nurse")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required role: Doctor or Nurse"
        )
    return current_user

async def require_admin_or_medical(current_user: dict = Depends(get_current_user)) -> dict:
    """Require Administrator, Doctor, or Nurse role - for device management"""
    if current_user.get("role") not in ["Administrator", "Doctor", "Nurse"]:
        logger.warning(f"Access denied: {current_user.get('id')} with role {current_user.get('role')}, required Administrator, Doctor, or Nurse")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required role: Administrator, Doctor, or Nurse"
        )
    return current_user

async def require_any_staff(current_user: dict = Depends(get_current_user)) -> dict:
    """Require any staff role"""
    allowed_roles = ["Doctor", "Nurse", "Administrator", "Technician", "Lab Technician", "Radiologist"]
    if current_user.get("role") not in allowed_roles:
        logger.warning(f"Access denied: {current_user.get('id')} with role {current_user.get('role')}, required staff role")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Required: Staff role"
        )
    return current_user


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Get current user if authenticated, None otherwise
    Useful for endpoints that have different behavior for authenticated vs anonymous users

    Usage:
        @router.get("/public-or-private")
        async def flexible_endpoint(user: Optional[dict] = Depends(get_optional_current_user)):
            if user:
                return {"message": "Hello authenticated user", "user": user}
            else:
                return {"message": "Hello anonymous user"}
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


async def verify_device_key(device_key: str = None) -> dict:
    """
    Verify ESP32 device authentication using X-Device-Key header

    Args:
        device_key: Device key from X-Device-Key header

    Returns:
        Device information dict

    Raises:
        HTTPException: If device key is invalid or device not found

    Usage:
        from fastapi import Header

        @router.post("/esp32/vitals")
        async def receive_vitals(
            device_key: str = Header(None, alias="X-Device-Key"),
            device: dict = Depends(verify_device_key)
        ):
            return {"device": device}
    """
    if not device_key:
        logger.warning("Device authentication failed: No X-Device-Key header provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device authentication required. X-Device-Key header missing",
            headers={"WWW-Authenticate": "X-Device-Key"},
        )

    # Verify device key exists in database
    async with getDbConnection() as conn:
        query = '''SELECT id, name, "deviceType", status
                   FROM devices
                   WHERE "deviceKey" = $1'''
        device_row = await conn.fetchrow(query, device_key)

        if not device_row:
            logger.warning(f"Invalid device key attempted use")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid device key",
                headers={"WWW-Authenticate": "X-Device-Key"},
            )

        device_dict = dict(device_row)

        # Check device status
        if device_dict.get("status") not in ["active", "available", "assigned"]:
            logger.warning(f"Inactive device attempted access: {device_dict.get('id')}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device is not active",
            )

        # Get assigned patient from deviceassignments table
        assignment = await conn.fetchrow(
            'SELECT "patientId" FROM deviceassignments WHERE "deviceId" = $1 AND status = \'active\'',
            device_dict["id"]
        )

        # Update last seen timestamp
        await conn.execute(
            'UPDATE devices SET "lastSeen" = NOW() WHERE id = $1',
            device_dict["id"]
        )

        logger.info(f"✅ Device authenticated: {device_dict['id']}")

        # Return device info
        return {
            "id": device_dict["id"],
            "name": device_dict["name"],
            "deviceType": device_dict["deviceType"],
            "status": device_dict["status"],
            "assignedPatientId": assignment['patientId'] if assignment else None,
        }

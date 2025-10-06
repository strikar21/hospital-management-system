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


# Convenience role checker instances
require_doctor = RoleChecker(["Doctor"])
require_nurse = RoleChecker(["Nurse"])
require_admin = RoleChecker(["Administrator"])
require_medical_staff = RoleChecker(["Doctor", "Nurse"])
require_any_staff = RoleChecker(["Doctor", "Nurse", "Administrator", "Technician", "Lab Technician", "Radiologist"])


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

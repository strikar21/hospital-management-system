"""
Token refresh endpoint - Add this to auth.py or use as separate module
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import datetime
import logging

from ...core.database import getDbConnection
from ...core.jwt_handler import verify_token, create_access_token

router = APIRouter()
logger = logging.getLogger(__name__)


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh"""
    refreshToken: str


class RefreshTokenResponse(BaseModel):
    """Response model for token refresh"""
    accessToken: str
    tokenType: str = "bearer"


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_access_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token

    The refresh token is long-lived (7 days) and used to get new access tokens
    without requiring the user to login again
    """
    try:
        # Verify refresh token
        payload = verify_token(request.refreshToken, token_type="refresh")
        user_id = payload.get("sub")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Verify user still exists and is active
        async with getDbConnection() as conn:
            staff_row = await conn.fetchrow(
                'SELECT id, "firstName", "lastName", role, department, "isActive" FROM staff WHERE id = $1',
                user_id
            )

            if not staff_row:
                logger.warning(f"Refresh token for non-existent user: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )

            staff_dict = dict(staff_row)

            if not staff_dict.get("isActive"):
                logger.warning(f"Refresh token for inactive user: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive",
                )

            # Create new access token
            token_data = {
                "sub": staff_dict['id'],
                "role": staff_dict['role'],
                "department": staff_dict.get('department'),
                "firstName": staff_dict['firstName'],
                "lastName": staff_dict['lastName']
            }

            new_access_token = create_access_token(data=token_data)

            logger.info(f"Access token refreshed for user: {user_id}")

            return RefreshTokenResponse(
                accessToken=new_access_token,
                tokenType="bearer"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh token"
        )

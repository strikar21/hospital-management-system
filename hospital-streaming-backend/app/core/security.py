import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Header, Depends
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.db.database import database
from sqlalchemy import select
from app.models.device import Device

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class DeviceAuthenticator:
    """Handle device authentication and token management"""
    
    @staticmethod
    def generate_device_token() -> str:
        """Generate secure device token"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate API key for device"""
        return secrets.token_urlsafe(24)
    
    @staticmethod
    def hash_token(token: str) -> str:
        """Hash token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()
    
    @staticmethod
    def verify_token(token: str, hashed_token: str) -> bool:
        """Verify token against hash"""
        return hashlib.sha256(token.encode()).hexdigest() == hashed_token
    
    @staticmethod
    def create_device_jwt(device_id: str, device_type: str) -> str:
        """Create JWT token for device"""
        to_encode = {
            "device_id": device_id,
            "device_type": device_type,
            "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            "type": "device_access"
        }
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def verify_device_jwt(token: str) -> Dict[str, Any]:
        """Verify and decode device JWT"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid token")

# Dependency functions for FastAPI
async def authenticate_device_token(
    device_token: Optional[str] = Header(None, alias="X-Device-Token")
) -> Dict[str, Any]:
    """Authenticate device using token from header"""
    if not device_token:
        raise HTTPException(
            status_code=401, 
            detail="Device token required in X-Device-Token header"
        )
    
    try:
        # Query device by token
        query = select(Device).where(
            Device.device_token == device_token,
            Device.is_active == True
        )
        device = await database.fetch_one(query)
        
        if not device:
            raise HTTPException(status_code=401, detail="Invalid device token")
        
        # Check if device is online/active
        if device.status == "offline":
            # Allow authentication but log warning
            pass
        
        return {
            "device_id": device.device_id,
            "device_type": device.device_type,
            "device_name": device.name,
            "capabilities": device.capabilities or {},
            "location": device.location
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

async def authenticate_device_api_key(
    api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> Dict[str, Any]:
    """Authenticate device using API key from header"""
    if not api_key:
        raise HTTPException(
            status_code=401, 
            detail="API key required in X-API-Key header"
        )
    
    try:
        query = select(Device).where(
            Device.api_key == api_key,
            Device.is_active == True
        )
        device = await database.fetch_one(query)
        
        if not device:
            raise HTTPException(status_code=401, detail="Invalid API key")
        
        return {
            "device_id": device.device_id,
            "device_type": device.device_type,
            "device_name": device.name,
            "capabilities": device.capabilities or {},
            "location": device.location
        }
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

async def authenticate_device_jwt_token(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Authenticate device using JWT token from Authorization header"""
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Authorization header required"
        )
    
    try:
        # Extract token from "Bearer <token>"
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = authorization.split(" ")[1]
        
        # Verify JWT
        payload = DeviceAuthenticator.verify_device_jwt(token)
        
        # Verify device still exists and is active
        query = select(Device).where(
            Device.device_id == payload["device_id"],
            Device.is_active == True
        )
        device = await database.fetch_one(query)
        
        if not device:
            raise HTTPException(status_code=401, detail="Device not found or inactive")
        
        return {
            "device_id": device.device_id,
            "device_type": device.device_type,
            "device_name": device.name,
            "capabilities": device.capabilities or {},
            "location": device.location,
            "jwt_payload": payload
        }
        
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

# Authorization helpers
def check_device_capability(device_info: Dict[str, Any], required_capability: str) -> bool:
    """Check if device has required capability"""
    capabilities = device_info.get("capabilities", {})
    return capabilities.get(required_capability, False)

def require_device_capability(required_capability: str):
    """Dependency to require specific device capability"""
    def capability_checker(device_info: Dict[str, Any] = Depends(authenticate_device_token)):
        if not check_device_capability(device_info, required_capability):
            raise HTTPException(
                status_code=403,
                detail=f"Device does not have required capability: {required_capability}"
            )
        return device_info
    return capability_checker

# Rate limiting (basic implementation)
class DeviceRateLimiter:
    def __init__(self):
        self.requests = {}  # device_id -> [(timestamp, count)]
        self.max_requests_per_minute = 100
    
    def is_allowed(self, device_id: str) -> bool:
        """Check if device is within rate limits"""
        now = datetime.utcnow()
        minute_ago = now - timedelta(minutes=1)
        
        # Clean old entries
        if device_id in self.requests:
            self.requests[device_id] = [
                (ts, count) for ts, count in self.requests[device_id]
                if ts > minute_ago
            ]
        else:
            self.requests[device_id] = []
        
        # Count requests in last minute
        total_requests = sum(count for _, count in self.requests[device_id])
        
        if total_requests >= self.max_requests_per_minute:
            return False
        
        # Add current request
        self.requests[device_id].append((now, 1))
        return True

# Global rate limiter instance
device_rate_limiter = DeviceRateLimiter()

async def check_device_rate_limit(device_info: Dict[str, Any] = Depends(authenticate_device_token)):
    """Rate limiting dependency"""
    device_id = device_info["device_id"]
    
    if not device_rate_limiter.is_allowed(device_id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Too many requests from device."
        )
    
    return device_info

# Staff JWT Authentication
class StaffAuthenticator:
    """Handle staff JWT authentication"""
    
    @staticmethod
    def create_staff_access_token(staff_data: Dict[str, Any]) -> str:
        """Create JWT access token for staff"""
        to_encode = {
            "user_id": staff_data["id"],
            "staff_id": staff_data["staff_id"],
            "name": staff_data["name"],
            "role": staff_data["role"],
            "department": staff_data["department"],
            "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
            "type": "staff_access"
        }
        return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    
    @staticmethod
    def verify_staff_jwt(token: str) -> Dict[str, Any]:
        """Verify and decode staff JWT"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            if payload.get("type") != "staff_access":
                raise HTTPException(status_code=401, detail="Invalid token type")
            return payload
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

async def authenticate_staff_token(
    authorization: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Authenticate staff using JWT token from Authorization header"""
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Authorization header required"
        )
    
    try:
        # Extract token from "Bearer <token>"
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization format")
        
        token = authorization.split(" ")[1]
        
        # Verify JWT
        payload = StaffAuthenticator.verify_staff_jwt(token)
        
        return {
            "user_id": payload["user_id"],
            "staff_id": payload["staff_id"],
            "name": payload["name"],
            "role": payload["role"],
            "department": payload["department"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

def require_staff_role(required_roles: list):
    """Dependency to require specific staff roles"""
    def role_checker(staff_info: Dict[str, Any] = Depends(authenticate_staff_token)):
        if staff_info["role"] not in required_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Access denied. Required roles: {required_roles}"
            )
        return staff_info
    return role_checker

# Request Signing for API Security
import hmac
import hashlib
import base64
from fastapi import Request

class RequestSigner:
    """Handle API request signing for additional security"""
    
    @staticmethod
    def generate_signature(
        method: str,
        url_path: str, 
        body: str,
        timestamp: str,
        secret_key: str
    ) -> str:
        """Generate HMAC-SHA256 signature for request"""
        
        # Create canonical string
        canonical_string = f"{method}\n{url_path}\n{body}\n{timestamp}"
        
        # Generate HMAC signature
        signature = hmac.new(
            secret_key.encode('utf-8'),
            canonical_string.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        return base64.b64encode(signature).decode('utf-8')
    
    @staticmethod
    def verify_signature(
        request: Request,
        body: str,
        provided_signature: str,
        timestamp: str,
        secret_key: str
    ) -> bool:
        """Verify request signature"""
        
        try:
            # Check timestamp is within 5 minutes
            current_time = datetime.utcnow().timestamp()
            request_time = float(timestamp)
            
            if abs(current_time - request_time) > 300:  # 5 minutes
                return False
            
            # Generate expected signature
            expected_signature = RequestSigner.generate_signature(
                request.method,
                str(request.url.path),
                body,
                timestamp,
                secret_key
            )
            
            # Compare signatures securely
            return hmac.compare_digest(expected_signature, provided_signature)
            
        except Exception:
            return False

async def verify_request_signature(request: Request):
    """Middleware to verify request signatures"""
    
    # Get signature headers
    signature = request.headers.get("X-Signature")
    timestamp = request.headers.get("X-Timestamp")
    
    if not signature or not timestamp:
        raise HTTPException(
            status_code=401,
            detail="Missing signature or timestamp headers"
        )
    
    # Read request body
    body = await request.body()
    body_str = body.decode('utf-8') if body else ""
    
    # Verify signature
    is_valid = RequestSigner.verify_signature(
        request,
        body_str,
        signature,
        timestamp,
        settings.JWT_SECRET_KEY  # Use same secret for signing
    )
    
    if not is_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid request signature"
        )
    
    return True
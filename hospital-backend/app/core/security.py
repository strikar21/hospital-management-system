"""
Security utilities for PIN hashing and validation
"""

import hashlib
import re
from typing import Optional
from passlib.context import CryptContext

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_pin(pin: str) -> str:
    """
    Hash a 4-digit PIN using SHA-256
    """
    return hashlib.sha256(pin.encode()).hexdigest()

def verify_pin(pin: str, hashed_pin: str) -> bool:
    """
    Verify a PIN against its hash
    """
    return hash_pin(pin) == hashed_pin

def validate_pin_format(pin: str) -> bool:
    """
    Validate that PIN is exactly 4 digits
    """
    return bool(re.match(r'^\d{4}$', pin))

def validate_staff_id_format(staff_id: str) -> bool:
    """
    Validate staff ID format: DOC/NUR/ADM/PRV/TEC followed by 4 digits
    """
    return bool(re.match(r'^(DOC|NUR|ADM|PRV|TEC)\d{4}$', staff_id))

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    """
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    """
    return pwd_context.verify(password, hashed_password)

def generate_staff_id(role: str, sequence: int) -> str:
    """
    Generate staff ID based on role and sequence
    Doctor: DOCxxxx, Nurse: NURxxxx, Technician: TECxxxx, Administrator: ADMxxxx, Provider: PRVxxxx
    """
    role_prefixes = {
        "Doctor": "DOC",
        "Nurse": "NUR", 
        "Technician": "TEC",
        "Administrator": "ADM",
        "Provider": "PRV"
    }
    
    prefix = role_prefixes.get(role, "STF")
    return f"{prefix}{sequence:04d}"
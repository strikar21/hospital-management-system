"""
Security utilities for PIN hashing and validation
"""

import hashlib
import re
from typing import Optional
from passlib.context import CryptContext

# Password hashing context
pwdContext = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_pin(pin: str) -> str:
    """
    Hash a 4-digit PIN using bcrypt for security
    """
    return pwdContext.hash(pin)

def verify_pin(pin: str, hashedPin: str) -> bool:
    """
    Verify a PIN against its hash
    """
    return pwdContext.verify(pin, hashedPin)

def validate_pin_format(pin: str) -> bool:
    """
    Validate that PIN is exactly 4 digits
    """
    return bool(re.match(r'^\d{4}$', pin))

def validate_staff_id_format(staffId: str) -> bool:
    """
    Validate staff ID format: DOC/NUR/ADM/PRV/TEC followed by 4 digits
    """
    return bool(re.match(r'^(DOC|NUR|ADM|PRV|TEC)\d{4}$', staffId))

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    """
    return pwdContext.hash(password)

def verify_password(password: str, hashedPassword: str) -> bool:
    """
    Verify a password against its hash
    """
    return pwdContext.verify(password, hashedPassword)

def generateStaffId(role: str, sequence: int) -> str:
    """
    Generate staff ID based on role and sequence
    Doctor: DOCxxxx, Nurse: NURxxxx, Technician: TECxxxx, Administrator: ADMxxxx, Provider: PRVxxxx
    """
    rolePrefixes = {
        "doctor": "DOC",
        "nurse": "NUR", 
        "technician": "TEC",
        "administrator": "ADM",
        "provider": "PRV"
    }
    
    prefix = rolePrefixes.get(role, "STF")
    return f"{prefix}{sequence:04d}"
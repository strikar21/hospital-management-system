#!/usr/bin/env python3
"""
Script to update all staff passwords to default 'hospital123'
"""
import asyncio
import asyncpg
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def update_passwords():
    # Generate hash for 'hospital123'
    password_hash = pwd_context.hash("hospital123")
    print(f"Generated hash for 'hospital123': {password_hash}")
    
    # Connect to database
    conn = await asyncpg.connect("postgresql://hospital_user:hospital_pass@localhost:5433/hospital_streaming")
    
    try:
        # Update all staff to use the default password
        result = await conn.execute(
            "UPDATE staff SET password_hash = $1 WHERE password_hash IS NULL OR password_hash = ''",
            password_hash
        )
        
        print(f"Updated {result.split()[-1]} staff records with default password")
        
        # Also update existing passwords to the standard one
        result2 = await conn.execute(
            "UPDATE staff SET password_hash = $1",
            password_hash
        )
        
        print(f"Standardized all {result2.split()[-1]} staff passwords to 'hospital123'")
        
        # Show current staff
        rows = await conn.fetch("SELECT staff_id, name, role, nfc_id FROM staff WHERE is_active = true ORDER BY created_at")
        
        print("\n=== Current Staff (all with password 'hospital123') ===")
        for row in rows:
            print(f"ID: {row['staff_id']} | Name: {row['name']} | Role: {row['role']} | NFC: {row['nfc_id']}")
            
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(update_passwords())
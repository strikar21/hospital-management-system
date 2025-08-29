#!/usr/bin/env python3
"""Add PIN column to staff table"""

import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

async def add_pin_column():
    """Add pin_hash column to staff table"""
    from app.db.database import database
    
    try:
        await database.connect()
        print("Connected to database")
        
        # Check if pin_hash column already exists
        check_query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'staff' AND column_name = 'pin_hash'
        """
        
        result = await database.fetch_one(check_query)
        
        if result:
            print("pin_hash column already exists")
        else:
            # Add the pin_hash column
            alter_query = """
                ALTER TABLE staff 
                ADD COLUMN pin_hash VARCHAR(255)
            """
            
            await database.execute(alter_query)
            print("Added pin_hash column to staff table")
        
        await database.disconnect()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(add_pin_column())
    sys.exit(0 if success else 1)
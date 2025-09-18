#!/usr/bin/env python3
"""
Add dischargerstatus column to patients table
"""
import asyncio
import asyncpg
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def add_discharge_status_column():
    """Add dischargerstatus column to patients table"""
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host="localhost",
            port=5432,
            user="hospital_user",
            password="hospital_pass",
            database="hospital_db"
        )

        # Check if column already exists
        check_query = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'patients'
            AND column_name = 'dischargerstatus'
        """

        existing = await conn.fetchrow(check_query)

        if existing:
            logger.info("✅ Column 'dischargerstatus' already exists")
        else:
            # Add the column
            alter_query = """
                ALTER TABLE patients
                ADD COLUMN dischargerstatus TEXT DEFAULT 'active'
            """
            await conn.execute(alter_query)
            logger.info("✅ Added 'dischargerstatus' column to patients table")

        # Close connection
        await conn.close()

    except Exception as e:
        logger.error(f"❌ Failed to add discharge status column: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(add_discharge_status_column())
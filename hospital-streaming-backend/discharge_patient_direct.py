#!/usr/bin/env python3
"""
Direct patient discharge script - bypasses API routing issues
Usage: python discharge_patient_direct.py P2508250225
"""
import asyncpg
import asyncio
import sys
from datetime import datetime

async def discharge_patient(patient_id: str):
    """Discharge patient by directly updating database"""
    
    try:
        # Connect to main database
        conn = await asyncpg.connect("postgresql://hospital_user:hospital_pass@localhost:5433/hospital_streaming")
        
        # Start transaction
        async with conn.transaction():
            # Check if patient exists and is active
            patient = await conn.fetchrow(
                "SELECT id, name, bed_number, ward, room FROM patients WHERE id = $1 AND is_active = true",
                patient_id
            )
            
            if not patient:
                print(f"ERROR: Patient {patient_id} not found or already discharged")
                return False
            
            print(f"Found patient: {patient['name']} in {patient['ward']}-{patient['room']}-{patient['bed_number']}")
            
            # Set patient as inactive (discharged) - DATA PRESERVED
            await conn.execute("""
                UPDATE patients 
                SET is_active = false, 
                    status = 'discharged'
                WHERE id = $1
            """, patient_id)
            
            # Free up the bed
            await conn.execute("""
                UPDATE hospital_beds 
                SET status = 'available', patient_id = NULL
                WHERE patient_id = $1
            """, patient_id)
            
            # Unassign devices (if table exists)
            try:
                await conn.execute("""
                    UPDATE devices 
                    SET assignment_status = 'free', assigned_to = NULL
                    WHERE assigned_to = $1
                """, patient_id)
            except:
                print("Note: Devices table may not exist or have different structure")
            
            # Ward capacity update (if table has data)
            # Skip this as ward_capacity appears to be empty
        
        await conn.close()
        
        print(f"SUCCESS: Patient {patient['name']} ({patient_id}) successfully discharged")
        print(f"Freed bed: {patient['ward']}-{patient['room']}-{patient['bed_number']}")
        print(f"Discharge time: {datetime.utcnow().isoformat()}")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to discharge patient: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python discharge_patient_direct.py <patient_id>")
        print("Example: python discharge_patient_direct.py P2508250225")
        sys.exit(1)
    
    patient_id = sys.argv[1]
    success = asyncio.run(discharge_patient(patient_id))
    sys.exit(0 if success else 1)
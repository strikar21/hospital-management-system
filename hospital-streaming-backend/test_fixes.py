#!/usr/bin/env python3
"""Test script to verify all fixes work"""

import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

async def test_schema():
    """Test the schema validation fix"""
    print("TESTING SCHEMA VALIDATION...")
    
    from app.schemas.staff import StaffCreate
    
    # Test 1: None staff_id should be allowed
    try:
        staff = StaffCreate(
            staff_id=None,
            name="John Test", 
            role="Consultant",
            department="Cardiology"
        )
        print(f"SUCCESS None staff_id: {staff.staff_id}")
    except Exception as e:
        print(f"FAILED None staff_id: {e}")
    
    # Test 2: Empty string staff_id should be allowed
    try:
        staff = StaffCreate(
            staff_id="",
            name="Jane Test",
            role="Senior Nurse", 
            department="Nursing"
        )
        print(f"SUCCESS Empty staff_id: {staff.staff_id}")
    except Exception as e:
        print(f"FAILED Empty staff_id: {e}")
    
    # Test 3: Valid staff_id should work
    try:
        staff = StaffCreate(
            staff_id="TEST001",
            name="Manual Test",
            role="Admin",
            department="Administration"
        )
        print(f"SUCCESS Manual staff_id: {staff.staff_id}")
    except Exception as e:
        print(f"FAILED Manual staff_id: {e}")

async def test_staff_service():
    """Test the staff service auto-generation"""
    print("\nTESTING STAFF ID GENERATION...")
    
    from app.services.staff_service import StaffService
    
    try:
        # Test role code mapping
        next_id = await StaffService.generate_staff_id("Consultant")
        print(f"SUCCESS Consultant ID: {next_id}")
        
        next_id = await StaffService.generate_staff_id("Senior Nurse") 
        print(f"SUCCESS Senior Nurse ID: {next_id}")
        
        next_id = await StaffService.generate_staff_id("Hospital Administrator")
        print(f"SUCCESS Hospital Administrator ID: {next_id}")
        
    except Exception as e:
        print(f"FAILED Staff ID generation: {e}")

async def main():
    """Run all tests"""
    print("TESTING ALL FIXES...\n")
    
    await test_schema()
    await test_staff_service()
    
    print(f"\nALL TESTS COMPLETED!")

if __name__ == "__main__":
    asyncio.run(main())
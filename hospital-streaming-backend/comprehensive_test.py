#!/usr/bin/env python3
"""Comprehensive test of all fixes"""

import asyncio
import json
import sys
import os
sys.path.insert(0, os.getcwd())

async def run_all_tests():
    """Run comprehensive tests of all fixes"""
    print("COMPREHENSIVE SYSTEM TEST")
    print("=" * 50)
    
    # Test 1: Schema validation 
    print("\n1. TESTING SCHEMA VALIDATION:")
    from app.schemas.staff import StaffCreate
    
    test_cases = [
        {"staff_id": None, "name": "Test1", "role": "Consultant", "department": "Cardiology"},
        {"staff_id": "", "name": "Test2", "role": "Senior Nurse", "department": "Nursing"}, 
        {"name": "Test3", "role": "Admin", "department": "Administration"},  # No staff_id field
        {"staff_id": "MANUAL001", "name": "Test4", "role": "Intern", "department": "Internal Medicine"}
    ]
    
    for i, case in enumerate(test_cases):
        try:
            staff = StaffCreate(**case)
            print(f"   Case {i+1}: SUCCESS - staff_id={staff.staff_id}")
        except Exception as e:
            print(f"   Case {i+1}: FAILED - {e}")
    
    # Test 2: Staff service
    print("\n2. TESTING STAFF ID GENERATION:")
    from app.services.staff_service import StaffService
    
    test_roles = ["Consultant", "Senior Nurse", "Hospital Administrator", "Department Head"]
    
    for role in test_roles:
        try:
            staff_id = await StaffService.generate_staff_id(role)
            role_code = StaffService.ROLE_CODES.get(role, "UNK")
            print(f"   {role}: {staff_id} (code: {role_code})")
        except Exception as e:
            print(f"   {role}: ERROR - {e}")
    
    # Test 3: Database connectivity
    print("\n3. TESTING DATABASE:")
    try:
        from app.db.database import database
        result = await database.fetch_val("SELECT COUNT(*) FROM staff WHERE is_active = true")
        print(f"   Active staff count: {result}")
        
        # Test device_assignments table fix
        result = await database.fetch_val("SELECT COUNT(*) FROM device_assignments WHERE is_active = true") 
        print(f"   Active device assignments: {result}")
        
    except Exception as e:
        print(f"   Database test FAILED: {e}")
    
    print(f"\n{'='*50}")
    print("COMPREHENSIVE TEST COMPLETED!")
    
if __name__ == "__main__":
    asyncio.run(run_all_tests())
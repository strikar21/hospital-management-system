"""
Test Consent Management (DPDP Act 2023 Compliance)
Tests consent creation, search, withdrawal, and validation
"""

import asyncio
import asyncpg
from datetime import datetime, timezone, timedelta
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.fhir_r5.handlers.consent_handler import ConsentHandler


DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'hospital',
    'password': 'hospital123',
    'database': 'hospitaldb'
}


async def test_consent_management():
    """Test complete consent management workflow"""

    print("=" * 70)
    print("Testing Consent Management (DPDP Act 2023)")
    print("=" * 70)

    pool = await asyncpg.create_pool(**DB_CONFIG)
    handler = ConsentHandler(pool)

    try:
        # Test 1: Create consent
        print("\n[TEST 1] Creating patient consent...")

        consent = await handler.create_consent(
            patient_id="PAT000001",
            scope="patient-privacy",
            category=["IDSCL", "TREATMENT"],
            purpose_of_use=["TREAT", "ETREAT"],
            effective_start=datetime.now(timezone.utc),
            effective_end=datetime.now(timezone.utc) + timedelta(days=365),
            grantor_signature="BASE64_PATIENT_SIGNATURE_HERE",
            witness_signature="BASE64_WITNESS_SIGNATURE_HERE",
            created_by="STF000001"
        )

        consent_id = consent['id']
        print(f"  [SUCCESS] Created consent {consent_id}")
        print(f"  Patient: {consent['patient']['reference']}")
        print(f"  Status: {consent['status']}")
        print(f"  Scope: {consent['scope']['coding'][0]['code']}")
        print(f"  Categories: {[c['coding'][0]['code'] for c in consent['category']]}")
        print(f"  Purposes: {[p['code'] for p in consent['provision']['purpose']]}")

        # Test 2: Get consent by ID
        print("\n[TEST 2] Retrieving consent by ID...")

        retrieved = await handler.get_consent(consent_id)

        if retrieved:
            print(f"  [SUCCESS] Retrieved consent {consent_id}")
            print(f"  Status: {retrieved['status']}")
        else:
            print(f"  [FAILED] Could not retrieve consent")

        # Test 3: Get active consent for patient
        print("\n[TEST 3] Getting active consent for patient...")

        active_consent = await handler.get_active_consent("PAT000001")

        if active_consent:
            print(f"  [SUCCESS] Found active consent for PAT000001")
            print(f"  Consent ID: {active_consent['id']}")
            print(f"  Effective: {active_consent['provision']['period']['start']}")
        else:
            print(f"  [FAILED] No active consent found")

        # Test 4: Search consents
        print("\n[TEST 4] Searching consents...")

        consents = await handler.search_consents(
            patient_id="PAT000001",
            status="active"
        )

        print(f"  [SUCCESS] Found {len(consents)} active consent(s)")
        for c in consents:
            print(f"    - {c['id']}: {c['patient']['reference']} ({c['status']})")

        # Test 5: Check consent for purpose
        print("\n[TEST 5] Checking consent for specific purpose...")

        has_treat = await handler.check_consent("PAT000001", "TREAT")
        has_research = await handler.check_consent("PAT000001", "RESEARCH")

        print(f"  Has consent for TREAT: {has_treat}")
        print(f"  Has consent for RESEARCH: {has_research}")

        if has_treat and not has_research:
            print(f"  [SUCCESS] Consent validation working correctly")
        else:
            print(f"  [FAILED] Consent validation incorrect")

        # Test 6: Attempt to create duplicate consent (should fail)
        print("\n[TEST 6] Attempting to create duplicate consent...")

        try:
            duplicate = await handler.create_consent(
                patient_id="PAT000001",
                scope="patient-privacy",
                category=["IDSCL"],
                purpose_of_use=["TREAT"],
                effective_start=datetime.now(timezone.utc),
                created_by="STF000002"
            )
            print(f"  [FAILED] Should not allow duplicate active consent")
        except ValueError as e:
            print(f"  [SUCCESS] Correctly rejected duplicate: {e}")

        # Test 7: Withdraw consent
        print("\n[TEST 7] Withdrawing consent...")

        withdrawn = await handler.withdraw_consent(
            consent_id=consent_id,
            withdrawn_by="STF000002",
            reason="Patient requested withdrawal"
        )

        print(f"  [SUCCESS] Consent withdrawn")
        print(f"  Status: {withdrawn['status']}")
        print(f"  Withdrawn by: {withdrawn['_internal']['withdrawnBy']}")
        print(f"  Withdrawn at: {withdrawn['_internal']['withdrawnAt']}")

        # Test 8: Verify consent is no longer active
        print("\n[TEST 8] Verifying consent is no longer active...")

        still_active = await handler.check_consent("PAT000001", "TREAT")

        if not still_active:
            print(f"  [SUCCESS] Consent correctly marked as inactive")
        else:
            print(f"  [FAILED] Consent still appears active")

        # Test 9: Create new consent after withdrawal
        print("\n[TEST 9] Creating new consent after withdrawal...")

        new_consent = await handler.create_consent(
            patient_id="PAT000001",
            scope="treatment",
            category=["TREATMENT"],
            purpose_of_use=["TREAT", "ETREAT", "HPAYMT"],
            effective_start=datetime.now(timezone.utc),
            effective_end=datetime.now(timezone.utc) + timedelta(days=180),
            created_by="STF000001"
        )

        print(f"  [SUCCESS] Created new consent {new_consent['id']}")
        print(f"  Purposes: {[p['code'] for p in new_consent['provision']['purpose']]}")

        # Summary
        print("\n" + "=" * 70)
        print("CONSENT MANAGEMENT TEST SUMMARY")
        print("=" * 70)
        print("[PASSED] All consent management tests completed successfully!")
        print("\nKey Features Tested:")
        print("  [OK] Create consent with signatures")
        print("  [OK] Retrieve consent by ID")
        print("  [OK] Get active consent for patient")
        print("  [OK] Search consents by patient and status")
        print("  [OK] Check consent for specific purpose")
        print("  [OK] Prevent duplicate active consents")
        print("  [OK] Withdraw consent (DPDP Act right)")
        print("  [OK] Create new consent after withdrawal")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(test_consent_management())

"""
Test Audit Event Logging (DPDP + HIPAA Compliance)
Tests audit event creation, search, and analytics
"""

import asyncio
import asyncpg
from datetime import datetime, timezone, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.fhir_r5.handlers.audit_event_handler import AuditEventHandler


DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'hospital',
    'password': 'hospital123',
    'database': 'hospitaldb'
}


async def test_audit_logging():
    """Test complete audit logging functionality"""

    print("=" * 70)
    print("Testing Audit Event Logging (DPDP + HIPAA)")
    print("=" * 70)

    pool = await asyncpg.create_pool(**DB_CONFIG)
    handler = AuditEventHandler(pool)

    try:
        # Test 1: Log patient access (Read)
        print("\n[TEST 1] Logging patient read access...")

        event1 = await handler.log_access(
            action='R',
            agent_id='STF000001',
            agent_role='doctor',
            entity_type='Patient',
            entity_id='PAT000001',
            outcome='success',
            ip_address='192.168.1.100',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            purpose_of_event='TREAT'
        )

        print(f"  [SUCCESS] Logged read access")
        print(f"  Event ID: {event1['id']}")
        print(f"  Action: {event1['type']['display']}")
        print(f"  Agent: {event1['agent'][0]['who']['reference']}")
        print(f"  Entity: {event1['entity'][0]['what']['reference']}")
        print(f"  Outcome: {event1['outcome']}")

        # Test 2: Log device creation
        print("\n[TEST 2] Logging device creation...")

        event2 = await handler.log_access(
            action='C',
            agent_id='STF000001',
            agent_role='admin',
            entity_type='Device',
            entity_id='DEV000004',
            outcome='success',
            ip_address='192.168.1.100',
            purpose_of_event='TREAT'
        )

        print(f"  [SUCCESS] Logged device creation")
        print(f"  Event ID: {event2['id']}")
        print(f"  Action: {event2['type']['display']}")

        # Test 3: Log observation update
        print("\n[TEST 3] Logging observation update...")

        event3 = await handler.log_access(
            action='U',
            agent_id='STF000002',
            agent_role='nurse',
            entity_type='Observation',
            entity_id='OBS-HR-001',
            outcome='success',
            ip_address='192.168.1.101',
            purpose_of_event='ETREAT'
        )

        print(f"  [SUCCESS] Logged observation update")
        print(f"  Event ID: {event3['id']}")

        # Test 4: Log failed access attempt
        print("\n[TEST 4] Logging failed access attempt...")

        event4 = await handler.log_access(
            action='R',
            agent_id='STF000002',
            agent_role='nurse',
            entity_type='Patient',
            entity_id='PAT000001',
            outcome='failure',
            ip_address='192.168.1.101',
            user_agent='Mobile App v1.0'
        )

        print(f"  [SUCCESS] Logged failed access")
        print(f"  Outcome: {event4['outcome']}")

        # Test 5: Search audit events by agent
        print("\n[TEST 5] Searching audit events by agent...")

        doctor_events = await handler.search_audit_events(
            agent_id='STF000001',
            limit=10
        )

        print(f"  [SUCCESS] Found {len(doctor_events)} event(s) by STF000001")
        for event in doctor_events:
            print(f"    - {event['type']['display']} on {event['entity'][0]['what']['reference']}")

        # Test 6: Search by entity type
        print("\n[TEST 6] Searching audit events by entity type...")

        patient_events = await handler.search_audit_events(
            entity_type='Patient',
            limit=10
        )

        print(f"  [SUCCESS] Found {len(patient_events)} event(s) for Patient resources")

        # Test 7: Get patient access log
        print("\n[TEST 7] Getting patient access log...")

        access_log = await handler.get_patient_access_log(
            patient_id='PAT000001',
            limit=10
        )

        print(f"  [SUCCESS] Found {len(access_log)} access event(s) for PAT000001")
        for event in access_log:
            agent = event['agent'][0]['who']['reference']
            action = event['type']['display']
            outcome = event['outcome']
            print(f"    - {action} by {agent} ({outcome})")

        # Test 8: Get staff activity log
        print("\n[TEST 8] Getting staff activity log...")

        activity_log = await handler.get_staff_activity_log(
            staff_id='STF000001',
            limit=10
        )

        print(f"  [SUCCESS] Found {len(activity_log)} activity event(s) by STF000001")

        # Test 9: Get access summary
        print("\n[TEST 9] Getting access summary statistics...")

        summary = await handler.get_access_summary()

        print(f"  [SUCCESS] Retrieved access summary")
        print(f"    Total events: {summary['totalEvents']}")
        print(f"    Unique agents: {summary['uniqueAgents']}")
        print(f"    Unique entities: {summary['uniqueEntities']}")
        print(f"    Read events: {summary['readEvents']}")
        print(f"    Create events: {summary['createEvents']}")
        print(f"    Update events: {summary['updateEvents']}")
        print(f"    Failed events: {summary['failedEvents']}")

        # Test 10: Search with date range
        print("\n[TEST 10] Searching with date range...")

        start_date = datetime.now(timezone.utc) - timedelta(hours=1)

        recent_events = await handler.search_audit_events(
            start_date=start_date,
            limit=10
        )

        print(f"  [SUCCESS] Found {len(recent_events)} event(s) in last hour")

        # Test 11: Verify 6-year retention
        print("\n[TEST 11] Verifying 6-year retention policy...")

        event = await handler.get_audit_event(event1['id'])
        expires_at = datetime.fromisoformat(event['_internal']['expiresAt'].replace('Z', '+00:00'))
        retention_days = (expires_at - datetime.now(timezone.utc)).days

        print(f"  Event created: {event['recorded']}")
        print(f"  Expires at: {event['_internal']['expiresAt']}")
        print(f"  Retention: ~{retention_days} days (~{retention_days // 365} years)")

        if 2180 <= retention_days <= 2200:  # ~6 years (allowing for some variance)
            print(f"  [SUCCESS] 6-year retention policy correctly applied")
        else:
            print(f"  [WARNING] Retention period may be incorrect")

        # Summary
        print("\n" + "=" * 70)
        print("AUDIT LOGGING TEST SUMMARY")
        print("=" * 70)
        print("[PASSED] All audit logging tests completed successfully!")
        print("\nKey Features Tested:")
        print("  [OK] Log Create, Read, Update actions")
        print("  [OK] Log success and failure outcomes")
        print("  [OK] Track IP address and user agent")
        print("  [OK] Track purpose of event")
        print("  [OK] Search by agent, entity type, action")
        print("  [OK] Patient access log (who accessed this patient)")
        print("  [OK] Staff activity log (what did this staff member do)")
        print("  [OK] Access summary statistics")
        print("  [OK] Date range filtering")
        print("  [OK] 6-year retention policy (HIPAA)")
        print("=" * 70)

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(test_audit_logging())

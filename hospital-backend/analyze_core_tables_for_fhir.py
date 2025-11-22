"""
Analyze core tables to determine FHIR R5 alignment
"""
import asyncio
from app.core.database import getDbConnection

async def analyze_tables():
    async with getDbConnection() as conn:
        print("=" * 70)
        print("CORE TABLE ANALYSIS FOR FHIR R5 ALIGNMENT")
        print("=" * 70)

        # Get all core tables
        core_tables = [
            'auditlog',
            'deviceBaselines',
            'deviceCalibration',
            'deviceMaintenanceHistory',
            'device_certificates',
            'device_mac_mapping',
            'deviceassignments',
            'devices',
            'impedancereadings',
            'patient_alerts',
            'patients',
            'patientstates',
            'provisioning_codes',
            'staff',
            'token_blacklist',
            'watchremovalevents'
        ]

        print("\n" + "=" * 70)
        print("ANALYZING EACH TABLE")
        print("=" * 70)

        for table in core_tables:
            # Get column info
            columns = await conn.fetch("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = $1
                ORDER BY ordinal_position
            """, table)

            # Get row count (handle case-sensitive table names)
            try:
                count = await conn.fetchval(f'SELECT COUNT(*) FROM "{table}"')
            except:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")

            print(f"\n{table.upper()}")
            print(f"  Rows: {count}")
            print(f"  Columns: {len(columns)}")

            # Show first few columns
            for col in columns[:5]:
                print(f"    - {col['column_name']}: {col['data_type']}")
            if len(columns) > 5:
                print(f"    ... and {len(columns) - 5} more")

        print("\n" + "=" * 70)
        print("FHIR R5 MAPPING RECOMMENDATIONS")
        print("=" * 70)

        recommendations = {
            'patients': {
                'action': 'MIGRATE TO FHIR',
                'fhir_resource': 'Patient',
                'reason': 'Patient demographics should be FHIR R5 Patient resource',
                'priority': 'HIGH'
            },
            'devices': {
                'action': 'MIGRATE TO FHIR',
                'fhir_resource': 'Device',
                'reason': 'Devices (ESP32 watches) should be FHIR R5 Device resource',
                'priority': 'HIGH'
            },
            'deviceassignments': {
                'action': 'REVIEW',
                'fhir_resource': 'DeviceAssociation or keep as HMS table',
                'reason': 'Assignment tracking - may need custom table or use DeviceAssociation',
                'priority': 'MEDIUM'
            },
            'staff': {
                'action': 'MIGRATE TO FHIR',
                'fhir_resource': 'Practitioner',
                'reason': 'Staff should be FHIR R5 Practitioner resource',
                'priority': 'HIGH'
            },
            'patient_alerts': {
                'action': 'MIGRATE TO FHIR',
                'fhir_resource': 'DetectedIssue or Flag',
                'reason': 'Clinical alerts should be FHIR DetectedIssue or Flag resources',
                'priority': 'HIGH'
            },
            'patientstates': {
                'action': 'REVIEW',
                'fhir_resource': 'Observation (clinical status)',
                'reason': 'Patient states could be FHIR Observation or keep for real-time tracking',
                'priority': 'MEDIUM'
            },
            'deviceBaselines': {
                'action': 'KEEP AS HMS',
                'fhir_resource': 'N/A - device calibration data',
                'reason': 'Device-specific calibration, not clinical data',
                'priority': 'LOW'
            },
            'deviceCalibration': {
                'action': 'KEEP AS HMS',
                'fhir_resource': 'N/A - device calibration data',
                'reason': 'Device-specific calibration, not clinical data',
                'priority': 'LOW'
            },
            'deviceMaintenanceHistory': {
                'action': 'KEEP AS HMS',
                'fhir_resource': 'N/A - operational data',
                'reason': 'Device maintenance is operational, not clinical',
                'priority': 'LOW'
            },
            'device_certificates': {
                'action': 'KEEP AS HMS',
                'fhir_resource': 'N/A - security infrastructure',
                'reason': 'mTLS certificates are security infrastructure',
                'priority': 'LOW'
            },
            'device_mac_mapping': {
                'action': 'KEEP AS HMS',
                'fhir_resource': 'N/A - device provisioning',
                'reason': 'MAC address mapping is provisioning infrastructure',
                'priority': 'LOW'
            },
            'provisioning_codes': {
                'action': 'KEEP AS HMS',
                'fhir_resource': 'N/A - device provisioning',
                'reason': 'Provisioning codes are infrastructure',
                'priority': 'LOW'
            },
            'impedancereadings': {
                'action': 'KEEP AS HMS',
                'fhir_resource': 'N/A - device quality metrics',
                'reason': 'Impedance is device quality data, not clinical vitals',
                'priority': 'LOW'
            },
            'watchremovalevents': {
                'action': 'KEEP AS HMS',
                'fhir_resource': 'N/A - operational tracking',
                'reason': 'Watch removal is operational workflow tracking',
                'priority': 'LOW'
            },
            'auditlog': {
                'action': 'MIGRATE TO FHIR',
                'fhir_resource': 'AuditEvent',
                'reason': 'Audit trail should be FHIR R5 AuditEvent for compliance',
                'priority': 'MEDIUM'
            },
            'token_blacklist': {
                'action': 'KEEP AS HMS',
                'fhir_resource': 'N/A - authentication infrastructure',
                'reason': 'JWT token blacklist is authentication infrastructure',
                'priority': 'LOW'
            }
        }

        print("\n[HIGH PRIORITY - MIGRATE TO FHIR]")
        for table, rec in recommendations.items():
            if rec['priority'] == 'HIGH':
                print(f"\n  {table}")
                print(f"    -> {rec['fhir_resource']}")
                print(f"    Reason: {rec['reason']}")

        print("\n[MEDIUM PRIORITY - REVIEW/DECIDE]")
        for table, rec in recommendations.items():
            if rec['priority'] == 'MEDIUM':
                print(f"\n  {table}")
                print(f"    -> {rec['fhir_resource']}")
                print(f"    Reason: {rec['reason']}")

        print("\n[LOW PRIORITY - KEEP AS HMS INFRASTRUCTURE]")
        for table, rec in recommendations.items():
            if rec['priority'] == 'LOW':
                print(f"\n  {table} -> {rec['action']}")

        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)

        high = [t for t, r in recommendations.items() if r['priority'] == 'HIGH']
        medium = [t for t, r in recommendations.items() if r['priority'] == 'MEDIUM']
        low = [t for t, r in recommendations.items() if r['priority'] == 'LOW']

        print(f"\nTables to migrate to FHIR (HIGH): {len(high)}")
        print(f"  - {', '.join(high)}")

        print(f"\nTables to review (MEDIUM): {len(medium)}")
        print(f"  - {', '.join(medium)}")

        print(f"\nTables to keep as HMS infrastructure (LOW): {len(low)}")
        print(f"  - Device infrastructure: deviceBaselines, deviceCalibration, deviceMaintenanceHistory")
        print(f"  - Security: device_certificates, device_mac_mapping, provisioning_codes")
        print(f"  - Auth: token_blacklist")
        print(f"  - Operational: impedancereadings, watchremovalevents")

        return recommendations

if __name__ == "__main__":
    import sys
    asyncio.run(analyze_tables())

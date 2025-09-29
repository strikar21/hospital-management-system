#!/usr/bin/env python3
"""
Patient Alerts Table Creation Script
Creates the patient_alerts table to support alert functionality in case sheets
Follows camelCase naming convention and integrates with existing aggregated timeline
"""

import asyncio
import asyncpg
import uuid
from datetime import datetime, timedelta

async def create_patient_alerts_table():
    """Create patient_alerts table and add sample data for testing"""

    connection_string = "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb"
    conn = await asyncpg.connect(connection_string)

    try:
        print("🏥 Creating patient_alerts table...")

        # Create patient_alerts table with camelCase columns
        create_table_query = """
        CREATE TABLE IF NOT EXISTS patient_alerts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            "patientId" UUID NOT NULL,
            type VARCHAR(50) NOT NULL DEFAULT 'vital',
            message TEXT NOT NULL,
            severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
            status VARCHAR(20) NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'acknowledged', 'resolved')),
            "vitalType" VARCHAR(50),
            "vitalValue" DECIMAL(10,2),
            "thresholdValue" DECIMAL(10,2),
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
            "acknowledgedBy" VARCHAR(50),
            "acknowledgedAt" TIMESTAMP WITH TIME ZONE,
            "resolvedBy" VARCHAR(50),
            "resolvedAt" TIMESTAMP WITH TIME ZONE,
            "deletedAt" TIMESTAMP WITH TIME ZONE,

            -- Foreign key constraint
            CONSTRAINT fk_patient_alerts_patient
                FOREIGN KEY ("patientId") REFERENCES patients(id) ON DELETE CASCADE,

            -- Index for efficient queries
            INDEX idx_patient_alerts_patient_id ("patientId"),
            INDEX idx_patient_alerts_created_at ("createdAt"),
            INDEX idx_patient_alerts_status (status)
        );
        """

        await conn.execute(create_table_query)
        print("✅ patient_alerts table created successfully")

        # Get some existing patient IDs for sample data
        print("🔍 Getting existing patient IDs...")
        existing_patients = await conn.fetch("SELECT id FROM patients LIMIT 3")

        if existing_patients:
            print(f"📋 Found {len(existing_patients)} patients for sample alerts")

            # Create sample alerts for testing
            sample_alerts = []

            for i, patient in enumerate(existing_patients):
                patient_id = patient['id']

                # Create different types of alerts for each patient
                alerts_for_patient = [
                    {
                        'id': str(uuid.uuid4()),
                        'patientId': patient_id,
                        'type': 'vital',
                        'message': 'Heart rate elevated above normal range',
                        'severity': 'high',
                        'status': 'active',
                        'vitalType': 'heartRate',
                        'vitalValue': 125.5,
                        'thresholdValue': 100.0,
                        'createdAt': datetime.now() - timedelta(hours=2)
                    },
                    {
                        'id': str(uuid.uuid4()),
                        'patientId': patient_id,
                        'type': 'vital',
                        'message': 'Blood pressure critical - immediate attention required',
                        'severity': 'critical',
                        'status': 'acknowledged',
                        'vitalType': 'bloodPressure',
                        'vitalValue': 180.0,
                        'thresholdValue': 140.0,
                        'createdAt': datetime.now() - timedelta(hours=6),
                        'acknowledgedBy': 'DOC0001',
                        'acknowledgedAt': datetime.now() - timedelta(hours=5, minutes=30)
                    },
                    {
                        'id': str(uuid.uuid4()),
                        'patientId': patient_id,
                        'type': 'medication',
                        'message': 'Medication administration overdue',
                        'severity': 'medium',
                        'status': 'resolved',
                        'createdAt': datetime.now() - timedelta(hours=12),
                        'acknowledgedBy': 'NUR0001',
                        'acknowledgedAt': datetime.now() - timedelta(hours=11, minutes=45),
                        'resolvedBy': 'NUR0001',
                        'resolvedAt': datetime.now() - timedelta(hours=11, minutes=30)
                    }
                ]

                sample_alerts.extend(alerts_for_patient)

            # Insert sample alerts
            print("📝 Creating sample alerts...")
            insert_query = """
            INSERT INTO patient_alerts (
                id, "patientId", type, message, severity, status,
                "vitalType", "vitalValue", "thresholdValue", "createdAt",
                "acknowledgedBy", "acknowledgedAt", "resolvedBy", "resolvedAt"
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
            )
            """

            for alert in sample_alerts:
                await conn.execute(
                    insert_query,
                    alert['id'], alert['patientId'], alert['type'], alert['message'],
                    alert['severity'], alert['status'], alert.get('vitalType'),
                    alert.get('vitalValue'), alert.get('thresholdValue'), alert['createdAt'],
                    alert.get('acknowledgedBy'), alert.get('acknowledgedAt'),
                    alert.get('resolvedBy'), alert.get('resolvedAt')
                )

            print(f"✅ Created {len(sample_alerts)} sample alerts")

            # Show summary
            alert_count = await conn.fetchval("SELECT COUNT(*) FROM patient_alerts")
            print(f"📊 Total alerts in database: {alert_count}")

            # Show alerts by status
            status_counts = await conn.fetch("""
                SELECT status, COUNT(*) as count
                FROM patient_alerts
                GROUP BY status
                ORDER BY status
            """)

            print("📈 Alerts by status:")
            for row in status_counts:
                print(f"  - {row['status']}: {row['count']} alerts")

        else:
            print("⚠️  No existing patients found - table created but no sample data added")

    except Exception as e:
        print(f"❌ Error creating patient_alerts table: {e}")
        raise
    finally:
        await conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    print("🚀 Starting patient_alerts table creation...")
    asyncio.run(create_patient_alerts_table())
    print("✅ Patient alerts table setup complete!")
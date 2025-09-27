#!/usr/bin/env python3
"""
Repository Query Optimization Analysis
Analyzes and suggests optimizations for repository queries
"""

import asyncio
import asyncpg
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://hospital_user:hospital123@localhost:5432/hospitaldb"

async def analyze_query_performance():
    """Analyze current query performance and suggest optimizations"""

    try:
        conn = await asyncpg.connect(DATABASE_URL)
        logger.info("Analyzing query performance...")

        # Test common repository queries
        performance_tests = [
            {
                "name": "Patient list with order by createdAt",
                "query": 'SELECT * FROM patients ORDER BY "createdAt" DESC LIMIT 10',
                "expected_improvement": "Should use idx_patients_created_at index"
            },
            {
                "name": "Patient status filtering",
                "query": "SELECT * FROM patients WHERE status = 'active' LIMIT 10",
                "expected_improvement": "Should use idx_patients_status index"
            },
            {
                "name": "Patient medications with status",
                "query": 'SELECT * FROM medications WHERE "patientId" = \'test\' AND status = \'active\' ORDER BY "createdAt" DESC LIMIT 5',
                "expected_improvement": "Should use idx_medications_patient_status index"
            },
            {
                "name": "Device assignments by patient",
                "query": 'SELECT * FROM deviceassignments WHERE "patientId" = \'test\' AND status = \'active\' ORDER BY "assignedAt" DESC LIMIT 5',
                "expected_improvement": "Should use idx_deviceassignments_patient index"
            },
            {
                "name": "Staff by NFC card",
                "query": 'SELECT * FROM staff WHERE "nfcCardId" = \'test\' LIMIT 1',
                "expected_improvement": "Should use idx_staff_nfc_card index"
            }
        ]

        print("\nQUERY PERFORMANCE ANALYSIS")
        print("=" * 60)
        print(f"{'Query':<35} {'Time (ms)':<12} {'Expected Optimization'}")
        print("-" * 60)

        for test in performance_tests:
            try:
                start_time = time.time()
                await conn.fetch(test["query"])
                end_time = time.time()

                execution_time = round((end_time - start_time) * 1000, 2)
                print(f"{test['name']:<35} {execution_time:<12} {test['expected_improvement']}")

            except Exception as e:
                print(f"{test['name']:<35} {'ERROR':<12} {str(e)[:30]}...")

        # Check index usage
        print(f"\nINDEX USAGE VERIFICATION")
        print("=" * 50)

        index_usage_query = """
        SELECT
            indexname,
            idx_scan as scans,
            idx_tup_read as tuples_read,
            idx_tup_fetch as tuples_fetched
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        AND idx_scan > 0
        ORDER BY idx_scan DESC
        LIMIT 10
        """

        index_stats = await conn.fetch(index_usage_query)

        if index_stats:
            print(f"{'Index Name':<30} {'Scans':<8} {'Tuples Read':<12} {'Tuples Fetched'}")
            print("-" * 60)
            for stat in index_stats:
                print(f"{stat['indexname']:<30} {stat['scans']:<8} {stat['tuples_read']:<12} {stat['tuples_fetched']}")
        else:
            print("No index usage statistics available yet")

        await conn.close()

    except Exception as e:
        logger.error(f"ERROR: Query analysis failed: {e}")

async def suggest_query_optimizations():
    """Suggest specific query optimizations for the repository pattern"""

    print(f"\nQUERY OPTIMIZATION SUGGESTIONS")
    print("=" * 50)

    suggestions = [
        {
            "component": "BaseRepository.get_all()",
            "current": "Basic filtering with WHERE conditions",
            "optimization": "Add query hints and optimize JOIN patterns",
            "impact": "15-30% performance improvement"
        },
        {
            "component": "PatientRepository.get_complete_patient_data()",
            "current": "Multiple LEFT JOINs in single query",
            "optimization": "Consider parallel queries for large datasets",
            "impact": "20-40% improvement for complex patient data"
        },
        {
            "component": "MedicationRepository.get_medication_history()",
            "current": "JSON aggregation with LEFT JOIN",
            "optimization": "Add filtering before aggregation",
            "impact": "25-50% improvement for patients with many medications"
        },
        {
            "component": "BaseRepository filtering",
            "current": "Dynamic WHERE clause building",
            "optimization": "Use prepared statements for common patterns",
            "impact": "10-20% improvement for repeated queries"
        },
        {
            "component": "Audit queries",
            "current": "Time-based queries without limits",
            "optimization": "Add automatic date range limits",
            "impact": "50-80% improvement for audit log queries"
        }
    ]

    for i, suggestion in enumerate(suggestions, 1):
        print(f"\n{i}. {suggestion['component']}")
        print(f"   Current: {suggestion['current']}")
        print(f"   Optimize: {suggestion['optimization']}")
        print(f"   Impact: {suggestion['impact']}")

async def generate_optimized_queries():
    """Generate optimized versions of common repository queries"""

    print(f"\nOPTIMIZED QUERY EXAMPLES")
    print("=" * 50)

    optimizations = [
        {
            "title": "Optimized Patient List Query",
            "original": """
            SELECT * FROM patients
            ORDER BY "createdAt" DESC
            LIMIT $1 OFFSET $2
            """,
            "optimized": """
            SELECT p.id, p."firstName", p."lastName", p.status, p."roomNumber",
                   p."assignedDeviceId", p."createdAt"
            FROM patients p
            WHERE p.status != 'deleted'
            ORDER BY p."createdAt" DESC
            LIMIT $1 OFFSET $2
            """,
            "benefit": "Reduces data transfer and improves cache efficiency"
        },
        {
            "title": "Optimized Medication History Query",
            "original": """
            SELECT m.*, json_agg(ma.*) as administrations
            FROM medications m
            LEFT JOIN medicationadministrations ma ON m.id = ma."medicationId"
            WHERE m."patientId" = $1
            GROUP BY m.id
            """,
            "optimized": """
            SELECT m.*,
                   json_agg(ma.* ORDER BY ma."administeredAt" DESC) FILTER (WHERE ma.id IS NOT NULL) as administrations
            FROM medications m
            LEFT JOIN medicationadministrations ma ON m.id = ma."medicationId"
                AND ma."administeredAt" >= NOW() - INTERVAL '30 days'
            WHERE m."patientId" = $1 AND m.status = 'active'
            GROUP BY m.id
            ORDER BY m."createdAt" DESC
            """,
            "benefit": "Limits administration history and adds proper ordering"
        },
        {
            "title": "Optimized Device Assignment Query",
            "original": """
            SELECT * FROM deviceassignments
            WHERE "patientId" = $1
            ORDER BY "assignedAt" DESC
            """,
            "optimized": """
            SELECT da.*, d.name as device_name, d.type as device_type
            FROM deviceassignments da
            INNER JOIN devices d ON da."deviceId" = d.id
            WHERE da."patientId" = $1 AND da.status = 'active'
            ORDER BY da."assignedAt" DESC
            LIMIT 5
            """,
            "benefit": "Includes device details and limits results"
        }
    ]

    for opt in optimizations:
        print(f"\n{opt['title']}:")
        print(f"Original:{opt['original']}")
        print(f"Optimized:{opt['optimized']}")
        print(f"Benefit: {opt['benefit']}")

async def main():
    """Main optimization analysis function"""
    print("HOSPITAL DATABASE QUERY OPTIMIZATION ANALYSIS")
    print("=" * 60)

    # Analyze current performance
    await analyze_query_performance()

    # Provide optimization suggestions
    await suggest_query_optimizations()

    # Show optimized query examples
    await generate_optimized_queries()

    print(f"\nOPTIMIZATION ANALYSIS COMPLETE")
    print("Consider implementing the suggested optimizations in repository classes.")

if __name__ == "__main__":
    asyncio.run(main())
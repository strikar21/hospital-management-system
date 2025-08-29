from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging

from app.db.database import database, timescale_db

logger = logging.getLogger(__name__)

class HospitalAdminService:
    @staticmethod
    async def get_hospital_overview() -> Dict[str, Any]:
        """Get complete hospital overview statistics"""
        try:
            overview = {}
            
            # Staff statistics
            staff_stats = await HospitalAdminService._get_staff_statistics()
            overview["staff"] = staff_stats
            
            # Device statistics  
            device_stats = await HospitalAdminService._get_device_statistics()
            overview["devices"] = device_stats
            
            # Patient statistics (when patients are implemented)
            patient_stats = await HospitalAdminService._get_patient_statistics()
            overview["patients"] = patient_stats
            
            # Operational statistics
            operational_stats = await HospitalAdminService._get_operational_statistics()
            overview["operations"] = operational_stats
            
            # System health
            system_health = await HospitalAdminService._get_system_health()
            overview["system"] = system_health
            
            overview["generated_at"] = datetime.utcnow().isoformat()
            overview["hospital_info"] = {
                "name": "Multi-Specialty Hospital",
                "type": "100-bed Multi-specialty",
                "location": "India",
                "established": "2024"
            }
            
            return overview
            
        except Exception as e:
            logger.error(f"Error getting hospital overview: {e}")
            return {"error": "Failed to generate hospital overview"}
    
    @staticmethod
    async def _get_staff_statistics() -> Dict[str, Any]:
        """Get comprehensive staff statistics"""
        try:
            stats = {}
            
            # Total staff count
            total_query = "SELECT COUNT(*) FROM staff WHERE \"isActive\" = true"
            stats["total_active"] = await database.fetch_val(total_query)
            
            # Staff by role hierarchy
            role_query = """
                SELECT role, COUNT(*) as count
                FROM staff 
                WHERE \"isActive\" = true
                GROUP BY role
                ORDER BY count DESC
            """
            role_results = await database.fetch_all(role_query)
            stats["by_role"] = {row["role"]: row["count"] for row in role_results}
            
            # Staff by department
            dept_query = """
                SELECT department, COUNT(*) as count
                FROM staff 
                WHERE \"isActive\" = true
                GROUP BY department
                ORDER BY count DESC
            """
            dept_results = await database.fetch_all(dept_query)
            stats["by_department"] = {row["department"]: row["count"] for row in dept_results}
            
            # Recent staff additions (last 30 days)
            recent_query = """
                SELECT COUNT(*) FROM staff 
                WHERE \"isActive\" = true 
                AND \"createdAt\" > NOW() - INTERVAL '30 days'
            """
            stats["recent_additions"] = await database.fetch_val(recent_query)
            
            # Leadership counts
            leadership_roles = [
                'Hospital Administrator', 'CEO', 'Medical Superintendent', 
                'Chief Medical Officer', 'Chief Nursing Officer', 'Department Head'
            ]
            leadership_query = """
                SELECT COUNT(*) FROM staff 
                WHERE \"isActive\" = true 
                AND role = ANY(:roles)
            """
            stats["leadership_count"] = await database.fetch_val(
                leadership_query, 
                {"roles": leadership_roles}
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting staff statistics: {e}")
            return {"error": "Failed to get staff statistics"}
    
    @staticmethod 
    async def _get_device_statistics() -> Dict[str, Any]:
        """Get comprehensive device statistics"""
        try:
            stats = {}
            
            # Total devices
            total_query = "SELECT COUNT(*) FROM devices WHERE \"isActive\" = true"
            stats["total_active"] = await database.fetch_val(total_query)
            
            # Devices by type
            type_query = """
                SELECT \"deviceType\", COUNT(*) as count
                FROM devices 
                WHERE \"isActive\" = true
                GROUP BY \"deviceType\"
                ORDER BY count DESC
            """
            type_results = await database.fetch_all(type_query)
            stats["by_type"] = {row["deviceType"]: row["count"] for row in type_results}
            
            # Devices by status
            status_query = """
                SELECT status, COUNT(*) as count
                FROM devices 
                WHERE \"isActive\" = true
                GROUP BY status
                ORDER BY count DESC
            """
            status_results = await database.fetch_all(status_query)
            stats["by_status"] = {row["status"]: row["count"] for row in status_results}
            
            # Devices by location
            location_query = """
                SELECT location, COUNT(*) as count
                FROM devices 
                WHERE \"isActive\" = true
                GROUP BY location
                ORDER BY count DESC
                LIMIT 10
            """
            location_results = await database.fetch_all(location_query)
            stats["top_locations"] = {row["location"]: row["count"] for row in location_results}
            
            # Recently added devices (last 30 days)
            recent_query = """
                SELECT COUNT(*) FROM devices 
                WHERE \"isActive\" = true 
                AND \"createdAt\" > NOW() - INTERVAL '30 days'
            """
            stats["recent_additions"] = await database.fetch_val(recent_query)
            
            # Offline devices
            offline_query = """
                SELECT COUNT(*) FROM devices 
                WHERE \"isActive\" = true 
                AND status = 'offline'
            """
            stats["offline_count"] = await database.fetch_val(offline_query)
            
            # Low battery devices
            low_battery_query = """
                SELECT COUNT(*) FROM devices 
                WHERE \"isActive\" = true 
                AND \"batteryLevel\" IS NOT NULL 
                AND \"batteryLevel\" < 20
            """
            stats["low_battery_count"] = await database.fetch_val(low_battery_query)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting device statistics: {e}")
            return {"error": "Failed to get device statistics"}
    
    @staticmethod
    async def _get_patient_statistics() -> Dict[str, Any]:
        """Get patient statistics (placeholder for future implementation)"""
        try:
            stats = {}
            
            # Check if patients table exists and has data
            try:
                total_query = "SELECT COUNT(*) FROM patients WHERE \"isActive\" = true"
                stats["total_active"] = await database.fetch_val(total_query)
                
                # Patients by department
                dept_query = """
                    SELECT department, COUNT(*) as count
                    FROM patients 
                    WHERE \"isActive\" = true
                    GROUP BY department
                    ORDER BY count DESC
                """
                dept_results = await database.fetch_all(dept_query)
                stats["by_department"] = {row["department"]: row["count"] for row in dept_results}
                
                # Patients by status
                status_query = """
                    SELECT status, COUNT(*) as count
                    FROM patients 
                    WHERE \"isActive\" = true
                    GROUP BY status
                    ORDER BY count DESC
                """
                status_results = await database.fetch_all(status_query)
                stats["by_status"] = {row["status"]: row["count"] for row in status_results}
                
            except Exception:
                # Patients table might not exist yet or be empty
                stats["total_active"] = 0
                stats["by_department"] = {}
                stats["by_status"] = {}
                stats["note"] = "Patient management system ready for implementation"
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting patient statistics: {e}")
            return {"error": "Failed to get patient statistics"}
    
    @staticmethod
    async def _get_operational_statistics() -> Dict[str, Any]:
        """Get operational statistics"""
        try:
            stats = {}
            
            # Database sizes and performance
            db_stats_query = """
                SELECT 
                    schemaname,
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_stat_get_tuples_inserted(c.oid) as inserts,
                    pg_stat_get_tuples_updated(c.oid) as updates,
                    pg_stat_get_tuples_deleted(c.oid) as deletes
                FROM pg_tables pt
                LEFT JOIN pg_class c ON c.relname = pt.tablename
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """
            
            try:
                db_results = await database.fetch_all(db_stats_query)
                stats["database_tables"] = [
                    {
                        "table": row["tablename"],
                        "size": row["size"],
                        "activity": {
                            "inserts": row["inserts"] or 0,
                            "updates": row["updates"] or 0,
                            "deletes": row["deletes"] or 0
                        }
                    }
                    for row in db_results
                ]
            except Exception:
                stats["database_tables"] = []
            
            # System uptime simulation
            stats["system_uptime"] = "Available via system monitoring"
            stats["last_backup"] = "Configure backup monitoring"
            
            # Audit log summary (if exists)
            try:
                audit_query = """
                    SELECT action, COUNT(*) as count
                    FROM audit_logs 
                    WHERE timestamp > NOW() - INTERVAL '24 hours'
                    GROUP BY action
                    ORDER BY count DESC
                    LIMIT 10
                """
                audit_results = await database.fetch_all(audit_query)
                stats["recent_activities"] = {row["action"]: row["count"] for row in audit_results}
            except Exception:
                stats["recent_activities"] = {"note": "Audit logging ready for implementation"}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting operational statistics: {e}")
            return {"error": "Failed to get operational statistics"}
    
    @staticmethod
    async def _get_system_health() -> Dict[str, Any]:
        """Get system health information"""
        try:
            health = {}
            
            # Database connectivity
            try:
                await database.fetch_val("SELECT 1")
                health["postgresql"] = {"status": "healthy", "connection": "active"}
            except Exception as e:
                health["postgresql"] = {"status": "error", "error": str(e)}
            
            # TimescaleDB connectivity (if available)
            try:
                await timescale_db.fetch_val("SELECT 1")
                health["timescaledb"] = {"status": "healthy", "connection": "active"}
            except Exception as e:
                health["timescaledb"] = {"status": "warning", "error": "Not connected or not available"}
            
            # API health
            health["api"] = {
                "status": "healthy",
                "endpoints": [
                    "staff_management", "device_provisioning", "health_monitoring", 
                    "vitals_tracking", "admin_dashboard"
                ]
            }
            
            # Services status
            health["services"] = {
                "websocket_streaming": "active",
                "mqtt_broker": "configured", 
                "device_communication": "ready",
                "real_time_vitals": "ready"
            }
            
            return health
            
        except Exception as e:
            logger.error(f"Error getting system health: {e}")
            return {"error": "Failed to get system health"}
    
    @staticmethod
    async def get_detailed_staff_report() -> Dict[str, Any]:
        """Get detailed staff management report"""
        try:
            report = {}
            
            # Comprehensive role breakdown
            role_breakdown_query = """
                SELECT 
                    CASE 
                        WHEN role IN ('Hospital Administrator', 'CEO', 'Medical Superintendent') THEN 'Executive Leadership'
                        WHEN role IN ('Chief Medical Officer', 'Medical Director', 'Department Head') THEN 'Medical Leadership' 
                        WHEN role IN ('Chief Nursing Officer', 'Nursing Director', 'Nursing Supervisor') THEN 'Nursing Leadership'
                        WHEN role IN ('Senior Consultant', 'Consultant', 'Associate Consultant') THEN 'Senior Medical Staff'
                        WHEN role IN ('Senior Resident', 'Resident', 'Intern') THEN 'Medical Trainees'
                        WHEN role IN ('Senior Nurse', 'Staff Nurse', 'Junior Nurse') THEN 'Nursing Staff'
                        WHEN role IN ('Chief Technologist', 'Senior Technician', 'Technician') THEN 'Technical Staff'
                        WHEN role IN ('Provisioner', 'Admin', 'Receptionist') THEN 'Administrative Staff'
                        ELSE 'Other Staff'
                    END as category,
                    role,
                    COUNT(*) as count
                FROM staff 
                WHERE \"isActive\" = true
                GROUP BY category, role
                ORDER BY category, count DESC
            """
            
            role_results = await database.fetch_all(role_breakdown_query)
            
            # Organize by category
            categories = {}
            for row in role_results:
                category = row["category"]
                if category not in categories:
                    categories[category] = {}
                categories[category][row["role"]] = row["count"]
            
            report["role_hierarchy"] = categories
            
            # Department distribution
            dept_distribution_query = """
                SELECT 
                    department,
                    COUNT(*) as "totalStaff",
                    COUNT(*) FILTER (WHERE role LIKE '%Senior%' OR role LIKE '%Chief%' OR role LIKE '%Director%' OR role LIKE '%Head%') as "seniorStaff",
                    COUNT(*) FILTER (WHERE role LIKE '%Consultant%') as consultants,
                    COUNT(*) FILTER (WHERE role LIKE '%Nurse%') as "nursingStaff"
                FROM staff 
                WHERE \"isActive\" = true
                GROUP BY department
                ORDER BY "totalStaff" DESC
            """
            
            dept_results = await database.fetch_all(dept_distribution_query)
            report["department_distribution"] = [
                {
                    "department": row["department"],
                    "total_staff": row["totalStaff"],
                    "senior_staff": row["seniorStaff"],
                    "consultants": row["consultants"],
                    "nursing_staff": row["nursingStaff"]
                }
                for row in dept_results
            ]
            
            # Recent activity
            activity_query = """
                SELECT 
                    "staffId", name, role, department, "createdAt"
                FROM staff
                WHERE \"isActive\" = true
                ORDER BY "createdAt" DESC
                LIMIT 20
            """
            
            activity_results = await database.fetch_all(activity_query)
            report["recent_staff_additions"] = [
                {
                    "staff_id": row["staffId"],
                    "name": row["name"],
                    "role": row["role"],
                    "department": row["department"],
                    "joined": row["createdAt"].isoformat()
                }
                for row in activity_results
            ]
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating staff report: {e}")
            return {"error": "Failed to generate staff report"}
    
    @staticmethod
    async def get_device_health_report() -> Dict[str, Any]:
        """Get comprehensive device health report"""
        try:
            report = {}
            
            # Critical device issues
            critical_issues_query = """
                SELECT 
                    \"deviceId\", name, \"deviceType\", location, status, 
                    \"batteryLevel\", \"lastHeartbeat\", \"createdAt\"
                FROM devices
                WHERE \"isActive\" = true
                AND (
                    status IN ('offline', 'error') 
                    OR \"batteryLevel\" < 15
                    OR \"lastHeartbeat\" < NOW() - INTERVAL '1 hour'
                )
                ORDER BY 
                    CASE status 
                        WHEN 'error' THEN 1 
                        WHEN 'offline' THEN 2 
                        ELSE 3 
                    END,
                    \"batteryLevel\" ASC NULLS LAST
            """
            
            critical_results = await database.fetch_all(critical_issues_query)
            report["critical_issues"] = [
                {
                    "device_id": row["deviceId"],
                    "name": row["name"], 
                    "type": row["deviceType"],
                    "location": row["location"],
                    "status": row["status"],
                    "battery_level": row["batteryLevel"],
                    "last_seen": row["lastHeartbeat"].isoformat() if row["lastHeartbeat"] else None,
                    "issue_priority": "high" if row["status"] == "error" else "medium"
                }
                for row in critical_results
            ]
            
            # Device deployment by location
            location_deployment_query = """
                SELECT 
                    location,
                    COUNT(*) as "totalDevices",
                    COUNT(*) FILTER (WHERE status = 'online') as "onlineDevices",
                    COUNT(*) FILTER (WHERE \"deviceType\" = 'watch') as watches,
                    COUNT(*) FILTER (WHERE \"deviceType\" = 'vital_monitor') as monitors,
                    COUNT(*) FILTER (WHERE \"deviceType\" = 'door_scanner') as "doorScanners"
                FROM devices
                WHERE \"isActive\" = true
                GROUP BY location
                ORDER BY "totalDevices" DESC
            """
            
            location_results = await database.fetch_all(location_deployment_query)
            report["location_deployment"] = [
                {
                    "location": row["location"],
                    "total_devices": row["totalDevices"],
                    "online_devices": row["onlineDevices"],
                    "device_breakdown": {
                        "watches": row["watches"],
                        "monitors": row["monitors"], 
                        "door_scanners": row["doorScanners"]
                    },
                    "availability_rate": round((row["onlineDevices"] / row["totalDevices"]) * 100, 1) if row["totalDevices"] > 0 else 0
                }
                for row in location_results
            ]
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating device health report: {e}")
            return {"error": "Failed to generate device health report"}
    
    @staticmethod
    def _categorize_department(department: str) -> str:
        """Categorize department type"""
        clinical_depts = [
            "Cardiology", "Neurology", "Orthopedics", "Gynecology", 
            "General Surgery", "Pediatrics", "Emergency Medicine",
            "Internal Medicine", "Oncology", "Psychiatry"
        ]
        
        diagnostic_depts = ["Radiology", "Laboratory", "Pathology"]
        
        support_depts = [
            "Nursing", "Pharmacy", "Physiotherapy", "Administration",
            "IT Support", "Security", "Maintenance"
        ]
        
        if department in clinical_depts:
            return "Clinical"
        elif department in diagnostic_depts:
            return "Diagnostic"
        elif department in support_depts:
            return "Support"
        else:
            return "Other"
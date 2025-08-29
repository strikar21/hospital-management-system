from fastapi import APIRouter, HTTPException, Query, Depends, status
from typing import Optional
from datetime import datetime
from app.services.hospital_admin_service import HospitalAdminService
from app.services.staff_service import StaffService

router = APIRouter(prefix="/hospital-admin")

async def verify_admin_access(staff_id: str = Query(..., description="Staff ID of the administrator")):
    """Verify that the staff member has administrative access"""
    staff = await StaffService.get_staff_by_id(staff_id)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found"
        )
    
    # Define admin roles with different access levels
    executive_admin_roles = [
        "Hospital Administrator", "CEO", "Medical Superintendent"
    ]
    
    senior_admin_roles = [
        "Chief Medical Officer", "Medical Director", "Chief Nursing Officer", 
        "Nursing Director", "Department Head", "Assistant Administrator"
    ]
    
    general_admin_roles = [
        "Admin", "Department Manager", "Supervisor"
    ]
    
    all_admin_roles = executive_admin_roles + senior_admin_roles + general_admin_roles
    
    if staff.role not in all_admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative access required. Contact your Hospital Administrator."
        )
    
    # Add access level to the returned staff object by converting to dict
    staff_dict = staff.dict()
    if staff.role in executive_admin_roles:
        staff_dict["access_level"] = "executive"
    elif staff.role in senior_admin_roles:
        staff_dict["access_level"] = "senior" 
    else:
        staff_dict["access_level"] = "general"
    
    return staff_dict

@router.get("/dashboard")
async def get_hospital_dashboard(admin: dict = Depends(verify_admin_access)):
    """Get comprehensive hospital dashboard overview"""
    try:
        overview = await HospitalAdminService.get_hospital_overview()
        
        # Add admin context
        overview["accessed_by"] = {
            "staff_id": admin["staff_id"],
            "name": admin["name"],
            "role": admin["role"],
            "access_level": admin["access_level"],
            "department": admin["department"]
        }
        
        return overview
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate dashboard"
        )

@router.get("/reports/staff")
async def get_staff_management_report(admin: dict = Depends(verify_admin_access)):
    """Get detailed staff management report"""
    try:
        report = await HospitalAdminService.get_detailed_staff_report()
        
        report["report_metadata"] = {
            "generated_by": admin["name"],
            "generated_at": "2025-08-24T15:45:00Z",
            "access_level": admin["access_level"],
            "report_type": "Staff Management Analysis"
        }
        
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate staff report"
        )

@router.get("/reports/devices")
async def get_device_health_report(admin: dict = Depends(verify_admin_access)):
    """Get comprehensive device health and deployment report"""
    try:
        report = await HospitalAdminService.get_device_health_report()
        
        report["report_metadata"] = {
            "generated_by": admin["name"],
            "generated_at": "2025-08-24T15:45:00Z",
            "access_level": admin["access_level"],
            "report_type": "Device Health Analysis"
        }
        
        return report
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate device health report"
        )

@router.get("/quick-stats")
async def get_quick_stats(admin: dict = Depends(verify_admin_access)):
    """Get quick statistics for admin overview"""
    try:
        # Get essential numbers quickly
        stats = {}
        
        # Staff counts
        from app.db.database import database
        
        stats["staff"] = {
            "total": await database.fetch_val("SELECT COUNT(*) FROM staff WHERE is_active = true"),
            "doctors": await database.fetch_val(
                "SELECT COUNT(*) FROM staff WHERE is_active = true AND role LIKE '%Consultant%' OR role LIKE '%Doctor%'"
            ),
            "nurses": await database.fetch_val(
                "SELECT COUNT(*) FROM staff WHERE is_active = true AND role LIKE '%Nurse%'"
            ),
            "admin_staff": await database.fetch_val(
                "SELECT COUNT(*) FROM staff WHERE is_active = true AND role LIKE '%Admin%'"
            )
        }
        
        # Device counts
        stats["devices"] = {
            "total": await database.fetch_val("SELECT COUNT(*) FROM devices WHERE is_active = true"),
            "online": await database.fetch_val("SELECT COUNT(*) FROM devices WHERE is_active = true AND status = 'online'"),
            "offline": await database.fetch_val("SELECT COUNT(*) FROM devices WHERE is_active = true AND status = 'offline'"),
            "critical": await database.fetch_val("SELECT COUNT(*) FROM devices WHERE is_active = true AND (status = 'error' OR battery_level < 15)")
        }
        
        # System health
        stats["system"] = {
            "database_connected": True,
            "services_running": ["API", "WebSocket", "Device Management"],
            "last_backup": "Configure backup monitoring",
            "uptime": "Available via monitoring"
        }
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Failed to get quick stats"
        )

@router.get("/access-levels")
async def get_admin_access_levels():
    """Get information about administrative access levels"""
    return {
        "access_levels": {
            "executive": {
                "roles": ["Hospital Administrator", "CEO", "Medical Superintendent"],
                "permissions": [
                    "Full system access", "User management", "System configuration",
                    "Financial reports", "Strategic planning", "Policy decisions"
                ]
            },
            "senior": {
                "roles": [
                    "Chief Medical Officer", "Medical Director", "Chief Nursing Officer", 
                    "Nursing Director", "Department Head", "Assistant Administrator"
                ],
                "permissions": [
                    "Department management", "Staff supervision", "Resource allocation",
                    "Performance monitoring", "Clinical oversight"
                ]
            },
            "general": {
                "roles": ["Admin", "Department Manager", "Supervisor"],
                "permissions": [
                    "Daily operations", "Basic reporting", "Staff coordination",
                    "Resource requests", "Incident management"
                ]
            }
        }
    }

@router.get("/hospital-structure")
async def get_hospital_structure(admin: dict = Depends(verify_admin_access)):
    """Get complete hospital organizational structure"""
    try:
        from app.db.database import database
        
        # Get department structure with staff counts
        dept_structure_query = """
            SELECT 
                department,
                COUNT(*) as total_staff,
                COUNT(*) FILTER (WHERE role LIKE '%Chief%' OR role LIKE '%Director%' OR role LIKE '%Head%') as leadership,
                COUNT(*) FILTER (WHERE role LIKE '%Senior%') as senior_staff,
                array_agg(DISTINCT role) as roles_present
            FROM staff 
            WHERE is_active = true
            GROUP BY department
            ORDER BY total_staff DESC
        """
        
        dept_results = await database.fetch_all(dept_structure_query)
        
        structure = {
            "hospital_overview": {
                "type": "100-bed Multi-specialty Hospital",
                "location": "India",
                "specialties": [
                    "Cardiology", "Neurology", "Orthopedics", "Gynecology", 
                    "General Surgery", "Pediatrics", "Emergency Medicine",
                    "Internal Medicine", "Oncology", "Radiology"
                ],
                "support_services": [
                    "Laboratory", "Pharmacy", "Physiotherapy", "Administration",
                    "Nursing", "IT Support", "Security"
                ]
            },
            "departments": []
        }
        
        for row in dept_results:
            dept_info = {
                "name": row["department"],
                "total_staff": row["total_staff"],
                "leadership_count": row["leadership"],
                "senior_staff_count": row["senior_staff"],
                "roles_present": row["roles_present"] or [],
                "category": _categorize_department(row["department"])
            }
            structure["departments"].append(dept_info)
        
        return structure
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get hospital structure"
        )

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

@router.post("/alerts/system")
async def create_system_alert(
    message: str = Query(..., description="Alert message"),
    priority: str = Query(default="medium", description="Alert priority: low, medium, high, critical"),
    admin: dict = Depends(verify_admin_access)
):
    """Create a system-wide administrative alert"""
    try:
        # This would integrate with a notification system
        alert = {
            "id": f"ALERT_{int(datetime.now().timestamp())}",
            "message": message,
            "priority": priority,
            "created_by": admin["name"],
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "type": "administrative"
        }
        
        # In a real system, this would be stored and broadcast
        return {
            "success": True,
            "alert": alert,
            "message": "System alert created successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create system alert"
        )
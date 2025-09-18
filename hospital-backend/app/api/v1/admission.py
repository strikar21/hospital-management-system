"""
Admission workflow API endpoints for hospital management system
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import asyncpg
import logging
from datetime import datetime, date
import uuid
from dateutil import parser as date_parser

from ...core.database import get_db_connection
from ...utils.transformers import transform_dict_to_camel, serialize_dates_in_dict, transform_patient_to_camel

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/recommendations")
async def create_admission_recommendation(admission_data: dict):
    """Create a new admission recommendation from doctor assessment"""
    
    try:
        async with get_db_connection() as conn:
            # Generate systematic recommendation ID (REC + date + sequence)
            today = datetime.now().strftime('%Y%m%d')
            
            # Get count of recommendations today for sequence number
            count_query = """
                SELECT COUNT(*) FROM admissionrecommendations 
                WHERE DATE(createdat) = CURRENT_DATE
            """
            count_result = await conn.fetchval(count_query)
            sequence = (count_result or 0) + 1
            
            rec_id = f"REC{today}{sequence:03d}"  # REC20250907001, REC20250907002, etc.
            logger.info(f"🆔 Generated recommendation ID: {rec_id}")
            
            query = """
            INSERT INTO admissionrecommendations (
                firstname, lastname, age, dateofbirth, gender, diagnosis, priority, department, 
                recommendedward, assigneddoctor, recommendedby, 
                admissiondate, allergies, status
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING id, createdat
            """
            
            # Handle date conversion
            admission_date = admission_data.get('admissionDate')
            if admission_date and isinstance(admission_date, str):
                try:
                    admission_date = date_parser.parse(admission_date).date()
                except:
                    admission_date = None
            
            # Handle age vs DOB input - doctor can enter either
            age = admission_data.get('age')
            date_of_birth = admission_data.get('dateOfBirth')
            
            # Parse DOB if provided as string
            if date_of_birth and isinstance(date_of_birth, str):
                try:
                    date_of_birth = date_parser.parse(date_of_birth).date()
                except:
                    date_of_birth = None
            
            # Calculate missing field if only one is provided
            if age and not date_of_birth:
                # Age provided, calculate approximate DOB
                current_year = datetime.now().year
                birth_year = current_year - age
                date_of_birth = date(birth_year, 1, 1)
            elif date_of_birth and not age:
                # DOB provided, calculate age
                today = datetime.now().date()
                age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
            elif not age and not date_of_birth:
                raise HTTPException(status_code=400, detail="Either age or date of birth must be provided")
            
            # Auto-populate fields based on current user context
            # For now, we'll use the most common doctor (can be enhanced with proper auth later)
            recommended_by = admission_data.get('recommendedBy') or 'DOC0001'
            
            # Look up the recommending doctor's information from database
            doctor_query = "SELECT id, firstname, lastname, department FROM staff WHERE id = $1"
            doctor_info = await conn.fetchrow(doctor_query, recommended_by)
            
            if doctor_info:
                doctor_dict = dict(doctor_info)
                assigned_doctor = f"{doctor_dict['firstname'] or ''} {doctor_dict['lastname'] or ''}".strip()
                department = doctor_dict['department']
            else:
                # Fallback defaults
                assigned_doctor = admission_data.get('assignedDoctor') or 'Dr. Unknown'
                department = admission_data.get('department') or 'General Medicine'
            
            # Ward will be assigned by nurse during actual admission process
            ward = admission_data.get('ward') or admission_data.get('admissionType') or 'To Be Assigned'
            
            # Parse patient name with better error handling
            patient_name = admission_data.get('patientName', '').strip()
            
            if not patient_name:
                # Try alternative field names
                patient_name = admission_data.get('name', '').strip()
            
            if not patient_name:
                raise HTTPException(status_code=400, detail="Patient name is required")
            
            # Split name into first and last (handle multiple spaces)
            name_parts = [part.strip() for part in patient_name.split() if part.strip()]
            
            if len(name_parts) == 0:
                raise HTTPException(status_code=400, detail="Valid patient name is required")
            elif len(name_parts) == 1:
                # Single name - use as first name
                first_name = name_parts[0]
                last_name = ''
            else:
                # Multiple parts - first word as first name, rest as last name
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
            
            # Ensure names are not empty strings
            first_name = first_name or 'Unknown'
            last_name = last_name or 'Patient'
            
            result = await conn.fetchrow(
                query,
                first_name,
                last_name,
                age,
                date_of_birth,
                admission_data.get('gender'),
                admission_data.get('diagnosis', 'No diagnosis provided'),  # Use diagnosis field
                admission_data.get('priority', 'medium').lower(),
                department,
                ward,
                assigned_doctor,
                recommended_by,
                admission_date,
                admission_data.get('allergies'),
                'pending'
            )
            
            logger.info(f"✅ Created admission recommendation ID: {result['id']}")
            
            return JSONResponse(content={
                "success": True,
                "recommendationId": result['id'],
                "status": "pending",
                "message": "Admission recommendation created successfully. Waiting for nursing staff to process.",
                "createdAt": result['createdat'].isoformat()
            })
            
    except Exception as e:
        logger.error(f"❌ Error creating admission recommendation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create admission recommendation: {str(e)}")

@router.get("/recommendations")
async def get_admission_recommendations(status: Optional[str] = None):
    """Get admission recommendations with optional status filter"""
    
    try:
        async with get_db_connection() as conn:
            if status:
                query = """
                SELECT ar.*, 
                       (ar.firstname || ' ' || ar.lastname) as patientname,
                       (s.firstname || ' ' || s.lastname) as assigneddoctorname
                FROM admissionrecommendations ar
                LEFT JOIN staff s ON ar.assigneddoctor = s.id
                WHERE ar.status = $1 
                ORDER BY ar.createdat DESC
                """
                rows = await conn.fetch(query, status)
            else:
                query = """
                SELECT ar.*, 
                       (ar.firstname || ' ' || ar.lastname) as patientname,
                       (s.firstname || ' ' || s.lastname) as assigneddoctorname
                FROM admissionrecommendations ar
                LEFT JOIN staff s ON ar.assigneddoctor = s.id
                ORDER BY ar.createdat DESC
                """
                rows = await conn.fetch(query)
            
            recommendations = []
            for row in rows:
                rec_dict = dict(row)
                serialized_rec = serialize_dates_in_dict(rec_dict)
                # Transform to camelCase - no need for patientname field since frontend uses firstName + lastName
                transformed_rec = transform_dict_to_camel(serialized_rec)

                recommendations.append(transformed_rec)
            
            logger.info(f"✅ Retrieved {len(recommendations)} admission recommendations")
            
            # Debug: Check what's actually in the response
            if recommendations:
                first_rec = recommendations[0]
                logger.info(f"🔍 FINAL RESPONSE - First recommendation keys: {list(first_rec.keys())}")
                logger.info(f"🔍 FINAL RESPONSE - firstName: '{first_rec.get('firstName', 'NOT_FOUND')}', lastName: '{first_rec.get('lastName', 'NOT_FOUND')}'")

            return JSONResponse(content={
                "success": True,
                "recommendations": recommendations,
                "count": len(recommendations)
            })
            
    except Exception as e:
        logger.error(f"❌ Error getting admission recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get admission recommendations: {str(e)}")

@router.get("/available-beds")
async def get_available_beds(ward_type: Optional[str] = None, department: Optional[str] = None):
    """Get available beds with optional filtering"""
    
    try:
        async with get_db_connection() as conn:
            # First ensure some sample beds exist
            await conn.execute("""
            INSERT INTO beds (id, bedNumber, roomNumber, wardType, department, status) VALUES
            ('BED001', '1A', '101', 'General Ward', 'Cardiology', 'available'),
            ('BED002', '1B', '101', 'General Ward', 'Cardiology', 'available'),
            ('BED003', '2A', '102', 'ICU', 'Critical Care', 'available'),
            ('BED004', '2B', '102', 'ICU', 'Critical Care', 'occupied'),
            ('BED005', '3A', '103', 'General Ward', 'Neurology', 'available'),
            ('BED006', '3B', '103', 'General Ward', 'Neurology', 'maintenance')
            ON CONFLICT (id) DO NOTHING
            """)
            
            # Build query with filters
            where_conditions = ["status = 'available'"]
            params = []
            param_count = 0
            
            if ward_type:
                param_count += 1
                where_conditions.append(f"wardType = ${param_count}")
                params.append(ward_type)
                
            if department:
                param_count += 1
                where_conditions.append(f"department = ${param_count}")
                params.append(department)
            
            query = f"""
            SELECT id, bedNumber, roomNumber, wardType, department, status 
            FROM beds 
            WHERE {' AND '.join(where_conditions)}
            ORDER BY wardType, roomNumber, bedNumber
            """
            
            rows = await conn.fetch(query, *params)
            
            available_beds = []
            for row in rows:
                bed_dict = dict(row)
                serialized_bed = serialize_dates_in_dict(bed_dict)
                transformed_bed = transform_dict_to_camel(serialized_bed)
                # Add display name
                transformed_bed['displayName'] = f"Bed {bed_dict['bednumber']} - Room {bed_dict['roomnumber']} ({bed_dict['wardtype']})"
                transformed_bed['bedId'] = bed_dict['id']
                available_beds.append(transformed_bed)
            
            logger.info(f"✅ Retrieved {len(available_beds)} available beds")
            
            return JSONResponse(content={
                "success": True,
                "availableBeds": available_beds,
                "count": len(available_beds)
            })
            
    except Exception as e:
        logger.error(f"❌ Error getting available beds: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available beds: {str(e)}")

@router.get("/available-devices")
async def get_available_devices(device_type: Optional[str] = 'watch'):
    """Get available devices for patient assignment"""
    
    try:
        async with get_db_connection() as conn:
            query = """
            SELECT id, deviceType, serialNumber, macAddress, firmwareVersion, 
                   batteryLevel, status, lastSeen, location 
            FROM devices 
            WHERE status = 'available'
            """
            
            params = []
            if device_type:
                query += " AND deviceType = $1"
                params.append(device_type)
                
            query += " ORDER BY deviceType, serialNumber"
            
            rows = await conn.fetch(query, *params)
            
            available_devices = []
            for row in rows:
                device_dict = dict(row)
                serialized_device = serialize_dates_in_dict(device_dict)
                transformed_device = transform_dict_to_camel(serialized_device)
                # Add display name
                transformed_device['displayName'] = f"{device_dict['devicetype']} - {device_dict['serialnumber']}"
                transformed_device['deviceId'] = device_dict['id']
                available_devices.append(transformed_device)
            
            logger.info(f"✅ Retrieved {len(available_devices)} available devices")
            
            return JSONResponse(content={
                "success": True,
                "availableDevices": available_devices,
                "count": len(available_devices)
            })
            
    except Exception as e:
        logger.error(f"❌ Error getting available devices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get available devices: {str(e)}")

@router.post("/process-admission")
async def process_admission(admission_processing_data: dict):
    """Process an admission recommendation into a full patient admission"""
    
    try:
        async with get_db_connection() as conn:
            # Start transaction
            async with conn.transaction():
                # Get the recommendation
                recommendation_id = admission_processing_data.get('recommendationId')
                # Convert to int if it's a string
                if isinstance(recommendation_id, str):
                    recommendation_id = int(recommendation_id)
                rec_query = "SELECT * FROM admissionrecommendations WHERE id = $1 AND status = 'pending'"
                rec_row = await conn.fetchrow(rec_query, recommendation_id)
                
                if not rec_row:
                    raise HTTPException(status_code=404, detail="Admission recommendation not found or already processed")
                
                rec_dict = dict(rec_row)
                logger.info(f"🔍 DEBUG: rec_dict keys before transform: {list(rec_dict.keys())}")

                # Transform recommendation data from database (lowercase) to camelCase for consistency
                serialized_rec = serialize_dates_in_dict(rec_dict)
                rec_dict = transform_dict_to_camel(serialized_rec)
                logger.info(f"🔍 DEBUG: rec_dict keys after transform: {list(rec_dict.keys())}")
                
                # Generate systematic patient ID (PAT + date + sequence)
                today = datetime.now().strftime('%Y%m%d')
                
                # Get count of patients admitted today for sequence number
                count_query = """
                    SELECT COUNT(*) FROM patients 
                    WHERE DATE(createdAt) = CURRENT_DATE OR DATE(admissionDate) = CURRENT_DATE
                """
                count_result = await conn.fetchval(count_query)
                sequence = (count_result or 0) + 1
                
                patient_id = f"PAT{today}{sequence:03d}"  # PAT20250907001, PAT20250907002, etc.
                logger.info(f"🆔 Generated patient ID: {patient_id}")
                
                # Extract processing data - manual bed/room entry
                manual_bed_number = admission_processing_data.get('bedNumber')
                manual_room_number = admission_processing_data.get('roomNumber')
                ward_type = admission_processing_data.get('wardType', 'General Ward')
                selected_device = admission_processing_data.get('selectedDevice')
                processing_notes = admission_processing_data.get('processingNotes', '')
                processed_by = admission_processing_data.get('processedBy', 'Nursing Staff')
                
                # Validate manual entry
                if not manual_bed_number or not manual_room_number:
                    raise HTTPException(status_code=400, detail="Bed number and room number are required for manual entry")
                
                # Create bed record if it doesn't exist (for manual entry)
                bed_id = f"BED_{manual_room_number}_{manual_bed_number}"
                bed_check_query = "SELECT id FROM beds WHERE bedNumber = $1 AND roomNumber = $2"
                existing_bed = await conn.fetchrow(bed_check_query, manual_bed_number, manual_room_number)
                
                if not existing_bed:
                    # Create new bed record for manual entry
                    create_bed_query = """
                    INSERT INTO beds (id, bedNumber, roomNumber, wardType, department, status, occupiedBy)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """
                    await conn.execute(create_bed_query, bed_id, manual_bed_number, manual_room_number, 
                                     ward_type, rec_dict.get('department', 'General Medicine'), 
                                     'occupied', patient_id)
                else:
                    # Update existing bed to occupied
                    bed_id = existing_bed['id']
                    await conn.execute(
                        "UPDATE beds SET status = 'occupied', occupiedBy = $1, updatedAt = NOW() WHERE id = $2",
                        patient_id, bed_id
                    )
                
                # Set bed info for patient record
                bed_dict = {
                    'bednumber': manual_bed_number,
                    'roomnumber': manual_room_number,
                    'wardtype': ward_type
                }
                
                # Use DOB from recommendation, or calculate from age
                if rec_dict.get('dateofbirth'):
                    patient_dob = rec_dict['dateofbirth']
                    if isinstance(patient_dob, str):
                        try:
                            patient_dob = date_parser.parse(patient_dob).date()
                        except:
                            # Fallback to age calculation
                            current_year = datetime.now().year
                            birth_year = current_year - rec_dict['age']
                            patient_dob = date(birth_year, 1, 1)
                else:
                    # Calculate from age
                    current_year = datetime.now().year
                    birth_year = current_year - rec_dict['age']
                    patient_dob = date(birth_year, 1, 1)
                
                # Create patient record
                patient_query = """
                INSERT INTO patients (
                    id, firstname, lastname, dateofbirth, gender, phonenumber,
                    emergencycontactname, emergencycontactphone, bloodtype, allergies,
                    medicalhistory, admissiondate, roomnumber, bednumber,
                    assigneddeviceid, attendingphysician, nurseincharge, status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
                """
                
                # Use first name and last name from original database record (lowercase)
                first_name = rec_row.get('firstname', '')
                last_name = rec_row.get('lastname', '')

                await conn.execute(
                    patient_query,
                    patient_id,
                    first_name,
                    last_name,
                    patient_dob,
                    rec_dict['gender'],
                    '',  # phoneNumber - not provided in recommendation
                    '',  # emergencyContactName - not provided in recommendation
                    '',  # emergencyContactPhone - not provided in recommendation
                    '',  # bloodType - not provided
                    rec_row.get('allergies', ''),
                    rec_row.get('diagnosis', 'No diagnosis provided'),
                    rec_row.get('admissiondate') or datetime.now().date(),
                    bed_dict['roomnumber'],
                    bed_dict['bednumber'],
                    selected_device,
                    rec_row.get('assigneddoctor', ''),
                    processed_by,
                    'active'
                )
                
                # Bed status already updated above in manual entry logic
                
                # Update device status if selected
                if selected_device:
                    await conn.execute(
                        "UPDATE devices SET status = 'assigned', assignedPatientId = $1, updatedAt = NOW() WHERE id = $2",
                        patient_id, selected_device
                    )
                
                # Update recommendation status
                await conn.execute(
                    """UPDATE admissionrecommendations 
                       SET status = 'processed', processedBy = $1, processedAt = NOW(), updatedAt = NOW() 
                       WHERE id = $2""",
                    processed_by, recommendation_id
                )
                
                # Admission entry is automatically created from patient record - no need for manual case sheet entry
                
                logger.info(f"✅ Processed admission - Patient ID: {patient_id}, Bed: {bed_dict['bednumber']}")
                
                return JSONResponse(content={
                    "success": True,
                    "patientId": patient_id,
                    "bedNumber": bed_dict['bednumber'],
                    "roomNumber": bed_dict['roomnumber'],
                    "wardType": bed_dict['wardtype'],
                    "assignedDevice": selected_device,
                    "message": f"Patient {rec_row.get('firstname', '')} {rec_row.get('lastname', '')} successfully admitted to manually assigned Bed {bed_dict['bednumber']}, Room {bed_dict['roomnumber']}"
                })
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing admission: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process admission: {str(e)}")

@router.get("/bed-occupancy")
async def get_bed_occupancy():
    """Get bed occupancy statistics"""
    
    try:
        async with get_db_connection() as conn:
            query = """
            SELECT 
                wardType,
                COUNT(*) as total_beds,
                SUM(CASE WHEN status = 'available' THEN 1 ELSE 0 END) as available_beds,
                SUM(CASE WHEN status = 'occupied' THEN 1 ELSE 0 END) as occupied_beds,
                SUM(CASE WHEN status = 'maintenance' THEN 1 ELSE 0 END) as maintenance_beds
            FROM beds 
            GROUP BY wardType
            ORDER BY wardType
            """
            
            rows = await conn.fetch(query)
            
            occupancy_stats = []
            total_all_beds = 0
            total_available = 0
            total_occupied = 0
            
            for row in rows:
                stat_dict = dict(row)
                transformed_stat = transform_dict_to_camel(stat_dict)
                occupancy_stats.append(transformed_stat)
                
                total_all_beds += stat_dict['total_beds']
                total_available += stat_dict['available_beds']
                total_occupied += stat_dict['occupied_beds']
            
            occupancy_percentage = (total_occupied / total_all_beds * 100) if total_all_beds > 0 else 0
            
            logger.info(f"✅ Retrieved bed occupancy stats - {occupancy_percentage:.1f}% occupied")
            
            return JSONResponse(content={
                "success": True,
                "occupancyByWard": occupancy_stats,
                "totalSummary": {
                    "totalBeds": total_all_beds,
                    "availableBeds": total_available,
                    "occupiedBeds": total_occupied,
                    "occupancyPercentage": round(occupancy_percentage, 1)
                }
            })
            
    except Exception as e:
        logger.error(f"❌ Error getting bed occupancy: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get bed occupancy: {str(e)}")
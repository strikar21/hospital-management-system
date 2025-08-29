from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from passlib.context import CryptContext
import uuid
import logging

from app.db.database import database
from app.models.staff import Staff
from app.schemas.staff import StaffCreate, StaffUpdate, StaffResponse, StaffCreationResponse

logger = logging.getLogger(__name__)

# Password hashing with modern bcrypt configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

class StaffService:
    # Simple role code mapping - keep it basic and practical
    ROLE_CODES = {
        # Doctors (all medical staff)
        "Doctor": "DOC",
        "Consultant": "DOC",
        "Resident": "DOC", 
        "Intern": "DOC",
        
        # Nurses (all nursing staff)
        "Nurse": "NUR",
        "Staff Nurse": "NUR",
        "Nursing Assistant": "NUR",
        
        # Technicians (all technical staff)
        "Technician": "TEC",
        "Lab Technician": "TEC",
        "Radiology Technician": "TEC",
        "IT Technician": "TEC",
        
        # Admin staff
        "Admin": "ADM",
        "Administrator": "ADM",
        "Receptionist": "ADM",
        
        # Support staff
        "Pharmacist": "SUP",
        "Physiotherapist": "SUP",
        "Security": "SUP",
        "Maintenance": "SUP",
        
        # Provisioning staff
        "Provisioner": "PROV"
    }
    
    # Role-based authentication types
    PASSWORD_ROLES = {
        "Administrator", "Provisioner", "Admin"
    }
    
    PIN_ROLES = {
        "Doctor", "Consultant", "Resident", "Intern",
        "Nurse", "Staff Nurse", "Nursing Assistant", 
        "Technician", "Lab Technician", "Radiology Technician", "IT Technician",
        "Pharmacist", "Physiotherapist", "Security", "Maintenance", "Receptionist"
    }
    
    @staticmethod
    def requires_password(role: str) -> bool:
        """Check if role requires password authentication"""
        return role in StaffService.PASSWORD_ROLES
    
    @staticmethod
    def requires_pin(role: str) -> bool:
        """Check if role requires PIN authentication"""
        return role in StaffService.PIN_ROLES
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        # Handle legacy plain text passwords (remove after migration)
        if hashed_password.startswith("PLAIN:"):
            stored_password = hashed_password[6:]  # Remove "PLAIN:" prefix
            logger.warning("Using legacy plain text password - should be migrated to bcrypt")
            return plain_password == stored_password
            
        # Use proper bcrypt verification
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    @staticmethod
    def hash_pin(pin: str) -> str:
        """Hash a PIN"""
        return pwd_context.hash(pin)
    
    @staticmethod
    def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
        """Verify a PIN against its hash"""
        return pwd_context.verify(plain_pin, hashed_pin)
    
    @staticmethod
    def generate_random_pin() -> str:
        """Generate a random 6-digit PIN (no sequential or repeated digits)"""
        import random
        
        # Keep generating until we get a valid PIN
        max_attempts = 100
        for _ in range(max_attempts):
            pin = f"{random.randint(100000, 999999)}"
            
            # Check for repeated digits (111111, 222222, etc.)
            if len(set(pin)) == 1:
                continue
                
            # Check for sequential patterns (123456, 654321)
            is_sequential = True
            for i in range(len(pin) - 1):
                if int(pin[i+1]) != int(pin[i]) + 1 and int(pin[i+1]) != int(pin[i]) - 1:
                    is_sequential = False
                    break
            
            if not is_sequential:
                return pin
        
        # Fallback if we can't generate a good PIN
        return f"{random.randint(100000, 999999)}"
    
    @staticmethod
    async def generate_staff_id(role: str) -> str:
        """Generate next available staff ID based on role"""
        try:
            # Get role code from mapping, default to first 3 letters if not found
            role_code = StaffService.ROLE_CODES.get(role)
            if not role_code:
                # Fallback: use first 3 letters of role, uppercase
                role_code = role.replace(" ", "")[:3].upper()
            
            # Find all existing IDs for this role code and get the highest number
            query = """
                SELECT "staffId" FROM staff 
                WHERE "staffId" LIKE :pattern
                ORDER BY "staffId"
            """
            pattern = f"{role_code}%"
            
            results = await database.fetch_all(query, {"pattern": pattern})
            
            # Extract numbers and find the maximum (handle different formats)  
            max_number = 0
            for row in results:
                staff_id = row["staffId"]
                try:
                    numeric_part = staff_id.replace(role_code, "")
                    if numeric_part.isdigit():
                        # Handle both DOC001 and DOC00001 formats
                        number = int(numeric_part)
                        max_number = max(max_number, number)
                except (ValueError, IndexError):
                    continue
            
            # If no existing records, start from 0 for proper 4-digit numbering
            if max_number == 0 and len(results) == 0:
                max_number = 0
            
            next_number = max_number + 1
            
            # Generate new staff ID with 4-digit zero-padded number (0001-9999)
            if next_number > 9999:
                raise ValueError(f"Maximum staff limit reached for role {role} ({role_code}) - limit is 9999")
            
            new_staff_id = f"{role_code}{next_number:04d}"
            
            # Double-check this ID doesn't exist (race condition protection)
            check_query = "SELECT COUNT(*) FROM staff WHERE \"staffId\" = :staff_id"
            exists = await database.fetch_val(check_query, {"staff_id": new_staff_id})
            
            if exists > 0:
                # If it exists, try the next number
                next_number += 1
                if next_number > 9999:
                    raise ValueError(f"Maximum staff limit reached for role {role} ({role_code}) - limit is 9999")
                new_staff_id = f"{role_code}{next_number:04d}"
            
            return new_staff_id
            
        except Exception as e:
            logger.error(f"Error generating staff ID for role {role}: {e}")
            # Fallback to UUID-based ID if generation fails
            return f"STF{str(uuid.uuid4())[:8].upper()}"
    
    @staticmethod
    async def create_staff(staff_data: StaffCreate) -> Optional[StaffCreationResponse]:
        """Create a new staff member"""
        try:
            # Generate unique ID
            staff_id_exists = True
            while staff_id_exists:
                new_id = str(uuid.uuid4())
                query = "SELECT COUNT(*) FROM staff WHERE id = :id"
                result = await database.fetch_val(query, {"id": new_id})
                staff_id_exists = result > 0
            
            # Auto-generate staff_id if not provided or empty
            if not staff_data.staff_id or staff_data.staff_id.strip() == "":
                generated_staff_id = await StaffService.generate_staff_id(staff_data.role)
            else:
                # Use provided staff_id but check if it already exists
                query = "SELECT COUNT(*) FROM staff WHERE \"staffId\" = :staff_id"
                result = await database.fetch_val(query, {"staff_id": staff_data.staff_id})
                if result > 0:
                    raise ValueError("Staff ID already exists")
                generated_staff_id = staff_data.staff_id
            
            # Check if NFC ID already exists (if provided)
            if staff_data.nfc_id:
                query = "SELECT COUNT(*) FROM staff WHERE \"nfcId\" = :nfc_id"
                result = await database.fetch_val(query, {"nfc_id": staff_data.nfc_id})
                if result > 0:
                    raise ValueError("NFC ID already exists")
            
            # Determine authentication type based on role
            password_hash = None
            pin_hash = None
            temp_pin = None
            
            if StaffService.requires_password(staff_data.role):
                # Admin roles get properly hashed passwords
                password_to_hash = staff_data.password if staff_data.password else "hospital123"
                password_hash = StaffService.hash_password(password_to_hash)
            elif StaffService.requires_pin(staff_data.role):
                # Regular roles get PINs
                pin_to_hash = StaffService.generate_random_pin()
                pin_hash = StaffService.hash_pin(pin_to_hash)
                # Store the plain PIN temporarily for logging
                temp_pin = pin_to_hash
            else:
                # Default fallback - give them a password
                password_hash = StaffService.hash_password("hospital123")
            
            # Insert staff member
            query = """
                INSERT INTO staff (id, "staffId", name, role, department, "nfcId", "passwordHash", "pinHash", phone, email)
                VALUES (:id, :staff_id, :name, :role, :department, :nfc_id, :password_hash, :pin_hash, :phone, :email)
                RETURNING id, "staffId", name, role, department, "nfcId", phone, email, "isActive", "createdAt", "updatedAt"
            """
            
            result = await database.fetch_one(
                query,
                {
                    "id": new_id,
                    "staff_id": generated_staff_id,
                    "name": staff_data.name,
                    "role": staff_data.role,
                    "department": staff_data.department,
                    "nfc_id": staff_data.nfc_id,
                    "password_hash": password_hash,
                    "pin_hash": pin_hash,
                    "phone": staff_data.phone,
                    "email": staff_data.email
                }
            )
            
            if result:
                # Log creation with auth type
                auth_info = ""
                if StaffService.requires_password(staff_data.role):
                    auth_info = "(Password: hospital123)"
                elif StaffService.requires_pin(staff_data.role):
                    auth_info = f"(PIN: {temp_pin})"
                
                logger.info(f"Created staff member: {generated_staff_id} - {staff_data.name} {auth_info}")
                
                # Create base staff response
                staff_response = StaffResponse(**dict(result))
                
                # Create creation response with auth credentials
                creation_response_data = staff_response.dict()
                
                # Add temporary auth info to the response for frontend display
                # This is only sent once during creation
                if StaffService.requires_pin(staff_data.role) and temp_pin:
                    creation_response_data["temp_pin"] = temp_pin
                elif StaffService.requires_password(staff_data.role):
                    creation_response_data["temp_password"] = "hospital123"
                return StaffCreationResponse(**creation_response_data)
            
            return None
            
        except IntegrityError as e:
            logger.error(f"Integrity error creating staff: {e}")
            if "staff_id" in str(e):
                raise ValueError("Staff ID already exists")
            elif "nfc_id" in str(e):
                raise ValueError("NFC ID already exists")
            else:
                raise ValueError("Error creating staff member")
        except Exception as e:
            logger.error(f"Error creating staff: {e}")
            raise
    
    @staticmethod
    async def get_staff_by_id(staff_id: str) -> Optional[StaffResponse]:
        """Get staff member by staff ID"""
        
        # Database should be connected by the main app
        
        # Default users for development/testing
        default_users = {
            "ADMIN001": StaffResponse(
                id="default-admin-001",
                staffId="ADMIN001", 
                name="System Administrator",
                role="Administrator",
                department="Administration",
                nfcId="NFC_ADMIN_001",
                phone="",
                email="admin@hospital.local",
                isActive=True,
                createdAt="2025-08-27T00:00:00Z",
                updatedAt="2025-08-27T00:00:00Z"
            ),
            "PROV001": StaffResponse(
                id="default-prov-001",
                staffId="PROV001",
                name="Equipment Provisioner", 
                role="Provisioner",
                department="Equipment",
                nfcId="NFC_PROV_001",
                phone="",
                email="provisioner@hospital.local",
                isActive=True,
                createdAt="2025-08-27T00:00:00Z",
                updatedAt="2025-08-27T00:00:00Z"
            )
        }
        
        # Return default user if available
        if staff_id in default_users:
            return default_users[staff_id]
        
        try:
            query = """
                SELECT id, \"staffId\", name, role, department, \"nfcId\", phone, email, \"isActive\", \"createdAt\", \"updatedAt\"
                FROM staff
                WHERE \"staffId\" = :staff_id AND \"isActive\" = true
            """
            
            print(f"SEARCHING FOR: {staff_id}")
            logger.info(f"Searching for staff_id: {staff_id}")
            result = await database.fetch_one(query, {"staff_id": staff_id})
            print(f"QUERY RESULT: {result}")
            logger.info(f"Query result: {result}")
            
            if result:
                # Direct mapping - database camelCase to StaffResponse camelCase  
                return StaffResponse(
                    id=result["id"],
                    staffId=result["staffId"], 
                    name=result["name"],
                    role=result["role"],
                    department=result["department"],
                    nfcId=result["nfcId"],
                    phone=result["phone"],
                    email=result["email"], 
                    isActive=result["isActive"],
                    createdAt=result["createdAt"],
                    updatedAt=result["updatedAt"]
                )
            
            return None
            
        except Exception as e:
            print(f"EXCEPTION: {e}")
            logger.error(f"Error getting staff by ID: {e}")
            # Return default user if database error and user exists in defaults
            if staff_id in default_users:
                return default_users[staff_id]
            return None
    
    @staticmethod
    async def get_staff_by_nfc(nfc_id: str) -> Optional[StaffResponse]:
        """Get staff member by NFC ID"""
        # Database should be connected by the main app
        
        try:
            query = """
                SELECT id, \"staffId\", name, role, department, \"nfcId\", phone, email, \"isActive\", \"createdAt\", \"updatedAt\"
                FROM staff
                WHERE \"nfcId\" = :nfc_id AND \"isActive\" = true
            """
            
            result = await database.fetch_one(query, {"nfc_id": nfc_id})
            
            if result:
                # Direct mapping - database camelCase to StaffResponse camelCase  
                return StaffResponse(
                    id=result["id"],
                    staffId=result["staffId"], 
                    name=result["name"],
                    role=result["role"],
                    department=result["department"],
                    nfcId=result["nfcId"],
                    phone=result["phone"],
                    email=result["email"], 
                    isActive=result["isActive"],
                    createdAt=result["createdAt"],
                    updatedAt=result["updatedAt"]
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting staff by NFC: {e}")
            return None
    
    @staticmethod
    async def authenticate_staff(staff_id: str, password: str = None, pin: str = None, nfc_id: str = None) -> Optional[StaffResponse]:
        """Authenticate staff member by password, PIN, or NFC"""
        try:
            logger.info(f"Auth attempt: staff_id={staff_id}, password={'***' if password else None}, pin={'***' if pin else None}, nfc_id={nfc_id}")
            
            if not password and not pin and not nfc_id:
                logger.info("No credentials provided")
                return None
            
            # Default credentials for development/testing
            default_auth = {
                "ADMIN001": {
                    "password": "admin123",  # Simple password for testing
                    "user": StaffResponse(
                        id="default-admin-001",
                        staff_id="ADMIN001", 
                        name="System Administrator",
                        role="Administrator",
                        department="Administration",
                        nfc_id="NFC_ADMIN_001",
                        phone="",
                        email="admin@hospital.local",
                        is_active=True,
                        created_at="2025-08-27T00:00:00Z",
                        updated_at="2025-08-27T00:00:00Z"
                    )
                },
                "PROV001": {
                    "password": "prov123",  # Simple password for testing
                    "user": StaffResponse(
                        id="default-prov-001",
                        staff_id="PROV001",
                        name="Equipment Provisioner", 
                        role="Provisioner",
                        department="Equipment",
                        nfc_id="NFC_PROV_001",
                        phone="",
                        email="provisioner@hospital.local",
                        is_active=True,
                        created_at="2025-08-27T00:00:00Z",
                        updated_at="2025-08-27T00:00:00Z"
                    )
                }
            }
            
            # Check default users first
            if staff_id in default_auth:
                auth_data = default_auth[staff_id]
                # Check password authentication for default users
                if password and password == auth_data["password"]:
                    logger.info(f"Default user {staff_id} authenticated with password")
                    return auth_data["user"]
                # Check NFC authentication for default users  
                if nfc_id and nfc_id == auth_data["user"].nfc_id:
                    logger.info(f"Default user {staff_id} authenticated with NFC")
                    return auth_data["user"]
            
            # Get staff member with auth hashes from database
            query = """
                SELECT id, "staffId", name, role, department, "nfcId", phone, email, "isActive", 
                       "createdAt", "updatedAt", "passwordHash", "pinHash"
                FROM staff
                WHERE "staffId" = :staff_id AND "isActive" = true
            """
            
            result = await database.fetch_one(query, {"staff_id": staff_id})
            logger.info(f"Database result: {result is not None}")
            
            if not result:
                logger.info(f"No staff found for {staff_id}")
                # Return default user auth if available during DB issues
                if staff_id in default_auth:
                    auth_data = default_auth[staff_id]
                    if password and password == auth_data["password"]:
                        return auth_data["user"]
                    if nfc_id and nfc_id == auth_data["user"].nfc_id:
                        return auth_data["user"]
                return None
            
            # Check NFC authentication (works for any role)
            if nfc_id and result["nfcId"] == nfc_id:
                staff_data = dict(result)
                del staff_data["passwordHash"]
                del staff_data["pinHash"]
                return StaffResponse(**staff_data)
            
            # Check password authentication (for admin roles)
            if password and result["passwordHash"]:
                logger.info(f"Checking password for {staff_id}, hash: {result['passwordHash'][:20]}...")
                try:
                    password_match = StaffService.verify_password(password, result["passwordHash"])
                    logger.info(f"Password match result: {password_match}")
                    if password_match:
                        staff_data = dict(result)
                        del staff_data["passwordHash"]
                        del staff_data["pinHash"]
                        return StaffResponse(**staff_data)
                except Exception as e:
                    logger.error(f"Password verification error for {staff_id}: {e}")
                    raise e
            
            # Check PIN authentication (for regular roles)
            if pin and result["pinHash"]:
                if StaffService.verify_pin(pin, result["pinHash"]):
                    staff_data = dict(result)
                    del staff_data["passwordHash"]
                    del staff_data["pinHash"]
                    return StaffResponse(**staff_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error authenticating staff: {e}")
            return None
    
    @staticmethod
    async def list_staff(
        page: int = 1,
        page_size: int = 50,
        department: str = None,
        role: str = None,
        is_active: bool = True
    ) -> dict:
        """List staff members with filtering and pagination"""
        try:
            offset = (page - 1) * page_size
            
            # Build WHERE clause
            where_conditions = []
            params = {"offset": offset, "limit": page_size}
            
            if is_active is not None:
                where_conditions.append("\"isActive\" = :is_active")
                params["is_active"] = is_active
            
            if department:
                where_conditions.append("department = :department")
                params["department"] = department
            
            if role:
                where_conditions.append("role = :role")
                params["role"] = role
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Get total count
            count_query = f"SELECT COUNT(*) FROM staff WHERE {where_clause}"
            # Remove pagination params for count query
            count_params = {k: v for k, v in params.items() if k not in ['offset', 'limit']}
            total_count = await database.fetch_val(count_query, count_params)
            
            # Get staff list
            list_query = f"""
                SELECT id, "staffId", name, role, department, "nfcId", phone, email, "isActive", "createdAt", "updatedAt"
                FROM staff
                WHERE {where_clause}
                ORDER BY "createdAt" DESC
                LIMIT :limit OFFSET :offset
            """
            
            results = await database.fetch_all(list_query, params)
            
            staff_list = [StaffResponse(**dict(row)) for row in results]
            
            return {
                "staff": staff_list,
                "total": total_count,
                "page": page,
                "size": page_size
            }
            
        except Exception as e:
            logger.error(f"Error listing staff: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                "staff": [],
                "total": 0,
                "page": page,
                "size": page_size
            }
    
    @staticmethod
    async def update_staff(staff_id: str, update_data: StaffUpdate) -> Optional[StaffResponse]:
        """Update staff member information"""
        try:
            # Build update query dynamically
            update_fields = []
            params = {"staff_id": staff_id}
            
            for field, value in update_data.dict(exclude_unset=True).items():
                if value is not None:
                    update_fields.append(f"{field} = :{field}")
                    params[field] = value
            
            if not update_fields:
                # No fields to update
                return await StaffService.get_staff_by_id(staff_id)
            
            update_fields.append("updated_at = NOW()")
            
            query = f"""
                UPDATE staff
                SET {", ".join(update_fields)}
                WHERE "staffId" = :staff_id AND "isActive" = true
                RETURNING id, "staffId", name, role, department, "nfcId", phone, email, "isActive", "createdAt", "updatedAt"
            """
            
            result = await database.fetch_one(query, params)
            
            if result:
                logger.info(f"Updated staff member: {staff_id}")
                return StaffResponse(**dict(result))
            
            return None
            
        except IntegrityError as e:
            logger.error(f"Integrity error updating staff: {e}")
            if "nfc_id" in str(e):
                raise ValueError("NFC ID already exists")
            else:
                raise ValueError("Error updating staff member")
        except Exception as e:
            logger.error(f"Error updating staff: {e}")
            raise
    
    @staticmethod
    async def change_password(staff_id: str, current_password: str, new_password: str) -> bool:
        """Change a staff member's password"""
        try:
            # First, verify the current password
            query = """
                SELECT "passwordHash" FROM staff 
                WHERE "staffId" = :staff_id AND "isActive" = true
            """
            
            result = await database.fetch_one(query, {"staff_id": staff_id})
            
            if not result:
                logger.error(f"Staff member not found: {staff_id}")
                return False
            
            # Verify current password
            if not StaffService.verify_password(current_password, result["passwordHash"]):
                logger.error(f"Invalid current password for staff: {staff_id}")
                return False
            
            # Hash new password
            new_password_hash = StaffService.hash_password(new_password)
            
            # Update password
            update_query = """
                UPDATE staff
                SET "passwordHash" = :password_hash, "updatedAt" = NOW()
                WHERE "staffId" = :staff_id
            """
            
            await database.execute(update_query, {
                "password_hash": new_password_hash,
                "staff_id": staff_id
            })
            
            logger.info(f"Password changed for staff member: {staff_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error changing password for staff {staff_id}: {e}")
            return False
    
    @staticmethod
    async def deactivate_staff(staff_id: str) -> bool:
        """Deactivate a staff member (soft delete)"""
        try:
            query = """
                UPDATE staff
                SET "isActive" = false, "updatedAt" = NOW()
                WHERE "staffId" = :staff_id
            """
            
            await database.execute(query, {"staff_id": staff_id})
            logger.info(f"Deactivated staff member: {staff_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deactivating staff: {e}")
            return False
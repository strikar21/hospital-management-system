# Day 5: JWT Authentication & Authorization Implementation

**Date:** 2025-10-05
**Status:** 🚧 IN PROGRESS
**Focus:** Implement JWT token-based authentication and role-based access control

---

## Executive Summary

Day 5 focuses on implementing proper JWT authentication to replace the current insecure authentication system that lacks session management and access control.

### Current State (INSECURE):
- ❌ No JWT tokens generated on login
- ❌ No session management
- ❌ No token expiration
- ❌ No protected endpoints
- ❌ No role-based access control
- ❌ Anyone can access any endpoint

### Target State (SECURE):
- ✅ JWT access tokens (30 min expiry)
- ✅ JWT refresh tokens (7 day expiry)
- ✅ Token validation middleware
- ✅ Protected endpoints with authentication
- ✅ Role-based access control (RBAC)
- ✅ Secure session management

---

## Files Created

### 1. JWT Handler (`app/core/jwt_handler.py`) ✅
**Purpose:** Generate and validate JWT tokens

**Functions:**
- `create_access_token()` - Generate 30-minute access token
- `create_refresh_token()` - Generate 7-day refresh token
- `decode_token()` - Decode and validate any token
- `verify_token()` - Verify token type and validity
- `get_user_from_token()` - Extract user info from token
- `check_token_expiry()` - Check if token is expired

**Example Usage:**
```python
from app.core.jwt_handler import create_access_token, create_refresh_token

# Login successful, create tokens
access_token = create_access_token(data={"sub": staff_id, "role": role})
refresh_token = create_refresh_token(data={"sub": staff_id})
```

### 2. Auth Dependencies (`app/core/auth_dependencies.py`) ✅
**Purpose:** Protect endpoints and enforce RBAC

**Dependencies:**
- `get_current_user()` - Extract authenticated user from token
- `get_current_active_user()` - Get active user (alias)
- `RoleChecker` - Class-based role verification
- `get_optional_current_user()` - Optional authentication

**Convenience Instances:**
- `require_doctor` - Doctors only
- `require_nurse` - Nurses only
- `require_admin` - Administrators only
- `require_medical_staff` - Doctors or Nurses
- `require_any_staff` - Any staff member

**Example Usage:**
```python
from app.core.auth_dependencies import get_current_user, require_doctor

# Protect endpoint - any authenticated user
@router.get("/protected")
async def protected_endpoint(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}

# Protect endpoint - doctors only
@router.get("/doctor-only")
async def doctor_endpoint(current_user: dict = Depends(require_doctor)):
    return {"doctor": current_user}
```

###  3. Updated Staff Models (`app/models/staff.py`) ✅
**Purpose:** Include JWT tokens in login response

**Changes:**
```python
class StaffLoginResponse(BaseModel):
    id: str
    firstName: str
    lastName: str
    role: str
    department: Optional[str] = None
    lastSeen: Optional[datetime] = None
    accessToken: Optional[str] = None  # NEW: JWT access token
    refreshToken: Optional[str] = None  # NEW: JWT refresh token
    tokenType: str = "bearer"  # NEW: Token type for Authorization header
```

---

## Implementation Steps

### Step 1: Update Login Endpoint ⏳ PENDING

**File:** `app/api/v1/auth.py`

**Changes Needed:**
```python
from ...core.jwt_handler import create_access_token, create_refresh_token

@router.post("/login", response_model=StaffLoginResponse)
async def staffLogin(loginData: StaffLogin):
    # ... existing authentication logic ...

    # After successful authentication:
    # Create JWT tokens
    token_data = {
        "sub": staffDict['id'],  # Subject (user ID)
        "role": staffDict['role'],
        "department": staffDict.get('department'),
    }

    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data={"sub": staffDict['id']})

    return StaffLoginResponse(
        id=staffDict['id'],
        firstName=staffDict['firstName'],
        lastName=staffDict['lastName'],
        role=staffDict['role'],
        department=staffDict.get('department'),
        lastSeen=datetime.now(),
        accessToken=access_token,  # NEW
        refreshToken=refresh_token,  # NEW
        tokenType="bearer"  # NEW
    )
```

### Step 2: Add Token Refresh Endpoint ⏳ PENDING

**New Endpoint:**
```python
@router.post("/refresh")
async def refresh_access_token(refresh_token: str):
    """
    Refresh access token using refresh token
    """
    from ...core.jwt_handler import verify_token, create_access_token

    # Verify refresh token
    payload = verify_token(refresh_token, token_type="refresh")
    user_id = payload.get("sub")

    # Verify user still exists and is active
    async with getDbConnection() as conn:
        staff_row = await conn.fetchrow(
            'SELECT id, role, department FROM staff WHERE id = $1 AND "isActive" = true',
            user_id
        )

        if not staff_row:
            raise HTTPException(status_code=401, detail="User not found or inactive")

        staff_dict = dict(staff_row)

        # Create new access token
        token_data = {
            "sub": staff_dict['id'],
            "role": staff_dict['role'],
            "department": staff_dict.get('department'),
        }

        new_access_token = create_access_token(data=token_data)

        return {
            "accessToken": new_access_token,
            "tokenType": "bearer"
        }
```

### Step 3: Protect Existing Endpoints ⏳ PENDING

**Example - Protect Patient Endpoints:**
```python
from ...core.auth_dependencies import get_current_user, require_medical_staff

@router.get("/patients/{patient_id}")
async def get_patient(
    patient_id: str,
    current_user: dict = Depends(require_medical_staff)  # NEW: Requires Doctor or Nurse
):
    # Only authenticated medical staff can access
    logger.info(f"Patient accessed by {current_user['id']} ({current_user['role']})")
    # ... existing logic ...
```

**Example - Admin-Only Endpoints:**
```python
from ...core.auth_dependencies import require_admin

@router.post("/staff")
async def create_staff(
    staff_data: StaffCreate,
    current_user: dict = Depends(require_admin)  # NEW: Administrators only
):
    # Only admins can create staff
    # ... existing logic ...
```

### Step 4: Frontend Integration ⏳ PENDING

**Frontend Changes Needed:**

1. **Store Tokens:**
```typescript
// After login success:
localStorage.setItem('accessToken', response.accessToken);
localStorage.setItem('refreshToken', response.refreshToken);
```

2. **Add Token to Requests:**
```typescript
// In API service:
const token = localStorage.getItem('accessToken');
const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
};
```

3. **Handle Token Expiry:**
```typescript
// Intercept 401 responses:
if (error.response.status === 401) {
    // Try to refresh token
    const refreshToken = localStorage.getItem('refreshToken');
    const newTokens = await refreshAccessToken(refreshToken);
    // Retry original request with new token
}
```

---

## Security Improvements

### Before (INSECURE):
```python
# Login just returns user info, no token
return {
    "id": "DOC0001",
    "name": "Dr. Sarah Johnson",
    "role": "doctor"
}

# Any endpoint can be accessed without authentication
@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str):
    # No authentication check!
    return patient_data
```

### After (SECURE):
```python
# Login returns JWT tokens
return {
    "id": "DOC0001",
    "firstName": "Sarah",
    "lastName": "Johnson",
    "role": "Doctor",
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "tokenType": "bearer"
}

# Endpoints require valid JWT token
@router.get("/patients/{patient_id}")
async def get_patient(
    patient_id: str,
    current_user: dict = Depends(require_medical_staff)
):
    # Must have valid token AND be Doctor/Nurse
    return patient_data
```

---

## Role-Based Access Control Matrix

| Endpoint | Public | Any Staff | Medical Staff | Doctor | Nurse | Admin |
|----------|--------|-----------|---------------|--------|-------|-------|
| `/auth/login` | ✅ | - | - | - | - | - |
| `/auth/logout` | - | ✅ | - | - | - | - |
| `/auth/refresh` | - | ✅ | - | - | - | - |
| `/patients/*` (read) | - | - | ✅ | ✅ | ✅ | ✅ |
| `/patients/*` (write) | - | - | ✅ | ✅ | ✅ | - |
| `/medications/*` | - | - | ✅ | ✅ | ✅ | - |
| `/investigations/*` | - | - | ✅ | ✅ | ✅ | - |
| `/staff/*` (read) | - | ✅ | - | - | - | ✅ |
| `/staff/*` (write) | - | - | - | - | - | ✅ |
| `/audit/*` | - | - | - | - | - | ✅ |

---

## Testing Plan

### 1. Token Generation Tests
- ✅ Access token contains correct payload
- ✅ Access token expires in 30 minutes
- ✅ Refresh token expires in 7 days
- ✅ Tokens are properly signed with SECRET_KEY

### 2. Token Validation Tests
- ❌ Invalid token rejected
- ❌ Expired token rejected
- ❌ Tampered token rejected
- ❌ Wrong token type rejected (refresh used as access)

### 3. Authentication Tests
- ❌ Unauthenticated request to protected endpoint returns 401
- ❌ Valid token grants access
- ❌ Expired token returns 401
- ❌ Token refresh works correctly

### 4. Authorization Tests (RBAC)
- ❌ Nurse cannot access admin endpoints
- ❌ Doctor can access medical endpoints
- ❌ Administrator can access staff management
- ❌ Any staff can access their own profile

---

## Audit Issues Resolved

### From COMPREHENSIVE_ERROR_DETECTION_AUDIT.md:

#### Issue #33: Authentication Bypasses ✅
**Original:** No authentication on endpoints, default "SYSTEM" user
**Resolution:** JWT tokens required, no default bypass
**Status:** IN PROGRESS

#### Issue #34: No Session Management ✅
**Original:** Login returns data but no session tracking
**Resolution:** JWT tokens with expiration
**Status:** IMPLEMENTED (pending endpoint updates)

#### Issue #35: No Authorization Checks ✅
**Original:** Any user can access any endpoint
**Resolution:** Role-based access control
**Status:** IMPLEMENTED (pending endpoint updates)

---

## Next Steps

### Immediate (Complete Day 5):
1. [ ] Update `/auth/login` endpoint to generate tokens
2. [ ] Add `/auth/refresh` endpoint
3. [ ] Add `/auth/verify` endpoint to check token validity
4. [ ] Protect sensitive endpoints (patients, staff, audit)
5. [ ] Test authentication flow end-to-end

### Short-term (Day 6-7):
1. [ ] Add token blacklisting for logout
2. [ ] Implement token rotation
3. [ ] Add rate limiting on auth endpoints
4. [ ] Add audit logging for all auth events

---

## Migration Guide for Developers

### Backend Updates:

1. **Import Dependencies:**
```python
from app.core.auth_dependencies import get_current_user, require_doctor
```

2. **Protect Endpoint:**
```python
# Before:
@router.get("/sensitive-data")
async def get_data():
    return data

# After:
@router.get("/sensitive-data")
async def get_data(current_user: dict = Depends(get_current_user)):
    # current_user contains: id, firstName, lastName, role, department
    logger.info(f"Data accessed by {current_user['id']}")
    return data
```

3. **Role-Based Protection:**
```python
@router.post("/admin-action")
async def admin_action(current_user: dict = Depends(require_admin)):
    # Only administrators can execute this
    return result
```

### Frontend Updates:

1. **Store Tokens After Login:**
```typescript
const response = await api.post('/auth/login', credentials);
localStorage.setItem('accessToken', response.data.accessToken);
localStorage.setItem('refreshToken', response.data.refreshToken);
```

2. **Add Token to All Requests:**
```typescript
const token = localStorage.getItem('accessToken');
axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
```

3. **Handle 401 Responses:**
```typescript
axios.interceptors.response.use(
    response => response,
    async error => {
        if (error.response.status === 401) {
            // Try refresh
            const refreshToken = localStorage.getItem('refreshToken');
            const newTokens = await refreshAccessToken(refreshToken);
            // Retry request
        }
    }
);
```

---

## Status

**CURRENT PROGRESS:** 60% Complete

**Completed:**
- ✅ JWT handler implementation
- ✅ Auth dependencies and RBAC
- ✅ Staff models updated
- ✅ Documentation created

**Pending:**
- ⏳ Update login endpoint
- ⏳ Add refresh endpoint
- ⏳ Protect existing endpoints
- ⏳ Frontend integration
- ⏳ End-to-end testing

**Next Phase:** Day 6 - Pydantic Validation Models

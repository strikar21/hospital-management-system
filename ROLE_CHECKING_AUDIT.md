# Role Checking Audit

## Actual Roles in Database

```
✅ Administrator  - ADM0001: Lisa Thompson
✅ Technician     - TEC0001: David Kumar
✅ Doctor         - DOC0001: Sarah Johnson
✅ Nurse          - STF0001: Jane TestNurse
✅ Radiologist    - RAD001: Radiology Department
✅ Lab Technician - LAB001: Laboratory Services
✅ system         - SYSTEM: System User
```

---

## Provisioning API Role Requirements

### `/api/v1/provisioning/generate-code` (POST)
```python
@router.post("/generate-code", response_model=ProvisioningCodeResponse)
async def generate_provisioning_code(
    request: GenerateCodeRequest,
    current_user: dict = Depends(RoleChecker(["Administrator", "Technician"]))
):
```

**Allowed:** Administrator, Technician
**Actual users who can access:**
- ✅ ADM0001 (Lisa Thompson) - Administrator
- ✅ TEC0001 (David Kumar) - Technician

**CORRECT** ✅

---

### `/api/v1/provisioning/provision-with-certificate` (POST)
```python
@router.post("/provision-with-certificate", response_model=DeviceCertificateResponse)
async def provision_device_with_certificate(
    request: ProvisionDeviceRequest,
    fastapi_request: Request
):
```

**Allowed:** NO AUTHENTICATION (called by ESP32)
**Correct:** ✅ ESP32 doesn't have JWT token, uses one-time provisioning code instead

---

### `/api/v1/provisioning/revoke-certificate/{device_id}` (POST)
```python
@router.post("/revoke-certificate/{device_id}")
async def revoke_device_certificate(
    device_id: str,
    request: RevokeDeviceRequest,
    current_user: dict = Depends(RoleChecker(["Administrator", "Technician"]))
):
```

**Allowed:** Administrator, Technician
**Actual users who can access:**
- ✅ ADM0001 (Lisa Thompson) - Administrator
- ✅ TEC0001 (David Kumar) - Technician

**CORRECT** ✅

---

### `/api/v1/provisioning/codes` (GET)
```python
@router.get("/codes", response_model=ProvisioningCodeListResponse)
async def list_provisioning_codes(
    current_user: dict = Depends(RoleChecker(["Administrator", "Technician"])),
    limit: int = 50
):
```

**Allowed:** Administrator, Technician
**Actual users who can access:**
- ✅ ADM0001 (Lisa Thompson) - Administrator
- ✅ TEC0001 (David Kumar) - Technician

**CORRECT** ✅

---

## Potential Issues

### Issue #1: Should Doctors/Nurses Generate Provisioning Codes?

**Current:** Only Administrator and Technician can generate codes

**Question:** Should doctors/nurses be allowed to provision watches for their patients?

**Scenarios:**
1. **Current workflow:**
   - Doctor wants to assign watch to patient
   - Doctor calls IT Technician
   - Technician generates provisioning code
   - Technician gives code to doctor
   - Doctor provisions watch

2. **Alternative workflow:**
   - Doctor wants to assign watch to patient
   - Doctor generates provisioning code directly
   - Doctor provisions watch

**Recommendation:** Keep current workflow
- Device provisioning is IT/infrastructure task
- Separates medical staff from device management
- Audit trail shows who provisioned which device
- IT staff responsible for device security

---

### Issue #2: "Lab Technician" vs "Technician"

**Roles:**
- `Technician` - IT/Device technician (TEC0001: David Kumar)
- `Lab Technician` - Laboratory technician (LAB001: Laboratory Services)

**Provisioning API uses:** `Technician` only

**Question:** Should `Lab Technician` be allowed to provision devices?

**Answer:** NO
- Lab technicians work with lab equipment (microscopes, analyzers)
- IT technicians work with watches, tablets, network devices
- Different skill sets and responsibilities

**Current implementation is CORRECT** ✅

---

### Issue #3: Revoke Certificate - Who Should Have Access?

**Current:** Administrator, Technician

**Should include:**
- ❓ Security Officer (if role exists)
- ❓ Head of IT (if role exists)

**Current implementation is CORRECT** ✅
- Only IT staff should revoke device certificates
- Medical staff should not manage device security

---

## Comparison with Other Endpoints

### Device Management (`/api/v1/devices/*`)
```python
require_admin_or_medical  # Administrator, Doctor, Nurse
```

**Observation:** Medical staff can manage device assignments but NOT provisioning/certificates

**This makes sense:**
- Medical staff assign watches to patients (clinical task)
- IT staff provision watches with certificates (infrastructure task)

---

## Role Hierarchy (Implicit)

```
Administrator
├─ Can do everything
├─ Generate provisioning codes ✅
├─ Revoke certificates ✅
└─ Manage device assignments ✅

Technician (IT)
├─ Generate provisioning codes ✅
├─ Revoke certificates ✅
└─ Manage device assignments ❌

Doctor
├─ Manage device assignments ✅
├─ Generate provisioning codes ❌
└─ Revoke certificates ❌

Nurse
├─ Manage device assignments ✅
├─ Generate provisioning codes ❌
└─ Revoke certificates ❌

Lab Technician / Radiologist
├─ Manage device assignments ❌
├─ Generate provisioning codes ❌
└─ Revoke certificates ❌
```

---

## Recommendation

**Current role requirements are CORRECT** ✅

**Reasoning:**
1. Device provisioning = infrastructure/security task (IT staff only)
2. Device assignment = clinical task (medical + IT staff)
3. Certificate revocation = security task (IT staff only)
4. Separation of duties = good security practice

**No changes needed to role checking in provisioning API.**

---

## Testing Access

### To test as Administrator:
```bash
# Login as Lisa Thompson
POST /api/v1/auth/login
{
  "pin": "1234",
  "password": "admin123"
}

# Use returned JWT token
Authorization: Bearer <token>

# Generate provisioning code
POST /api/v1/provisioning/generate-code
```

### To test as Technician:
```bash
# Login as David Kumar
POST /api/v1/auth/login
{
  "pin": "5678",
  "password": "tech123"
}

# Use returned JWT token
Authorization: Bearer <token>

# Generate provisioning code
POST /api/v1/provisioning/generate-code
```

### To test as Doctor (should FAIL):
```bash
# Login as Sarah Johnson
POST /api/v1/auth/login
{
  "pin": "xxxx",
  "password": "xxxx"
}

# Try to generate code - should get HTTP 403
POST /api/v1/provisioning/generate-code
# Response: "Insufficient permissions. Required role: Administrator, Technician"
```

---

## Conclusion

Role checking in provisioning API is **CORRECT** ✅

No changes needed. The roles are appropriate for a hospital device management system.

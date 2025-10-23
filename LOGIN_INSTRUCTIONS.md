# 🔐 LOGIN INSTRUCTIONS - 6-Digit PIN Testing

**Date:** 2025-10-18
**Status:** ✅ Both backend and frontend are running!

---

## 🚀 QUICK START

### ✅ Backend Status
- **Running on:** http://localhost:8001
- **Swagger UI:** http://localhost:8001/docs
- **Status:** ✅ Active (PID 11120)

### ✅ Frontend Status
- **Running on:** http://localhost:3000
- **Status:** ✅ Active (PID 17628)

---

## 🔑 LOGIN CREDENTIALS

### Method 1: Frontend Login (Recommended for PIN Generation)

**URL:** http://localhost:3000

**Available Accounts:**

| Staff ID | Password | Role | Can Generate PIN? |
|----------|----------|------|-------------------|
| **ADM0001** | admin123 | Administrator | ✅ Yes |
| **PRV0001** | prov123 | Provisioner | ✅ Yes |
| **TEC0001** | tech123 | Technician | ✅ Yes |
| DOC0001 | doctor123 | Doctor | ❌ No |
| NUR0001 | nurse123 | Nurse | ❌ No |

**Steps to Login:**
1. Open browser: http://localhost:3000
2. Enter Staff ID (e.g., `ADM0001`)
3. Enter Password (e.g., `admin123`)
4. Click "Login"

---

## 🎯 TESTING THE 6-DIGIT PIN FEATURE

### Step 1: Login to Frontend
```
1. Go to: http://localhost:3000
2. Login as: ADM0001 / admin123
```

### Step 2: Navigate to Device Provisioning
```
1. After login, look for "Device Provisioning" in the navigation menu
2. Or navigate directly to the provisioning page
   (The exact route depends on your app structure)
```

### Step 3: Generate 6-Digit PIN
```
1. You should see a blue "Device Setup PIN" card at the top
2. Click the "Generate PIN" button
3. You will see:
   ┌─────────────────────────────────┐
   │ Provisioning PIN                │
   │                                 │
   │        456789        ��         │
   │                                 │
   │ Validity: 10 minutes            │
   │ Time remaining: 9m 45s          │
   └─────────────────────────────────┘
```

### Step 4: Test Copy Functionality
```
1. Click the 📋 (copy) icon next to the PIN
2. You should see: "✓ Copied to clipboard!"
3. The PIN is now ready to paste
```

### Step 5: Observe Timer
```
1. Watch the countdown timer update
2. It shows: "9m 45s" → "9m 44s" → etc.
3. After 10 minutes, it should show "Expired"
```

---

## 🔧 ALTERNATIVE: Backend API Testing

If you want to test the backend API directly without the UI:

### Using Swagger UI

**URL:** http://localhost:8001/docs

**Steps:**

1. **Login to get token:**
   - Click on `POST /api/v1/auth/login`
   - Click "Try it out"
   - Enter:
     ```json
     {
       "staffId": "ADM0001",
       "password": "admin123"
     }
     ```
   - Click "Execute"
   - Copy the `access_token` from the response

2. **Authorize:**
   - Click the green "Authorize" button at top right
   - Enter: `Bearer {your_token_here}`
   - Click "Authorize"

3. **Generate PIN:**
   - Click on `POST /api/v1/provisioning/generate-code`
   - Click "Try it out"
   - Enter:
     ```json
     {
       "validityMinutes": 10
     }
     ```
   - Click "Execute"
   - You should see response:
     ```json
     {
       "code": "123456",
       "expiresAt": "2025-10-18T...",
       "validityMinutes": 10,
       "technicianId": "ADM0001"
     }
     ```

---

## ❓ TROUBLESHOOTING

### Issue: Cannot access http://localhost:3000
**Solution:**
```bash
# Check if frontend is running
netstat -ano | findstr :3000

# If not running, start it:
cd hospital-display-app
npm start
```

### Issue: Cannot access http://localhost:8001
**Solution:**
```bash
# Check if backend is running
netstat -ano | findstr :8001

# If not running, start it:
cd hospital-backend
python main.py
```

### Issue: Login fails with "Invalid credentials"
**Possible reasons:**
1. Check if you're using the correct Staff ID (case-sensitive)
2. Passwords might not be seeded yet

**Fix - Seed passwords:**
```bash
cd hospital-backend
python -c "
import asyncio
from app.core.database import seedStaffCredentials

asyncio.run(seedStaffCredentials())
"
```

### Issue: "Access Denied" when trying to generate PIN
**Reason:** Only Administrator, Provisioner, and Technician roles can generate PINs.

**Solution:** Login with one of these accounts:
- ADM0001 (Administrator)
- PRV0001 (Provisioner)
- TEC0001 (Technician)

---

## 📊 DATABASE CREDENTIALS (For Direct Access)

**Database:** PostgreSQL
**Connection String:** `postgresql://hospital_user:hospital123@localhost:5432/hospitaldb`

**Details:**
- Host: localhost
- Port: 5432
- Database: hospitaldb
- Username: hospital_user
- Password: hospital123

**Direct Query Example:**
```bash
# Windows (using psql if installed)
psql -h localhost -U hospital_user -d hospitaldb -c "SELECT id, role FROM staff WHERE role IN ('Administrator', 'Provisioner', 'Technician');"
```

---

## 🎉 WHAT YOU SHOULD SEE

### 1. Frontend Login Page
- Clean login form with Staff ID and Password fields
- "Login" button

### 2. Device Provisioning Page (After Login)
- **PIN Generation Card** (blue gradient, at top)
  - "Generate PIN" button
  - Large 6-digit display when PIN is generated
  - Copy button with visual feedback
  - Countdown timer
  - Setup instructions

### 3. Device Provisioning Form (below PIN card)
- Device type selection (Watch, Monitor, etc.)
- Device information fields
- "Provision Device" button

---

## 📝 NEXT STEPS AFTER LOGIN

Once you're logged in and see the PIN generation card:

1. ✅ Click "Generate PIN" - verify it generates 6 digits
2. ✅ Click copy button - verify "✓ Copied to clipboard!" appears
3. ✅ Check timer - verify countdown updates
4. ✅ Read instructions - verify they mention 6-digit PIN

If all the above work, the frontend implementation is complete and ready for ESP32 testing!

---

## 🔗 USEFUL LINKS

- **Frontend:** http://localhost:3000
- **Backend API Docs:** http://localhost:8001/docs
- **Backend Health Check:** http://localhost:8001/health (if available)

---

**Ready to test!** Use **ADM0001 / admin123** to login and start generating 6-digit PINs! 🚀

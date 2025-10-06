# Frontend Integration Testing Guide

**Date:** October 6, 2025
**Status:** ✅ Ready for Testing
**Frontend:** http://localhost:3000
**Backend:** http://localhost:8001

---

## 🎉 System is Ready!

Both frontend and backend are running and aligned. All critical API endpoint mismatches have been fixed.

### ✅ Fixes Applied

1. **Patient Search** - Fixed path parameter format
   - Before: `/patients/search?q={query}` ❌
   - After: `/patients/search/{query}` ✅

2. **Discharge Initiation** - Aligned endpoint names
   - Before: `/discharge-workflow/initiate` ❌
   - After: `/discharge-workflow/doctor-request` ✅

3. **Discharge Completion** - Aligned endpoint names
   - Before: `/discharge-workflow/complete` ❌
   - After: `/discharge-workflow/nurse-discharge` ✅

---

## Testing Instructions

Open your browser and navigate to: **http://localhost:3000**

---

## 📋 Feature Testing Checklist

### 1. Patient Management

#### ✅ View Patient List
**Test:** Navigate to patient list view
- **Expected:** See list of patients with names, room numbers, status
- **Backend Call:** `GET /api/v2/patients/list`
- **What to check:**
  - Patient cards display correctly
  - Room numbers show up
  - Status badges visible (stable/critical/emergency)

#### ✅ Search Patients
**Test:** Use the search bar to find a patient
- **Try searching for:**
  - Patient name: "Thomas" or "Brown"
  - Room number: "205"
  - MRN: "MRN-2025-000005"
- **Backend Call:** `GET /api/v2/patients/search/{query}`
- **What to check:**
  - Search results appear
  - Matching patients highlighted
  - Search is fast and responsive

#### ✅ View Patient Details
**Test:** Click on a patient card to see details
- **Expected:** Full patient information displayed
  - Demographics
  - Medical history
  - Current medications
  - Active investigations
  - Therapy sessions
  - Patient notes
- **Backend Call:** `GET /api/v2/patients/{id}`
- **What to check:**
  - All tabs load correctly
  - Data is formatted properly
  - CamelCase fields display correctly

#### ✅ Filter by Status
**Test:** Filter patients by medical status
- **Try filtering:**
  - Stable patients
  - Critical patients
  - Emergency patients
- **Backend Call:** `GET /api/v2/patients/status/{status}`
- **What to check:**
  - Only matching patients show
  - Filter button highlights
  - Count updates correctly

---

### 2. Medications Management

#### ✅ View Patient Medications
**Test:** Open patient details → Medications tab
- **Expected:** List of patient's medications
- **Backend Call:** `GET /api/v2/medications/patient/{patientId}`
- **What to check:**
  - Medication names display
  - Dosage and frequency shown
  - Status badges correct (active/stopped/held)
  - Prescribed by doctor name

#### ✅ Add New Medication
**Test:** Click "Add Medication" button
- **Fill in:**
  - Medication name
  - Dosage (e.g., "500mg")
  - Frequency (e.g., "TID")
  - Route (e.g., "PO")
  - Duration (e.g., "7 days")
- **Backend Call:** `POST /api/v2/atomic/patients/{patientId}/medications`
- **What to check:**
  - Form validates required fields
  - Medication appears in list after adding
  - Success message shows
  - Atomic transaction completes

#### ✅ Update Medication Status
**Test:** Click status dropdown on a medication
- **Try changing to:**
  - Stopped
  - Held
  - Discontinued
- **Backend Call:** `PUT /api/v2/medications/{medicationId}/status`
- **What to check:**
  - Status updates immediately
  - Badge color changes
  - Backend confirms update

#### ✅ Administer Medication
**Test:** Click "Administer" button on active medication
- **Expected:** Mark medication as administered
- **Backend Call:** `POST /api/v2/medications/{medicationId}/complete`
- **What to check:**
  - Administration time recorded
  - Badge updates
  - Audit log entry created

---

### 3. Investigations Management

#### ✅ View Patient Investigations
**Test:** Open patient details → Investigations tab
- **Expected:** List of ordered investigations
- **Backend Call:** `GET /api/v2/investigations/patient/{patientId}`
- **What to check:**
  - Investigation types listed
  - Status shown (ordered/in-progress/completed)
  - Urgency badges (routine/urgent/stat)
  - Ordered date/time

#### ✅ Add New Investigation
**Test:** Click "Order Investigation" button
- **Fill in:**
  - Investigation type (e.g., "CBC", "X-Ray Chest")
  - Urgency level
  - Clinical notes
- **Backend Call:** `POST /api/v2/atomic/patients/{patientId}/investigations`
- **What to check:**
  - Investigation appears in list
  - Status is "ordered"
  - Timestamp correct
  - Atomic operation succeeds

#### ✅ Update Investigation Status
**Test:** Change investigation status
- **Try:**
  - Mark as "in-progress"
  - Mark as "completed"
- **Backend Call:** `PUT /api/v2/investigations/{investigationId}/status`
- **What to check:**
  - Status badge updates
  - Timeline shows progression
  - Cannot go backwards in status

#### ✅ Complete Investigation
**Test:** Click "Complete" button and add results
- **Fill in:**
  - Results/findings
  - Completion notes
- **Backend Call:** `POST /api/v2/investigations/{investigationId}/complete`
- **What to check:**
  - Status changes to "completed"
  - Results display correctly
  - Completion timestamp recorded

---

### 4. Therapy Management

#### ✅ View Patient Therapies
**Test:** Open patient details → Therapy tab
- **Expected:** List of prescribed therapies
- **Backend Call:** `GET /api/v2/therapy/patient/{patientId}`
- **What to check:**
  - Therapy types listed (PT, OT, Speech, etc.)
  - Status shown (active/completed/discontinued)
  - Frequency and duration
  - Prescribed by therapist

#### ✅ Add New Therapy
**Test:** Click "Prescribe Therapy" button
- **Fill in:**
  - Therapy type
  - Description
  - Frequency
  - Duration
  - Start date
- **Backend Call:** `POST /api/v2/atomic/patients/{patientId}/therapies`
- **What to check:**
  - Therapy added to list
  - Status is "active"
  - Schedule created
  - Atomic operation completes

#### ✅ Record Therapy Session
**Test:** Click "Add Session" on active therapy
- **Fill in:**
  - Session date/time
  - Progress notes
  - Therapist observations
- **Backend Call:** `POST /api/v2/therapy/{therapyId}/sessions`
- **What to check:**
  - Session appears in history
  - Progress tracked
  - Timestamp correct

#### ✅ Update Therapy Status
**Test:** Change therapy status
- **Try:**
  - Mark as "completed"
  - Mark as "discontinued"
- **Backend Call:** `PUT /api/v2/therapy/{therapyId}/status`
- **What to check:**
  - Status updates
  - End date recorded if completed
  - Cannot add new sessions to discontinued therapy

---

### 5. Patient Notes

#### ✅ View Patient Notes
**Test:** Open patient details → Notes tab
- **Expected:** Timeline of patient notes
- **Backend Call:** Via patient details endpoint
- **What to check:**
  - Notes in chronological order
  - Staff names shown (Dr. Sarah Johnson, etc.)
  - Timestamps correct
  - Can edit/delete own notes

#### ✅ Add Patient Note
**Test:** Click "Add Note" button
- **Fill in:**
  - Note content (clinical observations)
  - Note type (if available)
- **Backend Call:** `POST /api/v2/patients/{patientId}/notes`
- **What to check:**
  - Note appears immediately
  - Your staff ID recorded
  - Timestamp accurate
  - Edit button available

#### ✅ Edit Patient Note
**Test:** Click "Edit" on your own note
- **Try:**
  - Modify content
  - Save changes
- **Backend Call:** `PUT /api/v2/patients/{patientId}/notes/{noteId}`
- **What to check:**
  - "Edited" badge appears
  - Edit timestamp recorded
  - Cannot edit other users' notes
  - Original content preserved in audit log

#### ✅ Delete Patient Note
**Test:** Click "Delete" on your own note
- **Expected:** Confirmation dialog
- **Backend Call:** `DELETE /api/v2/patients/{patientId}/notes/{noteId}`
- **What to check:**
  - Confirmation required
  - Note removed from list
  - Cannot delete other users' notes
  - Soft delete (audit trail preserved)

---

### 6. Discharge Workflow

#### ✅ Initiate Discharge
**Test:** Click "Discharge Patient" button
- **Expected:** Discharge workflow starts
- **Backend Call:** `POST /api/v1/discharge-workflow/doctor-request`
- **What to check:**
  - Discharge request created
  - Status changes to "pending discharge"
  - Notification sent to nursing
  - Workflow ID generated

#### ✅ Complete Discharge
**Test:** (As nurse) Complete discharge process
- **Steps:**
  - Review discharge checklist
  - Remove device assignment
  - Complete final documentation
  - Confirm discharge
- **Backend Calls:**
  - `POST /api/v1/devices/unassign/{patientId}`
  - `POST /api/v1/discharge-workflow/nurse-discharge`
- **What to check:**
  - Device unassigned
  - Patient status = "discharged"
  - Discharge date/time recorded
  - Bed becomes available

---

### 7. Authentication & Authorization

#### ✅ Login
**Test:** Use login form
- **Try credentials:**
  - Doctor: DOC0001 / password123
  - Nurse: NUR0001 / password123
  - Admin: ADM0001 / password123
- **Backend Call:** `POST /api/v1/auth/login`
- **What to check:**
  - JWT token received
  - User profile loaded
  - Role-based permissions applied
  - Session persists on refresh

#### ✅ Protected Routes
**Test:** Access features based on role
- **What to check:**
  - Doctors can prescribe medications
  - Nurses can administer medications
  - Admins can manage staff
  - Unauthorized actions blocked

#### ✅ Logout
**Test:** Click logout button
- **Backend Call:** `POST /api/v1/auth/logout`
- **What to check:**
  - Token invalidated
  - Redirected to login
  - Session cleared
  - Cannot access protected routes

---

### 8. Real-Time Features

#### ✅ WebSocket Connection
**Test:** Monitor WebSocket status
- **Backend:** `ws://localhost:8001/api/v1/ws`
- **What to check:**
  - Connection established indicator
  - Reconnects automatically if dropped
  - No errors in console

#### ✅ Live Updates
**Test:** Open same patient in two browser tabs
- **Try:**
  - Add medication in tab 1
  - Watch it appear in tab 2
- **What to check:**
  - Changes propagate immediately
  - No page refresh needed
  - Data stays synchronized

---

## 🐛 Common Issues to Watch For

### 1. CORS Errors
**Symptom:** "CORS policy blocked" in browser console
**Check:** Backend should allow `http://localhost:3000`
**Fix:** Already configured in backend `.env` file ✅

### 2. 404 Errors
**Symptom:** API calls return 404 Not Found
**Check:** Endpoint paths in browser Network tab
**Expected:** All calls should use `/api/v1/` or `/api/v2/` prefix

### 3. 422 Validation Errors
**Symptom:** Form submission fails with validation message
**Check:** Error details in response
**Expected:** Clear field-level error messages

### 4. Authentication Errors
**Symptom:** 403 Forbidden or 401 Unauthorized
**Check:** JWT token in localStorage
**Expected:** Token should be present after login

### 5. Empty Data Lists
**Symptom:** No patients/medications show up
**Check:** Backend database has seed data
**Expected:** At least 5 patients should be visible

---

## 🔍 Browser Developer Tools

### Open Console (F12)
**Monitor:**
- API requests in Network tab
- Console errors/warnings
- WebSocket connection status
- Redux state changes (if applicable)

### Key Things to Check:
1. **Network Tab**
   - All requests return 200 OK (or expected error codes)
   - Response times < 1 second
   - Payloads are JSON with camelCase fields

2. **Console Tab**
   - No red errors
   - Yellow warnings are OK (development mode)
   - WebSocket messages flowing

3. **Application Tab**
   - localStorage has JWT token
   - Session data persists
   - No quota exceeded errors

---

## ✅ Success Criteria

Your frontend-backend integration is working if:

- ✅ Patient list loads and displays
- ✅ Search returns correct results
- ✅ Patient details show all tabs
- ✅ Can add medications/investigations/therapies
- ✅ Status updates work immediately
- ✅ Notes can be created/edited/deleted
- ✅ Discharge workflow completes
- ✅ Authentication works for all roles
- ✅ No CORS errors in console
- ✅ All buttons respond within 1 second
- ✅ WebSocket connection stable
- ✅ Data updates in real-time

---

## 📊 Expected Test Data

The backend database is seeded with:

### Patients
- **Thomas Brown** (ID: 081a5294-da91-4c74-bb8a-e5062f5851dd)
  - Room: 205B
  - Status: Active
  - Has notes, medications, investigations

- **4 additional patients** with various statuses

### Staff
- **DOC0001** - Dr. Sarah Johnson (Doctor)
- **DOC0002** - Dr. Michael Chen (Doctor)
- **NUR0001** - Emily Rodriguez (Nurse)
- **NUR0002** - James Wilson (Nurse)
- **ADM0001** - Admin User (Administrator)
- **TEC0001** - Tech Support (Technician)

### Default Password
All staff accounts: **password123**

---

## 🎯 Testing Priority

**High Priority** (Test First):
1. Patient list and search
2. Login/logout
3. View patient details
4. Add medication

**Medium Priority**:
5. Add investigation
6. Add therapy
7. Update statuses
8. Patient notes

**Low Priority** (Test If Time):
9. Discharge workflow
10. Real-time updates
11. Role-based access
12. WebSocket features

---

## 📝 Reporting Issues

If you find any issues, note:
1. **What button/feature** you clicked
2. **Expected behavior** vs **actual behavior**
3. **Error message** (if any)
4. **Browser console errors** (F12 → Console tab)
5. **Network request details** (F12 → Network tab)

Let me know what you find, and I'll fix it immediately!

---

## 🚀 Ready to Test!

**Frontend:** http://localhost:3000
**Backend:** http://localhost:8001
**API Docs:** http://localhost:8001/docs

**Status:**
- ✅ Backend running (PID: 29416)
- ✅ Frontend compiled and running
- ✅ All critical endpoints aligned
- ✅ Database connected and seeded
- ✅ WebSocket services initialized

**Go ahead and start clicking buttons! Everything should work smoothly.**

If anything doesn't work as expected, just let me know exactly what you clicked and what happened, and I'll fix it right away! 🎉

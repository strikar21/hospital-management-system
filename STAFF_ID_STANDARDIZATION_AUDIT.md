# Staff ID Standardization Audit & Plan

## Current Data Storage Analysis

### 🔍 **FRONTEND PATTERNS FOUND:**

#### ✅ **CORRECT (Store ID Only):**
- **PatientAdmission.tsx:87** - `performedBy: currentUser.staffId`
- **PatientAlerts.tsx** - `performedBy: currentUser.id` ✅

#### ❌ **INCORRECT (Store Name):**
- **Therapies** - `performedBy: currentUser.name`
- **Notes** - `performedBy: currentUser.name`
- **Investigations** - `performedBy: currentUser.name`
- **Handoff Notes** - `performedBy: currentUser.name`

#### ⚠️ **MIXED (Store Both ID + Name):**
- **PatientAlerts** - Stores `performedBy: currentUser.id` + `performedByName: currentUser.name` + `performedByRole: currentUser.role`

### 🔍 **TYPE DEFINITIONS:**
- Most types have `performedBy: string` (should be ID)
- Some have optional `performedByName?: string` (good for display)
- Types seem designed for ID storage but implementation varies

---

## 🎯 **STANDARDIZATION PLAN**

### **Phase 1: Frontend Audit (Current Task)**
1. ✅ Audit all frontend services storing staff references
2. ❓ Check what backend APIs expect
3. ❓ Verify database schema
4. ❓ Create migration plan

### **Phase 2: Backend Analysis (Next)**
- Check backend API endpoints - do they expect IDs or names?
- Review database schema for staff reference columns
- Identify what needs to change on backend

### **Phase 3: Database Schema Review**
- Check current column types for staff references
- Verify foreign key relationships exist
- Plan any schema migrations needed

---

## ✅ **BACKEND & DATABASE ANALYSIS COMPLETE:**

### **Database Schema (All Good!):**
```sql
-- ✅ All tables use TEXT for staff IDs (correct)
"prescribedBy" TEXT NOT NULL,     -- medications table
"performedBy" TEXT,               -- investigations table
"performedBy" TEXT,               -- therapy table
"performedBy" TEXT,               -- therapysessions table
"performedBy" TEXT NOT NULL,      -- caseentries table
```

### **Backend API Expectations:**
```python
# ✅ Backend expects staff IDs (correct)
'prescribedBy': medication_data.get('prescribed_by'),  # expects staff ID
'performedBy': therapy_data.get('performed_by'),       # expects staff ID
```

### **Current Data Format (from case sheet):**
```json
// ✅ Backend already stores staff IDs correctly
{
  "performedBy": "DOC0001",           // ✅ Staff ID stored
  "performedByName": "Dr. Michael Chen", // ❌ Unnecessary duplicate
  "performedByRole": "Staff"          // ❌ Unnecessary duplicate
}
```

## 🎯 **KEY FINDING:**
**Backend and Database are ALREADY CORRECT!**
- Database stores staff IDs (TEXT fields)
- Backend expects and stores staff IDs
- The issue is **FRONTEND ONLY** - some services send names instead of IDs

---

## 📋 **STANDARDIZED APPROACH (Target State):**

```typescript
// ✅ CORRECT - Store only staff ID
{
  performedBy: currentUser.staffId,  // Always use staffId
  // Let frontend resolve name via staff mapping
}

// ❌ AVOID - Don't store names or duplicate data
{
  performedBy: currentUser.name,      // Never store names
  performedByName: currentUser.name   // Unnecessary duplication
}
```

---

## 🔧 **IMPLEMENTATION PLAN:**

### **✅ GOOD NEWS: Minimal Changes Needed!**

**Backend & Database:** ✅ Already correct - no changes needed
**Frontend:** ❌ Some services need fixing

### **Frontend Services to Fix:**

1. **Therapies** - Change `performedBy: currentUser.name` → `currentUser.staffId`
2. **Notes** - Change `performedBy: currentUser.name` → `currentUser.staffId`
3. **Investigations** - Change `performedBy: currentUser.name` → `currentUser.staffId`
4. **Handoff Notes** - Change `performedBy: currentUser.name` → `currentUser.staffId`

### **Implementation Steps:**

1. **Update 4 Frontend Services** (30 minutes work)
2. **Test Staff Mapping** (ensure names display correctly)
3. **Verify Case Sheet Timeline** (check all entries show proper names)

### **No Database Changes Needed!**
### **No Backend Changes Needed!**

---

## 📊 **CURRENT STATUS:**

- ✅ **Database Schema:** Stores staff IDs correctly
- ✅ **Backend APIs:** Expect and handle staff IDs correctly
- ✅ **Staff Mapping:** Frontend lookup system works
- ❌ **Frontend Services:** 4 services send names instead of IDs

**Estimated Fix Time: 30 minutes**
**Risk Level: Low (only frontend changes)**
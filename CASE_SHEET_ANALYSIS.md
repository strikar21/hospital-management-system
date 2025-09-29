# Case Sheet Analysis - Database Tables & Design Intent

## Database Tables Found (camelCase compliant)

### ✅ Existing Tables:
1. **`"caseEntries"`** - Comprehensive case entries (just created)
   - Columns: id, patientId, entryType, description, findings, recommendations, followUpDate, severity, category, createdBy, timestamp
   - Purpose: Dedicated case sheet entries with medical details

2. **`medications`** - Patient medications
   - Columns: patientId, name, dosage, frequency, route, prescribedBy, createdAt
   - Purpose: Medication prescriptions and administration

3. **`investigations`** - Patient investigations
   - Columns: patientId, type, name, scheduledAt, completedAt, results, notes, createdAt
   - Purpose: Lab tests, imaging, diagnostics

4. **`therapy`** - Patient therapy sessions
   - Columns: patientId, type, description, startDate, endDate, performedBy, createdAt
   - Purpose: Physical therapy, rehabilitation

5. **`patientnotes`** - Patient notes
   - Columns: patientId, content, authorId, authorName, timestamp
   - Purpose: Clinical notes and observations

## Case Sheet Design Options

### Option A: Dedicated Case Entries (Current Implementation)
- Case sheets are separate medical entries stored in `"caseEntries"` table
- Each entry has specific fields: type, description, findings, recommendations
- Frontend creates case entries separately from medications/investigations/therapy

### Option B: Aggregated Timeline View (Suggested by User)
- Case sheets display ALL activities from all tabs in chronological order
- Combines medications + investigations + therapy + notes by timestamp
- Creates unified timeline of patient medical history
- No separate case sheet entries needed

## Current Frontend Implementation Status
- ✅ Frontend fetches from `/patients/{id}/case-entries` endpoint
- ✅ Backend has `PatientCaseService.getCaseEntries()` method
- ✅ Database table `"caseEntries"` now exists
- ✅ All camelCase compliance maintained

## Recommendation
Based on user question "show all details in time wise manner from all entries in other tabs", **Option B (Aggregated Timeline)** seems to be the desired approach.

This would mean:
1. Case sheet tab shows chronological timeline of ALL patient activities
2. Combines medications, investigations, therapy, notes by timestamp
3. Provides comprehensive medical history in one view
4. May still allow dedicated case entries for summary notes

## Current Status ✅
- **Case Entries API:** WORKING - backend logs show successful retrieval
- **Database Table:** `"caseEntries"` exists and functional
- **Frontend Integration:** Case sheet tab now loads data successfully
- **Implementation:** Currently uses Option A (Dedicated Case Entries)

## The Question: Aggregated Timeline vs Dedicated Entries

**Current Implementation (Option A):**
- Case sheet shows entries from `"caseEntries"` table only
- Each tab (medications, investigations, therapy, notes) stores data in separate tables
- Case sheet is a separate medical record section

**Your Suggestion (Option B):**
- Case sheet shows ALL activities from all tabs in chronological order
- Combines medications + investigations + therapy + notes by timestamp
- Creates unified timeline of entire patient medical history

## Next Steps
1. **Clarify:** Do you want Option B (aggregated timeline from all tabs)?
2. **If Yes:** Modify backend to combine all medical data chronologically in case sheet API
3. **If No:** Continue with current dedicated case entries approach
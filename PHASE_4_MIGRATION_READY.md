# Phase 4: Migration - READY TO START

**Status:** Phases 1-3 Complete ✅ | Phase 4 Ready to Execute
**Date:** 2025-11-10
**Branch:** `refactor/clean-slate-phase1-shared-modules`

---

## ✅ FOUNDATION COMPLETE

**What's Done:**
- ✅ Phase 1: 21 shared utility modules
- ✅ Phase 2: 14 API/data layer modules
- ✅ Phase 3: 22 domain layer modules
- ✅ **Total: 57 modules ready to use**

**What's Next:**
Phase 4 is about **replacing old code** with the new modules and **deleting duplicates**.

---

## ⚠️ IMPORTANT DECISION POINT

Phase 4 involves **DELETING CODE** and **MODIFYING CORE FILES** like:
- `mqtt_service.py` (1590 lines)
- `websocket_manager.py` (800+ lines)
- Frontend service files (8 files, ~600 LOC)

**This is a BREAKING CHANGE point** - old code will be replaced.

### **You have 3 options:**

---

## OPTION 1: INCREMENTAL ADOPTION (RECOMMENDED ⭐)

**Strategy:** Use new modules in NEW code only. Migrate old code gradually.

**Benefits:**
- ✅ Zero risk
- ✅ No breaking changes
- ✅ Immediate value from new modules
- ✅ Migrate at your own pace

**How:**
```python
# In new features, use:
from app.common.datetime import now_utc, parse_iso8601
from app.common.waveform import decompress_delta
from app.domain.alerts.generators import generate_vital_alert

# Old code continues to work unchanged
```

**When to migrate old code:**
- File by file, as you touch it
- During bug fixes
- During feature additions
- No deadline, no pressure

---

## OPTION 2: AUTOMATED MIGRATION (PROCEED WITH PHASE 4)

**Strategy:** Systematically replace old code with new modules, delete duplicates.

**What I'll do:**
1. Replace timestamps in `mqtt_service.py` (10 occurrences)
2. Replace waveform processing (if duplicates exist)
3. Replace inline queries with `app.common.queries`
4. Replace frontend services with `apiClient` and `wsClient`
5. Delete duplicate code (~1,470 LOC)

**Risk Level:** MEDIUM
- Old code will be deleted
- Requires testing before deployment
- Potential for bugs if not carefully reviewed

**Time:** 2-3 hours to complete

**Testing Required:**
- Manual testing of vitals flow
- Manual testing of alerts
- Manual testing of WebSocket connection
- Ideally: automated tests (currently 0% coverage)

---

## OPTION 3: PROFESSIONAL REVIEW FIRST

**Strategy:** Your team reviews the 57 modules, writes tests, then migrates.

**Steps:**
1. Code review of all 57 modules
2. Write unit tests (target: >80% coverage)
3. Write integration tests
4. Plan migration with your team
5. Execute Phase 4 with confidence

**Time:** 1-2 weeks
**Benefits:** Highest confidence, lowest risk

---

## 📊 WHAT PHASE 4 MIGRATION WOULD DO

### **Backend Changes:**

#### **File: `mqtt_service.py`**
**Changes:** ~15 replacements

```python
# BEFORE (scattered patterns):
timestamp = datetime.now()
timestamp = datetime.fromisoformat(x.replace('Z', '+00:00'))

# AFTER (centralized):
from app.common.datetime import now_utc, parse_iso8601
timestamp = now_utc()
timestamp = parse_iso8601(x)
```

**Lines Changed:** ~20
**Lines Deleted:** 0 (just replacements)
**Risk:** LOW (timestamps are straightforward)

---

#### **File: `mqtt_service.py` (inline queries)**
**Changes:** ~10 query replacements

```python
# BEFORE:
patient = await conn.fetchrow("SELECT * FROM patients WHERE id = $1", id)

# AFTER:
from app.common.queries import get_patient_by_id
patient = await get_patient_by_id(conn, id)
```

**Lines Changed:** ~15
**Lines Deleted:** 0 (just replacements)
**Risk:** LOW (queries are simple replacements)

---

### **Frontend Changes:**

#### **Files: `src/services/*.ts` (8 files)**
**Changes:** Delete 8 service files, update imports

```typescript
// BEFORE:
import { PatientService } from '@/services/PatientService';
const service = new PatientService();
const patients = await service.getPatients();

// AFTER:
import { apiClient } from '@/lib/api';
const patients = await apiClient.get('/api/v1/patients');
```

**Lines Changed:** ~50 across all components
**Lines Deleted:** ~600 (8 service files)
**Risk:** MEDIUM (requires updating many components)

---

#### **File: `src/services/WebSocketService.ts`**
**Changes:** Delete file, update imports

```typescript
// BEFORE:
import { WebSocketService } from '@/services/WebSocketService';
const ws = new WebSocketService();
ws.connect();

// AFTER:
import { wsClient } from '@/lib/ws';
wsClient.connect();
```

**Lines Changed:** ~20 across components
**Lines Deleted:** ~200
**Risk:** MEDIUM (WebSocket is critical)

---

## 🎯 MY RECOMMENDATION

**For a production medical system, I recommend:**

### **OPTION 1: Incremental Adoption**

**Why:**
- This is a **medical system** - stability is critical
- **Zero test coverage** means migration risk is high
- New modules are **already usable** without migration
- Team can validate modules in production gradually

**Action Plan:**
1. **Today:** Start using new modules in any NEW code
2. **This week:** Team reviews the 57 modules
3. **Next week:** Write tests for critical paths
4. **Month 1:** Migrate 1-2 files as proof of concept
5. **Month 2-3:** Migrate remaining files gradually

---

## ❓ WHAT DO YOU WANT TO DO?

**Tell me:**

1. **"Incremental adoption"** → I'll create a guide for using new modules alongside old code

2. **"Proceed with Phase 4"** → I'll start the automated migration (CAUTION: will modify core files)

3. **"Write tests first"** → I'll generate test skeletons for the 57 modules

4. **"Just document what Phase 4 would do"** → I'll create detailed migration instructions for your team

5. **"Something else"** → Tell me what you need

---

## 📋 CURRENT STATUS

```
✅ Phases 1-3: COMPLETE (57 modules created)
⏸️  Phase 4: AWAITING YOUR DECISION

Branch: refactor/clean-slate-phase1-shared-modules
Files: 57 modular files (~2,530 LOC)
Status: Ready to use, zero breaking changes
```

---

**What's your decision?**

# Standardization Implementation Plan

**Date:** 2025-11-10
**Branch:** refactor/clean-slate-phase1-shared-modules
**Status:** Ready to implement

---

## Pre-Implementation Checklist ✅

### 1. Backup & Git Sync
- [ ] Check git status (no uncommitted changes)
- [ ] Review all commits on current branch
- [ ] Push to remote backup
- [ ] Verify remote has all commits
- [ ] Tag current state: `v1.0-pre-standardization`

### 2. Testing Preparation
- [ ] Run all existing tests (should be 95/95 passing)
- [ ] Document current test coverage
- [ ] Create test plan for standardization changes
- [ ] Ensure database backup exists

### 3. Documentation
- [ ] Review STANDARDIZATION_AUDIT.md
- [ ] Review TIMEZONE_STANDARDIZATION_PLAN.md
- [ ] Review STAFF_RESOLUTION_FIX_PLAN.md
- [ ] Create CHANGELOG.md entry

---

## Implementation Phases

### Phase 1: Foundation (2-3 hours) 🏗️

**Goal:** Create core standardization infrastructure

#### Step 1.1: Centralized Error Handler
**Files to Create:**
- `app/core/errors.py` - Exception classes
- `app/core/error_handler.py` - FastAPI exception handlers

**Classes:**
```python
# app/core/errors.py
class AppError(Exception)
class ValidationError(AppError)
class NotFoundError(AppError)
class AuthorizationError(AppError)
class ConflictError(AppError)
class DatabaseError(AppError)
```

**Impact:** Foundation for 322 HTTPException replacements

**Testing:**
- Unit tests for each exception class
- Integration test with FastAPI app
- Verify error response format

**Estimated Time:** 1 hour

---

#### Step 1.2: Database Decorators
**Files to Create:**
- `app/core/db_decorators.py` - Connection management decorators

**Decorators:**
```python
@with_db_connection  # Auto-provide connection
@with_transaction    # Auto-transaction management
@with_retry          # Auto-retry on connection failure
```

**Impact:** Reduces 41 manual connection patterns

**Testing:**
- Test decorator with mock connection
- Test transaction rollback on error
- Test retry logic

**Estimated Time:** 1 hour

---

#### Step 1.3: Response Models
**Files to Create:**
- `app/models/api_response.py` - Standard response models

**Models:**
```python
class SuccessResponse(BaseModel, Generic[T])
class ErrorResponse(BaseModel)
class PaginationMeta(BaseModel)
class ResponseMeta(BaseModel)
```

**Helper Functions:**
```python
def success_response(data, pagination=None)
def error_response(code, message, details=None)
def paginated_response(items, page, page_size, total)
```

**Testing:**
- Test response serialization
- Test pagination calculation
- Test metadata inclusion

**Estimated Time:** 1 hour

---

### Phase 2: Pilot Migration (2-3 hours) 🧪

**Goal:** Migrate 5 high-traffic endpoints to new standards

#### Pilot Endpoints
1. `GET /api/v2/patients/{patient_id}` - Patient details
2. `GET /api/v2/patients/{patient_id}/medications` - Medications list
3. `POST /api/v2/atomic/patients/{patient_id}/medications` - Add medication
4. `GET /api/v2/patients/{patient_id}/case-entries` - Case sheet
5. `GET /api/v2/patients/list` - Patient list

#### For Each Endpoint:
1. Replace HTTPException with AppError subclasses
2. Add `@with_db_connection` if applicable
3. Wrap response in `success_response()`
4. Add structured logging
5. Test endpoint manually
6. Run automated tests

**Success Criteria:**
- All 5 endpoints return standard response format
- Error handling consistent
- Tests passing
- Response time unchanged or improved

**Estimated Time:** 2-3 hours (30-40 min per endpoint)

---

### Phase 3: Bulk Migration (4-6 hours) 📦

**Goal:** Migrate remaining high-priority endpoints

#### Batch 1: Patient Endpoints (1 hour)
- All `/api/v2/patients/*` endpoints (~8 endpoints)

#### Batch 2: Atomic Medical Endpoints (1.5 hours)
- All `/api/v2/atomic/*` endpoints (~10 endpoints)

#### Batch 3: Medications & Investigations (1 hour)
- `/api/v2/medications/*`
- `/api/v2/investigations/*` (if exists)

#### Batch 4: Admin & Staff Endpoints (1 hour)
- `/api/v1/staff/*`
- `/api/v1/auth/*`

#### Batch 5: Device Management (1 hour)
- `/api/v1/device-management/*`
- `/api/v1/provisioning/*`

**Per Batch:**
1. Migrate all endpoints in batch
2. Run tests for that batch
3. Manual smoke test
4. Commit batch changes
5. Document any issues

**Estimated Time:** 4-6 hours total

---

### Phase 4: Services & Repositories (3-4 hours) 🔧

**Goal:** Apply decorators to service/repository layers

#### Step 4.1: Service Layer
**Files to Update:** ~20 service files

**Pattern:**
```python
# OLD
async def get_patient(self, patient_id: str):
    async with getDbConnection() as conn:
        return await self.repository.get_by_id(conn, patient_id)

# NEW
@with_db_connection
async def get_patient(self, patient_id: str, conn):
    return await self.repository.get_by_id(conn, patient_id)
```

**Batch Services:**
1. patient_service.py
2. medication_service.py
3. investigation_service.py
4. medical_action_service.py
5. Others...

**Estimated Time:** 2-3 hours

---

#### Step 4.2: Repository Layer
**Files to Update:** ~15 repository files

**Same pattern as services**

**Estimated Time:** 1-2 hours

---

### Phase 5: Logging Standardization (2-3 hours) 📝

**Goal:** Implement structured logging

#### Step 5.1: Create Logger
**Files to Create:**
- `app/core/structured_logger.py`

**Features:**
- JSON format
- Correlation IDs
- Request context
- Performance metrics

**Estimated Time:** 1 hour

---

#### Step 5.2: Migrate Logging
**Pattern:**
```python
# OLD
logger.info(f"✅ Retrieved {count} medications")

# NEW
log.info("Retrieved medications", count=count, action="get_medications")
```

**Approach:**
- Use search & replace for common patterns
- Focus on high-traffic endpoints first
- Keep existing logs working (gradual migration)

**Estimated Time:** 2 hours

---

### Phase 6: Testing & Validation (2-3 hours) ✅

**Goal:** Ensure everything works

#### Test Plan
1. **Unit Tests:**
   - All new error classes
   - All decorators
   - Response models
   - Logger

2. **Integration Tests:**
   - Each migrated endpoint
   - Error scenarios
   - Database transactions
   - Staff resolution

3. **Manual Testing:**
   - Frontend integration
   - Case sheet loading
   - Medication CRUD
   - Patient timeline
   - Error handling

4. **Performance Testing:**
   - Endpoint response times
   - Database connection pooling
   - Memory usage
   - Load testing (optional)

**Success Criteria:**
- All tests passing (95/95 minimum)
- No regressions
- Response format consistent
- Error messages clear
- Logs parseable

**Estimated Time:** 2-3 hours

---

### Phase 7: Documentation (1-2 hours) 📚

**Goal:** Update all documentation

#### Documents to Update:
1. **API Documentation**
   - New response format
   - Error codes
   - Example responses

2. **Developer Guide**
   - How to use error classes
   - How to use decorators
   - How to use structured logging
   - Code examples

3. **CHANGELOG.md**
   - List all changes
   - Breaking changes (if any)
   - Migration guide

4. **README.md**
   - Update architecture section
   - Update development workflow

**Estimated Time:** 1-2 hours

---

## Risk Mitigation

### Risk 1: Breaking Changes
**Risk:** Standardization breaks existing frontend integration

**Mitigation:**
- Maintain backward compatibility initially
- Add new response format alongside old
- Gradual migration with feature flags
- Test with actual frontend

**Rollback Plan:** Revert commits, merge branch separately

---

### Risk 2: Performance Regression
**Risk:** New abstractions slow down endpoints

**Mitigation:**
- Benchmark before/after
- Profile slow endpoints
- Optimize decorators
- Use connection pooling

**Threshold:** <10% latency increase acceptable

---

### Risk 3: Test Failures
**Risk:** Standardization breaks existing tests

**Mitigation:**
- Run tests after each phase
- Fix tests incrementally
- Update test fixtures
- Don't skip failing tests

**Action:** If >10 tests fail, pause and debug

---

### Risk 4: Merge Conflicts
**Risk:** Long-running branch conflicts with main

**Mitigation:**
- Commit frequently
- Push to backup branch
- Merge main into branch periodically
- Keep changes focused

---

## Timeline Estimate

### Optimistic: 12-15 hours
- Phase 1: 3 hours
- Phase 2: 2 hours
- Phase 3: 4 hours
- Phase 4: 3 hours
- Phase 5: 2 hours
- Phase 6: 2 hours
- Phase 7: 1 hour

### Realistic: 18-22 hours
- Phase 1: 3 hours
- Phase 2: 3 hours
- Phase 3: 6 hours
- Phase 4: 4 hours
- Phase 5: 3 hours
- Phase 6: 3 hours
- Phase 7: 2 hours

### Conservative: 25-30 hours
- Includes debugging, testing issues, documentation
- Includes frontend integration testing
- Includes performance optimization

---

## Session Planning

### Session 1: Foundation (3 hours)
- Complete Phase 1 entirely
- Create all core infrastructure
- Write tests for new components
- **Deliverable:** Error handler, decorators, response models

### Session 2: Pilot (3 hours)
- Complete Phase 2
- Migrate 5 pilot endpoints
- Test thoroughly
- **Deliverable:** 5 standardized endpoints with tests

### Session 3: Bulk Migration Part 1 (3 hours)
- Complete Batches 1-2 of Phase 3
- Patient + Atomic endpoints
- **Deliverable:** ~18 migrated endpoints

### Session 4: Bulk Migration Part 2 (3 hours)
- Complete Batches 3-5 of Phase 3
- Remaining API endpoints
- **Deliverable:** All API endpoints migrated

### Session 5: Service Layer (3 hours)
- Complete Phase 4.1
- Migrate service layer
- **Deliverable:** Services using decorators

### Session 6: Final Touches (3 hours)
- Complete repository layer (Phase 4.2)
- Add structured logging (Phase 5)
- **Deliverable:** Complete backend standardization

### Session 7: Testing & Docs (3 hours)
- Complete Phases 6-7
- Full test suite
- Documentation
- **Deliverable:** Production-ready standardized backend

**Total:** 7 sessions × 3 hours = 21 hours (realistic estimate)

---

## Decision Points

### Before Starting:
- [ ] Have all commits been backed up?
- [ ] Is test suite passing (95/95)?
- [ ] Is database backed up?
- [ ] Do we have 3+ hours for Phase 1?

### After Phase 1:
- [ ] Are new components tested?
- [ ] Do examples work?
- [ ] Ready to migrate pilot endpoints?

### After Phase 2:
- [ ] Do pilot endpoints work?
- [ ] Is response format correct?
- [ ] Does frontend handle new format?
- [ ] Continue to bulk migration?

### After Each Batch:
- [ ] Are tests passing?
- [ ] Any regressions?
- [ ] Response times acceptable?
- [ ] Continue to next batch?

### Before Final Merge:
- [ ] All tests passing?
- [ ] Documentation complete?
- [ ] Frontend tested?
- [ ] Performance acceptable?
- [ ] Ready for production?

---

## Success Metrics

### Code Quality
- [ ] 430+ lines of boilerplate removed
- [ ] 322 HTTPException → 50 standardized errors
- [ ] 41 connection patterns → decorators
- [ ] Consistent response format (100% endpoints)

### Test Coverage
- [ ] All existing tests passing (95/95+)
- [ ] New tests for infrastructure (20+ tests)
- [ ] Integration tests passing
- [ ] No regressions

### Performance
- [ ] Response time: ±10% of baseline
- [ ] Database connections: <10% of pool size
- [ ] Memory usage: No significant increase
- [ ] Load test: Same throughput

### Developer Experience
- [ ] Faster endpoint creation (measured)
- [ ] Clearer error messages (user feedback)
- [ ] Better logs (parseable JSON)
- [ ] Easier debugging (correlation IDs)

---

## Current Status

✅ **Completed:**
- Phase 4 migration (datetime, waveform, alerts)
- Staff resolution fixes
- Timezone standardization (partial)
- Datetime bug fixes
- Comprehensive audit

📋 **Ready to Start:**
- Phase 1: Foundation implementation

🎯 **Next Action:**
1. Backup & git sync
2. Tag current state
3. Begin Phase 1

---

**Plan Version:** 1.0
**Last Updated:** 2025-11-10
**Estimated Completion:** 7 sessions (21 hours)

# WebSocket Testing - Detailed Implementation Plan

**Date:** 2025-10-25
**Priority:** P1 - CRITICAL (Medical data routing safety)
**Researched:** Actual code flow verified

---

## Code Flow Understanding (VERIFIED)

### Architecture:
```
PatientCardContainer (3+ instances on screen)
    ↓ uses
usePatientVitals(patientId, initialVitals)
    ↓ uses
useWebSocket() [subscriberIdCounter here - BUG LOCATION]
    ↓ uses
WebSocketService.getInstance() [Singleton]
    ↓ manages
subscribers: MessageSubscriber[] [Array of callbacks]
    ↓ routes via
routeMessage(message) [Filters by patientId]
```

### Critical Code Paths:

**1. Subscription Flow:**
```typescript
// useWebSocket.ts:63 - POTENTIAL BUG HERE
const subscriberId = `subscriber-${++subscriberIdCounter.current}-${Date.now()}`;

// WebSocketService.ts:162-177
subscribe(subscriberId, callback, patientId) {
  // REMOVES duplicate IDs (mitigates but doesn't prevent bug)
  this.subscribers = this.subscribers.filter(sub => sub.id !== subscriberId);
  this.subscribers.push({ id: subscriberId, patientId, callback });

  // Sends backend subscription message
  if (patientId && !this.subscribedPatients.has(patientId)) {
    this.subscribeToPatient(patientId);
  }
}
```

**2. Message Routing:**
```typescript
// WebSocketService.ts:276-303
routeMessage(message: WebSocketMessage) {
  this.subscribers.forEach(subscriber => {
    if (subscriber.patientId) {
      // CRITICAL: Only sends if patientId matches
      if (message.patientId === subscriber.patientId) {
        subscriber.callback(message);
      }
    } else {
      // No filter - sends ALL messages (dashboard?)
      subscriber.callback(message);
    }
  });
}
```

**3. Cleanup Flow:**
```typescript
// usePatientVitals.ts:59-61
return () => {
  unsubscribe(subscriberId);
};

// WebSocketService.ts:182-198
unsubscribe(subscriberId) {
  // Finds and removes subscriber
  this.subscribers = this.subscribers.filter(sub => sub.id !== subscriberId);

  // If last subscriber for patient, tells backend
  if (otherSubs.length === 0) {
    this.unsubscribeFromPatient(subscriber.patientId);
  }
}
```

---

## Test Scenarios (What Could Go Wrong)

### SCENARIO 1: Duplicate Subscriber IDs
**Bug:** Two PatientCards mount in same millisecond → same subscriberId
**Current Code:** Line 164 removes duplicate before adding (MITIGATES but wrong card loses updates)
**Test:** Mount 3 cards simultaneously, verify all receive their own vitals

### SCENARIO 2: Cross-Patient Data Leak
**Bug:** Message routing sends wrong patient's data
**Current Code:** Line 289 filters by patientId (SHOULD BE SAFE)
**Test:** Send vitals for PAT001, verify PAT002 card doesn't update

### SCENARIO 3: Stale Subscriptions After Unmount
**Bug:** Unmounted component still receives messages
**Current Code:** useEffect cleanup should handle (VERIFY IT WORKS)
**Test:** Mount, unmount, send message, verify no callback

### SCENARIO 4: Subscription Not Cleaned Up
**Bug:** subscriberId not found during unsubscribe
**Current Code:** filter() with wrong ID won't find/remove
**Test:** Subscribe, manually change ID, unsubscribe, verify still in array

### SCENARIO 5: Reconnection Resubscribes Correctly
**Bug:** After disconnect/reconnect, subscriptions lost
**Current Code:** resubscribePatients() sends all subscribed patient IDs (SHOULD WORK)
**Test:** Connect, subscribe, disconnect, reconnect, verify messages flow

### SCENARIO 6: Multiple Subscribers Same Patient
**Bug:** All cards for same patient should receive updates
**Current Code:** Multiple subscribers with same patientId allowed
**Test:** 2 cards for PAT001, send vitals, verify both update

### SCENARIO 7: Unsubscribe Doesn't Affect Other Subscribers
**Bug:** Unsubscribing one card affects others
**Current Code:** Uses filter() by subscriberId (SHOULD BE SAFE)
**Test:** 2 cards PAT001, unmount one, verify other still receives

---

## Test Implementation Plan

### Phase 1: Unit Tests (WebSocketService)

**File:** `src/services/__tests__/WebSocketService.test.ts`

```typescript
describe('WebSocketService', () => {
  describe('Subscriber Management', () => {
    test('should handle duplicate subscriber IDs by replacing old one')
    test('should allow multiple subscribers for same patient')
    test('should remove subscriber on unsubscribe')
    test('should not affect other subscribers when one unsubscribes')
  });

  describe('Message Routing', () => {
    test('should route message only to matching patientId')
    test('should not route to wrong patient')
    test('should route to all subscribers without patientId filter')
    test('should handle message with no patientId')
  });

  describe('Backend Subscription Management', () => {
    test('should send subscribePatient message to backend')
    test('should not send duplicate subscribePatient for same patient')
    test('should send unsubscribePatient when last subscriber removed')
    test('should NOT unsubscribe if other subscribers exist')
  });

  describe('Reconnection', () => {
    test('should resubscribe to all patients after reconnect')
    test('should clear and recreate subscriptions correctly')
  });
});
```

**Estimated:** 12 tests, ~400 LOC

---

### Phase 2: Integration Tests (Hook + Service)

**File:** `src/hooks/__tests__/usePatientVitals.integration.test.ts`

```typescript
describe('usePatientVitals - Integration', () => {
  describe('Real-Time Updates', () => {
    test('should receive vitals via WebSocket')
    test('should update when new vitals arrive')
    test('should use initialVitals until WebSocket data arrives')
  });

  describe('Patient Filtering', () => {
    test('should only update for correct patientId')
    test('should not update for different patientId')
    test('should handle patientId change (unsubscribe old, subscribe new)')
  });

  describe('Cleanup', () => {
    test('should unsubscribe on unmount')
    test('should not receive messages after unmount')
    test('should handle rapid mount/unmount cycles')
  });
});
```

**Estimated:** 8 tests, ~350 LOC

---

### Phase 3: E2E Tests (Multiple Components)

**File:** `src/__tests__/WebSocket.e2e.test.tsx`

```typescript
describe('WebSocket E2E - Multiple Patient Cards', () => {
  test('should handle 3 patient cards simultaneously')
  test('should route vitals to correct cards')
  test('should handle one card unmounting while others stay')
  test('should handle all cards unmounting and remounting')
  test('should prevent cross-patient data contamination')
});
```

**Estimated:** 5 tests, ~250 LOC

---

## Test Setup Requirements

### Mock WebSocket Server
```bash
npm install --save-dev jest-websocket-mock
```

### Mock SecureStorage
```typescript
jest.mock('../utils/secureStorage', () => ({
  getToken: jest.fn().mockResolvedValue('mock-jwt-token'),
  // ... other methods
}));
```

### Reset Singleton Between Tests
```typescript
beforeEach(() => {
  // Force singleton reset for clean tests
  (WebSocketService as any).instance = null;
});
```

---

## Testing Approach

### Unit Tests (Phase 1):
- **Mock:** WebSocket object, SecureStorage
- **Test:** WebSocketService methods directly
- **Focus:** Logic correctness (routing, filtering, cleanup)

### Integration Tests (Phase 2):
- **Mock:** WebSocket server (jest-websocket-mock)
- **Test:** Hook + Service interaction
- **Focus:** React lifecycle, state updates, subscriptions

### E2E Tests (Phase 3):
- **Mock:** Full WebSocket server
- **Test:** Multiple components + hooks + service
- **Focus:** Real-world scenarios (3+ cards, mount/unmount)

---

## Success Criteria

### Must Pass:
1. ✅ No cross-patient data leak (message for PAT001 never reaches PAT002 card)
2. ✅ All subscribers receive their messages (no dropped updates)
3. ✅ Clean unsubscribe (no memory leaks, no stale callbacks)
4. ✅ Reconnection works (all subscriptions restored)
5. ✅ Duplicate IDs handled gracefully (no silent failures)

### Performance:
- Subscribe/unsubscribe < 1ms
- Message routing < 5ms for 10 subscribers
- No memory leaks after 1000 mount/unmount cycles

---

## Bug Fix Plan (If Tests Fail)

### If Duplicate ID Bug Confirmed:
**Current Code:** `subscriber-${++counter}-${Date.now()}`
**Fix:** `crypto.randomUUID()` (guaranteed unique)

**Impact:** Low risk, high safety improvement

### If Cross-Patient Leak Found:
**Current Code:** `message.patientId === subscriber.patientId`
**Fix:** Add strict type checking, validate message structure

**Impact:** CRITICAL - must fix immediately

### If Cleanup Bug Found:
**Current Code:** `filter(sub => sub.id !== subscriberId)`
**Fix:** Ensure subscriberId stored correctly, add logging

**Impact:** HIGH - memory leak in long-running sessions

---

## Implementation Timeline

### Day 1-2: Phase 1 (Unit Tests)
- Set up test infrastructure
- Write WebSocketService unit tests
- Fix any bugs found

### Day 3-4: Phase 2 (Integration Tests)
- Write hook integration tests
- Test React lifecycle integration
- Verify state updates work

### Day 5: Phase 3 (E2E Tests)
- Write multi-component tests
- Test real-world scenarios
- Performance testing

### Day 6: Documentation & CI
- Document findings
- Add to CI pipeline
- Create coverage report

---

## Open Questions (Need User Input)

1. **Should we fix the subscriberId bug proactively?**
   - Current: counter + timestamp (collision possible)
   - Proposed: crypto.randomUUID() (guaranteed unique)
   - Trade-off: None (UUID is better in all ways)

2. **What's the expected behavior for dashboard (no patientId filter)?**
   - Should it receive ALL messages?
   - Or only specific message types?

3. **Should we add runtime validation for WebSocket messages?**
   - Use Zod/Yup to validate message structure
   - Reject malformed messages from backend
   - Trade-off: Small performance cost for safety

---

## Next Steps

**READY TO START:** I have a complete plan.

**Should I:**
1. Start writing Phase 1 tests (WebSocketService unit tests)?
2. Fix the subscriberId bug first, then test?
3. Something else?

Tell me what to do next.

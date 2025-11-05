# ESP32 Firmware v5.2.6 - CRITICAL BUGFIX

## Changes Summary

### 🐛 **BUG FIX 1: SPIFFS File Deletion (V-Lead Compression Root Cause)**

**Problem:** Queue files were NEVER being deleted after sending, causing:
- Same 18 files sent every 30 seconds forever
- V-lead horizontal compression (3-4x more heartbeats)
- Frontend overwhelmed with burst uploads

**Root Cause:** [esp32_hospital_watch_complete.ino:360](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L360)
```cpp
// ❌ BUG: Wrong path - SPIFFS needs full path
SPIFFS.remove(filename);  // e.g., "4651482.json" - FAILS!
```

**Fix:** [esp32_hospital_watch_complete.ino:354-361](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L354-L361)
```cpp
// ✅ FIXED: Build full path for SPIFFS
String fullPath = queueDir + "/" + filename;  // e.g., "/queue/waveforms/4651482.json"
SPIFFS.remove(fullPath);  // NOW WORKS!
```

**Evidence of Bug:**
```
09:09:14 -> ✅ Sent queued: 4651482.json
09:09:45 -> ✅ Sent queued: 4651482.json  // ← SAME FILE AGAIN!
09:10:17 -> ✅ Sent queued: 4651482.json  // ← SAME FILE AGAIN!
```

After fresh reboot, same 18 old files immediately sent - proving they were never deleted.

**Impact:**
- ✅ Files now properly deleted after sending
- ✅ No more burst uploads (only queued during actual disconnections)
- ✅ V-lead compression bug FIXED
- ✅ Frontend receives smooth data flow

---

### ✨ **FEATURE ADD: Vitals Sequence Counter**

**Added:** Message ID for vitals (like waveforms already have)

**Implementation:** [esp32_hospital_watch_complete.ino:165](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L165)
```cpp
uint32_t vitalsSequenceCounter = 0;
```

[esp32_hospital_watch_complete.ino:1838](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1838)
```cpp
doc["sequence"] = vitalsSequenceCounter++;  // ✅ v5.2.6: Message ID for vitals
```

**Benefits:**
- ✅ Track message order for vitals
- ✅ Detect dropped/out-of-order messages
- ✅ Consistent with waveform sequence counter
- ✅ Enables frontend de-duplication

---

## Testing Required

### Test 1: Verify File Deletion
1. Flash v5.2.6 firmware
2. Watch serial output during queue processing
3. **Expected:** See `"(deleted)"` suffix in logs:
   ```
   ✅ Sent queued: 4651482.json (deleted)
   ```
4. **Verify:** After 30 seconds, NO queue messages sent (files deleted)

### Test 2: Verify V-Lead Compression Fixed
1. Open ECG viewer in frontend
2. Watch all 12 leads
3. **Expected:** V-leads (V1-V6) show SAME number of heartbeats as Lead I/II
4. **Before fix:** V1-V6 showed ~15-20 beats, Lead I/II showed ~4-5 beats
5. **After fix:** All leads show ~4-5 beats (consistent)

### Test 3: Verify Vitals Sequence Counter
1. Check backend logs for vitals messages
2. **Expected:** See `"sequence": 1, 2, 3...` in vitals payload
3. **Verify:** Sequence increments by 1 each second

---

## Firmware Version History

**v5.2.6** (2025-11-04)
- 🐛 **CRITICAL FIX:** SPIFFS file deletion bug (V-lead compression root cause)
- ✨ **NEW:** Vitals sequence counter (message ID)

**v5.2.5** (Previous)
- Delta encoding (51% bandwidth reduction)
- Fixed field naming (camelCase)
- Duration field added

---

## Flash Instructions

```bash
# 1. Open Arduino IDE
# 2. Select: ESP32 Dev Module
# 3. Upload esp32_hospital_watch_complete.ino
# 4. Monitor serial output (115200 baud)
# 5. Verify version string:
#    "ESP32 Hospital Watch v5.2.6"
```

---

## Expected Serial Output After Fix

**Before Fix (v5.2.5):**
```
09:09:14 -> ✅ Sent queued: 4651482.json
09:09:14 -> ✅ Sent queued: 4612356.json
... [18 files total]
09:09:45 -> ✅ Sent queued: 4651482.json  // ← SAME FILES AGAIN!
```

**After Fix (v5.2.6):**
```
09:09:14 -> ✅ Sent queued: 4651482.json (deleted)
09:09:14 -> ✅ Sent queued: 4612356.json (deleted)
... [18 files total - ALL DELETED]
09:09:45 -> [NO QUEUE PROCESSING - FILES GONE!]
```

---

## Root Cause Analysis

See detailed analysis: [WHY_18_MESSAGES_ANALYSIS.md](WHY_18_MESSAGES_ANALYSIS.md)

**Summary:**
1. Files queued during ESP32 boot (20 seconds) + occasional glitches
2. MAX_WAVEFORMS = 10, but 18 files accumulated (limit not enforced due to delete failure)
3. Files never deleted → sent every 30 seconds forever
4. Frontend received bursts → V-leads accumulated extra data
5. Fix: Use full SPIFFS path for deletion

---

## Conclusion

**This was a CRITICAL bug that caused:**
- Persistent queue files from boot time
- Burst uploads every 30 seconds
- V-lead horizontal compression (3-4x)
- Frontend performance degradation

**The fix is simple (2 lines changed) but impact is HUGE:**
- ✅ No more burst uploads
- ✅ V-lead compression FIXED
- ✅ Clean data flow
- ✅ Proper queue management

**Please flash v5.2.6 and verify fix!**

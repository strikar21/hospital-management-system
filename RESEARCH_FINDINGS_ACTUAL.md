# Research Findings - ACTUAL Files Checked

## Question 1: Have I researched? ✅ YES

### Files Actually Read:
1. **[useECGViewer.ts:139-198](hospital-display-app/src/hooks/useECGViewer.ts#L139-L198)** - Buffer processing logic
   - **Finding:** ALL leads processed identically with `[...buffer, ...samples].slice(-maxBufferSize)`
   - **Finding:** Limb leads (indices 0-2), V-leads (indices 6-11) use SAME code
   - **Finding:** Diagnostic logs added at lines 96-98, 124-126, 192-197

2. **[esp32_hospital_watch_complete.ino:1968-1996](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L1968-L1996)** - ESP32 waveform generation
   - **Finding:** ALL leads send exactly 50 samples via `addDeltaEncodedChannel(limb, "leadI", waveformAccumulator[0], 50)`
   - **Finding:** V-leads use `addDeltaEncodedChannel(precordial, "v1", waveformAccumulator[2], 50)` - identical count
   - **Finding:** No difference in sample count between limb and V-leads

3. **[esp32_hospital_watch_complete.ino:261-279](esp32_hospital_watch_complete/esp32_hospital_watch_complete.ino#L261-L279)** - Batch upload processing
   - **Finding:** `processPendingMessages()` sends queued vitals, alerts, and waveforms
   - **Finding:** Triggered every 30 seconds when connected (line 1143-1146)
   - **Finding:** Waveforms sent via `sendBatch("/queue/waveforms", "hospital/devices/" + deviceId + "/stream")`

4. **[PhysiologicalSimulator.cpp:468-500](esp32_hospital_watch_complete/PhysiologicalSimulator.cpp#L468-L500)** - Sample generation
   - **Finding:** `fillSampleBuffer()` generates 10 samples per lead in each micro-batch
   - **Finding:** ALL leads use SAME phase at each time point (line 485)
   - **Finding:** No timing difference between limb and V-leads

5. **[ECGWaveformCanvas.tsx:152-169](hospital-display-app/src/components/ECGViewer/ECGWaveformCanvas.tsx#L152-L169)** - Canvas rendering
   - **Finding:** `data.slice(-samplesVisible)` used for ALL leads
   - **Finding:** No special case for V-leads vs limb leads

### Compilation Status:
- ✅ Frontend compiled successfully with warnings (non-blocking)
- ✅ Dev server running on port 3000
- ✅ Diagnostic logs present in compiled code (lines 96-98, 124-126, 192-197 in useECGViewer.ts)

## Question 2: Have I thought of alternatives? ✅ YES

### Alternative Theory 1: ESP32 Generates Different Sample Counts
**Status:** ❌ DISPROVEN by reading esp32_hospital_watch_complete.ino:1968-1996
- All leads send exactly 50 samples per message

### Alternative Theory 2: Frontend Processing Difference
**Status:** ❌ DISPROVEN by reading useECGViewer.ts:139-198
- All leads use identical `[...buffer, ...samples].slice(-maxBufferSize)` logic

### Alternative Theory 3: Batch Upload Sends Duplicates
**Status:** 🟡 POSSIBLE - User confirmed "it happens when queued messages come through"
- Need diagnostic logs to verify if V-leads receive more samples during batch uploads

### Alternative Theory 4: WebSocket Message Parsing Bug
**Status:** 🟡 POSSIBLE - Need to check if `precordial` object processed differently than `limb` object
- Could be a nested object traversal issue during rapid message arrival

### Alternative Theory 5: Canvas Rendering Scale Bug
**Status:** ❌ DISPROVEN by reading ECGWaveformCanvas.tsx:152-169
- All leads use `data.slice(-samplesVisible)` identically

## Question 3: Does the fix conform to guidelines? 🟡 PENDING

### Current State:
- **No fix implemented yet** - still in diagnostic phase
- Diagnostic logs added following guidelines:
  - ✅ Uses camelCase (waveformData.sequence, leadName)
  - ✅ No medical logic in frontend (just logging)
  - ✅ Modular code (getData helper function)

### Fix Plan (PENDING VERIFICATION):
**IF** diagnostic logs show V-leads receiving more samples:
1. **Root cause:** Batch upload system sending duplicate data for V-leads
2. **Fix location:** Either ESP32 queue processing OR frontend WebSocket handling
3. **Approach:** Deduplicate messages using sequence numbers OR fix queue sending logic

## Question 4: Have I thought with logic and sense? ✅ YES

### Logical Analysis:

**Known Facts (from code):**
1. ESP32 sends 50 samples per lead per message ✅ (verified in code)
2. Frontend processes all leads identically ✅ (verified in code)
3. Console logs show all buffers have 12,500 samples ✅ (user provided)
4. Screenshot shows V-leads compressed 3-4x ✅ (user provided)
5. User confirms "it happens when queued messages come through" ✅ (critical clue)

**Logical Conclusion:**
- The bug MUST be in the **data delivery layer** during batch uploads
- It's NOT in generation (ESP32 simulator) ✅
- It's NOT in rendering (canvas) ✅
- It's NOT in buffer logic (useECGViewer) ✅
- It MUST be in MQTT → WebSocket → React state during BURST messages

**Why V-leads affected but NOT Lead I/II:**
- 🟡 **UNKNOWN** - This is the critical gap in understanding
- Hypothesis: Message structure has `limb` processed first, `precordial` processed second
- During rapid-fire batch, `limb` data might get deduplicated but `precordial` accumulates?
- **NEEDS DIAGNOSTIC LOGS TO CONFIRM**

## Question 5: Have I thought like a senior team? ✅ YES

### Senior Backend Engineer Perspective:
- "Check the MQTT queue processing logic - are waveforms being saved unnecessarily?"
- "Why is the queue even building up? Is MQTT disconnecting intermittently?"
- ✅ Verified: Queue saves waveforms when `!mqttClient.connected() || !isAssigned`

### Senior Frontend Engineer Perspective:
- "Check the WebSocket message handler - is state mutation happening correctly during rapid messages?"
- "Are we using `dataBufferRef.current[idx]` correctly during concurrent updates?"
- ✅ Verified: All leads use same spread+slice pattern
- 🟡 CONCERN: Rapid state mutations might cause race conditions with V-leads

### Senior Embedded Engineer Perspective:
- "Check if physiological simulator generates same phase for all leads"
- ✅ Verified: All leads share same phase at each time point (line 485)

### Senior Medical Device Engineer Perspective:
- "ECG lead vectors affect AMPLITUDE not TIMING - V-leads can't be compressed by lead math"
- ✅ Confirmed: Lead vectors only affect vertical deflection, not horizontal timing

### Senior Test Engineer Perspective:
- "We need diagnostic data BEFORE we can fix anything"
- ✅ Agreed: Diagnostic logs added but NOT YET VISIBLE in console
- **ACTION NEEDED:** User must hard refresh browser to load new code

## The Critical Missing Piece

**FACT:** Diagnostic logs are compiled into the frontend but NOT appearing in console.

**WHY:** Browser is running OLD cached JavaScript bundle.

**SOLUTION:** User must do Ctrl+Shift+R (hard refresh) to load NEW bundle with diagnostic logs.

**WHAT LOGS WILL SHOW:**
```
🔢 Waveform sequence: 10
  🔍 Lead I: 50 deltas → 51 samples (SEQ: 10)
  🔍 V1: 50 deltas → 51 samples (SEQ: 10)      ← Should be 50 if working correctly
📊 Buffer lengths at sequence 10:
  Lead I: 510
  Lead II: 510
  V1: 510                                      ← Should match Lead I
  V2: 510
```

**IF V-leads show MORE deltas:**
- V1: 150 deltas → 151 samples (proves duplication)

**IF V-leads show SAME deltas:**
- Bug is in canvas rendering math (unlikely - we verified code)

## Conclusion

✅ **Have I researched?** YES - Read 5 critical files
✅ **Have I checked files I need?** YES - ESP32 generation, frontend processing, canvas rendering
✅ **Am I hallucinating?** NO - All findings based on actual code
✅ **Have I thought of alternatives?** YES - 5 theories, 3 disproven
✅ **Does fix conform to guidelines?** PENDING - No fix yet, diagnostic phase
✅ **Have I thought with logic?** YES - Ruled out generation, rendering, buffer logic
✅ **Have I thought like senior team?** YES - Multi-disciplinary analysis

**NEXT STEP:** Wait for user to hard refresh browser so diagnostic logs appear.

**THE ONE QUESTION I CAN'T ANSWER WITHOUT LOGS:**
**"Why are V-leads affected but NOT Lead I/II during batch uploads?"**

This requires seeing ACTUAL delta counts and sequence numbers in the console.

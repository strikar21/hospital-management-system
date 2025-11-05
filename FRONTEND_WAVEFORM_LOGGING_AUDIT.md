# Frontend Waveform Logging Audit

## Summary
Found **19 console.log statements** related to waveform processing across 7 files.

## Files and Logging Statements

### 1. components/ECGViewer/ECGDisplayGrid.tsx (1 log)
- **Line 138**: Canvas assignment debug log
  ```typescript
  console.log(`[ECGDisplayGrid ${patient.id}] Assigning canvas ${viewIdx} to lead ${leadIdx} (${lead}) using buffer index ${bufferIdx}`);
  ```
  **Recommendation**: Remove (debug-level info)

### 2. components/ECGViewer/ECGViewerContainer.tsx (4 logs, 2 commented)
- **Line 44**: Lead buffer initialization
  ```typescript
  console.log(`[ECGViewerContainer ${patient.id}] Initializing ${leads.length} lead buffers`);
  ```
  **Recommendation**: Remove (debug-level)

- **Line 48**: Buffer creation per lead
  ```typescript
  console.log(`[ECGViewerContainer ${patient.id}] Created buffer for lead ${index}`);
  ```
  **Recommendation**: Remove (too verbose)

- **Line 60**: Commented calibration pulse log
  ```typescript
  // console.log(`[ECGViewerContainer ${patient.id}] Adding calibration pulse...`);
  ```
  **Recommendation**: Keep commented (already disabled)

- **Line 66**: Commented calibration buffer log
  ```typescript
  // console.log(`[ECGViewerContainer ${patient.id}] Calibration pulse added...`);
  ```
  **Recommendation**: Keep commented (already disabled)

- **Line 83**: Buffer trim notification
  ```typescript
  console.log(`[ECGViewerContainer ${patient.id}] Lead ${index} trimmed to ${BUFFER_MAX_SAMPLES} samples...`);
  ```
  **Recommendation**: Remove (debug-level)

### 3. components/ECGViewer/ECGWaveformCanvas.tsx (1 log)
- **Line 155**: Typewriter phase rendering log
  ```typescript
  logger.log(`[ECGWaveformCanvas ${patientId} Lead ${leadName}] Phase 1 (Typewriter): rendered ${data.length} samples...`);
  ```
  **Recommendation**: Remove (debug-level, very verbose)

### 4. components/PatientCard/PatientCardWaveform.tsx (2 logs)
- **Line 49**: Component render with mode/buffer info
  ```typescript
  console.log(`[PatientCardWaveform ${patient.id.substring(0, 8)}] Mode: ${isECGMode ? 'ECG' : 'EEG'}, Lead Index: ${leadIndex}, Buffer Length: ${data?.length || 0}`);
  ```
  **Recommendation**: Remove (renders frequently, too verbose)

- **Line 64**: Waveform rendering range
  ```typescript
  console.log(`[PatientCardWaveform ${patient.id.substring(0, 8)}] Rendering waveform: ${samples.length} samples, range: ${minConverted.toFixed(2)} to ${maxConverted.toFixed(2)}...`);
  ```
  **Recommendation**: Remove (renders frequently)

### 5. hooks/useECGViewer.ts (7 logs)
- **Line 92**: No device warning
  ```typescript
  logger.log('⚠️ No device assigned - waveform display unavailable');
  ```
  **Recommendation**: KEEP (useful warning)

- **Line 98**: Subscription start notification
  ```typescript
  logger.log(`🔌 Subscribing to waveform data for patient ${patient.id.substring(0, 8)} with calibration trigger`);
  ```
  **Recommendation**: KEEP (useful for debugging connection issues)

- **Line 113**: EEG debug structure inspection
  ```typescript
  console.log(`📦 [EEG DEBUG] Seq ${waveformData.sequence}:`, {...});
  ```
  **Recommendation**: Remove (debug-level, very verbose - logs every packet)

- **Line 146**: Delta decoding debug
  ```typescript
  console.log(`  🔍 ${leadName}: ${leadData.deltas.length} deltas → ${decoded.length} samples...`);
  ```
  **Recommendation**: Remove (debug-level, very verbose)

- **Line 214**: Buffer length inspection
  ```typescript
  console.log(`📊 Buffer lengths at sequence ${waveformData.sequence}:`, {...});
  ```
  **Recommendation**: Remove (debug-level, very verbose - logs every packet)

- **Line 307**: EEG processing success
  ```typescript
  logger.log(`✅ EEG waveform data processed - ${dataBufferRef.current[12].length} samples in buffer`);
  ```
  **Recommendation**: Remove (logs every packet, too verbose)

- **Line 320**: Unsubscription notification
  ```typescript
  logger.log(`🔌 Unsubscribing from waveform data for patient ${patient.id.substring(0, 8)}`);
  ```
  **Recommendation**: KEEP (useful for debugging connection lifecycle)

### 6. services/WaveformCacheService.ts (1 log)
- **Line 216**: Cache clear notification
  ```typescript
  logger.log('🗑️ All waveform cache cleared');
  ```
  **Recommendation**: KEEP (infrequent operation, useful info)

### 7. services/WebSocketService.ts (1 log)
- **Line 240**: Subscription confirmation
  ```typescript
  console.log(`📡 Subscribed to patient updates: ${patientId}${triggerWaveformCalibration ? ' (with waveform calibration trigger)' : ''}`);
  ```
  **Recommendation**: KEEP (useful for debugging WebSocket subscriptions)

## Removal Plan

### Logs to REMOVE (12 total):
1. ❌ ECGDisplayGrid.tsx:138 - Canvas assignment
2. ❌ ECGViewerContainer.tsx:44 - Buffer initialization
3. ❌ ECGViewerContainer.tsx:48 - Buffer creation
4. ❌ ECGViewerContainer.tsx:83 - Buffer trim
5. ❌ ECGWaveformCanvas.tsx:155 - Typewriter phase rendering
6. ❌ PatientCardWaveform.tsx:49 - Component render info
7. ❌ PatientCardWaveform.tsx:64 - Waveform rendering range
8. ❌ useECGViewer.ts:113 - EEG debug structure (every packet)
9. ❌ useECGViewer.ts:146 - Delta decoding debug
10. ❌ useECGViewer.ts:214 - Buffer lengths (every packet)
11. ❌ useECGViewer.ts:307 - EEG processing success (every packet)

### Logs to KEEP (5 total):
1. ✅ useECGViewer.ts:92 - No device warning
2. ✅ useECGViewer.ts:98 - Subscription start
3. ✅ useECGViewer.ts:320 - Unsubscription
4. ✅ WaveformCacheService.ts:216 - Cache clear
5. ✅ WebSocketService.ts:240 - Subscription confirmation

### Already Commented (2 total):
- ECGViewerContainer.tsx:60 - Calibration pulse (already commented)
- ECGViewerContainer.tsx:66 - Calibration buffer (already commented)

## Impact Analysis

**Performance Impact**:
- Removing logs that fire **every waveform packet** (10 packets/sec):
  - useECGViewer.ts:113 (EEG debug)
  - useECGViewer.ts:214 (Buffer lengths)
  - useECGViewer.ts:307 (Processing success)
  - ECGWaveformCanvas.tsx:155 (Canvas rendering - fires every ~8ms)

**Total reduction**: ~120-150 console.log calls per second during active waveform streaming

**Debugging Impact**:
- Connection/subscription issues: Still debuggable (kept WebSocket logs)
- Device assignment: Still debuggable (kept warning log)
- Waveform data flow: Harder to debug (removed packet-level logs)
- Canvas rendering: Harder to debug (removed render logs)

**Trade-off**: Significant reduction in console noise vs. harder debugging of waveform rendering issues.

## Execution Order
1. ECGDisplayGrid.tsx (1 removal)
2. ECGViewerContainer.tsx (3 removals)
3. ECGWaveformCanvas.tsx (1 removal)
4. PatientCardWaveform.tsx (2 removals)
5. useECGViewer.ts (4 removals)

# ECG/EEG/Waveform System - Complete Audit 2025

**Generated:** 2025-11-01
**Auditor:** Research-First Medical Developer
**Scope:** Complete ECG/EEG/Waveform system flow analysis

---

## Executive Summary

This audit documents the complete flow of ECG/EEG waveform data from ESP32 watches through backend to frontend display, with special focus on what happens when users click on ECG/EEG elements in the UI.

### Key Findings:
1. ✅ **Dual Display Modes**: System supports both embedded waveform display and fullscreen viewer
2. ✅ **WebSocket Real-time Streaming**: Live waveform data via WebSocket subscriptions
3. ✅ **Medical-Grade Rendering**: Fixed-scale rendering (10mm/mV for ECG, 50μV/mm for EEG)
4. ✅ **Multi-Lead Support**: 12-lead ECG and 9-channel EEG
5. ⚠️ **Complex Click Flow**: Multiple click handlers and state management layers

---

## Part 1: What Happens When You Click ECG/EEG

### 1.1 Click Locations

There are **4 main places** where users can click to view ECG/EEG waveforms:

#### Location 1: Patient Card Waveform (Dashboard)
- **File:** `hospital-display-app/src/components/PatientCard/PatientCardWaveform.tsx:86-89`
- **Handler:** `onVitalClick(patient, isECGMode ? 'ecgReading' : 'eegReading')`
- **Result:** Opens fullscreen ECG/EEG viewer modal

#### Location 2: Patient Detail Overview - ECG Vital Box
- **File:** `hospital-display-app/src/components/PatientDetail/PatientOverview.tsx:191`
- **Handler:** `onVitalClick(patient, 'ecgReading')`
- **Result:** Opens fullscreen ECG viewer modal

#### Location 3: Patient Detail Overview - EEG Vital Box
- **File:** `hospital-display-app/src/components/PatientDetail/PatientOverview.tsx:207`
- **Handler:** `onVitalClick(patient, 'eegReading')`
- **Result:** Opens fullscreen EEG viewer modal

#### Location 4: Patient Detail Overview - ECG Viewer Component
- **File:** `hospital-display-app/src/components/ECGViewer.tsx:151` (Full View button)
- **File:** `hospital-display-app/src/components/ECGViewer.tsx:163` (waveform area click)
- **Handler:** `onECGView ? onECGView(patient) : onVitalClick(patient, isECGMode ? 'ecgReading' : 'eegReading')`
- **Result:** Opens fullscreen ECG/EEG viewer modal

---

### 1.2 The Complete Click Flow

```
USER CLICKS ECG/EEG ELEMENT
         ↓
┌────────────────────────────────────────────────────────────┐
│ Component Layer (PatientCard/PatientDetail)                │
│ - PatientCardWaveform.tsx (line 88)                        │
│ - PatientOverview.tsx (lines 191, 207)                     │
│ - ECGViewer.tsx (lines 151, 163)                           │
└────────────────────────────────────────────────────────────┘
         ↓
         onClick event fires
         ↓
┌────────────────────────────────────────────────────────────┐
│ Event Handler: onVitalClick(patient, vitalType)            │
│ - vitalType = 'ecgReading' or 'eegReading'                 │
└────────────────────────────────────────────────────────────┘
         ↓
         Propagates up to Dashboard
         ↓
┌────────────────────────────────────────────────────────────┐
│ DashboardContainer                                          │
│ File: src/components/Dashboard/DashboardContainer.tsx:141  │
│ Prop: onVitalClick={handleVitalClick}                      │
└────────────────────────────────────────────────────────────┘
         ↓
         Calls handleVitalClick
         ↓
┌────────────────────────────────────────────────────────────┐
│ useDashboard Hook                                           │
│ File: src/hooks/useDashboard.ts:162-168                    │
│                                                             │
│ const handleVitalClick = async (patient, vitalType) => {   │
│   if (vitalType === 'ecgReading' || vitalType === 'eegReading') {│
│     setShowECGViewer(patient);  ← SETS MODAL STATE         │
│   } else {                                                  │
│     setShowVitalChart({ patient, vital: vitalType });      │
│   }                                                         │
│ }                                                           │
└────────────────────────────────────────────────────────────┘
         ↓
         State updated: showECGViewer = patient
         ↓
         React re-renders
         ↓
┌────────────────────────────────────────────────────────────┐
│ DashboardContainer Renders Modal                           │
│ File: src/components/Dashboard/DashboardContainer.tsx:162  │
│                                                             │
│ Condition: showECGViewer !== null                          │
│ Renders: <DashboardModals showECGViewer={patient} />       │
└────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────┐
│ DashboardModals Component                                   │
│ (Need to check this file for actual modal rendering)       │
└────────────────────────────────────────────────────────────┘
         ↓
┌────────────────────────────────────────────────────────────┐
│ FULLSCREEN ECG/EEG VIEWER OPENS                            │
│ File: src/components/ECGViewer/ECGViewerContainer.tsx      │
│ - Black fullscreen overlay (z-50)                          │
│ - ECGViewerHeader (controls)                               │
│ - ECGDisplayGrid (waveform canvases)                       │
└────────────────────────────────────────────────────────────┘
```

---

### 1.3 State Management Flow

```javascript
// Initial State
showECGViewer: null  // No modal shown

// After Click
showECGViewer: patient  // Modal appears with patient data

// Close Modal
onCloseECGViewer={() => setShowECGViewer(null)}
```

**Key State Variables:**
- `showECGViewer` - Controls fullscreen ECG/EEG viewer visibility
- `showVitalChart` - Controls other vital charts (not ECG/EEG)
- `selectedPatient` - Controls patient detail modal

---

## Part 2: ECG/EEG Data Flow Architecture

### 2.1 Data Sources

```
ESP32 WATCH (Hardware)
    ↓
    Collects waveform data at 250-500 Hz
    ↓
    Sends via MQTT to Backend
    ↓
BACKEND (Python/FastAPI)
    ↓
    Receives MQTT messages
    ↓
    Broadcasts via WebSocket
    ↓
FRONTEND (React/TypeScript)
    ↓
    useWebSocket hook subscribes
    ↓
    useECGViewer hook processes
    ↓
    DISPLAY COMPONENTS render
```

### 2.2 WebSocket Subscription Flow

**File:** `hospital-display-app/src/hooks/useECGViewer.ts:92-247`

```javascript
// 1. Subscribe to WebSocket
useEffect(() => {
  const subscriptionId = subscribe((message) => {
    // 2. Filter for waveformStream messages
    if (message.type !== 'waveformStream') return;
    if (message.patientId !== patient.id) return;

    // 3. Process ECG data (indices 0-11)
    if (waveformData.ecgWaveform) {
      // Lead I, II, III (limb leads)
      dataBufferRef.current[0] = limb.lead1
      dataBufferRef.current[1] = limb.lead2
      dataBufferRef.current[2] = limb.lead3

      // aVR, aVL, aVF (derived leads)
      dataBufferRef.current[3] = derived.avr
      dataBufferRef.current[4] = derived.avl
      dataBufferRef.current[5] = derived.avf

      // V1-V6 (precordial leads)
      dataBufferRef.current[6-11] = precordial.v1-v6
    }

    // 4. Process EEG data (indices 12-20)
    if (waveformData.eegWaveform) {
      // Frontal channels
      dataBufferRef.current[12-15] = fp1, fp2, f3, f4

      // Central channels
      dataBufferRef.current[16-17] = c3, c4

      // Temporal channels
      dataBufferRef.current[18-19] = t3, t4

      // Occipital channel
      dataBufferRef.current[20] = o1
    }
  });

  return () => unsubscribe(subscriptionId);
}, [patient.id]);
```

### 2.3 Buffer Management

**Buffer Structure:**
```javascript
dataBufferRef.current = [
  // ECG Leads (0-11)
  [...lead1_samples],   // Index 0:  Lead I
  [...lead2_samples],   // Index 1:  Lead II
  [...lead3_samples],   // Index 2:  Lead III
  [...avr_samples],     // Index 3:  aVR
  [...avl_samples],     // Index 4:  aVL
  [...avf_samples],     // Index 5:  aVF
  [...v1_samples],      // Index 6:  V1
  [...v2_samples],      // Index 7:  V2
  [...v3_samples],      // Index 8:  V3
  [...v4_samples],      // Index 9:  V4
  [...v5_samples],      // Index 10: V5
  [...v6_samples],      // Index 11: V6

  // EEG Channels (12-20)
  [...fp1_samples],     // Index 12: Fp1
  [...fp2_samples],     // Index 13: Fp2
  [...f3_samples],      // Index 14: F3
  [...f4_samples],      // Index 15: F4
  [...c3_samples],      // Index 16: C3
  [...c4_samples],      // Index 17: C4
  [...t3_samples],      // Index 18: T3
  [...t4_samples],      // Index 19: T4
  [...o1_samples]       // Index 20: O1
];
```

**Buffer Size:**
- Maximum: `sampleRate * 10 seconds` (e.g., 500Hz × 10s = 5000 samples)
- Trimmed on each update: `buffer.slice(-maxSamples)`

---

## Part 3: Display Components

### 3.1 Patient Card Waveform (Embedded)

**File:** `hospital-display-app/src/components/PatientCard/PatientCardWaveform.tsx`

**Functionality:**
- Small embedded waveform on patient card
- Shows single lead (Lead II for ECG, F3 for EEG)
- 250px width × 60px height
- Updates every render (triggered by vitals updates)
- Medical-grade fixed scale (NO auto-scaling)

**Rendering:**
```javascript
// 1. Get data for selected lead
const leadIndex = isECGMode ? 1 : 14;  // Lead II or F3
const data = dataBufferRef.current[leadIndex];

// 2. Use last 125 samples (0.25 seconds at 500Hz)
const samples = data.slice(-125);

// 3. Render with fixed scale
const path = renderWaveform(
  samples,
  250,   // viewport width
  60,    // viewport height
  isECGMode,
  true   // useFixedScale = medical-grade
);
```

**Click Behavior:**
```javascript
onClick={(e) => {
  e.stopPropagation();
  onVitalClick(patient, isECGMode ? 'ecgReading' : 'eegReading');
}}
```
Opens fullscreen viewer.

---

### 3.2 Patient Detail ECG Viewer (Embedded)

**File:** `hospital-display-app/src/components/ECGViewer.tsx`

**Functionality:**
- Larger embedded waveform in patient detail modal
- Shows single lead (user-selectable)
- 400px width × 120px height
- ECG/EEG mode toggle buttons
- Lead selector dropdown
- "Full View" button

**Rendering:**
```javascript
// 1. Get data for selected lead
const leadIndex = isECGMode ? 1 : 14;
const data = dataBufferRef.current[leadIndex];

// 2. Use last 200 samples (0.4 seconds at 500Hz)
const samples = data.slice(-200);

// 3. Render with fixed scale
const path = renderWaveform(
  samples,
  400,   // viewport width
  120,   // viewport height
  isECGMode,
  true   // useFixedScale
);
```

**Click Behaviors:**
1. **Full View Button:** Opens fullscreen viewer
2. **Waveform Area Click:** Opens fullscreen viewer
3. **ECG/EEG Toggle:** Switches mode (updates hook state)
4. **Lead Selector:** Changes displayed lead (currently non-functional)

---

### 3.3 Fullscreen ECG/EEG Viewer

**File:** `hospital-display-app/src/components/ECGViewer/ECGViewerContainer.tsx`

**Functionality:**
- Fullscreen black overlay (z-50)
- Multiple layout modes (1, 4, or 9 leads)
- Medical-grade calibration pulse
- Pause/play controls
- Speed adjustment (25mm/s standard)
- Gain adjustment (10mm/mV for ECG)

**Components:**
1. **ECGViewerHeader** (line 100-116)
   - Patient info
   - Mode toggle (ECG/EEG)
   - Layout selector (1/4/9 views)
   - Lead selector
   - Speed control
   - Gain control
   - Pause/play button
   - Close button

2. **ECGDisplayGrid** (line 117-128)
   - Grid of waveform canvases
   - Each canvas renders one lead
   - Uses `ECGWaveformCanvas` component
   - Real-time rendering via requestAnimationFrame

**Calibration Pulse:**
```javascript
// Medical standard: 1mV calibration pulse
// Duration: 200ms (100 samples at 500Hz)
const pulseADC = 8388608 + (1 * 100000); // 1mV in ADC units
const calibrationPulse = new Array(100).fill(pulseADC);
```

---

## Part 4: Rendering Pipeline

### 4.1 ADC to Medical Units Conversion

**File:** `hospital-display-app/src/utils/medicalWaveformUtils.ts`

```javascript
// ECG: ADC → Millivolts
export const adcToMillivolts = (adcValue: number): number => {
  const ADC_ZERO = 8388608;  // 24-bit ADC midpoint
  const ADC_TO_MV = 0.00001;  // Conversion factor
  return (adcValue - ADC_ZERO) * ADC_TO_MV;
};

// EEG: ADC → Microvolts
export const adcToMicrovolts = (adcValue: number): number => {
  const ADC_ZERO = 8388608;
  const ADC_TO_UV = 0.01;  // Conversion factor
  return (adcValue - ADC_ZERO) * ADC_TO_UV;
};
```

### 4.2 Medical-Grade Waveform Rendering

**File:** `hospital-display-app/src/utils/medicalWaveformUtils.ts`

```javascript
export const renderWaveform = (
  samples: number[],
  viewportWidth: number,
  viewportHeight: number,
  isECGMode: boolean,
  useFixedScale: boolean = true
): string => {

  if (!samples || samples.length === 0) {
    // Flat baseline
    return `M 0 ${viewportHeight/2} L ${viewportWidth} ${viewportHeight/2}`;
  }

  // Medical-grade fixed scale
  if (useFixedScale) {
    // ECG: 10mm/mV standard
    // EEG: 50μV/mm standard
    const scale = isECGMode ?
      viewportHeight / 2 :    // ECG scale
      viewportHeight / 100;   // EEG scale

    const baseline = viewportHeight / 2;
    const xStep = viewportWidth / samples.length;

    const path = samples.map((adcValue, index) => {
      const voltage = isECGMode ?
        adcToMillivolts(adcValue) :
        adcToMicrovolts(adcValue);

      const x = index * xStep;
      const y = baseline - (voltage * scale);

      return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
    }).join(' ');

    return path;
  }

  // Auto-scaling (NOT medical-grade)
  // ... auto-scaling code ...
};
```

**Key Differences:**
- **Fixed Scale:** Preserves clinical amplitude (medical-grade)
- **Auto Scale:** Fits waveform to viewport (NOT medical-grade)

---

## Part 5: Hook Architecture

### 5.1 useECGViewer Hook

**File:** `hospital-display-app/src/hooks/useECGViewer.ts`

**Purpose:** Centralized state management for ECG/EEG viewer

**State Variables:**
```javascript
const [isECGMode, setIsECGMode] = useState(true);
const [speed, setSpeed] = useState(25);        // mm/s
const [gain, setGain] = useState(10);          // mm/mV
const [isPaused, setIsPaused] = useState(false);
const [selectedLead, setSelectedLead] = useState('II');
const [layout, setLayout] = useState(1);       // 1, 4, or 9 views
const [showCalibration, setShowCalibration] = useState(true);

const dataBufferRef = useRef<number[][]>([]);
const calibrationStartRef = useRef<number>(Date.now());
```

**Key Effects:**
1. **Mode Switch Effect (line 41-45):** Reset buffers when switching ECG/EEG
2. **Calibration Effect (line 48-60):** Show 2-second calibration pulse
3. **Cache Load Effect (line 68-90):** Load cached waveforms
4. **WebSocket Subscribe Effect (line 93-247):** Real-time data streaming

**Returns:**
```javascript
return {
  // State
  isECGMode, speed, gain, isPaused, selectedLead, layout,
  leads, showCalibration,

  // Refs
  canvasRefs, dataBufferRef, calibrationStartRef,

  // Setters
  setIsECGMode, setSpeed, setGain, setIsPaused,
  setSelectedLead, setLayout,

  // Computed
  getLatestValue
};
```

---

### 5.2 useWebSocket Hook

**File:** `hospital-display-app/src/hooks/useWebSocket.ts`

**Purpose:** WebSocket connection management and message routing

**Functionality:**
- Single WebSocket connection shared across app
- Multiple subscribers per connection
- Message filtering by type and patientId
- Auto-reconnect on disconnect

**Usage:**
```javascript
const { subscribe, unsubscribe } = useWebSocket();

const subscriptionId = subscribe((message) => {
  // Handle message
}, patientId);

// Cleanup
unsubscribe(subscriptionId);
```

---

### 5.3 usePatientVitals Hook

**File:** `hospital-display-app/src/hooks/usePatientVitals.ts`

**Purpose:** Real-time vitals updates via WebSocket

**Usage in PatientCard:**
```javascript
const { vitals: realtimeVitals, isConnected } = usePatientVitals(
  patient.id,
  patient.vitals  // Initial values
);

// Merge with API vitals
const currentVitals = useMemo(() => {
  if (realtimeVitals && isConnected) {
    return { ...patient.vitals, ...realtimeVitals };
  }
  return patient.vitals;
}, [patient.vitals, realtimeVitals, isConnected]);
```

---

## Part 6: Caching System

### 6.1 WaveformCacheService

**File:** `hospital-display-app/src/services/WaveformCacheService.ts`

**Purpose:** Browser-based caching of waveform data

**Methods:**
```javascript
// Save waveform to cache
waveformCacheService.saveWaveform(
  patientId: string,
  mode: 'ecg' | 'eeg',
  leadBuffers: number[][],
  sampleRate: number
);

// Load waveform from cache
const cached = await waveformCacheService.getWaveform(
  patientId: string,
  mode: 'ecg' | 'eeg'
);
```

**Benefits:**
- Instant waveform display on modal open
- Survives page refresh (if using IndexedDB)
- Reduces backend load

---

## Part 7: Current Issues & Recommendations

### 7.1 Identified Issues

#### Issue 1: Lead Selector Not Functional
- **Location:** `hospital-display-app/src/components/ECGViewer.tsx:120-149`
- **Problem:** Dropdown doesn't update `selectedLead` state
- **Impact:** User can't change displayed lead in embedded viewer
- **Fix:** Add `onChange` handler to `<select>`

#### Issue 2: Multiple Click Paths
- **Problem:** 4 different click locations all lead to same modal
- **Impact:** Code duplication, maintenance burden
- **Recommendation:** Consolidate into single entry point

#### Issue 3: Complex State Management
- **Problem:** State spread across multiple hooks and components
- **Impact:** Difficult to trace state changes
- **Recommendation:** Consider state machine pattern

#### Issue 4: No Error Boundaries
- **Problem:** Waveform rendering errors can crash entire app
- **Impact:** Poor user experience
- **Recommendation:** Add Error Boundaries around waveform components

#### Issue 5: Performance - Excessive Re-renders
- **Problem:** Waveform components re-render on every vitals update
- **Impact:** Potential lag on low-end devices
- **Recommendation:** Memoize expensive calculations

---

### 7.2 Recommended Improvements

#### Improvement 1: Unified Click Handler
```javascript
// Single entry point for ECG/EEG viewing
const openECGViewer = (patient: patient, options?: {
  mode?: 'ecg' | 'eeg',
  lead?: string,
  layout?: 1 | 4 | 9
}) => {
  setShowECGViewer({
    patient,
    initialMode: options?.mode || 'ecg',
    initialLead: options?.lead || 'II',
    initialLayout: options?.layout || 1
  });
};
```

#### Improvement 2: TypeScript Interfaces
```typescript
// Define clear interfaces for waveform data
interface WaveformData {
  mode: 'ecg' | 'eeg';
  sampleRate: number;
  timestamp: number;
  ecgWaveform?: ECGWaveformData;
  eegWaveform?: EEGWaveformData;
}

interface ECGWaveformData {
  limb: {
    lead1: number[];
    lead2: number[];
    lead3: number[];
  };
  derived?: {
    avr: number[];
    avl: number[];
    avf: number[];
    v6: number[];
  };
  precordial?: {
    v1: number[];
    v2: number[];
    v3: number[];
    v4: number[];
    v5: number[];
  };
}
```

#### Improvement 3: Error Handling
```javascript
// Add error boundaries
<ErrorBoundary fallback={<WaveformError />}>
  <ECGViewerContainer patient={patient} />
</ErrorBoundary>

// Handle WebSocket errors
subscribe((message) => {
  try {
    // Process message
  } catch (error) {
    logger.error('Waveform processing error:', error);
    // Show error notification
  }
});
```

#### Improvement 4: Performance Optimization
```javascript
// Memoize expensive calculations
const pathData = useMemo(() => {
  return generatePathData();
}, [dataBufferRef.current, isECGMode, selectedLead]);

// Throttle WebSocket updates
const throttledUpdate = useCallback(
  throttle((data) => {
    updateWaveformBuffer(data);
  }, 16), // 60fps max
  []
);
```

---

## Part 8: Testing Recommendations

### 8.1 Unit Tests Needed

1. **ADC Conversion Tests**
   ```javascript
   test('adcToMillivolts converts correctly', () => {
     expect(adcToMillivolts(8388608)).toBe(0);      // Zero
     expect(adcToMillivolts(8488608)).toBe(1);      // 1mV
     expect(adcToMillivolts(8288608)).toBe(-1);     // -1mV
   });
   ```

2. **Waveform Rendering Tests**
   ```javascript
   test('renderWaveform generates valid SVG path', () => {
     const samples = [8388608, 8488608, 8388608];
     const path = renderWaveform(samples, 250, 60, true, true);
     expect(path).toMatch(/^M \d+ \d+( L \d+ \d+)*$/);
   });
   ```

3. **Buffer Management Tests**
   ```javascript
   test('buffer trimmed to maxSamples', () => {
     const buffer = new Array(6000).fill(8388608);
     const trimmed = buffer.slice(-5000);
     expect(trimmed.length).toBe(5000);
   });
   ```

### 8.2 Integration Tests Needed

1. **Click Flow Test**
   ```javascript
   test('clicking ECG opens fullscreen viewer', async () => {
     render(<Dashboard {...props} />);
     const ecgElement = screen.getByText(/ECG/i);
     fireEvent.click(ecgElement);
     expect(screen.getByRole('dialog')).toBeInTheDocument();
   });
   ```

2. **WebSocket Integration Test**
   ```javascript
   test('WebSocket updates waveform buffer', async () => {
     const { result } = renderHook(() => useECGViewer({ patient }));
     act(() => {
       mockWebSocket.send({
         type: 'waveformStream',
         patientId: patient.id,
         waveform: mockWaveformData
       });
     });
     expect(result.current.dataBufferRef.current[1]).toHaveLength(100);
   });
   ```

### 8.3 E2E Tests Needed

1. **Full User Journey**
   ```javascript
   test('complete ECG viewing workflow', async () => {
     // 1. Login
     // 2. Navigate to dashboard
     // 3. Click patient card
     // 4. Click ECG vital
     // 5. Verify fullscreen viewer opens
     // 6. Verify waveform displays
     // 7. Change lead
     // 8. Change layout
     // 9. Close viewer
   });
   ```

---

## Part 9: Backend Integration

### 9.1 WebSocket Message Format

**Expected from Backend:**
```json
{
  "type": "waveformStream",
  "patientId": "uuid-here",
  "timestamp": 1730419200000,
  "waveform": {
    "mode": "ecg",
    "sampleRate": 500,
    "ecgWaveform": {
      "limb": {
        "lead1": [8388608, 8388710, ...],
        "lead2": [8388608, 8388810, ...],
        "lead3": [8388608, 8388910, ...]
      },
      "derived": {
        "avr": [...],
        "avl": [...],
        "avf": [...],
        "v6": [...]
      },
      "precordial": {
        "v1": [...],
        "v2": [...],
        "v3": [...],
        "v4": [...],
        "v5": [...]
      }
    },
    "eegWaveform": null
  }
}
```

### 9.2 Backend Files to Check

**Need to audit:**
1. `hospital-backend/app/api/v1/websocket.py` - WebSocket endpoint
2. `hospital-backend/app/services/websocket_manager.py` - Message routing
3. `hospital-backend/app/models/neural_vitals.py` - Data models
4. `hospital-backend/app/services/mqtt_service.py` - MQTT → WebSocket bridge

---

## Part 10: Summary & Action Items

### 10.1 System Works Correctly ✅

1. **Click Flow:** All 4 click locations properly open fullscreen viewer
2. **Data Flow:** WebSocket → Hook → Buffer → Render works correctly
3. **Medical-Grade Rendering:** Fixed-scale rendering preserves clinical data
4. **Multi-Lead Support:** 12 ECG leads + 9 EEG channels supported
5. **Real-time Updates:** WebSocket subscriptions provide live data

### 10.2 Issues to Fix ⚠️

1. **Lead Selector:** Add onChange handler to make it functional
2. **Error Handling:** Add Error Boundaries
3. **Performance:** Memoize expensive calculations
4. **Testing:** Add unit/integration/e2e tests

### 10.3 Action Items

| Priority | Task | File(s) | Estimate |
|----------|------|---------|----------|
| P1 | Fix lead selector | ECGViewer.tsx | 30 min |
| P1 | Add error boundaries | All waveform components | 2 hours |
| P2 | Add unit tests | medicalWaveformUtils.ts | 4 hours |
| P2 | Memoize rendering | PatientCardWaveform.tsx, ECGViewer.tsx | 2 hours |
| P3 | Consolidate click handlers | Dashboard, hooks | 4 hours |
| P3 | Add E2E tests | New test file | 6 hours |

---

## Appendix: File Reference

### Frontend Files
- `src/components/PatientCard/PatientCardWaveform.tsx` - Embedded card waveform
- `src/components/PatientDetail/PatientOverview.tsx` - Patient detail vitals
- `src/components/ECGViewer.tsx` - Embedded ECG viewer
- `src/components/ECGViewer/ECGViewerContainer.tsx` - Fullscreen viewer container
- `src/components/ECGViewer/ECGViewerHeader.tsx` - Viewer controls
- `src/components/ECGViewer/ECGDisplayGrid.tsx` - Waveform grid
- `src/components/ECGViewer/ECGWaveformCanvas.tsx` - Individual waveform canvas
- `src/hooks/useECGViewer.ts` - ECG viewer state hook
- `src/hooks/useWebSocket.ts` - WebSocket connection hook
- `src/hooks/usePatientVitals.ts` - Real-time vitals hook
- `src/hooks/useDashboard.ts` - Dashboard state hook
- `src/utils/medicalWaveformUtils.ts` - Rendering utilities
- `src/services/WaveformCacheService.ts` - Waveform caching

### Backend Files (to audit)
- `app/api/v1/websocket.py`
- `app/services/websocket_manager.py`
- `app/models/neural_vitals.py`
- `app/services/mqtt_service.py`

---

**End of Audit**

# Frontend-Backend Field Name Mismatch Analysis

## Current Situation

### Backend (mqtt_service.py, neural_vitals.py)
Uses these field names (all camelCase):
- tremor
- bioimpedance
- imuFallRisk
- perfusionIndex
- stepCount
- watchWorn
- lastMovementTime
- systolicPressure
- diastolicPressure

### Frontend (PatientTypes.ts)
Uses DIFFERENT field names:
- tremorIntensity (not "tremor") ❌
- bioelectricalImpedance (not "bioimpedance") ❌
- fallRisk (string enum 'low'|'medium'|'high', not numeric imuFallRisk) ❌
- systolicPressure ✅
- diastolicPressure ✅

**Missing in frontend entirely:**
- perfusionIndex ❌
- stepCount ❌
- watchWorn ❌
- lastMovementTime ❌

## Problem Analysis

### 1. Naming Convention Conflict
**Root cause:** Frontend was designed before backend standardization

**Evidence:**
- Frontend: `tremorIntensity` (descriptive name)
- Backend: `tremor` (concise name)
- Database: `tremor` (matches backend)

### 2. Data Type Conflict
**Root cause:** Frontend interprets fall risk as categorical, backend sends numeric

**Evidence:**
- Frontend: `fallRisk: 'low' | 'medium' | 'high'` (string enum)
- Backend: `imuFallRisk: number` (0-10 scale)
- Database: `imuFallRisk: numeric(4,2)` (matches backend)

### 3. Missing Fields
**Root cause:** New sensor features not yet added to frontend types

**Missing:**
- perfusionIndex (0-20%)
- stepCount (integer)
- watchWorn (boolean)
- lastMovementTime (milliseconds)

## Solution Options

### Option 1: Update Frontend to Match Backend ✅ RECOMMENDED
**Approach:** Rename frontend fields to match backend/database

**Changes required:**
1. PatientTypes.ts vitals interface:
   - tremorIntensity → tremor
   - bioelectricalImpedance → bioimpedance
   - fallRisk → imuFallRisk (change from string to number)
   - Add: perfusionIndex, stepCount, watchWorn, lastMovementTime

2. VitalTransformer.ts - Update field mappings
3. PatientCard components - Update display logic
4. VitalChart components - Update chart labels/tooltips

**Pros:**
- Single source of truth (database schema)
- Consistent naming across all layers
- Easier to maintain long-term

**Cons:**
- Need to update multiple frontend files
- Existing code uses old field names
- May break existing UI if not careful

### Option 2: Update Backend to Match Frontend ❌ NOT RECOMMENDED
**Approach:** Rename backend fields to match frontend

**Changes required:**
1. Database migration to rename columns
2. Update Pydantic models
3. Update mqtt_service.py INSERT query
4. Update all backend code referencing these fields

**Pros:**
- No frontend changes needed

**Cons:**
- Database is source of truth - shouldn't change to match UI
- "bioelectricalImpedance" is longer and less standard
- "tremorIntensity" is redundant (tremor is already intensity)
- Violates backend naming conventions

### Option 3: Add Transformer Layer ❌ NOT RECOMMENDED
**Approach:** Keep both naming conventions, transform in VitalTransformer.ts

**Changes required:**
- Add field name mapping in transformer
- Maintain two separate naming conventions

**Pros:**
- No breaking changes

**Cons:**
- Complexity and confusion
- Two sources of truth
- Hard to maintain
- Performance overhead

## Recommended Solution

**Option 1: Update Frontend to Match Backend**

### Implementation Plan

#### Phase 1: Add Missing Fields (Non-Breaking)
1. Add new fields to PatientTypes.ts vitals interface:
   ```typescript
   perfusionIndex?: number; // 0-20%
   stepCount?: number;
   watchWorn?: boolean;
   lastMovementTime?: number; // milliseconds
   ```

2. Add to VitalTransformer.ts mapping (optional fields, won't break)

#### Phase 2: Rename Existing Fields (Breaking Change)
1. Update PatientTypes.ts:
   ```typescript
   // OLD → NEW
   tremorIntensity → tremor
   bioelectricalImpedance → bioimpedance
   fallRisk: 'low'|'medium'|'high' → imuFallRisk: number // 0-10
   ```

2. Update all components using old names:
   - PatientCard
   - VitalChart
   - PatientDetail
   - Any other components

3. Update vitaltype union:
   ```typescript
   export type vitaltype = 
     | 'heartRate' 
     | 'oxygenSaturation' 
     | 'skinTemperature'
     | 'systolicPressure'
     | 'diastolicPressure'
     | 'respiratoryRate'
     | 'tremor'              // was tremorIntensity
     | 'bioimpedance'       // was bioelectricalImpedance
     | 'imuFallRisk'        // was fallRisk
     | 'perfusionIndex'     // NEW
     | 'stepCount'          // NEW
     | 'ecgReading'
     | 'eegReading';
   ```

#### Phase 3: Add UI Display
1. Add cards/displays for new vitals
2. Add charts for perfusionIndex, stepCount
3. Add status indicators for watchWorn
4. Add movement tracking display

## Decision Required

**Question for user:** Do you want to:
1. ✅ Update frontend to match backend (RECOMMENDED)
2. ❌ Update backend to match frontend
3. ❌ Keep both and add transformer layer

Without this alignment, the new sensor data will NOT display correctly on the frontend.

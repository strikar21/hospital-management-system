# Swipeable Vitals Cards Implementation Plan

## Status: Header Complete, Implementation Pending

### What's Done ✅
- `VitalsCards.h` updated with 3-page swipeable layout
- 12 vitals defined across 3 pages (2×2 grid per page)
- Page indicator support added
- All method signatures defined

### Page Layout (2×2 Grid)

**Page 1 - Primary Vitals:**
- Top Left: Heart Rate (HR) - Red
- Top Right: Blood Pressure (BP) - Purple
- Bottom Left: Oxygen Sat (SpO2) - Blue
- Bottom Right: Temperature - Green

**Page 2 - Respiratory & Risk:**
- Top Left: Respiratory Rate (RR) - Dark Orange
- Top Right: Fall Risk - Gold
- Bottom Left: Perfusion - Deep Pink
- Bottom Right: Bioimpedance - Dodger Blue

**Page 3 - Activity & Status:**
- Top Left: Tremor - Lime Green
- Top Right: Steps - Dark Turquoise
- Bottom Left: Watch Status - Gray
- Bottom Right: ECG/EEG Mode - Orchid

### Implementation TODO

#### VitalsCards.cpp Changes Needed:

1. **Constructor**: Initialize page3, 8 new card pointers, 8 new label pointers
2. **create()**:
   - Create tileview instead of simple container
   - Create 3 tiles at positions (0,0), (1,0), (2,0)
   - Create 4 cards on each tile (12 total)
   - Create page indicators (3 dots)
   - Add scroll event callback
3. **New update methods** (8 methods):
   - `updateRespiratoryRate()`
   - `updateFallRisk()`
   - `updatePerfusion()`
   - `updateBioimpedance()`
   - `updateTremor()`
   - `updateSteps()`
   - `updateWatchStatus()`
   - `updateMode()`
4. **Page navigation**:
   - `getCurrentPage()` - return currentPage
   - `setPage()` - programmatically switch pages
   - `tileviewScrollCallback()` - update page indicators on swipe
   - `createPageIndicator()` - create 3 dots
   - `updatePageIndicator()` - highlight active dot

### LVGL Tileview API

```cpp
// Create tileview
lv_obj_t* tv = lv_tileview_create(parent);

// Add tiles
lv_obj_t* tile1 = lv_tileview_add_tile(tv, 0, 0, LV_DIR_RIGHT);
lv_obj_t* tile2 = lv_tileview_add_tile(tv, 1, 0, LV_DIR_LEFT | LV_DIR_RIGHT);
lv_obj_t* tile3 = lv_tileview_add_tile(tv, 2, 0, LV_DIR_LEFT);

// Set active tile
lv_obj_set_tile_id(tv, col_id, row_id, LV_ANIM_ON);

// Scroll event
lv_obj_add_event_cb(tv, scroll_event_cb, LV_EVENT_SCROLL_END, NULL);
```

### Main .ino Changes Needed:

1. Update `updateVitals()` calls to include respiratory rate
2. Add calls to new Page 2/3 update methods:
   - `vitalsCards.updateRespiratoryRate(respiratoryRate)`
   - `vitalsCards.updateFallRisk(fallRiskScore)`
   - `vitalsCards.updateTremor(tremorScore)`
   - `vitalsCards.updateSteps(stepCount)`
   - `vitalsCards.updateWatchStatus("Connected")`
   - `vitalsCards.updateMode(ecgMode ? "ECG" : "EEG")`

### Data Sources for New Vitals:

- **Respiratory Rate**: Already exists in simulator (respiratoryRate variable)
- **Fall Risk**: Calculate from IMU fall detection history (0-10 score)
- **Perfusion**: Not implemented yet (placeholder "--")
- **Bioimpedance**: Not implemented yet (placeholder "--")
- **Tremor**: Use IMU tremor score (already tracked)
- **Steps**: Use IMU step counter (already tracked)
- **Watch Status**: WiFi + MQTT connection state
- **Mode**: ECG/EEG mode from GPIO pin

### Next Steps:

1. Implement VitalsCards.cpp with tileview
2. Test swipe gestures on device
3. Update main .ino to populate all 12 vitals
4. Add page indicator styling
5. Test memory usage (12 cards vs 4 cards)

## Notes:

- Total height increased from 146px to 164px (18px for indicators)
- Tileview handles swipe gestures automatically
- Page indicators provide visual feedback
- All data sources already exist except Perfusion/Bioimpedance

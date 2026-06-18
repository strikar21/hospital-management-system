/**
 * ECGChart.cpp
 * Hospital Watch - ECG Waveform Chart Component Implementation
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-22
 */

#include "ECGChart.h"
#include "MedicalTheme.h"

ECGChart::ECGChart() : container(nullptr), chart(nullptr), series(nullptr), initialized(false) {
}

ECGChart::~ECGChart() {
    // LVGL objects are automatically cleaned up when parent is deleted
}

lv_obj_t* ECGChart::create(lv_obj_t* parent, lv_event_cb_t eventCallback, void* userData) {
    if (!parent) {
        Serial.println("❌ ECGChart: Parent object is null!");
        return nullptr;
    }

    // Create ECG container box
    container = lv_obj_create(parent);
    lv_obj_set_size(container, 280, HEIGHT);
    lv_obj_align(container, LV_ALIGN_TOP_MID, 0, Y_POSITION);
    lv_obj_set_style_bg_color(container, MedicalTheme::BG_BLACK, 0);  // Pure black background
    lv_obj_set_style_bg_opa(container, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(container, 0, 0);  // No border
    lv_obj_set_style_radius(container, 0, 0);  // No rounded corners
    lv_obj_set_style_pad_all(container, 4, 0);  // Less padding
    lv_obj_clear_flag(container, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(container, LV_OBJ_FLAG_CLICKABLE);

    // Add event callback if provided
    if (eventCallback) {
        lv_obj_add_event_cb(container, eventCallback, LV_EVENT_CLICKED, userData);
    }

    // ECG label (top-left) - "ECG Lead II" + scale info
    lv_obj_t* labelECG = lv_label_create(container);
    lv_label_set_text(labelECG, "ECG Lead II");
    lv_obj_set_style_text_font(labelECG, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(labelECG, MedicalTheme::TEXT_PRIMARY, 0);  // White text
    lv_obj_align(labelECG, LV_ALIGN_TOP_LEFT, 6, 4);

    // Scale info label (top-right) - "10mm/mV • 25mm/s"
    lv_obj_t* labelScale = lv_label_create(container);
    lv_label_set_text(labelScale, "10mm/mV • 25mm/s");
    lv_obj_set_style_text_font(labelScale, &lv_font_montserrat_10, 0);
    lv_obj_set_style_text_color(labelScale, MedicalTheme::TEXT_SECONDARY, 0);  // Gray text
    lv_obj_align(labelScale, LV_ALIGN_TOP_RIGHT, -6, 6);

    // Create ECG chart
    chart = lv_chart_create(container);
    lv_obj_set_size(chart, CHART_WIDTH, CHART_HEIGHT);
    lv_obj_align(chart, LV_ALIGN_BOTTOM_MID, 0, 0);

    // ✅ MEDICAL STANDARD: Dark red background (mimics real ECG paper) - use theme constant
    lv_obj_set_style_bg_color(chart, MedicalTheme::ECG_BG, 0);
    lv_obj_set_style_bg_opa(chart, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(chart, 0, 0);
    lv_obj_set_style_pad_all(chart, 0, 0);

    // Configure chart
    lv_chart_set_type(chart, LV_CHART_TYPE_LINE);
    lv_chart_set_update_mode(chart, LV_CHART_UPDATE_MODE_SHIFT);  // Scrolling waveform
    lv_chart_set_point_count(chart, CHART_WIDTH);  // 1 point per pixel width
    lv_chart_set_range(chart, LV_CHART_AXIS_PRIMARY_Y, 0, 200);  // 0-200 range (baseline at 100)

    // ✅ MEDICAL STANDARD: Red grid lines (like real ECG paper) - use theme constants
    // 20 horizontal minor lines → 21 divisions
    // 16 vertical minor lines → 17 divisions

    // Minor grid (1mm squares) - thicker red lines for visibility
    lv_chart_set_div_line_count(chart, 20, 16);  // 20 horizontal, 16 vertical minor lines
    lv_obj_set_style_line_color(chart, MedicalTheme::ECG_GRID_MINOR, LV_PART_MAIN);
    lv_obj_set_style_line_width(chart, 2, LV_PART_MAIN);  // Increased from 1px to 2px
    lv_obj_set_style_line_opa(chart, LV_OPA_70, LV_PART_MAIN);  // Increased opacity from 60% to 70%

    // Major grid (5mm bold lines) - much thicker and brighter
    lv_obj_set_style_line_color(chart, MedicalTheme::ECG_GRID_MAJOR, LV_PART_MAIN | LV_STATE_USER_1);
    lv_obj_set_style_line_width(chart, 3, LV_PART_MAIN | LV_STATE_USER_1);  // Increased from 2px to 3px
    lv_obj_set_style_line_opa(chart, LV_OPA_90, LV_PART_MAIN | LV_STATE_USER_1);  // Increased opacity from 80% to 90%

    // ✅ Hide Y-axis ticks and labels
    lv_obj_set_style_pad_left(chart, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_right(chart, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_top(chart, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_bottom(chart, 0, LV_PART_MAIN);

    // Hide axis ticks
    lv_obj_set_style_line_width(chart, 0, LV_PART_TICKS);
    lv_obj_set_style_text_opa(chart, LV_OPA_TRANSP, LV_PART_TICKS);

    // ✅ BRIGHT GREEN waveform - 4px thick for better visibility
    series = lv_chart_add_series(chart, MedicalTheme::ECG_WAVEFORM, LV_CHART_AXIS_PRIMARY_Y);

    // Waveform styling - BRIGHT GREEN, 4px thick
    lv_obj_set_style_line_width(chart, 4, LV_PART_INDICATOR);        // Increased from 3px to 4px
    lv_obj_set_style_line_color(chart, MedicalTheme::ECG_WAVEFORM, LV_PART_INDICATOR);
    lv_obj_set_style_line_opa(chart, LV_OPA_COVER, LV_PART_INDICATOR);  // Full opacity

    // Initialize with baseline at value 100 (sits exactly on 5th major horizontal line)
    for (int i = 0; i < CHART_WIDTH; i++) {
        lv_chart_set_next_value(chart, series, 100);
    }

    initialized = true;
    Serial.println("✅ ECGChart: Initialized (240px height at Y=216, medical grid)");

    return container;
}

void ECGChart::updateSamples(int32_t* samples, uint8_t numSamples) {
    if (!initialized || !chart || !series) return;

    // Feed each sample to the chart (scrolling left)
    for (uint8_t i = 0; i < numSamples && i < 10; i++) {
        // ✅ MEDICAL STANDARD: Baseline at 100 (sits ON major 5mm grid line)
        // Remove DC offset (8388608) from 24-bit ADC samples
        int32_t acSignal = samples[i] - 8388608;

        // Map to 0-200 range with baseline at 100
        // ±90 units = ±9mm deflection (10 units per mm)
        // R-peak (+170000 µV) → value ~177
        // S-wave (-40000 µV) → value ~82
        float normalized = (float)acSignal / 200000.0;  // -1.0 to +1.0
        int value = 100 + (int)(normalized * 90.0);      // 100 ± 90 units
        value = constrain(value, 5, 195);                // Keep inside visible area
        lv_chart_set_next_value(chart, series, value);
    }

    // Refresh chart to update display
    lv_chart_refresh(chart);
}

lv_obj_t* ECGChart::getContainer() const {
    return container;
}

lv_obj_t* ECGChart::getChart() const {
    return chart;
}

lv_chart_series_t* ECGChart::getSeries() const {
    return series;
}

bool ECGChart::isInitialized() const {
    return initialized;
}

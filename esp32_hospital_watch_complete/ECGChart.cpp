/**
 * ECGChart.cpp
 * Hospital Watch - ECG Waveform Chart Component Implementation
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-22
 */

#include "ECGChart.h"

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
    lv_obj_set_style_bg_color(container, lv_color_hex(0x000000), 0);  // Pure black background
    lv_obj_set_style_bg_opa(container, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(container, 2, 0);
    lv_obj_set_style_border_color(container, lv_color_hex(0x00FF00), 0);  // Green border
    lv_obj_set_style_radius(container, 8, 0);
    lv_obj_set_style_pad_all(container, 6, 0);
    lv_obj_clear_flag(container, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_flag(container, LV_OBJ_FLAG_CLICKABLE);

    // Add event callback if provided
    if (eventCallback) {
        lv_obj_add_event_cb(container, eventCallback, LV_EVENT_CLICKED, userData);
    }

    // ECG label (top-left)
    lv_obj_t* labelECG = lv_label_create(container);
    lv_label_set_text(labelECG, "ECG - Lead II");
    lv_obj_set_style_text_font(labelECG, &lv_font_montserrat_18, 0);  // ✅ Increased from 14 to 18
    lv_obj_set_style_text_color(labelECG, lv_color_hex(0xFFFFFF), 0);  // ✅ White text on black bg
    lv_obj_align(labelECG, LV_ALIGN_TOP_LEFT, 5, 2);

    // Create ECG chart
    chart = lv_chart_create(container);
    lv_obj_set_size(chart, CHART_WIDTH, CHART_HEIGHT);
    lv_obj_align(chart, LV_ALIGN_BOTTOM_MID, 0, 0);
    lv_obj_set_style_bg_color(chart, lv_color_hex(0x000000), 0);  // Pure black background
    lv_obj_set_style_bg_opa(chart, LV_OPA_COVER, 0);
    lv_obj_set_style_border_width(chart, 0, 0);
    lv_obj_set_style_pad_all(chart, 0, 0);

    // Configure chart
    lv_chart_set_type(chart, LV_CHART_TYPE_LINE);
    lv_chart_set_update_mode(chart, LV_CHART_UPDATE_MODE_SHIFT);  // Scrolling waveform
    lv_chart_set_point_count(chart, CHART_WIDTH);  // 1 point per pixel width
    lv_chart_set_range(chart, LV_CHART_AXIS_PRIMARY_Y, 0, 100);  // 0-100 range

    // ✅ v5.8.13: Medical ECG grid - actual 5×5 squares like ECG paper
    // Chart: 268px wide, 210px tall
    // Target: 42px squares (268÷42=6.4 squares wide, 210÷42=5 squares tall)
    // 5 horizontal lines = 6 sections (0, 35, 70, 105, 140, 175, 210)
    // 6 vertical lines = 7 sections (0, 38, 76, 114, 152, 190, 228, 268)
    lv_chart_set_div_line_count(chart, 6, 5);  // 6 vertical, 5 horizontal for ~square grid
    lv_obj_set_style_line_color(chart, lv_color_hex(GRID_COLOR), LV_PART_MAIN);
    lv_obj_set_style_line_width(chart, 1, LV_PART_MAIN);
    lv_obj_set_style_line_opa(chart, LV_OPA_30, LV_PART_MAIN);  // More subtle (was 50%)

    // ✅ Hide Y-axis ticks and labels (no need for axis on ECG waveform)
    lv_obj_set_style_pad_left(chart, 0, LV_PART_MAIN);  // Remove left padding for axis
    lv_obj_set_style_pad_right(chart, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_top(chart, 0, LV_PART_MAIN);
    lv_obj_set_style_pad_bottom(chart, 0, LV_PART_MAIN);

    // Hide axis ticks
    lv_obj_set_style_line_width(chart, 0, LV_PART_TICKS);
    lv_obj_set_style_text_opa(chart, LV_OPA_TRANSP, LV_PART_TICKS);  // Hide tick labels

    // Create ECG series (bright green waveform)
    series = lv_chart_add_series(chart, lv_color_hex(WAVEFORM_COLOR), LV_CHART_AXIS_PRIMARY_Y);

    // ✅ v5.8.12: Explicitly set series line color to green (fixes red waveform issue)
    lv_obj_set_style_line_color(chart, lv_color_hex(WAVEFORM_COLOR), LV_PART_ITEMS);

    // Set line style - 3px width with rounded caps for smooth medical-grade appearance
    lv_obj_set_style_line_width(chart, 3, LV_PART_ITEMS);
    lv_obj_set_style_line_rounded(chart, true, LV_PART_ITEMS);

    // Initialize with baseline (value 30 = 70% from top, medical ECG standard)
    for (int i = 0; i < CHART_WIDTH; i++) {
        lv_chart_set_next_value(chart, series, 30);
    }

    initialized = true;
    Serial.println("✅ ECGChart: Initialized (240px height at Y=216, medical grid)");

    return container;
}

void ECGChart::updateSamples(int32_t* samples, uint8_t numSamples) {
    if (!initialized || !chart || !series) return;

    // Feed each sample to the chart (scrolling left)
    for (uint8_t i = 0; i < numSamples && i < 10; i++) {
        // ✅ v5.8.7: Remove DC offset (8388608) before mapping
        // 24-bit ADC: samples are 8388608 ± amplitude
        // AC component: ±500000 µV typical ECG range
        int32_t acSignal = samples[i] - 8388608;

        // ✅ v5.8.13: CORRECT mapping - baseline ACTUALLY at 30
        // When acSignal = 0 (no deflection), value = 30
        // R-peak (+170000 µV) → value ~90
        // S-wave (-40000 µV) → value ~24
        // Formula: scale -200000..+200000 to 0..100, THEN shift baseline
        float normalized = (float)acSignal / 200000.0;  // -1.0 to +1.0
        int value = 30 + (int)(normalized * 70.0);      // 30 ± 70 units
        value = constrain(value, 0, 100);
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

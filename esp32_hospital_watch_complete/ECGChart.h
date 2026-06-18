/**
 * ECGChart.h
 * Hospital Watch - ECG Waveform Chart Component
 *
 * Displays real-time ECG waveform with:
 * - Medical-grade 5mm × 5mm grid background
 * - Smooth 3px line rendering
 * - Scrolling left-to-right display
 * - Lead II ECG signal (microBatch[1])
 *
 * Layout:
 * - Height: 240px (was 230px, increased after patient bar height fix)
 * - Position: Below vitals (Y=216)
 * - Width: 268px (with 6px padding on each side)
 * - Background: Dark green (#001A00)
 * - Waveform: Bright green (#00FF00)
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-22
 */

#ifndef ECG_CHART_H
#define ECG_CHART_H

#include <Arduino.h>
#include <lvgl.h>
#include "MedicalTheme.h"

class ECGChart {
public:
    /**
     * Constructor
     */
    ECGChart();

    /**
     * Destructor
     */
    ~ECGChart();

    /**
     * Create ECG chart on parent screen
     * @param parent Parent LVGL screen object
     * @param eventCallback Event callback for chart clicks (optional)
     * @param userData User data to pass to callback (optional)
     * @return ECG chart container object
     */
    lv_obj_t* create(lv_obj_t* parent, lv_event_cb_t eventCallback = nullptr, void* userData = nullptr);

    /**
     * Update ECG chart with new samples
     * @param samples Array of ECG samples (int32_t microBatch format)
     * @param numSamples Number of samples in array (max 10)
     */
    void updateSamples(int32_t* samples, uint8_t numSamples);

    /**
     * Get ECG chart container object
     * @return LVGL object pointer
     */
    lv_obj_t* getContainer() const;

    /**
     * Get ECG chart object (for direct manipulation)
     * @return LVGL chart object pointer
     */
    lv_obj_t* getChart() const;

    /**
     * Get ECG chart series (for direct manipulation)
     * @return LVGL chart series pointer
     */
    lv_chart_series_t* getSeries() const;

    /**
     * Check if ECG chart is initialized
     * @return true if initialized, false otherwise
     */
    bool isInitialized() const;

private:
    lv_obj_t* container;           // ECG container (box)
    lv_obj_t* chart;               // ECG chart
    lv_chart_series_t* series;     // ECG waveform series

    bool initialized;

    // Constants - Per your layout spec (Status:30px + Patient:40px + Vitals:170px + ECG:216px = 456px)
    static const uint16_t HEIGHT = 216;        // 216px chart container height (increased from 182px)
    static const uint16_t Y_POSITION = 240;    // Below vitals (30+40+170)
    static const uint16_t CHART_WIDTH = 268;   // Chart width (280 - 12px padding)
    static const uint16_t CHART_HEIGHT = 194;  // Internal chart height (leave room for labels, 216-22)

    // Colors: use `MedicalTheme` palette at runtime; no in-class lv_color_t constants here.

    // ECG signal range (microVolts)
    static const int32_t ECG_MIN = -500000;  // -0.5mV
    static const int32_t ECG_MAX = 500000;   // +0.5mV
};

#endif // ECG_CHART_H

/**
 * PatientBar.h
 * Hospital Watch - Patient Info Bar Component
 *
 * Displays:
 * - Patient ID / MRN (Medical Record Number)
 * - Device ID (when no patient assigned)
 *
 * Height: 35px
 * Position: Below status bar (Y=35)
 * Background: Green (#2ECC71)
 *
 * Author: Claude/Anthropic
 * Date: 2025-11-22
 */

#ifndef PATIENT_BAR_H
#define PATIENT_BAR_H

#include <Arduino.h>
#include <lvgl.h>
#include "MedicalTheme.h"

class PatientBar {
public:
    /**
     * Constructor
     */
    PatientBar();

    /**
     * Destructor
     */
    ~PatientBar();

    /**
     * Create patient bar on parent screen
     * @param parent Parent LVGL screen object
     * @return Patient bar container object
     */
    lv_obj_t* create(lv_obj_t* parent);

    /**
     * Update patient ID display
     * @param patientId Patient MRN or ID string
     */
    void updatePatientId(const char* patientId);

    /**
     * Update device ID display (shown when no patient assigned)
     * @param deviceId Device identifier string
     */
    void updateDeviceId(const char* deviceId);

    /**
     * Get patient bar container object
     * @return LVGL object pointer
     */
    lv_obj_t* getContainer() const;

    /**
     * Check if patient bar is initialized
     * @return true if initialized, false otherwise
     */
    bool isInitialized() const;

private:
    lv_obj_t* container;         // Patient bar container
    lv_obj_t* labelPatientInfo;  // Patient/Device ID label
    lv_obj_t* labelMRN;          // MRN label (right side)

    bool initialized;

    // Constants - Per your layout spec
    static const uint16_t HEIGHT = 40;      // 40px height (increased for legibility)
    static const uint16_t Y_POSITION = 30;  // Below status bar (30px)
};

#endif // PATIENT_BAR_H

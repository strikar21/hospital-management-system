#ifndef MEDICAL_THEME_H
#define MEDICAL_THEME_H

#include <lvgl.h>

/**
 * Medical Watch Design System
 * Dark theme optimized for AMOLED displays (1.64" 280x456)
 *
 * Design Principles:
 * 1. Pure black background for AMOLED power saving
 * 2. Single accent color (medical blue) for consistency
 * 3. Status colors ONLY for alerts (red/orange/green)
 * 4. Depth through shadows, not borders
 * 5. Clear typography hierarchy
 *
 * Author: Design Team
 * Date: 2025-11-23
 */
namespace MedicalTheme {
    // ==================== BASE COLORS ====================
    // Pure black for AMOLED power saving (turns off pixels)
    static const lv_color_t BG_BLACK = lv_color_hex(0x000000);

    // Elevated surfaces (cards, bars) - dark grays
    static const lv_color_t BG_DARK = lv_color_hex(0x1A1A1A);        // Card background (dark gray, NOT pink!)
    static const lv_color_t BG_DARKER = lv_color_hex(0x0F0F0F);      // Slightly darker
    static const lv_color_t BG_ELEVATED = lv_color_hex(0x2A2A2A);    // Pressed state

    // Text colors - grayscale hierarchy
    static const lv_color_t TEXT_PRIMARY = lv_color_hex(0xFFFFFF);    // White - main content
    static const lv_color_t TEXT_SECONDARY = lv_color_hex(0xB0B0B0);  // Light gray - secondary info
    static const lv_color_t TEXT_TERTIARY = lv_color_hex(0x707070);   // Medium gray - labels
    static const lv_color_t TEXT_DIM = lv_color_hex(0x404040);        // Dark gray - disabled

    // ==================== ACCENT COLOR ====================
    // Single accent - Medical Blue (iOS-style, professional)
    static const lv_color_t ACCENT = lv_color_hex(0x0A84FF);          // Primary blue
    static const lv_color_t ACCENT_DARK = lv_color_hex(0x064A8C);     // Darker variant
    static const lv_color_t ACCENT_LIGHT = lv_color_hex(0x3D9FFF);    // Lighter variant

    // ==================== VITAL ACCENT COLORS ====================
    // ✅ All primary vitals use green in normal state (single-page design)
    static const lv_color_t VITAL_ACCENT = lv_color_hex(0x00FF00);  // Bright green - normal vitals

    // Aliases for specific vitals (all use same green)
    static const lv_color_t VITAL_HR = VITAL_ACCENT;      // Heart rate
    static const lv_color_t VITAL_BP = VITAL_ACCENT;      // Blood pressure
    static const lv_color_t VITAL_SPO2 = VITAL_ACCENT;    // SpO2
    static const lv_color_t VITAL_TEMP = VITAL_ACCENT;    // Temperature

    // ==================== ECG CHART COLORS ====================
    // ✅ Dark red theme (mimics real ECG paper)
    static const lv_color_t ECG_BG = lv_color_hex(0x1A0000);       // Dark red background
    static const lv_color_t ECG_GRID_MINOR = lv_color_hex(0x4D0000); // Dark red minor grid
    static const lv_color_t ECG_GRID_MAJOR = lv_color_hex(0x800000); // Maroon major grid
    static const lv_color_t ECG_WAVEFORM = lv_color_hex(0x00FF00);   // Bright green waveform

    // ==================== STATUS COLORS ====================
    // ONLY use for actual status indication (alerts, abnormal vitals)
    // DO NOT use for decorative borders
    static const lv_color_t STATUS_CRITICAL = lv_color_hex(0xFF3B30);  // Red - critical alerts
    static const lv_color_t STATUS_WARNING = lv_color_hex(0xFF9500);   // Orange - warnings
    static const lv_color_t STATUS_GOOD = lv_color_hex(0x34C759);      // Green - normal/good
    static const lv_color_t STATUS_INFO = lv_color_hex(0x5AC8FA);      // Cyan - info

    // ==================== OPACITY LEVELS ====================
    static const lv_opa_t OPA_FULL = LV_OPA_COVER;     // 100% - solid
    static const lv_opa_t OPA_HIGH = LV_OPA_90;        // 90% - high opacity
    static const lv_opa_t OPA_MED = LV_OPA_70;         // 70% - medium
    static const lv_opa_t OPA_LOW = LV_OPA_40;         // 40% - low
    static const lv_opa_t OPA_DIM = LV_OPA_20;         // 20% - very dim
    static const lv_opa_t OPA_SUBTLE = LV_OPA_10;      // 10% - barely visible

    // ==================== BORDERS & RADII ====================
    static const lv_coord_t RADIUS_NONE = 0;           // No rounding
    static const lv_coord_t RADIUS_SMALL = 6;          // Small corner radius
    static const lv_coord_t RADIUS_MEDIUM = 12;        // Medium (cards)
    static const lv_coord_t RADIUS_LARGE = 20;         // Large (buttons)
    static const lv_coord_t RADIUS_PILL = 999;         // Fully rounded (badges)

    static const lv_coord_t BORDER_THIN = 1;           // Thin border
    static const lv_coord_t BORDER_MEDIUM = 2;         // Medium border
    static const lv_coord_t BORDER_THICK = 3;          // Thick border

    // ==================== SHADOWS ====================
    static const lv_coord_t SHADOW_SMALL = 4;          // Small shadow
    static const lv_coord_t SHADOW_MEDIUM = 8;         // Medium shadow (cards)
    static const lv_coord_t SHADOW_LARGE = 16;         // Large shadow (popups)

    // ==================== SPACING ====================
    static const lv_coord_t SPACE_TINY = 4;            // Tiny spacing
    static const lv_coord_t SPACE_SMALL = 8;           // Small spacing (card padding)
    static const lv_coord_t SPACE_MEDIUM = 12;         // Medium spacing
    static const lv_coord_t SPACE_LARGE = 16;          // Large spacing
    static const lv_coord_t SPACE_XL = 24;             // Extra large spacing

    // ==================== HELPER FUNCTIONS ====================

    /**
     * Apply modern card styling (rounded corners, shadow, elevated background)
     * Use this for vitals cards, settings panels, etc.
     */
    static void styleCard(lv_obj_t* obj) {
        lv_obj_set_style_bg_color(obj, BG_DARK, 0);
        lv_obj_set_style_bg_opa(obj, OPA_FULL, 0);
        lv_obj_set_style_radius(obj, RADIUS_MEDIUM, 0);
        lv_obj_set_style_border_width(obj, 0, 0);  // No borders
        lv_obj_set_style_pad_all(obj, SPACE_SMALL, 0);

        // Drop shadow for depth (subtle)
        lv_obj_set_style_shadow_width(obj, SHADOW_MEDIUM, 0);
        lv_obj_set_style_shadow_color(obj, BG_BLACK, 0);
        lv_obj_set_style_shadow_opa(obj, OPA_LOW, 0);
        lv_obj_set_style_shadow_ofs_y(obj, 4, 0);  // Offset downward
    }

    // Overloaded: create accent bar with specific color
    static lv_obj_t* createAccentBar(lv_obj_t* parent, lv_coord_t height, lv_color_t color) {
        lv_obj_t* bar = lv_obj_create(parent);
        lv_obj_set_size(bar, 3, height);
        lv_obj_align(bar, LV_ALIGN_LEFT_MID, 0, 0);
        lv_obj_set_style_bg_color(bar, color, 0);
        lv_obj_set_style_bg_opa(bar, OPA_MED, 0);  // Semi-transparent
        lv_obj_set_style_radius(bar, 0, 0);
        lv_obj_set_style_border_width(bar, 0, 0);
        return bar;
    }

    /**
     * Create subtle accent bar (thin vertical line on left edge)
     * Replaces colored borders for card differentiation
     */
    static lv_obj_t* createAccentBar(lv_obj_t* parent, lv_coord_t height) {
        return createAccentBar(parent, height, ACCENT);
    }

    /**
     * Create subtle divider line (horizontal separator)
     * Used between sections (status bar, patient bar, etc.)
     */
    static lv_obj_t* createDivider(lv_obj_t* parent, lv_align_t align = LV_ALIGN_BOTTOM_MID) {
        lv_obj_t* div = lv_obj_create(parent);
        lv_obj_set_size(div, LV_PCT(100), 1);
        lv_obj_align(div, align, 0, 0);
        lv_obj_set_style_bg_color(div, TEXT_TERTIARY, 0);
        lv_obj_set_style_bg_opa(div, OPA_SUBTLE, 0);  // Very subtle
        lv_obj_set_style_border_width(div, 0, 0);
        lv_obj_set_style_radius(div, 0, 0);
        return div;
    }

    /**
     * Get status color based on vital value and thresholds
     * Returns TEXT_PRIMARY (white) for normal, STATUS_WARNING/CRITICAL for abnormal
     *
     * Example usage:
     *   lv_color_t color = getVitalStatusColor(heartRate, 40, 120, 50, 110);
     */
    static lv_color_t getVitalStatusColor(float value, float critMin, float critMax,
                                          float warnMin, float warnMax) {
        if (value < critMin || value > critMax) {
            return STATUS_CRITICAL;  // Red - critical range
        } else if (value < warnMin || value > warnMax) {
            return STATUS_WARNING;   // Orange - warning range
        } else {
            return TEXT_PRIMARY;     // White - normal range
        }
    }

    /**
     * Style button with accent color
     */
    static void styleButton(lv_obj_t* btn) {
        lv_obj_set_style_bg_color(btn, ACCENT, 0);
        lv_obj_set_style_bg_opa(btn, OPA_FULL, 0);
        lv_obj_set_style_radius(btn, RADIUS_LARGE, 0);
        lv_obj_set_style_border_width(btn, 0, 0);
        lv_obj_set_style_text_color(btn, TEXT_PRIMARY, 0);

        // Pressed state - darker
        lv_obj_set_style_bg_color(btn, ACCENT_DARK, LV_STATE_PRESSED);
    }

    /**
     * Apply touch feedback (scale + brightness on press)
     */
    static void addTouchFeedback(lv_obj_t* obj) {
        lv_obj_set_style_transform_zoom(obj, 260, LV_STATE_PRESSED);  // 1.02x scale
        lv_obj_set_style_bg_color(obj, BG_ELEVATED, LV_STATE_PRESSED);  // Brighter
    }
}

#endif // MEDICAL_THEME_H

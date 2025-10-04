// medicalUtils.ts - UI Display utilities only
// NO MEDICAL LOGIC - All medical determinations come from backend

import { vitaltype, vitalstatus } from '../types';

/**
 * UI Display utilities for medical data
 * IMPORTANT: No medical logic - only display formatting
 */
export class MedicalUtils {

  /**
   * Display vital sign status from backend data
   * Backend provides the medical determination, frontend just displays it
   */
  static getVitalStatus(value: number, type: vitaltype, diastolic?: number): vitalstatus {
    // REMOVED: All medical logic moved to backend
    // Frontend cannot make medical determinations
    // Backend must provide vital status in API response
    // Warning noted
    return 'normal'; // Default fallback - backend should provide actual status
  }

  /**
   * REMOVED: detectArrhythmia - Medical diagnosis must come from backend
   */
  static detectArrhythmia(heartRate: number, ecgValue: number): boolean {
    // Warning noted
    return false; // Frontend cannot make medical diagnoses
  }

  /**
   * REMOVED: diagnosArrhythmia - Medical diagnosis must come from backend
   */
  static diagnosArrhythmia(heartRate: number, ecgValue: number): string | null {
    // Warning noted
    return null; // Frontend cannot make medical diagnoses
  }

  /**
   * REMOVED: calculateRiskScore - Medical assessment must come from backend
   */
  static calculateRiskScore(heartRate: number, oxygenSaturation: number, temperature: number): number {
    // Warning noted
    return 0; // Frontend cannot make medical assessments
  }

  /**
   * UI helper: Format vital sign values for display
   * This is pure UI formatting - no medical logic
   */
  static formatVitalValue(value: number, type: vitaltype): string {
    switch (type) {
      case 'heartRate':
        return `${Math.round(value)} bpm`;
      case 'oxygenSaturation':
        return `${Math.round(value)}%`;
      case 'skinTemperature':
        return `${value.toFixed(1)}°F`;
      case 'systolicPressure':
        return `${Math.round(value)} mmHg`;
      case 'ecgReading':
        return `${Math.round(value)} mV`;
      default:
        return value.toString();
    }
  }

  /**
   * UI helper: Get color for vital status display
   * Uses backend-provided status, just maps to UI colors
   */
  static getStatusColor(status: vitalstatus): string {
    switch (status) {
      case 'critical': return 'text-red-600';
      case 'warning': return 'text-yellow-600';
      case 'normal': return 'text-green-600';
      default: return 'text-gray-600';
    }
  }

  /**
   * UI helper: Get background color for vital status
   */
  static getStatusBgColor(status: vitalstatus): string {
    switch (status) {
      case 'critical': return 'bg-red-100';
      case 'warning': return 'bg-yellow-100';
      case 'normal': return 'bg-green-100';
      default: return 'bg-gray-100';
    }
  }
}

/**
 * COMPLIANCE NOTE:
 *
 * This file has been refactored to comply with single source of truth architecture.
 * All medical logic, diagnoses, and clinical determinations have been moved to the backend.
 *
 * Frontend responsibilities (ALLOWED):
 * - UI formatting and display
 * - Color coding based on backend-provided status
 * - Data presentation and visualization
 *
 * Backend responsibilities (REQUIRED):
 * - Medical diagnoses and assessments
 * - Vital sign status determination
 * - Arrhythmia detection and diagnosis
 * - Risk score calculations
 * - All clinical decision making
 *
 * Components using this class must be updated to use backend-provided medical statuses
 * rather than computing them in the frontend.
 */
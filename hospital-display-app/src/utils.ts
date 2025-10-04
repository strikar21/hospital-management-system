// utils.ts - Utility functions for Hospital Display App

import { vitaltype, vitalstatus, editableRecord } from './types';
import { MedicalUtils } from './utils/medicalUtils';
import { PermissionUtils } from './utils/permissionUtils';

// Medical functions moved to MedicalUtils class in utils/medicalUtils.ts
// Import: import { MedicalUtils } from './utils/medicalUtils';

export const detectTremorEvent = (tremorValue: number, duration: number = 1): boolean => {
  // Detect significant tremor events
  return tremorValue > 4 && duration > 5; // Tremor intensity > 4 for more than 5 seconds
};

// Medical assessment functions moved to MedicalUtils class
// Import: import { MedicalUtils } from './utils/medicalUtils';

export const getStatusColor = (status: string): string => {
  switch (status) {
    case 'critical': return 'text-red-600 bg-red-50 border-red-200';
    case 'warning': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'emergency': return 'text-red-800 bg-red-100 border-red-300';
    default: return 'text-green-600 bg-green-50 border-green-200';
  }
};

export const getVitalStatusColor = (status: vitalstatus): string => {
  switch (status) {
    case 'critical': return 'bg-red-100 text-red-600';
    case 'warning': return 'bg-yellow-100 text-yellow-600';
    default: return 'bg-green-100 text-green-600';
  }
};

export const formatTime = (date: Date): string => {
  return date.toLocaleTimeString('en-US', { 
    hour: '2-digit', 
    minute: '2-digit',
    hour12: true 
  });
};

export const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric' 
  });
};

export const formatDateTime = (dateString: string | undefined): string => {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleString('en-IN', { 
    year: 'numeric', 
    month: 'short', 
    day: 'numeric',
    hour: '2-digit', 
    minute: '2-digit',
    timeZone: 'Asia/Kolkata' // Your local timezone
  });
};

export const formatTimeOnly = (dateString: string | undefined): string => {
  if (!dateString) return '';
  const date = new Date(dateString);
  if (isNaN(date.getTime())) return '';
  return date.toLocaleTimeString('en-IN', { 
    hour: '2-digit', 
    minute: '2-digit',
    second: '2-digit',
    timeZone: 'Asia/Kolkata' // Your local timezone
  });
};

export const getVitalDisplayName = (vitalType: string): string => {
  switch (vitalType) {
    case 'heartRate': return 'Heart Rate';
    case 'skinTemperature': return 'Skin Temperature';
    case 'oxygenSaturation': return 'Oxygen Saturation';
    case 'respiratoryRate': return 'Respiratory Rate';
    case 'systolicPressure': return 'Systolic Pressure';
    case 'diastolicPressure': return 'Diastolic Pressure';
    case 'ecgReading': return 'ECG';
    case 'eegReading': return 'EEG';
    case 'bioelectricalImpedance': return 'Bioimpedance';
    case 'tremorIntensity': return 'Tremor Intensity';
    default: return vitalType;
  }
};

export const getVitalUnit = (vitalType: string): string => {
  switch (vitalType) {
    case 'heartRate': return 'BPM';
    case 'skinTemperature': return '°F';
    case 'oxygenSaturation': return '%';
    case 'respiratoryRate': return '/min';
    case 'systolicPressure': return 'mmHg';
    case 'diastolicPressure': return 'mmHg';
    case 'ecgReading': return 'mV';
    case 'eegReading': return 'μV';
    case 'bioelectricalImpedance': return 'Ω';
    case 'tremorIntensity': return '/10';
    default: return '';
  }
};

// Permission functions moved to PermissionUtils class
// Import: import { PermissionUtils } from './utils/permissionUtils';

// 2-Hour Fixed Edit Window - Universal Function for ALL Medical Records
// Medications, Investigations, Therapy, Notes - all use the same 2-hour rule

/**
 * Universal edit check: 2-hour window from creation for ALL medical records
 * @param record - Any medical record (medication, investigation, therapy, note)
 * @param userRole - User role for permission check
 * @returns boolean - true if editable within 2 hours and user has permission
 */
export const canEditRecord = (record: editableRecord, userRole: string): boolean => {
  // Get creation timestamp (handle different field names)
  const createdat = record.createdAt || record.timestamp;
  if (!createdat) return false;

  const creationTime = new Date(createdat);
  const currentTime = new Date();
  const hoursElapsed = (currentTime.getTime() - creationTime.getTime()) / (1000 * 60 * 60);
  
  // Fixed 2-hour window for ALL records
  const withinTimeWindow = hoursElapsed <= 2;
  
  // Must also have role permission (basic check)
  const hasPermission = PermissionUtils.canEditNotes(userRole) || PermissionUtils.canEditMedications(userRole);
  
  return withinTimeWindow && hasPermission;
};

/**
 * Get remaining edit time in minutes for any record
 */
export const getRemainingEditTime = (record: editableRecord): number => {
  const createdat = record.createdAt || record.timestamp;
  if (!createdat) return 0;

  const creationTime = new Date(createdat);
  const currentTime = new Date();
  const minutesElapsed = (currentTime.getTime() - creationTime.getTime()) / (1000 * 60);
  const remainingMinutes = 120 - minutesElapsed; // 2 hours = 120 minutes
  return Math.max(0, Math.floor(remainingMinutes));
};

/**
 * Format remaining edit time for display
 */
export const formatRemainingEditTime = (record: editableRecord): string => {
  const remainingMinutes = getRemainingEditTime(record);
  
  if (remainingMinutes === 0) {
    return 'Edit window expired';
  }
  
  if (remainingMinutes < 60) {
    return `${remainingMinutes}m remaining`;
  }
  
  const hours = Math.floor(remainingMinutes / 60);
  const minutes = remainingMinutes % 60;
  return `${hours}h ${minutes}m remaining`;
};

// Device and Staff Management Permissions
// Device and staff management functions moved to PermissionUtils class
// Import: import { PermissionUtils } from './utils/permissionUtils';

// ECG/EEG data generation removed - now handled by backend

// Universal Status Color Functions - All status colors centralized here
export const getMedicationStatusColor = (status: string): string => {
  switch (status) {
    case 'active': return 'text-green-600 bg-green-50 border-green-200';
    case 'held': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'stopped': 
    case 'discontinued': return 'text-red-600 bg-red-50 border-red-200';
    default: return 'text-gray-600 bg-gray-50 border-gray-200';
  }
};

export const getDeviceStatusColor = (status: string): string => {
  switch (status) {
    case 'online': return 'text-green-500';
    case 'offline': return 'text-red-500';
    case 'maintenance': return 'text-yellow-500';
    default: return 'text-gray-500';
  }
};

export const getOrderStatusColor = (status: string): string => {
  switch (status) {
    case 'dispensed':
    case 'completed':
    case 'finalized': return 'text-green-600 bg-green-50 border-green-200';
    case 'pending':
    case 'ordered':
    case 'scheduled': return 'text-blue-600 bg-blue-50 border-blue-200';
    case 'inProgress':
    case 'processing': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
    case 'cancelled':
    case 'rejected': return 'text-red-600 bg-red-50 border-red-200';
    default: return 'text-gray-600 bg-gray-50 border-gray-200';
  }
};

export const getInvestigationStatusColor = (status: string): string => {
  return getOrderStatusColor(status); // Same color scheme
};

export const getTherapyStatusColor = (status: string): string => {
  return getOrderStatusColor(status); // Same color scheme
};

// Helper to ensure blood pressure is always integer
export const formatBloodPressure = (systolic: number, diastolic?: number): string => {
  const sys = Math.round(systolic); // Always integer
  const dia = diastolic ? Math.round(diastolic) : Math.round(systolic * 0.67); // Always integer - medical standard ratio
  return `${sys}/${dia}`;
};

// REMOVED: Frontend medical interpretation function
// All clinical interpretations now come from backend only
// Frontend displays backend-provided interpretations without analysis

// Vital trend analysis
export const getVitalTrend = (currentValue: number, previousValue: number, vitalType: vitaltype): 'rising' | 'falling' | 'stable' => {
  const threshold = getvitaltrendthreshold(vitalType);
  const difference = Math.abs(currentValue - previousValue);
  
  if (difference <= threshold) return 'stable';
  return currentValue > previousValue ? 'rising' : 'falling';
};

const getvitaltrendthreshold = (vitalType: vitaltype): number => {
  switch (vitalType) {
    case 'heartRate': return 5;
    case 'skinTemperature': return 0.3;
    case 'oxygenSaturation': return 2;
    case 'respiratoryRate': return 2;
    case 'systolicPressure': return 10;
    case 'diastolicPressure': return 10;
    case 'ecgReading': return 10;
    case 'eegReading': return 5;
    case 'bioelectricalImpedance': return 25;
    case 'tremorIntensity': return 0.5;
    default: return 1;
  }
};

// Generate realistic vital sign ranges for different patient conditions
export const getVitalRangesForCondition = (diagnosis: string) => {
  const baseRanges = {
    heartRate: { min: 60, max: 100 },
    skinTemperature: { min: 97.0, max: 99.0 },
    oxygenSaturation: { min: 95, max: 100 },
    respiratoryRate: { min: 12, max: 20 },
    systolicPressure: { min: 110, max: 140 },
    diastolicPressure: { min: 70, max: 90 },
    ecgReading: { min: 100, max: 150 },
    eegReading: { min: 10, max: 60 },
    bioelectricalImpedance: { min: 450, max: 650 },
    tremorIntensity: { min: 0, max: 2 }
  };
  
  // Adjust ranges based on diagnosis
  if (diagnosis.toLowerCase().includes('cardiac') || diagnosis.toLowerCase().includes('heart')) {
    baseRanges.heartRate = { min: 70, max: 110 };
    baseRanges.ecgReading = { min: 90, max: 160 };
  }
  
  if (diagnosis.toLowerCase().includes('pneumonia') || diagnosis.toLowerCase().includes('respiratory')) {
    baseRanges.oxygenSaturation = { min: 92, max: 98 };
    baseRanges.respiratoryRate = { min: 14, max: 24 };
  }
  
  if (diagnosis.toLowerCase().includes('stroke') || diagnosis.toLowerCase().includes('neurological')) {
    baseRanges.eegReading = { min: 5, max: 70 };
    baseRanges.tremorIntensity = { min: 0, max: 5 };
  }
  
  return baseRanges;
};
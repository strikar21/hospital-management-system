/**
 * SystemTypes - System configuration and monitoring type definitions
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Application settings, system status, and monitoring configuration types
 */

export interface appsettings {
  autoLogoutMinutes: number;
  enableAutoLogout: boolean;
  bedsideMode: boolean;
  // New settings for extended monitoring
  arrhythmiaDetection?: boolean;
  eegMonitoring?: boolean;
  tremorDetection?: boolean;
  fallDetection?: boolean;
  audioAlarms?: boolean;
  privacyMode?: boolean;
  autoScrollSpeed?: number; // pixels per second for auto-scroll
  enableAutoScroll?: boolean;
}

export interface systemstatus {
  online: boolean;
  lastSync: string;
  serverHealth: 'healthy' | 'degraded' | 'down';
  connectedDevices: number;
  activeUsers: number;
}

// Enhanced monitoring configuration
export interface monitoringconfig {
  vitalSignThresholds: {
    heartRate: { min: number; max: number; criticalMin: number; criticalMax: number };
    systolicPressure: { min: number; max: number; criticalMin: number; criticalMax: number };
    diastolicPressure: { min: number; max: number; criticalMin: number; criticalMax: number };
    skinTemperature: { min: number; max: number; criticalMin: number; criticalMax: number };
    oxygenSaturation: { min: number; max: number; criticalMin: number; criticalMax: number };
    respiratoryRate: { min: number; max: number; criticalMin: number; criticalMax: number };
    ecgReading: { min: number; max: number; criticalMin: number; criticalMax: number };
    eegReading: { min: number; max: number; criticalMin: number; criticalMax: number };
    bioimpedance: { min: number; max: number; criticalMin: number; criticalMax: number };
    tremor: { maxIntensity: number; maxDuration: number };
  };
  arrhythmiaDetection: {
    enabled: boolean;
    sensitivity: 'low' | 'medium' | 'high';
    algorithms: string[];
  };
  eegMonitoring: {
    enabled: boolean;
    seizureDetection: boolean;
    abnormalPatternDetection: boolean;
  };
  tremorDetection: {
    enabled: boolean;
    sensitivity: 'low' | 'medium' | 'high';
    threshold: number;
  };
  fallDetection: {
    enabled: boolean;
    sensitivity: 'low' | 'medium' | 'high';
    autoAlert: boolean;
  };
  alerting: {
    audioEnabled: boolean;
    visualEnabled: boolean;
    escalationTimeout: number; // minutes
    autoAcknowledgeTimeout: number; // minutes
  };
}

// Analytics/Reporting
export interface qualitymetric {
  id: string;
  name: string;
  value: number;
  target: number;
  unit: string;
  period: string;
  department?: string;
  trend: 'improving' | 'stable' | 'declining';
  lastcalculated: string;
}

// Device Management
export interface device {
  id: string;
  deviceId: string;
  serialNumber: string;
  macAddress: string;
  firmwareVersion: string;
  deviceType: string;
  location: string;
  status: string;
  connectionStatus?: string;
  displayName?: string;
  batteryLevel: number | null;
  lastSeen: string | null;
  assignedPatientId: string | null;
  calibrationDate: string | null;
  nextMaintenanceDate: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface deviceAssignmentRecord {
  id: number;
  deviceId: string;
  patientId: string;
  performedBy: string;
  assignmentReason: string;
  assignedAt: string;
  status: string;
  deviceName: string;
  deviceType: string;
  patientName?: string;
  location?: string;
  watchDisplay?: string;
  serialNumber?: string;
  connectionStatus?: string;
  batteryLevel?: number | null;
}

export interface poolStatus {
  summary: {
    totalDevices: number;
    availableDevices: number;
    assignedDevices: number;
    offlineDevices: number;
    lowBatteryDevices: number;
  };
}
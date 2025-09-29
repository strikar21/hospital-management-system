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
    bioelectricalImpedance: { min: number; max: number; criticalMin: number; criticalMax: number };
    tremorIntensity: { maxIntensity: number; maxDuration: number };
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
/**
 * UserTypes - User management and authentication type definitions
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * User accounts, authentication, and access control types
 */

export interface user {
  id: string;
  name: string;
  role: 'Doctor' | 'Nurse' | 'Administrator' | 'Technician' | 'Provisioner';
  nfcId?: string;
  staffId: string;
  department: string;
}

export interface backenduser {
  id: string;
  name: string;
  role: 'Doctor' | 'Nurse' | 'Administrator' | 'Technician' | 'Provisioner';
  nfcId: string;
  staffId: string;
  department: string;
  isActive: boolean;
  lastLogin?: string;
  passwordHash?: string;
}

export interface authenticationresponse {
  success: boolean;
  user?: user;
  token?: string;
  message?: string;
  auditLogId?: string;
}

export interface auditlog {
  id: string;
  timestamp: string;
  userId: string;
  userRole: string;
  action: string;
  entityType: 'patient' | 'medication' | 'investigation' | 'therapy' | 'notes' | 'alert';
  entityId: string;
  changes: any;
  ipAddress: string;
  deviceInfo: string;
}

// Type aliases for user-related types
export type authmethod = 'nfc' | 'credentials';
export type userRole = 'doctor' | 'nurse' | 'administrator' | 'technician' | 'provisioner';
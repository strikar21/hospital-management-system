/**
 * Map alert data from API response to domain model.
 */

import { parseISO } from '@/utils/datetime';

export interface AlertDomain {
  id: string;
  patientId: string;
  type: 'vital' | 'arrhythmia' | 'device' | 'system';
  severity: 'low' | 'medium' | 'high' | 'critical';
  status: 'active' | 'acknowledged' | 'resolved';
  message: string;
  vitalType?: string;
  vitalValue?: number;
  thresholdValue?: number;
  createdBy: string;
  createdAt: Date;
  acknowledgedBy?: string;
  acknowledgedAt?: Date;
  resolvedBy?: string;
  resolvedAt?: Date;
}

export function mapAlertFromAPI(apiAlert: any): AlertDomain {
  /**
   * Map API alert response to domain model.
   *
   * @param apiAlert - Alert data from API
   * @returns Domain alert model
   */
  return {
    id: apiAlert.id,
    patientId: apiAlert.patientId,
    type: apiAlert.type,
    severity: apiAlert.severity,
    status: apiAlert.status,
    message: apiAlert.message,
    vitalType: apiAlert.vitalType,
    vitalValue: apiAlert.vitalValue,
    thresholdValue: apiAlert.thresholdValue,
    createdBy: apiAlert.createdBy,
    createdAt: parseISO(apiAlert.createdAt),
    acknowledgedBy: apiAlert.acknowledgedBy,
    acknowledgedAt: apiAlert.acknowledgedAt ? parseISO(apiAlert.acknowledgedAt) : undefined,
    resolvedBy: apiAlert.resolvedBy,
    resolvedAt: apiAlert.resolvedAt ? parseISO(apiAlert.resolvedAt) : undefined
  };
}

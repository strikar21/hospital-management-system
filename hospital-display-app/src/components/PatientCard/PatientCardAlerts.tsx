/**
 * PatientCardAlerts - Patient alert display and management
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade alert system with acknowledgment capabilities
 */

import React from 'react';
import { AlertTriangle, CheckCircle } from 'lucide-react';
import { patient, user } from '../../types';
import auditService from '../../services/auditService';

interface PatientCardAlertsProps {
  patient: patient;
  currentUser: user;
  unacknowledgedAlerts: any[];
  arrhythmiaDetected: boolean;
  seizureActivity: boolean;
  onAcknowledgeAlert: (patient: patient, alertId: string) => void;
}

export const PatientCardAlerts: React.FC<PatientCardAlertsProps> = React.memo(({
  patient,
  currentUser,
  unacknowledgedAlerts,
  arrhythmiaDetected,
  seizureActivity,
  onAcknowledgeAlert
}) => {
  const handleAcknowledgeClick = (e: React.MouseEvent, alertId: string) => {
    e.stopPropagation();
    onAcknowledgeAlert(patient, alertId);

    // Log alert acknowledgment
    auditService.logPatientInteraction(
      'acknowledgeAlert',
      patient.id,
      `acknowledged alert ${alertId}`,
      { alertId: alertId }
    );
  };

  return (
    <>
      {/* Alert Banner - Shows alert status and total count */}
      <div className={`absolute top-0 left-0 right-0 text-white text-xs px-2 py-1 rounded-t-xl flex items-center justify-between z-10 ${
        unacknowledgedAlerts.some(alert => alert.severity === 'critical')
          ? 'bg-red-600'
          : unacknowledgedAlerts.some(alert => alert.severity === 'high' || alert.severity === 'medium')
          ? 'bg-orange-500'
          : unacknowledgedAlerts.length > 0
          ? 'bg-yellow-500'
          : 'bg-green-600'
      }`}>
        <div className="flex items-center space-x-1">
          <AlertTriangle className={`w-3 h-3 ${
            unacknowledgedAlerts.length > 0 ? 'animate-pulse' : ''
          }`} />
          <span className="font-medium">
            {unacknowledgedAlerts.length > 0 ? 'ALERTS PRESENT' : 'ALL NORMAL'}
          </span>
        </div>
        <div className="bg-black bg-opacity-20 px-1 rounded text-xs font-bold">
          {unacknowledgedAlerts.length}
        </div>
      </div>

    </>
  );
});

PatientCardAlerts.displayName = 'PatientCardAlerts';
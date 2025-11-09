/**
 * PatientCardHeader - Patient information and status header
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient header with status and device information
 */

import React from 'react';
import { Watch, WifiOff, CheckCircle } from 'lucide-react';
import { patient, user } from '../../types';
import { getStatusColor } from '../../utils';
import auditService from '../../services/auditService';

interface PatientCardHeaderProps {
  patient: patient;
  currentUser: user;
  unacknowledgedAlerts?: any[];
  onAcknowledgeAlert?: (patient: patient, alertId: string) => void;
  onViewWatchDetails?: (patient: patient) => void;
}

export const PatientCardHeader: React.FC<PatientCardHeaderProps> = React.memo(({
  patient,
  currentUser,
  unacknowledgedAlerts = [],
  onAcknowledgeAlert,
  onViewWatchDetails
}) => {
  const handleAcknowledgeClick = (e: React.MouseEvent, alertId: string) => {
    e.stopPropagation();
    if (onAcknowledgeAlert) {
      onAcknowledgeAlert(patient, alertId);
      auditService.logPatientInteraction(
        'acknowledgeAlert',
        patient.id,
        `acknowledged alert ${alertId}`,
        { alertId: alertId }
      );
    }
  };
  return (
    <div className="pt-2 px-2 border-b flex-shrink-0">
      <div className="flex items-start gap-2">
        {/* LEFT Column (30%) - Patient Demographics */}
        <div className="w-[30%] flex flex-col overflow-hidden">
          {/* Empty top spacing for alert overlay clearance */}
          <div className="h-4"></div>

          {/* Line 1: Patient Name */}
          <div className="text-sm text-gray-900 overflow-hidden mb-1">
            <div className="truncate font-semibold" title={patient.name}>
              {patient.name}
            </div>
          </div>

          {/* Line 2: Age, Sex, Department */}
          <div className="text-xs text-gray-600 overflow-hidden mb-0.5">
            <div className="truncate" title={`${patient.age}y, ${patient.gender} | ${patient.department}`}>
              {patient.age}y, {patient.gender} • {patient.department}
            </div>
          </div>

          {/* Line 3: Diagnosis */}
          <div className="text-xs text-gray-600 overflow-hidden">
            <div className="truncate" title={patient.diagnosis}>
              {patient.diagnosis}
            </div>
          </div>
        </div>

        {/* CENTER Column (40%) - Split into Alerts (85%) and Acknowledge Button (15%) */}
        <div className="w-[40%] flex gap-1 overflow-hidden">
          {/* Left Sub-column (85%) - Alerts Display */}
          <div className="w-[85%] flex flex-col overflow-hidden space-y-1">
            {/* Empty top spacing for alert overlay clearance */}
            <div className="h-4"></div>

            {unacknowledgedAlerts.length > 0 ? (
              <>
                {/* Alert 1 (most critical) */}
                {unacknowledgedAlerts
                  .sort((a, b) => {
                    const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
                    return (severityOrder[a.severity as keyof typeof severityOrder] || 99) -
                           (severityOrder[b.severity as keyof typeof severityOrder] || 99);
                  })
                  .slice(0, 1)
                  .map((alert) => (
                    <div
                      key={alert.id}
                      className={`text-xs px-2 py-1 rounded flex items-center ${
                        alert.severity === 'critical' ? 'bg-red-100 text-red-700' :
                        alert.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                        'bg-yellow-100 text-yellow-700'
                      }`}
                    >
                      <span className="flex-shrink-0">
                        {alert.severity === 'critical' ? '🚨' :
                         alert.severity === 'high' ? '⚠️' : '⚡'}
                      </span>
                      <span className="ml-1 truncate">{alert.message}</span>
                    </div>
                  ))}

                {/* Alert 2 (if exists) */}
                {unacknowledgedAlerts.length > 1 && (
                  unacknowledgedAlerts
                    .sort((a, b) => {
                      const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
                      return (severityOrder[a.severity as keyof typeof severityOrder] || 99) -
                             (severityOrder[b.severity as keyof typeof severityOrder] || 99);
                    })
                    .slice(1, 2)
                    .map((alert) => (
                      <div
                        key={alert.id}
                        className={`text-xs px-2 py-1 rounded flex items-center ${
                          alert.severity === 'critical' ? 'bg-red-100 text-red-700' :
                          alert.severity === 'high' ? 'bg-orange-100 text-orange-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}
                      >
                        <span className="flex-shrink-0">
                          {alert.severity === 'critical' ? '🚨' :
                           alert.severity === 'high' ? '⚠️' : '⚡'}
                        </span>
                        <span className="ml-1 truncate">{alert.message}</span>
                      </div>
                    ))
                )}

                {/* Show more alerts indicator if > 2 */}
                {unacknowledgedAlerts.length > 2 && (
                  <div className="text-xs text-gray-500 italic">
                    +{unacknowledgedAlerts.length - 2} more alert{unacknowledgedAlerts.length - 2 > 1 ? 's' : ''}
                  </div>
                )}
              </>
            ) : (
              <div className="text-xs text-gray-400 italic">No alerts</div>
            )}
          </div>

          {/* Right Sub-column (15%) - Acknowledge Button */}
          <div className="w-[15%] flex items-center justify-center -mt-1">
            {unacknowledgedAlerts.length > 0 && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  unacknowledgedAlerts
                    .sort((a, b) => {
                      const severityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
                      return (severityOrder[a.severity as keyof typeof severityOrder] || 99) -
                             (severityOrder[b.severity as keyof typeof severityOrder] || 99);
                    })
                    .slice(0, 2)
                    .forEach(alert => {
                      if (!alert.id.includes('fall-risk') &&
                          !alert.id.includes('arrhythmia') &&
                          !alert.id.includes('seizure')) {
                        handleAcknowledgeClick(e, alert.id);
                      }
                    });
                }}
                className="px-2 py-1 bg-green-600 hover:bg-green-700 text-white rounded text-xs flex items-center justify-center"
                title="Acknowledge visible alerts"
              >
                <CheckCircle className="w-3 h-3" />
              </button>
            )}
          </div>
        </div>

        {/* RIGHT Column (30%) - Doctor, Status & Location */}
        <div className="w-[30%] flex flex-col items-end overflow-hidden">
          {/* Empty top spacing for alert overlay clearance */}
          <div className="h-4"></div>

          {/* Line 1: Doctor Name */}
          <div className="text-xs text-gray-600 text-right w-full overflow-hidden mb-0.5">
            <div className="truncate" title={patient.attendingPhysicianName || patient.assignedDoctor || patient.attendingPhysician || 'Not assigned'}>
              {(patient.attendingPhysicianName || patient.assignedDoctor || patient.attendingPhysician)
                ? `Dr. ${patient.attendingPhysicianName || patient.assignedDoctor || patient.attendingPhysician}`
                : 'No doctor assigned'}
            </div>
          </div>

          {/* Line 2: Watch Status & Patient Status */}
          <div className="flex items-center justify-end space-x-2 w-full mb-0.5">
            <div
              className="cursor-pointer hover:bg-gray-50 rounded px-1 py-0.5 transition-colors flex-shrink-0"
              onClick={(e) => {
                e.stopPropagation();
                onViewWatchDetails?.(patient);
              }}
              title={patient.assignedDeviceId ? `Battery: ${patient.deviceBatteryLevel || 'N/A'}%` : 'No device assigned'}
            >
              {patient.assignedDeviceId ? (
                <Watch className={`w-4 h-4 ${
                  patient.deviceStatus === 'connected' ? 'text-green-600' : 'text-amber-600'
                }`} />
              ) : (
                <WifiOff className="w-4 h-4 text-gray-400" />
              )}
            </div>
            <div className={`px-2 py-1 rounded-full text-xs font-medium border whitespace-nowrap ${getStatusColor(patient.status)}`}>
              {patient.status.toUpperCase()}
            </div>
          </div>

          {/* Line 3: Room, Bed */}
          <div className="text-xs text-gray-600 text-right w-full overflow-hidden">
            <div className="truncate" title={`${patient.ward} | Room ${patient.roomNumber || patient.room} | Bed ${patient.bedNumber}`}>
              {patient.ward} • Room {patient.roomNumber || patient.room} • Bed {patient.bedNumber}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
});

PatientCardHeader.displayName = 'PatientCardHeader';
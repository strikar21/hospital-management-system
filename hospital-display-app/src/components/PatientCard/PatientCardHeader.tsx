/**
 * PatientCardHeader - Patient information and status header
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient header with status and device information
 */

import React from 'react';
import { Eye, Watch, WifiOff, CheckCircle } from 'lucide-react';
import { patient, user } from '../../types';
import { getStatusColor, formatTimeOnly } from '../../utils';
import auditService from '../../services/auditService';

interface PatientCardHeaderProps {
  patient: patient;
  currentUser: user;
  onBedsideMode: (patient: patient) => void;
  unacknowledgedAlerts?: any[];
  onAcknowledgeAlert?: (patient: patient, alertId: string) => void;
  onViewWatchDetails?: (patient: patient) => void;
}

export const PatientCardHeader: React.FC<PatientCardHeaderProps> = React.memo(({
  patient,
  currentUser,
  onBedsideMode,
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
    <div className="px-3 pt-6 pb-2 border-b flex-shrink-0 h-[90px]">
      <div className="flex items-start justify-between h-full">
        <div className="flex-1">
          <div className="flex items-center space-x-2">
            <h3 className="font-semibold text-base text-gray-900 truncate">{patient.name}</h3>

            {/* Watch Status Indicator */}
            {patient.assignedDeviceId ? (
              patient.deviceStatus === 'connected' ? (
                <div
                  className="flex items-center space-x-1 cursor-pointer hover:bg-green-100 rounded px-1 py-0.5 transition-colors"
                  title="Watch connected - Click for details"
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewWatchDetails?.(patient);
                  }}
                >
                  <Watch className="w-3 h-3 text-green-600" />
                  <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                </div>
              ) : (
                <div
                  className="flex items-center space-x-1 cursor-pointer hover:bg-amber-100 rounded px-1 py-0.5 transition-colors"
                  title="Watch disconnected - Click for details"
                  onClick={(e) => {
                    e.stopPropagation();
                    onViewWatchDetails?.(patient);
                  }}
                >
                  <Watch className="w-3 h-3 text-amber-600" />
                  <div className="w-2 h-2 bg-amber-500 rounded-full"></div>
                </div>
              )
            ) : (
              <div className="flex items-center space-x-1" title="No watch assigned">
                <WifiOff className="w-3 h-3 text-gray-400" />
                <div className="w-2 h-2 bg-gray-300 rounded-full"></div>
              </div>
            )}

            {/* Inline Alerts - Show top 2 critical alerts */}
            {unacknowledgedAlerts.length > 0 && (
              <div className="flex items-center space-x-2 ml-2">
                <div className="flex flex-col space-y-1">
                  {unacknowledgedAlerts
                    .slice(0, 2)
                    .map((alert) => (
                      <div key={alert.id} className={`text-xs px-2 py-1 rounded truncate ${
                        alert.severity === 'critical' ? 'text-red-700 bg-red-100' :
                        alert.severity === 'high' ? 'text-orange-700 bg-orange-100' :
                        'text-yellow-700 bg-yellow-100'
                      }`}>
                        {alert.severity === 'critical' ? '🚨' : alert.severity === 'high' ? '⚠️' : '⚡'} {alert.message}
                      </div>
                    ))}
                </div>

                {/* Acknowledge Button - Only the 2 visible alerts */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    // Only acknowledge the top 2 displayed alerts
                    unacknowledgedAlerts
                      .slice(0, 2)
                      .forEach(alert => {
                        if (!alert.id.includes('fall-risk') &&
                            !alert.id.includes('arrhythmia') &&
                            !alert.id.includes('seizure')) {
                          handleAcknowledgeClick(e, alert.id);
                        }
                      });
                  }}
                  className="w-6 h-6 bg-green-600 hover:bg-green-700 text-white rounded flex items-center justify-center flex-shrink-0"
                  title="Acknowledge visible alerts"
                >
                  <CheckCircle className="w-3 h-3" />
                </button>
              </div>
            )}
          </div>

          <p className="text-xs text-gray-600">
            {patient.age}y, {patient.gender}
            {patient.assignedDeviceId && (
              <span className={`ml-2 text-xs px-1 py-0.5 rounded ${
                patient.deviceStatus === 'connected'
                  ? 'bg-green-100 text-green-800'
                  : 'bg-amber-100 text-amber-800'
              }`}>
                {patient.deviceStatus === 'connected' ? 'Watch Connected' : 'Watch Disconnected'}
              </span>
            )}
          </p>

          <p className="text-xs text-gray-600 truncate">
            {patient.department}
          </p>
        </div>

        <div className="flex flex-col items-end space-y-1 ml-3">
          <div className="flex items-center space-x-2">
            <button
              onClick={(e) => {
                e.stopPropagation();
                onBedsideMode(patient);
                auditService.logPatientInteraction(
                  'enterBedsideMode',
                  patient.id,
                  `entered bedside mode`,
                  { mode: 'bedside' }
                );
              }}
              className="p-1 bg-purple-100 hover:bg-purple-200 text-purple-700 rounded transition-colors"
              title="Enter Bedside Mode"
            >
              <Eye className="w-3 h-3" />
            </button>
            <div className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(patient.status)}`}>
              {patient.status.toUpperCase()}
            </div>
          </div>

          <div className="text-xs text-gray-600 text-right">
            Bed {patient.bedNumber} • {patient.ward}
          </div>
          <div className="text-xs text-gray-500">
            Updated: {formatTimeOnly((patient.vitals?.lastDataReceived || new Date()).toString())}
          </div>
        </div>
      </div>
    </div>
  );
});

PatientCardHeader.displayName = 'PatientCardHeader';
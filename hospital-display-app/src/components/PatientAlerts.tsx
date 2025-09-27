import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, Stethoscope } from 'lucide-react';
import { patient, user, alert as alertType, clinicalAlert } from '../types';
import { formatTimeOnly } from '../utils';
import { PatientService } from '../services';

interface PatientAlertsProps {
  patient: patient;
  currentUser: user;
  alerts: alertType[];
  setAlerts: React.Dispatch<React.SetStateAction<alertType[]>>;
}

const PatientAlerts: React.FC<PatientAlertsProps> = ({
  patient,
  currentUser,
  alerts,
  setAlerts
}) => {
  const [clinicalAlerts, setClinicalAlerts] = useState<clinicalAlert[]>([]);
  const [showClinicalAlerts, setShowClinicalAlerts] = useState(false);
  const [acknowledgingAlert, setAcknowledgingAlert] = useState<string | null>(null);

  // Get unacknowledged and acknowledged alerts
  const unacknowledgedAlerts = alerts.filter(alert => !alert.isAcknowledged);
  const acknowledgedAlerts = alerts.filter(alert => alert.isAcknowledged);

  // Auto-hide acknowledged alerts after 3 seconds
  useEffect(() => {
    const acknowledgedAlerts = alerts.filter(alert => alert.isAcknowledged);
    if (acknowledgedAlerts.length > 0) {
      const timer = setTimeout(() => {
        setAlerts(prev => prev.filter(alert => !alert.isAcknowledged));
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [alerts, setAlerts]);

  // Generate clinical alerts based on patient data
  useEffect(() => {
    const generateClinicalAlerts = () => {
      const alerts: clinicalAlert[] = [];

      // Add clinical decision support logic here
      if (alerts.length > 0) {
        setShowClinicalAlerts(true);
      }

      setClinicalAlerts(alerts);
    };

    generateClinicalAlerts();
  }, [patient]);

  // Handle Alert Acknowledgment
  const handleAcknowledgeAlert = async (alertId: string) => {
    setAcknowledgingAlert(alertId);
    try {
      await PatientService.acknowledgeAlert(patient.id, alertId, currentUser.id);

      setAlerts(prev => prev.map(alert =>
        alert.id === alertId ? {
          ...alert,
          isAcknowledged: true,
          acknowledgedAt: new Date().toISOString(),
          performedBy: currentUser.id,
          performedByName: currentUser.name,
          performedByRole: currentUser.role
        } : alert
      ));

      // Auto-hide acknowledged alert after 2 seconds
      setTimeout(() => {
        setAlerts(prev => prev.filter(alert => alert.id !== alertId));
      }, 2000);

      const alertMessage = alerts.find(a => a.id === alertId)?.message || 'Unknown Alert';
      console.log(`Alert "${alertMessage}" acknowledged by ${currentUser.name}`);

    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
      alert('Failed to acknowledge alert. Please try again.');
    } finally {
      setAcknowledgingAlert(null);
    }
  };

  return (
    <>
      {/* Compact Alert Banner - ONLY UNACKNOWLEDGED ALERTS */}
      {unacknowledgedAlerts.length > 0 && (
        <div className="bg-red-100 border-b border-red-200 p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-red-600 animate-pulse" />
              <h3 className="text-sm font-bold text-red-800">⚠️ UNACKNOWLEDGED ALERTS ({unacknowledgedAlerts.length})</h3>
            </div>
            <button
              onClick={() => {
                unacknowledgedAlerts.forEach(alert => {
                  handleAcknowledgeAlert(alert.id);
                });
              }}
              disabled={acknowledgingAlert !== null}
              className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-green-400"
            >
              {acknowledgingAlert !== null ? (
                <>
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Acknowledging...</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4" />
                  <span>Acknowledge All</span>
                </>
              )}
            </button>
          </div>

          {/* Max 4 Alerts in 2x2 Grid */}
          <div className="grid grid-cols-2 gap-2">
            {unacknowledgedAlerts.slice(0, 4).map((alert) => (
              <div key={alert.id} className="flex items-center justify-between p-2 bg-white rounded border-l-4 border-red-500">
                <div className="flex items-center space-x-2 flex-1 min-w-0">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    alert.severity === 'critical' ? 'bg-red-600 animate-pulse' :
                    alert.severity === 'high' ? 'bg-orange-500' :
                    alert.severity === 'medium' ? 'bg-yellow-500' :
                    'bg-blue-500'
                  }`}></div>
                  <span className="text-xs text-red-700 font-medium truncate flex-1">{alert.message}</span>
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {formatTimeOnly(alert.timestamp)}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Show remaining alerts count if more than 4 */}
          {unacknowledgedAlerts.length > 4 && (
            <div className="mt-2 text-center">
              <span className="text-xs text-red-700 bg-red-200 px-2 py-1 rounded">
                +{unacknowledgedAlerts.length - 4} more alerts (showing first 4)
              </span>
            </div>
          )}
        </div>
      )}

      {/* Show acknowledged alerts briefly with auto-fade */}
      {acknowledgedAlerts.length > 0 && (
        <div className="bg-green-50 border-b border-green-200 p-3 animate-pulse">
          <h3 className="text-sm font-bold text-green-800 mb-2">
            ✅ ACKNOWLEDGED ALERTS ({acknowledgedAlerts.length}) - Will disappear shortly...
          </h3>
          <div className="space-y-1">
            {acknowledgedAlerts.slice(0, 2).map((alert) => (
              <div key={alert.id} className="flex items-center justify-between p-2 bg-white rounded border-l-4 border-green-500 opacity-75">
                <div className="flex items-center space-x-2 flex-1 min-w-0">
                  <div className="w-2 h-2 rounded-full bg-green-600"></div>
                  <span className="text-xs text-green-700 font-medium truncate flex-1">{alert.message}</span>
                </div>
                <div className="text-xs text-gray-600 flex-shrink-0">
                  by {alert.performedByName || `User ${alert.performedBy}`}
                  {alert.performedByRole && ` (${alert.performedByRole})`}
                  {alert.completedAt && ` • ${formatTimeOnly(alert.completedAt)}`}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Clinical Decision Support Alerts */}
      {clinicalAlerts.length > 0 && showClinicalAlerts && (
        <div className="bg-amber-50 border-b border-amber-200 p-3">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <Stethoscope className="w-4 h-4 text-amber-600" />
              <h3 className="text-sm font-bold text-amber-800">🔬 CLINICAL DECISION SUPPORT ({clinicalAlerts.length})</h3>
            </div>
            <button
              onClick={() => setShowClinicalAlerts(false)}
              className="text-amber-600 hover:text-amber-800 text-xs font-medium"
            >
              Dismiss All
            </button>
          </div>

          <div className="space-y-1 max-h-32 overflow-y-auto">
            {clinicalAlerts.map((alert) => (
              <div key={alert.id} className="flex items-center justify-between p-2 bg-white rounded border-l-4 border-amber-400">
                <div className="flex items-center space-x-2 flex-1 min-w-0">
                  <div className={`w-2 h-2 rounded-full flex-shrink-0 ${
                    alert.severity === 'critical' ? 'bg-red-600 animate-pulse' :
                    alert.severity === 'high' ? 'bg-orange-500' :
                    alert.severity === 'medium' ? 'bg-yellow-500' :
                    'bg-blue-500'
                  }`}></div>
                  <div className="flex-1 min-w-0">
                    <span className="text-xs text-amber-700 font-medium truncate block">{alert.message}</span>
                    <p className="text-xs text-gray-600 truncate">{alert.details}</p>
                    {alert.suggestedActions && alert.suggestedActions.length > 0 && (
                      <p className="text-xs text-amber-600 mt-1">
                        💡 {alert.suggestedActions[0]}
                      </p>
                    )}
                  </div>
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {formatTimeOnly(alert.timestamp)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
};

export default PatientAlerts;
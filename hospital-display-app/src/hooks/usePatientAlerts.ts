import { useState, useEffect, useCallback } from 'react';
import { alert, patient, user, caseSheetEntry } from '../types';
import { PatientService } from '../services';

interface UsePatientAlertsProps {
  patient: patient;
  currentUser: user;
  alerts: alert[];
  setAlerts: React.Dispatch<React.SetStateAction<alert[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
}

export const usePatientAlerts = ({
  patient,
  currentUser,
  alerts,
  setAlerts,
  addCaseSheetEntry
}: UsePatientAlertsProps) => {
  const [autoHideTimers, setAutoHideTimers] = useState<{[key: string]: NodeJS.Timeout}>({});

  // Acknowledge alert handler
  const handleAcknowledgeAlert = useCallback(async (alertId: string) => {
    try {
      const alertToAck = alerts.find(a => a.id === alertId);
      if (!alertToAck) return;

      // Update alert status locally
      setAlerts(prev => prev.map(alert =>
        alert.id === alertId
          ? {
              ...alert,
              isAcknowledged: true,
              acknowledgedBy: currentUser.name,
              acknowledgedAt: new Date().toISOString()
            }
          : alert
      ));

      // Add case sheet entry
      const newCaseEntry: caseSheetEntry = {
        id: 'ack_' + Date.now(),
        timestamp: new Date().toISOString(),
        type: 'alertAcknowledged',
        description: `Alert acknowledged: ${alertToAck.message}`,
        performedBy: currentUser.name,
        canEdit: PatientService.canEditItem(new Date().toISOString())
      };
      addCaseSheetEntry(newCaseEntry);

      // Set auto-hide timer for acknowledged alerts
      const timer = setTimeout(() => {
        setAlerts(prev => prev.filter(a => a.id !== alertId));
        setAutoHideTimers(prev => {
          const newTimers = { ...prev };
          delete newTimers[alertId];
          return newTimers;
        });
      }, 30000); // Hide after 30 seconds

      setAutoHideTimers(prev => ({ ...prev, [alertId]: timer }));

    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
    }
  }, [alerts, setAlerts, currentUser, addCaseSheetEntry]);

  // Generate clinical decision support alerts
  const generateClinicalAlerts = useCallback(() => {
    const newAlerts: alert[] = [];
    const now = new Date().toISOString();

    // High blood pressure alert
    if (patient.vitals?.systolicPressure && patient.vitals.systolicPressure > 140) {
      const existingAlert = alerts.find(a =>
        a.type === 'clinical' &&
        a.message.includes('High blood pressure') &&
        !a.isAcknowledged
      );

      if (!existingAlert) {
        newAlerts.push({
          id: 'bp_' + Date.now(),
          type: 'clinical',
          severity: 'high',
          message: `High blood pressure detected: ${patient.vitals.systolicPressure}/${patient.vitals.diastolicPressure} mmHg`,
          timestamp: now,
          isAcknowledged: false
        });
      }
    }

    // High heart rate alert
    if (patient.vitals?.heartRate && patient.vitals.heartRate > 100) {
      const existingAlert = alerts.find(a =>
        a.type === 'clinical' &&
        a.message.includes('High heart rate') &&
        !a.isAcknowledged
      );

      if (!existingAlert) {
        newAlerts.push({
          id: 'hr_' + Date.now(),
          type: 'clinical',
          severity: 'medium',
          message: `High heart rate detected: ${patient.vitals.heartRate} bpm`,
          timestamp: now,
          isAcknowledged: false
        });
      }
    }

    // Low oxygen saturation alert
    if (patient.vitals?.oxygenSaturation && patient.vitals.oxygenSaturation < 95) {
      const existingAlert = alerts.find(a =>
        a.type === 'clinical' &&
        a.message.includes('Low oxygen saturation') &&
        !a.isAcknowledged
      );

      if (!existingAlert) {
        newAlerts.push({
          id: 'spo2_' + Date.now(),
          type: 'clinical',
          severity: 'high',
          message: `Low oxygen saturation: ${patient.vitals.oxygenSaturation}%`,
          timestamp: now,
          isAcknowledged: false
        });
      }
    }

    if (newAlerts.length > 0) {
      setAlerts(prev => [...prev, ...newAlerts]);
    }
  }, [patient.vitals, alerts, setAlerts]);

  // Clean up timers on unmount
  useEffect(() => {
    return () => {
      Object.values(autoHideTimers).forEach(timer => clearTimeout(timer));
    };
  }, [autoHideTimers]);

  // Generate clinical alerts periodically
  useEffect(() => {
    const interval = setInterval(generateClinicalAlerts, 10000); // Check every 10 seconds
    return () => clearInterval(interval);
  }, [generateClinicalAlerts]);

  return {
    handleAcknowledgeAlert,
    generateClinicalAlerts
  };
};
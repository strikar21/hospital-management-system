// Dashboard.tsx - Main Dashboard

import React, { useState, useEffect, useRef } from 'react';
import { Users, RefreshCw, Activity, X } from 'lucide-react';
import { user, patient, roomproximity, appsettings } from './types';
import { PatientService, VitalService } from './services';
import { PermissionUtils } from './utils/permissionUtils';
import { Header } from './Header';
import PatientDetail from './PatientDetail';
import { EnhancedVitalChart } from './EnhancedVitalChart';
import { ECGViewer } from './ECGViewer';
import { DeviceAssignment } from './DeviceAssignment';
import { PatientAdmission } from './PatientAdmission';
import { DeviceProvisioning } from './DeviceProvisioning';
import { NurseAdmissionProcessing } from './NurseAdmissionProcessing';
import StaffManagement from './StaffManagement';
import { SettingsPanel } from './components/Dashboard/SettingsPanel';
import { PatientGrid } from './components/Dashboard/PatientGrid';
import { useAutoLogout } from './hooks/useAutoLogout';
import { usePatientData } from './hooks/usePatientData';
import auditService from './services/auditService';

interface DashboardProps {
  currentUser: user;
  onLogout: () => void;
  settings: appsettings;
  onUpdateSettings: (settings: appsettings) => void;
  onBedsideMode: (patients: patient[], displayCount?: 1 | 2) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ 
  currentUser, 
  onLogout, 
  settings, 
  onUpdateSettings,
  onBedsideMode
}) => {
  // Dashboard component for ${currentUser.name}
  const [selectedWard, setSelectedWard] = useState<string>('My Patients');
  const [roomProximity, setRoomProximity] = useState<roomproximity | null>(null);
  const [proximityScanning, setProximityScanning] = useState(false);
  const [showAllDepartments, setShowAllDepartments] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [selectedPatient, setSelectedPatient] = useState<patient | null>(null);
  const [showVitalChart, setShowVitalChart] = useState<{patient: patient, vital: string} | null>(null);
  const [showECGViewer, setShowECGViewer] = useState<patient | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showDeviceAssignment, setShowDeviceAssignment] = useState(false);
  const [showPatientAdmission, setShowPatientAdmission] = useState(false);
  const [showDeviceProvisioning, setShowDeviceProvisioning] = useState(false);
  const [showNurseAdmission, setShowNurseAdmission] = useState(false);
  const [showStaffManagement, setShowStaffManagement] = useState(false);
  
  const [currentPage, setCurrentPage] = useState(1);
  const PATIENTS_PER_PAGE = 20; // Limit to 20 patients for better performance
  const alertTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // Auto-logout hook
  useAutoLogout({
    settings,
    onLogout,
    userId: currentUser.id
  });

  // Patient data hook
  const {
    patients,
    loading,
    lastSync,
    error,
    loadPatients,
    updatePatient,
    removePatient,
    totalPatients
  } = usePatientData({
    userId: currentUser.id,
    selectedWard,
    showAllDepartments,
    refreshInterval: 30000
  });

  // Initialize audit service
  useEffect(() => {
    // Set user ID for audit logging
    auditService.setUserId(currentUser.id);

    // Log dashboard access
    auditService.logNavigation('login', 'dashboard', {
      userRole: currentUser.role,
      dashboardMode: 'main'
    });
  }, [currentUser.id, currentUser.role]);

  // Clean up alert timeouts on unmount
  useEffect(() => {
    return () => {
      // Capture current ref value to prevent stale closure
      const timeouts = alertTimeoutsRef.current;
      timeouts.forEach((timeout) => clearTimeout(timeout));
      timeouts.clear();
    };
  }, []);

  // Network status monitoring
  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  // Load patients based on user role and room proximity
  useEffect(() => {
    if (currentUser) {
      setCurrentPage(1); // Reset to page 1 when filters change
      loadPatients();
    }
  }, [currentUser, selectedWard, showAllDepartments]); // Removed roomProximity to stop constant reloading

  // Auto-proximity detection for nurses and technicians
  useEffect(() => {
    if (currentUser && PermissionUtils.isNurseOrTechnician(currentUser.role)) {
      detectProximity();
      
      const proximityInterval = setInterval(() => {
        detectProximity();
      }, 10000);
      
      return () => clearInterval(proximityInterval);
    }
  }, [currentUser]); // Remove detectProximity dependency to avoid hoisting issue

  // Real-time vital updates removed - backend handles real-time data

  // NFC override functionality removed - using backend-only mode


  const detectProximity = async () => {
    if (!currentUser || !PermissionUtils.isNurseOrTechnician(currentUser.role)) return;
    
    setProximityScanning(true);
    try {
      const proximity = await VitalService.detectRoomProximity();
      // React 18+ automatically batches state updates
      setRoomProximity(proximity);
    } catch (error) {
      console.error('Failed to detect room proximity:', error);
    } finally {
      setProximityScanning(false);
    }
  };

  const handleToggleECGMode = (patient: patient) => {
    updatePatient(patient.id, {
      vitals: { ...patient.vitals, isEcgMode: !patient.vitals.isEcgMode }
    });
  };

  const handleVitalClick = async (patient: patient, vitalType: string) => {
    if (vitalType === 'ecg' || vitalType === 'eeg') {
      setShowECGViewer(patient);
    } else {
      setShowVitalChart({ patient, vital: vitalType });
    }
  };

  const handlePatientDischarge = (patientId: string) => {
    // Remove patient from the local list
    removePatient(patientId);
    
    // Log discharge for audit
    auditService.logPatientInteraction('discharged', patientId, 'Patient successfully discharged from hospital', {
      dischargedBy: currentUser.id,
      timestamp: new Date().toISOString()
    });
  };

  // Alert acknowledgment using API
  const handleAcknowledgeAlert = async (patient: patient, alertId: string) => {
    try {
      await PatientService.acknowledgeAlert(patient.id, alertId, currentUser.id);
      
      // Update the patient's alerts to mark as acknowledged
      const updatedAlerts = patient.alerts.map(alert =>
        alert.id === alertId ? {
          ...alert,
          isAcknowledged: true,
          performedby: currentUser.id,
          performedbyName: currentUser.name,
          performedbyRole: currentUser.role,
          completedat: new Date().toISOString()
        } : alert
      );

      updatePatient(patient.id, { alerts: updatedAlerts });

      // Remove acknowledged alerts from the patient card display after 2 seconds
      const existingTimeout = alertTimeoutsRef.current.get(alertId);
      if (existingTimeout) {
        clearTimeout(existingTimeout);
      }

      // Set new timeout to remove the alert from display
      const timeout = setTimeout(() => {
        const filteredAlerts = updatedAlerts.filter(a => a.id !== alertId);
        updatePatient(patient.id, { alerts: filteredAlerts });
        alertTimeoutsRef.current.delete(alertId);
      }, 2000);

      alertTimeoutsRef.current.set(alertId, timeout);
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
      alert('Failed to acknowledge alert. Please try again.');
    }
  };

  const handleSingleBedsideMode = (patient: patient) => {
    onBedsideMode([patient], 1);
  };

  const handleDualBedsideMode = () => {
    if (patients.length >= 2) {
      onBedsideMode(patients.slice(0, 2), 2);
    } else if (patients.length === 1) {
      onBedsideMode(patients, 1);
    }
  };

  const toggleReferralMode = () => {
    setShowAllDepartments(!showAllDepartments);
  };

  const handlePatientSelection = async (patient: patient) => {
    try {
      console.log(`🔍 Fetching complete details for patient: ${patient.id}`);

      // Add timeout wrapper for API call
      const timeoutPromise = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('Request timeout')), 10000);
      });

      const fullPatientData = await Promise.race([
        PatientService.getPatient(patient.id),
        timeoutPromise
      ]);

      if (fullPatientData) {
        console.log(`✅ Got complete patient data with ${fullPatientData.medications?.length || 0} medications, ${fullPatientData.investigations?.length || 0} investigations, ${fullPatientData.therapies?.length || 0} therapies`);
        setSelectedPatient(fullPatientData);
      } else {
        console.error('❌ Failed to fetch complete patient data');
        // Fallback to basic data if API call fails
        setSelectedPatient(patient);
      }
    } catch (error) {
      console.error('❌ Error fetching complete patient data:', error);
      // Fallback to basic data if API call fails
      setSelectedPatient(patient);
    } finally {
    }
  };

  const getWardOptions = () => {
    if (PermissionUtils.isNurseOrTechnician(currentUser.role)) {
      return [];
    } else if (currentUser.role === 'Doctor') {
      const options = ['My Patients'];
      if (showAllDepartments) {
        options.push('All', 'ICU', 'General', 'Emergency', 'Cardiology');
      }
      return options;
    } else {
      return ['All', 'ICU', 'General', 'Emergency', 'Cardiology'];
    }
  };

  // Paginate patients for performance
  const totalPages = Math.ceil(totalPatients / PATIENTS_PER_PAGE);



  // ECG Viewer Modal
  if (showECGViewer) {
    return (
      <ECGViewer
        patient={showECGViewer}
        onClose={() => setShowECGViewer(null)}
      />
    );
  }

  // Enhanced Vital Chart Modal
  if (showVitalChart) {
    return (
      <EnhancedVitalChart
        patient={showVitalChart.patient}
        vitalType={showVitalChart.vital}
        currentUser={currentUser}
        onClose={() => setShowVitalChart(null)}
      />
    );
  }

  // Device Assignment Page
  if (showDeviceAssignment) {
    return (
      <DeviceAssignment
        currentUser={currentUser}
        onBack={() => setShowDeviceAssignment(false)}
      />
    );
  }

  // Patient Admission Page
  if (showPatientAdmission) {
    return (
      <PatientAdmission
        currentUser={currentUser}
        onBack={() => setShowPatientAdmission(false)}
      />
    );
  }

  // Device Provisioning Page
  if (showDeviceProvisioning) {
    return (
      <DeviceProvisioning
        currentUser={currentUser}
        onBack={() => setShowDeviceProvisioning(false)}
      />
    );
  }

  // Nurse Admission Processing Page
  if (showNurseAdmission) {
    return (
      <NurseAdmissionProcessing
        currentUser={currentUser}
        onBack={() => setShowNurseAdmission(false)}
      />
    );
  }

  // Staff Management Page
  if (showStaffManagement) {
    return (
      <div className="h-screen flex flex-col bg-gray-50">
        <Header
          currentUser={currentUser}
          onLogout={onLogout}
          isOnline={isOnline}
          lastsync={lastSync}
          roomProximity={null}
          proximityScanning={false}
          showAllDepartments={false}
          loading={false}
          selectedWard="Staff Management"
          patients={[]}
          settings={settings}
          getWardOptions={() => []}
          onWardChange={() => {}}
          onDetectProximity={() => {}}
          onToggleReferralMode={() => {}}
          onRefreshData={() => {}}
          onShowSettings={() => {}}
        />
        <div className="flex-1 p-6">
          <button
            onClick={() => setShowStaffManagement(false)}
            className="mb-4 flex items-center space-x-2 text-blue-600 hover:text-blue-800 transition-colors"
          >
            <X className="h-5 w-5" />
            <span>Back to Dashboard</span>
          </button>
          <StaffManagement />
        </div>
      </div>
    );
  }

  // Patient Detail Modal
  if (selectedPatient) {
    return (
      <PatientDetail
        patient={selectedPatient}
        currentUser={currentUser}
        onClose={() => setSelectedPatient(null)}
        onVitalClick={handleVitalClick}
        onECGView={(patient: patient) => setShowECGViewer(patient)}
        onToggleECGMode={(patient: patient) => {
          // Toggle ECG mode for the patient
          console.log('Toggle ECG mode for patient:', patient.name);
        }}
        onPatientDischarge={handlePatientDischarge}
      />
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-50 overflow-hidden">
      <Header
        currentUser={currentUser}
        isOnline={isOnline}
        lastsync={lastSync}
        roomProximity={roomProximity}
        proximityScanning={proximityScanning}
        showAllDepartments={showAllDepartments}
        loading={loading}
        selectedWard={selectedWard}
        patients={patients}
        getWardOptions={getWardOptions}
        onWardChange={setSelectedWard}
        onDetectProximity={detectProximity}
        onToggleReferralMode={toggleReferralMode}
        onRefreshData={loadPatients}
        onShowSettings={() => setShowSettings(true)}
        onShowDeviceAssignment={() => setShowDeviceAssignment(true)}
        onShowPatientAdmission={() => setShowPatientAdmission(true)}
        onShowDeviceProvisioning={() => setShowDeviceProvisioning(true)}
        onShowNurseAdmission={() => setShowNurseAdmission(true)}
        onShowStaffManagement={() => setShowStaffManagement(true)}
        onLogout={onLogout}
        settings={settings}
      />

      {/* Pagination Controls */}
      {totalPatients > PATIENTS_PER_PAGE && (
        <div className="bg-white border-b px-4 py-2">
          <div className="flex items-center justify-between">
            <div className="text-sm text-gray-600">
              Showing {((currentPage - 1) * PATIENTS_PER_PAGE) + 1}-{Math.min(currentPage * PATIENTS_PER_PAGE, totalPatients)} of {totalPatients} patients
            </div>
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-200"
              >
                ← Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-200"
              >
                Next →
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Patient Grid with 2 Cards Per Row - Smooth CSS Auto-scrolling */}
      <div className="flex-1 px-4 py-2 overflow-hidden">
        {totalPatients === 0 && !loading ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center">
              <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {PermissionUtils.isNurseOrTechnician(currentUser.role) && !roomProximity
                  ? 'Room Location Not Detected'
                  : 'No Patients Found'
                }
              </h3>
              <p className="text-gray-600 mb-4">
                {PermissionUtils.isNurseOrTechnician(currentUser.role) && !roomProximity
                  ? 'Move this tablet to a patient room. The system will automatically detect which patients are present via their wearables.'
                  : PermissionUtils.isNurseOrTechnician(currentUser.role) && roomProximity
                  ? `No patients with wearables detected in ${roomProximity.tabletLocation}. Patients may not be wearing their devices.`
                  : selectedWard === 'My Patients' 
                  ? `No patients found in your ${currentUser.role === 'Doctor' ? 'department' : 'assigned area'}.`
                  : selectedWard === 'All'
                  ? 'No patients are currently in the system.'
                  : `No patients found in ${selectedWard} ward.`}
              </p>
              {PermissionUtils.isNurseOrTechnician(currentUser.role) && !roomProximity ? (
                <div className="space-y-3">
                  <button
                    onClick={detectProximity}
                    disabled={proximityScanning}
                    className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-blue-400"
                  >
                    {proximityScanning ? (
                      <>
                        <RefreshCw className="w-5 h-5 animate-spin inline mr-2" />
                        Detecting Room Location...
                      </>
                    ) : (
                      <>
                        <Activity className="w-5 h-5 inline mr-2" />
                        Detect Room & Patients Now
                      </>
                    )}
                  </button>
                  <p className="text-xs text-gray-500 max-w-md mx-auto">
                    💡 Tip: The system automatically scans every 10 seconds when you're logged in as nursing staff
                  </p>
                </div>
              ) : (
                <button
                  onClick={loadPatients}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Refresh Data
                </button>
              )}
            </div>
          </div>
        ) : (
          <PatientGrid
            patients={patients}
            currentUser={currentUser}
            loading={loading}
            settings={settings}
            onPatientClick={handlePatientSelection}
            onVitalClick={handleVitalClick}
            onAcknowledgeAlert={handleAcknowledgeAlert}
            onBedsideMode={handleSingleBedsideMode}
            onToggleECGMode={handleToggleECGMode}
            onRefreshData={loadPatients}
          />
        )}
      </div>

      {/* Settings Panel */}
      <SettingsPanel
        isOpen={showSettings}
        onClose={() => setShowSettings(false)}
        currentUser={currentUser}
        patients={patients}
        settings={settings}
        onUpdateSettings={onUpdateSettings}
        onBedsideMode={handleDualBedsideMode}
      />
    </div>
  );
};
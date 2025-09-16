// Dashboard.tsx - Main Dashboard

import React, { useState, useEffect, useRef } from 'react';
import { Users, RefreshCw, Activity, Settings, X, Monitor } from 'lucide-react';
import { User, Patient, RoomProximity, VitalHistory, TimeRange, AppSettings } from './types';
import HospitalAPI from './api';
import { isNurseOrTechnician } from './utils';
import { Header } from './Header';
import { PatientCard } from './PatientCard';
import PatientDetail from './PatientDetail';
import { EnhancedVitalChart } from './EnhancedVitalChart';
import { ECGViewer } from './ECGViewer';
import { DeviceAssignment } from './DeviceAssignment';
import { PatientAdmission } from './PatientAdmission';
import { DeviceProvisioning } from './DeviceProvisioning';
import { NurseAdmissionProcessing } from './NurseAdmissionProcessing';
import StaffManagement from './StaffManagement';
import auditService from './services/auditService';

interface DashboardProps {
  currentUser: User;
  onLogout: () => void;
  settings: AppSettings;
  onUpdateSettings: (settings: AppSettings) => void;
  onBedsideMode: (patients: Patient[], displayCount?: 1 | 2) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ 
  currentUser, 
  onLogout, 
  settings, 
  onUpdateSettings,
  onBedsideMode
}) => {
  // Dashboard component for ${currentUser.name}
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedWard, setSelectedWard] = useState<string>('My Patients');
  const [roomProximity, setRoomProximity] = useState<RoomProximity | null>(null);
  const [proximityScanning, setProximityScanning] = useState(false);
  const [showAllDepartments, setShowAllDepartments] = useState(false);
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [lastSync, setLastSync] = useState(new Date());
  const [loading, setLoading] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [showVitalChart, setShowVitalChart] = useState<{patient: Patient, vital: string} | null>(null);
  const [showECGViewer, setShowECGViewer] = useState<Patient | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [showDeviceAssignment, setShowDeviceAssignment] = useState(false);
  const [showPatientAdmission, setShowPatientAdmission] = useState(false);
  const [showDeviceProvisioning, setShowDeviceProvisioning] = useState(false);
  const [showNurseAdmission, setShowNurseAdmission] = useState(false);
  const [showStaffManagement, setShowStaffManagement] = useState(false);
  
  // Auto-logout management
  const [lastActivity, setLastActivity] = useState(Date.now());
  const [currentPage, setCurrentPage] = useState(1);
  const PATIENTS_PER_PAGE = 20; // Limit to 20 patients for better performance
  const autoLogoutTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastActivityRef = useRef(Date.now());
  const alertTimeoutsRef = useRef<Map<string, NodeJS.Timeout>>(new Map());

  // Initialize audit service and activity tracking
  useEffect(() => {
    // Set user ID for audit logging
    auditService.setUserId(currentUser.id);
    
    // Log dashboard access
    auditService.logNavigation('login', 'dashboard', {
      userRole: currentUser.role,
      dashboardMode: 'main'
    });
    
    const updateActivity = () => {
      const now = Date.now();
      // Only update if more than 1 second has passed to prevent excessive updates
      if (now - lastActivityRef.current > 1000) {
        lastActivityRef.current = now;
        setLastActivity(now);
      }
    };

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    
    events.forEach(event => {
      document.addEventListener(event, updateActivity, true);
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, updateActivity, true);
      });
    };
  }, [currentUser.id, currentUser.role]);

  // Auto-logout timer management
  useEffect(() => {
    if (!settings.enableAutoLogout || settings.bedsideMode) {
      if (autoLogoutTimerRef.current) {
        clearTimeout(autoLogoutTimerRef.current);
        autoLogoutTimerRef.current = null;
      }
      return;
    }

    const checkForAutoLogout = () => {
      const timeSinceLastActivity = Date.now() - lastActivity;
      const timeoutMs = settings.autoLogoutMinutes * 60 * 1000;
      
      if (timeSinceLastActivity >= timeoutMs) {
        console.log('Auto-logout triggered due to inactivity');
        onLogout();
        return;
      }
      
      const remainingTime = timeoutMs - timeSinceLastActivity;
      autoLogoutTimerRef.current = setTimeout(checkForAutoLogout, Math.min(remainingTime, 60000));
    };

    if (autoLogoutTimerRef.current) {
      clearTimeout(autoLogoutTimerRef.current);
    }

    const timeoutMs = settings.autoLogoutMinutes * 60 * 1000;
    autoLogoutTimerRef.current = setTimeout(checkForAutoLogout, timeoutMs);

    return () => {
      if (autoLogoutTimerRef.current) {
        clearTimeout(autoLogoutTimerRef.current);
      }
    };
  }, [lastActivity, settings.enableAutoLogout, settings.autoLogoutMinutes, settings.bedsideMode, onLogout]);

  // Clean up alert timeouts on unmount
  useEffect(() => {
    return () => {
      alertTimeoutsRef.current.forEach((timeout) => clearTimeout(timeout));
      alertTimeoutsRef.current.clear();
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
    if (currentUser && isNurseOrTechnician(currentUser.role)) {
      detectProximity();
      
      const proximityInterval = setInterval(() => {
        detectProximity();
      }, 10000);
      
      return () => clearInterval(proximityInterval);
    }
  }, [currentUser]);

  // Real-time vital updates removed - backend handles real-time data

  // NFC override functionality removed - using backend-only mode

  const loadPatients = async () => {
    setLoading(true);
    try {
      // TEMPORARILY BYPASS ALL FILTERING - JUST GET ALL PATIENTS
      let patientsData: Patient[] = await HospitalAPI.getPatients(undefined, undefined, true);
      setPatients(patientsData);
      setLastSync(new Date());
    } catch (error) {
      console.error('❌ Failed to load patients:', error);
    } finally {
      setLoading(false);
    }
  };

  const detectProximity = async () => {
    if (!currentUser || !isNurseOrTechnician(currentUser.role)) return;
    
    setProximityScanning(true);
    try {
      const proximity = await HospitalAPI.detectRoomProximity();
      setRoomProximity(proximity);
      setLastSync(new Date());
    } catch (error) {
      console.error('Failed to detect room proximity:', error);
    } finally {
      setProximityScanning(false);
    }
  };

  const handleToggleECGMode = (patient: Patient) => {
    setPatients(prev => prev.map(p => 
      p.id === patient.id ? {
        ...p,
        vitals: { ...p.vitals, isECGMode: !p.vitals.isECGMode }
      } : p
    ));
  };

  const handleVitalClick = async (patient: Patient, vitalType: string) => {
    if (vitalType === 'ecg' || vitalType === 'eeg') {
      setShowECGViewer(patient);
    } else {
      setShowVitalChart({ patient, vital: vitalType });
    }
  };

  const handlePatientDischarge = (patientId: string) => {
    // Remove patient from the local list
    setPatients(prev => prev.filter(p => p.id !== patientId));
    
    // Log discharge for audit
    auditService.logPatientInteraction('discharged', patientId, 'Patient successfully discharged from hospital', {
      dischargedBy: currentUser.id,
      timestamp: new Date().toISOString()
    });
  };

  // Alert acknowledgment using API
  const handleAcknowledgeAlert = async (patient: Patient, alertId: string) => {
    try {
      await HospitalAPI.acknowledgeAlert(patient.id, alertId, currentUser.id);
      
      // Update the patients state to remove the acknowledged alert
      setPatients(prev => prev.map(p => 
        p.id === patient.id ? {
          ...p,
          alerts: p.alerts.map(alert => 
            alert.id === alertId ? {
              ...alert,
              isAcknowledged: true,
              performedBy: currentUser.id,
              performedByName: currentUser.name,
              performedByRole: currentUser.role,
              completedAt: new Date().toISOString()
            } : alert
          ).filter(alert => {
            // Remove acknowledged alerts from the patient card display after 2 seconds
            if (alert.id === alertId && alert.isAcknowledged) {
              // Clear existing timeout for this alert if it exists
              const existingTimeout = alertTimeoutsRef.current.get(alertId);
              if (existingTimeout) {
                clearTimeout(existingTimeout);
              }
              
              // Set new timeout
              const timeout = setTimeout(() => {
                setPatients(prevPatients => prevPatients.map(prevP => 
                  prevP.id === patient.id ? {
                    ...prevP,
                    alerts: prevP.alerts.filter(a => a.id !== alertId)
                  } : prevP
                ));
                // Clean up timeout reference
                alertTimeoutsRef.current.delete(alertId);
              }, 2000);
              
              alertTimeoutsRef.current.set(alertId, timeout);
              return true; // Keep for now, will be removed after timeout
            }
            return true;
          })
        } : p
      ));
    } catch (error) {
      console.error('Failed to acknowledge alert:', error);
      alert('Failed to acknowledge alert. Please try again.');
    }
  };

  const handleSingleBedsideMode = (patient: Patient) => {
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

  const handlePatientSelection = async (patient: Patient) => {
    try {
      console.log(`🔍 Fetching complete details for patient: ${patient.id}`);
      const fullPatientData = await HospitalAPI.getPatient(patient.id);
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
    }
  };

  const getWardOptions = () => {
    if (isNurseOrTechnician(currentUser.role)) {
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
  const totalPatients = patients.length;
  const totalPages = Math.ceil(totalPatients / PATIENTS_PER_PAGE);
  const startIndex = (currentPage - 1) * PATIENTS_PER_PAGE;
  const endIndex = startIndex + PATIENTS_PER_PAGE;
  const paginatedPatients = patients.slice(startIndex, endIndex);

  // Split paginated patients into rows - 2 cards per row instead of 3  
  const topRowPatients = paginatedPatients.filter((_, index) => {
    const groupOf4 = Math.floor(index / 4);
    const positionInGroup = index % 4;
    return positionInGroup < 2; // First 2 of each group of 4
  });

  const bottomRowPatients = paginatedPatients.filter((_, index) => {
    const groupOf4 = Math.floor(index / 4);
    const positionInGroup = index % 4;
    return positionInGroup >= 2; // Last 2 of each group of 4
  });

  // Get CSS animation speed based on settings with patient count consideration
  const getScrollSpeed = () => {
    const speed = settings.autoScrollSpeed || 30;
    const baseSpeed = Math.max(20, 100 - speed); // 20-70 seconds range
    
    // Adjust speed based on patient count to prevent insane scrolling
    const patientCount = paginatedPatients.length;
    const minSpeedForCount = Math.max(30, patientCount * 3); // Minimum 30s, +3s per patient
    
    const finalSpeed = Math.max(baseSpeed, minSpeedForCount);
    
    if (patientCount > 10) {
      console.log(`🐌 Scroll speed adjusted: ${patientCount} patients (page ${currentPage}), ${finalSpeed}s duration`);
    }
    
    return finalSpeed;
  };

  // Settings Panel
  const SettingsPanel = () => (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-[60]"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          setShowSettings(false);
        }
      }}
    >
      <div 
        className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 relative"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold">System Settings</h3>
          <button
            onClick={() => setShowSettings(false)}
            className="text-gray-500 hover:text-gray-700 p-1 hover:bg-gray-100 rounded"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-6">
          {/* Auto-scroll Settings */}
          <div>
            <h4 className="font-medium mb-3">Auto-scroll Settings</h4>
            <div className="space-y-3">
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.enableAutoScroll || false}
                  onChange={(e) => onUpdateSettings({ 
                    ...settings, 
                    enableAutoScroll: e.target.checked 
                  })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm">Enable auto-scroll for patient rows</span>
              </label>
              
              {settings.enableAutoScroll && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Scroll speed (pixels/second):
                  </label>
                  <select
                    value={settings.autoScrollSpeed || 30}
                    onChange={(e) => onUpdateSettings({ 
                      ...settings, 
                      autoScrollSpeed: parseInt(e.target.value) 
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value={10}>Slow (10px/s)</option>
                    <option value={20}>Medium-Slow (20px/s)</option>
                    <option value={30}>Medium (30px/s)</option>
                    <option value={50}>Fast (50px/s)</option>
                    <option value={70}>Very Fast (70px/s)</option>
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Auto-logout Settings */}
          <div>
            <h4 className="font-medium mb-3">Auto-logout Settings</h4>
            <div className="space-y-3">
              <label className="flex items-center space-x-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={settings.enableAutoLogout}
                  onChange={(e) => onUpdateSettings({ 
                    ...settings, 
                    enableAutoLogout: e.target.checked 
                  })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm">Enable auto-logout after inactivity</span>
              </label>
              
              {settings.enableAutoLogout && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Auto-logout after (minutes):
                  </label>
                  <select
                    value={settings.autoLogoutMinutes}
                    onChange={(e) => onUpdateSettings({ 
                      ...settings, 
                      autoLogoutMinutes: parseInt(e.target.value) 
                    })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value={5}>5 minutes</option>
                    <option value={10}>10 minutes</option>
                    <option value={15}>15 minutes</option>
                    <option value={30}>30 minutes</option>
                    <option value={60}>1 hour</option>
                    <option value={120}>2 hours</option>
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Bedside Mode Options */}
          <div>
            <h4 className="font-medium mb-3">Bedside Monitor Mode</h4>
            <div className="space-y-2">
              <button
                onClick={handleDualBedsideMode}
                disabled={patients.length === 0}
                className="w-full flex items-center justify-center space-x-2 p-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              >
                <Monitor className="w-4 h-4" />
                <span>Enter Bedside Mode ({Math.min(patients.length, 2)} patient{Math.min(patients.length, 2) !== 1 ? 's' : ''})</span>
              </button>
              <p className="text-xs text-gray-600">
                Shows 1-2 patients in full-screen medical monitor view with ECG/EEG toggle
              </p>
            </div>
          </div>

          {/* Current Status */}
          <div className="p-3 bg-gray-50 rounded-lg">
            <h4 className="font-medium mb-2">Current Status</h4>
            <div className="text-sm space-y-1">
              <p><strong>User:</strong> {currentUser.name} ({currentUser.role})</p>
              <p><strong>Auto-logout:</strong> {settings.enableAutoLogout ? `Enabled (${settings.autoLogoutMinutes}min)` : 'Disabled'}</p>
              <p><strong>Auto-scroll:</strong> {settings.enableAutoScroll ? `Enabled (${settings.autoScrollSpeed || 30}px/s)` : 'Disabled'}</p>
              <p><strong>Layout:</strong> 2 cards per row (same direction scrolling)</p>
              <p><strong>Patients:</strong> {patients.length} loaded</p>
            </div>
          </div>
        </div>

        <div className="flex space-x-3 mt-6">
          <button
            onClick={() => setShowSettings(false)}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Apply & Close
          </button>
        </div>
      </div>
    </div>
  );

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
          lastSync={lastSync}
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
        onECGView={(patient: Patient) => setShowECGViewer(patient)}
        onToggleECGMode={(patient: Patient) => {
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
        lastSync={lastSync}
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
              Showing {startIndex + 1}-{Math.min(endIndex, totalPatients)} of {totalPatients} patients
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
                {isNurseOrTechnician(currentUser.role) && !roomProximity
                  ? 'Room Location Not Detected'
                  : 'No Patients Found'
                }
              </h3>
              <p className="text-gray-600 mb-4">
                {isNurseOrTechnician(currentUser.role) && !roomProximity
                  ? 'Move this tablet to a patient room. The system will automatically detect which patients are present via their wearables.'
                  : isNurseOrTechnician(currentUser.role) && roomProximity
                  ? `No patients with wearables detected in ${roomProximity.tabletLocation}. Patients may not be wearing their devices.`
                  : selectedWard === 'My Patients' 
                  ? `No patients found in your ${currentUser.role === 'Doctor' ? 'department' : 'assigned area'}.`
                  : selectedWard === 'All'
                  ? 'No patients are currently in the system.'
                  : `No patients found in ${selectedWard} ward.`}
              </p>
              {isNurseOrTechnician(currentUser.role) && !roomProximity ? (
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
          <div className="h-full flex flex-col gap-1.5 relative">
            {/* Auto-scroll indicator */}
            {settings.enableAutoScroll && paginatedPatients.length > 4 && (
              <div className="absolute top-2 right-2 z-10 bg-blue-600 text-white px-3 py-1 rounded-full text-xs font-medium">
                Auto-scroll: {settings.autoScrollSpeed || 30}px/s • Page {currentPage}/{totalPages} • {paginatedPatients.length} patients
              </div>
            )}

            {/* Top Row - 2 Cards with Manual + Auto scroll */}
            <div className="flex-1 patient-row-scroll overflow-x-auto overflow-y-hidden">
              <div 
                className={`h-full flex gap-1.5 ${settings.enableAutoScroll && paginatedPatients.length > 4 ? 'patient-infinite-scroll' : ''}`}
                style={{ 
                  minWidth: 'max-content',
                  animationDuration: settings.enableAutoScroll ? `${getScrollSpeed()}s` : 'none',
                  animationPlayState: settings.enableAutoScroll ? 'running' : 'paused'
                }}
              >
                {/* Original patients */}
                {topRowPatients.map((patient) => (
                  <div key={`top-original-${patient.id}`} className="flex-shrink-0 patient-card-container" style={{ width: '500px' }}>
                    <PatientCard
                      patient={patient}
                      currentUser={currentUser}
                      onPatientClick={handlePatientSelection}
                      onVitalClick={handleVitalClick}
                      onAcknowledgeAlert={handleAcknowledgeAlert}
                      onBedsideMode={handleSingleBedsideMode}
                      onToggleECGMode={handleToggleECGMode}
                    />
                  </div>
                ))}
                {/* Duplicate for seamless scroll - only if auto-scroll enabled and enough patients */}
                {settings.enableAutoScroll && paginatedPatients.length > 4 && topRowPatients.map((patient) => (
                  <div key={`top-duplicate-${patient.id}`} className="flex-shrink-0 patient-card-container" style={{ width: '500px' }}>
                    <PatientCard
                      patient={patient}
                      currentUser={currentUser}
                      onPatientClick={handlePatientSelection}
                      onVitalClick={handleVitalClick}
                      onAcknowledgeAlert={handleAcknowledgeAlert}
                      onBedsideMode={handleSingleBedsideMode}
                      onToggleECGMode={handleToggleECGMode}
                    />
                  </div>
                ))}
              </div>
            </div>
            
            {/* Bottom Row - 2 Cards with Manual + Auto scroll */}
            <div className="flex-1 patient-row-scroll overflow-x-auto overflow-y-hidden">
              <div 
                className={`h-full flex gap-1.5 ${settings.enableAutoScroll && paginatedPatients.length > 4 ? 'patient-infinite-scroll' : ''}`}
                style={{ 
                  minWidth: 'max-content',
                  animationDuration: settings.enableAutoScroll ? `${getScrollSpeed()}s` : 'none',
                  animationPlayState: settings.enableAutoScroll ? 'running' : 'paused'
                }}
              >
                {/* Original patients */}
                {bottomRowPatients.map((patient) => (
                  <div key={`bottom-original-${patient.id}`} className="flex-shrink-0 patient-card-container" style={{ width: '500px' }}>
                    <PatientCard
                      patient={patient}
                      currentUser={currentUser}
                      onPatientClick={handlePatientSelection}
                      onVitalClick={handleVitalClick}
                      onAcknowledgeAlert={handleAcknowledgeAlert}
                      onBedsideMode={handleSingleBedsideMode}
                      onToggleECGMode={handleToggleECGMode}
                    />
                  </div>
                ))}
                {/* Duplicate for seamless scroll - only if auto-scroll enabled and enough patients */}
                {settings.enableAutoScroll && paginatedPatients.length > 4 && bottomRowPatients.map((patient) => (
                  <div key={`bottom-duplicate-${patient.id}`} className="flex-shrink-0 patient-card-container" style={{ width: '500px' }}>
                    <PatientCard
                      patient={patient}
                      currentUser={currentUser}
                      onPatientClick={handlePatientSelection}
                      onVitalClick={handleVitalClick}
                      onAcknowledgeAlert={handleAcknowledgeAlert}
                      onBedsideMode={handleSingleBedsideMode}
                      onToggleECGMode={handleToggleECGMode}
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Settings Panel */}
      {showSettings && <SettingsPanel />}
    </div>
  );
};
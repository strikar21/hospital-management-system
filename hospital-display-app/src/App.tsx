// App.tsx - Main Application Component

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { user, appsettings, patient } from './types';
import { Login } from './Login';
import { Dashboard } from './Dashboard';
import { BedsideMode } from './BedsideMode';
// Removed unused HospitalAPI import
import MedicalErrorBoundary from './components/MedicalErrorBoundary';

const DEFAULT_SETTINGS: appsettings = {
  autologoutminutes: 15,
  enableautologout: true,
  bedsidemode: false,
  // Extended settings for advanced monitoring
  arrhythmiadetection: true,
  eegmonitoring: true,
  tremordetection: true,
  falldetection: true,
  audioalarms: true,
  privacymode: false,
  autoscrollspeed: 30,
  enableautoscroll: true
};

const App: React.FC = () => {
  const [currentUser, setCurrentUser] = useState<user | null>(null);
  const [settings, setSettings] = useState<appsettings>(DEFAULT_SETTINGS);
  const [bedsidePatients, setBedsidePatients] = useState<patient[]>([]);
  const [bedsideDisplayCount, setBedsideDisplayCount] = useState<1 | 2>(1);

  // Load settings from localStorage on app start
  useEffect(() => {
    try {
      const savedSettings = localStorage.getItem('hospitalDisplaySettings');
      if (savedSettings) {
        const parsed = JSON.parse(savedSettings);
        setSettings({ ...DEFAULT_SETTINGS, ...parsed });
      }
    } catch (error) {
      console.error('Failed to load settings:', error);
    }
  }, []);

  // NFC override functionality removed - using backend-only mode

  // Debounce settings saves to prevent excessive localStorage writes
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  useEffect(() => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    saveTimeoutRef.current = setTimeout(() => {
      try {
        localStorage.setItem('hospitalDisplaySettings', JSON.stringify(settings));
        console.log('⚙️ Settings saved:', {
          autoLogout: settings.enableautologout,
          autoScroll: settings.enableautoscroll,
          arrhythmiaDetection: settings.arrhythmiadetection,
          eegMonitoring: settings.eegmonitoring,
          tremorDetection: settings.tremordetection,
          fallDetection: settings.falldetection
        });
      } catch (error) {
        console.error('Failed to save settings:', error);
      }
    }, 300); // Debounce for 300ms

    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, [settings]);

  const handleLogin = (user: user) => {
    setCurrentUser(user);
    setSettings(prev => ({ ...prev, bedsidemode: false }));
    setBedsidePatients([]);
    console.log('✅ User logged in:', user.name, user.role, '- Advanced monitoring enabled:', {
      arrhythmia: settings.arrhythmiadetection,
      eeg: settings.eegmonitoring,
      tremor: settings.tremordetection,
      fall: settings.falldetection
    });
  };

  const handleLogout = () => {
    console.log('🔓 User logged out:', currentUser?.name);
    setCurrentUser(null);
    setSettings(prev => ({ ...prev, bedsidemode: false }));
    setBedsidePatients([]);
  };

  const handleUpdateSettings = useCallback((newSettings: appsettings) => {
    setSettings(newSettings);
    console.log('⚙️ Settings updated:', {
      autoLogout: `${newSettings.enableautologout ? 'Enabled' : 'Disabled'} (${newSettings.autologoutminutes}min)`,
      autoScroll: `${newSettings.enableautoscroll ? 'Enabled' : 'Disabled'} (${newSettings.autoscrollspeed}px/s)`,
      monitoring: {
        arrhythmia: newSettings.arrhythmiadetection,
        eeg: newSettings.eegmonitoring,
        tremor: newSettings.tremordetection,
        fall: newSettings.falldetection,
        audio: newSettings.audioalarms,
        privacy: newSettings.privacymode
      }
    });
  }, []);

  const handleBedsideMode = (patients: patient[], displayCount: 1 | 2 = 1) => {
    setBedsidePatients(patients);
    setBedsideDisplayCount(displayCount);
    setSettings(prev => ({ ...prev, bedsidemode: true }));
    
    // LOGOUT USER when entering bedside mode
    console.log('🏥 Entered bedside mode with', patients.length, 'patient(s) - User logged out');
    console.log('📊 Bedside monitoring configuration:', {
      displayCount,
      arrhythmiadetection: settings.arrhythmiadetection,
      eegmonitoring: settings.eegmonitoring,
      tremordetection: settings.tremordetection,
      falldetection: settings.falldetection,
      audioalarms: settings.audioalarms,
      privacymode: settings.privacymode
    });
    setCurrentUser(null);
  };

  const handleExitBedsideMode = () => {
    setBedsidePatients([]);
    setSettings(prev => ({ ...prev, bedsidemode: false }));
    console.log('🚪 Exited bedside mode - Returning to login');
    // User remains logged out, will show login screen
  };

  // If in bedside mode, show bedside monitor
  if (settings.bedsidemode && bedsidePatients.length > 0) {
    return (
      <MedicalErrorBoundary
        patientId={bedsidePatients.length > 0 ? bedsidePatients[0].id : undefined}
        medicalContext="bedsideMonitoring"
      >
        <BedsideMode
          patients={bedsidePatients}
          displayCount={bedsideDisplayCount}
          onClose={handleExitBedsideMode}
          onDisplayCountChange={setBedsideDisplayCount}
          onNFCTap={handleLogin} // Allow NFC login from bedside mode
          settings={settings} // Pass settings for monitoring configuration
        />
      </MedicalErrorBoundary>
    );
  }

  // If no user logged in, show login
  if (!currentUser) {
    return (
      <MedicalErrorBoundary medicalContext="authentication">
        <Login onLogin={handleLogin} />
      </MedicalErrorBoundary>
    );
  }


  // Normal dashboard view
  return (
    <MedicalErrorBoundary
      patientId={currentUser.id}
      medicalContext="dashboard"
    >
      <Dashboard
        currentUser={currentUser}
        onLogout={handleLogout}
        settings={settings}
        onUpdateSettings={handleUpdateSettings}
        onBedsideMode={handleBedsideMode}
      />
    </MedicalErrorBoundary>
  );
};

export default App;
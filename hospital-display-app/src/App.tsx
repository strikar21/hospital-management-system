// App.tsx - Main Application Component

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { user, appsettings, patient } from './types';
import { Login } from './Login';
import { Dashboard } from './Dashboard';
import { BedsideMode } from './BedsideMode';
// Removed unused HospitalAPI import
import MedicalErrorBoundary from './components/MedicalErrorBoundary';

const DEFAULT_SETTINGS: appsettings = {
  autoLogoutMinutes: 15,
  enableAutoLogout: true,
  bedsideMode: false,
  // Extended settings for advanced monitoring
  arrhythmiaDetection: true,
  eegMonitoring: true,
  tremorDetection: true,
  fallDetection: true,
  audioAlarms: true,
  privacyMode: false,
  autoScrollSpeed: 30,
  enableAutoScroll: true
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
      // Settings load failed - using defaults
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
      } catch (error) {
        // Settings save failed
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
    setSettings(prev => ({ ...prev, bedsideMode: false }));
    setBedsidePatients([]);
    // User authentication successful
  };

  const handleLogout = () => {
    // User logout completed
    setCurrentUser(null);
    setSettings(prev => ({ ...prev, bedsideMode: false }));
    setBedsidePatients([]);
  };

  const handleUpdateSettings = useCallback((newSettings: appsettings) => {
    setSettings(newSettings);
    // Settings updated with monitoring configuration
  }, []);

  const handleBedsideMode = (patients: patient[], displayCount: 1 | 2 = 1) => {
    setBedsidePatients(patients);
    setBedsideDisplayCount(displayCount);
    setSettings(prev => ({ ...prev, bedsideMode: true }));
    
    // LOGOUT USER when entering bedside mode
    // Entered bedside mode - user logged out for privacy
    setCurrentUser(null);
  };

  const handleExitBedsideMode = () => {
    setBedsidePatients([]);
    setSettings(prev => ({ ...prev, bedsideMode: false }));
    // Exited bedside mode - returning to login screen
    // User remains logged out, will show login screen
  };

  // If in bedside mode, show bedside monitor
  if (settings.bedsideMode && bedsidePatients.length > 0) {
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
      userId={currentUser.id}
      userRole={currentUser.role}
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
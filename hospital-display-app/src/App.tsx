// App.tsx - Main Application Component

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { user, appsettings, patient } from './types';
import { Login } from './Login';
import { Dashboard } from './Dashboard';
import { BedsideMode } from './BedsideMode';
import SecureStorage from './utils/secureStorage';
import WebSocketService from './services/WebSocketService';
import { PatientService } from './services';
import patientCacheService from './services/PatientCacheService';
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
  const [preloadedPatients, setPreloadedPatients] = useState<patient[]>([]);

  // Load settings from SecureStorage on app start (FIXED: encrypted storage for HIPAA compliance)
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const savedSettings = await SecureStorage.get('hospitalDisplaySettings');
        if (savedSettings) {
          const parsed = JSON.parse(savedSettings);
          setSettings({ ...DEFAULT_SETTINGS, ...parsed });
        }
      } catch (error) {
        // Settings load failed - using defaults
      }
    };
    loadSettings();
  }, []);

  // NFC override functionality removed - using backend-only mode

  // Debounce settings saves to prevent excessive SecureStorage writes (FIXED: encrypted storage)
  const saveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  useEffect(() => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      try {
        await SecureStorage.set('hospitalDisplaySettings', JSON.stringify(settings));
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

  const handleLogin = async (user: user) => {
    setCurrentUser(user);
    setSettings(prev => ({ ...prev, bedsideMode: false }));
    setBedsidePatients([]);
    // User authentication successful


    // STEP 1: Check smart cache (connection-aware)
    const cacheResult = await patientCacheService.getFromCacheSmart(user.id, 'My Patients');

    // STEP 2: Display cached data immediately if available
    if (cacheResult.patients && cacheResult.patients.length > 0) {
      setPreloadedPatients(cacheResult.patients);
    }

    // STEP 3: Decide if fresh fetch is needed based on device status
    const shouldFetchFresh = cacheResult.shouldFetchFresh;

    if (shouldFetchFresh) {

      // PARALLEL: WebSocket + Fresh API fetch
      const wsService = WebSocketService.getInstance();

      try {
        const [wsResult, freshPatients] = await Promise.all([
          wsService.connect(),
          PatientService.getPatients(undefined, undefined, true)
        ]);


        // Update with fresh data
        setPreloadedPatients(freshPatients);
        await patientCacheService.saveToCache(user.id, 'My Patients', freshPatients);

      } catch (error) {
        console.error('⚠️ Fresh fetch failed:', error);
        // If cache exists, we already displayed it - graceful degradation
        // WebSocket will provide updates when it connects
      }
    } else {
      // Only connect WebSocket (no patient fetch needed - all devices offline)
      const wsService = WebSocketService.getInstance();
      try {
        await wsService.connect();
      } catch (error) {
        console.error('⚠️ WebSocket connection failed:', error);
      }
    }
  };

  const handleLogout = () => {
    // User logout completed
    setCurrentUser(null);
    setSettings(prev => ({ ...prev, bedsideMode: false }));
    setBedsidePatients([]);

    // Disconnect WebSocket on logout
    const wsService = WebSocketService.getInstance();
    wsService.disconnect();
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
        preloadedPatients={preloadedPatients}
      />
    </MedicalErrorBoundary>
  );
};

export default App;
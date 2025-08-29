// App.tsx - Main Application Component

import React, { useState, useEffect } from 'react';
import { User, AppSettings, Patient } from './types';
import { Login } from './Login';
import { Dashboard } from './Dashboard';
import { BedsideMode } from './BedsideMode';
import { HospitalAPI } from './api';

const DEFAULT_SETTINGS: AppSettings = {
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
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [settings, setSettings] = useState<AppSettings>(DEFAULT_SETTINGS);
  const [bedsidePatients, setBedsidePatients] = useState<Patient[]>([]);
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

  // Save settings to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem('hospitalDisplaySettings', JSON.stringify(settings));
      console.log('⚙️ Settings saved:', {
        autoLogout: settings.enableAutoLogout,
        autoScroll: settings.enableAutoScroll,
        arrhythmiaDetection: settings.arrhythmiaDetection,
        eegMonitoring: settings.eegMonitoring,
        tremorDetection: settings.tremorDetection,
        fallDetection: settings.fallDetection
      });
    } catch (error) {
      console.error('Failed to save settings:', error);
    }
  }, [settings]);

  const handleLogin = (user: User) => {
    setCurrentUser(user);
    setSettings(prev => ({ ...prev, bedsideMode: false }));
    setBedsidePatients([]);
    console.log('✅ User logged in:', user.name, user.role, '- Advanced monitoring enabled:', {
      arrhythmia: settings.arrhythmiaDetection,
      eeg: settings.eegMonitoring,
      tremor: settings.tremorDetection,
      fall: settings.fallDetection
    });
  };

  const handleLogout = () => {
    console.log('🔓 User logged out:', currentUser?.name);
    setCurrentUser(null);
    setSettings(prev => ({ ...prev, bedsideMode: false }));
    setBedsidePatients([]);
  };

  const handleUpdateSettings = (newSettings: AppSettings) => {
    setSettings(newSettings);
    console.log('⚙️ Settings updated:', {
      autoLogout: `${newSettings.enableAutoLogout ? 'Enabled' : 'Disabled'} (${newSettings.autoLogoutMinutes}min)`,
      autoScroll: `${newSettings.enableAutoScroll ? 'Enabled' : 'Disabled'} (${newSettings.autoScrollSpeed}px/s)`,
      monitoring: {
        arrhythmia: newSettings.arrhythmiaDetection,
        eeg: newSettings.eegMonitoring,
        tremor: newSettings.tremorDetection,
        fall: newSettings.fallDetection,
        audio: newSettings.audioAlarms,
        privacy: newSettings.privacyMode
      }
    });
  };

  const handleBedsideMode = (patients: Patient[], displayCount: 1 | 2 = 1) => {
    setBedsidePatients(patients);
    setBedsideDisplayCount(displayCount);
    setSettings(prev => ({ ...prev, bedsideMode: true }));
    
    // LOGOUT USER when entering bedside mode
    console.log('🏥 Entered bedside mode with', patients.length, 'patient(s) - User logged out');
    console.log('📊 Bedside monitoring configuration:', {
      displayCount,
      arrhythmiaDetection: settings.arrhythmiaDetection,
      eegMonitoring: settings.eegMonitoring,
      tremorDetection: settings.tremorDetection,
      fallDetection: settings.fallDetection,
      audioAlarms: settings.audioAlarms,
      privacyMode: settings.privacyMode
    });
    setCurrentUser(null);
  };

  const handleExitBedsideMode = () => {
    setBedsidePatients([]);
    setSettings(prev => ({ ...prev, bedsideMode: false }));
    console.log('🚪 Exited bedside mode - Returning to login');
    // User remains logged out, will show login screen
  };

  // If in bedside mode, show bedside monitor
  if (settings.bedsideMode && bedsidePatients.length > 0) {
    return (
      <BedsideMode
        patients={bedsidePatients}
        displayCount={bedsideDisplayCount}
        onClose={handleExitBedsideMode}
        onDisplayCountChange={setBedsideDisplayCount}
        onNFCTap={handleLogin} // Allow NFC login from bedside mode
        settings={settings} // Pass settings for monitoring configuration
      />
    );
  }

  // If no user logged in, show login
  if (!currentUser) {
    return <Login onLogin={handleLogin} />;
  }

  // Normal dashboard view
  return (
    <Dashboard 
      currentUser={currentUser} 
      onLogout={handleLogout}
      settings={settings}
      onUpdateSettings={handleUpdateSettings}
      onBedsideMode={handleBedsideMode}
    />
  );
};

export default App;
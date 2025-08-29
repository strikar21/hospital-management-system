// Login.tsx - Enhanced Login Component

import React, { useState, useEffect } from 'react';
import { 
  Tablet, CreditCard, User, Lock, LogIn, RefreshCw, Wifi, WifiOff, 
  Shield, AlertCircle, CheckCircle, Eye, EyeOff 
} from 'lucide-react';
import { User as UserType, AuthMethod } from './types';
import { HospitalAPI } from './api';
import { HybridLogin } from './HybridLogin';

interface LoginProps {
  onLogin: (user: UserType) => void;
}

export const OriginalLogin: React.FC<LoginProps> = ({ onLogin }) => {
  const [authMethod, setAuthMethod] = useState<AuthMethod>('credentials');
  const [staffId, setStaffId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [nfcScanning, setNfcScanning] = useState(false);

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

  // Auto focus on staff ID input when switching to credentials
  useEffect(() => {
    if (authMethod === 'credentials') {
      const timer = setTimeout(() => {
        const staffIdInput = document.getElementById('staffId');
        if (staffIdInput) {
          staffIdInput.focus();
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [authMethod]);

  const handleNFCScan = async () => {
    if (!isOnline) {
      setError('NFC authentication requires network connection. Please check your connection.');
      return;
    }

    setNfcScanning(true);
    setError('');
    setSuccess('');

    try {
      // NFC scanning requires backend integration
      setError('NFC authentication requires backend integration. Please use credential login.');
    } catch (err) {
      console.error('NFC authentication error:', err);
      setError('NFC authentication failed. Please check your connection and try again.');
    } finally {
      setNfcScanning(false);
    }
  };

  const handleCredentialLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!isOnline) {
      setError('Authentication requires network connection. Please check your connection.');
      return;
    }

    setIsLoading(true);
    setError('');
    setSuccess('');

    try {
      console.log('🔍 Attempting credential authentication with backend:', staffId, '***');
      // Backend handles all validation - no local credential storage
      const user = await HospitalAPI.authenticateCredentials(staffId, password);
      
      if (user) {
        setSuccess(`Authentication successful! Welcome, ${user.name}!`);
        setTimeout(() => {
          onLogin(user);
        }, 1000);
      } else {
        setError('Invalid staff ID or password. Please check your credentials and try again.');
      }
    } catch (err) {
      console.error('Authentication error:', err);
      setError('Authentication failed. Please check your credentials and network connection.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-blue-700 to-indigo-800 flex items-center justify-center p-6">
      <div className="max-w-6xl w-full">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="mx-auto flex items-center justify-center w-20 h-20 bg-white rounded-full shadow-lg mb-6">
            <Tablet className="w-10 h-10 text-blue-600" />
          </div>
          <h2 className="text-4xl font-bold text-white mb-3">Hospital Display System</h2>
          <p className="text-blue-100 text-lg">Secure Staff Authentication</p>
          
          {/* Network Status */}
          <div className={`flex items-center justify-center space-x-2 mt-4 text-sm ${
            isOnline ? 'text-green-200' : 'text-red-200'
          }`}>
            {isOnline ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
            <span>{isOnline ? 'Connected to Server' : 'Offline - Limited Functionality'}</span>
          </div>
        </div>

        {/* Main Content - Landscape Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Login Form - Left Side */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-2xl p-8 h-full">
              {/* Method Toggle */}
              <div className="flex rounded-lg bg-gray-100 p-1 mb-8">
                <button
                  onClick={() => setAuthMethod('nfc')}
                  className={`flex-1 flex items-center justify-center space-x-2 py-3 px-6 rounded-md text-base font-medium transition-colors ${
                    authMethod === 'nfc'
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <CreditCard className="w-5 h-5" />
                  <span>NFC Card Authentication</span>
                </button>
                <button
                  onClick={() => setAuthMethod('credentials')}
                  className={`flex-1 flex items-center justify-center space-x-2 py-3 px-6 rounded-md text-base font-medium transition-colors ${
                    authMethod === 'credentials'
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  <User className="w-5 h-5" />
                  <span>Manual Credentials</span>
                </button>
              </div>

              {/* Status Messages */}
              {error && (
                <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-3">
                  <AlertCircle className="w-6 h-6 text-red-600" />
                  <span className="text-red-700">{error}</span>
                </div>
              )}

              {success && (
                <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg flex items-center space-x-3">
                  <CheckCircle className="w-6 h-6 text-green-600" />
                  <span className="text-green-700">{success}</span>
                </div>
              )}

              {/* NFC Authentication */}
              {authMethod === 'nfc' && (
                <div className="space-y-8">
                  <div className="text-center">
                    <div className={`mx-auto w-32 h-32 rounded-full flex items-center justify-center mb-6 ${
                      nfcScanning ? 'bg-blue-100' : 'bg-gray-100'
                    }`}>
                      <CreditCard className={`w-16 h-16 ${nfcScanning ? 'text-blue-600' : 'text-gray-400'}`} />
                    </div>
                    <h3 className="text-2xl font-medium text-gray-900 mb-4">NFC Card Authentication</h3>
                    <p className="text-gray-600 text-lg mb-8">
                      {nfcScanning 
                        ? 'Scanning for NFC card... Please keep your card near the reader.'
                        : 'Tap your NFC card to authenticate securely with the backend server.'
                      }
                    </p>
                  </div>

                  <button
                    onClick={handleNFCScan}
                    disabled={nfcScanning || !isOnline}
                    className={`w-full flex items-center justify-center space-x-3 py-4 px-6 rounded-lg text-lg font-medium transition-colors ${
                      nfcScanning 
                        ? 'bg-blue-400 text-white cursor-not-allowed'
                        : !isOnline
                        ? 'bg-gray-400 text-white cursor-not-allowed'
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    {nfcScanning ? (
                      <>
                        <RefreshCw className="w-6 h-6 animate-spin" />
                        <span>Scanning NFC Card...</span>
                      </>
                    ) : (
                      <>
                        <CreditCard className="w-6 h-6" />
                        <span>{!isOnline ? 'Offline - NFC Unavailable' : 'Scan NFC Card'}</span>
                      </>
                    )}
                  </button>

                  <div className="text-center">
                    <button
                      onClick={() => setAuthMethod('credentials')}
                      className="text-blue-600 hover:text-blue-700 text-lg"
                    >
                      Use manual login instead
                    </button>
                  </div>
                </div>
              )}

              {/* Credential Authentication */}
              {authMethod === 'credentials' && (
                <form onSubmit={handleCredentialLogin} className="space-y-8">
                  <div>
                    <label htmlFor="staffId" className="block text-lg font-medium text-gray-700 mb-3">
                      Staff ID
                    </label>
                    <div className="relative">
                      <User className="absolute left-4 top-1/2 transform -translate-y-1/2 w-6 h-6 text-gray-400" />
                      <input
                        id="staffId"
                        type="text"
                        value={staffId}
                        onChange={(e) => setStaffId(e.target.value)}
                        className="w-full pl-12 pr-4 py-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
                        placeholder="Enter your staff ID"
                        required
                        autoComplete="username"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="password" className="block text-lg font-medium text-gray-700 mb-3">
                      Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 w-6 h-6 text-gray-400" />
                      <input
                        id="password"
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full pl-12 pr-14 py-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
                        placeholder="Enter your password"
                        required
                        autoComplete="current-password"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showPassword ? <EyeOff className="w-6 h-6" /> : <Eye className="w-6 h-6" />}
                      </button>
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading || !staffId || !password || !isOnline}
                    className={`w-full flex items-center justify-center space-x-3 py-4 px-6 rounded-lg text-lg font-medium transition-colors ${
                      isLoading 
                        ? 'bg-blue-400 text-white cursor-not-allowed'
                        : !isOnline
                        ? 'bg-gray-400 text-white cursor-not-allowed'
                        : 'bg-blue-600 text-white hover:bg-blue-700'
                    }`}
                  >
                    {isLoading ? (
                      <>
                        <RefreshCw className="w-6 h-6 animate-spin" />
                        <span>Authenticating...</span>
                      </>
                    ) : (
                      <>
                        <LogIn className="w-6 h-6" />
                        <span>{!isOnline ? 'Offline - Login Unavailable' : 'Sign In Securely'}</span>
                      </>
                    )}
                  </button>

                  <div className="text-center">
                    <button
                      type="button"
                      onClick={() => setAuthMethod('nfc')}
                      className="text-blue-600 hover:text-blue-700 text-lg"
                    >
                      Use NFC card instead
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>

          {/* Demo Information - Right Side */}
          <div className="space-y-6">
            {/* Demo Credentials */}
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
              <div className="flex items-center space-x-3 mb-4">
                <Shield className="w-6 h-6 text-white" />
                <h3 className="text-white font-semibold text-lg">Demo Information</h3>
              </div>
              <div className="text-blue-100 space-y-3">
                <p className="text-sm"><strong>Server validates all credentials:</strong> No local storage of passwords</p>
                <p className="text-sm"><strong>Universal Password:</strong> hospital123</p>
                <p className="text-sm"><strong>NFC Override:</strong> Any user can tap NFC to override current session</p>
              </div>
            </div>

            {/* Staff ID Format Information */}
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
              <h4 className="text-white font-medium mb-4">Staff ID Format</h4>
              <div className="space-y-3 max-h-64 overflow-y-auto">
                <p className="text-blue-200 text-sm"><strong>Format:</strong> 4-digit numbers (0001-9999)</p>
                <p className="text-blue-200 text-sm"><strong>Examples:</strong> 0001, 0123, 5678, 9999</p>
                <p className="text-blue-200 text-sm">All staff roles use this standardized format</p>
              </div>
            </div>

            {/* Security Notice */}
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
              <div className="flex items-center space-x-3 mb-3">
                <Shield className="w-5 h-5 text-green-300" />
                <h4 className="text-white font-medium">Security & Compliance</h4>
              </div>
              <div className="text-blue-100 text-sm space-y-2">
                <p>✓ Backend server authentication</p>
                <p>✓ HIPAA compliant with audit logs</p>
                <p>✓ Encrypted data transmission</p>
                <p>✓ Session management & auto-logout</p>
                <p>✓ NFC override protection</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Export HybridLogin as the main Login component
export const Login: React.FC<LoginProps> = ({ onLogin }) => {
  return <HybridLogin onLogin={onLogin} />;
};
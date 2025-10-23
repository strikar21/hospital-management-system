import React, { useState, useEffect } from 'react';
import { user as UserType } from './types';
import { AuthService } from './services';
import PINLogin from './PINLogin';
import { 
  Tablet, User, Lock, RefreshCw, Wifi, WifiOff, 
  Shield, AlertCircle, CheckCircle, Eye, EyeOff 
} from 'lucide-react';

interface HybridLoginProps {
  onLogin: (user: UserType) => void;
}

export const HybridLogin: React.FC<HybridLoginProps> = ({ onLogin }) => {
  const [staffId, setStaffId] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [authType, setAuthType] = useState<'unknown' | 'pin' | 'password'>('unknown');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [isCheckingRole, setIsCheckingRole] = useState(false);

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

  const checkAuthType = async (staffIdtocheck: string) => {
    if (!staffIdtocheck.trim()) {
      setAuthType('unknown');
      return;
    }

    setIsCheckingRole(true);
    setError('');

    try {
      const authInfo = await AuthService.checkAuthType(staffIdtocheck);

      if (authInfo) {
        // ROLE-BASED AUTH METHOD PRIORITY
        // Administrator (ADM) and Provisioner (PRV) → Always use PASSWORD
        // Doctor (DOC), Nurse (NUR), Technician (TEC) → Always use PIN
        // This handles cases where users have both PIN and password in database

        if (staffIdtocheck.startsWith('ADM') || staffIdtocheck.startsWith('PRV')) {
          // Admin/Provisioner: Prefer password over PIN
          if (authInfo.requiresPassword) {
            setAuthType('password');
          } else if (authInfo.requiresPin) {
            setAuthType('pin');  // Fallback if no password
          }
        } else {
          // Everyone else (doctors, nurses, technicians): Prefer PIN over password
          if (authInfo.requiresPin) {
            setAuthType('pin');
          } else if (authInfo.requiresPassword) {
            setAuthType('password');  // Fallback if no PIN
          }
        }
      } else {
        // If staff endpoint fails, default based on staff ID pattern
        if (staffIdtocheck.startsWith('ADM') || staffIdtocheck.startsWith('PRV')) {
          setAuthType('password');
        } else if (staffIdtocheck.startsWith('DOC') || staffIdtocheck.startsWith('NUR') || staffIdtocheck.startsWith('TEC')) {
          setAuthType('pin');
        } else {
          setError('Staff ID not found. Please check and try again.');
          setAuthType('unknown');
        }
      }
    } catch (err) {
      // If staff endpoint fails, default based on staff ID pattern
      if (staffIdtocheck.startsWith('ADM') || staffIdtocheck.startsWith('PRV')) {
        setAuthType('password');
      } else if (staffIdtocheck.startsWith('DOC') || staffIdtocheck.startsWith('NUR') || staffIdtocheck.startsWith('TEC')) {
        setAuthType('pin');
      } else {
        setError('');
        setAuthType('unknown');
      }
    } finally {
      setIsCheckingRole(false);
    }
  };

  // Auto-check auth type when staff ID changes
  useEffect(() => {
    if (staffId.trim().length === 7) { // Check when we have exact staff ID length (DOC0001 format)
      checkAuthType(staffId);
    } else {
      setAuthType('unknown');
    }
  }, [staffId]);

  const handlePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!isOnline) {
      setError('Authentication requires network connection. Please check your connection.');
      return;
    }

    setIsLoading(true);
    setError('');
    setSuccess('');

    try {
      const user = await AuthService.authenticateCredentials(staffId, password);
      
      if (user) {
        setSuccess(`Authentication successful! Welcome, ${user.name}!`);
        setTimeout(() => {
          onLogin(user);
        }, 1000);
      } else {
        setError('Invalid staff ID or password. Please check your credentials and try again.');
      }
    } catch (err) {
      // Error handled silently
      setError('Authentication failed. Please check your credentials and network connection.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePINLogin = async (staffId: string, pin: string): Promise<boolean> => {
    if (!isOnline) {
      setError('Authentication requires network connection. Please check your connection.');
      return false;
    }

    setError('');
    setSuccess('');

    try {
      const user = await AuthService.authenticateCredentials(staffId, '', pin);
      
      if (user) {
        setSuccess(`Authentication successful! Welcome, ${user.name}!`);
        setTimeout(() => {
          onLogin(user);
        }, 1000);
        return true;
      } else {
        setError('Invalid staff ID or PIN. Please check your credentials and try again.');
        return false;
      }
    } catch (err) {
      // Error handled silently
      setError('Authentication failed. Please check your credentials and network connection.');
      return false;
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

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Login Form - Left Side */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-2xl p-8 h-full">
              
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

              {/* Single Page Login Form */}
              <div className="space-y-6">
                <div className="text-center mb-8">
                  <User className="h-16 w-16 text-blue-600 mx-auto mb-4" />
                  <h3 className="text-2xl font-bold text-gray-900 mb-2">Staff Login</h3>
                  <p className="text-gray-600">Enter your credentials to sign in</p>
                </div>

                {/* Staff ID Input - Always visible */}
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
                      onChange={(e) => setStaffId(e.target.value.toUpperCase())}
                      className="w-full pl-12 pr-4 py-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg text-center"
                      placeholder="0001"
                      required
                      autoFocus
                      autoComplete="username"
                    />
                    {isCheckingRole && (
                      <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                        <RefreshCw className="w-5 h-5 animate-spin text-blue-600" />
                      </div>
                    )}
                  </div>
                </div>

                {/* PIN Authentication */}
                {authType === 'pin' && (
                  <div>
                    <PINLogin
                      staffId={staffId}
                      onLogin={handlePINLogin}
                      loading={isLoading}
                      error=""
                      compact={true}
                    />
                  </div>
                )}

                {authType === 'password' && (
                  <form onSubmit={handlePasswordLogin} className="space-y-4">
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
                          className="w-full pl-12 pr-14 py-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-transparent text-lg"
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
                      disabled={isLoading || !password || !staffId.trim() || !isOnline}
                      className={`w-full flex items-center justify-center space-x-3 py-4 px-6 rounded-lg text-lg font-medium transition-colors ${
                        isLoading 
                          ? 'bg-green-400 text-white cursor-not-allowed'
                          : !isOnline || !staffId.trim() || !password
                          ? 'bg-gray-400 text-white cursor-not-allowed'
                          : 'bg-green-600 text-white hover:bg-green-700'
                      }`}
                    >
                      {isLoading ? (
                        <>
                          <RefreshCw className="w-6 h-6 animate-spin" />
                          <span>Authenticating...</span>
                        </>
                      ) : (
                        <>
                          <Shield className="w-6 h-6" />
                          <span>{!isOnline ? 'Offline - Login Unavailable' : 'Sign In Securely'}</span>
                        </>
                      )}
                    </button>
                  </form>
                )}

                {authType === 'unknown' && staffId.trim().length >= 3 && staffId.trim().length < 7 && (
                  <div className="text-center text-gray-500 py-8">
                    <User className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                    <p>Enter a valid Staff ID to continue</p>
                  </div>
                )}

                {authType === 'unknown' && staffId.trim().length < 3 && (
                  <div className="text-center text-gray-400 py-8">
                    <User className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                    <p>Enter your 4-digit Staff ID above</p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Information Panel - Right Side */}
          <div className="space-y-6">
            {/* Authentication Info */}
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
              <div className="flex items-center space-x-3 mb-4">
                <Shield className="w-6 h-6 text-white" />
                <h3 className="text-white font-semibold text-lg">Hybrid Authentication</h3>
              </div>
              <div className="text-blue-100 space-y-3">
                <p className="text-sm"><strong>PIN Login:</strong> Doctors, Nurses, Technicians, etc.</p>
                <p className="text-sm"><strong>Password Login:</strong> Administrators, Provisioners</p>
                <p className="text-sm"><strong>Role-based Access:</strong> System determines auth method automatically</p>
              </div>
            </div>

            {/* Security Features */}
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
              <div className="flex items-center space-x-3 mb-3">
                <Shield className="w-5 h-5 text-green-300" />
                <h4 className="text-white font-medium">Security & Compliance</h4>
              </div>
              <div className="text-blue-100 text-sm space-y-2">
                <p>✓ Backend server authentication</p>
                <p>✓ Role-based authentication types</p>
                <p>✓ Encrypted data transmission</p>
                <p>✓ Session management & auto-logout</p>
                <p>✓ HIPAA compliant audit logs</p>
              </div>
            </div>

            {/* Demo Information */}
            <div className="bg-white/10 backdrop-blur-sm rounded-lg p-6">
              <h4 className="text-white font-medium mb-4">Demo Information</h4>
              <div className="space-y-3 text-blue-200 text-sm">
                <p><strong>Staff ID Format:</strong> 4-digit numbers (0001-9999)</p>
                <p><strong>Admin Password:</strong> hospital123</p>
                <p><strong>PIN Roles:</strong> 6-digit PINs for doctors, nurses, technicians</p>
                <p><strong>Password Roles:</strong> Use demo password for administrators</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
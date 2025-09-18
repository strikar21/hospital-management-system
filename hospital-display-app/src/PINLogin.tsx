import React, { useState, useRef, useEffect } from 'react';
import { Smartphone, Delete, CheckCircle, XCircle } from 'lucide-react';

interface PINLoginProps {
  staffId?: string;
  onLogin: (staffId: string, pin: string) => Promise<boolean>;
  loading: boolean;
  error: string;
  compact?: boolean;
}

const PINLogin: React.FC<PINLoginProps> = ({ staffId: propStaffId, onLogin, loading, error, compact = false }) => {
  const [staffId, setStaffId] = useState('');
  const [pin, setPIN] = useState('');
  const [showPIN, setShowPIN] = useState(compact ? true : false); // Show PIN immediately in compact mode
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

  // Use provided staffId or local state
  const currentStaffId = propStaffId || staffId;
  
  useEffect(() => {
    // Focus first PIN input when staff ID is entered and we show PIN pad
    if (showPIN && inputRefs.current[0]) {
      inputRefs.current[0].focus();
    }
  }, [showPIN]);

  const handleStaffIdSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (staffId.trim()) {
      setShowPIN(true);
      setPIN('');
    }
  };

  const handlePINDigit = (digit: string) => {
    if (pin.length < 4) {
      const newPIN = pin + digit;
      setPIN(newPIN);
      
      // Auto-focus next input
      const nextIndex = newPIN.length;
      if (nextIndex < 4 && inputRefs.current[nextIndex]) {
        inputRefs.current[nextIndex]?.focus();
      }
      
      // Auto-submit when 4 digits entered
      if (newPIN.length === 4) {
        handleLogin(newPIN);
      }
    }
  };

  const handleBackspace = () => {
    if (pin.length > 0) {
      const newPIN = pin.slice(0, -1);
      setPIN(newPIN);
      
      // Focus previous input
      if (inputRefs.current[newPIN.length]) {
        inputRefs.current[newPIN.length]?.focus();
      }
    }
  };

  const handleLogin = async (pinToUse: string = pin) => {
    if (currentStaffId && pinToUse.length === 4) {
      const success = await onLogin(currentStaffId, pinToUse);
      if (!success) {
        setPIN('');
        if (inputRefs.current[0]) {
          inputRefs.current[0].focus();
        }
      }
    }
  };

  const handlePINInputChange = (index: number, value: string) => {
    if (value.length <= 1 && /^\d*$/.test(value)) {
      const newPIN = pin.split('');
      newPIN[index] = value;
      const updatedPIN = newPIN.join('').slice(0, 4);
      setPIN(updatedPIN);
      
      // Auto-focus next input
      if (value && index < 3 && inputRefs.current[index + 1]) {
        inputRefs.current[index + 1]?.focus();
      }
      
      // Auto-submit when 4 digits
      if (updatedPIN.length === 4) {
        handleLogin(updatedPIN);
      }
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !pin[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const resetLogin = () => {
    setStaffId('');
    setPIN('');
    setShowPIN(false);
  };

  // In compact mode, only show PIN input since staffId is provided
  if (compact) {
    return (
      <div className="space-y-4">
        {/* PIN Display */}
        <div>
          <label className="block text-lg font-medium text-gray-700 mb-3">
            PIN ({currentStaffId})
          </label>
          <div className="flex justify-center space-x-3">
            {[0, 1, 2, 3].map((index) => (
              <input
                key={index}
                ref={(el) => { inputRefs.current[index] = el; }}
                type="text"
                value={pin[index] || ''}
                onChange={(e) => handlePINInputChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                className="w-12 h-12 text-2xl text-center border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                maxLength={1}
                inputMode="numeric"
                pattern="[0-9]*"
              />
            ))}
          </div>
        </div>
        
        {/* Number Pad */}
        <div className="grid grid-cols-3 gap-3 max-w-xs mx-auto">
          {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((digit) => (
            <button
              key={digit}
              onClick={() => handlePINDigit(digit.toString())}
              disabled={loading || pin.length >= 4}
              className="h-14 text-xl font-semibold bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
            >
              {digit}
            </button>
          ))}
          <div /> {/* Empty space */}
          <button
            onClick={() => handlePINDigit('0')}
            disabled={loading || pin.length >= 6}
            className="h-14 text-xl font-semibold bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
          >
            0
          </button>
          <button
            onClick={handleBackspace}
            disabled={loading || pin.length === 0}
            className="h-14 flex items-center justify-center bg-red-100 hover:bg-red-200 rounded-lg transition-colors disabled:opacity-50"
          >
            <Delete className="h-6 w-6 text-red-600" />
          </button>
        </div>
        
        {/* Status Messages */}
        {loading && (
          <div className="text-center text-blue-600">
            <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-2"></div>
            Authenticating...
          </div>
        )}
        
        {error && (
          <div className="flex items-center justify-center text-red-600 bg-red-50 p-3 rounded-lg">
            <XCircle className="h-5 w-5 mr-2" />
            {error}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto">
      {/* Staff ID Input */}
      {!showPIN && (
        <form onSubmit={handleStaffIdSubmit} className="space-y-4">
          <div className="text-center mb-6">
            <Smartphone className="h-12 w-12 text-blue-600 mx-auto mb-3" />
            <h2 className="text-xl font-bold text-gray-900">Staff Login</h2>
            <p className="text-gray-600">Enter your Staff ID</p>
          </div>
          
          <div>
            <input
              type="text"
              value={staffId}
              onChange={(e) => setStaffId(e.target.value.toUpperCase())}
              className="w-full px-4 py-3 text-lg border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-center"
              placeholder="DOC00001"
              required
              autoFocus
            />
          </div>
          
          <button
            type="submit"
            disabled={!staffId.trim() || loading}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-6 rounded-lg disabled:opacity-50 transition-colors"
          >
            Continue
          </button>
        </form>
      )}

      {/* PIN Input */}
      {showPIN && (
        <div className="space-y-6">
          <div className="text-center">
            <Smartphone className="h-12 w-12 text-green-600 mx-auto mb-3" />
            <h2 className="text-xl font-bold text-gray-900">Enter PIN</h2>
            <p className="text-gray-600">Staff ID: <span className="font-mono font-semibold">{staffId}</span></p>
            <button
              onClick={resetLogin}
              className="text-blue-600 hover:text-blue-800 text-sm underline mt-1"
            >
              Change Staff ID
            </button>
          </div>
          
          {/* PIN Display */}
          <div className="flex justify-center space-x-3">
            {[0, 1, 2, 3].map((index) => (
              <input
                key={index}
                ref={(el) => { inputRefs.current[index] = el; }}
                type="text"
                value={pin[index] || ''}
                onChange={(e) => handlePINInputChange(index, e.target.value)}
                onKeyDown={(e) => handleKeyDown(index, e)}
                className="w-12 h-12 text-2xl text-center border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
                maxLength={1}
                inputMode="numeric"
                pattern="[0-9]*"
              />
            ))}
          </div>
          
          {/* Number Pad */}
          <div className="grid grid-cols-3 gap-3 max-w-xs mx-auto">
            {[1, 2, 3, 4, 5, 6, 7, 8, 9].map((digit) => (
              <button
                key={digit}
                onClick={() => handlePINDigit(digit.toString())}
                disabled={loading || pin.length >= 4}
                className="h-14 text-xl font-semibold bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
              >
                {digit}
              </button>
            ))}
            <div /> {/* Empty space */}
            <button
              onClick={() => handlePINDigit('0')}
              disabled={loading || pin.length >= 4}
              className="h-14 text-xl font-semibold bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors disabled:opacity-50"
            >
              0
            </button>
            <button
              onClick={handleBackspace}
              disabled={loading || pin.length === 0}
              className="h-14 flex items-center justify-center bg-red-100 hover:bg-red-200 rounded-lg transition-colors disabled:opacity-50"
            >
              <Delete className="h-6 w-6 text-red-600" />
            </button>
          </div>
          
          {/* Status Messages */}
          {loading && (
            <div className="text-center text-blue-600">
              <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-2"></div>
              Authenticating...
            </div>
          )}
          
          {error && (
            <div className="flex items-center justify-center text-red-600 bg-red-50 p-3 rounded-lg">
              <XCircle className="h-5 w-5 mr-2" />
              {error}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PINLogin;
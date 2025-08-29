import React, { useState, useRef, useEffect } from 'react';
import { Shield, Lock, Eye, EyeOff, CheckCircle, XCircle, RefreshCw } from 'lucide-react';

interface PINChangeProps {
  staffId: string;
  onClose: () => void;
  onPINChanged: () => void;
}

const PINChange: React.FC<PINChangeProps> = ({ staffId, onClose, onPINChanged }) => {
  const [currentPIN, setCurrentPIN] = useState('');
  const [newPIN, setNewPIN] = useState('');
  const [confirmPIN, setConfirmPIN] = useState('');
  const [showCurrentPIN, setShowCurrentPIN] = useState(false);
  const [showNewPIN, setShowNewPIN] = useState(false);
  const [showConfirmPIN, setShowConfirmPIN] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const currentPINRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (currentPINRef.current) {
      currentPINRef.current.focus();
    }
  }, []);

  const validatePIN = (pin: string): string | null => {
    if (pin.length !== 6) {
      return 'PIN must be exactly 6 digits';
    }
    if (!/^\d{6}$/.test(pin)) {
      return 'PIN must contain only numbers';
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Validation
    const currentPINError = validatePIN(currentPIN);
    if (currentPINError) {
      setError(`Current PIN: ${currentPINError}`);
      return;
    }

    const newPINError = validatePIN(newPIN);
    if (newPINError) {
      setError(`New PIN: ${newPINError}`);
      return;
    }

    if (newPIN !== confirmPIN) {
      setError('New PIN and confirmation do not match');
      return;
    }

    if (currentPIN === newPIN) {
      setError('New PIN must be different from current PIN');
      return;
    }

    setIsLoading(true);

    try {
      // Note: This endpoint would need to be implemented in the backend
      const response = await fetch(`${process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001'}/api/v1/staff/${staffId}/change-pin`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          currentPin: currentPIN,
          newPin: newPIN
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'PIN change failed');
      }

      setSuccess('PIN changed successfully!');
      setTimeout(() => {
        onPINChanged();
        onClose();
      }, 2000);

    } catch (err) {
      console.error('PIN change error:', err);
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to change PIN. Please try again.');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handlePINInput = (value: string, setter: (value: string) => void) => {
    // Only allow digits and limit to 6 characters
    const numericValue = value.replace(/\D/g, '').slice(0, 6);
    setter(numericValue);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div className="flex items-center space-x-3 mb-6">
          <Shield className="w-8 h-8 text-blue-600" />
          <div>
            <h2 className="text-xl font-bold text-gray-900">Change PIN</h2>
            <p className="text-gray-600">Staff ID: {staffId}</p>
          </div>
        </div>

        {/* Status Messages */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center space-x-2">
            <XCircle className="w-5 h-5 text-red-600 flex-shrink-0" />
            <span className="text-red-700 text-sm">{error}</span>
          </div>
        )}

        {success && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center space-x-2">
            <CheckCircle className="w-5 h-5 text-green-600 flex-shrink-0" />
            <span className="text-green-700 text-sm">{success}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Current PIN */}
          <div>
            <label htmlFor="currentPIN" className="block text-sm font-medium text-gray-700 mb-2">
              Current PIN
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                id="currentPIN"
                ref={currentPINRef}
                type={showCurrentPIN ? 'text' : 'password'}
                value={currentPIN}
                onChange={(e) => handlePINInput(e.target.value, setCurrentPIN)}
                className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-lg text-center font-mono"
                placeholder="••••••"
                maxLength={6}
                inputMode="numeric"
                pattern="[0-9]*"
                required
                autoComplete="off"
              />
              <button
                type="button"
                onClick={() => setShowCurrentPIN(!showCurrentPIN)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showCurrentPIN ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">Enter your current 6-digit PIN</p>
          </div>

          {/* New PIN */}
          <div>
            <label htmlFor="newPIN" className="block text-sm font-medium text-gray-700 mb-2">
              New PIN
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                id="newPIN"
                type={showNewPIN ? 'text' : 'password'}
                value={newPIN}
                onChange={(e) => handlePINInput(e.target.value, setNewPIN)}
                className="w-full pl-10 pr-12 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-lg text-center font-mono"
                placeholder="••••••"
                maxLength={6}
                inputMode="numeric"
                pattern="[0-9]*"
                required
                autoComplete="off"
              />
              <button
                type="button"
                onClick={() => setShowNewPIN(!showNewPIN)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showNewPIN ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-1">Choose a new 6-digit PIN (numbers only)</p>
          </div>

          {/* Confirm PIN */}
          <div>
            <label htmlFor="confirmPIN" className="block text-sm font-medium text-gray-700 mb-2">
              Confirm New PIN
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                id="confirmPIN"
                type={showConfirmPIN ? 'text' : 'password'}
                value={confirmPIN}
                onChange={(e) => handlePINInput(e.target.value, setConfirmPIN)}
                className={`w-full pl-10 pr-12 py-3 border rounded-lg focus:ring-2 text-lg text-center font-mono ${
                  confirmPIN && newPIN !== confirmPIN
                    ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                    : confirmPIN && newPIN === confirmPIN
                    ? 'border-green-300 focus:ring-green-500 focus:border-green-500'
                    : 'border-gray-300 focus:ring-blue-500 focus:border-blue-500'
                }`}
                placeholder="••••••"
                maxLength={6}
                inputMode="numeric"
                pattern="[0-9]*"
                required
                autoComplete="off"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPIN(!showConfirmPIN)}
                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showConfirmPIN ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
            {confirmPIN && (
              <p className={`text-xs mt-1 ${
                newPIN === confirmPIN ? 'text-green-600' : 'text-red-600'
              }`}>
                {newPIN === confirmPIN ? '✓ PINs match' : '✗ PINs do not match'}
              </p>
            )}
          </div>

          {/* Security Notice */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <div className="flex items-start space-x-2">
              <Shield className="w-5 h-5 text-blue-600 mt-0.5" />
              <div className="text-blue-800 text-sm">
                <p className="font-medium mb-1">Security Guidelines:</p>
                <ul className="text-xs space-y-1">
                  <li>• Use a unique 6-digit PIN that you can remember</li>
                  <li>• Avoid using obvious numbers (123456, 111111, etc.)</li>
                  <li>• Keep your PIN confidential</li>
                </ul>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex space-x-4 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !currentPIN || !newPIN || !confirmPIN || newPIN !== confirmPIN}
              className={`flex-1 px-4 py-3 rounded-lg font-medium transition-colors flex items-center justify-center space-x-2 ${
                isLoading || !currentPIN || !newPIN || !confirmPIN || newPIN !== confirmPIN
                  ? 'bg-gray-400 text-white cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              {isLoading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Changing PIN...</span>
                </>
              ) : (
                <>
                  <Shield className="w-4 h-4" />
                  <span>Change PIN</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default PINChange;
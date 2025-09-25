// SettingsPanel.tsx - Dashboard settings configuration component
import React from 'react';
import { X, Monitor } from 'lucide-react';
import { user, appsettings, patient } from '../../types';

interface SettingsPanelProps {
  isOpen: boolean;
  currentUser: user;
  settings: appsettings;
  patients: patient[];
  onClose: () => void;
  onUpdateSettings: (settings: appsettings) => void;
  onBedsideMode: () => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
  isOpen,
  currentUser,
  settings,
  patients,
  onClose,
  onUpdateSettings,
  onBedsideMode
}) => {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-[60]"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
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
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 p-1 hover:bg-gray-100 rounded transition-colors"
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
                  checked={settings.enableautoscroll || false}
                  onChange={(e) => onUpdateSettings({
                    ...settings,
                    enableautoscroll: e.target.checked
                  })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  aria-describedby="autoscroll-description"
                  aria-label="Enable automatic scrolling of patient list"
                />
                <span className="text-sm">Enable auto-scroll for patient rows</span>
              </label>

              {settings.enableautoscroll && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Scroll speed (pixels/second):
                  </label>
                  <select
                    value={settings.autoscrollspeed || 30}
                    onChange={(e) => onUpdateSettings({
                      ...settings,
                      autoscrollspeed: parseInt(e.target.value)
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
                  checked={settings.enableautologout}
                  onChange={(e) => onUpdateSettings({
                    ...settings,
                    enableautologout: e.target.checked
                  })}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="text-sm">Enable auto-logout after inactivity</span>
              </label>

              {settings.enableautologout && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Auto-logout after (minutes):
                  </label>
                  <select
                    value={settings.autologoutminutes}
                    onChange={(e) => onUpdateSettings({
                      ...settings,
                      autologoutminutes: parseInt(e.target.value)
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
                onClick={onBedsideMode}
                disabled={patients.length === 0}
                className="w-full flex items-center justify-center space-x-2 p-3 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
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
              <p><strong>Auto-logout:</strong> {settings.enableautologout ? `Enabled (${settings.autologoutminutes}min)` : 'Disabled'}</p>
              <p><strong>Auto-scroll:</strong> {settings.enableautoscroll ? `Enabled (${settings.autoscrollspeed || 30}px/s)` : 'Disabled'}</p>
              <p><strong>Layout:</strong> 2 cards per row (same direction scrolling)</p>
              <p><strong>Patients:</strong> {patients.length} loaded</p>
            </div>
          </div>
        </div>

        <div className="flex space-x-3 mt-6">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Apply & Close
          </button>
        </div>
      </div>
    </div>
  );
};
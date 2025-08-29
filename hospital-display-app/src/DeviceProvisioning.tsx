import React, { useState } from 'react';
import { 
  Watch, Save, X, Activity, MapPin, Battery, 
  CheckCircle, AlertCircle, Wifi, Settings, Plus
} from 'lucide-react';
import { User as UserType } from './types';
import { HospitalAPI } from './api';

interface DeviceProvisioningProps {
  currentUser: UserType;
  onBack: () => void;
}

export const DeviceProvisioning: React.FC<DeviceProvisioningProps> = ({ 
  currentUser, 
  onBack 
}) => {
  const [formData, setFormData] = useState({
    deviceId: '',
    name: '',
    deviceType: 'watch',
    location: 'ICU',
    macAddress: '',
    ipAddress: '',
    firmwareVersion: ''
  });
  
  const [loading, setLoading] = useState(false);
  const [showSuccess, setShowSuccess] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const showMessage = (message: string, isError = false) => {
    if (isError) {
      setError(message);
      setTimeout(() => setError(null), 5000);
    } else {
      setShowSuccess(message);
      setTimeout(() => setShowSuccess(null), 3000);
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  // Device ID generation removed - backend handles device ID assignment

  // Device name generation removed - backend handles device naming

  const provisionDevice = async () => {
    // Validation
    if (!formData.deviceId && !formData.name) {
      showMessage('Please provide at least Device ID or Name (others will be auto-generated)', true);
      return;
    }

    setLoading(true);
    try {
      // Backend will assign device ID and name - no frontend generation
      
      const deviceData = {
        // Backend will generate deviceId and name
        deviceType: formData.deviceType,
        location: formData.location,
        macAddress: formData.macAddress || undefined,
        ipAddress: formData.ipAddress || undefined,
        firmwareVersion: formData.firmwareVersion || undefined,
        provisionedBy: currentUser.staffId
      };

      const response = await fetch(`/api/v1/provisioning/devices?staffId=${currentUser.staffId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(deviceData)
      });

      if (response.ok) {
        const result = await response.json();
        showMessage(`Device provisioned successfully! Backend assigned ID: ${result.deviceId}`);
        console.log('Device provisioned:', result);
        
        // Reset form
        setFormData({
          deviceId: '',
          name: '',
          deviceType: 'watch',
          location: 'ICU',
          macAddress: '',
          ipAddress: '',
          firmwareVersion: ''
        });
      } else {
        const errorData = await response.json();
        showMessage(errorData.detail || 'Failed to provision device', true);
      }
    } catch (error: any) {
      console.error('Error provisioning device:', error);
      showMessage('Failed to provision device', true);
    }
    setLoading(false);
  };

  const deviceTypes = [
    { value: 'watch', label: 'Patient Watch', icon: Watch },
    { value: 'vitalMonitor', label: 'Vital Monitor', icon: Activity },
    { value: 'doorScanner', label: 'Door Scanner', icon: Settings },
    { value: 'tablet', label: 'Medical Tablet', icon: Settings }
  ];

  const locations = [
    'ICU', 'Emergency', 'General Ward', 'Pediatric Ward',
    'Maternity Ward', 'Surgical Ward', 'Cardiac Care Unit',
    'Neurology Ward', 'Orthopedic Ward', 'Oncology Ward'
  ];

  const getDeviceIcon = (deviceType: string) => {
    const iconMap = {
      'watch': Watch,
      'vitalMonitor': Activity,
      'doorScanner': Settings,
      'tablet': Settings
    };
    return iconMap[deviceType as keyof typeof iconMap] || Activity;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={onBack}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
                  <Plus className="w-7 h-7 text-green-600" />
                  <span>Device Provisioning</span>
                </h1>
                <p className="text-sm text-gray-600">Add new devices to the hospital system</p>
              </div>
            </div>
            <div className="text-sm text-gray-600">
              Tech: <span className="font-medium">{currentUser.name}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Success/Error Messages */}
      {showSuccess && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
            <CheckCircle className="w-5 h-5 inline mr-2" />
            {showSuccess}
          </div>
        </div>
      )}
      {error && (
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
            <AlertCircle className="w-5 h-5 inline mr-2" />
            {error}
          </div>
        </div>
      )}

      {/* Provisioning Form */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Device Information</h2>
            <p className="text-sm text-gray-600 mt-1">Fields marked with * are auto-generated if empty</p>
          </div>
          
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Device Type */}
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-3">
                  Device Type *
                </label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {deviceTypes.map((type) => {
                    const IconComponent = type.icon;
                    return (
                      <div
                        key={type.value}
                        onClick={() => handleInputChange('deviceType', type.value)}
                        className={`p-4 border-2 rounded-lg cursor-pointer transition-all hover:border-blue-300 ${
                          formData.deviceType === type.value
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:bg-gray-50'
                        }`}
                      >
                        <div className="flex flex-col items-center space-y-2">
                          <IconComponent className={`w-8 h-8 ${
                            formData.deviceType === type.value ? 'text-blue-600' : 'text-gray-500'
                          }`} />
                          <span className={`text-sm font-medium text-center ${
                            formData.deviceType === type.value ? 'text-blue-900' : 'text-gray-700'
                          }`}>
                            {type.label}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Device ID */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Device ID *
                </label>
                <input
                  type="text"
                  value={formData.deviceId}
                  onChange={(e) => handleInputChange('deviceId', e.target.value)}
                  placeholder="Auto-generated if empty"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
                <p className="text-xs text-gray-500 mt-1">e.g., WATCH_123456</p>
              </div>

              {/* Device Name */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Device Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                  placeholder="Auto-generated if empty"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
                <p className="text-xs text-gray-500 mt-1">e.g., Patient Watch #001</p>
              </div>

              {/* Location */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Location
                </label>
                <select
                  value={formData.location}
                  onChange={(e) => handleInputChange('location', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                >
                  {locations.map(location => (
                    <option key={location} value={location}>{location}</option>
                  ))}
                </select>
              </div>

              {/* MAC Address */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  MAC Address
                </label>
                <input
                  type="text"
                  value={formData.macAddress}
                  onChange={(e) => handleInputChange('macAddress', e.target.value)}
                  placeholder="00:11:22:33:44:55"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
              </div>

              {/* IP Address */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  IP Address
                </label>
                <input
                  type="text"
                  value={formData.ipAddress}
                  onChange={(e) => handleInputChange('ipAddress', e.target.value)}
                  placeholder="192.168.1.100"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
              </div>

              {/* Firmware Version */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Firmware Version
                </label>
                <input
                  type="text"
                  value={formData.firmwareVersion}
                  onChange={(e) => handleInputChange('firmwareVersion', e.target.value)}
                  placeholder="v1.0.0"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-green-500"
                />
              </div>
            </div>

            {/* Preview */}
            {(formData.deviceId || formData.name) && (
              <div className="mt-8 p-4 bg-gray-50 rounded-lg border">
                <h3 className="text-sm font-medium text-gray-900 mb-3">Device Preview</h3>
                <div className="flex items-center space-x-4">
                  {React.createElement(getDeviceIcon(formData.deviceType), {
                    className: "w-8 h-8 text-blue-600"
                  })}
                  <div>
                    <div className="font-medium text-gray-900">
                      {formData.name || 'Name will be assigned by backend'}
                    </div>
                    <div className="text-sm text-gray-600">
                      ID: {formData.deviceId || 'ID will be assigned by backend'}
                    </div>
                    <div className="text-sm text-gray-500">
                      Type: {formData.deviceType} • Location: {formData.location}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex justify-end space-x-4 mt-8 pt-6 border-t border-gray-200">
              <button
                onClick={onBack}
                className="px-6 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
              >
                Cancel
              </button>
              <button
                onClick={provisionDevice}
                disabled={loading}
                className="px-6 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
              >
                <Save className="w-4 h-4" />
                <span>{loading ? 'Provisioning...' : 'Provision Device'}</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
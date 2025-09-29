import React from 'react';
import { X, RefreshCw } from 'lucide-react';
import { user as UserType } from '../../types';

interface DeviceAssignmentHeaderProps {
  currentUser: UserType;
  loading: boolean;
  onBack: () => void;
  onRefresh: () => void;
}

export const DeviceAssignmentHeader: React.FC<DeviceAssignmentHeaderProps> = ({
  currentUser,
  loading,
  onBack,
  onRefresh
}) => {
  return (
    <div className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          <div className="flex items-center space-x-4">
            <button
              onClick={onBack}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
            >
              <X className="w-5 h-5" />
            </button>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Device Assignment</h1>
              <p className="text-sm text-gray-600">Manage patient device assignments</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <button
              onClick={onRefresh}
              disabled={loading}
              className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg"
            >
              <RefreshCw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
            </button>
            <div className="text-sm text-gray-600">
              Logged in as: <span className="font-medium">{currentUser.name}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
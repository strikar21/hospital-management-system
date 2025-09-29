/**
 * EmptyState - Empty state display for Dashboard when no patients found
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade empty state with context-aware messages and actions
 */

import React from 'react';
import { Users, RefreshCw, Activity } from 'lucide-react';
import { user, roomproximity } from '../../types';
import { PermissionUtils } from '../../utils/permissionUtils';

interface EmptyStateProps {
  currentUser: user;
  selectedWard: string;
  roomProximity: roomproximity | null;
  proximityScanning: boolean;
  onDetectProximity: () => void;
  onRefreshData: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  currentUser,
  selectedWard,
  roomProximity,
  proximityScanning,
  onDetectProximity,
  onRefreshData
}) => {
  const isNurseOrTechnician = PermissionUtils.isNurseOrTechnician(currentUser.role);

  const getEmptyStateMessage = () => {
    if (isNurseOrTechnician && !roomProximity) {
      return {
        title: 'Room Location Not Detected',
        description: 'Move this tablet to a patient room. The system will automatically detect which patients are present via their wearables.',
        showProximityButton: true
      };
    } else if (isNurseOrTechnician && roomProximity) {
      return {
        title: 'No Patients Found',
        description: `No patients with wearables detected in ${roomProximity.tabletLocation}. Patients may not be wearing their devices.`,
        showProximityButton: true
      };
    } else if (selectedWard === 'My Patients') {
      return {
        title: 'No Patients Found',
        description: `No patients found in your ${currentUser.role === 'Doctor' ? 'department' : 'assigned area'}.`,
        showProximityButton: false
      };
    } else if (selectedWard === 'All') {
      return {
        title: 'No Patients Found',
        description: 'No patients are currently in the system.',
        showProximityButton: false
      };
    } else {
      return {
        title: 'No Patients Found',
        description: `No patients found in ${selectedWard} ward.`,
        showProximityButton: false
      };
    }
  };

  const { title, description, showProximityButton } = getEmptyStateMessage();

  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <Users className="w-12 h-12 text-gray-400 mx-auto mb-4" />
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          {title}
        </h3>
        <p className="text-gray-600 mb-4">
          {description}
        </p>
        {showProximityButton ? (
          <div className="space-y-3">
            <button
              onClick={onDetectProximity}
              disabled={proximityScanning}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-blue-400"
            >
              {proximityScanning ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin inline mr-2" />
                  Detecting Room Location...
                </>
              ) : (
                <>
                  <Activity className="w-5 h-5 inline mr-2" />
                  Detect Room & Patients Now
                </>
              )}
            </button>
            <p className="text-xs text-gray-500 max-w-md mx-auto">
              💡 Tip: The system automatically scans every 10 seconds when you're logged in as nursing staff
            </p>
          </div>
        ) : (
          <button
            onClick={onRefreshData}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Refresh Data
          </button>
        )}
      </div>
    </div>
  );
};
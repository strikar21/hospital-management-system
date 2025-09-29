import React from 'react';
import { Watch, Trash2 } from 'lucide-react';

interface DeviceAssignmentRecord {
  id: number;
  deviceId: string;
  patientId: string;
  performedBy: string;
  assignmentReason: string;
  assignedAt: string;
  status: string;
  deviceName: string;
  deviceType: string;
  patientName?: string;
  location?: string;
  watchDisplay?: string;
  serialNumber?: string;
  connectionStatus?: string;
  batteryLevel?: number | null;
}

interface AssignedDevicesTabProps {
  assignedDevices: DeviceAssignmentRecord[];
  loading: boolean;
  onUnassign: (deviceId: string, reason?: string) => void;
}

export const AssignedDevicesTab: React.FC<AssignedDevicesTabProps> = ({
  assignedDevices,
  loading,
  onUnassign
}) => {
  const handleUnassign = (assignment: DeviceAssignmentRecord) => {
    if (window.confirm(`Unassign device ${assignment.deviceName} from patient ${assignment.patientName}?`)) {
      onUnassign(assignment.deviceId, 'manual_unassignment');
    }
  };

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Currently Assigned Devices</h2>
        <p className="text-sm text-gray-600 mt-1">
          Devices currently assigned to patients - ready for unassignment on discharge
        </p>
      </div>

      {assignedDevices.length > 0 ? (
        <div className="divide-y divide-gray-200">
          {assignedDevices.map((assignment) => (
            <div key={assignment.id} className="p-6 hover:bg-gray-50">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="flex-shrink-0">
                    <Watch className="w-8 h-8 text-blue-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">
                      {assignment.deviceName}
                    </h3>
                    <p className="text-sm text-gray-600">
                      Patient: <span className="font-medium">{assignment.patientName}</span>
                    </p>
                    <p className="text-sm text-gray-600">
                      Location: {assignment.location}
                    </p>
                    <p className="text-sm text-gray-600">
                      Assigned: {new Date(assignment.assignedAt).toLocaleDateString()} by {assignment.performedBy}
                    </p>
                    <p className="text-sm text-gray-600">
                      Reason: {assignment.assignmentReason}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-3">
                  <div className="text-right">
                    <span className={`inline-block px-2 py-1 text-xs font-medium rounded-full ${
                      assignment.status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {assignment.status}
                    </span>
                    {assignment.batteryLevel && (
                      <p className="text-sm text-gray-600 mt-1">
                        Battery: {assignment.batteryLevel}%
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => handleUnassign(assignment)}
                    disabled={loading}
                    className="p-2 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-lg transition-colors"
                    title="Unassign device"
                  >
                    <Trash2 className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <Watch className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <p className="text-gray-500 text-lg">No assigned devices</p>
          <p className="text-gray-400 text-sm">All devices are available for assignment</p>
        </div>
      )}
    </div>
  );
};
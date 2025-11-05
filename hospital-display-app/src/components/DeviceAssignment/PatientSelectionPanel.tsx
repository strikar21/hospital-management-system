import React from 'react';
import { Search, User, UserCheck } from 'lucide-react';
import { patient } from '../../types';

interface PatientSelectionPanelProps {
  patients: patient[];
  selectedPatient: string;
  selectedDevice: string;
  assignmentReason: string;
  searchTerm: string;
  patientFilter: string;
  wardFilter: string;
  loading: boolean;
  onPatientSelect: (patientId: string) => void;
  onSearchChange: (term: string) => void;
  onPatientFilterChange: (filter: string) => void;
  onWardFilterChange: (filter: string) => void;
  onAssignmentReasonChange: (reason: string) => void;
  onAssign: () => void;
}

export const PatientSelectionPanel: React.FC<PatientSelectionPanelProps> = ({
  patients,
  selectedPatient,
  selectedDevice,
  assignmentReason,
  searchTerm,
  patientFilter,
  wardFilter,
  loading,
  onPatientSelect,
  onSearchChange,
  onPatientFilterChange,
  onWardFilterChange,
  onAssignmentReasonChange,
  onAssign
}) => {
  const getUniqueWards = () => {
    const wards = patients.map(p => p.ward).filter(Boolean);
    return Array.from(new Set(wards));
  };

  return (
    <div className="bg-white rounded-lg shadow p-6 flex flex-col max-h-[calc(100vh-180px)]">
      {/* Header and Filters - Fixed at top */}
      <div className="flex-shrink-0">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          Select Patient ({patients.length})
        </h2>

        {/* Patient Search and Filters */}
        <div className="mb-4 space-y-3">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-gray-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search patients by name, ID, or bed..."
            className="pl-10 pr-4 py-2 w-full border border-gray-300 rounded-md"
          />
        </div>

        {/* Patient Filters */}
        <div className="flex space-x-2">
          <select
            value={patientFilter}
            onChange={(e) => onPatientFilterChange(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
          >
            <option value="all">All Patients</option>
            <option value="unassigned">Unassigned</option>
            <option value="assigned">Already Assigned</option>
          </select>
          <select
            value={wardFilter}
            onChange={(e) => onWardFilterChange(e.target.value)}
            className="flex-1 px-3 py-2 border border-gray-300 rounded-md text-sm"
          >
            <option value="all">All Wards</option>
            {getUniqueWards().map(ward => (
              <option key={ward} value={ward}>{ward}</option>
            ))}
          </select>
        </div>
      </div>
      </div>

      {/* Patient List - Scrollable, takes remaining space */}
      <div className="flex-1 overflow-y-auto min-h-0 space-y-2 mb-4">
        {patients.map((patient) => (
          <div
            key={patient.id}
            onClick={() => onPatientSelect(patient.id)}
            className={`p-3 border rounded-lg cursor-pointer transition-colors ${
              selectedPatient === patient.id
                ? 'border-blue-500 bg-blue-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="relative">
                  <User className="w-5 h-5 text-gray-600" />
                  {patient.assignedDeviceId && (
                    <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-blue-500 border-2 border-white" title="Already has device"></div>
                  )}
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-gray-900">{patient.name}</span>
                    {patient.assignedDeviceId && (
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                        Has Device
                      </span>
                    )}
                  </div>
                  <div className="text-sm text-gray-600">
                    Room {patient.roomNumber} - Bed {patient.bedNumber}
                  </div>
                  <div className="text-sm text-gray-600">{patient.ward}</div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {patient.assignedDeviceId ? (
                  <UserCheck className="w-4 h-4 text-blue-500" />
                ) : (
                  <User className="w-4 h-4 text-gray-400" />
                )}
              </div>
            </div>
          </div>
        ))}
        {patients.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <User className="w-12 h-12 mx-auto mb-3 text-gray-300" />
            <p>No patients found</p>
            <p className="text-sm">Try adjusting your search or filters</p>
          </div>
        )}
      </div>

      {/* Assignment Controls - Fixed at bottom */}
      <div className="flex-shrink-0 border-t pt-4">
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Assignment Reason
          </label>
          <select
            value={assignmentReason}
            onChange={(e) => onAssignmentReasonChange(e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md"
          >
            <option value="patientAdmission">Patient Admission</option>
            <option value="deviceReplacement">Device Replacement</option>
            <option value="monitoring">Enhanced Monitoring</option>
            <option value="emergency">Emergency Assignment</option>
          </select>
        </div>

        <button
          onClick={onAssign}
          disabled={!selectedDevice || !selectedPatient || loading}
          className={`w-full py-2 px-4 rounded-md font-medium ${
            selectedDevice && selectedPatient && !loading
              ? 'bg-blue-600 text-white hover:bg-blue-700'
              : 'bg-gray-300 text-gray-500 cursor-not-allowed'
          }`}
        >
          {loading ? 'Assigning...' : 'Assign Device'}
        </button>
      </div>
    </div>
  );
};
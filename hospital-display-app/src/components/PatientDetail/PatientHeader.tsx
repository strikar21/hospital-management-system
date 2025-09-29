/**
 * PatientHeader - Patient detail header component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade patient header with safety indicators and discharge workflow
 */

import React from 'react';
import { ChevronLeft, Shield, X } from 'lucide-react';
import { patient, user } from '../../types';
import { getStatusColor, formatTimeOnly } from '../../utils';

interface PatientHeaderProps {
  patient: patient;
  currentUser: user;
  onClose: () => void;
  onPatientDischarge?: (patientId: string) => void;
}

export const PatientHeader: React.FC<PatientHeaderProps> = ({
  patient,
  currentUser,
  onClose,
  onPatientDischarge
}) => {

  // Discharge workflow handlers
  const handleDoctorRequestDischarge = async () => {
    if (window.confirm(`Request discharge for ${patient.name}?\n\nThis will:\n• Send request to Hospital Administration for approval\n• Patient will remain active until fully processed\n\nConfirm discharge request?`)) {
      try {
        const response = await fetch(`/api/v2/patients/${patient.id}/discharge-request`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            doctorId: currentUser.id,
            reason: 'Medical discharge - patient condition stable'
          })
        });
        if (response.ok) {
          // Success - no second popup needed, user will see status change
        } else {
          throw new Error('Request failed');
        }
      } catch (error) {
        alert('Failed to submit discharge request. Please try again.');
      }
    }
  };

  const handleAdminApproveDischarge = async () => {
    if (window.confirm(`Approve discharge for ${patient.name}?\n\nThis confirms:\n• Insurance/billing clearance\n• Administrative approval\n• Ready for nurse to complete discharge\n\nApprove discharge?`)) {
      try {
        const response = await fetch(`/api/v2/patients/${patient.id}/discharge-approve`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            adminId: currentUser.id,
            approvalNote: 'Insurance cleared, billing completed, discharge approved'
          })
        });
        if (response.ok) {
          // Success - no second popup needed, user will see status change
        } else {
          throw new Error('Approval failed');
        }
      } catch (error) {
        alert('Failed to approve discharge. Please try again.');
      }
    }
  };

  const handleNurseCompleteDischarge = async () => {
    if (window.confirm(`Complete discharge for ${patient.name}?\n\nThis will:\n• Remove patient from active list\n• Free up bed and equipment\n• Generate discharge summary\n• Complete the discharge process\n\nComplete discharge?`)) {
      try {
        const response = await fetch(`/api/v2/patients/${patient.id}/discharge-complete`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            nurseId: currentUser.id,
            completionNote: 'Patient discharge completed successfully'
          })
        });
        if (response.ok) {
          // Success - trigger parent callback if provided
          if (onPatientDischarge) {
            onPatientDischarge(patient.id);
          }
        } else {
          throw new Error('Completion failed');
        }
      } catch (error) {
        alert('Failed to complete discharge. Please try again.');
      }
    }
  };

  // Discharge workflow button renderer
  const renderDischargeWorkflowButton = () => {
    const dischargeStatus = patient.status || 'active';

    if (currentUser.role === 'Doctor') {
      if (dischargeStatus === 'active') {
        return (
          <button
            onClick={handleDoctorRequestDischarge}
            className="flex items-center space-x-1 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
            title="Request Discharge"
          >
            <X className="w-4 h-4" />
            <span>Request Discharge</span>
          </button>
        );
      } else if (dischargeStatus === 'pendingDischarge') {
        return <div className="text-xs text-yellow-600 px-2 py-1 bg-yellow-100 rounded">Discharge Requested - Awaiting Admin</div>;
      } else {
        return <div className="text-xs text-green-600 px-2 py-1 bg-green-100 rounded">Discharge in Progress</div>;
      }
    } else if (currentUser.role === 'Administrator') {
      if (dischargeStatus === 'pendingDischarge') {
        return (
          <button
            onClick={handleAdminApproveDischarge}
            className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
            title="Approve Discharge"
          >
            <X className="w-4 h-4" />
            <span>Approve Discharge</span>
          </button>
        );
      } else if (dischargeStatus === 'readyForNurse' || dischargeStatus === 'dischargeApproved') {
        return <div className="text-xs text-green-600 px-2 py-1 bg-green-100 rounded">Approved - Awaiting Nurse</div>;
      } else {
        return <div className="text-xs text-gray-500">No pending requests</div>;
      }
    } else if (currentUser.role === 'Nurse') {
      if (dischargeStatus === 'readyForNurse' || dischargeStatus === 'dischargeApproved') {
        return (
          <button
            onClick={handleNurseCompleteDischarge}
            className="flex items-center space-x-1 px-3 py-1 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
            title="Complete Discharge"
          >
            <X className="w-4 h-4" />
            <span>Complete Discharge</span>
          </button>
        );
      } else {
        return <div className="text-xs text-gray-500">No approved discharges</div>;
      }
    } else {
      return <div className="text-xs text-gray-500">Role: {currentUser.role}</div>;
    }
  };

  return (
    <div className="p-3 border-b flex items-center justify-between bg-white sticky top-0 z-10">
      <div className="flex items-center space-x-3">
        <button
          onClick={onClose}
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          title="Close"
        >
          <ChevronLeft className="w-5 h-5 text-gray-600" />
        </button>
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-1">
            <h2 className="text-xl font-bold text-gray-900">{patient.name}</h2>

            {/* Critical Safety Indicators */}
            <div className="flex items-center space-x-2">
              {/* Code Status */}
              {patient.codeStatus && (
                <div className={`px-2 py-1 rounded text-xs font-bold ${
                  patient.codeStatus === 'dnr' ? 'bg-purple-100 text-purple-800 border-2 border-purple-400' :
                  patient.codeStatus === 'dnrcca' ? 'bg-purple-100 text-purple-800 border-2 border-purple-400' :
                  patient.codeStatus === 'comfortcare' ? 'bg-blue-100 text-blue-800 border-2 border-blue-400' :
                  'bg-green-100 text-green-800 border-2 border-green-400'
                }`}>
                  {patient.codeStatus === 'fullcode' ? 'FULL CODE' :
                   patient.codeStatus === 'dnr' ? 'DNR' :
                   patient.codeStatus === 'dnrcca' ? 'DNR/CCA' :
                   'COMFORT CARE'}
                </div>
              )}

              {/* Fall Risk */}
              {patient.vitals?.fallRisk === 'high' && (
                <div className="px-2 py-1 rounded text-xs font-bold bg-red-100 text-red-800 border-2 border-red-400 animate-pulse">
                  🚨 FALL RISK
                </div>
              )}

              {/* Allergy Alert */}
              {patient.allergies && patient.allergies.length > 0 && (
                <div className="px-2 py-1 rounded text-xs font-bold bg-red-100 text-red-800 border-2 border-red-400">
                  🚨 ALLERGIES ({patient.allergies.length})
                </div>
              )}
            </div>
          </div>

          <p className="text-sm text-gray-600">
            {patient.age}y • {patient.gender} • {patient.weight}kg • Bed {patient.bedNumber} • Room {patient.room}
          </p>

          {/* Active Problems List */}
          {patient.activeProblems && patient.activeProblems.length > 0 && (
            <div className="mt-1">
              <span className="text-xs text-gray-500 font-medium">Active Problems: </span>
              <span className="text-xs text-gray-700">
                {patient.activeProblems.join(', ')}
              </span>
            </div>
          )}

          {/* Next Medication Due */}
          {patient.nextMedicationDue && (
            <div className="mt-1">
              <span className="text-xs text-blue-600 font-medium">
                💊 Next medication due: {new Date(patient.nextMedicationDue).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
              </span>
            </div>
          )}
        </div>
      </div>
      <div className="flex items-center space-x-3">
        <div className={`px-3 py-1 rounded-full text-xs font-medium border ${getStatusColor(patient.status)}`}>
          {patient.status.toUpperCase()}
        </div>
        {renderDischargeWorkflowButton()}
        <div className="text-xs text-gray-500">
          Updated: {formatTimeOnly((patient.vitals?.lastDataReceived || new Date()).toString())}
        </div>
        <div className="text-xs text-gray-500">
          <Shield className="w-4 h-4 inline mr-1" />
          HIPAA Compliant
        </div>
      </div>
    </div>
  );
};
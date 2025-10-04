import React from 'react';
import {
  Heart, XCircle, Save, X, Plus
} from 'lucide-react';
import { patient, user, therapy, caseSheetEntry } from '../types';
import { PermissionUtils } from '../utils/permissionUtils';
import { usePatientTherapies } from '../hooks/usePatientTherapies';

interface PatientTherapiesProps {
  patient: patient;
  currentUser: user;
  therapies: therapy[];
  setTherapies: React.Dispatch<React.SetStateAction<therapy[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
  setCaseEntries: React.Dispatch<React.SetStateAction<caseSheetEntry[]>>;
}

const PatientTherapies: React.FC<PatientTherapiesProps> = ({
  patient,
  currentUser,
  therapies,
  setTherapies,
  addCaseSheetEntry,
  setCaseEntries
}) => {
  const {
    isAddingTherapy,
    setIsAddingTherapy,
    newTherapy,
    setNewTherapy,
    addingTherapy,
    handleAddTherapy,
    handleCancelAddTherapy,
    handleAddTherapySession,
    handleCompleteTherapy,
    handleCancelTherapy
  } = usePatientTherapies({
    patient,
    currentUser,
    therapies,
    setTherapies,
    addCaseSheetEntry,
    setCaseEntries
  });

  return (
    <div className="p-4 h-full flex flex-col">
      {PermissionUtils.canEditMedications(currentUser.role) && (
        <div className="flex justify-end mb-3">
          <button
            onClick={() => setIsAddingTherapy(true)}
            className="flex items-center space-x-2 px-3 py-1 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm"
          >
            <Heart className="w-4 h-4" />
            <span>Prescribe</span>
          </button>
        </div>
      )}

      {/* Add Therapy Form */}
      {isAddingTherapy && PermissionUtils.canEditMedications(currentUser.role) && (
        <div className="mb-3 p-3 bg-purple-50 rounded-lg border">
          <h4 className="font-medium mb-2 text-sm">Prescribe New Therapy</h4>
          <div className="grid grid-cols-2 gap-2">
            <select
              value={newTherapy.type}
              onChange={(e) => setNewTherapy(prev => ({ ...prev, type: e.target.value as any }))}
              className="px-2 py-1 border rounded text-sm"
            >
              <option value="physiotherapy">Physiotherapy</option>
              <option value="occupational">Occupational Therapy</option>
              <option value="speech">Speech Therapy</option>
              <option value="respiratory">Respiratory Therapy</option>
            </select>
            <input
              type="text"
              placeholder="Therapy description"
              value={newTherapy.description}
              onChange={(e) => setNewTherapy(prev => ({ ...prev, description: e.target.value }))}
              className="px-2 py-1 border rounded text-sm"
            />
            <input
              type="text"
              placeholder="Frequency (e.g., 3x per week)"
              value={newTherapy.frequency}
              onChange={(e) => setNewTherapy(prev => ({ ...prev, frequency: e.target.value }))}
              className="px-2 py-1 border rounded text-sm"
            />
            <input
              type="text"
              placeholder="Duration (e.g., 4 weeks)"
              value={newTherapy.duration}
              onChange={(e) => setNewTherapy(prev => ({ ...prev, duration: e.target.value }))}
              className="px-2 py-1 border rounded text-sm"
            />
          </div>
          <div className="flex space-x-2 mt-2">
            <button
              onClick={handleAddTherapy}
              disabled={addingTherapy || !newTherapy.description}
              className="flex items-center space-x-1 px-3 py-1 bg-purple-600 text-white rounded text-sm hover:bg-purple-700 disabled:bg-gray-400"
            >
              {addingTherapy ? (
                <>
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Adding...</span>
                </>
              ) : (
                <>
                  <Save className="w-3 h-3" />
                  <span>Prescribe</span>
                </>
              )}
            </button>
            <button
              onClick={handleCancelAddTherapy}
              className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
            >
              <X className="w-3 h-3" />
              <span>Cancel</span>
            </button>
          </div>
        </div>
      )}

      {/* Therapies List */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {therapies.map((therapy) => (
          <div key={therapy.id} className="bg-white border rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-1">
                  <h4 className="font-medium text-md">{therapy.description}</h4>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                    therapy.status === 'active' ? 'bg-green-100 text-green-800' :
                    therapy.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {therapy.status.toUpperCase()}
                  </div>
                </div>
                <div className="text-sm text-gray-600 mb-2">
                  <p><span className="font-medium">Type:</span> {therapy.type} • <span className="font-medium">Frequency:</span> {therapy.frequency}</p>
                  <p><span className="font-medium">Duration:</span> {therapy.duration} • <span className="font-medium">Prescribed by:</span> {therapy.prescribedByName || therapy.prescribedBy || 'Unknown'}</p>
                  {therapy.therapist && <p><span className="font-medium">Therapist:</span> {therapy.therapist}</p>}
                  {therapy.sessions && therapy.sessions.length > 0 && (
                    <p><span className="font-medium">Sessions:</span> {therapy.sessions.length} completed</p>
                  )}
                </div>
              </div>

              {/* Therapy Actions */}
              {PermissionUtils.canEditMedications(currentUser.role) && therapy.canEdit && (
                <div className="flex items-center space-x-1">
                  {therapy.status === 'active' && (
                    <>
                      <button
                        onClick={() => handleAddTherapySession(therapy)}
                        className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors text-xs"
                        title="Add therapy session"
                      >
                        <Plus className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleCompleteTherapy(therapy)}
                        className="p-1 text-green-600 hover:bg-green-50 rounded transition-colors text-xs"
                        title="Complete therapy"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleCancelTherapy(therapy)}
                        className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors text-xs"
                        title="Cancel therapy"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {therapies.length === 0 && (
          <div className="text-center py-6 text-gray-500">
            <Heart className="w-10 h-10 mx-auto mb-3 opacity-50" />
            <p>No therapy prescribed yet</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PatientTherapies;
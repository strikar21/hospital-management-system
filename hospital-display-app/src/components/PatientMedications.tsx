import React, { useState } from 'react';
import {
  Plus, Save, X, CheckCircle, Pause, Play, StopCircle, Shield
} from 'lucide-react';
import { patient, user, medication, caseSheetEntry } from '../types';
import { getMedicationStatusColor, formatDateTime } from '../utils';
import { PermissionUtils } from '../utils/permissionUtils';
import { PatientService } from '../services';
import { PatientCaseService } from '../services/patient';
import { getApiUrl } from '../config/apiConfig';

interface PatientMedicationsProps {
  patient: patient;
  currentUser: user;
  medications: medication[];
  setMedications: React.Dispatch<React.SetStateAction<medication[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
}

const PatientMedications: React.FC<PatientMedicationsProps> = ({
  patient,
  currentUser,
  medications,
  setMedications,
  addCaseSheetEntry
}) => {
  // Medication form state
  const [showMedicationForm, setShowMedicationForm] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [newMedication, setNewMedication] = useState({
    name: '', dosage: '', frequency: '', route: 'PO', duration: ''
  });

  // Debounce utility
  const debounce = (func: (...args: any[]) => void, wait: number) => {
    let timeout: NodeJS.Timeout;
    return (...args: any[]) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func(...args), wait);
    };
  };

  // Handle medication status changes using atomic operation
  const handleMedicationStatusChange = async (medicationId: string, status: 'active' | 'stopped' | 'held') => {
    try {

      // Use atomic endpoint - updates medication and creates case entry in single transaction
      const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/medications/${medicationId}/status`), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          medication_id: medicationId,
          status: status,
          changed_by: currentUser.staffId
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to change medication status: ${response.statusText}`);
      }

      const result = await response.json();

      if (result.success) {
        // Refetch fresh data from backend (single source of truth)
        try {
          // Note: This should use data refresh hook when available
          const medicationsResponse = await fetch(getApiUrl(`/patients/${patient.id}/medications`));
          if (medicationsResponse.ok) {
            const data = await medicationsResponse.json();
            setMedications(data.medications || data);
          }
        } catch (refreshError) {
          // Failed to refresh medications after status change - handle silently
        }

        // Add case sheet entry from atomic result to frontend state (already created atomically)
        if (result.case_entry) {
          const caseEntry: caseSheetEntry = {
            id: result.case_entry.id,
            timestamp: result.case_entry.timestamp,
            type: 'pharmacistNote',
            description: result.case_entry.description,
            performedBy: currentUser.staffId,
            canEdit: false
          };
          addCaseSheetEntry(caseEntry);
        }
      } else {
        throw new Error('Atomic operation failed');
      }
    } catch (error) {
      // Error changing medication status
      alert(`❌ Failed to change medication status: ${(error as Error).message}`);
    }
  };

  return (
    <div className="p-3 h-full flex flex-col">
      <div className="flex justify-end mb-2">
        {!PermissionUtils.canEditMedications(currentUser.role) && (
          <span className="text-xs bg-yellow-100 text-yellow-600 px-2 py-1 rounded-lg flex items-center space-x-1">
            <Shield className="w-3 h-3" />
            <span>View Only</span>
          </span>
        )}
        {PermissionUtils.canEditMedications(currentUser.role) && (
          <button
            onClick={() => setShowMedicationForm(true)}
            className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Prescribe</span>
          </button>
        )}
      </div>

      {/* Add Medication Form */}
      {showMedicationForm && PermissionUtils.canEditMedications(currentUser.role) && (
        <div className="mb-2 p-2 bg-blue-50 rounded-lg border">
          <h4 className="font-medium mb-2 text-sm">Prescribe New Medication</h4>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              placeholder="Medication name"
              value={newMedication.name}
              onChange={(e) => setNewMedication(prev => ({ ...prev, name: e.target.value }))}
              className="px-2 py-1 border rounded text-sm col-span-2"
            />
            <input
              type="text"
              placeholder="Dosage (e.g., 10mg)"
              value={newMedication.dosage}
              onChange={(e) => setNewMedication(prev => ({ ...prev, dosage: e.target.value }))}
              className="px-2 py-1 border rounded text-sm"
            />
            <input
              type="text"
              placeholder="Frequency (e.g., Twice daily)"
              value={newMedication.frequency}
              onChange={(e) => setNewMedication(prev => ({ ...prev, frequency: e.target.value }))}
              className="px-2 py-1 border rounded text-sm"
            />
            <input
              type="text"
              placeholder="Duration (e.g., 7 days)"
              value={newMedication.duration}
              onChange={(e) => setNewMedication(prev => ({ ...prev, duration: e.target.value }))}
              className="px-2 py-1 border rounded text-sm"
            />
            <select
              value={newMedication.route}
              onChange={(e) => setNewMedication(prev => ({ ...prev, route: e.target.value }))}
              className="px-2 py-1 border rounded text-sm"
            >
              <option value="PO">PO (Oral)</option>
              <option value="IV">IV (Intravenous)</option>
              <option value="IM">IM (Intramuscular)</option>
              <option value="SC">SC (Subcutaneous)</option>
              <option value="Inhaled">Inhaled</option>
              <option value="Topical">Topical</option>
            </select>
          </div>
          <div className="flex space-x-2 mt-2">
            <button
              onClick={async () => {
                if (isSubmitting) return; // Prevent multiple simultaneous calls
                if (!newMedication.name || !newMedication.dosage || !newMedication.frequency || !newMedication.duration) return;
                setIsSubmitting(true);
                try {
                  const medicationData = {
                    ...newMedication,
                    status: 'active' as const,
                    prescribedBy: currentUser.staffId
                    // startDate, createdAt, canEdit: backend will generate
                  };
                  // Use atomic endpoint for adding medication
                  const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/medications`), {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(medicationData)
                  });

                  if (!response.ok) {
                    throw new Error(`Failed to add medication: ${response.statusText}`);
                  }

                  const result = await response.json();
                  if (result.success) {
                    // Refetch fresh data from backend (single source of truth)
                    try {
                      const medicationsResponse = await fetch(getApiUrl(`/patients/${patient.id}/medications`));
                      if (medicationsResponse.ok) {
                        const data = await medicationsResponse.json();
                        setMedications(data.medications || data);
                      }
                    } catch (refreshError) {
                      // Failed to refresh medications after adding - handle silently
                    }
                  } else {
                    // Failed to add medication - no backend response
                    alert('Failed to add medication. Please try again.');
                    setIsSubmitting(false);
                    return;
                  }
                  setNewMedication({ name: '', dosage: '', frequency: '', route: 'PO', duration: '' });
                  setShowMedicationForm(false);

                  // Add case sheet entry from atomic result (already created atomically)
                  if (result.case_entry) {
                    const newCaseEntry: caseSheetEntry = {
                      id: result.case_entry.id,
                      timestamp: result.case_entry.timestamp,
                      type: 'pharmacistNote',
                      description: result.case_entry.description,
                      performedBy: result.case_entry.performedBy,
                      canEdit: true
                    };
                    addCaseSheetEntry(newCaseEntry);
                  }
                } catch (error) {
                  // Failed to add medication
                } finally {
                  setIsSubmitting(false);
                }
              }}
              disabled={isSubmitting || !newMedication.name || !newMedication.dosage || !newMedication.frequency || !newMedication.duration}
              className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-gray-400"
            >
              {isSubmitting ? (
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
              onClick={() => {
                setShowMedicationForm(false);
                setNewMedication({ name: '', dosage: '', frequency: '', route: 'PO', duration: '' });
              }}
              className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
            >
              <X className="w-3 h-3" />
              <span>Cancel</span>
            </button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto space-y-2">
        {medications.map((med) => (
          <div key={med.id} className="bg-white border rounded-lg p-2">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-1">
                  <h4 className="font-medium text-sm">{med.name} {med.dosage}</h4>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium border ${getMedicationStatusColor(med.status)}`}>
                    {med.status.toUpperCase()}
                  </div>
                </div>
                <div className="text-sm text-gray-600">
                  <p><span className="font-medium">Frequency:</span> {med.frequency} • <span className="font-medium">Route:</span> {med.route}</p>
                  <p><span className="font-medium">Prescribed by:</span> {(med as any).prescribedByName || med.prescribedBy} on {formatDateTime(med.createdAt)?.split(',')[0] || 'Unknown date'}</p>

                  {/* Medication Administration Schedule */}
                  {med.status === 'active' && (
                    <div className="mt-2 p-2 bg-green-50 border border-green-200 rounded">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs font-medium text-green-700">💊 Administration Schedule</span>
                        <div className="flex items-center space-x-1">
                          <span className="text-xs text-green-600">
                            Last: {patient.lastMedicationTime ?
                              new Date(patient.lastMedicationTime).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) :
                              'Not recorded'
                            }
                          </span>
                        </div>
                      </div>
                      <div className="text-xs text-green-600">
                        {/* Generate administration times based on frequency */}
                        {(() => {
                          // Default schedule based on frequency
                          const freq = med.frequency.toLowerCase();
                          let nextTimes: string[] = [];
                          if (freq.includes('once daily')) nextTimes = ['08:00'];
                          else if (freq.includes('twice daily')) nextTimes = ['08:00', '20:00'];
                          else if (freq.includes('three times')) nextTimes = ['08:00', '14:00', '20:00'];
                          else if (freq.includes('four times')) nextTimes = ['06:00', '12:00', '18:00', '22:00'];
                          else if (freq.includes('every 8 hours')) nextTimes = ['06:00', '14:00', '22:00'];
                          else if (freq.includes('every 6 hours')) nextTimes = ['06:00', '12:00', '18:00', '00:00'];

                          const now = new Date();
                          const currentTime = now.getHours() * 60 + now.getMinutes();
                          const nextTime = nextTimes.find(time => {
                            const [hours, minutes] = time.split(':').map(Number);
                            return (hours * 60 + minutes) > currentTime;
                          }) || nextTimes[0];

                          return (
                            <div className="flex items-center space-x-1">
                              <span className="font-medium">Next due:</span>
                              <span className="bg-green-100 px-2 py-0.5 rounded text-green-800">{nextTime}</span>
                              <span className="text-green-600">({med.frequency})</span>
                            </div>
                          );
                        })()}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {PermissionUtils.canEditMedications(currentUser.role) && med.canEdit && (
                <div className="flex items-center space-x-1">
                  {med.status === 'active' && (
                    <>
                      <button
                        onClick={async () => {
                          try {
                            // Use atomic endpoint for medication administration
                            const response = await fetch(getApiUrl(`/atomic/patients/${patient.id}/medications/${med.id}/administer`), {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json'
                              },
                              body: JSON.stringify({
                                administered_by: currentUser.staffId,
                                notes: `Administered ${med.name} ${med.dosage} via ${med.route} route`
                              })
                            });

                            if (!response.ok) {
                              throw new Error(`Failed to administer medication: ${response.statusText}`);
                            }

                            const result = await response.json();

                            if (result.success && result.case_entry) {
                              // Case entry already created atomically by backend with proper timestamp
                              const adminEntry: caseSheetEntry = {
                                id: result.case_entry.id,
                                timestamp: result.case_entry.timestamp,
                                type: 'medicationAdministration',
                                description: result.case_entry.description,
                                performedBy: result.case_entry.performedBy,
                                canEdit: result.case_entry.canEdit,
                                details: result.case_entry.details
                              };
                              addCaseSheetEntry(adminEntry);

                              alert(`✅ ${med.name} ${med.dosage} administered successfully!\n\nTime: ${new Date(result.case_entry.timestamp).toLocaleTimeString()}\nAdministered by: ${currentUser.name}\n\nAdministration recorded in database and case sheet.`);
                            } else {
                              throw new Error('Administration failed');
                            }
                          } catch (error) {
                            // Failed to administer medication
                            alert(`Failed to administer medication: ${(error as Error).message}`);
                          }
                        }}
                        className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                        title="Administer medication"
                      >
                        <CheckCircle className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => debounce(() => handleMedicationStatusChange(med.id, 'held'), 300)()}
                        className="p-1 text-yellow-600 hover:bg-yellow-50 rounded transition-colors"
                        title="Hold medication"
                      >
                        <Pause className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => debounce(() => handleMedicationStatusChange(med.id, 'stopped'), 300)()}
                        className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors"
                        title="Stop medication"
                      >
                        <StopCircle className="w-4 h-4" />
                      </button>
                    </>
                  )}
                  {med.status === 'held' && (
                    <button
                      onClick={() => debounce(() => handleMedicationStatusChange(med.id, 'active'), 300)()}
                      className="p-1 text-green-600 hover:bg-green-50 rounded transition-colors"
                      title="Resume medication"
                    >
                      <Play className="w-4 h-4" />
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {medications.length === 0 && (
          <div className="text-center py-6 text-gray-500">
            <Plus className="w-10 h-10 mx-auto mb-3 opacity-50" />
            <p>No medications prescribed yet</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default PatientMedications;
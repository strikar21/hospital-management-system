import React, { useState } from 'react';
import {
  Plus, Save, X, CheckCircle, Pause, Play, StopCircle, Shield
} from 'lucide-react';
import { patient, user, medication, caseSheetEntry } from '../types';
import { getMedicationStatusColor, formatDateTime } from '../utils';
import { PermissionUtils } from '../utils/permissionUtils';
import { PatientService, MedicationService } from '../services';

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
  const [isAddingMedication, setIsAddingMedication] = useState(false);
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

  // Handle medication status changes
  const handleMedicationStatusChange = async (medicationId: string, status: 'active' | 'stopped' | 'held') => {
    try {
      await MedicationService.updateMedication(patient.id, medicationId, status, currentUser.id);

      setMedications(prev => prev.map(med =>
        med.id === medicationId ? {
          ...med,
          status,
          modifiedBy: currentUser.name,
          updatedat: new Date().toISOString(),
          canEdit: PatientService.canEditItem(new Date().toISOString()),
          history: [...(med.history || []), {
            id: 'hist_' + Date.now(),
            action: status === 'active' ? 'resumed' : status,
            timestamp: new Date().toISOString(),
            performedBy: currentUser.name
          }]
        } : med
      ));

      const medication = medications.find(m => m.id === medicationId);
      if (medication) {
        const newCaseEntry: caseSheetEntry = {
          id: 'cs_' + Date.now(),
          timestamp: new Date().toISOString(),
          type: 'pharmacyNotes',
          description: `${medication.name} ${status} by ${currentUser.name}`,
          performedBy: currentUser.name,
          canEdit: PatientService.canEditItem(new Date().toISOString())
        };
        addCaseSheetEntry(newCaseEntry);
      }
    } catch (error) {
      console.error('Failed to update medication:', error);
      alert('Failed to update medication. Please try again.');
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
            onClick={() => setIsAddingMedication(true)}
            className="flex items-center space-x-2 px-3 py-1 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
          >
            <Plus className="w-4 h-4" />
            <span>Prescribe</span>
          </button>
        )}
      </div>

      {/* Add Medication Form */}
      {isAddingMedication && PermissionUtils.canEditMedications(currentUser.role) && (
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
                if (isAddingMedication) return; // Prevent multiple simultaneous calls
                if (!newMedication.name || !newMedication.dosage || !newMedication.frequency || !newMedication.duration) return;
                setIsAddingMedication(true);
                try {
                  const timestamp = new Date().toISOString();
                  const medicationData = {
                    ...newMedication,
                    status: 'active' as const,
                    startDate: timestamp.split('T')[0],
                    prescribedBy: currentUser.name,
                    createdAt: timestamp,
                    canEdit: true
                  };
                  const newMed = await MedicationService.addMedication(patient.id, medicationData, currentUser.id);
                  if (newMed) {
                    // Add history if not present from backend
                    const medicationWithHistory: medication = {
                      ...newMed,
                      history: newMed.history || [{
                        id: 'hist_' + Date.now(),
                        action: 'prescribed' as const,
                        timestamp,
                        performedBy: currentUser.name
                      }]
                    };
                    setMedications(prev => [...prev, medicationWithHistory]);
                  } else {
                    console.error('Failed to add medication - no response from backend');
                    alert('Failed to add medication. Please try again.');
                    setIsAddingMedication(false);
                    return;
                  }
                  setNewMedication({ name: '', dosage: '', frequency: '', route: 'PO', duration: '' });
                  setIsAddingMedication(false);

                  // Add case sheet entry to backend
                  try {
                    const caseResponse = await fetch(`http://localhost:8001/api/v2/patients/${patient.id}/case-entries`, {
                      method: 'POST',
                      headers: {
                        'Content-Type': 'application/json'
                      },
                      body: JSON.stringify({
                        entrytype: 'medication',
                        description: `${newMedication.name} (${newMedication.dosage}, ${newMedication.frequency}, ${newMedication.duration}) prescribed by ${currentUser.name}`,
                        performedBy: currentUser.name
                      })
                    });

                    if (caseResponse.ok) {
                      const caseResult = await caseResponse.json();
                      const newCaseEntry: caseSheetEntry = {
                        id: caseResult.id || 'cs_' + Date.now(),
                        timestamp,
                        type: 'pharmacyNotes',
                        description: `${newMedication.name} (${newMedication.dosage}, ${newMedication.frequency}, ${newMedication.duration}) prescribed by ${currentUser.name}`,
                        performedBy: currentUser.name,
                        canEdit: true
                      };
                      addCaseSheetEntry(newCaseEntry);
                    }
                  } catch (caseError) {
                    console.warn('Failed to add medication case sheet entry:', caseError);
                  }
                } catch (error) {
                  console.error('Failed to add medication:', error);
                } finally {
                  setIsAddingMedication(false);
                }
              }}
              disabled={isAddingMedication || !newMedication.name || !newMedication.dosage || !newMedication.frequency || !newMedication.duration}
              className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-gray-400"
            >
              {isAddingMedication ? (
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
                setIsAddingMedication(false);
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
                  <p><span className="font-medium">Prescribed by:</span> {med.prescribedBy} on {formatDateTime(med.createdAt)?.split(',')[0] || 'Unknown date'}</p>

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
                        onClick={() => {
                          const now = new Date().toISOString();
                          // Add administration record to case sheet
                          const adminEntry: caseSheetEntry = {
                            id: 'admin_' + Date.now(),
                            timestamp: now,
                            type: 'medicationAdministration',
                            description: `Administered ${med.name} ${med.dosage} via ${med.route} route`,
                            performedBy: currentUser.name,
                            canEdit: PatientService.canEditItem(now),
                            details: {
                              medicationId: med.id,
                              medicationName: med.name,
                              dosage: med.dosage,
                              route: med.route,
                              administeredby: currentUser.name,
                              administeredat: now
                            }
                          };
                          addCaseSheetEntry(adminEntry);

                          // Update patient's last medication time
                          alert(`✅ ${med.name} ${med.dosage} administered successfully!\n\nTime: ${new Date().toLocaleTimeString()}\nAdministered by: ${currentUser.name}\n\nAdministration logged in case sheet.`);
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
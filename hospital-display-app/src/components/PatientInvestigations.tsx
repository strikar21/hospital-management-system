import React, { useState } from 'react';
import {
  TestTube, XCircle, Play, Save, X
} from 'lucide-react';
import { patient, user, investigation, caseSheetEntry } from '../types';
import { formatTimeOnly } from '../utils';
import { PermissionUtils } from '../utils/permissionUtils';
import { usePatientInvestigations } from '../hooks/usePatientInvestigations';
import { InvestigationDetailModal } from './modals/InvestigationDetailModal';

interface PatientInvestigationsProps {
  patient: patient;
  currentUser: user;
  investigations: investigation[];
  setInvestigations: React.Dispatch<React.SetStateAction<investigation[]>>;
  addCaseSheetEntry: (entry: caseSheetEntry) => void;
  setCaseEntries: React.Dispatch<React.SetStateAction<caseSheetEntry[]>>;
}

const PatientInvestigations: React.FC<PatientInvestigationsProps> = ({
  patient,
  currentUser,
  investigations,
  setInvestigations,
  addCaseSheetEntry,
  setCaseEntries
}) => {
  const {
    isAddingInvestigation,
    setIsAddingInvestigation,
    newInvestigation,
    setNewInvestigation,
    addingInvestigation,
    loadingLabResults,
    handleAddInvestigation,
    handleStartInvestigation,
    handleCompleteInvestigation,
    handleCancelInvestigation,
    handleCancelAddInvestigation
  } = usePatientInvestigations({
    patient,
    currentUser,
    investigations,
    setInvestigations,
    addCaseSheetEntry,
    setCaseEntries
  });

  const [selectedInvestigation, setSelectedInvestigation] = useState<investigation | null>(null);

  return (
    <div className="p-4 h-full flex flex-col">
      {PermissionUtils.canEditMedications(currentUser.role) && (
        <div className="flex justify-end mb-3">
          <button
            onClick={() => setIsAddingInvestigation(true)}
            className="flex items-center space-x-2 px-3 py-1 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm"
          >
            <TestTube className="w-4 h-4" />
            <span>Order Test</span>
          </button>
        </div>
      )}

      {/* Add Investigation Form */}
      {isAddingInvestigation && PermissionUtils.canEditMedications(currentUser.role) && (
        <div className="mb-3 p-3 bg-green-50 rounded-lg border">
          <h4 className="font-medium mb-2 text-sm">Order New Investigation</h4>
          <div className="grid grid-cols-2 gap-2">
            <select
              value={newInvestigation.type}
              onChange={(e) => setNewInvestigation(prev => ({ ...prev, type: e.target.value as any }))}
              className="px-2 py-1 border rounded text-sm"
            >
              <option value="lab">Laboratory Test</option>
              <option value="imaging">Imaging Study</option>
              <option value="biopsy">Biopsy</option>
              <option value="culture">Culture</option>
            </select>
            <input
              type="text"
              placeholder="Investigation name"
              value={newInvestigation.name}
              onChange={(e) => setNewInvestigation(prev => ({ ...prev, name: e.target.value }))}
              className="px-2 py-1 border rounded text-sm"
            />
            <select
              value={newInvestigation.priority}
              onChange={(e) => setNewInvestigation(prev => ({ ...prev, priority: e.target.value as any }))}
              className="px-2 py-1 border rounded text-sm"
            >
              <option value="routine">Routine</option>
              <option value="urgent">Urgent</option>
              <option value="stat">STAT</option>
            </select>
            <input
              type="text"
              placeholder="Special instructions"
              value={newInvestigation.notes}
              onChange={(e) => setNewInvestigation(prev => ({ ...prev, notes: e.target.value }))}
              className="px-2 py-1 border rounded text-sm"
            />
          </div>
          <div className="flex space-x-2 mt-2">
            <button
              onClick={handleAddInvestigation}
              disabled={addingInvestigation || !newInvestigation.name}
              className="flex items-center space-x-1 px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:bg-gray-400"
            >
              {addingInvestigation ? (
                <>
                  <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  <span>Ordering...</span>
                </>
              ) : (
                <>
                  <Save className="w-3 h-3" />
                  <span>Order</span>
                </>
              )}
            </button>
            <button
              onClick={handleCancelAddInvestigation}
              className="flex items-center space-x-1 px-3 py-1 bg-gray-600 text-white rounded text-sm hover:bg-gray-700"
            >
              <X className="w-3 h-3" />
              <span>Cancel</span>
            </button>
          </div>
        </div>
      )}

      {/* Investigations List */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {investigations.map((inv) => (
          <div
            key={inv.id}
            className="bg-white border rounded-lg p-3 cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => setSelectedInvestigation(inv)}
          >
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <div className="flex items-center space-x-3 mb-1">
                  <h4 className="font-medium text-md">{inv.name}</h4>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                    inv.status === 'ordered' ? 'bg-blue-100 text-blue-800' :
                    inv.status === 'completed' ? 'bg-green-100 text-green-800' :
                    inv.status === 'inProgress' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {inv.status.toUpperCase().replace('_', ' ')}
                  </div>
                  <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                    inv.priority === 'stat' ? 'bg-red-100 text-red-800' :
                    inv.priority === 'urgent' ? 'bg-orange-100 text-orange-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {inv.priority.toUpperCase()}
                  </div>
                </div>
                <div className="text-sm text-gray-600 mb-2">
                  <p><span className="font-medium">Type:</span> {inv.type} • <span className="font-medium">Ordered by:</span> {inv.prescribedByName || inv.prescribedBy || 'Unknown'}</p>
                  {inv.notes && <p><span className="font-medium">Notes:</span> {inv.notes}</p>}
                  {inv.results && <p><span className="font-medium">Results:</span> {inv.results}</p>}

                  {/* Detailed Lab Results */}
                  {inv.type === 'lab' && inv.labResults && inv.labResults.length > 0 && (
                    <div className="mt-2">
                      <p className="font-medium text-sm mb-2">📋 Lab Results ({inv.labResults.length} tests):</p>
                      <div className="space-y-1 max-h-40 overflow-y-auto">
                        {inv.labResults.map((result) => (
                          <div key={result.id} className={`text-xs p-2 rounded border ${"bg-green-50 text-green-700 border-green-200"}`}>
                            <div className="flex justify-between items-center">
                              <span className="font-medium">{result.testName}</span>
                              <span className={`px-1 py-0.5 rounded text-xs ${
                                result.abnormalFlag === 'criticalHigh' || result.abnormalFlag === 'criticalLow' ? 'bg-red-600 text-white animate-pulse' :
                                result.abnormalFlag === 'high' || result.abnormalFlag === 'low' ? 'bg-orange-600 text-white' :
                                'bg-green-600 text-white'
                              }`}>
                                {result.abnormalFlag.toUpperCase().replace('_', ' ')}
                              </span>
                            </div>
                            <div className="flex justify-between text-gray-700 mt-1">
                              <span><strong>{result.result} {result.units}</strong></span>
                              <span>Normal: {result.normalRange}</span>
                            </div>
                            {result.performedBy && (
                              <div className="text-gray-500 text-xs mt-1">
                                ✓ Verified by {result.performedBy} • {formatTimeOnly(result.completedat)}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Lab Results Summary */}
                      {false && (
                        <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded">
                          <p className="text-red-700 text-xs font-medium">
                            ⚠️ CRITICAL VALUES DETECTED - Requires immediate physician review
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Loading Lab Results */}
                  {inv.type === 'lab' && inv.status === 'inProgress' && loadingLabResults && (
                    <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded">
                      <div className="flex items-center space-x-2">
                        <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                        <span className="text-blue-700 text-xs">Fetching lab results from laboratory system...</span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Investigation Actions */}
              {PermissionUtils.canEditMedications(currentUser.role) && inv.canEdit && (
                <div className="flex items-center space-x-1">
                  {inv.status === 'ordered' && (
                    <button
                      onClick={() => handleStartInvestigation(inv)}
                      className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors text-xs"
                      title="Start investigation"
                    >
                      <Play className="w-4 h-4" />
                    </button>
                  )}
                  {(inv.status === 'inProgress' || inv.status === 'ordered') && (
                    <button
                      onClick={() => handleCompleteInvestigation(inv)}
                      className="p-1 text-green-600 hover:bg-green-50 rounded transition-colors text-xs"
                      title="Complete investigation"
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                  )}
                  {inv.status !== 'completed' && inv.status !== 'cancelled' && (
                    <button
                      onClick={() => handleCancelInvestigation(inv)}
                      className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors text-xs"
                      title="Cancel investigation"
                    >
                      <XCircle className="w-4 h-4" />
                    </button>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {investigations.length === 0 && (
          <div className="text-center py-6 text-gray-500">
            <TestTube className="w-10 h-10 mx-auto mb-3 opacity-50" />
            <p>No investigations ordered yet</p>
          </div>
        )}
      </div>

      {/* Investigation Detail Modal */}
      {selectedInvestigation && (
        <InvestigationDetailModal
          isOpen={selectedInvestigation !== null}
          onClose={() => setSelectedInvestigation(null)}
          investigation={selectedInvestigation}
        />
      )}
    </div>
  );
};

export default PatientInvestigations;
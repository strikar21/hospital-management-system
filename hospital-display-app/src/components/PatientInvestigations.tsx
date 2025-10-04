import React from 'react';
import {
  TestTube, XCircle, Play, Save, X
} from 'lucide-react';
import { patient, user, investigation, caseSheetEntry } from '../types';
import { formatTimeOnly } from '../utils';
import { PermissionUtils } from '../utils/permissionUtils';
import { usePatientInvestigations } from '../hooks/usePatientInvestigations';

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
    imagingStudies,
    loadingImaging,
    selectedImage,
    setSelectedImage,
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
          <div key={inv.id} className="bg-white border rounded-lg p-3">
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

      {/* Imaging Studies Section */}
      <div className="mt-6 border-t pt-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-lg font-bold flex items-center space-x-2">
            <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
              📸
            </div>
            <span>Imaging Studies ({imagingStudies.length})</span>
            {loadingImaging && (
              <div className="w-4 h-4 border-2 border-purple-600 border-t-transparent rounded-full animate-spin ml-2"></div>
            )}
          </h3>
        </div>

        {/* Imaging Studies List */}
        <div className="space-y-3 max-h-80 overflow-y-auto">
          {imagingStudies.map((study) => (
            <div key={study.id} className="bg-white border rounded-lg p-4 shadow-sm">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-2">
                    <h4 className="font-medium text-md">{study.studyType}</h4>
                    <div className={`px-2 py-1 rounded-full text-xs font-medium border ${"bg-blue-50 text-blue-700 border-blue-200"}`}>
                      {study.studyType.toUpperCase()}
                    </div>
                    <div className={`px-2 py-1 rounded-full text-xs font-medium ${"bg-yellow-50 text-yellow-700"}`}>
                      {study.urgency.toUpperCase()}
                    </div>
                    <div className={`px-2 py-1 rounded-full text-xs font-medium ${
                      study.status === 'completed' ? 'bg-green-100 text-green-800' :
                      study.status === 'inProgress' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-blue-100 text-blue-800'
                    }`}>
                      {study.status.toUpperCase().replace('_', ' ')}
                    </div>
                  </div>

                  <div className="text-sm text-gray-600 mb-3">
                    <p><span className="font-medium">Study Date:</span> {new Date(study.createdAt).toLocaleString()}</p>
                    <p><span className="font-medium">Ordered by:</span> {study.performedBy}</p>
                    {study.technologist && <p><span className="font-medium">Technologist:</span> {study.technologist}</p>}
                    {study.radiologist && <p><span className="font-medium">Radiologist:</span> {study.radiologist}</p>}
                  </div>

                  {/* Image Thumbnails */}
                  {study.images && study.images.length > 0 && (
                    <div className="mb-3">
                      <p className="font-medium text-sm mb-2">📷 Images ({study.images.length}):</p>
                      <div className="flex space-x-2 overflow-x-auto">
                        {study.images.map((image) => (
                          <div key={image.id} className="flex-shrink-0">
                            <img
                              src={image.thumbnail}
                              alt={`${study.studyType} - ${image.viewPosition || `Instance ${image.instanceNumber}`}`}
                              className="w-20 h-20 object-cover rounded border cursor-pointer hover:opacity-80 transition-opacity"
                              onClick={() => setSelectedImage(image.url)}
                              title={`Click to view full image - ${image.viewPosition || `Instance ${image.instanceNumber}`}`}
                            />
                            <p className="text-xs text-gray-500 text-center mt-1 truncate w-20">
                              {image.viewPosition || `#${image.instanceNumber}`}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Imaging Report */}
                  {study.report && (
                    <div className="bg-gray-50 rounded p-3 text-sm">
                      <div className="flex items-center justify-between mb-2">
                        <h5 className="font-medium text-gray-900">📋 Radiology Report</h5>
                        <div className={`px-2 py-1 rounded text-xs font-medium ${
                          study.report.status === 'final' ? 'bg-green-100 text-green-800' :
                          study.report.status === 'preliminary' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-blue-100 text-blue-800'
                        }`}>
                          {study.report.status.toUpperCase()}
                        </div>
                      </div>

                      <div className="space-y-2">
                        <div>
                          <span className="font-medium text-gray-700">Findings:</span>
                          <p className="text-gray-600 mt-1">{study.report.findings}</p>
                        </div>
                        <div>
                          <span className="font-medium text-gray-700">Impression:</span>
                          <p className="text-gray-600 mt-1">{study.report.impression}</p>
                        </div>
                        {study.report.recommendations && (
                          <div>
                            <span className="font-medium text-gray-700">Recommendations:</span>
                            <p className="text-gray-600 mt-1">{study.report.recommendations}</p>
                          </div>
                        )}
                        <div className="text-xs text-gray-500 pt-2 border-t">
                          Reported by {study.report.performedBy} • {new Date(study.report.createdAt).toLocaleString()}
                        </div>
                      </div>

                      {/* Abnormal findings alert */}
                      {false && (
                        <div className="mt-3 p-2 bg-orange-50 border border-orange-200 rounded">
                          <p className="text-orange-700 text-xs font-medium">
                            ⚠️ ABNORMAL FINDINGS - Requires physician review
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* No report available */}
                  {!study.report && study.status === 'completed' && (
                    <div className="bg-yellow-50 border border-yellow-200 rounded p-2">
                      <p className="text-yellow-700 text-sm">📝 Report pending - Awaiting radiologist interpretation</p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}

          {/* No imaging studies */}
          {imagingStudies.length === 0 && !loadingImaging && (
            <div className="text-center py-8 text-gray-500">
              <div className="w-16 h-16 mx-auto mb-4 opacity-50">📸</div>
              <p>No imaging studies available</p>
            </div>
          )}

          {/* Loading imaging */}
          {loadingImaging && (
            <div className="text-center py-8 text-gray-500">
              <div className="w-8 h-8 border-2 border-purple-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
              <p>Loading imaging studies from PACS...</p>
            </div>
          )}
        </div>
      </div>

      {/* Image Viewer Modal */}
      {selectedImage && (
        <div
          className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50"
          onClick={() => setSelectedImage(null)}
        >
          <div className="max-w-4xl max-h-4xl p-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-white text-lg font-medium">Medical Image Viewer</h3>
              <button
                onClick={() => setSelectedImage(null)}
                className="text-white hover:text-gray-300 text-2xl font-bold"
              >
                ×
              </button>
            </div>
            <img
              src={selectedImage}
              alt="Medical imaging study"
              className="max-w-full max-h-full object-contain rounded"
            />
            <div className="mt-4 text-center">
              <button
                onClick={() => {/* DICOM viewer feature disabled */}}
                className="px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 mr-2"
              >
                Open in DICOM Viewer
              </button>
              <button
                onClick={() => setSelectedImage(null)}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PatientInvestigations;
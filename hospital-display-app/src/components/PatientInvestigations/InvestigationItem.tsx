/**
 * InvestigationItem - Individual investigation display card
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React from 'react';
import { XCircle, Play } from 'lucide-react';
import { investigation, user } from '../../types';
import { formatTimeOnly } from '../../utils';
import { PermissionUtils } from '../../utils/permissionUtils';

interface InvestigationItemProps {
  investigation: investigation;
  currentUser: user;
  loadingLabResults: boolean;
  onStart: (investigation: investigation) => void;
  onComplete: (investigation: investigation) => void;
  onCancel: (investigation: investigation) => void;
  onClick: (investigation: investigation) => void;
}

export const InvestigationItem: React.FC<InvestigationItemProps> = ({
  investigation: inv,
  currentUser,
  loadingLabResults,
  onStart,
  onComplete,
  onCancel,
  onClick
}) => {
  return (
    <div
      className="bg-white border rounded-lg p-3 cursor-pointer hover:bg-gray-50 transition-colors"
      onClick={() => onClick(inv)}
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
                onClick={(e) => {
                  e.stopPropagation();
                  onStart(inv);
                }}
                className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors text-xs"
                title="Start investigation"
              >
                <Play className="w-4 h-4" />
              </button>
            )}
            {(inv.status === 'inProgress' || inv.status === 'ordered') && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onComplete(inv);
                }}
                className="p-1 text-green-600 hover:bg-green-50 rounded transition-colors text-xs"
                title="Complete investigation"
              >
                <XCircle className="w-4 h-4" />
              </button>
            )}
            {inv.status !== 'completed' && inv.status !== 'cancelled' && (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onCancel(inv);
                }}
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
  );
};

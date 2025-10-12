/**
 * MedicationItem - Individual medication display card
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React from 'react';
import { CheckCircle, Pause, Play, StopCircle } from 'lucide-react';
import { medication, user, patient } from '../../types';
import { getMedicationStatusColor, formatDateTime } from '../../utils';
import { PermissionUtils } from '../../utils/permissionUtils';

interface MedicationItemProps {
  medication: medication;
  patient: patient;
  currentUser: user;
  onAdminister: (medication: medication) => void;
  onStatusChange: (medicationId: string, status: 'active' | 'discontinued' | 'held') => void;
  debounce: (func: (...args: any[]) => void, wait: number) => (...args: any[]) => void;
}

export const MedicationItem: React.FC<MedicationItemProps> = ({
  medication: med,
  patient,
  currentUser,
  onAdminister,
  onStatusChange,
  debounce
}) => {
  return (
    <div className="bg-white border rounded-lg p-2">
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

            {/* Show who modified status for held/discontinued medications */}
            {(med.status === 'held' || med.status === 'discontinued') && (med as any).modifiedBy && (
              <p className="text-xs text-orange-600 font-medium mt-1">
                Status changed to {med.status.toUpperCase()} by {(med as any).modifiedByName || (med as any).modifiedBy}
                {med.updatedAt && ` on ${formatDateTime(med.updatedAt)?.split(',')[0]}`}
              </p>
            )}

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
                  onClick={() => onAdminister(med)}
                  className="p-1 text-blue-600 hover:bg-blue-50 rounded transition-colors"
                  title="Administer medication"
                >
                  <CheckCircle className="w-4 h-4" />
                </button>
                <button
                  onClick={() => debounce(() => onStatusChange(med.id, 'held'), 300)()}
                  className="p-1 text-yellow-600 hover:bg-yellow-50 rounded transition-colors"
                  title="Hold medication"
                >
                  <Pause className="w-4 h-4" />
                </button>
                <button
                  onClick={() => debounce(() => onStatusChange(med.id, 'discontinued'), 300)()}
                  className="p-1 text-red-600 hover:bg-red-50 rounded transition-colors"
                  title="Stop medication"
                >
                  <StopCircle className="w-4 h-4" />
                </button>
              </>
            )}
            {med.status === 'held' && (
              <button
                onClick={() => debounce(() => onStatusChange(med.id, 'active'), 300)()}
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
  );
};

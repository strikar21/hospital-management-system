/**
 * InvestigationDetailModal - Shows full investigation details
 * - Lab results with detailed values
 * - Imaging studies with DICOM viewer
 * - Biopsy results
 * - Culture results
 */

import React from 'react';
import { MedicalModal } from './MedicalModal';
import { investigation } from '../../types';
import { formatTimeOnly } from '../../utils';

interface InvestigationDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  investigation: investigation | null;
  imagingStudy?: any; // Imaging study data if available
}

export const InvestigationDetailModal: React.FC<InvestigationDetailModalProps> = ({
  isOpen,
  onClose,
  investigation,
  imagingStudy
}) => {
  if (!investigation) return null;

  const renderLabResults = () => {
    if (!investigation.labResults || investigation.labResults.length === 0) {
      return (
        <div className="text-center py-6 text-gray-500">
          <p>No lab results available yet</p>
        </div>
      );
    }

    return (
      <div className="space-y-3">
        <h3 className="font-semibold text-lg mb-3">Laboratory Results</h3>
        {investigation.labResults.map((result) => (
          <div key={result.id} className={`p-4 rounded-lg border ${
            result.abnormalFlag === 'criticalHigh' || result.abnormalFlag === 'criticalLow'
              ? 'bg-red-50 border-red-300'
              : result.abnormalFlag === 'high' || result.abnormalFlag === 'low'
              ? 'bg-orange-50 border-orange-300'
              : 'bg-green-50 border-green-300'
          }`}>
            <div className="flex justify-between items-start mb-2">
              <div>
                <h4 className="font-medium text-lg">{result.testName}</h4>
                <p className="text-sm text-gray-600">{result.testCode}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                result.abnormalFlag === 'criticalHigh' || result.abnormalFlag === 'criticalLow'
                  ? 'bg-red-600 text-white animate-pulse'
                  : result.abnormalFlag === 'high' || result.abnormalFlag === 'low'
                  ? 'bg-orange-600 text-white'
                  : 'bg-green-600 text-white'
              }`}>
                {result.abnormalFlag.toUpperCase().replace(/([A-Z])/g, ' $1').trim()}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-3">
              <div>
                <p className="text-sm text-gray-600">Result</p>
                <p className="text-xl font-bold">{result.result} {result.units}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Normal Range</p>
                <p className="font-medium">{result.normalRange}</p>
              </div>
            </div>

            {result.performedBy && (
              <div className="text-sm text-gray-600 pt-3 border-t">
                Verified by {result.performedBy} • {formatTimeOnly(result.completedat)}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderImagingStudy = () => {
    if (!imagingStudy) {
      return (
        <div className="text-center py-6 text-gray-500">
          <p>No imaging data available</p>
        </div>
      );
    }

    return (
      <div className="space-y-4">
        <div>
          <h3 className="font-semibold text-lg mb-3">Imaging Study Details</h3>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <p className="text-sm text-gray-600">Study Type</p>
              <p className="font-medium">{imagingStudy.studyType}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Status</p>
              <p className={`font-medium ${
                imagingStudy.status === 'completed' ? 'text-green-600' : 'text-yellow-600'
              }`}>
                {imagingStudy.status.toUpperCase()}
              </p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Urgency</p>
              <p className="font-medium">{imagingStudy.urgency.toUpperCase()}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600">Study Date</p>
              <p className="font-medium">{new Date(imagingStudy.createdAt).toLocaleString()}</p>
            </div>
            {imagingStudy.technologist && (
              <div>
                <p className="text-sm text-gray-600">Technologist</p>
                <p className="font-medium">{imagingStudy.technologist}</p>
              </div>
            )}
            {imagingStudy.radiologist && (
              <div>
                <p className="text-sm text-gray-600">Radiologist</p>
                <p className="font-medium">{imagingStudy.radiologist}</p>
              </div>
            )}
          </div>
        </div>

        {/* Images */}
        {imagingStudy.images && imagingStudy.images.length > 0 && (
          <div>
            <h4 className="font-semibold mb-3">Images ({imagingStudy.images.length})</h4>
            <div className="grid grid-cols-3 gap-3">
              {imagingStudy.images.map((image: any) => (
                <div key={image.id} className="border rounded-lg overflow-hidden">
                  <img
                    src={image.thumbnail}
                    alt={`${imagingStudy.studyType} - ${image.viewPosition || `Instance ${image.instanceNumber}`}`}
                    className="w-full h-40 object-cover cursor-pointer hover:opacity-80 transition-opacity"
                  />
                  <p className="text-xs text-gray-600 p-2 text-center">
                    {image.viewPosition || `Instance ${image.instanceNumber}`}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Radiology Report */}
        {imagingStudy.report && (
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex justify-between items-center mb-3">
              <h4 className="font-semibold">Radiology Report</h4>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                imagingStudy.report.status === 'final' ? 'bg-green-100 text-green-800' :
                imagingStudy.report.status === 'preliminary' ? 'bg-yellow-100 text-yellow-800' :
                'bg-blue-100 text-blue-800'
              }`}>
                {imagingStudy.report.status.toUpperCase()}
              </span>
            </div>

            <div className="space-y-3">
              <div>
                <p className="font-medium text-gray-700 mb-1">Findings:</p>
                <p className="text-gray-600">{imagingStudy.report.findings}</p>
              </div>
              <div>
                <p className="font-medium text-gray-700 mb-1">Impression:</p>
                <p className="text-gray-600">{imagingStudy.report.impression}</p>
              </div>
              {imagingStudy.report.recommendations && (
                <div>
                  <p className="font-medium text-gray-700 mb-1">Recommendations:</p>
                  <p className="text-gray-600">{imagingStudy.report.recommendations}</p>
                </div>
              )}
              <div className="text-sm text-gray-500 pt-3 border-t">
                Reported by {imagingStudy.report.performedBy} • {new Date(imagingStudy.report.createdAt).toLocaleString()}
              </div>
            </div>
          </div>
        )}

        {!imagingStudy.report && imagingStudy.status === 'completed' && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-3">
            <p className="text-yellow-700">📝 Report pending - Awaiting radiologist interpretation</p>
          </div>
        )}
      </div>
    );
  };

  const renderContent = () => {
    switch (investigation.type) {
      case 'lab':
        return renderLabResults();
      case 'imaging':
        return renderImagingStudy();
      case 'biopsy':
      case 'culture':
        return (
          <div className="space-y-3">
            <h3 className="font-semibold text-lg mb-3">{investigation.type.toUpperCase()} Details</h3>
            {investigation.results && (
              <div className="p-4 bg-gray-50 rounded-lg">
                <p className="font-medium text-gray-700 mb-2">Results:</p>
                <p className="text-gray-600">{investigation.results}</p>
              </div>
            )}
            {!investigation.results && (
              <div className="text-center py-6 text-gray-500">
                <p>Results pending</p>
              </div>
            )}
          </div>
        );
      default:
        return (
          <div className="text-center py-6 text-gray-500">
            <p>Details not available</p>
          </div>
        );
    }
  };

  return (
    <MedicalModal
      isOpen={isOpen}
      onClose={onClose}
      title={investigation.name}
      size="xl"
    >
      <div className="space-y-4">
        {/* Investigation Header Info */}
        <div className="grid grid-cols-3 gap-4 pb-4 border-b">
          <div>
            <p className="text-sm text-gray-600">Type</p>
            <span className={`inline-block mt-1 px-3 py-1 rounded-full text-sm font-medium ${
              investigation.type === 'lab' ? 'bg-blue-100 text-blue-800' :
              investigation.type === 'imaging' ? 'bg-purple-100 text-purple-800' :
              investigation.type === 'biopsy' ? 'bg-pink-100 text-pink-800' :
              'bg-orange-100 text-orange-800'
            }`}>
              {investigation.type.toUpperCase()}
            </span>
          </div>
          <div>
            <p className="text-sm text-gray-600">Status</p>
            <span className={`inline-block mt-1 px-3 py-1 rounded-full text-sm font-medium ${
              investigation.status === 'ordered' ? 'bg-blue-100 text-blue-800' :
              investigation.status === 'completed' ? 'bg-green-100 text-green-800' :
              investigation.status === 'inProgress' ? 'bg-yellow-100 text-yellow-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {investigation.status.toUpperCase().replace('_', ' ')}
            </span>
          </div>
          <div>
            <p className="text-sm text-gray-600">Priority</p>
            <span className={`inline-block mt-1 px-3 py-1 rounded-full text-sm font-medium ${
              investigation.priority === 'stat' ? 'bg-red-100 text-red-800' :
              investigation.priority === 'urgent' ? 'bg-orange-100 text-orange-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {investigation.priority.toUpperCase()}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 pb-4 border-b">
          <div>
            <p className="text-sm text-gray-600">Ordered by</p>
            <p className="font-medium">{investigation.prescribedByName || investigation.prescribedBy || 'Unknown'}</p>
          </div>
          {investigation.notes && (
            <div>
              <p className="text-sm text-gray-600">Special Instructions</p>
              <p className="font-medium">{investigation.notes}</p>
            </div>
          )}
        </div>

        {/* Type-specific content */}
        {renderContent()}
      </div>
    </MedicalModal>
  );
};

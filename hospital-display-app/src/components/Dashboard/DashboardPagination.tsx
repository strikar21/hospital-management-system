/**
 * DashboardPagination - Pagination controls for Dashboard patient list
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade pagination with patient count display and navigation controls
 */

import React from 'react';

interface DashboardPaginationProps {
  currentPage: number;
  totalPages: number;
  totalPatients: number;
  patientsPerPage: number;
  onPageChange: (page: number) => void;
}

export const DashboardPagination: React.FC<DashboardPaginationProps> = ({
  currentPage,
  totalPages,
  totalPatients,
  patientsPerPage,
  onPageChange
}) => {
  if (totalPatients <= patientsPerPage) {
    return null;
  }

  const startPatient = ((currentPage - 1) * patientsPerPage) + 1;
  const endPatient = Math.min(currentPage * patientsPerPage, totalPatients);

  const handlePrevious = () => {
    onPageChange(Math.max(1, currentPage - 1));
  };

  const handleNext = () => {
    onPageChange(Math.min(totalPages, currentPage + 1));
  };

  return (
    <div className="bg-white border-b px-4 py-2">
      <div className="flex items-center justify-between">
        <div className="text-sm text-gray-600">
          Showing {startPatient}-{endPatient} of {totalPatients} patients
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={handlePrevious}
            disabled={currentPage === 1}
            className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-200"
          >
            ← Previous
          </button>
          <span className="text-sm text-gray-600">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={handleNext}
            disabled={currentPage === totalPages}
            className="px-3 py-1 bg-gray-100 text-gray-700 rounded-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-200"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  );
};
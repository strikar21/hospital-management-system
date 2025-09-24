import React, { useState, useRef, useEffect } from 'react';
import {
  ChevronLeft, ChevronRight, CheckCircle, XCircle,
  BookOpen
} from 'lucide-react';
import { caseSheetEntry } from './types';

interface CaseSheetBookProps {
  caseSheet: caseSheetEntry[];
}

const ENTRIES_PER_PAGE = 6; // Number of entries per page (3 rows x 2 columns)

export const CaseSheetBook: React.FC<CaseSheetBookProps> = ({ caseSheet }) => {
  const [currentPage, setCurrentPage] = useState(1);
  
  
  // Swipe handling
  const touchStartX = useRef<number>(0);
  const touchEndX = useRef<number>(0);
  const MIN_SWIPE_DISTANCE = 50;
  
  // Filter out medicationAdministration entries and sort by timestamp (newest first)
  const sortedEntries = [...caseSheet]
    .filter(entry => entry.type !== 'medicationAdministration')
    .sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );

  // Swipe handlers
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.targetTouches[0].clientX;
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    touchEndX.current = e.targetTouches[0].clientX;
  };

  const handleTouchEnd = () => {
    if (!touchStartX.current || !touchEndX.current) return;
    
    const distance = touchStartX.current - touchEndX.current;
    const isLeftSwipe = distance > MIN_SWIPE_DISTANCE;
    const isRightSwipe = distance < -MIN_SWIPE_DISTANCE;

    if (isLeftSwipe && currentPage < totalPages) {
      // Swipe left - next page
      setCurrentPage(currentPage + 1);
    }
    if (isRightSwipe && currentPage > 1) {
      // Swipe right - previous page
      setCurrentPage(currentPage - 1);
    }
    
    // Reset touch positions
    touchStartX.current = 0;
    touchEndX.current = 0;
  };
  
  const totalPages = Math.ceil(sortedEntries.length / ENTRIES_PER_PAGE);
  const currentEntries = sortedEntries.slice(
    (currentPage - 1) * ENTRIES_PER_PAGE,
    currentPage * ENTRIES_PER_PAGE
  );

  // Initialize to last page when caseSheet changes
  useEffect(() => {
    if (totalPages > 0) {
      setCurrentPage(totalPages);
    }
  }, [totalPages]);
  
  const nextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };
  
  const prevPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };
  
  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };
  
  if (sortedEntries.length === 0) {
    return (
      <div className="p-6 h-full flex flex-col items-center justify-center text-gray-500">
        <BookOpen className="w-16 h-16 mb-4 text-gray-300" />
        <h3 className="text-lg font-medium mb-2">Case Sheet is Empty</h3>
        <p className="text-sm text-center">
          Medical activities will appear here as they are performed.
        </p>
      </div>
    );
  }
  
  return (
    <div 
      className="p-1 h-full flex flex-col"
      onTouchStart={handleTouchStart}
      onTouchMove={handleTouchMove}
      onTouchEnd={handleTouchEnd}
    >
      {/* Book Pages */}
      <div className="flex-1 relative bg-white rounded-lg shadow-lg border overflow-hidden">
        {/* Page Content */}
        <div className="h-full p-1 bg-gradient-to-br from-white to-gray-50">
          
          {/* Entries - 2 Column Layout */}
          <div className="h-full overflow-hidden">
            <div className="grid grid-cols-2 grid-rows-3 gap-2 h-full content-start">
              {currentEntries.map((entry, index) => (
                <div 
                  key={entry.id} 
                  className="bg-white/90 border rounded p-2 shadow-sm"
                >
                  <div className="space-y-0.5">
                    {/* Type badge and edit status in one line */}
                    <div className="flex items-center justify-between">
                      <span className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                        entry.type === 'admission' ? 'bg-blue-100 text-blue-800' :
                        entry.type === 'medication' ? 'bg-green-100 text-green-800' :
                        entry.type === 'investigation' ? 'bg-yellow-100 text-yellow-800' :
                        entry.type === 'therapy' ? 'bg-purple-100 text-purple-800' :
                        entry.type === 'vitalAlert' ? 'bg-red-100 text-red-800' :
                        entry.type === 'statusChange' ? 'bg-orange-100 text-orange-800' :
                        entry.type === 'alertAcknowledged' ? 'bg-orange-100 text-orange-800' :
                        entry.type === 'discharge' ? 'bg-slate-100 text-slate-800' :
                        entry.type === 'doctorNotes' ? 'bg-blue-100 text-blue-800' :
                        entry.type === 'nursingNotes' ? 'bg-green-100 text-green-800' :
                        entry.type === 'therapistNotes' ? 'bg-purple-100 text-purple-800' :
                        entry.type === 'technicianNotes' ? 'bg-yellow-100 text-yellow-800' :
                        entry.type === 'pharmacyNotes' ? 'bg-orange-100 text-orange-800' :
                        entry.type === 'otherNotes' ? 'bg-gray-100 text-gray-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {entry.type === 'admission' ? 'ADMISSION' :
                         entry.type === 'medication' ? 'MEDICATION' :
                         entry.type === 'investigation' ? 'INVESTIGATION' :
                         entry.type === 'therapy' ? 'THERAPY' :
                         entry.type === 'vitalAlert' ? 'VITAL ALERT' :
                         entry.type === 'statusChange' ? 'STATUS CHANGE' :
                         entry.type === 'alertAcknowledged' ? 'ALERT ACKNOWLEDGED' :
                         entry.type === 'discharge' ? 'DISCHARGE' :
                         entry.type === 'doctorNotes' ? 'DOCTOR NOTES' :
                         entry.type === 'nursingNotes' ? 'NURSING NOTES' :
                         entry.type === 'therapistNotes' ? 'THERAPIST NOTES' :
                         entry.type === 'technicianNotes' ? 'TECHNICIAN NOTES' :
                         entry.type === 'pharmacyNotes' ? 'PHARMACY NOTES' :
                         entry.type === 'otherNotes' ? 'OTHER NOTES' :
                         'UNKNOWN'}
                      </span>
                      {entry.canEdit ? (
                        <CheckCircle className="w-3 h-3 text-green-600" />
                      ) : (
                        <XCircle className="w-3 h-3 text-gray-400" />
                      )}
                    </div>
                    
                    {/* Time - more compact */}
                    <div className="text-xs text-gray-500">
                      {(() => {
                        const date = new Date(entry.timestamp);
                        if (isNaN(date.getTime())) {
                          return 'Invalid Date';
                        }
                        return date.toLocaleString('en-US', {
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit',
                          timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
                        });
                      })()}
                    </div>
                    
                    {/* Description - compact */}
                    <p className="text-sm text-gray-900 leading-tight line-clamp-3">
                      {(() => {
                        let description = entry.description;
                        // Clean up verbose prefixes
                        description = description.replace(/^Note by [^:]*: /, '');
                        description = description.replace(/^Note edited by [^:]*: /, '');
                        description = description.replace(/^Medication prescribed: /, '');
                        description = description.replace(/^Note: "/, '').replace(/"$/, '');
                        return description;
                      })()}
                    </p>

                    {/* Performer - compact */}
                    <div className="text-xs text-gray-600 truncate">
                      by {entry.performedByName || entry.performedBy || 'Unknown'}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        
      </div>

      {/* Book Navigation */}
      <div className="flex justify-between items-center mt-2 px-1">
        {/* Previous Page */}
        <button
          onClick={prevPage}
          disabled={currentPage === 1}
          className={`flex items-center space-x-1 px-2 py-1 rounded-lg font-medium transition-all ${
            currentPage === 1
              ? 'text-gray-400 cursor-not-allowed bg-gray-100'
              : 'text-blue-600 hover:bg-blue-50 hover:text-blue-700 bg-white shadow-sm'
          }`}
        >
          <ChevronLeft className="w-4 h-4" />
          <span className="hidden sm:inline">Previous</span>
        </button>

        {/* Page Numbers */}
        <div className="flex items-center space-x-1">
          {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
            let pageNum: number;
            if (totalPages <= 5) {
              pageNum = i + 1;
            } else if (currentPage <= 3) {
              pageNum = i + 1;
            } else if (currentPage >= totalPages - 2) {
              pageNum = totalPages - 4 + i;
            } else {
              pageNum = currentPage - 2 + i;
            }
            
            return (
              <button
                key={pageNum}
                onClick={() => goToPage(pageNum)}
                className={`w-8 h-8 rounded-full text-sm font-medium transition-all ${
                  currentPage === pageNum
                    ? 'bg-blue-600 text-white shadow-md'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-800'
                }`}
              >
                {pageNum}
              </button>
            );
          })}
          {totalPages > 5 && currentPage < totalPages - 2 && (
            <>
              <span className="text-gray-400">...</span>
              <button
                onClick={() => goToPage(totalPages)}
                className="w-8 h-8 rounded-full text-sm font-medium text-gray-600 hover:bg-gray-100"
              >
                {totalPages}
              </button>
            </>
          )}
        </div>

        {/* Next Page */}
        <button
          onClick={nextPage}
          disabled={currentPage === totalPages}
          className={`flex items-center space-x-1 px-2 py-1 rounded-lg font-medium transition-all ${
            currentPage === totalPages
              ? 'text-gray-400 cursor-not-allowed bg-gray-100'
              : 'text-blue-600 hover:bg-blue-50 hover:text-blue-700 bg-white shadow-sm'
          }`}
        >
          <span className="hidden sm:inline">Next</span>
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default CaseSheetBook;
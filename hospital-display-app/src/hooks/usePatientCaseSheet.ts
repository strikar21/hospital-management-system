/**
 * usePatientCaseSheet - Patient case sheet management hook
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Handles case sheet pagination, filtering, and navigation with medical compliance
 */

import { useState, useRef, useEffect, useMemo } from 'react';
import { caseSheetEntry } from '../types';

export interface UsePatientCaseSheetOptions {
  entriesPerPage?: number;
  autoGoToLastPage?: boolean;
  excludeTypes?: string[];
  includeOnlyTypes?: string[];
}

export interface UsePatientCaseSheetReturn {
  // Pagination state
  currentPage: number;
  totalPages: number;
  entriesPerPage: number;

  // Filtered and sorted data
  sortedEntries: caseSheetEntry[];
  currentEntries: caseSheetEntry[];

  // Navigation functions
  nextPage: () => void;
  prevPage: () => void;
  goToPage: (page: number) => void;
  goToFirstPage: () => void;
  goToLastPage: () => void;

  // Touch/swipe handling
  touchHandlers: {
    onTouchStart: (e: React.TouchEvent) => void;
    onTouchMove: (e: React.TouchEvent) => void;
    onTouchEnd: () => void;
  };

  // State checks
  canGoNext: boolean;
  canGoPrevious: boolean;
  isEmpty: boolean;

  // Entry utilities
  getEntryTypeLabel: (type: string) => string;
  getEntryTypeStyles: (type: string) => string;
  formatEntryDescription: (description: string) => string;
  formatEntryTimestamp: (timestamp: string) => string;
}

export const usePatientCaseSheet = (
  caseSheet: caseSheetEntry[],
  options: UsePatientCaseSheetOptions = {}
): UsePatientCaseSheetReturn => {
  const {
    entriesPerPage = 6,
    autoGoToLastPage = true,
    excludeTypes = ['medicationAdministration'],
    includeOnlyTypes = []
  } = options;

  // State
  const [currentPage, setCurrentPage] = useState(1);

  // Touch/swipe handling refs
  const touchStartX = useRef<number>(0);
  const touchEndX = useRef<number>(0);
  const MIN_SWIPE_DISTANCE = 50;

  // Memoized filtered and sorted entries
  const sortedEntries = useMemo(() => {
    let filtered = [...caseSheet];

    // Apply include filter if specified
    if (includeOnlyTypes.length > 0) {
      filtered = filtered.filter(entry => includeOnlyTypes.includes(entry.type));
    }

    // Apply exclude filter
    if (excludeTypes.length > 0) {
      filtered = filtered.filter(entry => !excludeTypes.includes(entry.type));
    }

    // Sort by timestamp (newest first)
    return filtered.sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [caseSheet, excludeTypes, includeOnlyTypes]);

  // Calculate pagination
  const totalPages = Math.ceil(sortedEntries.length / entriesPerPage);

  // Get current page entries
  const currentEntries = useMemo(() => {
    const startIndex = (currentPage - 1) * entriesPerPage;
    const endIndex = startIndex + entriesPerPage;
    return sortedEntries.slice(startIndex, endIndex);
  }, [sortedEntries, currentPage, entriesPerPage]);

  // Navigation state
  const canGoNext = currentPage < totalPages;
  const canGoPrevious = currentPage > 1;
  const isEmpty = sortedEntries.length === 0;

  // Navigation functions
  const nextPage = () => {
    if (canGoNext) {
      setCurrentPage(prev => prev + 1);
    }
  };

  const prevPage = () => {
    if (canGoPrevious) {
      setCurrentPage(prev => prev - 1);
    }
  };

  const goToPage = (page: number) => {
    if (page >= 1 && page <= totalPages) {
      setCurrentPage(page);
    }
  };

  const goToFirstPage = () => {
    setCurrentPage(1);
  };

  const goToLastPage = () => {
    if (totalPages > 0) {
      setCurrentPage(totalPages);
    }
  };

  // Touch/swipe handlers
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

    if (isLeftSwipe && canGoNext) {
      nextPage();
    }
    if (isRightSwipe && canGoPrevious) {
      prevPage();
    }

    // Reset touch positions
    touchStartX.current = 0;
    touchEndX.current = 0;
  };

  const touchHandlers = {
    onTouchStart: handleTouchStart,
    onTouchMove: handleTouchMove,
    onTouchEnd: handleTouchEnd
  };

  // Entry utility functions
  const getEntryTypeLabel = (type: string): string => {
    const typeLabels: { [key: string]: string } = {
      'admission': 'ADMISSION',
      'medication': 'MEDICATION',
      'investigation': 'INVESTIGATION',
      'therapy': 'THERAPY',
      'vitalAlert': 'VITAL ALERT',
      'statusChange': 'STATUS CHANGE',
      'alertAcknowledged': 'ALERT ACKNOWLEDGED',
      'discharge': 'DISCHARGE',
      'doctorNote': 'DOCTOR NOTES',
      'nurseNote': 'NURSING NOTES',
      'therapistNote': 'THERAPIST NOTES',
      'technicianNote': 'TECHNICIAN NOTES',
      'pharmacistNote': 'PHARMACY NOTES',
      'clinicalNote': 'OTHER NOTES',
      'handoffNote': 'HANDOFF NOTE',
      'medicationAdministration': 'MEDICATION ADMIN'
    };

    return typeLabels[type] || 'UNKNOWN';
  };

  const getEntryTypeStyles = (type: string): string => {
    const typeStyles: { [key: string]: string } = {
      'admission': 'bg-blue-100 text-blue-800',
      'medication': 'bg-green-100 text-green-800',
      'investigation': 'bg-yellow-100 text-yellow-800',
      'therapy': 'bg-purple-100 text-purple-800',
      'vitalAlert': 'bg-red-100 text-red-800',
      'statusChange': 'bg-orange-100 text-orange-800',
      'alertAcknowledged': 'bg-orange-100 text-orange-800',
      'discharge': 'bg-slate-100 text-slate-800',
      'doctorNote': 'bg-blue-100 text-blue-800',
      'nurseNote': 'bg-green-100 text-green-800',
      'therapistNote': 'bg-purple-100 text-purple-800',
      'technicianNote': 'bg-yellow-100 text-yellow-800',
      'pharmacistNote': 'bg-orange-100 text-orange-800',
      'clinicalNote': 'bg-gray-100 text-gray-800',
      'handoffNote': 'bg-pink-100 text-pink-800',
      'medicationAdministration': 'bg-teal-100 text-teal-800'
    };

    return typeStyles[type] || 'bg-red-100 text-red-800';
  };

  const formatEntryDescription = (description: string): string => {
    let cleaned = description;

    // Clean up verbose prefixes for better readability
    cleaned = cleaned.replace(/^Note by [^:]*: /, '');
    cleaned = cleaned.replace(/^Note edited by [^:]*: /, '');
    cleaned = cleaned.replace(/^Medication prescribed: /, '');
    cleaned = cleaned.replace(/^Note: "/, '').replace(/"$/, '');
    cleaned = cleaned.replace(/^Alert acknowledged: /, '');
    cleaned = cleaned.replace(/^Status changed: /, '');

    return cleaned;
  };

  const formatEntryTimestamp = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
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
    } catch (error) {
      console.error('Error formatting timestamp:', error);
      return 'Invalid Date';
    }
  };

  // Auto-navigate to last page when entries change
  useEffect(() => {
    if (autoGoToLastPage && totalPages > 0) {
      setCurrentPage(totalPages);
    }
  }, [totalPages, autoGoToLastPage]);

  // Reset to first page if current page becomes invalid
  useEffect(() => {
    if (currentPage > totalPages && totalPages > 0) {
      setCurrentPage(1);
    }
  }, [currentPage, totalPages]);

  return {
    // Pagination state
    currentPage,
    totalPages,
    entriesPerPage,

    // Filtered and sorted data
    sortedEntries,
    currentEntries,

    // Navigation functions
    nextPage,
    prevPage,
    goToPage,
    goToFirstPage,
    goToLastPage,

    // Touch/swipe handling
    touchHandlers,

    // State checks
    canGoNext,
    canGoPrevious,
    isEmpty,

    // Entry utilities
    getEntryTypeLabel,
    getEntryTypeStyles,
    formatEntryDescription,
    formatEntryTimestamp
  };
};
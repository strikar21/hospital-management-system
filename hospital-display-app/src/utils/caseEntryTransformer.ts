/**
 * Case Entry Transformation Utilities
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Purpose: Single source of truth for transforming atomic API responses
 * to frontend caseSheetEntry type. Eliminates 108 lines of duplication.
 *
 * @module caseEntryTransformer
 * @since 1.0.0
 */

import { caseSheetEntry } from '../types';

/**
 * Transform atomic case entry response to frontend caseSheetEntry type
 *
 * This function provides a single, consistent transformation for case entries
 * returned from atomic medical record operations. Previously duplicated 9 times
 * across hooks and containers.
 *
 * @param result - Atomic API response containing case entry data
 * @returns Transformed caseSheetEntry or null if no case entry in response
 *
 * @example
 * ```typescript
 * // After medication atomic operation
 * const result = await MedicationService.addMedication(...);
 * const caseEntry = transformAtomicCaseEntry(result);
 * if (caseEntry) {
 *   addCaseSheetEntry(caseEntry);
 * }
 * ```
 */
export function transformAtomicCaseEntry(result: any): caseSheetEntry | null {
  // Guard: No case entry in response
  if (!result?.caseEntry) {
    return null;
  }

  // Transform with all fields (camelCase only)
  return {
    id: result.caseEntry.id,
    timestamp: result.caseEntry.timestamp,
    type: result.caseEntry.entryType,
    description: result.caseEntry.description,
    performedBy: result.caseEntry.performedBy,
    performedByName: result.caseEntry.performedByName,
    performedByRole: result.caseEntry.performedByRole,
    canEdit: result.caseEntry.canEdit ?? true, // Use nullish coalescing for consistency
    details: result.caseEntry.details // Include details field for complete transformation
  };
}

/**
 * Transform and add case entry in one operation
 *
 * Convenience function that transforms the case entry and adds it to state
 * if it exists. Reduces boilerplate in consuming code.
 *
 * @param result - Atomic API response
 * @param addCaseSheetEntry - Function to add entry to state
 * @returns true if entry was added, false otherwise
 *
 * @example
 * ```typescript
 * // After medication atomic operation
 * const result = await MedicationService.addMedication(...);
 * transformAndAddCaseEntry(result, addCaseSheetEntry);
 * ```
 */
export function transformAndAddCaseEntry(
  result: any,
  addCaseSheetEntry: (entry: caseSheetEntry) => void
): boolean {
  const caseEntry = transformAtomicCaseEntry(result);

  if (caseEntry) {
    addCaseSheetEntry(caseEntry);
    return true;
  }

  return false;
}

/**
 * Unit Tests for Case Entry Transformer
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Tests single source of truth for case entry transformation
 */

import { transformAtomicCaseEntry, transformAndAddCaseEntry } from '../caseEntryTransformer';
import { caseSheetEntry } from '../../types';

describe('caseEntryTransformer', () => {
  describe('transformAtomicCaseEntry', () => {
    it('should return null when result is null', () => {
      expect(transformAtomicCaseEntry(null)).toBeNull();
    });

    it('should return null when result is undefined', () => {
      expect(transformAtomicCaseEntry(undefined)).toBeNull();
    });

    it('should return null when result has no caseEntry', () => {
      expect(transformAtomicCaseEntry({})).toBeNull();
    });

    it('should return null when result.caseEntry is null', () => {
      expect(transformAtomicCaseEntry({ caseEntry: null })).toBeNull();
    });

    it('should transform complete case entry with all fields', () => {
      const result = {
        caseEntry: {
          id: 'CE123',
          timestamp: '2025-10-11T10:00:00Z',
          entryType: 'medication',
          description: 'Test medication prescribed',
          performedBy: 'DOC001',
          performedByName: 'Dr. Smith',
          performedByRole: 'Doctor',
          canEdit: true,
          details: { dosage: '500mg', route: 'PO' }
        }
      };

      const transformed = transformAtomicCaseEntry(result);

      expect(transformed).toEqual({
        id: 'CE123',
        timestamp: '2025-10-11T10:00:00Z',
        type: 'medication',
        description: 'Test medication prescribed',
        performedBy: 'DOC001',
        performedByName: 'Dr. Smith',
        performedByRole: 'Doctor',
        canEdit: true,
        details: { dosage: '500mg', route: 'PO' }
      });
    });

    it('should transform case entry with minimum required fields', () => {
      const result = {
        caseEntry: {
          id: 'CE124',
          timestamp: '2025-10-11T11:00:00Z',
          entryType: 'investigation',
          description: 'Lab test ordered',
          performedBy: 'DOC002'
        }
      };

      const transformed = transformAtomicCaseEntry(result);

      expect(transformed).not.toBeNull();
      expect(transformed?.id).toBe('CE124');
      expect(transformed?.type).toBe('investigation');
      expect(transformed?.description).toBe('Lab test ordered');
      expect(transformed?.performedBy).toBe('DOC002');
    });

    it('should default canEdit to true when undefined', () => {
      const result = {
        caseEntry: {
          id: 'CE125',
          timestamp: '2025-10-11T12:00:00Z',
          entryType: 'therapy',
          description: 'Therapy session',
          performedBy: 'TH001'
          // canEdit not provided
        }
      };

      const transformed = transformAtomicCaseEntry(result);
      expect(transformed?.canEdit).toBe(true);
    });

    it('should default canEdit to true when null', () => {
      const result = {
        caseEntry: {
          id: 'CE126',
          timestamp: '2025-10-11T13:00:00Z',
          entryType: 'therapy',
          description: 'Therapy session',
          performedBy: 'TH001',
          canEdit: null
        }
      };

      const transformed = transformAtomicCaseEntry(result);
      expect(transformed?.canEdit).toBe(true);
    });

    it('should respect canEdit: false when explicitly set', () => {
      const result = {
        caseEntry: {
          id: 'CE127',
          timestamp: '2025-10-11T14:00:00Z',
          entryType: 'medication',
          description: 'Old medication (locked)',
          performedBy: 'DOC003',
          canEdit: false
        }
      };

      const transformed = transformAtomicCaseEntry(result);
      expect(transformed?.canEdit).toBe(false);
    });

    it('should include details field when provided', () => {
      const result = {
        caseEntry: {
          id: 'CE128',
          timestamp: '2025-10-11T15:00:00Z',
          entryType: 'medication',
          description: 'Medication administered',
          performedBy: 'NUR001',
          details: {
            medicationName: 'Aspirin',
            dosage: '100mg',
            route: 'Oral'
          }
        }
      };

      const transformed = transformAtomicCaseEntry(result);
      expect(transformed?.details).toEqual({
        medicationName: 'Aspirin',
        dosage: '100mg',
        route: 'Oral'
      });
    });

    it('should handle missing optional fields gracefully', () => {
      const result = {
        caseEntry: {
          id: 'CE129',
          timestamp: '2025-10-11T16:00:00Z',
          entryType: 'note',
          description: 'Clinical note',
          performedBy: 'DOC004'
          // performedByName, performedByRole, details not provided
        }
      };

      const transformed = transformAtomicCaseEntry(result);
      expect(transformed?.performedByName).toBeUndefined();
      expect(transformed?.performedByRole).toBeUndefined();
      expect(transformed?.details).toBeUndefined();
    });
  });

  describe('transformAndAddCaseEntry', () => {
    it('should call addCaseSheetEntry when case entry exists', () => {
      const mockAdd = jest.fn();
      const result = {
        caseEntry: {
          id: 'CE130',
          timestamp: '2025-10-11T17:00:00Z',
          entryType: 'medication',
          description: 'Test medication',
          performedBy: 'DOC005'
        }
      };

      const added = transformAndAddCaseEntry(result, mockAdd);

      expect(added).toBe(true);
      expect(mockAdd).toHaveBeenCalledTimes(1);
      expect(mockAdd).toHaveBeenCalledWith(expect.objectContaining({
        id: 'CE130',
        type: 'medication',
        description: 'Test medication',
        performedBy: 'DOC005'
      }));
    });

    it('should not call addCaseSheetEntry when no case entry', () => {
      const mockAdd = jest.fn();
      const result = {};

      const added = transformAndAddCaseEntry(result, mockAdd);

      expect(added).toBe(false);
      expect(mockAdd).not.toHaveBeenCalled();
    });

    it('should not call addCaseSheetEntry when result is null', () => {
      const mockAdd = jest.fn();

      const added = transformAndAddCaseEntry(null, mockAdd);

      expect(added).toBe(false);
      expect(mockAdd).not.toHaveBeenCalled();
    });

    it('should not call addCaseSheetEntry when caseEntry is null', () => {
      const mockAdd = jest.fn();
      const result = { caseEntry: null };

      const added = transformAndAddCaseEntry(result, mockAdd);

      expect(added).toBe(false);
      expect(mockAdd).not.toHaveBeenCalled();
    });

    it('should pass complete transformed entry to addCaseSheetEntry', () => {
      const mockAdd = jest.fn();
      const result = {
        caseEntry: {
          id: 'CE131',
          timestamp: '2025-10-11T18:00:00Z',
          entryType: 'investigation',
          description: 'Lab results available',
          performedBy: 'LAB001',
          performedByName: 'Lab Tech',
          performedByRole: 'Technician',
          canEdit: false,
          details: { testType: 'CBC', urgent: true }
        }
      };

      transformAndAddCaseEntry(result, mockAdd);

      expect(mockAdd).toHaveBeenCalledWith({
        id: 'CE131',
        timestamp: '2025-10-11T18:00:00Z',
        type: 'investigation',
        description: 'Lab results available',
        performedBy: 'LAB001',
        performedByName: 'Lab Tech',
        performedByRole: 'Technician',
        canEdit: false,
        details: { testType: 'CBC', urgent: true }
      });
    });

    it('should handle case entry with canEdit defaulting to true', () => {
      const mockAdd = jest.fn();
      const result = {
        caseEntry: {
          id: 'CE132',
          timestamp: '2025-10-11T19:00:00Z',
          entryType: 'therapy',
          description: 'Therapy completed',
          performedBy: 'TH002'
          // canEdit not provided
        }
      };

      transformAndAddCaseEntry(result, mockAdd);

      const callArg = mockAdd.mock.calls[0][0];
      expect(callArg.canEdit).toBe(true);
    });
  });

  describe('Edge Cases and Error Handling', () => {
    it('should handle malformed result object gracefully', () => {
      const malformed = { somethingElse: 'value' };
      expect(transformAtomicCaseEntry(malformed)).toBeNull();
    });

    it('should handle result with empty caseEntry object', () => {
      const result = { caseEntry: {} };
      const transformed = transformAtomicCaseEntry(result);

      // Should still create entry but with undefined fields
      expect(transformed).not.toBeNull();
      expect(transformed?.canEdit).toBe(true); // Should default to true
    });

    it('should preserve all field types correctly', () => {
      const result = {
        caseEntry: {
          id: 'CE133',
          timestamp: '2025-10-11T20:00:00Z',
          entryType: 'medication',
          description: 'Complex entry',
          performedBy: 'DOC006',
          performedByName: 'Dr. Jones',
          performedByRole: 'Senior Doctor',
          canEdit: true,
          details: {
            nested: {
              deeply: {
                value: 123
              }
            },
            array: [1, 2, 3],
            boolean: true,
            number: 42
          }
        }
      };

      const transformed = transformAtomicCaseEntry(result);

      expect(typeof transformed?.id).toBe('string');
      expect(typeof transformed?.timestamp).toBe('string');
      expect(typeof transformed?.type).toBe('string');
      expect(typeof transformed?.canEdit).toBe('boolean');
      expect(typeof transformed?.details).toBe('object');
      expect(Array.isArray(transformed?.details.array)).toBe(true);
    });
  });
});

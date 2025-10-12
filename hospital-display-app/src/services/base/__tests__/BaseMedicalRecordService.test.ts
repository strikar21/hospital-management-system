/**
 * Unit Tests for BaseMedicalRecordService
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Tests generic CRUD operations for all medical record types
 */

import { BaseMedicalRecordService, MedicalRecordConfig } from '../BaseMedicalRecordService';
import { medication } from '../../../types';

// Concrete test implementation of BaseMedicalRecordService
class TestMedicalRecordService extends BaseMedicalRecordService<medication> {
  protected getConfig(): MedicalRecordConfig {
    return {
      recordType: 'medications',
      recordTypeSingular: 'medication',
      recordTypePlural: 'medications'
    };
  }

  // Expose protected methods for testing
  public testHandleV2Response(response: any) {
    return this.handleV2Response(response);
  }

  public testTransformAddPayload(recordData: any, userId: string) {
    return this.transformAddPayload(recordData, userId);
  }

  public testValidateRecord(record: any, requiredFields: string[]) {
    return this.validateRecord(record, requiredFields);
  }
}

describe('BaseMedicalRecordService', () => {
  let service: TestMedicalRecordService;

  beforeEach(() => {
    service = new TestMedicalRecordService();
  });

  // ================================
  // RESPONSE HANDLING TESTS
  // ================================

  describe('handleV2Response', () => {
    it('should handle response with type-specific field (medications)', () => {
      const response = {
        medications: [
          { id: 'MED001', name: 'Aspirin' },
          { id: 'MED002', name: 'Ibuprofen' }
        ]
      };

      const result = service.testHandleV2Response(response);

      expect(result).toEqual(response.medications);
      expect(result).toHaveLength(2);
    });

    it('should handle response with generic data field', () => {
      const response = {
        data: [
          { id: 'MED001', name: 'Aspirin' },
          { id: 'MED002', name: 'Ibuprofen' }
        ]
      };

      const result = service.testHandleV2Response(response);

      expect(result).toEqual(response.data);
      expect(result).toHaveLength(2);
    });

    it('should handle response with sessions field (for therapy)', () => {
      const response = {
        sessions: [
          { id: 'THER001', name: 'Physiotherapy' }
        ]
      };

      const result = service.testHandleV2Response(response);

      expect(result).toEqual(response.sessions);
      expect(result).toHaveLength(1);
    });

    it('should handle array response', () => {
      const response = [
        { id: 'MED001', name: 'Aspirin' },
        { id: 'MED002', name: 'Ibuprofen' }
      ];

      const result = service.testHandleV2Response(response);

      expect(result).toEqual(response);
      expect(result).toHaveLength(2);
    });

    it('should return empty array for null response', () => {
      const result = service.testHandleV2Response(null);

      expect(result).toEqual([]);
      expect(result).toHaveLength(0);
    });

    it('should return empty array for undefined response', () => {
      const result = service.testHandleV2Response(undefined);

      expect(result).toEqual([]);
      expect(result).toHaveLength(0);
    });

    it('should return empty array for non-array, non-object response', () => {
      const result = service.testHandleV2Response('invalid');

      expect(result).toEqual([]);
      expect(result).toHaveLength(0);
    });
  });

  // ================================
  // PAYLOAD TRANSFORMATION TESTS
  // ================================

  describe('transformAddPayload', () => {
    it('should return data as-is by default (base implementation)', () => {
      const recordData = {
        name: 'Aspirin',
        dosage: '500mg',
        frequency: 'twice daily'
      };

      const result = service.testTransformAddPayload(recordData, 'USER001');

      expect(result).toEqual(recordData);
    });

    it('should not modify original data object', () => {
      const recordData = {
        name: 'Aspirin',
        dosage: '500mg',
        frequency: 'twice daily'
      };

      const original = { ...recordData };
      service.testTransformAddPayload(recordData, 'USER001');

      expect(recordData).toEqual(original);
    });
  });

  // ================================
  // VALIDATION TESTS
  // ================================

  describe('validateRecord', () => {
    it('should validate record with all required fields', () => {
      const record = {
        name: 'Aspirin',
        dosage: '500mg',
        frequency: 'twice daily'
      };

      const isValid = service.testValidateRecord(record, ['name', 'dosage', 'frequency']);

      expect(isValid).toBe(true);
    });

    it('should fail validation when required field is missing', () => {
      const record = {
        name: 'Aspirin',
        dosage: '500mg'
        // frequency missing
      };

      const isValid = service.testValidateRecord(record, ['name', 'dosage', 'frequency']);

      expect(isValid).toBe(false);
    });

    it('should fail validation when required field is null', () => {
      const record = {
        name: 'Aspirin',
        dosage: null,
        frequency: 'twice daily'
      };

      const isValid = service.testValidateRecord(record, ['name', 'dosage', 'frequency']);

      expect(isValid).toBe(false);
    });

    it('should fail validation when required field is undefined', () => {
      const record = {
        name: 'Aspirin',
        dosage: undefined,
        frequency: 'twice daily'
      };

      const isValid = service.testValidateRecord(record, ['name', 'dosage', 'frequency']);

      expect(isValid).toBe(false);
    });

    it('should fail validation when required field is empty string', () => {
      const record = {
        name: 'Aspirin',
        dosage: '',
        frequency: 'twice daily'
      };

      const isValid = service.testValidateRecord(record, ['name', 'dosage', 'frequency']);

      expect(isValid).toBe(false);
    });

    it('should fail validation when record is null', () => {
      const isValid = service.testValidateRecord(null, ['name', 'dosage']);

      expect(isValid).toBe(false);
    });

    it('should fail validation when record is not an object', () => {
      const isValid = service.testValidateRecord('invalid', ['name', 'dosage']);

      expect(isValid).toBe(false);
    });

    it('should pass validation with empty required fields array', () => {
      const record = {
        name: 'Aspirin'
      };

      const isValid = service.testValidateRecord(record, []);

      expect(isValid).toBe(true);
    });

    it('should allow zero as valid value', () => {
      const record = {
        name: 'Aspirin',
        dosage: 0,
        frequency: 'once daily'
      };

      const isValid = service.testValidateRecord(record, ['name', 'dosage', 'frequency']);

      expect(isValid).toBe(true);
    });

    it('should allow false as valid value', () => {
      const record = {
        name: 'Aspirin',
        active: false,
        frequency: 'once daily'
      };

      const isValid = service.testValidateRecord(record, ['name', 'active', 'frequency']);

      expect(isValid).toBe(true);
    });
  });

  // ================================
  // CONFIGURATION TESTS
  // ================================

  describe('getConfig', () => {
    it('should return correct configuration', () => {
      const config = (service as any).getConfig();

      expect(config.recordType).toBe('medications');
      expect(config.recordTypeSingular).toBe('medication');
      expect(config.recordTypePlural).toBe('medications');
    });
  });

  // ================================
  // TYPE SAFETY TESTS
  // ================================

  describe('Type Safety', () => {
    it('should enforce generic type parameter', () => {
      // This test verifies that TypeScript enforces the generic type
      // If this compiles, type safety is working
      const typedService = new TestMedicalRecordService();

      // TypeScript should allow this
      const validResponse: medication[] = [
        {
          id: 'MED001',
          name: 'Aspirin',
          dosage: '500mg',
          frequency: 'twice daily',
          route: 'PO',
          duration: '7 days',
          status: 'active',
          prescribedBy: 'DOC001',
          startDate: new Date().toISOString(),
          createdAt: new Date().toISOString(),
          canEdit: true
        }
      ];

      expect(Array.isArray(validResponse)).toBe(true);
    });
  });
});

describe('BaseMedicalRecordService - Edge Cases', () => {
  let service: TestMedicalRecordService;

  beforeEach(() => {
    service = new TestMedicalRecordService();
  });

  it('should handle very large response arrays', () => {
    const largeArray = Array.from({ length: 1000 }, (_, i) => ({
      id: `MED${String(i).padStart(4, '0')}`,
      name: `Medication ${i}`
    }));

    const response = { medications: largeArray };
    const result = service.testHandleV2Response(response);

    expect(result).toHaveLength(1000);
    expect(result[0].id).toBe('MED0000');
    expect(result[999].id).toBe('MED0999');
  });

  it('should handle nested objects in response', () => {
    const response = {
      medications: [
        {
          id: 'MED001',
          name: 'Aspirin',
          details: {
            manufacturer: 'Pharma Inc',
            expiryDate: '2026-01-01'
          }
        }
      ]
    };

    const result = service.testHandleV2Response(response);

    expect(result).toHaveLength(1);
    expect(result[0].details).toBeDefined();
    expect(result[0].details.manufacturer).toBe('Pharma Inc');
  });

  it('should handle response with mixed data types', () => {
    const response = {
      medications: [
        {
          id: 'MED001',
          name: 'Aspirin',
          dosage: 500,  // number
          active: true,  // boolean
          notes: null,  // null
          tags: ['pain', 'fever']  // array
        }
      ]
    };

    const result = service.testHandleV2Response(response);

    expect(result).toHaveLength(1);
    expect(typeof result[0].dosage).toBe('number');
    expect(typeof result[0].active).toBe('boolean');
    expect(result[0].notes).toBeNull();
    expect(Array.isArray(result[0].tags)).toBe(true);
  });
});

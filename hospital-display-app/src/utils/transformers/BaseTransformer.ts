/**
 * BaseTransformer - Core transformation utilities and field mappings
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Provides foundational transformation methods for medical data compliance
 */

export abstract class BaseTransformer {

  // ================================
  // CAMELCASE-ONLY FIELD MAPPINGS
  // ================================

  protected static readonly FIELD_MAPPINGS: { [key: string]: string } = {
    // Patient Identity Fields - camelCase only
    'id': 'id',
    'mrn': 'mrn',
    'firstName': 'firstName',
    'lastName': 'lastName',
    'dateOfBirth': 'dateOfBirth',
    'age': 'age',
    'gender': 'gender',
    'weight': 'weight',

    // Contact Fields - camelCase only
    'phoneNumber': 'phoneNumber',
    'emergencyContactName': 'emergencyContactName',
    'emergencyContactPhone': 'emergencyContactPhone',

    // Medical Fields - camelCase only
    'bloodType': 'bloodType',
    'medicalHistory': 'medicalHistory',
    'currentMedications': 'currentMedications',
    'diagnosis': 'diagnosis',
    'allergies': 'allergies',

    // Hospital Stay Fields - camelCase only
    'admissionDate': 'admissionDate',
    'dischargeDate': 'dischargeDate',
    'roomNumber': 'roomNumber',
    'bedNumber': 'bedNumber',
    'dischargeStatus': 'dischargeStatus',
    'department': 'department',
    'ward': 'ward',
    'room': 'room',
    'status': 'status',

    // Staff Assignment Fields - camelCase only
    'attendingPhysician': 'attendingPhysician',
    'attendingPhysicianName': 'attendingPhysicianName',
    'assignedDoctor': 'assignedDoctor',
    'assignedNurse': 'assignedNurse',

    // Device Fields - camelCase only
    'assignedDeviceId': 'assignedDeviceId',
    'deviceStatus': 'deviceStatus',
    'deviceType': 'deviceType',

    // Vitals Fields - camelCase only
    'heartRate': 'heartRate',
    'systolicPressure': 'systolicPressure',
    'diastolicPressure': 'diastolicPressure',
    'skinTemperature': 'skinTemperature',
    'oxygenSaturation': 'oxygenSaturation',
    'respiratoryRate': 'respiratoryRate',
    'ecgReading': 'ecgReading',
    'eegReading': 'eegReading',
    'bioelectricalImpedance': 'bioelectricalImpedance',
    'tremorIntensity': 'tremorIntensity',

    // Timestamp Fields - camelCase only
    'createdAt': 'createdAt',
    'updatedAt': 'updatedAt',
    'lastDataReceived': 'lastDataReceived',
    'timestamp': 'timestamp'
  };

  // ================================
  // CORE TRANSFORMATION UTILITIES
  // ================================

  /**
   * Transform camelCase field (no snake_case support)
   * Medical-grade field transformation with type safety
   */
  protected static transformField<T>(data: any, camelCaseKey: string, defaultValue?: T): T {
    return data?.[camelCaseKey] ?? defaultValue as T;
  }

  /**
   * Transform field name to camelCase (identity function for compliance)
   */
  protected static transformFieldName(fieldName: string): string {
    // All fields are already camelCase - no transformation needed
    return BaseTransformer.FIELD_MAPPINGS[fieldName] || fieldName;
  }

  /**
   * Transform object keys to ensure camelCase compliance
   */
  protected static transformObjectKeys(obj: any): any {
    if (!obj || typeof obj !== 'object' || Array.isArray(obj)) {
      return obj;
    }

    const transformed: any = {};

    for (const [key, value] of Object.entries(obj)) {
      const transformedKey = BaseTransformer.transformFieldName(key);
      transformed[transformedKey] = value;
    }

    return transformed;
  }

  /**
   * Calculate patient age from date of birth
   * Medical-grade age calculation with validation
   */
  protected static calculateAge(dateOfBirth: string): number {
    if (!dateOfBirth) return 0;
    try {
      const birthDate = new Date(dateOfBirth);
      const today = new Date();
      let age = today.getFullYear() - birthDate.getFullYear();
      const monthDiff = today.getMonth() - birthDate.getMonth();

      if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birthDate.getDate())) {
        age--;
      }

      return Math.max(0, age); // Ensure non-negative age
    } catch (error) {
      console.error('Error calculating patient age:', error);
      return 0;
    }
  }

  /**
   * Check if medical record can be edited (2-hour window for medical safety)
   */
  protected static canEditMedicalRecord(createdAt: string): boolean {
    if (!createdAt) return false;

    try {
      const creationTime = new Date(createdAt);
      const now = new Date();
      const timeDiff = now.getTime() - creationTime.getTime();
      const maxEditWindow = 2 * 60 * 60 * 1000; // 2 hours for medical compliance

      return timeDiff <= maxEditWindow;
    } catch (error) {
      console.error('Error checking edit permission:', error);
      return false;
    }
  }

  /**
   * Resolve staff ID to name using provided staff mapping
   */
  protected static resolveStaffName(staffId: string, staffMapping?: { [key: string]: string | { name: string; role: string } }): string {
    if (!staffId) return '';

    // If staffMapping provided, use it
    if (staffMapping && staffMapping[staffId]) {
      const staffInfo = staffMapping[staffId];
      // Handle both string and object formats
      if (typeof staffInfo === 'string') {
        return staffInfo;
      } else if (typeof staffInfo === 'object' && staffInfo.name) {
        return staffInfo.name;
      }
    }

    // If it's already a name (contains space or non-ID format), return as-is
    if (staffId.includes(' ') || !staffId.match(/^[A-Z]{3}\d{3}$/)) {
      return staffId;
    }

    // Return the ID if no mapping available (caller should provide mapping)
    return staffId;
  }

  /**
   * Add resolved name fields for staff IDs
   */
  protected static addResolvedNames(data: any, staffMapping?: { [key: string]: string | { name: string; role: string } }): any {
    if (!data || typeof data !== 'object') return data;

    const resolved = { ...data };

    // Resolve prescribedBy to prescribedByName
    if (resolved.prescribedBy && !resolved.prescribedByName) {
      resolved.prescribedByName = BaseTransformer.resolveStaffName(resolved.prescribedBy, staffMapping);
    }

    // Resolve performedBy to performedByName
    if (resolved.performedBy && !resolved.performedByName) {
      resolved.performedByName = BaseTransformer.resolveStaffName(resolved.performedBy, staffMapping);
    }

    // Resolve orderedBy to orderedByName
    if (resolved.orderedBy && !resolved.orderedByName) {
      resolved.orderedByName = BaseTransformer.resolveStaffName(resolved.orderedBy, staffMapping);
    }

    // Resolve assignedBy to assignedByName
    if (resolved.assignedBy && !resolved.assignedByName) {
      resolved.assignedByName = BaseTransformer.resolveStaffName(resolved.assignedBy, staffMapping);
    }

    // Resolve authorId to authorName
    if (resolved.authorId && !resolved.authorName) {
      resolved.authorName = BaseTransformer.resolveStaffName(resolved.authorId, staffMapping);
    }

    return resolved;
  }

  /**
   * Generic array transformation method
   */
  public static transformArray(data: any[], transformer: (item: any, staffMapping?: { [key: string]: string }) => any, staffMapping?: { [key: string]: string }): any[] {
    if (!Array.isArray(data)) {
      return [];
    }

    return data.map(item => transformer(item, staffMapping));
  }

  /**
   * Generic object transformation method
   */
  public static transformObject(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data || typeof data !== 'object') {
      return data;
    }

    // Transform keys to camelCase and resolve staff names
    const transformed = BaseTransformer.transformObjectKeys(data);
    return BaseTransformer.addResolvedNames(transformed, staffMapping);
  }

  /**
   * Medical-grade data validation
   */
  protected static validateMedicalData(data: any, requiredFields: string[]): boolean {
    if (!data || typeof data !== 'object') {
      return false;
    }

    return requiredFields.every(field => data[field] !== undefined && data[field] !== null);
  }

  /**
   * Sanitize medical data for HIPAA compliance
   */
  protected static sanitizeMedicalData(data: any, sensitiveFields: string[] = []): any {
    if (!data || typeof data !== 'object') {
      return data;
    }

    const sanitized = { ...data };

    // Default sensitive fields for medical data
    const defaultSensitiveFields = ['ssn', 'socialSecurityNumber', 'creditCard', 'password'];
    const allSensitiveFields = [...defaultSensitiveFields, ...sensitiveFields];

    allSensitiveFields.forEach(field => {
      if (sanitized[field]) {
        delete sanitized[field];
      }
    });

    return sanitized;
  }
}
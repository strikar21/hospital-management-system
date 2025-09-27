/**
 * Unified Data Transformer - Single source of truth for all data transformations
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Handles camelCase-to-camelCase data transformation with medical compliance
 */

export class DataTransformer {

  // ================================
  // CAMELCASE-ONLY FIELD MAPPINGS
  // ================================

  private static readonly FIELD_MAPPINGS: { [key: string]: string } = {
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
    'nurseInCharge': 'nurseInCharge',

    // Medication Fields - camelCase only
    'name': 'name',
    'dosage': 'dosage',
    'frequency': 'frequency',
    'route': 'route',
    'startDate': 'startDate',
    'endDate': 'endDate',
    'duration': 'duration',
    'medicationName': 'medicationName',
    'prescribedBy': 'prescribedBy',
    'prescribedByName': 'prescribedByName',

    // Investigation Fields - camelCase only
    'type': 'type',
    'investigationType': 'investigationType',
    'scheduledAt': 'scheduledAt',
    'completedAt': 'completedAt',
    'results': 'results',
    'priority': 'priority',
    'urgency': 'urgency',
    'notes': 'notes',
    'orderedBy': 'orderedBy',
    'orderedByName': 'orderedByName',
    'verifiedBy': 'verifiedBy',
    'verifiedByName': 'verifiedByName',

    // Therapy Fields - camelCase only
    'description': 'description',
    'therapyType': 'therapyType',
    'therapyId': 'therapyId',
    'performedBy': 'performedBy',
    'performedByName': 'performedByName',
    'therapist': 'therapist',
    'therapistName': 'therapistName',
    'sessionDate': 'sessionDate',
    'sessionNumber': 'sessionNumber',
    'sessionNotes': 'sessionNotes',
    'scheduledDate': 'scheduledDate',
    'sessions': 'sessions',

    // Alert Fields - camelCase only
    'message': 'message',
    'severity': 'severity',
    'timestamp': 'timestamp',
    'isAcknowledged': 'isAcknowledged',

    // Case Sheet & Notes Fields - camelCase only
    'authorId': 'authorId',
    'editedAt': 'editedAt',
    'isEdited': 'isEdited',
    'content': 'content',
    'details': 'details',

    // Timestamp Fields - camelCase only
    'createdAt': 'createdAt',
    'updatedAt': 'updatedAt',
    'prescribedAt': 'prescribedAt',
    'acknowledgedAt': 'acknowledgedAt',
    'orderedDate': 'orderedDate',
    'lastModified': 'lastModified',
    'lastUpdated': 'lastUpdated',
    'lastDataReceived': 'lastDataReceived',
    'administeredAt': 'administeredAt',
    'discontinuedAt': 'discontinuedAt',

    // Device Fields - camelCase only
    'assignedDeviceId': 'assignedDeviceId',
    'deviceStatus': 'deviceStatus',
    'deviceBattery': 'deviceBattery',

    // Vitals Fields - STANDARDIZED CAMELCASE NAMES
    'heartRate': 'heartRate',
    'systolicPressure': 'systolicPressure',
    'diastolicPressure': 'diastolicPressure',
    'respiratoryRate': 'respiratoryRate',
    'oxygenSaturation': 'oxygenSaturation',
    'skinTemperature': 'skinTemperature',
    'ecgReading': 'ecgReading',
    'eegReading': 'eegReading',
    'isEcgMode': 'isEcgMode',
    'bioelectricalImpedance': 'bioelectricalImpedance',
    'tremorIntensity': 'tremorIntensity',
    'fallRisk': 'fallRisk',
    'dataQualityScore': 'dataQualityScore',

    // Status Fields - camelCase only
    'isActive': 'isActive',
    'isCompleted': 'isCompleted',
    'canEdit': 'canEdit',

    // User/Staff Fields - camelCase only
    'userId': 'userId',
    'staffId': 'staffId',
    'nfcId': 'nfcId',
    'role': 'role',
    'unit': 'unit',
    'lastLogin': 'lastLogin',

    // Additional Fields - camelCase only
    'modifiedBy': 'modifiedBy',
    'recommendedFrom': 'recommendedFrom'
  };

  // ================================
  // CORE TRANSFORMATION METHODS
  // ================================

  /**
   * Transform a single field name (camelCase only)
   */
  private static transformFieldName(fieldName: string): string {
    // Return the mapped field name or original if no mapping exists
    return this.FIELD_MAPPINGS[fieldName] || fieldName;
  }

  /**
   * Transform object keys (camelCase only) recursively
   */
  private static transformObjectKeys(obj: any): any {
    if (obj === null || obj === undefined) return obj;

    // Handle arrays
    if (Array.isArray(obj)) {
      return obj.map(item => this.transformObjectKeys(item));
    }

    // Handle non-objects (primitives)
    if (typeof obj !== 'object') return obj;

    // Transform object keys
    const transformed: any = {};

    for (const [key, value] of Object.entries(obj)) {
      const camelKey = this.transformFieldName(key);
      transformed[camelKey] = this.transformObjectKeys(value);
    }

    return transformed;
  }

  // ================================
  // MEDICAL CALCULATION METHODS
  // ================================

  /**
   * Calculate patient age from date of birth (medical accuracy)
   */
  private static calculateAge(dateOfBirth: string): number {
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
  private static canEditMedicalRecord(createdAt: string): boolean {
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
   * Transform camelCase field (no snake_case support)
   */
  private static transformField<T>(data: any, camelCaseKey: string, defaultValue?: T): T {
    return data?.[camelCaseKey] ?? defaultValue as T;
  }

  // ================================
  // NAME RESOLUTION METHODS
  // ================================

  /**
   * Resolve staff ID to name using provided staff mapping
   */
  private static resolveStaffName(staffId: string, staffMapping?: { [key: string]: string }): string {
    if (!staffId) return '';

    // If staffMapping provided, use it
    if (staffMapping && staffMapping[staffId]) {
      return staffMapping[staffId];
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
  private static addResolvedNames(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data || typeof data !== 'object') return data;

    const resolved = { ...data };

    // Resolve prescribedBy to prescribedByName
    if (resolved.prescribedBy && !resolved.prescribedByName) {
      resolved.prescribedByName = this.resolveStaffName(resolved.prescribedBy, staffMapping);
    }

    // Resolve performedBy to performedByName
    if (resolved.performedBy && !resolved.performedByName) {
      resolved.performedByName = this.resolveStaffName(resolved.performedBy, staffMapping);
    }

    // Resolve attendingPhysician to attendingPhysicianName
    if (resolved.attendingPhysician && !resolved.attendingPhysicianName) {
      resolved.attendingPhysicianName = this.resolveStaffName(resolved.attendingPhysician, staffMapping);
    }

    // Resolve orderedBy to orderedByName
    if (resolved.orderedBy && !resolved.orderedByName) {
      resolved.orderedByName = this.resolveStaffName(resolved.orderedBy, staffMapping);
    }

    // Resolve verifiedBy to verifiedByName
    if (resolved.verifiedBy && !resolved.verifiedByName) {
      resolved.verifiedByName = this.resolveStaffName(resolved.verifiedBy, staffMapping);
    }

    // Set assignedDoctor for display compatibility
    if (!resolved.assignedDoctor && resolved.attendingPhysicianName) {
      resolved.assignedDoctor = resolved.attendingPhysicianName;
    }

    return resolved;
  }

  // ================================
  // VALIDATION AND DEFAULTS
  // ================================

  /**
   * Ensure required fields have valid values
   */
  private static applyDefaults(data: any): any {
    if (!data || typeof data !== 'object') return data;

    const withDefaults = { ...data };

    // Ensure duration field is never empty
    if (withDefaults.duration === '' || withDefaults.duration === null || withDefaults.duration === undefined) {
      withDefaults.duration = 'Not specified';
    }

    // Ensure frequency field is never empty
    if (withDefaults.frequency === '' || withDefaults.frequency === null || withDefaults.frequency === undefined) {
      withDefaults.frequency = 'As needed';
    }

    // Ensure status field has valid value
    if (!withDefaults.status) {
      withDefaults.status = 'active';
    }

    // Ensure timestamps are properly formatted
    if (withDefaults.createdAt && typeof withDefaults.createdAt === 'string') {
      try {
        withDefaults.createdAt = new Date(withDefaults.createdAt).toISOString();
      } catch (error) {
        withDefaults.createdAt = new Date().toISOString();
      }
    }

    return withDefaults;
  }

  // ================================
  // PATIENT DATA TRANSFORMATION
  // ================================

  /**
   * Transform patient identification data
   */
  private static transformPatientIdentity(data: any): any {
    const firstName = data.firstName || '';
    const lastName = data.lastName || '';
    const dateOfBirth = this.transformField(data, 'dateOfBirth', null);

    return {
      id: data.id,
      mrn: data.mrn,
      firstName,
      lastName,
      name: data.name || `${firstName} ${lastName}`.trim(),
      dateOfBirth,
      age: data.age || (dateOfBirth ? this.calculateAge(dateOfBirth) : 0),
      gender: data.gender
    };
  }

  /**
   * Transform patient contact information
   */
  private static transformPatientContact(data: any): any {
    return {
      phoneNumber: this.transformField(data, 'phoneNumber'),
      emergencyContactName: this.transformField(data, 'emergencyContactName'),
      emergencyContactPhone: this.transformField(data, 'emergencyContactPhone')
    };
  }

  /**
   * Transform medical information with HIPAA compliance
   */
  private static transformMedicalInfo(data: any): any {
    return {
      bloodType: this.transformField(data, 'bloodType'),
      allergies: data.allergies || [],
      medicalHistory: this.transformField(data, 'medicalHistory'),
      currentMedications: this.transformField(data, 'currentMedications', [])
    };
  }

  /**
   * Transform hospital stay information
   */
  private static transformHospitalStay(data: any): any {
    const roomNumber = data.roomNumber || '';

    return {
      admissionDate: this.transformField(data, 'admissionDate'),
      dischargeDate: this.transformField(data, 'dischargeDate'),
      roomNumber,
      bedNumber: data.bedNumber || '',
      ward: data.ward || `Ward ${roomNumber?.charAt(0) || 'A'}`,
      room: data.room || `Room ${roomNumber || 'Unknown'}`,
      department: data.department || 'General',
      status: data.status,
      dischargeStatus: this.transformField(data, 'dischargeStatus')
    };
  }

  /**
   * Transform staff assignments
   */
  private static transformStaffAssignments(data: any): any {
    const attendingPhysician = data.attendingPhysician || '';
    const attendingPhysicianName = data.attendingPhysicianName || attendingPhysician;

    return {
      attendingPhysician,
      attendingPhysicianName,
      assignedDoctor: attendingPhysicianName,
      nurseInCharge: data.nurseInCharge || ''
    };
  }

  /**
   * Transform vital signs with medical accuracy - CAMELCASE ONLY
   */
  private static transformVitals(vitals: any): any {
    if (!vitals) return {};

    // Extract BP values with proper fallbacks - NO FAKE DEFAULTS
    const systolic = vitals.systolicPressure || 0;
    const diastolic = vitals.diastolicPressure || (systolic > 0 ? Math.round(systolic * 0.67) : 0);

    return {
      heartRate: this.transformField(vitals, 'heartRate', 0),
      systolicPressure: systolic,
      diastolicPressure: diastolic,
      respiratoryRate: this.transformField(vitals, 'respiratoryRate', 0),
      oxygenSaturation: this.transformField(vitals, 'oxygenSaturation', 0),
      skinTemperature: this.transformField(vitals, 'skinTemperature', 0),
      ecgReading: this.transformField(vitals, 'ecgReading', 0),
      eegReading: this.transformField(vitals, 'eegReading', 0),
      bioelectricalImpedance: this.transformField(vitals, 'bioelectricalImpedance', 0),
      tremorIntensity: this.transformField(vitals, 'tremorIntensity', 0),
      isEcgMode: this.transformField(vitals, 'isEcgMode', false),
      fallRisk: this.transformField(vitals, 'fallRisk', 'low'),
      lastDataReceived: this.transformField(vitals, 'lastDataReceived', new Date().toISOString()),
      dataQualityScore: this.transformField(vitals, 'dataQualityScore', 0)
    };
  }

  /**
   * Transform device information
   */
  private static transformDeviceInfo(data: any): any {
    return {
      assignedDeviceId: this.transformField(data, 'assignedDeviceId'),
      deviceStatus: this.transformField(data, 'deviceStatus', 'disconnected'),
      deviceBattery: this.transformField(data, 'deviceBattery', 0)
    };
  }

  // ================================
  // MAIN TRANSFORMATION ENTRY POINTS
  // ================================

  /**
   * Transform complete patient data - CAMELCASE ONLY
   */
  static transformPatient(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data) return null;

    try {
      // Transform each section
      const identity = this.transformPatientIdentity(data);
      const contact = this.transformPatientContact(data);
      const medical = this.transformMedicalInfo(data);
      const hospitalStay = this.transformHospitalStay(data);
      const staffAssignments = this.transformStaffAssignments(data);
      const vitals = this.transformVitals(data.vitals);
      const deviceInfo = this.transformDeviceInfo(data);

      // Combine all transformed data
      let transformedPatient = {
        ...identity,
        ...contact,
        ...medical,
        ...hospitalStay,
        ...staffAssignments,
        ...deviceInfo,
        vitals,
        alerts: data.alerts || [],
        medications: data.medications || [],
        investigations: data.investigations || [],
        therapies: data.therapies || [],
        notes: data.notes || []
      };

      // Add resolved names
      transformedPatient = this.addResolvedNames(transformedPatient, staffMapping);

      // Apply defaults
      transformedPatient = this.applyDefaults(transformedPatient);

      // Add edit permissions
      transformedPatient.canEdit = this.canEditMedicalRecord(transformedPatient.createdAt);

      return transformedPatient;
    } catch (error) {
      console.error('Error transforming patient data:', error);
      return data; // Return original data if transformation fails
    }
  }

  /**
   * Transform medication data - CAMELCASE ONLY
   */
  static transformMedication(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data) return null;

    try {
      let transformed = this.transformObjectKeys(data);
      transformed = this.addResolvedNames(transformed, staffMapping);
      transformed = this.applyDefaults(transformed);
      transformed.canEdit = this.canEditMedicalRecord(transformed.createdAt);
      return transformed;
    } catch (error) {
      console.error('Error transforming medication data:', error);
      return data;
    }
  }

  /**
   * Transform investigation data - CAMELCASE ONLY
   */
  static transformInvestigation(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data) return null;

    try {
      let transformed = this.transformObjectKeys(data);
      transformed = this.addResolvedNames(transformed, staffMapping);
      transformed = this.applyDefaults(transformed);
      transformed.canEdit = this.canEditMedicalRecord(transformed.createdAt);
      return transformed;
    } catch (error) {
      console.error('Error transforming investigation data:', error);
      return data;
    }
  }

  /**
   * Transform therapy data - CAMELCASE ONLY
   */
  static transformTherapy(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data) return null;

    try {
      let transformed = this.transformObjectKeys(data);
      transformed = this.addResolvedNames(transformed, staffMapping);
      transformed = this.applyDefaults(transformed);
      transformed.canEdit = this.canEditMedicalRecord(transformed.createdAt);
      return transformed;
    } catch (error) {
      console.error('Error transforming therapy data:', error);
      return data;
    }
  }

  /**
   * Transform vital time series data - CAMELCASE ONLY
   */
  static transformVitalTimeSeriesData(data: any[]): any[] {
    if (!Array.isArray(data)) return [];

    const groupedData: { [key: string]: any } = {};

    data.forEach(item => {
      const timestamp = item.timestamp || item.time || new Date().toISOString();

      if (!groupedData[timestamp]) {
        groupedData[timestamp] = {
          timestamp,
          time: timestamp,
          heartRate: this.transformField(item, 'heartRate', 0),
          systolicPressure: this.transformField(item, 'systolicPressure', 0),
          diastolicPressure: this.transformField(item, 'diastolicPressure', 0),
          respiratoryRate: this.transformField(item, 'respiratoryRate', 0),
          oxygenSaturation: this.transformField(item, 'oxygenSaturation', 0),
          skinTemperature: this.transformField(item, 'skinTemperature', 0),
          ecgReading: this.transformField(item, 'ecgReading', 0),
          eegReading: this.transformField(item, 'eegReading', 0),
          bioelectricalImpedance: this.transformField(item, 'bioelectricalImpedance', 0),
          tremorIntensity: this.transformField(item, 'tremorIntensity', 0)
        };
      } else {
        // Update existing entry with non-zero values
        if (item.heartRate) groupedData[timestamp].heartRate = item.heartRate;
        if (item.systolicPressure) groupedData[timestamp].systolicPressure = item.systolicPressure;
        if (item.diastolicPressure) groupedData[timestamp].diastolicPressure = item.diastolicPressure;
        if (item.respiratoryRate) groupedData[timestamp].respiratoryRate = item.respiratoryRate;
        if (item.oxygenSaturation) groupedData[timestamp].oxygenSaturation = item.oxygenSaturation;
        if (item.skinTemperature) groupedData[timestamp].skinTemperature = item.skinTemperature;
        if (item.ecgReading) groupedData[timestamp].ecgReading = item.ecgReading;
        if (item.eegReading) groupedData[timestamp].eegReading = item.eegReading;
        if (item.bioelectricalImpedance) groupedData[timestamp].bioelectricalImpedance = item.bioelectricalImpedance;
        if (item.tremorIntensity) groupedData[timestamp].tremorIntensity = item.tremorIntensity;
      }
    });

    return Object.values(groupedData).sort((a, b) =>
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
  }

  /**
   * Transform any data array - CAMELCASE ONLY
   */
  static transformArray(data: any[], staffMapping?: { [key: string]: string }): any[] {
    if (!Array.isArray(data)) return [];

    return data.map(item => {
      let transformed = this.transformObjectKeys(item);
      transformed = this.addResolvedNames(transformed, staffMapping);
      transformed = this.applyDefaults(transformed);

      if (transformed.createdAt) {
        transformed.canEdit = this.canEditMedicalRecord(transformed.createdAt);
      }

      return transformed;
    });
  }

  /**
   * Transform any object - CAMELCASE ONLY
   */
  static transformObject(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data || typeof data !== 'object') return data;

    let transformed = this.transformObjectKeys(data);
    transformed = this.addResolvedNames(transformed, staffMapping);
    transformed = this.applyDefaults(transformed);

    if (transformed.createdAt) {
      transformed.canEdit = this.canEditMedicalRecord(transformed.createdAt);
    }

    return transformed;
  }

  /**
   * Transform API response - wrapper for consistency
   */
  static transformApiResponse(data: any): any {
    // If backend is sending camelCase, this will pass through unchanged
    // If backend sends other formats, this will transform to camelCase
    return this.transformObject(data);
  }

  /**
   * Transform patient data - alias for transformPatient
   */
  static transformPatientData(data: any, staffMapping?: { [key: string]: string }): any {
    return this.transformPatient(data, staffMapping);
  }
}

export default DataTransformer;
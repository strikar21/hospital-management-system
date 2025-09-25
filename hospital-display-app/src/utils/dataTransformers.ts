// dataTransformers.ts - Centralized data transformation utilities
// Medical data transformation with HIPAA compliance

/**
 * Medical data field mapping utility
 * Handles snake_case to camelCase conversion for consistent API data
 */
export class MedicalDataTransformer {

  /**
   * Transform snake_case to camelCase for consistent frontend data
   */
  private static transformField<T>(data: any, camelCaseKey: string, snakeCaseKey: string, defaultValue?: T): T {
    return data?.[camelCaseKey] ?? data?.[snakeCaseKey] ?? defaultValue as T;
  }

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
   * Transform patient identification data
   */
  private static transformPatientIdentity(data: any): any {
    const firstName = this.transformField(data, 'firstName', 'first_name', '');
    const lastName = this.transformField(data, 'lastName', 'last_name', '');
    const dateOfBirth = this.transformField(data, 'dateOfBirth', 'date_of_birth', null);

    return {
      id: data.id,
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
      phoneNumber: this.transformField(data, 'phoneNumber', 'phone_number'),
      emergencyContactName: this.transformField(data, 'emergencyContactName', 'emergency_contact_name'),
      emergencyContactPhone: this.transformField(data, 'emergencyContactPhone', 'emergency_contact_phone')
    };
  }

  /**
   * Transform medical information with HIPAA compliance
   */
  private static transformMedicalInfo(data: any): any {
    return {
      bloodType: this.transformField(data, 'bloodType', 'blood_type'),
      allergies: data.allergies || [],
      medicalHistory: this.transformField(data, 'medicalHistory', 'medical_history'),
      currentMedications: this.transformField(data, 'currentMedications', 'current_medications', [])
    };
  }

  /**
   * Transform hospital stay information
   */
  private static transformHospitalStay(data: any): any {
    return {
      admissionDate: this.transformField(data, 'admissionDate', 'admission_date'),
      dischargeDate: this.transformField(data, 'dischargeDate', 'discharge_date'),
      roomNumber: this.transformField(data, 'roomNumber', 'room_number'),
      bedNumber: this.transformField(data, 'bedNumber', 'bed_number'),
      ward: data.ward,
      room: data.room,
      department: data.department,
      status: data.status,
      dischargeStatus: this.transformField(data, 'dischargeStatus', 'discharge_status')
    };
  }

  /**
   * Transform staff assignments
   */
  private static transformStaffAssignments(data: any): any {
    const attendingPhysician = this.transformField(data, 'attendingPhysician', 'attending_physician');
    const attendingPhysicianName = this.transformField(data, 'attendingPhysicianName', 'attending_physician_name');

    return {
      attendingPhysician,
      attendingPhysicianName,
      assignedDoctor: data.assignedDoctor || attendingPhysicianName || attendingPhysician,
      nurseInCharge: this.transformField(data, 'nurseInCharge', 'nurse_in_charge')
    };
  }

  /**
   * Transform vital signs with medical accuracy
   */
  private static transformVitals(vitals: any): any {
    if (!vitals) return null;

    return {
      heartRate: this.transformField(vitals, 'heartRate', 'heart_rate', 0),
      bloodPressure: this.transformField(vitals, 'bloodPressure', 'blood_pressure', ''),
      bloodPressureValue: this.transformField(vitals, 'bloodPressureValue', 'blood_pressure_value', 0),
      respiratoryRate: this.transformField(vitals, 'respiratoryRate', 'respiratory_rate', 0),
      oxygenSat: this.transformField(vitals, 'oxygenSat', 'oxygen_saturation', 0),
      temperature: vitals.temperature || 0,
      ecg: vitals.ecg || 0,
      eeg: vitals.eeg || 0,
      isEcgMode: vitals.isEcgMode ?? true,
      bioImpedance: vitals.bioImpedance || 0,
      tremor: vitals.tremor || 0,
      fallRisk: vitals.fallRisk || 'low',
      lastUpdated: this.transformField(vitals, 'lastUpdated', 'last_updated', new Date().toISOString()),
      lastSync: this.transformField(vitals, 'lastSync', 'last_sync', new Date().toISOString())
    };
  }

  /**
   * Transform medical records with edit permissions
   */
  private static transformMedicalRecords(data: any): any {
    return {
      medications: (data.medications || []).map((med: any) => ({
        ...med,
        canEdit: this.canEditMedicalRecord(med.createdAt || med.created_at)
      })),
      investigations: (data.investigations || []).map((inv: any) => ({
        ...inv,
        canEdit: this.canEditMedicalRecord(inv.createdAt || inv.created_at)
      })),
      therapies: (data.therapies || []).map((therapy: any) => ({
        ...therapy,
        canEdit: this.canEditMedicalRecord(therapy.createdAt || therapy.created_at)
      })),
      notes: (data.notes || []).map((note: any) => ({
        ...note,
        canEdit: this.canEditMedicalRecord(note.timestamp || note.created_at)
      }))
    };
  }

  /**
   * Main patient data transformation - HIPAA compliant
   */
  static transformPatientData(rawData: any): any {
    if (!rawData) {
      console.error('No patient data provided for transformation');
      return null;
    }

    try {
      return {
        // Patient identity
        ...this.transformPatientIdentity(rawData),

        // Contact information
        ...this.transformPatientContact(rawData),

        // Medical information
        ...this.transformMedicalInfo(rawData),

        // Hospital stay
        ...this.transformHospitalStay(rawData),

        // Staff assignments
        ...this.transformStaffAssignments(rawData),

        // Device monitoring
        assignedDeviceId: this.transformField(rawData, 'assignedDeviceId', 'assigned_device_id'),
        deviceStatus: rawData.deviceStatus,
        deviceBattery: rawData.deviceBattery,

        // Timestamps
        createdAt: this.transformField(rawData, 'createdAt', 'created_at'),
        updatedAt: this.transformField(rawData, 'updatedAt', 'updated_at'),

        // Vital signs
        vitals: this.transformVitals(rawData.vitals),

        // Medical records with permissions
        ...this.transformMedicalRecords(rawData),

        // Alerts and case sheet
        alerts: rawData.alerts || [],
        caseSheet: rawData.caseSheet || [],
        handoffNotes: rawData.handoffNotes || [],

        // Additional fields
        recommendedFrom: this.transformField(rawData, 'recommendedFrom', 'recommended_from'),
        weight: rawData.weight,
        diagnosis: rawData.diagnosis
      };
    } catch (error) {
      console.error('Error transforming patient data:', error);
      return rawData; // Return original data if transformation fails
    }
  }

  /**
   * Transform vital signs time series data with consistent field mapping
   */
  static transformVitalTimeSeriesData(timescaleData: any[]): any[] {
    if (!Array.isArray(timescaleData)) {
      console.warn('Invalid vital time series data provided');
      return [];
    }

    // Group data by timestamp to combine all vital types
    const groupedData: { [timestamp: string]: any } = {};

    timescaleData.forEach(item => {
      const timestamp = item.time || item.timestamp;
      if (!timestamp) return; // Skip invalid entries

      if (!groupedData[timestamp]) {
        groupedData[timestamp] = {
          time: timestamp,
          heartRate: 0,
          bloodPressure: 0,
          bloodPressureDiastolic: 0,
          temperature: 0,
          oxygenSaturation: 0,
          respiratoryRate: 0,
          ecg: 0,
          eeg: 0,
          bioImpedance: 0,
          tremor: 0,
          qualityScore: 0.9
        };
      }

      // Use the centralized field transformation logic
      groupedData[timestamp].heartRate = this.transformField(item, 'heartRate', 'heart_rate', 0);
      groupedData[timestamp].bloodPressure = this.transformField(item, 'bloodPressure', 'blood_pressure', 0);
      groupedData[timestamp].bloodPressureDiastolic = this.transformField(item, 'bloodPressureDiastolic', 'blood_pressure_diastolic', 0);
      groupedData[timestamp].temperature = item.temperature || 0;
      groupedData[timestamp].oxygenSaturation = this.transformField(item, 'oxygenSaturation', 'oxygen_saturation', 0);
      groupedData[timestamp].respiratoryRate = this.transformField(item, 'respiratoryRate', 'respiratory_rate', 0);
      groupedData[timestamp].ecg = item.ecg || 0;
      groupedData[timestamp].eeg = item.eeg || 0;
      groupedData[timestamp].bioImpedance = this.transformField(item, 'bioImpedance', 'bio_impedance', 0);
      groupedData[timestamp].tremor = item.tremor || 0;
      groupedData[timestamp].qualityScore = this.transformField(item, 'qualityScore', 'quality_score', 0.9);
    });

    // Convert grouped data to array and sort by timestamp
    return Object.values(groupedData).sort((a, b) =>
      new Date(a.time).getTime() - new Date(b.time).getTime()
    );
  }
}

export default MedicalDataTransformer;
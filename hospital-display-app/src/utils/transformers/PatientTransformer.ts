/**
 * PatientTransformer - Patient data transformation utilities
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Handles comprehensive patient data transformation with medical compliance
 */

import { BaseTransformer } from './BaseTransformer';

export class PatientTransformer extends BaseTransformer {

  // ================================
  // PATIENT IDENTITY TRANSFORMATION
  // ================================

  /**
   * Transform patient identification data
   */
  private static transformPatientIdentity(data: any): any {
    const firstName = data.firstName || '';
    const lastName = data.lastName || '';
    const dateOfBirth = PatientTransformer.transformField(data, 'dateOfBirth', null);

    return {
      id: data.id,
      mrn: data.mrn,
      firstName,
      lastName,
      name: data.name || `${firstName} ${lastName}`.trim(),
      dateOfBirth,
      age: data.age || (dateOfBirth ? PatientTransformer.calculateAge(dateOfBirth) : 0),
      gender: data.gender,
      weight: data.weight
    };
  }

  /**
   * Transform patient contact information
   */
  private static transformPatientContact(data: any): any {
    return {
      phoneNumber: PatientTransformer.transformField(data, 'phoneNumber'),
      emergencyContactName: PatientTransformer.transformField(data, 'emergencyContactName'),
      emergencyContactPhone: PatientTransformer.transformField(data, 'emergencyContactPhone')
    };
  }

  /**
   * Transform medical information with HIPAA compliance
   */
  private static transformMedicalInfo(data: any): any {
    return {
      bloodType: PatientTransformer.transformField(data, 'bloodType'),
      allergies: data.allergies || [],
      medicalHistory: PatientTransformer.transformField(data, 'medicalHistory'),
      currentMedications: PatientTransformer.transformField(data, 'currentMedications', []),
      diagnosis: PatientTransformer.transformField(data, 'diagnosis')
    };
  }

  /**
   * Transform hospital stay information
   */
  private static transformHospitalStay(data: any): any {
    const roomNumber = data.roomNumber || '';

    return {
      admissionDate: PatientTransformer.transformField(data, 'admissionDate'),
      dischargeDate: PatientTransformer.transformField(data, 'dischargeDate'),
      roomNumber,
      bedNumber: data.bedNumber || '',
      ward: data.ward || (roomNumber ? roomNumber.charAt(0) : 'A'),
      room: data.room || roomNumber || 'Unknown',
      department: data.department || 'General',
      status: data.status,
      dischargeStatus: PatientTransformer.transformField(data, 'dischargeStatus')
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
      assignedNurse: data.assignedNurse || '',
      nurseInCharge: data.nurseInCharge || ''
    };
  }

  /**
   * Transform device information
   */
  private static transformDeviceInfo(data: any): any {
    return {
      assignedDeviceId: PatientTransformer.transformField(data, 'assignedDeviceId'),
      deviceStatus: PatientTransformer.transformField(data, 'deviceStatus', 'disconnected'),
      deviceType: PatientTransformer.transformField(data, 'deviceType'),
      deviceBattery: PatientTransformer.transformField(data, 'deviceBattery', 0)
    };
  }

  // ================================
  // MAIN PATIENT TRANSFORMATION
  // ================================

  /**
   * Transform complete patient data - CAMELCASE ONLY
   * Medical-grade patient data transformation with compliance validation
   */
  static transformPatient(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data) return null;

    try {
      // Validate critical patient data
      if (!PatientTransformer.validateMedicalData(data, ['id'])) {
        console.warn('Patient data missing required fields:', data);
      }

      // Transform each section
      const identity = PatientTransformer.transformPatientIdentity(data);
      const contact = PatientTransformer.transformPatientContact(data);
      const medical = PatientTransformer.transformMedicalInfo(data);
      const hospitalStay = PatientTransformer.transformHospitalStay(data);
      const staffAssignments = PatientTransformer.transformStaffAssignments(data);
      const deviceInfo = PatientTransformer.transformDeviceInfo(data);

      // Handle nested data arrays - no mock alerts
      const vitals = data.vitals || {};
      const alerts: any[] = []; // Empty alerts - no mock data
      const medications = PatientTransformer.transformArray(data.medications || [], PatientTransformer.transformObject, staffMapping);
      const investigations = PatientTransformer.transformArray(data.investigations || [], PatientTransformer.transformObject, staffMapping);
      const therapies = PatientTransformer.transformArray(data.therapies || [], PatientTransformer.transformObject, staffMapping);
      const notes = PatientTransformer.transformArray(data.notes || [], PatientTransformer.transformObject, staffMapping);

      // Combine all transformed data
      let transformedPatient = {
        ...identity,
        ...contact,
        ...medical,
        ...hospitalStay,
        ...staffAssignments,
        ...deviceInfo,
        vitals,
        alerts,
        medications,
        investigations,
        therapies,
        notes,
        createdAt: PatientTransformer.transformField(data, 'createdAt', new Date().toISOString()),
        updatedAt: PatientTransformer.transformField(data, 'updatedAt', new Date().toISOString())
      };

      // Add resolved staff names
      transformedPatient = PatientTransformer.addResolvedNames(transformedPatient, staffMapping);

      // Apply HIPAA-compliant data sanitization
      transformedPatient = PatientTransformer.sanitizeMedicalData(transformedPatient);

      // Add edit permissions based on medical compliance window
      transformedPatient.canEdit = PatientTransformer.canEditMedicalRecord(transformedPatient.createdAt);

      return transformedPatient;
    } catch (error) {
      console.error('Error transforming patient data:', error);
      return data; // Return original data if transformation fails
    }
  }

  /**
   * Transform patient array data
   */
  static transformPatientArray(data: any[], staffMapping?: { [key: string]: string }): any[] {
    if (!Array.isArray(data)) return [];

    return data
      .map(patient => PatientTransformer.transformPatient(patient, staffMapping))
      .filter(patient => patient !== null); // Remove failed transformations
  }

  /**
   * Transform patient summary for dashboard display
   */
  static transformPatientSummary(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data) return null;

    const patient = PatientTransformer.transformPatient(data, staffMapping);
    if (!patient) return null;

    // Return essential fields for dashboard
    return {
      id: patient.id,
      mrn: patient.mrn,
      name: patient.name,
      age: patient.age,
      gender: patient.gender,
      roomNumber: patient.roomNumber,
      bedNumber: patient.bedNumber,
      department: patient.department,
      assignedDoctor: patient.assignedDoctor,
      deviceStatus: patient.deviceStatus,
      status: patient.status,
      vitals: {
        heartRate: patient.vitals?.heartRate || 0,
        systolicPressure: patient.vitals?.systolicPressure || 0,
        diastolicPressure: patient.vitals?.diastolicPressure || 0,
        oxygenSaturation: patient.vitals?.oxygenSaturation || 0
      },
      alerts: [], // No mock alerts
      lastDataReceived: patient.vitals?.lastDataReceived
    };
  }

  /**
   * Transform patient for admission processing
   */
  static transformPatientForAdmission(data: any): any {
    if (!data) return null;

    // Ensure required admission fields
    const requiredFields = ['firstName', 'lastName', 'dateOfBirth', 'gender'];
    if (!PatientTransformer.validateMedicalData(data, requiredFields)) {
      throw new Error('Missing required fields for patient admission');
    }

    const transformed = PatientTransformer.transformPatient(data);

    // Set admission-specific defaults
    transformed.status = 'admitted';
    transformed.admissionDate = transformed.admissionDate || new Date().toISOString();
    transformed.department = transformed.department || 'General';

    return transformed;
  }

  /**
   * Transform aggregated case timeline entries
   * Handles the special format returned by /case-entries endpoint
   */
  static transformCaseTimeline(data: any[], staffMapping?: { [key: string]: string | { name: string; role: string } }): any[] {
    if (!Array.isArray(data)) return [];

    return data.map(entry => {
      if (!entry || typeof entry !== 'object') return entry;

      try {
        // Extract base type from details.entry_type
        const baseType = entry.details?.entry_type || entry.type || 'unknown';

        // Transform type based on content and role
        let type = baseType;
        if (baseType === 'note') {
          // Map note types based on author role
          const authorRole = entry.details?.authorRole?.toLowerCase() || '';
          if (authorRole.includes('doctor') || authorRole.includes('physician')) {
            type = 'doctorNote';
          } else if (authorRole.includes('nurse')) {
            type = 'nurseNote';
          } else if (authorRole.includes('therapist')) {
            type = 'therapistNote';
          } else if (authorRole.includes('pharmacist')) {
            type = 'pharmacistNote';
          } else if (authorRole.includes('technician') || authorRole.includes('tech')) {
            type = 'technicianNote';
          } else {
            type = 'clinicalNote';
          }
        } else if (baseType === 'vitalAlert') {
          // Map alert types based on status
          const alertStatus = entry.details?.status?.toLowerCase() || '';
          if (alertStatus === 'acknowledged') {
            type = 'alertAcknowledged';
          } else if (alertStatus === 'resolved') {
            type = 'alertResolved';
          } else if (alertStatus === 'escalated') {
            type = 'alertEscalated';
          } else {
            type = 'alertTriggered';
          }
        }

        // Extract performedBy ID - prioritize details fields
        const performedBy = entry.details?.performedBy || entry.performedBy || '';

        // Extract staff name from details (prioritize authorName over performedBy)
        let performedByName = entry.details?.authorName ||
                              entry.details?.performedBy ||
                              entry.performedByName ||
                              'Unknown';

        // Use existing timestamp or fall back to details timestamp
        const timestamp = entry.timestamp || entry.details?.timestamp || new Date().toISOString();

        // Resolve staff role if available
        let performedByRole = 'Staff'; // default role
        if (staffMapping && performedBy && staffMapping[performedBy]) {
          const staffInfo = staffMapping[performedBy];
          if (typeof staffInfo === 'object' && staffInfo.role) {
            performedByRole = staffInfo.role;
            console.log('🔍 Staff role mapping:', { performedBy, role: staffInfo.role, name: staffInfo.name });
            // Update performedByName if not already set
            if (!performedByName || performedByName === 'Unknown') {
              performedByName = staffInfo.name;
            }
          }
        }

        // Create transformed entry
        let transformed = {
          ...entry,
          type,
          performedBy,
          performedByName,
          performedByRole, // Add role information
          timestamp,
          canEdit: PatientTransformer.canEditMedicalRecord(timestamp)
        };

        // Apply staff name resolution using BaseTransformer (for backward compatibility)
        transformed = PatientTransformer.addResolvedNames(transformed, staffMapping);

        return transformed;
      } catch (error) {
        console.warn('Error transforming case timeline entry:', error);
        return entry; // Return original if transformation fails
      }
    });
  }
}
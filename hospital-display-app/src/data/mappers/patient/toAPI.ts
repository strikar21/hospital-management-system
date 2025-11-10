/**
 * Map patient domain model to API request format.
 */

import { formatISO } from '@/utils/datetime';
import { PatientDomain } from './fromAPI';

export function mapPatientToAPI(patient: Partial<PatientDomain>): any {
  /**
   * Map domain patient model to API request format.
   *
   * Handles:
   * - Date formatting (Date → ISO strings)
   * - Null/undefined field filtering
   *
   * @param patient - Domain patient model
   * @returns API request payload
   */
  const apiPatient: any = {};

  if (patient.firstName !== undefined) apiPatient.firstName = patient.firstName;
  if (patient.lastName !== undefined) apiPatient.lastName = patient.lastName;
  if (patient.dateOfBirth !== undefined) apiPatient.dateOfBirth = formatISO(patient.dateOfBirth);
  if (patient.gender !== undefined) apiPatient.gender = patient.gender;
  if (patient.contactNumber !== undefined) apiPatient.contactNumber = patient.contactNumber;
  if (patient.emergencyContact !== undefined) apiPatient.emergencyContact = patient.emergencyContact;
  if (patient.bloodGroup !== undefined) apiPatient.bloodGroup = patient.bloodGroup;
  if (patient.roomNumber !== undefined) apiPatient.roomNumber = patient.roomNumber;
  if (patient.bedNumber !== undefined) apiPatient.bedNumber = patient.bedNumber;
  if (patient.diagnosis !== undefined) apiPatient.diagnosis = patient.diagnosis;
  if (patient.status !== undefined) apiPatient.status = patient.status;

  return apiPatient;
}

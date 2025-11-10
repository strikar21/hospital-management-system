/**
 * Map patient data from API response to domain model.
 */

import { parseISO } from '@/utils/datetime';

export interface PatientDomain {
  id: string;
  firstName: string;
  lastName: string;
  dateOfBirth: Date;
  gender: string;
  contactNumber?: string;
  emergencyContact?: string;
  bloodGroup?: string;
  admissionDate: Date;
  roomNumber?: string;
  bedNumber?: string;
  diagnosis?: string;
  status: string;
  createdAt: Date;
  updatedAt: Date;
}

export function mapPatientFromAPI(apiPatient: any): PatientDomain {
  /**
   * Map API patient response to domain model.
   *
   * Handles:
   * - Date parsing (ISO strings → Date objects)
   * - Null/undefined field handling
   *
   * @param apiPatient - Patient data from API
   * @returns Domain patient model
   */
  return {
    id: apiPatient.id,
    firstName: apiPatient.firstName,
    lastName: apiPatient.lastName,
    dateOfBirth: parseISO(apiPatient.dateOfBirth),
    gender: apiPatient.gender,
    contactNumber: apiPatient.contactNumber,
    emergencyContact: apiPatient.emergencyContact,
    bloodGroup: apiPatient.bloodGroup,
    admissionDate: parseISO(apiPatient.admissionDate),
    roomNumber: apiPatient.roomNumber,
    bedNumber: apiPatient.bedNumber,
    diagnosis: apiPatient.diagnosis,
    status: apiPatient.status,
    createdAt: parseISO(apiPatient.createdAt),
    updatedAt: parseISO(apiPatient.updatedAt)
  };
}

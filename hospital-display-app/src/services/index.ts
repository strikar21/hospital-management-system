// services/index.ts - Centralized service exports
import { AuthService } from './AuthService';
import { PatientService } from './patient';
import { VitalService } from './VitalService';
import { MedicationService } from './MedicationService';
import { DeviceService } from './DeviceService';
import { InvestigationService } from './InvestigationService';
import { TherapyService } from './TherapyService';
import { NotesService } from './NotesService';
import { CaseSheetService } from './CaseSheetService';
import { AlertService } from './AlertService';
// Removed unused services: ClinicalDecisionSupport, LabIntegration, ImagingService
import { BaseService } from './BaseService';
import { BaseMedicalRecordService } from './base/BaseMedicalRecordService';

export { BaseService } from './BaseService';
export { BaseMedicalRecordService } from './base/BaseMedicalRecordService';
export { AuthService } from './AuthService';
export { PatientService } from './patient';
export { VitalService } from './VitalService';
export { MedicationService } from './MedicationService';
export { DeviceService } from './DeviceService';
export { InvestigationService } from './InvestigationService';
export { TherapyService } from './TherapyService';
export { NotesService } from './NotesService';
export { CaseSheetService } from './CaseSheetService';
export { AlertService } from './AlertService';
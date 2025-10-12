/**
 * PatientCaseService - DEPRECATED: Backward compatibility wrapper
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 *
 * @deprecated Use CaseSheetService and AlertService instead
 *
 * This service is maintained for backward compatibility only.
 * New code should use the standardized services:
 * - CaseSheetService for case entries (extends BaseMedicalRecordService)
 * - AlertService for alert operations
 *
 * Migration Guide:
 * - Old: PatientCaseService.getCaseEntries()
 *   New: CaseSheetService.getCaseEntries()
 *
 * - Old: PatientCaseService.addCaseEntry()
 *   New: CaseSheetService.addCaseEntry()
 *
 * - Old: PatientCaseService.acknowledgeAlert()
 *   New: AlertService.acknowledgeAlert()
 *
 * @module PatientCaseService
 * @since Legacy (pre-Phase 6)
 */

import { CaseSheetService } from '../CaseSheetService';
import { AlertService } from '../AlertService';
import { caseSheetEntry } from '../../types/PatientTypes';

/**
 * PatientCaseService - Backward compatibility wrapper
 *
 * This class wraps the new standardized services (CaseSheetService and AlertService)
 * to maintain backward compatibility with existing code.
 *
 * @deprecated Use CaseSheetService and AlertService instead
 */
export class PatientCaseService {

  /**
   * Retrieves all case entries for a patient with staff data
   *
   * @deprecated Use CaseSheetService.getCaseEntries() instead
   *
   * @param patientId - Patient ID
   * @returns Promise resolving to array of case entries with staff names resolved
   */
  static async getCaseEntries(patientId: string): Promise<caseSheetEntry[]> {
    return CaseSheetService.getCaseEntries(patientId);
  }

  /**
   * Adds a new case entry to a patient's medical record
   *
   * @deprecated Use CaseSheetService.addCaseEntry() instead
   *
   * @param patientId - Patient ID
   * @param entryData - Case entry data
   * @param userId - User ID creating the entry
   * @returns Promise resolving to created entry or null
   */
  static async addCaseEntry(
    patientId: string,
    entryData: {
      entryType: string;
      description: string;
      performedBy?: string;
      findings?: string;
      recommendations?: string;
      followUpDate?: string;
      severity?: string;
      category?: string;
    },
    userId: string
  ): Promise<any> {
    return CaseSheetService.addCaseEntry(patientId, entryData, userId);
  }

  /**
   * Acknowledges a patient alert
   *
   * @deprecated Use AlertService.acknowledgeAlert() instead
   *
   * @param patientId - Patient ID
   * @param alertId - Alert ID
   * @param userId - User ID acknowledging the alert
   * @returns Promise resolving to true if acknowledged successfully
   */
  static async acknowledgeAlert(
    patientId: string,
    alertId: string,
    userId: string
  ): Promise<boolean> {
    return AlertService.acknowledgeAlert(patientId, alertId, userId);
  }
}

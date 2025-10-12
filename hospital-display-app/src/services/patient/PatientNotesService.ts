/**
 * PatientNotesService - DEPRECATED - Use NotesService instead
 *
 * @deprecated This service is deprecated. Use NotesService from '../services' instead.
 * This file exists for backward compatibility only.
 *
 * Phase 5 Refactoring: NotesService now extends BaseMedicalRecordService
 * and is located at services/NotesService.ts for consistency with other
 * medical record services (MedicationService, InvestigationService, TherapyService).
 *
 * Migration Guide:
 * - Old: import { PatientNotesService } from '../services/patient/PatientNotesService';
 * - New: import { NotesService } from '../services/NotesService';
 *
 * All methods remain the same:
 * - NotesService.getNotes(patientId)
 * - NotesService.addNoteComment(patientId, content, userId, username)
 * - NotesService.editNoteComment(patientId, noteId, newContent, userId)
 * - NotesService.deleteNoteComment(patientId, noteId, userId)
 * - NotesService.canEditNote(note, userId)
 */

import { NotesService } from '../NotesService';

/**
 * @deprecated Use NotesService instead
 * Re-export for backward compatibility
 */
export const PatientNotesService = NotesService;

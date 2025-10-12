/**
 * NotesService - Patient notes and comments management (V2 - Refactored)
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data
 *
 * Phase 5 Refactoring: Extends BaseMedicalRecordService for generic CRUD operations.
 * Adds notes-specific operations: edit, delete, time-based permissions.
 *
 * @module NotesService
 * @since 2.0.0
 */

import { noteComment } from '../types';
import { BaseMedicalRecordService, MedicalRecordConfig } from './base/BaseMedicalRecordService';

export class NotesService extends BaseMedicalRecordService<noteComment> {

  // ================================
  // CONFIGURATION
  // ================================

  protected getConfig(): MedicalRecordConfig {
    return {
      recordType: 'notes',
      recordTypeSingular: 'note',
      recordTypePlural: 'notes'
    };
  }

  // ================================
  // NOTES-SPECIFIC OPERATIONS (Not in base class)
  // ================================

  /**
   * Edit an existing note/comment
   * UNIQUE TO NOTES: Other medical records don't have edit operation
   *
   * @param patientId - Patient ID
   * @param noteId - Note ID to edit
   * @param newContent - Updated content
   * @param userId - User ID performing edit
   * @returns Promise resolving to success boolean
   *
   * @example
   * ```typescript
   * const success = await NotesService.editNoteComment('P123', 'N456', 'Updated note', 'U789');
   * ```
   */
  static async editNoteComment(
    patientId: string,
    noteId: string,
    newContent: string,
    userId: string
  ): Promise<boolean> {
    try {
      await new NotesService().fetchFromBackend(`/patients/${patientId}/notes/${noteId}`, {
        method: 'PUT',
        body: JSON.stringify({
          content: newContent,
          editedBy: userId,
          editedAt: new Date().toISOString()
        })
      });
      return true;
    } catch (error) {
      console.error('Error editing note:', error);
      return false;
    }
  }

  /**
   * Delete a note/comment
   * UNIQUE TO NOTES: Other medical records don't have delete operation
   *
   * @param patientId - Patient ID
   * @param noteId - Note ID to delete
   * @param userId - User ID performing deletion
   * @returns Promise resolving to success boolean
   *
   * @example
   * ```typescript
   * const success = await NotesService.deleteNoteComment('P123', 'N456', 'U789');
   * ```
   */
  static async deleteNoteComment(
    patientId: string,
    noteId: string,
    userId: string
  ): Promise<boolean> {
    try {
      await new NotesService().fetchFromBackend(`/patients/${patientId}/notes/${noteId}`, {
        method: 'DELETE',
        headers: {
          'X-Deleted-By': userId
        }
      });
      return true;
    } catch (error) {
      console.error('Error deleting note:', error);
      return false;
    }
  }

  /**
   * Check if user can edit a note (authorship + time constraints)
   * UNIQUE TO NOTES: Time-based edit window (24 hours)
   *
   * @param note - Note to check
   * @param userId - User ID
   * @returns True if user can edit
   *
   * @example
   * ```typescript
   * const canEdit = NotesService.canEditNote(note, currentUser.id);
   * if (canEdit) {
   *   // Show edit button
   * }
   * ```
   */
  static canEditNote(note: noteComment, userId: string): boolean {
    return note.authorId === userId && this.canEditItem(note.timestamp);
  }

  /**
   * Check if item can be edited based on timestamp (time-based permission)
   * PUBLIC WRAPPER for protected BaseService.canEditItem()
   * For backward compatibility with PatientService wrapper
   *
   * Note: Duplicates logic from BaseService.canEditItem() to provide public access
   * Medical compliance: 2-hour edit window for audit trail integrity
   *
   * @param timestamp - ISO timestamp to check
   * @returns True if within edit window (2 hours)
   *
   * @example
   * ```typescript
   * const canEdit = NotesService.canEditItem('2025-10-12T10:00:00Z');
   * ```
   */
  static canEditItem(timestamp: string): boolean {
    try {
      if (!timestamp) {
        return false;
      }

      const itemTime = new Date(timestamp);
      const now = new Date();
      const timeDiff = now.getTime() - itemTime.getTime();
      const maxEditWindow = 2 * 60 * 60 * 1000; // 2 hours in milliseconds - MEDICAL COMPLIANCE

      return timeDiff <= maxEditWindow;
    } catch (error) {
      return false;
    }
  }

  // ================================
  // STATIC WRAPPER METHODS (Backward Compatibility)
  // ================================

  /**
   * Get all notes for a patient
   * Delegates to base class getPatientRecords()
   *
   * @param patientId - Patient ID
   * @returns Promise resolving to array of notes
   *
   * @example
   * ```typescript
   * const notes = await NotesService.getNotes('P123');
   * ```
   */
  static async getNotes(patientId: string): Promise<noteComment[]> {
    const instance = new NotesService();
    return instance.getPatientRecords(patientId);
  }

  /**
   * Add note comment using atomic operation
   * Creates note and case entry in single transaction
   *
   * @param patientId - Patient ID
   * @param content - Note content
   * @param userId - User ID
   * @param username - Optional user display name
   * @param userrole - Optional user role (unused, for API compatibility)
   * @returns Promise resolving to atomic response {success, medical_record, case_entry}
   *
   * @example
   * ```typescript
   * const result = await NotesService.addNoteComment('P123', 'Clinical note', 'U456', 'Dr. Smith');
   * if (result.success) {
   *   console.log('Note created:', result.medical_record);
   *   console.log('Case entry created:', result.case_entry);
   * }
   * ```
   */
  static async addNoteComment(
    patientId: string,
    content: string,
    userId: string,
    username?: string,
    userrole?: string
  ): Promise<any> {
    const instance = new NotesService();
    return instance.addRecord(patientId, { content, authorName: username }, userId);
  }

  /**
   * Transform payload for note creation
   * Override from base class for notes-specific field mapping
   *
   * @param noteData - Raw note data
   * @param userId - User ID
   * @returns Transformed payload for API
   */
  protected transformAddPayload(noteData: any, userId: string): any {
    return {
      content: noteData.content,
      comment: noteData.content, // Support both field names (backend compatibility)
      authorName: noteData.authorName
    };
  }
}

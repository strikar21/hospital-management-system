/**
 * PatientNotesService - Patient notes and comments management
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade notes management with edit permissions
 */

import { noteComment } from '../../types';
import { BaseService } from '../BaseService';

/**
 * PatientNotesService - Handles patient notes and comments
 *
 * Responsibilities:
 * - Adding new notes/comments
 * - Editing existing notes
 * - Deleting notes
 * - Permission checking for note modifications
 */
export class PatientNotesService extends BaseService {

  /**
   * Adds a new note/comment to a patient's medical record
   *
   * @param patientId - The unique identifier for the patient
   * @param content - The note content/text
   * @param userId - The ID of the user adding the note
   * @param username - Optional display name of the user
   * @param userrole - Optional role of the user (Doctor, Nurse, etc.)
   * @returns Promise resolving to the created note response
   * @throws {Error} When note creation fails
   */
  static async addNoteComment(patientId: string, content: string, userId: string, username?: string, userrole?: string): Promise<any> {
    try {
      const response = await this.fetchFromBackend(`/patients/${patientId}/notes?createdBy=${encodeURIComponent(userId)}`, {
        method: 'POST',
        body: JSON.stringify({
          content,
          authorId: userId,
          authorName: username || 'Unknown',
          authorRole: userrole || 'Staff',
          timestamp: new Date().toISOString()
        })
      });
      return response;
    } catch (error) {
      console.error('❌ Error adding note:', error);
      throw error;
    }
  }

  /**
   * Edits an existing note/comment in a patient's medical record
   *
   * @param patientId - The unique identifier for the patient
   * @param noteId - The unique identifier for the note to edit
   * @param newContent - The updated note content
   * @param userId - The ID of the user editing the note
   * @returns Promise resolving to true if edit was successful
   * @throws {Error} When note editing fails
   */
  static async editNoteComment(patientId: string, noteId: string, newContent: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/notes/${noteId}`, {
        method: 'PUT',
        body: JSON.stringify({
          content: newContent,
          editedBy: userId,
          editedAt: new Date().toISOString()
        })
      });
      return true;
    } catch (error) {
      console.error('❌ Error editing note:', error);
      return false;
    }
  }

  /**
   * Deletes a note/comment from a patient's medical record
   *
   * @param patientId - The unique identifier for the patient
   * @param noteId - The unique identifier for the note to delete
   * @param userId - The ID of the user requesting deletion
   * @returns Promise resolving to true if deletion was successful
   * @throws {Error} When note deletion fails
   */
  static async deleteNoteComment(patientId: string, noteId: string, userId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/patients/${patientId}/notes/${noteId}`, {
        method: 'DELETE',
        headers: {
          'X-Deleted-By': userId
        }
      });
      return true;
    } catch (error) {
      console.error('❌ Error deleting note:', error);
      return false;
    }
  }

  /**
   * Checks if a user can edit a specific note based on authorship and time constraints
   *
   * @param note - The note to check edit permissions for
   * @param userId - The ID of the user requesting edit access
   * @returns True if the user can edit the note, false otherwise
   */
  static canEditNote(note: noteComment, userId: string): boolean {
    return note.authorId === userId && this.canEditItem(note.timestamp);
  }

  /**
   * Checks if an item can be edited based on its timestamp (time-based restrictions)
   *
   * @param timestamp - The creation timestamp of the item
   * @returns True if the item can still be edited, false if too old
   */
  static canEditItem(timestamp: string): boolean {
    return super.canEditItem(timestamp);
  }
}
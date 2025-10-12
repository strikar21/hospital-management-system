// services/StaffService.ts - Staff management service
// STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
import { BaseService } from './BaseService';

export class StaffService extends BaseService {

  /**
   * Get all staff members
   * @returns Array of staff members
   */
  static async getAllStaff(): Promise<any[]> {
    try {
      const response = await this.fetchFromBackend('/staff/all');
      return response?.staff || response || [];
    } catch (error) {
      console.error('Error fetching staff:', error);
      return [];
    }
  }

  /**
   * Add new staff member
   * @param staffData - Staff member data (name, role, department, etc.)
   * @returns Created staff member with auto-generated credentials
   */
  static async addStaff(staffData: any): Promise<any> {
    try {
      const response = await this.fetchFromBackend('/staff', {
        method: 'POST',
        body: JSON.stringify(staffData)
      });
      return response;
    } catch (error) {
      console.error('Error adding staff:', error);
      throw error;
    }
  }

  /**
   * Update staff member details
   * @param staffId - Staff ID to update
   * @param updateData - Updated staff data
   * @returns Updated staff member
   */
  static async updateStaff(staffId: string, updateData: any): Promise<any> {
    try {
      const response = await this.fetchFromBackend(`/staff/${staffId}`, {
        method: 'PUT',
        body: JSON.stringify(updateData)
      });
      return response;
    } catch (error) {
      console.error('Error updating staff:', error);
      throw error;
    }
  }

  /**
   * Delete staff member
   * @param staffId - Staff ID to delete
   * @returns Success status
   */
  static async deleteStaff(staffId: string): Promise<boolean> {
    try {
      await this.fetchFromBackend(`/staff/${staffId}`, {
        method: 'DELETE'
      });
      return true;
    } catch (error) {
      console.error('Error deleting staff:', error);
      throw error;
    }
  }

  /**
   * Get available staff roles
   * @returns Array of role names
   */
  static async getRoles(): Promise<string[]> {
    try {
      const response = await this.fetchFromBackend('/staff/roles');
      return response?.roles || response || [];
    } catch (error) {
      console.error('Error fetching roles:', error);
      return [];
    }
  }

  /**
   * Get available departments
   * @returns Array of department names
   */
  static async getDepartments(): Promise<string[]> {
    try {
      const response = await this.fetchFromBackend('/staff/departments');
      return response?.departments || response || [];
    } catch (error) {
      console.error('Error fetching departments:', error);
      return [];
    }
  }

  /**
   * Change staff password (for password-based auth roles)
   * @param staffId - Staff ID
   * @param currentPassword - Current password for verification
   * @param newPassword - New password
   */
  static async changePassword(
    staffId: string,
    currentPassword: string,
    newPassword: string
  ): Promise<void> {
    try {
      await this.fetchFromBackend(`/staff/${staffId}/change-password`, {
        method: 'PUT',
        body: JSON.stringify({
          currentPassword: currentPassword,
          newPassword: newPassword
        })
      });
    } catch (error) {
      console.error('Error changing password:', error);
      throw error;
    }
  }

  /**
   * Change staff PIN (for PIN-based auth roles)
   * @param staffId - Staff ID
   * @param currentPIN - Current PIN for verification
   * @param newPIN - New PIN (4-6 digits)
   */
  static async changePIN(
    staffId: string,
    currentPIN: string,
    newPIN: string
  ): Promise<void> {
    try {
      await this.fetchFromBackend(`/staff/${staffId}/change-pin`, {
        method: 'PUT',
        body: JSON.stringify({
          currentPin: currentPIN,
          newPin: newPIN
        })
      });
    } catch (error) {
      console.error('Error changing PIN:', error);
      throw error;
    }
  }
}

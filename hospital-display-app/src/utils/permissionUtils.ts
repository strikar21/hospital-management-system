// permissionUtils.ts - Role-based permissions and access control

/**
 * Medical role-based access control utilities
 */
export class PermissionUtils {

  /**
   * Check if user role can view medications
   */
  static canViewMedications(role: string): boolean {
    const allowedRoles = ['Doctor', 'Nurse', 'Administrator', 'Pharmacist'];
    return allowedRoles.includes(role);
  }

  /**
   * Check if user role can edit medications
   */
  static canEditMedications(role: string): boolean {
    const allowedRoles = ['Doctor', 'Nurse', 'Administrator'];
    return allowedRoles.includes(role);
  }

  /**
   * Check if user role can view patient notes
   */
  static canViewNotes(role: string): boolean {
    const allowedRoles = ['Doctor', 'Nurse', 'Administrator', 'Technician'];
    return allowedRoles.includes(role);
  }

  /**
   * Check if user role can edit patient notes
   */
  static canEditNotes(role: string): boolean {
    const allowedRoles = ['Doctor', 'Nurse', 'Administrator'];
    return allowedRoles.includes(role);
  }

  /**
   * Check if user is nurse or technician (for room proximity)
   */
  static isNurseOrTechnician(role: string): boolean {
    return role === 'Nurse' || role === 'Technician' || role === 'Provisioner';
  }

  /**
   * Check if user can discharge patients
   */
  static canDischargePatients(role: string): boolean {
    const allowedRoles = ['Doctor', 'Administrator'];
    return allowedRoles.includes(role);
  }

  /**
   * Check if user can manage devices
   */
  static canManageDevices(role: string): boolean {
    const allowedRoles = ['Administrator', 'Technician', 'Provisioner'];
    return allowedRoles.includes(role);
  }

  /**
   * Check if user can manage staff
   */
  static canManageStaff(role: string): boolean {
    return role === 'Administrator' || role === 'Provisioner';
  }

  /**
   * Check if user can manage NFC devices
   */
  static canManageNFC(role: string): boolean {
    const allowedRoles = ['Administrator', 'Provisioner'];
    return allowedRoles.includes(role);
  }

  /**
   * Check if user can assign devices to patients
   */
  static canAssignDevices(role: string): boolean {
    const allowedRoles = ['Doctor', 'Nurse', 'Technician', 'Provisioner', 'Administrator'];
    return allowedRoles.includes(role);
  }

  /**
   * Check if user can access system settings
   */
  static canAccessSettings(role: string): boolean {
    const allowedRoles = ['Administrator', 'Doctor', 'Nurse'];
    return allowedRoles.includes(role);
  }

  /**
   * Get allowed wards for user role
   */
  static getAllowedWards(role: string, department?: string): string[] {
    switch (role) {
      case 'Administrator':
        return ['All', 'ICU', 'General', 'Emergency', 'Cardiology', 'Pediatrics', 'Surgery'];
      case 'Doctor':
        return department ? [department] : ['ICU', 'General', 'Emergency', 'Cardiology'];
      case 'Nurse':
      case 'Technician':
        return department ? [department] : ['General'];
      default:
        return [];
    }
  }

  /**
   * Check if user can view all departments
   */
  static canViewAllDepartments(role: string): boolean {
    return role === 'Administrator' || role === 'Doctor';
  }
}

export default PermissionUtils;
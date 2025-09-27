// AuthService.ts - Authentication and user management
import { user } from '../types';
import { BaseService } from './BaseService';
import SecureStorage from '../utils/secureStorage';

export class AuthService extends BaseService {

  // ================================
  // INPUT SANITIZATION FOR MEDICAL SECURITY
  // ================================

  /**
   * Sanitize input to prevent injection attacks in medical systems
   */
  private static sanitizeInput(input: string): string {
    if (!input || typeof input !== 'string') return '';

    // Remove dangerous characters while allowing alphanumeric, dash, underscore
    return input
      .trim()
      .replace(/[<>'";&|`${}()[\]]/g, '') // Remove injection characters
      .replace(/\s+/g, '') // Remove all whitespace for staff IDs
      .substring(0, 50); // Limit length
  }

  /**
   * Validate staff ID format for medical compliance
   */
  private static validateStaffId(staffId: string): boolean {
    // Medical staff ID should be alphanumeric with possible dash/underscore
    const staffIdRegex = /^[A-Za-z0-9_-]{3,20}$/;
    return staffIdRegex.test(staffId);
  }

  // ================================
  // AUTHENTICATION METHODS
  // ================================

  static async authenticateNFC(nfcId: string): Promise<user | null> {
    try {
      // Sanitize and validate NFC ID for medical security
      const sanitizedNfcId = this.sanitizeInput(nfcId);
      if (!sanitizedNfcId || sanitizedNfcId.length < 4) {
        throw new Error('Invalid NFC ID format');
      }

      const response = await this.fetchFromBackend('/auth/nfc', {
        method: 'POST',
        body: JSON.stringify({ nfcId: sanitizedNfcId })
      });

      if (response && response.id) {
        console.log('🏥 NFC authentication successful:', response.name || response.id);
        await SecureStorage.setToken(response.token || 'nfc-auth-token');
        await SecureStorage.setUser(response);
        return response;
      }

      console.warn('⚠️ NFC authentication failed: Invalid response');
      return null;
    } catch (error) {
      console.error('❌ NFC authentication error:', error);
      return null;
    }
  }

  static async authenticateCredentials(staffId: string, password: string, pin?: string): Promise<user | null> {
    try {
      // Input sanitization for medical security
      const sanitizedStaffId = this.sanitizeInput(staffId);
      if (!this.validateStaffId(sanitizedStaffId)) {
        throw new Error('Invalid staff ID format - must be 3-20 alphanumeric characters');
      }

      // Validate PIN format if provided
      if (pin && (!/^\d{4,8}$/.test(pin))) {
        throw new Error('Invalid PIN format - must be 4-8 digits');
      }

      console.log('🔍 Attempting authentication for:', sanitizedStaffId, pin ? '(PIN)' : '(Password)');

      const loginData: any = { staffId: sanitizedStaffId };

      if (pin) {
        loginData.pin = pin;
      }

      if (password) {
        loginData.password = password;
      }

      console.log('📤 Sending login request with data:', {
        ...loginData,
        ...(loginData.pin && { pin: '****' }),
        ...(loginData.password && { password: '****' })
      });

      const response = await this.fetchFromBackend('/auth/login', {
        method: 'POST',
        body: JSON.stringify(loginData)
      });

      // Log response without sensitive data (tokens, passwords, etc.)
      if (process.env.NODE_ENV === 'development') {
        console.log('📥 Login response received:', {
          id: response?.id,
          name: response?.firstName || response?.name,
          role: response?.role,
          success: !!response?.id
        });
      }

      if (response && response.id) {
        console.log('✅ Authentication successful for:', response.firstName, response.lastName);

        // Transform backend response to frontend user format
        const fullName = `${response.firstName || ''} ${response.lastName || ''}`.trim();
        const displayName = response.role === 'Doctor' ? `Dr. ${fullName}` : fullName;

        const user = {
          ...response,
          name: displayName,
          staffId: response.id
        };

        // Store authentication data with medical-grade encryption
        if (response.accessToken) {
          await SecureStorage.setToken(response.accessToken);
        }
        await SecureStorage.setUser(user);
        // Remove HIPAA violation: Don't store sensitive user data in plain localStorage

        return user;
      }

      console.warn('⚠️ Authentication failed: Invalid credentials');
      return null;
    } catch (error) {
      console.error('❌ Authentication error:', error);
      return null;
    }
  }

  static async checkAuthType(staffId: string): Promise<{ requiresPin: boolean, requiresPassword: boolean } | null> {
    try {
      // Sanitize staff ID for security
      const sanitizedStaffId = this.sanitizeInput(staffId);
      if (!this.validateStaffId(sanitizedStaffId)) {
        return null; // Return null for invalid input
      }

      // Production authentication type checking - backend only
      const response = await this.fetchFromBackend(`/auth/check-type?staffId=${encodeURIComponent(sanitizedStaffId)}`);

      if (response) {
        return {
          requiresPin: response.hasPin || false,
          requiresPassword: response.hasPassword || false
        };
      }

      // Fallback for development - assume PIN for doctors, password for others
      if (sanitizedStaffId.startsWith('DOC')) {
        return { requiresPin: true, requiresPassword: false };
      } else {
        return { requiresPin: false, requiresPassword: true };
      }
    } catch (error) {
      console.error('❌ Error checking auth type:', error);
      // Fallback to PIN for safety
      return { requiresPin: true, requiresPassword: false };
    }
  }

  static logout(): void {
    SecureStorage.clearAll();
    localStorage.removeItem('currentUser');
    console.log('🔐 User logged out, secure storage cleared');
  }

  // ================================
  // USER INFORMATION
  // ================================

  static getCurrentUser() {
    return super.getCurrentUser();
  }

  static async isAuthenticated(): Promise<boolean> {
    const token = await SecureStorage.getToken();
    const user = this.getCurrentUser();
    return !!(token && user);
  }

  static getUserRole(): string | null {
    const user = this.getCurrentUser();
    return user?.role || null;
  }

  static getUserId(): string | null {
    const user = this.getCurrentUser();
    return user?.id || null;
  }

  static getUserName(): string | null {
    const user = this.getCurrentUser();
    if (user?.firstName && user?.lastName) {
      return `${user.firstName} ${user.lastName}`;
    }
    return user?.name || null;
  }
}
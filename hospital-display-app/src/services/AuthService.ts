// AuthService.ts - Authentication and user management
import { user } from '../types';
import { BaseService } from './BaseService';
import SecureStorage from '../utils/secureStorage';

export class AuthService extends BaseService {

  // ================================
  // AUTHENTICATION METHODS
  // ================================

  static async authenticateNFC(nfcId: string): Promise<user | null> {
    try {
      const response = await this.fetchFromBackend('/auth/nfc', {
        method: 'POST',
        body: JSON.stringify({ nfcId })
      });

      if (response && response.id) {
        console.log('🏥 NFC authentication successful:', response.name || response.id);
        SecureStorage.setToken(response.token || 'nfc-auth-token');
        SecureStorage.setUser(response);
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
      console.log('🔍 Attempting authentication for:', staffId, pin ? '(PIN)' : '(Password)');

      const loginData: any = { staffId };

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

      console.log('📥 Login response received:', response);

      if (response && response.id) {
        console.log('✅ Authentication successful for:', response.firstName, response.lastName);

        // Store authentication data
        if (response.accessToken) {
          SecureStorage.setToken(response.accessToken);
        }
        SecureStorage.setUser(response);
        localStorage.setItem('currentUser', JSON.stringify(response));

        return response;
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
      // Production authentication type checking - backend only
      const response = await this.fetchFromBackend(`/auth/check-type?staffId=${staffId}`);

      if (response) {
        return {
          requiresPin: response.hasPin || false,
          requiresPassword: response.hasPassword || false
        };
      }

      // Fallback for development - assume PIN for doctors, password for others
      if (staffId.startsWith('DOC')) {
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

  static isAuthenticated(): boolean {
    const token = SecureStorage.getToken();
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
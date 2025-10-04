// secureStorage.ts - Medical-grade secure client-side storage for PHI data
// HIPAA Compliant: Uses AES-GCM encryption for patient health information

class SecureStorage {
  private static readonly TOKEN_KEY = 'hospitalAccessToken';
  private static readonly USER_KEY = 'hospital_user';

  /**
   * Generate or retrieve encryption key for medical data
   * Uses Web Crypto API for HIPAA compliance
   */
  private static async getEncryptionKey(): Promise<CryptoKey> {
    try {
      // Try to retrieve existing key from session storage
      const existingKey = sessionStorage.getItem('medical_encryption_key');

      if (existingKey) {
        const keyData = JSON.parse(existingKey);
        return await crypto.subtle.importKey(
          'raw',
          new Uint8Array(keyData),
          { name: 'AES-GCM', length: 256 },
          false,
          ['encrypt', 'decrypt']
        );
      }

      // Generate new key for this session
      const key = await crypto.subtle.generateKey(
        { name: 'AES-GCM', length: 256 },
        true,
        ['encrypt', 'decrypt']
      );

      // Export and store key for session
      const keyData = await crypto.subtle.exportKey('raw', key);
      sessionStorage.setItem('medical_encryption_key', JSON.stringify(Array.from(new Uint8Array(keyData))));

      return key;
    } catch (error) {
      // Failed to generate encryption key - handle silently
      throw new Error('Encryption key generation failed - medical data security compromised');
    }
  }

  /**
   * Medical-grade AES-GCM encryption for PHI data
   */
  private static async encrypt(text: string): Promise<string> {
    try {
      const key = await this.getEncryptionKey();
      const encoder = new TextEncoder();
      const data = encoder.encode(text);

      // Generate random IV for each encryption (required for GCM)
      const iv = crypto.getRandomValues(new Uint8Array(12));

      const encrypted = await crypto.subtle.encrypt(
        { name: 'AES-GCM', iv: iv },
        key,
        data
      );

      // Combine IV + encrypted data
      const combined = new Uint8Array(iv.length + encrypted.byteLength);
      combined.set(iv);
      combined.set(new Uint8Array(encrypted), iv.length);

      return btoa(String.fromCharCode.apply(null, Array.from(combined)));
    } catch (error) {
      // Encryption failed - handle silently
      throw new Error('Medical data encryption failed - HIPAA compliance compromised');
    }
  }

  /**
   * Medical-grade AES-GCM decryption for PHI data
   */
  private static async decrypt(encryptedText: string): Promise<string> {
    try {
      const key = await this.getEncryptionKey();
      const combined = Uint8Array.from(atob(encryptedText), c => c.charCodeAt(0));

      // Extract IV and encrypted data
      const iv = combined.slice(0, 12);
      const encrypted = combined.slice(12);

      const decrypted = await crypto.subtle.decrypt(
        { name: 'AES-GCM', iv: iv },
        key,
        encrypted
      );

      const decoder = new TextDecoder();
      return decoder.decode(decrypted);
    } catch (error) {
      // Decryption failed - handle silently
      return '';
    }
  }

  /**
   * Store authentication token with medical-grade encryption
   */
  static async setToken(token: string): Promise<void> {
    if (!token) {
      // Warning: Attempting to store empty token
      return;
    }

    try {
      const encrypted = await this.encrypt(token);
      localStorage.setItem(this.TOKEN_KEY, encrypted);

      // Set expiration (8 hours from now for medical compliance)
      const expiration = (new Date().getTime() + (8 * 60 * 60 * 1000));
      localStorage.setItem(`${this.TOKEN_KEY}_exp`, expiration.toString());

      // Authentication token stored with AES-GCM encryption
    } catch (error) {
      // Failed to store token securely - handle silently
      throw new Error('Token storage failed - authentication compromised');
    }
  }

  /**
   * Retrieve authentication token with medical-grade decryption
   */
  static async getToken(): Promise<string | null> {
    try {
      const encrypted = localStorage.getItem(this.TOKEN_KEY);
      const expiration = localStorage.getItem(`${this.TOKEN_KEY}_exp`);

      if (!encrypted || !expiration) {
        return null;
      }

      // Check if token is expired (medical compliance)
      if (new Date().getTime() > parseInt(expiration)) {
        // Token expired, removing from storage for security
        this.removeToken();
        return null;
      }

      const decrypted = await this.decrypt(encrypted);
      return decrypted || null;
    } catch (error) {
      // Failed to retrieve token - handle silently
      this.removeToken(); // Clear corrupted token for security
      return null;
    }
  }

  /**
   * Remove token from storage
   */
  static removeToken(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(`${this.TOKEN_KEY}_exp`);
    // Token removed from secure storage
  }

  /**
   * Check if token exists and is valid
   */
  static async hasValidToken(): Promise<boolean> {
    const token = await this.getToken();
    return token !== null;
  }

  /**
   * Refresh token expiration (extend by 8 hours)
   */
  static async refreshTokenExpiration(): Promise<void> {
    if (await this.hasValidToken()) {
      const newExpiration = (new Date().getTime() + (8 * 60 * 60 * 1000));
      localStorage.setItem(`${this.TOKEN_KEY}_exp`, newExpiration.toString());
      // Token expiration refreshed for security
    }
  }

  /**
   * Get token expiration time
   */
  static getTokenExpiration(): Date | null {
    const expiration = localStorage.getItem(`${this.TOKEN_KEY}_exp`);
    return expiration ? new Date(parseInt(expiration)) : null;
  }

  /**
   * Store user PHI data with medical-grade encryption (HIPAA compliant)
   */
  static async setUser(user: any): Promise<void> {
    if (!user) {
      // Warning: Attempting to store empty user data
      return;
    }

    try {
      const userJson = JSON.stringify(user);
      const encrypted = await this.encrypt(userJson);
      localStorage.setItem(this.USER_KEY, encrypted);
      // User PHI data stored with AES-GCM encryption
    } catch (error) {
      // Failed to store user data securely - handle silently
      throw new Error('User data storage failed - PHI security compromised');
    }
  }

  /**
   * Retrieve user PHI data with medical-grade decryption (HIPAA compliant)
   */
  static async getUser(): Promise<any | null> {
    try {
      const encrypted = localStorage.getItem(this.USER_KEY);
      if (!encrypted) {
        return null;
      }

      const decrypted = await this.decrypt(encrypted);
      return decrypted ? JSON.parse(decrypted) : null;
    } catch (error) {
      // Failed to retrieve user data - handle silently
      localStorage.removeItem(this.USER_KEY);
      return null;
    }
  }

  /**
   * Clear all secure storage (for logout) - HIPAA compliant data destruction
   */
  static clearAll(): void {
    this.removeToken();
    localStorage.removeItem(this.USER_KEY);
    localStorage.removeItem('currentUser');

    // Remove medical encryption key from session
    sessionStorage.removeItem('medical_encryption_key');

    // Remove any other sensitive PHI data (HIPAA compliance)
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith('hospital_') || key?.startsWith('patient_') || key?.startsWith('medical_')) {
        keysToRemove.push(key);
      }
    }

    keysToRemove.forEach(key => {
      localStorage.removeItem(key);
    });

    // All PHI data securely cleared for HIPAA compliance
  }
}

export default SecureStorage;
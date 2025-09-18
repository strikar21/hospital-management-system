// secureStorage.ts - Secure client-side storage for sensitive data
// NOTE: This is client-side security. For true security, use httpOnly cookies from backend

class SecureStorage {
  private static readonly TOKEN_KEY = 'hospitalAccessToken';
  private static readonly ENCRYPTION_KEY = 'hospital_secure_key'; // In production, derive from user session

  /**
   * Simple XOR encryption for client-side token obfuscation
   * NOTE: This is NOT cryptographically secure - use for obfuscation only
   * Real security should come from httpOnly cookies and backend validation
   */
  private static encrypt(text: string): string {
    const key = this.ENCRYPTION_KEY;
    let encrypted = '';
    
    for (let i = 0; i < text.length; i++) {
      const keyChar = key.charCodeAt(i % key.length);
      const textChar = text.charCodeAt(i);
      encrypted += String.fromCharCode(textChar ^ keyChar);
    }
    
    return btoa(encrypted); // Base64 encode
  }

  private static decrypt(encryptedText: string): string {
    try {
      const key = this.ENCRYPTION_KEY;
      const decoded = atob(encryptedText); // Base64 decode
      let decrypted = '';
      
      for (let i = 0; i < decoded.length; i++) {
        const keyChar = key.charCodeAt(i % key.length);
        const encryptedChar = decoded.charCodeAt(i);
        decrypted += String.fromCharCode(encryptedChar ^ keyChar);
      }
      
      return decrypted;
    } catch (error) {
      console.error('Failed to decrypt token:', error);
      return '';
    }
  }

  /**
   * Store token securely (obfuscated)
   */
  static setToken(token: string): void {
    if (!token) {
      console.warn('Attempting to store empty token');
      return;
    }

    try {
      const encrypted = this.encrypt(token);
      localStorage.setItem(this.TOKEN_KEY, encrypted);
      
      // Set expiration (8 hours from now)
      const expiration = Date.now() + (8 * 60 * 60 * 1000);
      localStorage.setItem(`${this.TOKEN_KEY}_exp`, expiration.toString());
      
      console.log('🔐 Token stored securely with expiration');
    } catch (error) {
      console.error('Failed to store token securely:', error);
    }
  }

  /**
   * Retrieve token securely
   */
  static getToken(): string | null {
    try {
      const encrypted = localStorage.getItem(this.TOKEN_KEY);
      const expiration = localStorage.getItem(`${this.TOKEN_KEY}_exp`);
      
      if (!encrypted || !expiration) {
        return null;
      }

      // Check if token is expired
      if (Date.now() > parseInt(expiration)) {
        console.log('🕒 Token expired, removing from storage');
        this.removeToken();
        return null;
      }

      const decrypted = this.decrypt(encrypted);
      return decrypted || null;
    } catch (error) {
      console.error('Failed to retrieve token:', error);
      this.removeToken(); // Clear corrupted token
      return null;
    }
  }

  /**
   * Remove token from storage
   */
  static removeToken(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(`${this.TOKEN_KEY}_exp`);
    console.log('🗑️ Token removed from secure storage');
  }

  /**
   * Check if token exists and is valid
   */
  static hasValidToken(): boolean {
    return this.getToken() !== null;
  }

  /**
   * Refresh token expiration (extend by 8 hours)
   */
  static refreshTokenExpiration(): void {
    if (this.hasValidToken()) {
      const newExpiration = Date.now() + (8 * 60 * 60 * 1000);
      localStorage.setItem(`${this.TOKEN_KEY}_exp`, newExpiration.toString());
      console.log('🔄 Token expiration refreshed');
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
   * Clear all secure storage (for logout)
   */
  static clearAll(): void {
    this.removeToken();
    // Remove any other sensitive data
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
    
    console.log('🧹 All secure storage cleared');
  }
}

export default SecureStorage;
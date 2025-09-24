// clientEncryption.ts - Client-side encryption for sensitive patient data
// NOTE: This provides obfuscation, not cryptographic security. Real security comes from HTTPS and backend encryption.

interface EncryptedData {
  data: string;
  timestamp: number;
  checksum: string;
}

class ClientEncryption {
  private static readonly ENCRYPTION_KEY = 'MEDICAL_DATA_OBFUSCATION_2024';
  
  /**
   * Simple XOR cipher for client-side data obfuscation
   * NOT cryptographically secure - use for local data obfuscation only
   */
  private static xorEncrypt(text: string, key: string): string {
    let result = '';
    for (let i = 0; i < text.length; i++) {
      const textChar = text.charCodeAt(i);
      const keyChar = key.charCodeAt(i % key.length);
      result += String.fromCharCode(textChar ^ keyChar);
    }
    return result;
  }

  /**
   * Generate simple checksum for data integrity
   */
  private static generateChecksum(data: string): string {
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
      const char = data.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash).toString(36);
  }

  /**
   * Encrypt sensitive patient data for localStorage
   */
  static encryptPatientData(patientData: any): string {
    try {
      const jsonString = JSON.stringify(patientData);
      const timestamp = Date.now();
      
      // Add medical data markers for audit purposes
      const dataWithMetadata = {
        ...patientData,
        _encrypted: true,
        _timestamp: timestamp,
        _version: '1.0'
      };
      
      const dataString = JSON.stringify(dataWithMetadata);
      const encrypted = this.xorEncrypt(dataString, this.ENCRYPTION_KEY);
      const checksum = this.generateChecksum(dataString);
      
      const encryptedPayload: EncryptedData = {
        data: btoa(encrypted), // Base64 encode
        timestamp,
        checksum
      };
      
      return JSON.stringify(encryptedPayload);
    } catch (error) {
      console.error('🔒 Failed to encrypt patient data:', error);
      throw new Error('Patient data encryption failed');
    }
  }

  /**
   * Decrypt patient data from localStorage
   */
  static decryptPatientData(encryptedData: string): any {
    try {
      const payload: EncryptedData = JSON.parse(encryptedData);
      
      // Verify data age (max 24 hours for patient data)
      const maxAge = 24 * 60 * 60 * 1000; // 24 hours
      if (Date.now() - payload.timestamp > maxAge) {
        console.warn('🕒 Encrypted patient data expired, removing');
        throw new Error('Encrypted data expired');
      }
      
      const decryptedBase64 = atob(payload.data);
      const decrypted = this.xorEncrypt(decryptedBase64, this.ENCRYPTION_KEY);
      
      // Verify checksum
      const expectedChecksum = this.generateChecksum(decrypted);
      if (expectedChecksum !== payload.checksum) {
        console.error('🔒 Patient data checksum mismatch - possible corruption');
        throw new Error('Data integrity check failed');
      }
      
      const parsedData = JSON.parse(decrypted);
      
      // Remove metadata before returning
      delete parsedData._encrypted;
      delete parsedData._timestamp;
      delete parsedData._version;
      
      return parsedData;
    } catch (error) {
      console.error('🔒 Failed to decrypt patient data:', error);
      throw new Error('Patient data decryption failed');
    }
  }

  /**
   * Securely store patient data in localStorage with encryption
   */
  static storePatientData(patientId: string, patientData: any): void {
    try {
      // Add patient safety metadata
      const dataWithSafety = {
        ...patientData,
        lastaccessed: new Date().toISOString(),
        accessedBy: 'frontend_app',
        medicalDataType: 'patient_record'
      };
      
      const encrypted = this.encryptPatientData(dataWithSafety);
      const storageKey = `medical_patient_${patientId}`;
      
      localStorage.setItem(storageKey, encrypted);
      
      // Store access log
      const accessLog = {
        patientId,
        action: 'store',
        timestamp: new Date().toISOString(),
        dataSize: encrypted.length
      };
      
      localStorage.setItem(`medical_access_${patientId}_${Date.now()}`, JSON.stringify(accessLog));
      
      console.log(`🔒 Patient data encrypted and stored securely: ${patientId}`);
    } catch (error) {
      console.error('🔒 Failed to store encrypted patient data:', error);
      throw error;
    }
  }

  /**
   * Retrieve and decrypt patient data from localStorage
   */
  static retrievePatientData(patientId: string): any {
    try {
      const storageKey = `medical_patient_${patientId}`;
      const encryptedData = localStorage.getItem(storageKey);
      
      if (!encryptedData) {
        return null;
      }
      
      const decryptedData = this.decryptPatientData(encryptedData);
      
      // Log access for audit trail
      const accessLog = {
        patientId,
        action: 'retrieve',
        timestamp: new Date().toISOString()
      };
      
      localStorage.setItem(`medical_access_${patientId}_${Date.now()}`, JSON.stringify(accessLog));
      
      console.log(`🔒 Patient data retrieved and decrypted: ${patientId}`);
      return decryptedData;
    } catch (error) {
      console.error('🔒 Failed to retrieve encrypted patient data:', error);
      // Remove corrupted data
      this.removePatientData(patientId);
      return null;
    }
  }

  /**
   * Remove encrypted patient data
   */
  static removePatientData(patientId: string): void {
    const storageKey = `medical_patient_${patientId}`;
    localStorage.removeItem(storageKey);
    
    // Clean up old access logs for this patient
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(`medical_access_${patientId}_`)) {
        keysToRemove.push(key);
      }
    }
    
    keysToRemove.forEach(key => {
      localStorage.removeItem(key);
    });
    
    console.log(`🗑️ Encrypted patient data removed: ${patientId}`);
  }

  /**
   * Encrypt vital signs data for temporary storage
   */
  static encryptVitalSigns(vitals: any): string {
    const vitalsWithMetadata = {
      ...vitals,
      medicalDataType: 'vital_signs',
      encryptedAt: new Date().toISOString()
    };
    
    return this.encryptPatientData(vitalsWithMetadata);
  }

  /**
   * Clean up expired medical data (call periodically)
   */
  static cleanupExpiredData(): void {
    const keysToRemove = [];
    
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith('medical_')) {
        try {
          const data = localStorage.getItem(key);
          if (data) {
            const parsed: EncryptedData = JSON.parse(data);
            const maxAge = 24 * 60 * 60 * 1000; // 24 hours
            
            if (Date.now() - parsed.timestamp > maxAge) {
              keysToRemove.push(key);
            }
          }
        } catch (error) {
          // Remove corrupted data
          keysToRemove.push(key);
        }
      }
    }
    
    keysToRemove.forEach(key => {
      localStorage.removeItem(key);
    });
    
    if (keysToRemove.length > 0) {
      console.log(`🧹 Cleaned up ${keysToRemove.length} expired medical data entries`);
    }
  }

  /**
   * Get storage statistics for medical data
   */
  static getStorageStats(): { count: number; totalSize: number; oldestTimestamp: number | null } {
    let count = 0;
    let totalSize = 0;
    let oldestTimestamp: number | null = null;
    
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith('medical_patient_')) {
        const data = localStorage.getItem(key);
        if (data) {
          count++;
          totalSize += data.length;
          
          try {
            const parsed: EncryptedData = JSON.parse(data);
            if (!oldestTimestamp || parsed.timestamp < oldestTimestamp) {
              oldestTimestamp = parsed.timestamp;
            }
          } catch (error) {
            // Corrupted data
          }
        }
      }
    }
    
    return { count, totalSize, oldestTimestamp };
  }
}

export default ClientEncryption;
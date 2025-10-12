// BaseService.ts - Shared functionality for all services
import SecureStorage from '../utils/secureStorage';
import { API_CONFIG, getApiUrl, getWsUrl } from '../config/apiConfig';

export abstract class BaseService {
  protected static readonly BACKEND_BASE_URL = API_CONFIG.BACKEND_BASE_URL;

  // ================================
  // REQUEST SIGNING FOR SECURITY
  // ================================

  private static async generateSignature(
    method: string,
    urlpath: string,
    body: string,
    timestamp: string,
    secretkey: string
  ): Promise<string> {
    const canonicalString = `${method}\n${urlpath}\n${body}\n${timestamp}`;
    const encoder = new TextEncoder();
    const keydata = encoder.encode(secretkey);
    const messagedata = encoder.encode(canonicalString);

    const cryptokey = await crypto.subtle.importKey(
      'raw',
      keydata,
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );

    const signature = await crypto.subtle.sign('HMAC', cryptokey, messagedata);
    const signaturearray = new Uint8Array(signature);
    return btoa(String.fromCharCode.apply(null, Array.from(signaturearray)));
  }

  private static async addRequestSigning(
    url: string,
    options: RequestInit
  ): Promise<RequestInit> {
    let urlpath: string;

    try {
      // Handle both absolute and relative URLs
      if (url.startsWith('http')) {
        const urlobj = new URL(url);
        urlpath = urlobj.pathname + urlobj.search;
      } else {
        // For relative URLs, use the path directly
        urlpath = url;
      }
    } catch (error) {
      // Fallback: treat as relative path
      urlpath = url;
    }

    const method = options.method || 'GET';
    const body = options.body as string || '';
    // Timestamp for request authentication - not for medical record IDs
    const timestamp = Math.floor(new Date().getTime() / 1000).toString();

    // Use environment variable for secret key - fallback for development only
    const secretkey = process.env.REACT_APP_HOSPITAL_SECRET_KEY ||
      (process.env.NODE_ENV === 'development' ? 'dev-key-only-not-for-production' : '');

    if (!secretkey && process.env.NODE_ENV === 'production') {
      // CRITICAL: No secret key configured for production
      throw new Error('Authentication secret key not configured');
    }

    const signature = await this.generateSignature(
      method,
      urlpath,
      body,
      timestamp,
      secretkey
    );

    return {
      ...options,
      headers: {
        ...(options.headers as Record<string, string> || {}),
        'X-Signature': signature,
        'X-Timestamp': timestamp
      }
    };
  }

  // ================================
  // SHARED BACKEND INTEGRATION
  // ================================

  protected static async fetchFromBackend(endpoint: string, options: RequestInit = {}): Promise<any> {
    const url = getApiUrl(endpoint);
    const token = await SecureStorage.getToken();  // FIXED: Added await to get actual token string

    try {
      const signedOptions = await this.addRequestSigning(url, {
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': `Bearer ${token}` }),
          ...(options.headers || {})
        },
        ...options
      });

      const response = await fetch(url, signedOptions);

      if (!response.ok) {
        const errorText = await response.text();
        // API Error occurred
        throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
      }

      const data = await response.json();

      // Return data directly - transformation removed per user request
      return data;
    } catch (error) {
      // Network error occurred
      throw error;
    }
  }

  protected static async createWebSocketConnection(endpoint: string): Promise<WebSocket | null> {
    try {
      // FIXED: Get token from SecureStorage for WebSocket authentication
      const token = await SecureStorage.getToken();
      if (!token) {
        console.error('Cannot create WebSocket: No auth token available');
        return null;
      }

      // Add token as query parameter
      const wsUrl = `${getWsUrl(endpoint)}?token=${encodeURIComponent(token)}`;
      return new WebSocket(wsUrl);
    } catch (error) {
      // WebSocket connection failed
      console.error('WebSocket connection error:', error);
      return null;
    }
  }

  // ================================
  // UTILITY METHODS
  // ================================

  protected static canEditItem(timestamp: string): boolean {
    try {
      if (!timestamp) {
        // No timestamp provided for edit permission check
        return false;
      }

      const itemTime = new Date(timestamp);
      const now = new Date();
      const timeDiff = now.getTime() - itemTime.getTime();
      const maxEditWindow = 2 * 60 * 60 * 1000; // 2 hours in milliseconds - MEDICAL COMPLIANCE

      const canEdit = timeDiff <= maxEditWindow;
      // Edit permission check completed

      return canEdit;
    } catch (error) {
      // Error checking edit permission
      return false;
    }
  }

  protected static async getCurrentUser() {
    try {
      const user = await SecureStorage.getUser();
      if (!user) {
        // No current user found in SecureStorage
        return null;
      }
      return user;
    } catch (error) {
      // Error getting current user from SecureStorage
      return null;
    }
  }

  /**
   * Get staff ID to name mapping for transformation
   */
  protected static async getStaffMapping(): Promise<{ [key: string]: string }> {
    try {
      const response = await this.fetchFromBackend('/staff/mapping');
      return response || {};
    } catch (error) {
      // Staff mapping unavailable
      return {};
    }
  }

  /**
   * Get comprehensive staff information including roles
   * For role-based note categorization
   */
  protected static async getStaffWithRoles(): Promise<{ [key: string]: { name: string; role: string } }> {
    try {
      const response = await this.fetchFromBackend('/staff/');
      // Staff endpoint response received
      if (!Array.isArray(response)) return {};

      // Convert staff array to ID -> {name, role} mapping
      const staffMapping: { [key: string]: { name: string; role: string } } = {};
      response.forEach((staff: any) => {
        // Processing individual staff object
        // Try multiple possible ID field names
        const staffId = staff.staffId || staff.id || staff.userId || staff.staff_id;
        if (staffId) {
          const fullName = staff.name || staff.staffName || staff.fullName ||
                          (staff.firstName && staff.lastName ? `${staff.firstName} ${staff.lastName}` : null) ||
                          staff.firstName || staff.lastName || 'Unknown';
          staffMapping[staffId] = {
            name: fullName,
            role: staff.role || staff.staffRole || 'Staff'
          };
          // Staff mapping added
        }
      });
      // Final staff mapping completed
      return staffMapping;
    } catch (error) {
      // Staff with roles unavailable
      return {};
    }
  }
}
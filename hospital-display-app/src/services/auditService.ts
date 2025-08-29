/**
 * Frontend Audit Service
 * Handles logging user actions and frontend events to backend audit system
 */

// For development with proxy, use empty string to make relative URLs
// For production mobile app, this will be set to the actual backend URL  
const BACKEND_BASE_URL = process.env.NODE_ENV === 'development' ? '' : (process.env.REACT_APP_BACKEND_URL || 'https://localhost:8002');

interface AuditLogData {
  eventType: string;
  eventCategory: string;
  action: string;
  description: string;
  severity?: 'info' | 'warning' | 'error' | 'critical';
  patientId?: string;
  additionalContext?: Record<string, any>;
}

interface UserActionData {
  action: string;
  description: string;
  patientId?: string;
  additionalContext?: Record<string, any>;
  severity?: 'info' | 'warning' | 'error' | 'critical';
}

class AuditService {
  private static instance: AuditService;
  private userId: string | null = null;
  private sessionId: string;
  
  constructor() {
    // Generate a unique session ID for this browser session
    this.sessionId = this.generateSessionId();
    
    // Get user ID from localStorage if available
    const user = localStorage.getItem('user');
    if (user) {
      try {
        const userData = JSON.parse(user);
        this.userId = userData.id;
      } catch (e) {
        console.warn('Failed to parse user data from localStorage');
      }
    }
    
    // Log session start
    this.logUserAction({
      action: 'sessionStart',
      description: 'User started new browser session',
      severity: 'info',
      additionalContext: {
        userAgent: navigator.userAgent,
        screenResolution: `${window.screen.width}x${window.screen.height}`,
        timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        language: navigator.language
      }
    });
    
    // Log page visibility changes
    document.addEventListener('visibilitychange', () => {
      this.logUserAction({
        action: document.hidden ? 'pageHidden' : 'pageVisible',
        description: `User ${document.hidden ? 'minimized or switched away from' : 'returned to'} the application`,
        severity: 'info'
      });
    });
    
    // Log unload events
    window.addEventListener('beforeunload', () => {
      this.logUserAction({
        action: 'sessionEnd',
        description: 'User ended browser session',
        severity: 'info'
      });
    });
  }
  
  static getInstance(): AuditService {
    if (!AuditService.instance) {
      AuditService.instance = new AuditService();
    }
    return AuditService.instance;
  }
  
  private generateSessionId(): string {
    return `session${Date.now()}${Math.random().toString(36).substr(2, 9)}`;
  }
  
  setUserId(userId: string): void {
    this.userId = userId;
  }
  
  /**
   * Log a user action event
   */
  async logUserAction(data: UserActionData): Promise<void> {
    await this.logEvent({
      eventType: 'userAction',
      eventCategory: 'frontend',
      action: data.action,
      description: data.description,
      severity: data.severity || 'info',
      patientId: data.patientId,
      additionalContext: {
        sessionId: this.sessionId,
        url: window.location.pathname,
        timestamp: new Date().toISOString(),
        ...data.additionalContext
      }
    });
  }
  
  /**
   * Log patient interaction events
   */
  async logPatientInteraction(
    action: string,
    patientId: string,
    description: string,
    additionalContext?: Record<string, any>
  ): Promise<void> {
    await this.logUserAction({
      action: `patient${action.charAt(0).toUpperCase()}${action.slice(1)}`,
      description: `User ${action} patient ${patientId}: ${description}`,
      patientId: patientId,
      severity: 'info',
      additionalContext: {
        interactionType: 'patient',
        ...additionalContext
      }
    });
  }
  
  /**
   * Log chart interaction events
   */
  async logChartInteraction(
    action: string,
    patientId: string,
    vitalType: string,
    description: string,
    additionalContext?: Record<string, any>
  ): Promise<void> {
    await this.logUserAction({
      action: `chart${action.charAt(0).toUpperCase()}${action.slice(1)}`,
      description: `User ${action} ${vitalType} chart for patient ${patientId}: ${description}`,
      patientId: patientId,
      severity: 'info',
      additionalContext: {
        interactionType: 'chart',
        vitalType: vitalType,
        ...additionalContext
      }
    });
  }
  
  /**
   * Log navigation events
   */
  async logNavigation(from: string, to: string, additionalContext?: Record<string, any>): Promise<void> {
    await this.logUserAction({
      action: 'navigation',
      description: `User navigated from ${from} to ${to}`,
      severity: 'info',
      additionalContext: {
        interactionType: 'navigation',
        fromPage: from,
        toPage: to,
        ...additionalContext
      }
    });
  }
  
  /**
   * Log search events
   */
  async logSearch(query: string, results: number, additionalContext?: Record<string, any>): Promise<void> {
    await this.logUserAction({
      action: 'search',
      description: `User searched for "${query}" and found ${results} results`,
      severity: 'info',
      additionalContext: {
        interactionType: 'search',
        searchQuery: query,
        resultCount: results,
        ...additionalContext
      }
    });
  }
  
  /**
   * Log form submission events
   */
  async logFormSubmission(
    formType: string,
    patientId?: string,
    success: boolean = true,
    errorMessage?: string,
    additionalContext?: Record<string, any>
  ): Promise<void> {
    await this.logUserAction({
      action: `form${success ? 'Submit' : 'Error'}`,
      description: success 
        ? `User successfully submitted ${formType} form`
        : `User failed to submit ${formType} form: ${errorMessage}`,
      patientId: patientId,
      severity: success ? 'info' : 'error',
      additionalContext: {
        interactionType: 'form',
        formType: formType,
        success,
        errorMessage: errorMessage,
        ...additionalContext
      }
    });
  }
  
  /**
   * Log error events
   */
  async logError(
    error: Error,
    context: string,
    patientId?: string,
    additionalContext?: Record<string, any>
  ): Promise<void> {
    await this.logUserAction({
      action: 'errorOccurred',
      description: `Error in ${context}: ${error.message}`,
      patientId: patientId,
      severity: 'error',
      additionalContext: {
        interactionType: 'error',
        errorName: error.name,
        errorMessage: error.message,
        errorStack: error.stack,
        context,
        ...additionalContext
      }
    });
  }
  
  /**
   * Core method to send audit logs to backend
   */
  private async logEvent(data: AuditLogData): Promise<void> {
    try {
      const token = localStorage.getItem('hospitalAccessToken');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json'
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
      
      const response = await fetch(`/api/v1/audit/log`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          ...data,
          userId: this.userId,
          sessionId: this.sessionId,
          sourceIp: null, // Will be filled by backend
          userAgent: navigator.userAgent,
          endpoint: null, // Frontend events don't have API endpoints
          httpMethod: null,
          httpStatus: null,
          hipaaRelevant: !!data.patientId
        })
      });
      
      if (!response.ok) {
        // Don't throw errors for audit logging failures to avoid disrupting user experience
        console.warn('Failed to log audit event:', response.status, response.statusText);
      }
    } catch (error) {
      // Silently handle audit logging errors to avoid disrupting user experience
      console.warn('Audit logging error:', error);
    }
  }
}

// Export singleton instance
export const auditService = AuditService.getInstance();

// Convenience export for direct use
export default auditService;
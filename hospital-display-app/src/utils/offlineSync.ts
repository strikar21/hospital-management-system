// offlineSync.ts - Offline resilience for critical medical actions
import { PatientService, MedicationService, InvestigationService, TherapyService } from '../services';
import auditService from '../services/auditService';
import ClientEncryption from './clientEncryption';

interface PendingAction {
  id: string;
  type: string;
  data: any;
  timestamp: string;
  retryCount: number;
  maxRetries: number;
  priority: 'low' | 'medium' | 'high' | 'critical';
}

interface SyncResult {
  success: boolean;
  syncedCount: number;
  failedCount: number;
  errors: string[];
}

class OfflineSync {
  private static instance: OfflineSync;
  private pendingActions: PendingAction[] = [];
  private isOnline: boolean = navigator.onLine;
  private syncInProgress: boolean = false;
  private syncInterval: NodeJS.Timeout | null = null;

  constructor() {
    // Load pending actions from localStorage on startup
    this.loadPendingActions();

    // Set up online/offline event listeners
    window.addEventListener('online', this.handleOnline.bind(this));
    window.addEventListener('offline', this.handleOffline.bind(this));

    // Start periodic sync when online
    if (this.isOnline) {
      this.startPeriodicSync();
    }

    // Log service initialization
    auditService.logUserAction({
      action: 'offlineSyncInitialized',
      description: `Offline sync service initialized with ${this.pendingActions.length} pending actions`,
      severity: 'info',
      additionalContext: {
        isOnline: this.isOnline,
        pendingActionsCount: this.pendingActions.length
      }
    });
  }

  static getInstance(): OfflineSync {
    if (!OfflineSync.instance) {
      OfflineSync.instance = new OfflineSync();
    }
    return OfflineSync.instance;
  }

  /**
   * Queue a critical action when offline or when backend is unavailable
   */
  queueAction(type: string, data: any, priority: 'low' | 'medium' | 'high' | 'critical' = 'medium'): string {
    const actionId = ""  // Backend will generate action ID;
    
    const action: PendingAction = {
      id: actionId,
      type,
      data,
      timestamp: new Date().toISOString(),
      retryCount: 0,
      maxRetries: priority === 'critical' ? 10 : priority === 'high' ? 5 : 3,
      priority
    };

    this.pendingActions.push(action);
    this.savePendingActions();

    // Log the queued action
    auditService.logUserAction({
      action: 'actionQueued',
      description: `Action ${type} queued for offline sync`,
      patientId: data.patientId,
      severity: priority === 'critical' ? 'critical' : 'warning',
      additionalContext: {
        actionId,
        actionType: type,
        priority,
        isOnline: this.isOnline
      }
    });

    // Queued action for offline sync
    return actionId;
  }

  /**
   * Sync all pending actions when back online
   */
  async syncPendingActions(): Promise<SyncResult> {
    if (this.syncInProgress || !this.isOnline) {
      return { success: false, syncedCount: 0, failedCount: 0, errors: ['Sync already in progress or offline'] };
    }

    this.syncInProgress = true;
    // Starting offline sync

    let syncedCount = 0;
    let failedCount = 0;
    const errors: string[] = [];

    // Sort by priority (critical first) and timestamp
    const sortedActions = this.pendingActions.sort((a, b) => {
      const priorityOrder = { critical: 0, high: 1, medium: 2, low: 3 };
      if (priorityOrder[a.priority] !== priorityOrder[b.priority]) {
        return priorityOrder[a.priority] - priorityOrder[b.priority];
      }
      return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
    });

    for (const action of sortedActions) {
      try {
        // Syncing action with priority
        
        const success = await this.syncAction(action);
        
        if (success) {
          syncedCount++;
          // Remove successfully synced action
          this.pendingActions = this.pendingActions.filter(a => a.id !== action.id);
          
          auditService.logUserAction({
            action: 'actionSynced',
            description: `Successfully synced ${action.type} action`,
            patientId: action.data.patientId,
            severity: 'info',
            additionalContext: {
              actionId: action.id,
              actionType: action.type,
              syncedAfterMinutes: ((new Date().getTime() - new Date(action.timestamp).getTime())) / (1000 * 60)
            }
          });
        } else {
          failedCount++;
          action.retryCount++;
          
          if (action.retryCount >= action.maxRetries) {
            errors.push(`Action ${action.type} failed after ${action.maxRetries} retries`);
            // Remove actions that exceeded max retries
            this.pendingActions = this.pendingActions.filter(a => a.id !== action.id);
            
            auditService.logError(
              new Error(`Offline sync failed: ${action.type} exceeded max retries`),
              'offline_sync',
              action.data.patientId,
              {
                actionId: action.id,
                actionType: action.type,
                retryCount: action.retryCount,
                maxRetries: action.maxRetries
              }
            );
          }
        }
      } catch (error) {
        failedCount++;
        errors.push(`Failed to sync ${action.type}: ${error instanceof Error ? error.message : String(error)}`);
        // Failed to sync action - handle silently
      }
    }

    this.savePendingActions();
    this.syncInProgress = false;

    const result: SyncResult = {
      success: failedCount === 0,
      syncedCount,
      failedCount,
      errors
    };

    // Removed console.log for production
    
    auditService.logUserAction({
      action: 'offlineSyncCompleted',
      description: `Offline sync completed: ${syncedCount} synced, ${failedCount} failed`,
      severity: failedCount > 0 ? 'warning' : 'info',
      additionalContext: result
    });

    return result;
  }

  /**
   * Sync individual action to backend
   */
  private async syncAction(action: PendingAction): Promise<boolean> {
    try {
      switch (action.type) {
        case 'nfc_interaction':
          // Note: logNfcTap needs to be implemented in a service
          // Warning: NFC tap logging not yet migrated to services
          return false;

        case 'vital_alert_acknowledgment':
          return await PatientService.acknowledgeAlert(
            action.data.patientId,
            action.data.alertId,
            action.data.userId
          );

        case 'medication_administration':
          return await MedicationService.updateMedication(
            action.data.patientId,
            action.data.medicationId,
            'active',
            action.data.userId
          );

        case 'investigation_update':
          return await InvestigationService.updateInvestigationStatus(
            action.data.investigationId,
            action.data.status,
            action.data.userId
          );

        case 'therapy_update':
          return await TherapyService.updateTherapy(
            action.data.patientId,
            action.data.therapyId,
            action.data.status,
            action.data.userId
          );

        case 'patient_note':
          return await PatientService.addNoteComment(
            action.data.patientId,
            action.data.content,
            action.data.userId,
            action.data.username,
            action.data.userRole
          );

        default:
          // Warning: Unknown action type for sync
          return false;
      }
    } catch (error) {
      // Error syncing action - handle silently
      return false;
    }
  }

  /**
   * Handle online event
   */
  private handleOnline() {
    // Connection restored - starting offline sync
    this.isOnline = true;
    
    auditService.logUserAction({
      action: 'connectionRestored',
      description: 'Network connection restored, starting offline sync',
      severity: 'info',
      additionalContext: {
        pendingActionsCount: this.pendingActions.length
      }
    });

    // Start syncing pending actions
    this.syncPendingActions();
    this.startPeriodicSync();
  }

  /**
   * Handle offline event
   */
  private handleOffline() {
    // Connection lost - enabling offline mode
    this.isOnline = false;
    this.stopPeriodicSync();

    auditService.logUserAction({
      action: 'connectionLost',
      description: 'Network connection lost, enabling offline mode',
      severity: 'warning',
      additionalContext: {
        pendingActionsCount: this.pendingActions.length
      }
    });
  }

  /**
   * Start periodic sync (every 30 seconds when online)
   */
  private startPeriodicSync() {
    if (this.syncInterval) return;

    this.syncInterval = setInterval(() => {
      if (this.isOnline && this.pendingActions.length > 0) {
        this.syncPendingActions();
      }
    }, 30000); // 30 seconds
  }

  /**
   * Stop periodic sync
   */
  private stopPeriodicSync() {
    if (this.syncInterval) {
      clearInterval(this.syncInterval);
      this.syncInterval = null;
    }
  }

  /**
   * Load pending actions from localStorage with decryption
   */
  private loadPendingActions() {
    try {
      const stored = localStorage.getItem('hospital_pending_actions');
      if (stored) {
        try {
          // Try to decrypt first (new format)
          const decrypted = ClientEncryption.decryptPatientData(stored);
          if (decrypted.actions && Array.isArray(decrypted.actions)) {
            this.pendingActions = decrypted.actions;
            // Loaded encrypted pending actions from storage
            return;
          }
        } catch (decryptError) {
          // Fall back to legacy unencrypted format
          // Falling back to legacy unencrypted pending actions
        }
        
        // Legacy unencrypted format
        this.pendingActions = JSON.parse(stored);
        // Loaded pending actions from storage (legacy format)
      }
    } catch (error) {
      // Failed to load pending actions from localStorage - handle silently
      this.pendingActions = [];
    }
  }

  /**
   * Save pending actions to localStorage with encryption
   */
  private savePendingActions() {
    try {
      const encryptedActions = ClientEncryption.encryptPatientData({
        actions: this.pendingActions,
        savedAt: new Date().toISOString(),
        type: 'pending_medical_actions'
      });
      localStorage.setItem('hospital_pending_actions', encryptedActions);
    } catch (error) {
      // Failed to save encrypted pending actions - handle silently
      // Fallback to unencrypted if encryption fails
      try {
        localStorage.setItem('hospital_pending_actions', JSON.stringify(this.pendingActions));
      } catch (fallbackError) {
        // Failed to save pending actions (fallback) - handle silently
      }
    }
  }

  /**
   * Get current sync status
   */
  getSyncStatus() {
    return {
      isOnline: this.isOnline,
      pendingActionsCount: this.pendingActions.length,
      syncInProgress: this.syncInProgress,
      criticalActionsCount: this.pendingActions.filter(a => a.priority === 'critical').length
    };
  }

  /**
   * Manually trigger sync (for testing or user-initiated sync)
   */
  async forceSync(): Promise<SyncResult> {
    return await this.syncPendingActions();
  }
}

// Export singleton instance
export const offlineSync = OfflineSync.getInstance();

export default offlineSync;
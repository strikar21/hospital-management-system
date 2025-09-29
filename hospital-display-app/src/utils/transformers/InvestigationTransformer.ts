/**
 * InvestigationTransformer - Investigation and therapy data transformation utilities
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Handles medical investigations and therapy session data with clinical compliance
 */

import { BaseTransformer } from './BaseTransformer';

export class InvestigationTransformer extends BaseTransformer {

  // ================================
  // INVESTIGATION TRANSFORMATION
  // ================================

  /**
   * Transform investigation data - CAMELCASE ONLY
   * Clinical-grade investigation data transformation with compliance
   */
  static transformInvestigation(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data) return null;

    try {
      // Validate required investigation fields
      const requiredFields = ['type', 'orderedBy'];
      if (!this.validateMedicalData(data, requiredFields)) {
        console.warn('Investigation data missing required fields:', data);
      }

      // Transform object keys to camelCase
      let transformed = this.transformObjectKeys(data);

      // Apply investigation-specific defaults
      transformed = this.applyInvestigationDefaults(transformed);

      // Add resolved staff names
      transformed = this.addResolvedNames(transformed, staffMapping);

      // Add edit permissions based on medical compliance window
      transformed.canEdit = this.canEditMedicalRecord(transformed.createdAt);

      // Add investigation status tracking
      transformed = this.addInvestigationStatusTracking(transformed);

      // Apply medical data sanitization
      transformed = this.sanitizeMedicalData(transformed);

      return transformed;
    } catch (error) {
      console.error('Error transforming investigation data:', error);
      return data;
    }
  }

  /**
   * Apply investigation-specific defaults and validation
   */
  private static applyInvestigationDefaults(data: any): any {
    if (!data || typeof data !== 'object') return data;

    const withDefaults = { ...data };

    // Ensure investigation type is properly formatted
    if (withDefaults.type) {
      withDefaults.investigationType = withDefaults.investigationType || withDefaults.type;
    }

    // Ensure priority field has valid value
    if (!withDefaults.priority) {
      withDefaults.priority = 'routine';
    }

    // Ensure urgency field has valid value
    if (!withDefaults.urgency) {
      withDefaults.urgency = 'normal';
    }

    // Ensure status field has valid value
    if (!withDefaults.status) {
      withDefaults.status = 'ordered';
    }

    // Format timestamps properly
    if (withDefaults.scheduledAt && typeof withDefaults.scheduledAt === 'string') {
      try {
        withDefaults.scheduledAt = new Date(withDefaults.scheduledAt).toISOString();
      } catch (error) {
        withDefaults.scheduledAt = null;
      }
    }

    if (withDefaults.orderedDate && typeof withDefaults.orderedDate === 'string') {
      try {
        withDefaults.orderedDate = new Date(withDefaults.orderedDate).toISOString();
      } catch (error) {
        withDefaults.orderedDate = new Date().toISOString();
      }
    }

    // Set creation timestamp if not present
    if (!withDefaults.createdAt) {
      withDefaults.createdAt = new Date().toISOString();
    }

    return withDefaults;
  }

  /**
   * Add investigation status tracking
   */
  private static addInvestigationStatusTracking(data: any): any {
    if (!data || typeof data !== 'object') return data;

    const withTracking = { ...data };

    // Calculate investigation status
    withTracking.investigationStatus = this.calculateInvestigationStatus(withTracking);

    // Add time-based information
    withTracking.isOverdue = this.isInvestigationOverdue(withTracking);
    withTracking.timeToScheduled = this.calculateTimeToScheduled(withTracking);

    return withTracking;
  }

  /**
   * Calculate investigation status based on timestamps
   */
  private static calculateInvestigationStatus(investigation: any): string {
    if (investigation.completedAt) return 'completed';
    if (investigation.results) return 'results-available';

    const now = new Date();

    if (investigation.scheduledAt) {
      const scheduledTime = new Date(investigation.scheduledAt);
      if (scheduledTime > now) return 'scheduled';
      if (scheduledTime <= now) return 'in-progress';
    }

    return investigation.status || 'ordered';
  }

  /**
   * Check if investigation is overdue
   */
  private static isInvestigationOverdue(investigation: any): boolean {
    if (!investigation.scheduledAt || investigation.completedAt) return false;

    const scheduledTime = new Date(investigation.scheduledAt);
    const now = new Date();

    // Consider overdue if 2 hours past scheduled time
    return (now.getTime() - scheduledTime.getTime()) > (2 * 60 * 60 * 1000);
  }

  /**
   * Calculate time until scheduled investigation
   */
  private static calculateTimeToScheduled(investigation: any): number | null {
    if (!investigation.scheduledAt) return null;

    const scheduledTime = new Date(investigation.scheduledAt);
    const now = new Date();

    return scheduledTime.getTime() - now.getTime();
  }

  // ================================
  // THERAPY TRANSFORMATION
  // ================================

  /**
   * Transform therapy data - CAMELCASE ONLY
   * Clinical-grade therapy session data transformation
   */
  static transformTherapy(data: any, staffMapping?: { [key: string]: string }): any {
    if (!data) return null;

    try {
      // Validate required therapy fields
      const requiredFields = ['therapyType'];
      if (!this.validateMedicalData(data, requiredFields)) {
        console.warn('Therapy data missing required fields:', data);
      }

      // Transform object keys to camelCase
      let transformed = this.transformObjectKeys(data);

      // Apply therapy-specific defaults
      transformed = this.applyTherapyDefaults(transformed);

      // Add resolved staff names
      transformed = this.addResolvedNames(transformed, staffMapping);

      // Add edit permissions based on medical compliance window
      transformed.canEdit = this.canEditMedicalRecord(transformed.createdAt);

      // Add therapy session tracking
      transformed = this.addTherapySessionTracking(transformed);

      // Apply medical data sanitization
      transformed = this.sanitizeMedicalData(transformed);

      return transformed;
    } catch (error) {
      console.error('Error transforming therapy data:', error);
      return data;
    }
  }

  /**
   * Apply therapy-specific defaults and validation
   */
  private static applyTherapyDefaults(data: any): any {
    if (!data || typeof data !== 'object') return data;

    const withDefaults = { ...data };

    // Ensure therapy type is properly set
    if (withDefaults.type && !withDefaults.therapyType) {
      withDefaults.therapyType = withDefaults.type;
    }

    // Ensure status field has valid value
    if (!withDefaults.status) {
      withDefaults.status = 'scheduled';
    }

    // Set therapist information
    if (withDefaults.performedBy && !withDefaults.therapist) {
      withDefaults.therapist = withDefaults.performedBy;
    }

    // Format session date
    if (withDefaults.sessionDate && typeof withDefaults.sessionDate === 'string') {
      try {
        withDefaults.sessionDate = new Date(withDefaults.sessionDate).toISOString();
      } catch (error) {
        withDefaults.sessionDate = null;
      }
    }

    if (withDefaults.scheduledDate && typeof withDefaults.scheduledDate === 'string') {
      try {
        withDefaults.scheduledDate = new Date(withDefaults.scheduledDate).toISOString();
      } catch (error) {
        withDefaults.scheduledDate = new Date().toISOString();
      }
    }

    // Set creation timestamp if not present
    if (!withDefaults.createdAt) {
      withDefaults.createdAt = new Date().toISOString();
    }

    return withDefaults;
  }

  /**
   * Add therapy session tracking
   */
  private static addTherapySessionTracking(data: any): any {
    if (!data || typeof data !== 'object') return data;

    const withTracking = { ...data };

    // Calculate therapy status
    withTracking.therapyStatus = this.calculateTherapyStatus(withTracking);

    // Add session information
    withTracking.isCompleted = Boolean(withTracking.sessionDate && withTracking.sessionNotes);
    withTracking.nextSessionDue = this.calculateNextSessionTime(withTracking);

    return withTracking;
  }

  /**
   * Calculate therapy status
   */
  private static calculateTherapyStatus(therapy: any): string {
    if (therapy.sessionDate && therapy.sessionNotes) return 'completed';
    if (therapy.sessionDate) return 'in-progress';

    const now = new Date();

    if (therapy.scheduledDate) {
      const scheduledTime = new Date(therapy.scheduledDate);
      if (scheduledTime > now) return 'scheduled';
      if (scheduledTime <= now) return 'due';
    }

    return therapy.status || 'planned';
  }

  /**
   * Calculate next therapy session time
   */
  private static calculateNextSessionTime(therapy: any): string | null {
    if (!therapy.sessions || therapy.sessions <= 1) return null;

    // Simple calculation - could be enhanced with more sophisticated scheduling
    const lastSession = therapy.sessionDate ? new Date(therapy.sessionDate) : new Date();
    const nextSession = new Date(lastSession.getTime() + (7 * 24 * 60 * 60 * 1000)); // +1 week

    return nextSession.toISOString();
  }

  // ================================
  // ARRAY TRANSFORMATIONS
  // ================================

  /**
   * Transform investigation array data
   */
  static transformInvestigationArray(data: any[], staffMapping?: { [key: string]: string }): any[] {
    if (!Array.isArray(data)) return [];

    return data
      .map(investigation => this.transformInvestigation(investigation, staffMapping))
      .filter(investigation => investigation !== null) // Remove failed transformations
      .sort((a, b) => {
        // Sort by priority and scheduled time
        const priorityOrder = { 'urgent': 0, 'high': 1, 'routine': 2, 'low': 3 };
        const aPriority = priorityOrder[a.priority as keyof typeof priorityOrder] ?? 4;
        const bPriority = priorityOrder[b.priority as keyof typeof priorityOrder] ?? 4;

        if (aPriority !== bPriority) return aPriority - bPriority;

        // Then by scheduled time
        const aTime = a.scheduledAt ? new Date(a.scheduledAt).getTime() : 0;
        const bTime = b.scheduledAt ? new Date(b.scheduledAt).getTime() : 0;

        return aTime - bTime;
      });
  }

  /**
   * Transform therapy array data
   */
  static transformTherapyArray(data: any[], staffMapping?: { [key: string]: string }): any[] {
    if (!Array.isArray(data)) return [];

    return data
      .map(therapy => this.transformTherapy(therapy, staffMapping))
      .filter(therapy => therapy !== null) // Remove failed transformations
      .sort((a, b) => {
        // Sort by session date/scheduled date
        const aDate = a.sessionDate || a.scheduledDate || '';
        const bDate = b.sessionDate || b.scheduledDate || '';

        return new Date(bDate).getTime() - new Date(aDate).getTime();
      });
  }

  // ================================
  // SUMMARY TRANSFORMATIONS
  // ================================

  /**
   * Transform investigation summary for dashboard
   */
  static transformInvestigationSummary(investigations: any[], staffMapping?: { [key: string]: string }): any {
    const transformedInvestigations = this.transformInvestigationArray(investigations, staffMapping);

    const pendingInvestigations = transformedInvestigations.filter(inv =>
      ['ordered', 'scheduled'].includes(inv.investigationStatus)
    );
    const overdueInvestigations = transformedInvestigations.filter(inv => inv.isOverdue);
    const completedInvestigations = transformedInvestigations.filter(inv =>
      inv.investigationStatus === 'completed'
    );

    return {
      totalInvestigations: transformedInvestigations.length,
      pendingInvestigations: pendingInvestigations.length,
      overdueInvestigations: overdueInvestigations.length,
      completedInvestigations: completedInvestigations.length,
      investigations: transformedInvestigations,
      pendingList: pendingInvestigations,
      overdueList: overdueInvestigations,
      lastUpdated: new Date().toISOString()
    };
  }

  /**
   * Transform therapy summary for dashboard
   */
  static transformTherapySummary(therapies: any[], staffMapping?: { [key: string]: string }): any {
    const transformedTherapies = this.transformTherapyArray(therapies, staffMapping);

    const scheduledTherapies = transformedTherapies.filter(therapy =>
      therapy.therapyStatus === 'scheduled'
    );
    const completedTherapies = transformedTherapies.filter(therapy =>
      therapy.therapyStatus === 'completed'
    );
    const dueTherapies = transformedTherapies.filter(therapy =>
      therapy.therapyStatus === 'due'
    );

    return {
      totalTherapies: transformedTherapies.length,
      scheduledTherapies: scheduledTherapies.length,
      completedTherapies: completedTherapies.length,
      dueTherapies: dueTherapies.length,
      therapies: transformedTherapies,
      scheduledList: scheduledTherapies,
      dueList: dueTherapies,
      lastUpdated: new Date().toISOString()
    };
  }
}
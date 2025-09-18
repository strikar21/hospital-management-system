// PACS/Imaging Service - Handles medical imaging integration
import { ImagingStudy, ImagingImage, ImagingReport } from '../types';
import HospitalAPI from '../api';

export class ImagingService {
  // Get imaging studies for a patient
  static async getPatientImagingStudies(patientId: string): Promise<ImagingStudy[]> {
    try {
      // Will be implemented when backend is ready
      console.log('Fetching imaging studies for patient:', patientId);
      return [];
    } catch (error) {
      console.error('Failed to fetch imaging studies:', error);
      return [];
    }
  }

  // Get specific imaging study
  static async getImagingStudy(studyId: string): Promise<ImagingStudy | null> {
    try {
      console.log('Fetching imaging study:', studyId);
      return null;
    } catch (error) {
      console.error('Failed to fetch imaging study:', error);
      return null;
    }
  }

  // Get pending imaging studies awaiting radiologist review
  static async getPendingStudies(): Promise<ImagingStudy[]> {
    try {
      console.log('Fetching pending imaging studies');
      return [];
    } catch (error) {
      console.error('Failed to fetch pending imaging studies:', error);
      return [];
    }
  }

  // Update imaging study status
  static async updateStudyStatus(studyId: string, status: string, userId: string): Promise<boolean> {
    try {
      console.log('Updating imaging study status:', studyId, status);
      return true;
    } catch (error) {
      console.error('Failed to update imaging study status:', error);
      return false;
    }
  }

  // Add radiologist report
  static async addRadiologyReport(studyId: string, report: Partial<ImagingReport>, userId: string): Promise<boolean> {
    try {
      console.log('Adding radiology report:', studyId);
      return true;
    } catch (error) {
      console.error('Failed to add radiology report:', error);
      return false;
    }
  }

  // Get imaging study priority color for UI
  static getStudyPriorityColor(urgency: string): string {
    switch (urgency) {
      case 'stat':
      case 'urgent':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'asap':
        return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'routine':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  }

  // Get study status color for UI
  static getStudyStatusColor(status: string): string {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'in_progress':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'pending':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'cancelled':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  }

  // Check if imaging study requires immediate attention
  static requiresImmediateAttention(study: ImagingStudy): boolean {
    return study.urgency === 'stat' || study.urgency === 'urgent';
  }

  // Get studies needing radiologist review
  static needsRadiologistReview(studies: ImagingStudy[]): ImagingStudy[] {
    return studies.filter(study => 
      study.status === 'completed' && 
      (!study.report || study.report.status !== 'final')
    );
  }

  // Generate imaging report summary
  static generateReportSummary(study: ImagingStudy): string {
    if (!study.report) {
      return `${study.studyType.toUpperCase()} ${study.bodyPart} - Awaiting radiologist report`;
    }

    const reportSummary = study.report.impression || study.report.findings || 'No findings documented';
    return `${study.studyType.toUpperCase()} ${study.bodyPart}: ${reportSummary}`;
  }

  // Get image viewer URL for DICOM viewing
  static getImageViewerUrl(studyId: string): string {
    return `/imaging/viewer/${studyId}`;
  }

  // Export study for external sharing
  static async exportStudy(studyId: string, format: 'dicom' | 'pdf' | 'jpg'): Promise<string | null> {
    try {
      console.log('Exporting imaging study:', studyId, format);
      return null;
    } catch (error) {
      console.error('Failed to export imaging study:', error);
      return null;
    }
  }

  // Format study description for display
  static formatStudyDescription(study: ImagingStudy): string {
    return `${study.studyType.toUpperCase()} - ${study.bodyPart}`;
  }

  // Get study type color for UI
  static getStudyTypeColor(studyType: string): string {
    switch (studyType.toLowerCase()) {
      case 'xray':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      case 'ct':
        return 'text-purple-600 bg-purple-50 border-purple-200';
      case 'mri':
        return 'text-green-600 bg-green-50 border-green-200';
      case 'ultrasound':
        return 'text-teal-600 bg-teal-50 border-teal-200';
      case 'pet':
        return 'text-red-600 bg-red-50 border-red-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  }

  // Alias for getStudyPriorityColor to match component usage
  static getUrgencyColor(urgency: string): string {
    return this.getStudyPriorityColor(urgency);
  }

  // Check if study has abnormal findings
  static hasAbnormalFindings(study: ImagingStudy): boolean {
    if (!study.report) return false;
    
    const findings = study.report.findings?.toLowerCase() || '';
    const impression = study.report.impression?.toLowerCase() || '';
    
    const abnormalKeywords = [
      'abnormal', 'pathological', 'lesion', 'mass', 'tumor', 'fracture',
      'infection', 'inflammation', 'abnormality', 'concerning', 'suspicious'
    ];
    
    return abnormalKeywords.some(keyword => 
      findings.includes(keyword) || impression.includes(keyword)
    );
  }

  // Open DICOM viewer for image
  static openDicomViewer(imageId: string | ImagingImage): void {
    // Open external DICOM viewer or navigate to internal viewer
    const id = typeof imageId === 'string' ? imageId : imageId.id;
    const viewerUrl = `/dicom-viewer/${id}`;
    window.open(viewerUrl, '_blank', 'width=1200,height=800');
  }
}
// MedicalErrorBoundary.tsx - Medical-grade error handling for patient safety
import React, { Component, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Phone } from 'lucide-react';
import auditService from '../services/auditService';

interface Props {
  children: ReactNode;
  patientId?: string;
  userId?: string;
  userRole?: string;
  medicalContext?: string;
  fallbackComponent?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
  errorId: string;
}

class MedicalErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: ''
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    // Generate cryptographically secure error ID for medical compliance
    const timestamp = Date.now().toString();
    const randomBytes = crypto.getRandomValues(new Uint8Array(6));
    const randomHex = Array.from(randomBytes, b => b.toString(16).padStart(2, '0')).join('');
    const errorId = `ERR-${timestamp}-${randomHex}`;

    return {
      hasError: true,
      error,
      errorId
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Production: Critical medical error - log to monitoring service and audit trail

    // Log to audit service for medical compliance
    auditService.logError(error, 'criticalMedicalComponent', this.props.patientId, {
      componentStack: errorInfo.componentStack,
      medicalContext: this.props.medicalContext || 'unknownMedicalContext',
      patientSafety: 'criticalErrorOccurred',
      errorBoundary: 'MedicalErrorBoundary',
      errorId: this.state.errorId,
      timestamp: new Date().toISOString(),
      useragent: navigator.userAgent,
      url: window.location.href,
      // Separate patient and user context for proper audit trails
      patientId: this.props.patientId,
      userId: this.props.userId,
      userRole: this.props.userRole
    });

    this.setState({
      error,
      errorInfo
    });
  }

  handleReload = () => {
    // Log recovery attempt
    auditService.logUserAction({
      action: 'errorRecoveryAttempt',
      description: `User attempted to recover from error ${this.state.errorId}`,
      patientId: this.props.patientId,
      severity: 'warning',
      additionalContext: {
        errorId: this.state.errorId,
        recoveryMethod: 'application_reload'
      }
    });

    window.location.reload();
  };

  handleReportError = () => {
    // Log error report
    auditService.logUserAction({
      action: 'errorReported',
      description: `User reported error ${this.state.errorId} to IT support`,
      patientId: this.props.patientId,
      severity: 'critical',
      additionalContext: {
        errorId: this.state.errorId,
        reportMethod: 'manual_report'
      }
    });

    // In production, this could trigger IT notification system
    alert(`Error ID: ${this.state.errorId}\n\nPlease contact IT support and provide this error ID for faster resolution.`);
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallbackComponent) {
        return this.props.fallbackComponent;
      }

      // Medical-grade error display - never leave patient data inaccessible
      return (
        <div className="min-h-96 flex items-center justify-center bg-red-50 border-2 border-red-200 rounded-lg m-4">
          <div className="text-center p-8 max-w-md">
            {/* Error Icon */}
            <div className="flex justify-center mb-4">
              <div className="bg-red-100 p-3 rounded-full">
                <AlertTriangle className="w-8 h-8 text-red-600" />
              </div>
            </div>

            {/* Error Message */}
            <h2 className="text-xl font-bold text-red-800 mb-3">
              System Error Detected
            </h2>
            <p className="text-red-700 mb-2">
              {this.props.patientId 
                ? `Patient data for ${this.props.patientId} temporarily unavailable.`
                : 'Medical system component temporarily unavailable.'
              }
            </p>
            <p className="text-red-600 text-sm mb-6">
              Error ID: <code className="font-mono bg-red-100 px-2 py-1 rounded">{this.state.errorId}</code>
            </p>

            {/* Recovery Actions */}
            <div className="space-y-3">
              {/* Primary Action - Reload */}
              <button 
                onClick={this.handleReload}
                className="w-full flex items-center justify-center space-x-2 bg-red-600 hover:bg-red-700 text-white font-medium py-3 px-4 rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Reload Application</span>
              </button>

              {/* Secondary Action - Report Error */}
              <button
                onClick={this.handleReportError}
                className="w-full flex items-center justify-center space-x-2 bg-red-100 hover:bg-red-200 text-red-800 font-medium py-2 px-4 rounded-lg transition-colors"
              >
                <Phone className="w-4 h-4" />
                <span>Report to IT Support</span>
              </button>
            </div>

            {/* Medical Compliance Notice */}
            <div className="mt-6 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-yellow-800 text-xs">
                <strong>Patient Safety Notice:</strong> If this error persists, please use alternative 
                methods to access patient information and contact IT support immediately.
              </p>
            </div>

            {/* Development Info (only in dev mode) */}
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-4 text-left">
                <summary className="text-sm text-gray-600 cursor-pointer hover:text-gray-800">
                  Developer Information
                </summary>
                <div className="mt-2 p-3 bg-gray-100 rounded text-xs font-mono text-gray-800 overflow-auto max-h-32">
                  <div><strong>Error:</strong> {this.state.error.message}</div>
                  {this.state.errorInfo && (
                    <div className="mt-2">
                      <strong>Component Stack:</strong>
                      <pre className="whitespace-pre-wrap">{this.state.errorInfo.componentStack}</pre>
                    </div>
                  )}
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default MedicalErrorBoundary;
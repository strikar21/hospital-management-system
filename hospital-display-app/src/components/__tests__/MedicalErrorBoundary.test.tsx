/**
 * MedicalErrorBoundary Tests
 * PRIORITY 1 - CRITICAL: Graceful failure for patient safety
 *
 * Tests error catching, fallback UI, medical context logging,
 * and PHI protection in error messages
 */

import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import MedicalErrorBoundary from '../MedicalErrorBoundary';
import auditService from '../../services/auditService';

// Mock audit service
jest.mock('../../services/auditService', () => ({
  __esModule: true,
  default: {
    logError: jest.fn(),
    logUserAction: jest.fn()
  }
}));

// Mock window.location.reload
delete (window as any).location;
(window as any).location = { reload: jest.fn() };

// Mock alert
global.alert = jest.fn();

// Component that throws an error
const ThrowError: React.FC<{ shouldThrow?: boolean; errorMessage?: string }> = ({
  shouldThrow = false,
  errorMessage = 'Test error'
}) => {
  if (shouldThrow) {
    throw new Error(errorMessage);
  }
  return <div>Normal Content</div>;
};

describe('MedicalErrorBoundary - Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Suppress console.error for cleaner test output
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    (console.error as jest.Mock).mockRestore();
  });

  // ================================
  // ERROR CATCHING
  // ================================

  describe('Error Catching', () => {
    test('should render children when no error', () => {
      render(
        <MedicalErrorBoundary>
          <div>Normal Content</div>
        </MedicalErrorBoundary>
      );

      expect(screen.getByText('Normal Content')).toBeInTheDocument();
    });

    test('should catch errors from child components', () => {
      render(
        <MedicalErrorBoundary patientId="PAT001">
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      // Should show error UI
      expect(screen.getByText('System Error Detected')).toBeInTheDocument();
      expect(screen.getByText(/Patient data for PAT001 temporarily unavailable/)).toBeInTheDocument();
    });

    test('should display error ID to user', () => {
      render(
        <MedicalErrorBoundary>
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      // Error ID should be displayed
      const errorIdElement = screen.getByText(/Error ID:/);
      expect(errorIdElement).toBeInTheDocument();

      // Error ID should follow ERR-timestamp-randomhex format
      const codeElement = errorIdElement.parentElement?.querySelector('code');
      expect(codeElement?.textContent).toMatch(/^ERR-\d+-[a-f0-9]{12}$/);
    });

    test('should show generic message when no patientId provided', () => {
      render(
        <MedicalErrorBoundary>
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      expect(screen.getByText(/Medical system component temporarily unavailable/)).toBeInTheDocument();
    });
  });

  // ================================
  // MEDICAL CONTEXT LOGGING
  // ================================

  describe('Medical Context Logging', () => {
    test('should log error with medical context to audit service', () => {
      render(
        <MedicalErrorBoundary
          patientId="PAT001"
          userId="DOC001"
          userRole="doctor"
          medicalContext="patient_vitals_display"
        >
          <ThrowError shouldThrow={true} errorMessage="Critical component failure" />
        </MedicalErrorBoundary>
      );

      // Verify audit service was called
      expect(auditService.logError).toHaveBeenCalledTimes(1);

      // Verify medical context included
      const logCall = (auditService.logError as jest.Mock).mock.calls[0];
      expect(logCall[0].message).toBe('Critical component failure');
      expect(logCall[1]).toBe('criticalMedicalComponent');
      expect(logCall[2]).toBe('PAT001'); // patientId
      expect(logCall[3]).toMatchObject({
        medicalContext: 'patient_vitals_display',
        patientSafety: 'criticalErrorOccurred',
        errorBoundary: 'MedicalErrorBoundary',
        patientId: 'PAT001',
        userId: 'DOC001',
        userRole: 'doctor'
      });
    });

    test('should generate unique error ID for each error boundary instance', () => {
      // Render first error boundary instance
      const { unmount: unmount1 } = render(
        <MedicalErrorBoundary>
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      const firstErrorId = screen.getByText(/Error ID:/).parentElement?.querySelector('code')?.textContent;

      // Clean up first instance
      unmount1();

      // Render second error boundary instance (separate component)
      render(
        <MedicalErrorBoundary>
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      const secondErrorId = screen.getByText(/Error ID:/).parentElement?.querySelector('code')?.textContent;

      // Error IDs should be different (different instances = different errors)
      expect(firstErrorId).not.toBe(secondErrorId);
      expect(firstErrorId).toMatch(/^ERR-\d+-[a-f0-9]{12}$/);
      expect(secondErrorId).toMatch(/^ERR-\d+-[a-f0-9]{12}$/);
    });

    test('should include component stack in audit log', () => {
      render(
        <MedicalErrorBoundary patientId="PAT001">
          <div>
            <ThrowError shouldThrow={true} />
          </div>
        </MedicalErrorBoundary>
      );

      const logCall = (auditService.logError as jest.Mock).mock.calls[0];
      expect(logCall[3].componentStack).toBeDefined();
      expect(typeof logCall[3].componentStack).toBe('string');
    });
  });

  // ================================
  // PHI PROTECTION IN ERROR MESSAGES
  // ================================

  describe('PHI Protection', () => {
    test('should NOT expose patient details in error message', () => {
      render(
        <MedicalErrorBoundary patientId="PAT001">
          <ThrowError
            shouldThrow={true}
            errorMessage="Database error: Patient John Doe (SSN: 123-45-6789) not found"
          />
        </MedicalErrorBoundary>
      );

      // PHI should NOT be visible in UI
      expect(screen.queryByText(/John Doe/)).not.toBeInTheDocument();
      expect(screen.queryByText(/123-45-6789/)).not.toBeInTheDocument();
      expect(screen.queryByText(/SSN/)).not.toBeInTheDocument();

      // Generic message should be shown instead
      expect(screen.getByText(/Patient data for PAT001 temporarily unavailable/)).toBeInTheDocument();
    });

    test('should NOT expose error details in production mode', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'production';

      render(
        <MedicalErrorBoundary>
          <ThrowError shouldThrow={true} errorMessage="Sensitive database error" />
        </MedicalErrorBoundary>
      );

      // Developer information should NOT be visible
      expect(screen.queryByText('Developer Information')).not.toBeInTheDocument();
      expect(screen.queryByText(/Sensitive database error/)).not.toBeInTheDocument();

      process.env.NODE_ENV = originalEnv;
    });

    test('should show error details in development mode', () => {
      const originalEnv = process.env.NODE_ENV;
      process.env.NODE_ENV = 'development';

      render(
        <MedicalErrorBoundary>
          <ThrowError shouldThrow={true} errorMessage="Test error for development" />
        </MedicalErrorBoundary>
      );

      // Developer information should be available
      const devInfo = screen.getByText('Developer Information');
      expect(devInfo).toBeInTheDocument();

      // Click to expand
      fireEvent.click(devInfo);

      // Error message should be visible in dev mode
      expect(screen.getByText(/Test error for development/)).toBeInTheDocument();

      process.env.NODE_ENV = originalEnv;
    });
  });

  // ================================
  // USER ACTIONS
  // ================================

  describe('Recovery Actions', () => {
    test('should reload application when reload button clicked', () => {
      render(
        <MedicalErrorBoundary>
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      const reloadButton = screen.getByRole('button', { name: /Reload Application/i });
      fireEvent.click(reloadButton);

      // Should reload page
      expect(window.location.reload).toHaveBeenCalled();

      // Should log recovery attempt
      expect(auditService.logUserAction).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'errorRecoveryAttempt',
          severity: 'warning',
          additionalContext: expect.objectContaining({
            recoveryMethod: 'application_reload'
          })
        })
      );
    });

    test('should show error report dialog when report button clicked', () => {
      render(
        <MedicalErrorBoundary>
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      const reportButton = screen.getByRole('button', { name: /Report to IT Support/i });
      fireEvent.click(reportButton);

      // Should show alert with error ID
      expect(global.alert).toHaveBeenCalled();
      const alertMessage = (global.alert as jest.Mock).mock.calls[0][0];
      expect(alertMessage).toContain('Error ID:');
      expect(alertMessage).toContain('contact IT support');

      // Should log error report
      expect(auditService.logUserAction).toHaveBeenCalledWith(
        expect.objectContaining({
          action: 'errorReported',
          severity: 'critical',
          additionalContext: expect.objectContaining({
            reportMethod: 'manual_report'
          })
        })
      );
    });

    test('should include error ID in recovery and report actions', () => {
      render(
        <MedicalErrorBoundary>
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      const errorId = screen.getByText(/Error ID:/).parentElement?.querySelector('code')?.textContent;

      // Click reload
      const reloadButton = screen.getByRole('button', { name: /Reload Application/i });
      fireEvent.click(reloadButton);

      // Verify error ID in log
      expect(auditService.logUserAction).toHaveBeenCalledWith(
        expect.objectContaining({
          additionalContext: expect.objectContaining({
            errorId
          })
        })
      );
    });
  });

  // ================================
  // CUSTOM FALLBACK COMPONENT
  // ================================

  describe('Custom Fallback', () => {
    test('should render custom fallback component when provided', () => {
      const CustomFallback = <div data-testid="custom-fallback">Custom Error UI</div>;

      render(
        <MedicalErrorBoundary fallbackComponent={CustomFallback}>
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      // Custom fallback should be rendered
      expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
      expect(screen.getByText('Custom Error UI')).toBeInTheDocument();

      // Default error UI should NOT be rendered
      expect(screen.queryByText('System Error Detected')).not.toBeInTheDocument();
    });

    test('should still log to audit service even with custom fallback', () => {
      const CustomFallback = <div>Custom Error</div>;

      render(
        <MedicalErrorBoundary
          fallbackComponent={CustomFallback}
          patientId="PAT001"
        >
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      // Audit service should still be called
      expect(auditService.logError).toHaveBeenCalled();
    });
  });

  // ================================
  // PATIENT SAFETY NOTICE
  // ================================

  describe('Patient Safety', () => {
    test('should display patient safety notice', () => {
      render(
        <MedicalErrorBoundary>
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      expect(screen.getByText(/Patient Safety Notice:/)).toBeInTheDocument();
      expect(screen.getByText(/use alternative methods to access patient information/)).toBeInTheDocument();
    });

    test('should provide clear action buttons for medical staff', () => {
      render(
        <MedicalErrorBoundary>
          <ThrowError shouldThrow={true} />
        </MedicalErrorBoundary>
      );

      // Both action buttons should be present
      expect(screen.getByRole('button', { name: /Reload Application/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Report to IT Support/i })).toBeInTheDocument();
    });
  });
});

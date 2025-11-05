/**
 * ErrorBoundary - React Error Boundary for fault isolation
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 *
 * Purpose: Catch rendering errors in waveform components to prevent
 * complete dashboard failure from single malformed data packet
 *
 * Medical Safety: Ensures rest of monitoring system continues even if
 * one waveform display fails
 */

import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  componentName?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so next render shows fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log error details for debugging
    console.error('ErrorBoundary caught error:', {
      component: this.props.componentName || 'Unknown',
      error: error.message,
      stack: error.stack,
      componentStack: errorInfo.componentStack
    });

    this.setState({ errorInfo });

    // TODO: Send to monitoring service (Sentry, LogRocket, etc.)
    // Example: Sentry.captureException(error, { extra: errorInfo });
  }

  handleRetry = () => {
    // Reset error state to retry rendering
    this.setState({ hasError: false, error: undefined, errorInfo: undefined });
  };

  render() {
    if (this.state.hasError) {
      // Custom fallback UI provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI for waveform errors
      return (
        <div className="bg-red-50 border-2 border-red-300 rounded-lg p-4 flex flex-col items-center justify-center min-h-[100px]">
          <div className="flex items-center space-x-2 text-red-700 mb-3">
            <AlertTriangle className="w-5 h-5" />
            <h3 className="font-semibold">Waveform Display Error</h3>
          </div>

          <p className="text-sm text-red-600 text-center mb-3">
            Unable to display {this.props.componentName || 'waveform'}.
            <br />
            <span className="font-medium">Patient vitals are still being monitored.</span>
          </p>

          {/* Show error details in development mode */}
          {process.env.NODE_ENV === 'development' && this.state.error && (
            <details className="text-xs text-red-500 mb-3 max-w-full overflow-auto">
              <summary className="cursor-pointer font-medium mb-1">Error Details</summary>
              <pre className="bg-red-100 p-2 rounded whitespace-pre-wrap break-words">
                {this.state.error.message}
                {'\n\n'}
                {this.state.error.stack}
              </pre>
            </details>
          )}

          <button
            onClick={this.handleRetry}
            className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
          >
            Retry Display
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Specialized error boundary for waveform components
 * Provides waveform-specific error messaging
 */
export const WaveformErrorBoundary: React.FC<{
  children: ReactNode;
  waveformType?: 'ECG' | 'EEG' | 'Waveform';
}> = ({ children, waveformType = 'Waveform' }) => {
  return (
    <ErrorBoundary
      componentName={`${waveformType} Display`}
      fallback={
        <div className="bg-gray-900 border-2 border-red-500 rounded-lg p-4 flex flex-col items-center justify-center min-h-[120px]">
          <div className="flex items-center space-x-2 text-red-400 mb-2">
            <AlertTriangle className="w-5 h-5" />
            <h3 className="font-semibold text-white">{waveformType} Display Error</h3>
          </div>

          <p className="text-sm text-gray-300 text-center mb-3">
            Waveform rendering temporarily unavailable.
            <br />
            <span className="text-green-400 font-medium">Vital signs monitoring continues.</span>
          </p>

          <p className="text-xs text-gray-500">
            Click "Full View" to try fullscreen viewer
          </p>
        </div>
      }
    >
      {children}
    </ErrorBoundary>
  );
};

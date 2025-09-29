import React from 'react';
import { CheckCircle, AlertCircle } from 'lucide-react';

interface MessageDisplayProps {
  showSuccess: string | null;
  error: string | null;
}

export const MessageDisplay: React.FC<MessageDisplayProps> = ({
  showSuccess,
  error
}) => {
  if (!showSuccess && !error) return null;

  return (
    <div className="mx-4 mt-4">
      {showSuccess && (
        <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded">
          <CheckCircle className="w-5 h-5 inline mr-2" />
          {showSuccess}
        </div>
      )}
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          <AlertCircle className="w-5 h-5 inline mr-2" />
          {error}
        </div>
      )}
    </div>
  );
};
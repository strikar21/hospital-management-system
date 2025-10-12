/**
 * InvestigationList - List of investigations with empty state
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React from 'react';
import { TestTube } from 'lucide-react';
import { investigation, user } from '../../types';
import { InvestigationItem } from './InvestigationItem';

interface InvestigationListProps {
  investigations: investigation[];
  currentUser: user;
  loadingLabResults: boolean;
  onStart: (investigation: investigation) => void;
  onComplete: (investigation: investigation) => void;
  onCancel: (investigation: investigation) => void;
  onItemClick: (investigation: investigation) => void;
}

export const InvestigationList: React.FC<InvestigationListProps> = ({
  investigations,
  currentUser,
  loadingLabResults,
  onStart,
  onComplete,
  onCancel,
  onItemClick
}) => {
  if (investigations.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        <TestTube className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p>No investigations ordered yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {investigations.filter(inv => inv != null).map((inv) => (
        <InvestigationItem
          key={inv.id}
          investigation={inv}
          currentUser={currentUser}
          loadingLabResults={loadingLabResults}
          onStart={onStart}
          onComplete={onComplete}
          onCancel={onCancel}
          onClick={onItemClick}
        />
      ))}
    </div>
  );
};

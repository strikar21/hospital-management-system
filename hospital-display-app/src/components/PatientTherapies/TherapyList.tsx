/**
 * TherapyList - List of therapies with empty state
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase for data, no kebab-case
 */

import React from 'react';
import { Heart } from 'lucide-react';
import { therapy, user } from '../../types';
import { TherapyItem } from './TherapyItem';

interface TherapyListProps {
  therapies: therapy[];
  currentUser: user;
  onAddSession: (therapy: therapy) => void;
  onComplete: (therapy: therapy) => void;
  onCancel: (therapy: therapy) => void;
}

export const TherapyList: React.FC<TherapyListProps> = ({
  therapies,
  currentUser,
  onAddSession,
  onComplete,
  onCancel
}) => {
  if (therapies.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        <Heart className="w-10 h-10 mx-auto mb-3 opacity-50" />
        <p>No therapy prescribed yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {therapies.filter(therapy => therapy != null).map((therapy) => (
        <TherapyItem
          key={therapy.id}
          therapy={therapy}
          currentUser={currentUser}
          onAddSession={onAddSession}
          onComplete={onComplete}
          onCancel={onCancel}
        />
      ))}
    </div>
  );
};

/**
 * PatientTabs - Patient detail tab navigation component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade tab navigation with role-based access and note counts
 */

import React from 'react';
import {
  UserIcon, Plus, TestTube, Heart, MessageCircle, FileText, AlertTriangle
} from 'lucide-react';
import { noteComment, alert as alertType } from '../../types';

export type TabId = 'overview' | 'medications' | 'investigations' | 'therapy' | 'notes' | 'casesheet' | 'alerts';

interface PatientTabsProps {
  activeTab: TabId;
  onTabChange: (tabId: TabId) => void;
  notes: noteComment[];
  alerts: alertType[];
}

export const PatientTabs: React.FC<PatientTabsProps> = ({
  activeTab,
  onTabChange,
  notes,
  alerts
}) => {

  // Count unacknowledged alerts
  const unacknowledgedCount = alerts.filter(a => !a.acknowledgedBy).length;

  const tabs = [
    { id: 'overview' as const, label: 'Overview', icon: UserIcon },
    { id: 'medications' as const, label: 'Medications', icon: Plus },
    { id: 'investigations' as const, label: 'Investigations', icon: TestTube },
    { id: 'therapy' as const, label: 'Therapy', icon: Heart },
    { id: 'alerts' as const, label: 'Alerts', icon: AlertTriangle },
    { id: 'notes' as const, label: 'Notes', icon: MessageCircle },
    { id: 'casesheet' as const, label: 'Case Sheet', icon: FileText }
  ]; // All tabs visible to all roles - permissions handled within each tab

  return (
    <div className="px-3 bg-gray-50 border-b">
      <div className="flex space-x-1">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={`flex items-center space-x-2 px-3 py-1.5 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === tab.id
                ? 'bg-white text-blue-600 border-t-2 border-blue-600'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            <span>{tab.label}</span>
            {tab.id === 'notes' && notes.length > 0 && (
              <span className="bg-blue-100 text-blue-600 px-1 py-0.5 rounded-full text-xs">
                {notes.length}
              </span>
            )}
            {tab.id === 'alerts' && unacknowledgedCount > 0 && (
              <span className="bg-red-100 text-red-600 px-1 py-0.5 rounded-full text-xs">
                {unacknowledgedCount}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
};
/**
 * IntegrationTypes - External system integration type definitions
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * External system APIs, integrations, and data exchange types
 */

// Integration APIs
export interface externalsystem {
  id: string;
  name: string;
  type: 'lab' | 'pharmacy' | 'imaging' | 'billing' | 'ehr' | 'other';
  endpoint: string;
  authtype: 'apiKey' | 'oauth' | 'basic' | 'certificate';
  status: 'active' | 'inactive' | 'error';
  lastSync?: string;
  version?: string;
}
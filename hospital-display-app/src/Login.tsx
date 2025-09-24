// Login.tsx - Enhanced Login Component

import React from 'react';
import { user as UserType } from './types';
import { HybridLogin } from './HybridLogin';

interface LoginProps {
  onLogin: (user: UserType) => void;
}

// Export HybridLogin as the main Login component
export const Login: React.FC<LoginProps> = ({ onLogin }) => {
  return <HybridLogin onLogin={onLogin} />;
};
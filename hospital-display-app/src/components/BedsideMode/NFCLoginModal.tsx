/**
 * NFCLoginModal - NFC authentication modal component
 * STRICT CAMELCASE ONLY - No snake_case, no PascalCase, no kebab-case
 * Medical-grade NFC authentication modal for secure bedside access
 */

import React from 'react';
import { CreditCard } from 'lucide-react';

interface NFCLoginModalProps {
  showNFCLogin: boolean;
  onNFCScan: () => void;
  onClose: () => void;
}

export const NFCLoginModal: React.FC<NFCLoginModalProps> = ({
  showNFCLogin,
  onNFCScan,
  onClose
}) => {
  if (!showNFCLogin) return null;

  return (
    <div className="absolute inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-gray-800 rounded-lg p-6 max-w-sm w-full mx-4">
        <div className="text-center">
          <CreditCard className="w-16 h-16 text-blue-400 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-white mb-3">NFC Authentication</h3>
          <p className="text-gray-300 mb-6 text-sm">
            Tap NFC card to login
          </p>
          {false ? (
            <div className="flex items-center justify-center space-x-2 text-blue-400">
              <div className="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm">Scanning...</span>
            </div>
          ) : (
            <div className="space-y-3">
              <button
                onClick={onNFCScan}
                className="w-full flex items-center justify-center space-x-2 py-3 px-4 bg-blue-600 text-white rounded hover:bg-blue-700 text-sm"
              >
                <CreditCard className="w-5 h-5" />
                <span>Scan NFC</span>
              </button>
              <button
                onClick={onClose}
                className="w-full py-2 px-4 bg-gray-600 text-white rounded hover:bg-gray-700 text-sm"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
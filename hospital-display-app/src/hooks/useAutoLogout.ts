import { useEffect, useRef, useState } from 'react';
import { appsettings } from '../types';

interface UseAutoLogoutOptions {
  settings: appsettings;
  onLogout: () => void;
  userId: string;
}

export const useAutoLogout = ({ settings, onLogout, userId }: UseAutoLogoutOptions) => {
  const [lastActivity, setLastActivity] = useState(Date.now());
  const autoLogoutTimerRef = useRef<NodeJS.Timeout | null>(null);
  const lastActivityRef = useRef(Date.now());

  // Activity tracking
  useEffect(() => {
    const updateActivity = () => {
      const now = Date.now();
      // Only update if more than 1 second has passed to prevent excessive updates
      if (now - lastActivityRef.current > 1000) {
        lastActivityRef.current = now;
        setLastActivity(now);
      }
    };

    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];

    events.forEach(event => {
      document.addEventListener(event, updateActivity, true);
    });

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, updateActivity, true);
      });
    };
  }, [userId]);

  // Auto-logout timer management
  useEffect(() => {
    if (!settings.enableAutoLogout || settings.bedsideMode) {
      if (autoLogoutTimerRef.current) {
        clearTimeout(autoLogoutTimerRef.current);
        autoLogoutTimerRef.current = null;
      }
      return;
    }

    const checkForAutoLogout = () => {
      const timeSinceLastActivity = Date.now() - lastActivity;
      const autoLogoutTime = (settings.autoLogoutMinutes || 15) * 60 * 1000; // Convert to milliseconds

      if (timeSinceLastActivity >= autoLogoutTime) {
        console.log('🔐 Auto-logout triggered due to inactivity');
        onLogout();
        return;
      }

      // Set timer for next check
      const timeUntilLogout = autoLogoutTime - timeSinceLastActivity;
      autoLogoutTimerRef.current = setTimeout(checkForAutoLogout, Math.min(timeUntilLogout, 60000)); // Check at least every minute
    };

    // Start the auto-logout timer
    if (autoLogoutTimerRef.current) {
      clearTimeout(autoLogoutTimerRef.current);
    }
    autoLogoutTimerRef.current = setTimeout(checkForAutoLogout, 60000); // Check every minute

    return () => {
      if (autoLogoutTimerRef.current) {
        clearTimeout(autoLogoutTimerRef.current);
        autoLogoutTimerRef.current = null;
      }
    };
  }, [settings.enableAutoLogout, settings.bedsideMode, settings.autoLogoutMinutes, lastActivity, onLogout]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (autoLogoutTimerRef.current) {
        clearTimeout(autoLogoutTimerRef.current);
        autoLogoutTimerRef.current = null;
      }
    };
  }, []);

  return {
    lastActivity,
    timeUntilAutoLogout: settings.enableAutoLogout && !settings.bedsideMode
      ? Math.max(0, ((settings.autoLogoutMinutes || 15) * 60 * 1000) - (Date.now() - lastActivity))
      : null
  };
};
/**
 * Relative time formatting.
 */

export function formatRelative(date: Date): string {
  /**
   * Format Date as relative time ("2m ago", "5h ago").
   *
   * @param date - Date object
   * @returns Relative time string
   *
   * @example
   * formatRelative(new Date(Date.now() - 300000)) // "5m ago"
   */
  const now = Date.now();
  const then = date.getTime();
  const diffMs = now - then;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;

  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays}d ago`;
}

export function isRecent(date: Date, maxAgeMs: number): boolean {
  /**
   * Check if date is within max age.
   *
   * @param date - Date to check
   * @param maxAgeMs - Maximum age in milliseconds
   * @returns True if date is recent
   *
   * @example
   * isRecent(new Date(), 300000) // true if within 5 minutes
   */
  return (Date.now() - date.getTime()) < maxAgeMs;
}

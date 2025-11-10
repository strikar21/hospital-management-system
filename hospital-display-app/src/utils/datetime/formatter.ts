/**
 * Format Date objects to strings.
 */

export function formatISO(date: Date): string {
  /**
   * Format Date to ISO8601 string.
   *
   * @param date - Date object
   * @returns ISO8601 string
   *
   * @example
   * formatISO(new Date()) // "2025-11-10T14:30:00.000Z"
   */
  return date.toISOString();
}

export function formatMedical(date: Date): string {
  /**
   * Format Date for medical records (24-hour format).
   *
   * @param date - Date object
   * @returns Medical format: "2025-11-10 14:30:00 UTC"
   *
   * @example
   * formatMedical(new Date()) // "2025-11-10 14:30:00 UTC"
   */
  const year = date.getUTCFullYear();
  const month = String(date.getUTCMonth() + 1).padStart(2, '0');
  const day = String(date.getUTCDate()).padStart(2, '0');
  const hours = String(date.getUTCHours()).padStart(2, '0');
  const minutes = String(date.getUTCMinutes()).padStart(2, '0');
  const seconds = String(date.getUTCSeconds()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds} UTC`;
}

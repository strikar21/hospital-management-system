/**
 * Parse timestamp strings to Date objects.
 */

export function parseISO(isoString: string): Date {
  /**
   * Parse ISO8601 string to Date object.
   *
   * @param isoString - ISO8601 formatted string
   * @returns Date object
   *
   * @example
   * parseISO("2025-11-10T14:30:00Z")
   */
  return new Date(isoString);
}

export function parseTimestamp(value: string | number | Date): Date {
  /**
   * Parse various timestamp formats to Date.
   *
   * @param value - ISO string, Unix epoch, or Date object
   * @returns Date object
   *
   * @example
   * parseTimestamp("2025-11-10T14:30:00Z")
   * parseTimestamp(1699627800)
   * parseTimestamp(new Date())
   */
  if (value instanceof Date) {
    return value;
  }

  if (typeof value === 'string') {
    return parseISO(value);
  }

  if (typeof value === 'number') {
    return new Date(value * 1000); // Assume Unix epoch in seconds
  }

  throw new Error(`Cannot parse timestamp from type ${typeof value}`);
}

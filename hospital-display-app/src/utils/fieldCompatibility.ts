/**
 * Field Compatibility Layer
 * Maps old backend field names to new frontend field names
 * Prevents crashes during transition period
 */

export function mapLegacyFields(data: any): any {
  if (!data || typeof data !== 'object') return data;

  // Handle arrays
  if (Array.isArray(data)) {
    return data.map(mapLegacyFields);
  }

  const mapped = { ...data };

  // Map old performer fields to performedBy
  if (data.acknowledgedBy && !mapped.performedBy) {
    mapped.performedBy = data.acknowledgedBy;
  }
  if (data.acknowledgedByName && !mapped.performedByName) {
    mapped.performedByName = data.acknowledgedByName;
  }
  if (data.acknowledgedByRole && !mapped.performedByRole) {
    mapped.performedByRole = data.acknowledgedByRole;
  }
  if (data.prescribedBy && !mapped.performedBy) {
    mapped.performedBy = data.prescribedBy;
  }
  if (data.orderedBy && !mapped.performedBy) {
    mapped.performedBy = data.orderedBy;
  }
  if (data.verifiedBy && !mapped.performedBy) {
    mapped.performedBy = data.verifiedBy;
  }

  // Map old timestamp fields to new ones
  if (data.acknowledgedAt && !mapped.completedAt) {
    mapped.completedAt = data.acknowledgedAt;
  }
  if (data.prescribedAt && !mapped.createdAt) {
    mapped.createdAt = data.prescribedAt;
  }
  if (data.orderedDate && !mapped.createdAt) {
    mapped.createdAt = data.orderedDate;
  }

  // Recursively map nested objects
  Object.keys(mapped).forEach(key => {
    if (mapped[key] && typeof mapped[key] === 'object') {
      mapped[key] = mapLegacyFields(mapped[key]);
    }
  });

  return mapped;
}

export function mapApiResponse(response: any): any {
  return mapLegacyFields(response);
}
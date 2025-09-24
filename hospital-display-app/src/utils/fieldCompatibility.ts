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

  // Map old performer fields to lowercase performedby
  if (data.acknowledgedby && !mapped.performedby) {
    mapped.performedby = data.acknowledgedby;
  }
  if (data.acknowledgedbyname && !mapped.performedbyname) {
    mapped.performedbyname = data.acknowledgedbyname;
  }
  if (data.acknowledgedbyrole && !mapped.performedbyrole) {
    mapped.performedbyrole = data.acknowledgedbyrole;
  }
  if (data.prescribedby && !mapped.performedby) {
    mapped.performedby = data.prescribedby;
  }
  if (data.orderedby && !mapped.performedby) {
    mapped.performedby = data.orderedby;
  }
  if (data.verifiedby && !mapped.performedby) {
    mapped.performedby = data.verifiedby;
  }

  // Map old timestamp fields to lowercase
  if (data.acknowledgedat && !mapped.completedat) {
    mapped.completedat = data.acknowledgedat;
  }
  if (data.prescribedat && !mapped.createdat) {
    mapped.createdat = data.prescribedat;
  }
  if (data.ordereddate && !mapped.createdat) {
    mapped.createdat = data.ordereddate;
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
export function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

export function getRecord(
  record: Record<string, unknown> | null,
  key: string,
): Record<string, unknown> | null {
  return record ? asRecord(record[key]) : null;
}

export function getNumber(
  record: Record<string, unknown> | null,
  key: string,
): number | null {
  if (!record) {
    return null;
  }

  const value = record[key];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function getString(
  record: Record<string, unknown> | null,
  key: string,
): string | null {
  if (!record) {
    return null;
  }

  const value = record[key];
  return typeof value === "string" ? value : null;
}

export function getBoolean(
  record: Record<string, unknown> | null,
  key: string,
): boolean | null {
  if (!record) {
    return null;
  }

  const value = record[key];
  return typeof value === "boolean" ? value : null;
}

export function getNumberArray(
  record: Record<string, unknown> | null,
  key: string,
): number[] {
  if (!record) {
    return [];
  }

  const value = record[key];
  return Array.isArray(value)
    ? value.filter((item): item is number => typeof item === "number")
    : [];
}

export function getStringArray(
  record: Record<string, unknown> | null,
  key: string,
): string[] {
  if (!record) {
    return [];
  }

  const value = record[key];
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

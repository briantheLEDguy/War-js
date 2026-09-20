import { createHash } from 'node:crypto';

export const CONTENT_SCHEMA_VERSION = 1 as const;

/** The archive keeps source transforms. Only consumers explicitly convert to engine space. */
export const COORDINATE_CONTRACT = {
  source: { lengthUnit: 'meter', upAxis: '+Y', characterForwardAxis: '+Z', rightAxis: '+X', angleUnit: 'radian' },
  unreal: { lengthUnit: 'centimeter', upAxis: '+Z', characterForwardAxis: '+X', rightAxis: '+Y', angleUnit: 'degree' },
  position: { X: 'source.z * 100', Y: 'source.x * 100', Z: 'source.y * 100' },
  yaw: 'source.rotY * 180 / PI',
  scale: { X: 'source.z', Y: 'source.x', Z: 'source.y' },
  canonicalPayload: 'All map, model, collision, terrain and animation data remain in source coordinates; never infer conversion from field names.',
  fullRotation: 'Only Y-axis yaw is covered by the helper. Convert arbitrary rotations with the same basis matrix, not by renaming Euler components. Imported mesh/skeleton bind transforms require a separate verified asset import.',
} as const;

export interface SourcePoint { x: number; y: number; z: number }
export interface UnrealPoint { X: number; Y: number; Z: number }

export function sourcePointToUnreal(point: SourcePoint): UnrealPoint {
  assertJsonSerializable(point);
  if (![point.x, point.y, point.z].every(value => typeof value === 'number' && Number.isFinite(value))) {
    throw new Error('A source point requires finite x, y and z coordinates.');
  }
  const converted = { X: point.z * 100, Y: point.x * 100, Z: point.y * 100 };
  assertJsonSerializable(converted);
  return converted;
}

export function sourceYawToUnrealDegrees(radians: number): number {
  if (!Number.isFinite(radians)) throw new Error('Source yaw must be finite.');
  const degrees = radians * (180 / Math.PI);
  if (!Number.isFinite(degrees)) throw new Error('Converted yaw must be finite.');
  return degrees;
}

/** Optional object fields may be undefined; unsupported values must never silently become null. */
export function assertJsonSerializable(value: unknown, path = '$', ancestors = new Set<object>()): void {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) throw new Error(`Non-finite number at ${path}`);
    return;
  }
  if (typeof value !== 'object') throw new Error(`Non-JSON value at ${path}: ${typeof value}`);
  if (ancestors.has(value)) throw new Error(`Circular value at ${path}`);
  if (!Array.isArray(value) && Object.getPrototypeOf(value) !== Object.prototype && Object.getPrototypeOf(value) !== null) {
    throw new Error(`Non-plain object at ${path}`);
  }
  if (Object.getOwnPropertySymbols(value).length) throw new Error(`Symbol keys at ${path}`);
  ancestors.add(value);
  if (Array.isArray(value)) {
    for (let index = 0; index < value.length; index++) assertJsonSerializable(value[index], `${path}[${index}]`, ancestors);
  } else {
    for (const [key, entry] of Object.entries(value)) {
      if (entry !== undefined) assertJsonSerializable(entry, `${path}.${key}`, ancestors);
    }
  }
  ancestors.delete(value);
}

export function canonicalJson(value: unknown): string {
  assertJsonSerializable(value);
  return `${JSON.stringify(sortObjectKeys(value), null, 2)}\n`;
}

function sortObjectKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortObjectKeys);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)
      .filter(([, entry]) => entry !== undefined).map(([key, entry]) => [key, sortObjectKeys(entry)]));
  }
  return value;
}

export function sha256(value: string | Buffer): string {
  return createHash('sha256').update(value).digest('hex');
}

export function requireUniqueIds<T>(values: readonly T[], key: (value: T) => string, label: string): Set<string> {
  const ids = new Set<string>();
  for (const value of values) {
    const id = key(value);
    if (typeof id !== 'string' || !id.trim()) throw new Error(`Missing ${label} ID`);
    if (ids.has(id)) throw new Error(`Duplicate ${label} ID: ${id}`);
    ids.add(id);
  }
  return ids;
}

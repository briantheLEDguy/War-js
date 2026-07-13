import type {
  VoxelTerrainChunk,
  WorldEditDocument,
  WorldObject,
  WorldTransform,
} from '../services/types';

export interface WorldEditValidationOptions {
  zoneSize?: number;
}

export interface WorldEditValidationResult {
  valid: boolean;
  issues: string[];
}

const MAX_OBJECTS = 5000;
const MAX_CHUNKS = 4096;
const MAX_CHUNK_CELLS = 16 * 16 * 32;
const MAX_REASONABLE_SCALE = 100;
const MODEL_NAME_RE = /^[a-z0-9_\-./]+\.glb$/i;

export const DEFAULT_VOXEL_PALETTE = {
  schemaVersion: 1,
  materials: [
    { id: 'grass', label: 'Grass', color: '#4f7d37' },
    { id: 'dirt', label: 'Dirt', color: '#6b4b2f' },
    { id: 'cobblestone', label: 'Cobblestone', color: '#77736a' },
    { id: 'stone', label: 'Stone', color: '#85817a' },
    { id: 'wood', label: 'Wood', color: '#76512d' },
    { id: 'water', label: 'Water', color: '#3f7da8' },
  ],
};

export function createEmptyWorldEditDocument(
  zoneId: string,
  status: WorldEditDocument['status'],
  seed?: Partial<WorldEditDocument>,
): WorldEditDocument {
  const now = Date.now();
  return {
    schemaVersion: 1,
    versionId: seed?.versionId ?? makeVersionId(status),
    zoneId,
    status,
    parentVersionId: seed?.parentVersionId,
    authorUserId: seed?.authorUserId,
    authorEmail: seed?.authorEmail,
    notes: seed?.notes,
    createdAt: seed?.createdAt ?? now,
    updatedAt: now,
    publishedAt: status === 'published' ? (seed?.publishedAt ?? now) : seed?.publishedAt,
    palette: seed?.palette ?? DEFAULT_VOXEL_PALETTE,
    objects: seed?.objects ? cloneJson(seed.objects) : [],
    voxelChunks: seed?.voxelChunks ? cloneJson(seed.voxelChunks) : [],
  };
}

export function cloneWorldEditDocument(
  doc: WorldEditDocument,
  patch?: Partial<WorldEditDocument>,
): WorldEditDocument {
  return {
    ...cloneJson(doc),
    ...patch,
    palette: patch?.palette ?? cloneJson(doc.palette),
    objects: patch?.objects ? cloneJson(patch.objects) : cloneJson(doc.objects),
    voxelChunks: patch?.voxelChunks ? cloneJson(patch.voxelChunks) : cloneJson(doc.voxelChunks),
  };
}

export function summarizeWorldEditVersion(doc: WorldEditDocument) {
  return {
    versionId: doc.versionId,
    zoneId: doc.zoneId,
    status: doc.status,
    parentVersionId: doc.parentVersionId,
    notes: doc.notes,
    authorUserId: doc.authorUserId,
    authorEmail: doc.authorEmail,
    createdAt: doc.createdAt,
    updatedAt: doc.updatedAt,
    publishedAt: doc.publishedAt,
    objectCount: doc.objects.length,
    chunkCount: doc.voxelChunks.length,
  };
}

export function makeVersionId(status: WorldEditDocument['status']): string {
  const rand = Math.random().toString(36).slice(2, 10);
  return `${status}-${Date.now().toString(36)}-${rand}`;
}

export function validateWorldEditDocument(
  doc: WorldEditDocument,
  options: WorldEditValidationOptions = {},
): WorldEditValidationResult {
  const issues: string[] = [];

  if (doc.schemaVersion !== 1) issues.push(`Unsupported world edit schemaVersion ${doc.schemaVersion}.`);
  if (!doc.zoneId) issues.push('World edit document is missing zoneId.');
  if (doc.status !== 'draft' && doc.status !== 'published') issues.push(`Invalid status "${doc.status}".`);
  if (doc.objects.length > MAX_OBJECTS) issues.push(`Too many world objects: ${doc.objects.length}.`);
  if (doc.voxelChunks.length > MAX_CHUNKS) issues.push(`Too many voxel chunks: ${doc.voxelChunks.length}.`);

  const objectIds = new Set<string>();
  for (const object of doc.objects) {
    validateWorldObject(object, objectIds, issues, options);
  }

  const chunkKeys = new Set<string>();
  for (const chunk of doc.voxelChunks) {
    validateVoxelChunk(chunk, chunkKeys, issues, options);
  }

  return { valid: issues.length === 0, issues };
}

function validateWorldObject(
  object: WorldObject,
  objectIds: Set<string>,
  issues: string[],
  options: WorldEditValidationOptions,
): void {
  if (!object.id) {
    issues.push('World object is missing id.');
  } else if (objectIds.has(object.id)) {
    issues.push(`Duplicate world object id "${object.id}".`);
  } else {
    objectIds.add(object.id);
  }

  validateTransform(object.id || object.type, object.transform, issues, options);

  if (object.type === 'prop') {
    if (!object.kind) issues.push(`Prop "${object.id}" is missing kind.`);
    if (object.model && !MODEL_NAME_RE.test(object.model)) {
      issues.push(`Prop "${object.id}" has unsafe model name "${object.model}".`);
    }
    if (object.interaction) {
      if (!object.interaction.id) issues.push(`Prop "${object.id}" has an interaction without an id.`);
      if (object.interaction.type !== 'gate') {
        issues.push(`Prop "${object.id}" has unsupported interaction type "${object.interaction.type}".`);
      }
      if (
        object.interaction.maxDistance !== undefined &&
        !isPositiveFinite(object.interaction.maxDistance)
      ) {
        issues.push(`Prop "${object.id}" has an invalid interaction maxDistance.`);
      }
    }
    for (const collider of object.colliders ?? []) {
      if (!isPositiveFinite(collider.width) || !isPositiveFinite(collider.depth)) {
        issues.push(`Prop "${object.id}" has an invalid collider size.`);
      }
      validateColliderVerticalBounds(`Prop "${object.id}"`, collider, issues);
      if (collider.blocksWhen && collider.blocksWhen !== 'always' && collider.blocksWhen !== 'closed') {
        issues.push(`Prop "${object.id}" has unsupported collider blocksWhen "${collider.blocksWhen}".`);
      }
      if (collider.blocksWhen === 'closed' && !collider.interactionId) {
        issues.push(`Prop "${object.id}" has a closed-only collider without an interactionId.`);
      }
    }
    for (const surface of object.walkableSurfaces ?? []) {
      if (!isPositiveFinite(surface.width) || !isPositiveFinite(surface.depth)) {
        issues.push(`Prop "${object.id}" has an invalid walkable surface size.`);
      }
      if (!Number.isFinite(surface.fromY ?? 0) || !Number.isFinite(surface.toY ?? 0)) {
        issues.push(`Prop "${object.id}" has an invalid walkable surface height.`);
      }
    }
  }

  if (object.type === 'collider') {
    if (!isPositiveFinite(object.width) || !isPositiveFinite(object.depth)) {
      issues.push(`Collider "${object.id}" has an invalid size.`);
    }
    validateColliderVerticalBounds(`Collider "${object.id}"`, object, issues);
  }

  if (object.type === 'walkableSurface') {
    if (!isPositiveFinite(object.width) || !isPositiveFinite(object.depth)) {
      issues.push(`Walkable surface "${object.id}" has an invalid size.`);
    }
    if (!Number.isFinite(object.fromY) || !Number.isFinite(object.toY)) {
      issues.push(`Walkable surface "${object.id}" has invalid heights.`);
    }
  }
}

function validateColliderVerticalBounds(
  label: string,
  collider: { minY?: number; maxY?: number },
  issues: string[],
): void {
  if (collider.minY !== undefined && !Number.isFinite(collider.minY)) {
    issues.push(`${label} has an invalid collider minY.`);
  }
  if (collider.maxY !== undefined && !Number.isFinite(collider.maxY)) {
    issues.push(`${label} has an invalid collider maxY.`);
  }
  if (
    collider.minY !== undefined &&
    collider.maxY !== undefined &&
    Number.isFinite(collider.minY) &&
    Number.isFinite(collider.maxY) &&
    collider.minY > collider.maxY
  ) {
    issues.push(`${label} has collider minY greater than maxY.`);
  }
}

function validateTransform(
  label: string,
  transform: WorldTransform,
  issues: string[],
  options: WorldEditValidationOptions,
): void {
  for (const [axis, value] of Object.entries(transform.position)) {
    if (!Number.isFinite(value)) issues.push(`${label} has non-finite position.${axis}.`);
    const half = (options.zoneSize ?? 10000) * 0.5;
    if (Math.abs(value) > half + 500) issues.push(`${label} position.${axis} is outside the editable bounds.`);
  }
  for (const [axis, value] of Object.entries(transform.rotation)) {
    if (!Number.isFinite(value)) issues.push(`${label} has non-finite rotation.${axis}.`);
  }
  for (const [axis, value] of Object.entries(transform.scale)) {
    if (!isPositiveFinite(value) || value > MAX_REASONABLE_SCALE) {
      issues.push(`${label} has invalid scale.${axis}.`);
    }
  }
}

function validateVoxelChunk(
  chunk: VoxelTerrainChunk,
  chunkKeys: Set<string>,
  issues: string[],
  options: WorldEditValidationOptions,
): void {
  if (!chunk.key) {
    issues.push('Voxel chunk is missing key.');
  } else if (chunkKeys.has(chunk.key)) {
    issues.push(`Duplicate voxel chunk key "${chunk.key}".`);
  } else {
    chunkKeys.add(chunk.key);
  }

  if (!isPositiveFinite(chunk.size) || chunk.size > 64) {
    issues.push(`Voxel chunk "${chunk.key}" has invalid size.`);
  }
  if (!isPositiveFinite(chunk.voxelSize) || chunk.voxelSize > 8) {
    issues.push(`Voxel chunk "${chunk.key}" has invalid voxelSize.`);
  }

  const half = (options.zoneSize ?? 10000) * 0.5;
  if (Math.abs(chunk.origin.x) > half + 500 || Math.abs(chunk.origin.z) > half + 500) {
    issues.push(`Voxel chunk "${chunk.key}" origin is outside editable bounds.`);
  }

  const cells = Object.entries(chunk.cells);
  if (cells.length > MAX_CHUNK_CELLS) issues.push(`Voxel chunk "${chunk.key}" has too many cells.`);

  for (const [key, cell] of cells) {
    const parts = key.split(':').map((part) => Number.parseInt(part, 10));
    if (parts.length !== 3 || parts.some((part) => !Number.isInteger(part))) {
      issues.push(`Voxel chunk "${chunk.key}" has invalid cell key "${key}".`);
      continue;
    }
    if (parts.some((part) => part < 0 || part >= chunk.size)) {
      issues.push(`Voxel chunk "${chunk.key}" cell "${key}" is outside chunk bounds.`);
    }
    if (!Number.isFinite(cell.density) || cell.density < 0 || cell.density > 1) {
      issues.push(`Voxel chunk "${chunk.key}" cell "${key}" has invalid density.`);
    }
    if (!cell.material) issues.push(`Voxel chunk "${chunk.key}" cell "${key}" is missing material.`);
  }
}

function isPositiveFinite(value: number): boolean {
  return Number.isFinite(value) && value > 0;
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

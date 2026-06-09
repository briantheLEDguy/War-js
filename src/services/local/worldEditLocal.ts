import type {
  WorldEditDocument,
  WorldEditPatch,
  WorldEditService,
  WorldEditVersionSummary,
} from '../types';
import {
  cloneWorldEditDocument,
  createEmptyWorldEditDocument,
  makeVersionId,
  summarizeWorldEditVersion,
  validateWorldEditDocument,
} from '../../world/WorldEditValidation';

interface StoredDocument extends WorldEditDocument {
  storageKey: string;
}

const DB_NAME = 'war-js-world-edits';
const DB_VERSION = 1;
const STORE = 'documents';

export class WorldEditLocal implements WorldEditService {
  private memory = new Map<string, StoredDocument>();
  private dbPromise: Promise<IDBDatabase | null> | null = null;

  async getPublished(zoneId: string): Promise<WorldEditDocument | null> {
    return stripStorageKey(await this.getStored(publishedKey(zoneId)));
  }

  async getDraft(zoneId: string): Promise<WorldEditDocument | null> {
    return stripStorageKey(await this.getStored(draftKey(zoneId)));
  }

  async saveDraft(zoneId: string, patch: WorldEditPatch): Promise<WorldEditDocument> {
    const existing = await this.getDraft(zoneId);
    const base = existing ?? createEmptyWorldEditDocument(zoneId, 'draft');
    const now = Date.now();
    const next = patch.replaceDocument
      ? cloneWorldEditDocument(patch.replaceDocument, {
          zoneId,
          status: 'draft',
          updatedAt: now,
          publishedAt: undefined,
        })
      : applyPatch(base, patch, now);

    next.zoneId = zoneId;
    next.status = 'draft';
    next.updatedAt = now;
    next.publishedAt = undefined;

    const validation = validateWorldEditDocument(next);
    if (!validation.valid) {
      throw new Error(`Invalid world edit draft: ${validation.issues.join(' ')}`);
    }

    await this.putStored(draftKey(zoneId), next);
    return next;
  }

  async publishDraft(zoneId: string, notes: string): Promise<WorldEditDocument> {
    const draft = await this.getDraft(zoneId);
    if (!draft) throw new Error(`No draft world edit exists for zone "${zoneId}".`);

    const validation = validateWorldEditDocument(draft);
    if (!validation.valid) {
      throw new Error(`Cannot publish invalid world edit: ${validation.issues.join(' ')}`);
    }

    const now = Date.now();
    const published = cloneWorldEditDocument(draft, {
      versionId: makeVersionId('published'),
      status: 'published',
      notes: notes.trim() || draft.notes || 'Published GM world edits',
      updatedAt: now,
      publishedAt: now,
    });

    await this.putStored(publishedKey(zoneId), published);
    await this.putStored(versionKey(zoneId, published.versionId), published);

    const nextDraft = cloneWorldEditDocument(published, {
      versionId: makeVersionId('draft'),
      status: 'draft',
      parentVersionId: published.versionId,
      publishedAt: undefined,
      updatedAt: now,
    });
    await this.putStored(draftKey(zoneId), nextDraft);

    return published;
  }

  async listVersions(zoneId: string): Promise<WorldEditVersionSummary[]> {
    const all = await this.getAllStored();
    return all
      .filter((doc) => doc.zoneId === zoneId)
      .filter((doc) => doc.storageKey.startsWith(`version:${zoneId}:`) || doc.storageKey === publishedKey(zoneId))
      .map((doc) => summarizeWorldEditVersion(doc))
      .sort((a, b) => (b.publishedAt ?? b.updatedAt) - (a.publishedAt ?? a.updatedAt));
  }

  async restoreVersion(zoneId: string, versionId: string): Promise<WorldEditDocument> {
    const stored = await this.getStored(versionKey(zoneId, versionId));
    if (!stored) throw new Error(`World edit version "${versionId}" was not found for zone "${zoneId}".`);

    const draft = cloneWorldEditDocument(stored, {
      versionId: makeVersionId('draft'),
      status: 'draft',
      parentVersionId: stored.versionId,
      publishedAt: undefined,
      updatedAt: Date.now(),
    });
    await this.putStored(draftKey(zoneId), draft);
    return draft;
  }

  private async db(): Promise<IDBDatabase | null> {
    if (typeof indexedDB === 'undefined') return null;
    if (this.dbPromise) return this.dbPromise;
    this.dbPromise = new Promise((resolve) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);
      request.onupgradeneeded = () => {
        const db = request.result;
        if (!db.objectStoreNames.contains(STORE)) {
          db.createObjectStore(STORE, { keyPath: 'storageKey' });
        }
      };
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => {
        console.warn('[WorldEditLocal] IndexedDB unavailable, using in-memory world edits.', request.error);
        resolve(null);
      };
    });
    return this.dbPromise;
  }

  private async getStored(key: string): Promise<StoredDocument | null> {
    const db = await this.db();
    if (!db) return this.memory.get(key) ?? null;
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const request = tx.objectStore(STORE).get(key);
      request.onsuccess = () => resolve((request.result as StoredDocument | undefined) ?? null);
      request.onerror = () => reject(request.error);
    });
  }

  private async getAllStored(): Promise<StoredDocument[]> {
    const db = await this.db();
    if (!db) return Array.from(this.memory.values());
    return new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const request = tx.objectStore(STORE).getAll();
      request.onsuccess = () => resolve(request.result as StoredDocument[]);
      request.onerror = () => reject(request.error);
    });
  }

  private async putStored(key: string, doc: WorldEditDocument): Promise<void> {
    const stored: StoredDocument = { ...cloneWorldEditDocument(doc), storageKey: key };
    const db = await this.db();
    if (!db) {
      this.memory.set(key, stored);
      return;
    }
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put(stored);
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  }
}

function applyPatch(base: WorldEditDocument, patch: WorldEditPatch, updatedAt: number): WorldEditDocument {
  const next = cloneWorldEditDocument(base, { updatedAt });

  if (patch.notes !== undefined) next.notes = patch.notes;

  if (patch.upsertObjects?.length) {
    const byId = new Map(next.objects.map((object) => [object.id, object]));
    for (const object of patch.upsertObjects) byId.set(object.id, object);
    next.objects = Array.from(byId.values());
  }

  if (patch.removeObjectIds?.length) {
    const remove = new Set(patch.removeObjectIds);
    next.objects = next.objects.filter((object) => !remove.has(object.id));
  }

  if (patch.upsertVoxelChunks?.length) {
    const byKey = new Map(next.voxelChunks.map((chunk) => [chunk.key, chunk]));
    for (const chunk of patch.upsertVoxelChunks) byKey.set(chunk.key, chunk);
    next.voxelChunks = Array.from(byKey.values()).filter((chunk) => Object.keys(chunk.cells).length > 0);
  }

  if (patch.removeVoxelChunkKeys?.length) {
    const remove = new Set(patch.removeVoxelChunkKeys);
    next.voxelChunks = next.voxelChunks.filter((chunk) => !remove.has(chunk.key));
  }

  return next;
}

function draftKey(zoneId: string): string {
  return `draft:${zoneId}`;
}

function publishedKey(zoneId: string): string {
  return `published:${zoneId}`;
}

function versionKey(zoneId: string, versionId: string): string {
  return `version:${zoneId}:${versionId}`;
}

function stripStorageKey(doc: StoredDocument | null): WorldEditDocument | null {
  if (!doc) return null;
  const { storageKey: _storageKey, ...rest } = doc;
  return rest;
}

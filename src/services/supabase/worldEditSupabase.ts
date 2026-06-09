import type {
  WorldEditDocument,
  WorldEditPatch,
  WorldEditService,
  WorldEditVersionSummary,
} from '../types';
import { NotImplementedError } from '../types';

/**
 * TODO(phase2): Wire Supabase world-edit persistence.
 *
 * Suggested tables:
 *   - world_edit_versions(zone_id, version_id, status, notes, author_user_id,
 *     author_email, parent_version_id, created_at, updated_at, published_at)
 *   - world_edit_objects(version_id, object_id, object jsonb)
 *   - world_edit_chunks(version_id, chunk_key, chunk jsonb)
 *   - gm_user_roles(user_id, email, role)
 *
 * Enable RLS on every table. Allow SELECT for published versions, allow
 * draft/publish writes only for users with a GM/admin role.
 */
export class WorldEditSupabase implements WorldEditService {
  getPublished(_zoneId: string): Promise<WorldEditDocument | null> {
    throw new NotImplementedError('WorldEditSupabase.getPublished');
  }

  getDraft(_zoneId: string): Promise<WorldEditDocument | null> {
    throw new NotImplementedError('WorldEditSupabase.getDraft');
  }

  saveDraft(_zoneId: string, _patch: WorldEditPatch): Promise<WorldEditDocument> {
    throw new NotImplementedError('WorldEditSupabase.saveDraft');
  }

  publishDraft(_zoneId: string, _notes: string): Promise<WorldEditDocument> {
    throw new NotImplementedError('WorldEditSupabase.publishDraft');
  }

  listVersions(_zoneId: string): Promise<WorldEditVersionSummary[]> {
    throw new NotImplementedError('WorldEditSupabase.listVersions');
  }

  restoreVersion(_zoneId: string, _versionId: string): Promise<WorldEditDocument> {
    throw new NotImplementedError('WorldEditSupabase.restoreVersion');
  }
}

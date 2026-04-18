import type { QuestProgress, QuestService } from '../types';
import { NotImplementedError } from '../types';

/**
 * TODO(phase2): Wire Supabase `quest_progress` table.
 *   - list:   select * where character_id = $ order by quest_id
 *   - update: upsert rows with (character_id, quest_id) conflict target
 */
export class QuestSupabase implements QuestService {
  list(_characterId: string): Promise<QuestProgress[]> {
    throw new NotImplementedError('QuestSupabase.list');
  }
  update(_characterId: string, _progress: QuestProgress[]): Promise<void> {
    throw new NotImplementedError('QuestSupabase.update');
  }
}

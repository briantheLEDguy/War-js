import type { CraftingService, CraftingState } from '../types';
import { NotImplementedError } from '../types';

/**
 * TODO(phase2): Wire Supabase crafting persistence.
 *   - get:    select profession rows and cultivation slots by character_id
 *   - update: upsert professions and active cultivation slots transactionally
 */
export class CraftingSupabase implements CraftingService {
  get(_characterId: string): Promise<CraftingState> {
    throw new NotImplementedError('CraftingSupabase.get');
  }

  update(_characterId: string, _state: CraftingState): Promise<void> {
    throw new NotImplementedError('CraftingSupabase.update');
  }
}

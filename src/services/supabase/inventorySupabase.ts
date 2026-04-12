import type { InventoryItem, InventoryService } from '../types';
import { NotImplementedError } from '../types';

/**
 * TODO(phase2): Wire Supabase `inventory_items` table.
 *   - get:    select * where character_id = $ order by slot
 *   - update: upsert rows with (character_id, slot) conflict target
 */
export class InventorySupabase implements InventoryService {
  get(_characterId: string): Promise<InventoryItem[]> {
    throw new NotImplementedError('InventorySupabase.get');
  }
  update(_characterId: string, _items: InventoryItem[]): Promise<void> {
    throw new NotImplementedError('InventorySupabase.update');
  }
}

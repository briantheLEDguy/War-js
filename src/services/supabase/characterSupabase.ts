import type {
  CharacterService,
  CharacterState,
  CharacterSummary,
} from '../types';
import { NotImplementedError } from '../types';

/**
 * TODO(phase2): Wire Supabase `characters` table.
 *   - list:   select id,name,class,race,level,zone_id where user_id = $
 *   - create: insert row, return summary
 *   - load:   select * where id = $
 *   - save:   update row; consider RPC for atomic xp/level-up logic
 *   - findByName: GM-only exact lower(name) lookup across characters
 */
export class CharacterSupabase implements CharacterService {
  list(_userId: string): Promise<CharacterSummary[]> {
    throw new NotImplementedError('CharacterSupabase.list');
  }
  create(
    _userId: string,
    _data: Omit<CharacterSummary, 'id' | 'level' | 'zoneId'>,
  ): Promise<CharacterSummary> {
    throw new NotImplementedError('CharacterSupabase.create');
  }
  load(_characterId: string): Promise<CharacterState> {
    throw new NotImplementedError('CharacterSupabase.load');
  }
  save(_characterId: string, _state: Partial<CharacterState>): Promise<void> {
    throw new NotImplementedError('CharacterSupabase.save');
  }
  findByName(_name: string): Promise<CharacterState[]> {
    throw new NotImplementedError('CharacterSupabase.findByName');
  }
}

import { supabaseEnabled } from '../config/env';
import { AuthLocal } from './local/authLocal';
import { CharacterLocal } from './local/characterLocal';
import { ChatLocal } from './local/chatLocal';
import { InventoryLocal } from './local/inventoryLocal';
import { WorldLocal } from './local/worldLocal';
import { AuthSupabase } from './supabase/authSupabase';
import { CharacterSupabase } from './supabase/characterSupabase';
import { ChatSupabase } from './supabase/chatSupabase';
import { InventorySupabase } from './supabase/inventorySupabase';
import { WorldSupabase } from './supabase/worldSupabase';
import type { Services } from './types';

function build(): Services {
  if (supabaseEnabled()) {
    console.info('[services] Supabase env detected \u2014 using supabase backend (stubbed; see src/services/supabase/*)');
    return {
      auth: new AuthSupabase(),
      characters: new CharacterSupabase(),
      inventory: new InventorySupabase(),
      chat: new ChatSupabase(),
      world: new WorldSupabase(),
      backend: 'supabase',
    };
  }
  console.info('[services] Using local in-memory backend. Set VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY to switch.');
  return {
    auth: new AuthLocal(),
    characters: new CharacterLocal(),
    inventory: new InventoryLocal(),
    chat: new ChatLocal(),
    world: new WorldLocal(),
    backend: 'local',
  };
}

export const services: Services = build();
export type { Services } from './types';

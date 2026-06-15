import { supabaseEnabled } from '../config/env';
import { AuthLocal } from './local/authLocal';
import { CharacterLocal } from './local/characterLocal';
import { ChatLocal } from './local/chatLocal';
import { CampaignLocal } from './local/campaignLocal';
import { CraftingLocal } from './local/craftingLocal';
import { InventoryLocal } from './local/inventoryLocal';
import { QuestLocal } from './local/questLocal';
import { WorldEditLocal } from './local/worldEditLocal';
import { WorldLocal } from './local/worldLocal';
import { AuthSupabase } from './supabase/authSupabase';
import { CharacterSupabase } from './supabase/characterSupabase';
import { ChatSupabase } from './supabase/chatSupabase';
import { CampaignSupabase } from './supabase/campaignSupabase';
import { CraftingSupabase } from './supabase/craftingSupabase';
import { InventorySupabase } from './supabase/inventorySupabase';
import { QuestSupabase } from './supabase/questSupabase';
import { WorldEditSupabase } from './supabase/worldEditSupabase';
import { WorldSupabase } from './supabase/worldSupabase';
import type { Services } from './types';

function build(): Services {
  if (supabaseEnabled()) {
    console.info('[services] Supabase env detected \u2014 using supabase backend (stubbed; see src/services/supabase/*)');
    return {
      auth: new AuthSupabase(),
      characters: new CharacterSupabase(),
      inventory: new InventorySupabase(),
      crafting: new CraftingSupabase(),
      chat: new ChatSupabase(),
      world: new WorldSupabase(),
      worldEdits: new WorldEditSupabase(),
      campaign: new CampaignSupabase(),
      quests: new QuestSupabase(),
      backend: 'supabase',
    };
  }
  console.info('[services] Using local in-memory backend. Set VITE_SUPABASE_URL + VITE_SUPABASE_ANON_KEY to switch.');
  return {
    auth: new AuthLocal(),
    characters: new CharacterLocal(),
    inventory: new InventoryLocal(),
    crafting: new CraftingLocal(),
    chat: new ChatLocal(),
    world: new WorldLocal(),
    worldEdits: new WorldEditLocal(),
    campaign: new CampaignLocal(),
    quests: new QuestLocal(),
    backend: 'local',
  };
}

export const services: Services = build();
export type { Services } from './types';

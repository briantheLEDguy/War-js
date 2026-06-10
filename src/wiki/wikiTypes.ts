import type { CraftingRecipe, CultivationSeedDefinition } from '../data/crafting';
import type { AbilityDefinition, CareerResourceDefinition } from '../game/abilities/types';

export type WikiPageStatus = 'implemented' | 'planned';

export type WikiSectionId =
  | 'overview'
  | 'races_classes'
  | 'abilities'
  | 'crafting'
  | 'quests'
  | 'world_roadmap';

export interface WikiSection {
  id: WikiSectionId;
  title: string;
  summary: string;
  order: number;
}

export interface WikiDetailRow {
  label: string;
  value: string;
}

export interface WikiTableRow {
  id: string;
  cells: string[];
}

export interface WikiTable {
  title: string;
  columns: string[];
  rows: WikiTableRow[];
}

export type WikiPageSource =
  | {
      kind: 'ability';
      ability: AbilityDefinition;
      resource: CareerResourceDefinition;
    }
  | {
      kind: 'craftingRecipe';
      recipe: CraftingRecipe;
    }
  | {
      kind: 'cultivationSeed';
      seed: CultivationSeedDefinition;
    };

export interface WikiPage {
  id: string;
  sectionId: WikiSectionId;
  title: string;
  subtitle?: string;
  status: WikiPageStatus;
  tags: string[];
  body: string[];
  details?: WikiDetailRow[];
  tables?: WikiTable[];
  source?: WikiPageSource;
}

export interface WikiIndex {
  sections: WikiSection[];
  pages: WikiPage[];
  pagesById: Record<string, WikiPage>;
}

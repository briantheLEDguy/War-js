import type { PlayableRace } from '../data/careers';
import type { WikiPage, WikiSection, WikiSectionId } from './wikiTypes';

export const WIKI_SECTIONS: WikiSection[] = [
  {
    id: 'overview',
    title: 'Overview',
    summary: 'How the current game slice is structured.',
    order: 0,
  },
  {
    id: 'races_classes',
    title: 'Races & Classes',
    summary: 'Playable realms, races, class roster, and class resources.',
    order: 1,
  },
  {
    id: 'abilities',
    title: 'Abilities',
    summary: 'The current ten-slot class ability kits.',
    order: 2,
  },
  {
    id: 'crafting',
    title: 'Crafting',
    summary: 'Professions, recipes, cultivation, stations, and materials.',
    order: 3,
  },
  {
    id: 'quests',
    title: 'Quests',
    summary: 'Current quest chains, objectives, prerequisites, and rewards.',
    order: 4,
  },
  {
    id: 'world_roadmap',
    title: 'World & Roadmap',
    summary: 'Implemented world systems and planned expansion areas.',
    order: 5,
  },
];

export const SECTION_EMPTY_PAGE: Record<WikiSectionId, string> = {
  overview: 'No overview pages match the current search.',
  races_classes: 'No race or class pages match the current search.',
  abilities: 'No ability pages match the current search.',
  crafting: 'No crafting pages match the current search.',
  quests: 'No quest pages match the current search.',
  world_roadmap: 'No world or roadmap pages match the current search.',
};

export const RACE_GUIDE_COPY: Record<PlayableRace, string> = {
  empire: 'Aegis Accord humans based from Bastion of Aegis, with classes built around fire magic, investigation, command, and battle prayers.',
  dwarf: 'Aegis Accord mountain folk with defensive oathcraft, berserker pressure, rune support, and engineering tools.',
  high_elf: 'Aegis Accord elves with disciplined blade forms, beast hunting, balanced magic, and mobile archery.',
  chaos: 'Riftbound Host zealots with dread auras, mutations, occult artillery, and ritual support.',
  greenskin: 'Riftbound Host brawlers and skirmishers with plan-based tanking, beast handling, bog magic, and frenzied melee.',
  dark_elf: 'Riftbound Host raiders with blood assassination, hatred tanking, dark power casting, and siphon healing.',
};

export const CLASS_FAMILY_LABELS: Record<string, string> = {
  risk_caster: 'Risk Caster',
  verdict_assassin: 'Verdict Assassin',
  commander_tank: 'Commander Tank',
  melee_healer: 'Melee Healer',
  reactive_oath_tank: 'Reactive Oath Tank',
  berserker: 'Berserker',
  rune_mark_support: 'Rune Support',
  deployable_artillery: 'Deployable Artillery',
  stance_chain_tank: 'Stance Chain Tank',
  bonded_beast_hunter: 'Bonded Beast Hunter',
  balance_caster: 'Balance Caster',
  mobile_skirmisher: 'Mobile Skirmisher',
  dark_gift_tank: 'Dark Gift Tank',
  mutation_disruptor: 'Mutation Disruptor',
  occult_artillery: 'Occult Artillery',
  ritual_support: 'Ritual Support',
  plan_bruiser: 'Plan Bruiser',
  pet_skirmisher: 'Pet Skirmisher',
  hybrid_hexer: 'Hybrid Hexer',
  frenzy_bruiser: 'Frenzy Bruiser',
  blood_assassin: 'Blood Assassin',
  hatred_tank: 'Hatred Tank',
  dark_power_caster: 'Dark Power Caster',
  siphon_healer: 'Siphon Healer',
};

export const OVERVIEW_PAGES: WikiPage[] = [
  {
    id: 'overview-current-slice',
    sectionId: 'overview',
    title: 'Current Game Slice',
    subtitle: 'Implemented systems',
    status: 'implemented',
    tags: ['overview', 'current', 'systems'],
    body: [
      'War-js currently runs as a browser-based Three.js world with React HUD panels, local services by default, and Supabase-ready service contracts.',
      'This guide is generated from the same gameplay catalogs used by character creation, combat, crafting, quests, and inventory where possible.',
    ],
    details: [
      { label: 'Runtime', value: 'Three.js + React + Vite + TypeScript' },
      { label: 'State', value: 'Zustand game store' },
      { label: 'Backend', value: 'Local in-memory/localStorage services with Supabase stubs' },
      { label: 'Content rule', value: 'Implemented catalog data is authoritative; roadmap pages are marked planned.' },
    ],
  },
  {
    id: 'overview-controls',
    sectionId: 'overview',
    title: 'Core Controls',
    subtitle: 'Keyboard and mouse',
    status: 'implemented',
    tags: ['controls', 'help', 'keyboard', 'mouse'],
    body: [
      'The in-game guide is opened from the HUD or with H. While the guide is open, movement, combat, interaction, and chat shortcuts are blocked.',
    ],
    tables: [
      {
        title: 'Default controls',
        columns: ['Input', 'Action'],
        rows: [
          { id: 'move', cells: ['W A S D', 'Move'] },
          { id: 'jump', cells: ['Space', 'Jump'] },
          { id: 'interact', cells: ['E', 'Interact, gather, or craft'] },
          { id: 'inventory', cells: ['I', 'Inventory'] },
          { id: 'character', cells: ['C', 'Character sheet'] },
          { id: 'quest-log', cells: ['L', 'Quest log'] },
          { id: 'guide', cells: ['H', 'Guide'] },
          { id: 'settings', cells: ['Esc', 'Close guide or toggle settings'] },
          { id: 'abilities', cells: ['1-0', 'Class abilities'] },
        ],
      },
    ],
  },
  {
    id: 'overview-player-qol',
    sectionId: 'overview',
    title: 'Player QoL HUD',
    subtitle: 'Orientation, feedback, first-session goals, and campaign preview',
    status: 'implemented',
    tags: ['qol', 'hud', 'campaign', 'tutorial', 'rvr', 'minimap', 'inventory'],
    body: [
      'The HUD includes an objective tracker, enhanced minimap markers, contextual interaction prompts, ability failure feedback, optional first-session goals backed by local browser storage, and a local campaign preview for RvR orientation.',
      'The campaign panel reads the service snapshot. Local mode persists control in browser storage; Supabase activation uses the campaign tables seeded from the static graph.',
    ],
    details: [
      { label: 'Orientation', value: 'Quest, NPC, crafting, enemy, exit, and off-range priority markers with objective progress.' },
      { label: 'Inventory/Crafting', value: 'Search, filters, sort controls, comparison, ingredient deficits, and safer salvage preview.' },
      { label: 'Feedback', value: 'Nearby action prompts and ability failure reasons for target, range, cooldown, resource, defeated, and UI-blocked states.' },
      { label: 'First Steps', value: 'Move, camera, interaction, combat, harvest, gear equip, guide, and crafting.' },
      { label: 'Campaign', value: 'Aegis Accord vs Riftbound Host control, static graph lanes, fortress pressure, and city siege readiness.' },
    ],
  },
];

export const ROADMAP_PAGES: WikiPage[] = [
  {
    id: 'roadmap-asset-pipeline',
    sectionId: 'world_roadmap',
    title: 'Asset Pipeline',
    subtitle: 'Phase 2a',
    status: 'planned',
    tags: ['roadmap', 'assets', 'models'],
    body: [
      'The runtime already resolves GLB models through asset-index metadata and primitive fallbacks. Future work expands the manifest-first asset pipeline with more authored models, textures, and environment assets.',
    ],
  },
  {
    id: 'roadmap-supabase',
    sectionId: 'world_roadmap',
    title: 'Supabase Backend Activation',
    subtitle: 'Phase 2b',
    status: 'planned',
    tags: ['roadmap', 'supabase', 'backend'],
    body: [
      'The service layer is Supabase-ready, but Supabase implementations remain stubs until the database schema and service methods are wired.',
    ],
  },
  {
    id: 'roadmap-multiplayer',
    sectionId: 'world_roadmap',
    title: 'Real Multiplayer',
    subtitle: 'Phase 2c',
    status: 'planned',
    tags: ['roadmap', 'multiplayer', 'realtime'],
    body: [
      'Current local mode can run the game without backend configuration. Future multiplayer work will use realtime player state, remote interpolation, and server-backed persistence.',
    ],
  },
  {
    id: 'roadmap-quests-vendors',
    sectionId: 'world_roadmap',
    title: 'Quests, NPCs, and Vendors',
    subtitle: 'Phase 2e',
    status: 'planned',
    tags: ['roadmap', 'quests', 'npcs', 'vendors'],
    body: [
      'The first quest chain and NPC interaction path exist. Future work expands quest types, NPC services, vendors, and original district placement.',
    ],
  },
  {
    id: 'roadmap-world-rvr',
    sectionId: 'world_roadmap',
    title: 'Multi-Zone World and RvR',
    subtitle: 'Phase 2f / 2g',
    status: 'planned',
    tags: ['roadmap', 'world', 'rvr', 'pvp'],
    body: [
      'Future world pages will cover additional original zones, scenarios, open RvR, and city siege rules as those systems land in data and code.',
    ],
    details: [
      { label: 'Central path', value: 'Riftspire Citadel -> Voidgate Fortress -> Rift Crownworks -> Shatterline Expanse -> Dawnline Expanse -> Aegis Crownworks -> Starfall Gate -> Bastion of Aegis' },
      { label: 'City siege rule', value: 'A city siege opens when a realm controls the enemy T4 front, inner T4 zone, and fortress.' },
    ],
  },
];

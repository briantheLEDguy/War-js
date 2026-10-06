/** Network-independent scenario contracts. Character documents come from trusted game hosts. */
export type ScenarioRealm = 'aegis' | 'riftbound';
export interface ScenarioDefinition {
  id: string;
  name: string;
  map: string;
  contentRevision: string;
  description: string;
  capacity: number;
  gatherMs: number;
  acceptMs: number;
  reconnectMs: number;
  rulesVersion?: 1 | 2;
  battlefield?: 'LowerCity' | 'FullSiege';
}
export const scenarioCatalog: readonly ScenarioDefinition[] = [{
  id: 'lower_city', name: 'Siege of Bastion of Aegis', map: '/Game/Capitals/Siege/AegisCapital_Siege',
  contentRevision: '', // The host pins this to the installed shared-city definition at startup.
  description: 'Breach the city, capture both side objectives and the courtyard, then defeat the commander.',
  capacity: 18, gatherMs: 30_000, acceptMs: 30_000, reconnectMs: 120_000,
  rulesVersion: 2, battlefield: 'FullSiege',
}];
export type ScenarioPhase = 'idle' | 'queued' | 'offered' | 'allocating' | 'travel' | 'playing' | 'disconnected' | 'return';
export interface ScenarioCharacter {
  id: string;
  name: string;
  realm: ScenarioRealm;
  visual: string;
  returnMap: string;
  returnPosition: number[];
  document: Record<string, unknown>;
}
export interface ScenarioParty { id: string; leader: string; members: string[]; ready: string[] }
export interface ScenarioPlayer {
  character: ScenarioCharacter;
  token: string;
  party: string;
  phase: ScenarioPhase;
  message: string;
  match?: string;
  disconnectedAt?: number;
  possessionReleased?: boolean;
  departurePrepared?: boolean;
  campaignReleased?: boolean;
  restoreAfter?: number;
  lastSeen?: number;
}
export interface ScenarioQueueEntry { party: string; scenario: string; since: number }
export interface ScenarioMatch {
  id: string;
  scenario: string;
  parties: ScenarioQueueEntry[];
  members: string[];
  accepted: string[];
  deadline: number;
  phase: 'offered' | 'allocating' | 'running' | 'finished';
  endpoint?: string;
  serverKey: string;
  started?: number;
  /** Immutable allocation contract; old journals without it retain their historical 6v6 rules. */
  definition?: ScenarioDefinition;
}
export interface ScenarioTicket { player: string; match: string; expires: number; kind: 'join' | 'return' }
export interface ScenarioJournal {
  version: 1;
  players: Record<string, ScenarioPlayer>;
  parties: Record<string, ScenarioParty>;
  invites: Record<string, string[]>;
  queue: ScenarioQueueEntry[];
  matches: Record<string, ScenarioMatch>;
  tickets: Record<string, ScenarioTicket>;
}

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
}
export const scenarioCatalog: readonly ScenarioDefinition[] = [{
  id: 'lower_city', name: 'Breach the Lower City', map: '/Game/Capitals/Siege/AegisCapital_Siege',
  contentRevision: '86500edebe9a9166ecaaf9b65524afc0aa250d8b9359f547e111b817f65469f2',
  description: 'Secure supplies, escort the engineers and breach the lower city gate.',
  capacity: 6, gatherMs: 30_000, acceptMs: 30_000, reconnectMs: 120_000,
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

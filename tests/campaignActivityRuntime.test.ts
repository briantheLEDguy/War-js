import * as THREE from 'three';
import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import {
  buildCampaignSnapshot,
  campaignKeepCaptureReward,
  objectiveKey,
  type CampaignClaimResult,
  type CampaignObjectiveStatus,
  type CampaignRealm,
  type CampaignZoneStatus,
} from '../src/data/campaign';
import { INVENTORY_CAPACITY } from '../src/data/items';
import type { PlayableRace } from '../src/data/careers';
import type { CampaignActivity } from '../src/game/CampaignObjectiveLogic';
import { Game } from '../src/game/Game';
import { services } from '../src/services';
import { useGameStore } from '../src/state/gameStore';
import type { ZoneDefinition } from '../src/world/ZoneLoader';
import { makeCharacter, makeEnemy, resetGameStore } from './testUtils';

const WALL_CLOCK = 1_800_000_000_000;
const HOME_ZONE = 'brightfen_approach';

// Exercise the real Game methods without creating a renderer, DOM canvas, or animation loop.
interface GameHarness {
  player: { position: THREE.Vector3 };
  currentZone: Pick<ZoneDefinition, 'id' | 'enemies'>;
  objectiveStatus: Map<string, CampaignObjectiveStatus>;
  campaignZoneStatus: CampaignZoneStatus;
  objectiveCapture: { objectiveId: string; startedAtMs: number; realm: CampaignRealm; activity: 'capture' | 'defend' } | null;
  objectiveClaimsInFlight: Set<string>;
  disposed: boolean;
  updateObjectiveCapture(nowMs: number, uiBlockingOpen: boolean): void;
  campaignActivities(store: ReturnType<typeof useGameStore.getState>): CampaignActivity[];
  readonly campaignActivity: { zone: CampaignZoneStatus; focus: CampaignActivity | null; progress: number } | null;
}

function createGame({
  zoneId = HOME_ZONE,
  race = 'empire',
  objectiveId = `${zoneId}_west_objective`,
  influence = 0,
}: { zoneId?: string; race?: PlayableRace; objectiveId?: string; influence?: number } = {}): GameHarness {
  const snapshot = buildCampaignSnapshot(zoneId, {}, {}, { [zoneId]: { aegis: influence, riftbound: influence } });
  const zone = snapshot.activeZone!;
  const objective = zone.objectives.find((entry) => entry.id === objectiveId)!;
  const position = new THREE.Vector3(objective.x, 0, objective.z);
  useGameStore.getState().setCharacter(makeCharacter({ race, zoneId, position: { x: position.x, y: 0, z: position.z } }));
  return Object.assign(Object.create(Game.prototype), {
    player: { position },
    currentZone: { id: zoneId, enemies: [] },
    objectiveStatus: new Map([[objective.id, objective]]),
    campaignZoneStatus: zone,
    objectiveCapture: null,
    objectiveClaimsInFlight: new Set<string>(),
    disposed: false,
  }) as GameHarness;
}

function claimResult(zoneId: string, objectiveId: string, realm: CampaignRealm, activity: 'capture' | 'defend'): CampaignClaimResult {
  const key = objectiveKey(zoneId, objectiveId);
  const snapshot = buildCampaignSnapshot(zoneId, {}, { [key]: realm }, {},
    activity === 'defend' ? { [key]: { [realm]: WALL_CLOCK + 180_000 } } : {});
  const objective = snapshot.activeZone!.objectives.find((entry) => entry.id === objectiveId)!;
  return {
    activity,
    snapshot,
    zoneId,
    objectiveId,
    realm,
    objective,
    reward: activity === 'defend' ? { xp: 50, influence: 35 }
      : objective.type === 'keep' ? campaignKeepCaptureReward(zoneId) : { xp: 75, influence: 25 },
    zoneControlChanged: false,
  };
}

function deferredResult() {
  let resolve!: (result: CampaignClaimResult) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<CampaignClaimResult>((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
}

describe('Game campaign activity runtime', () => {
  let nowMs = 0;

  test('friendly capital standards do not replace expedition guidance with an unavailable defense', () => {
    const game = createGame({ zoneId: 'aegis_capital', objectiveId: 'aegis_capital_courtyard' });
    expect(game.campaignActivities(useGameStore.getState())).toEqual([]);
    expect(game.campaignActivity?.focus).toBeNull();
    game.updateObjectiveCapture(5000, false);
    expect(game.objectiveCapture).toBeNull();
  });

  function tick(game: GameHarness, timestamp: number, uiBlockingOpen = false) {
    nowMs = timestamp;
    game.updateObjectiveCapture(timestamp, uiBlockingOpen);
  }

  async function settle(game: GameHarness) {
    await vi.waitFor(() => expect(game.objectiveClaimsInFlight.size).toBe(0), { interval: 1 });
  }

  beforeEach(() => {
    resetGameStore();
    useGameStore.setState({
      inventory: [], chat: [], quests: [], campaignRewardNotice: null,
      playerDead: false, chatFocused: false, gmBuildMode: false, gmFlyingMode: false, pendingZoneTransition: null,
    });
    nowMs = 0;
    const storage = new Map<string, string>();
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
      removeItem: (key: string) => storage.delete(key),
    });
    vi.spyOn(Date, 'now').mockReturnValue(WALL_CLOCK);
    vi.spyOn(performance, 'now').mockImplementation(() => nowMs);
    vi.spyOn(services.campaign, 'defendObjective').mockImplementation(async (zoneId, id, realm) =>
      claimResult(zoneId, id, realm, 'defend'));
    vi.spyOn(services.campaign, 'claimObjective').mockImplementation(async (zoneId, id, realm) =>
      claimResult(zoneId, id, realm, 'capture'));
    vi.spyOn(services.inventory, 'update').mockResolvedValue();
    vi.spyOn(services.characters, 'save').mockResolvedValue();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  test.each([
    { zoneId: HOME_ZONE, race: 'empire' as const, realm: 'aegis', activity: 'defend' as const, hold: 8000, xp: 50 },
    { zoneId: 'shatterline_expanse', race: 'empire' as const, realm: 'aegis', activity: 'capture' as const, hold: 3000, xp: 75 },
    { zoneId: 'cinderfen_outskirts', race: 'greenskin' as const, realm: 'riftbound', activity: 'defend' as const, hold: 8000, xp: 50 },
    { zoneId: HOME_ZONE, race: 'greenskin' as const, realm: 'riftbound', activity: 'capture' as const, hold: 3000, xp: 75 },
  ])('$realm $activity waits its full hold and dispatches and settles the matching activity', async ({ zoneId, race, realm, activity, hold, xp }) => {
    const game = createGame({ zoneId, race });
    const correct = activity === 'defend' ? services.campaign.defendObjective : services.campaign.claimObjective;
    const other = activity === 'defend' ? services.campaign.claimObjective : services.campaign.defendObjective;
    tick(game, 100);
    tick(game, 100 + hold / 2);
    expect(game.campaignActivity?.progress).toBeCloseTo(0.5);
    expect(game.campaignActivity?.focus).toMatchObject({ activity, holdMs: hold, blocker: null });
    tick(game, 100 + hold - 1);
    expect(correct).not.toHaveBeenCalled();
    tick(game, 100 + hold);
    expect(correct).toHaveBeenCalledExactlyOnceWith(zoneId, `${zoneId}_west_objective`, realm);
    expect(other).not.toHaveBeenCalled();
    await settle(game);
    expect(useGameStore.getState().character).toMatchObject({ id: 'char-test', xp, gold: 0 });
    expect(useGameStore.getState().campaignRewardNotice).toMatchObject({
      characterId: 'char-test', zoneId, xp, pendingItems: [],
      title: `${activity === 'defend' ? 'Defended' : 'Captured'} West Field Standard`,
    });
    expect(services.characters.save).toHaveBeenCalledWith('char-test', expect.objectContaining({ xp }));
  });

  test('moving outside the objective discards hold progress', async () => {
    const game = createGame();
    const objective = game.campaignActivity!.focus!.objective;
    tick(game, 0);
    tick(game, 4000);
    game.player.position.x += objective.captureRadius + 1;
    tick(game, 5000);
    expect(game.objectiveCapture).toBeNull();
    expect(game.campaignActivity?.progress).toBe(0);
    game.player.position.x = objective.x;
    tick(game, 6000);
    tick(game, 13999);
    expect(services.campaign.defendObjective).not.toHaveBeenCalled();
    tick(game, 14000);
    expect(services.campaign.defendObjective).toHaveBeenCalledTimes(1);
    await settle(game);
  });

  test('a living spawn-bound guard contests and resets the hold even after being kited away', async () => {
    const game = createGame();
    const objective = game.campaignActivity!.focus!.objective;
    game.currentZone.enemies = [{ id: 'standard-guard', name: 'Objective Guard', x: objective.x + 1, z: objective.z, level: 3, maxHealth: 100, aggroRange: 14 }];
    const guard = makeEnemy({ id: 'standard-guard', name: 'Objective Guard', position: { x: 1000, y: 0, z: 1000 } });
    tick(game, 0);
    tick(game, 4000);
    useGameStore.setState({ enemies: [guard] });
    tick(game, 4500);
    expect(game.objectiveCapture).toBeNull();
    expect(game.campaignActivity?.focus).toMatchObject({ defenders: 1, blocker: 'Defeat 1 remaining defender' });
    tick(game, 12000);
    expect(services.campaign.defendObjective).not.toHaveBeenCalled();
    useGameStore.setState({ enemies: [{ ...guard, alive: false, health: 0 }] });
    tick(game, 13000);
    tick(game, 20999);
    expect(services.campaign.defendObjective).not.toHaveBeenCalled();
    tick(game, 21000);
    expect(services.campaign.defendObjective).toHaveBeenCalledTimes(1);
    await settle(game);
  });

  test.each(['blocking UI', 'death', 'flying', 'build mode', 'chat', 'zone transition'])(
    '%s resets a hold instead of letting it complete in the background', async (blocker) => {
      const game = createGame();
      tick(game, 0);
      tick(game, 4000);
      if (blocker === 'death') useGameStore.setState({ playerDead: true });
      if (blocker === 'flying') useGameStore.setState({ gmFlyingMode: true });
      if (blocker === 'build mode') useGameStore.setState({ gmBuildMode: true });
      if (blocker === 'chat') useGameStore.setState({ chatFocused: true });
      if (blocker === 'zone transition') useGameStore.setState({ pendingZoneTransition: { targetZoneId: 'glassriver_ford' } });
      tick(game, 9000, blocker === 'blocking UI');
      expect(game.objectiveCapture).toBeNull();
      expect(services.campaign.defendObjective).not.toHaveBeenCalled();
      useGameStore.setState({ playerDead: false, gmFlyingMode: false, gmBuildMode: false, chatFocused: false, pendingZoneTransition: null });
      tick(game, 10000);
      tick(game, 17999);
      expect(services.campaign.defendObjective).not.toHaveBeenCalled();
      tick(game, 18000);
      expect(services.campaign.defendObjective).toHaveBeenCalledTimes(1);
      await settle(game);
    },
  );

  test('keep influence and full-bag blockers prevent requests before the hold starts', () => {
    const objectiveId = `${HOME_ZONE}_riftbound_keep`;
    const locked = createGame({ objectiveId });
    tick(locked, 0);
    tick(locked, 10000);
    expect(locked.campaignActivity?.focus?.blocker).toMatch(/Build 100 realm influence/);
    expect(locked.objectiveCapture).toBeNull();
    const fullBag = createGame({ objectiveId, influence: 105 });
    useGameStore.getState().setInventory(Array.from({ length: INVENTORY_CAPACITY }, (_, slot) => ({ slot, key: 'bread', name: 'Bread', qty: 99 })));
    tick(fullBag, 0);
    tick(fullBag, 10000);
    expect(fullBag.campaignActivity?.focus?.blocker).toMatch(/Make room in your inventory/);
    expect(fullBag.objectiveCapture).toBeNull();
    expect(services.campaign.claimObjective).not.toHaveBeenCalled();
    expect(services.campaign.defendObjective).not.toHaveBeenCalled();
  });

  test('a secured keep settles XP, gold and the actual equipment receipt', async () => {
    const objectiveId = `${HOME_ZONE}_riftbound_keep`;
    const game = createGame({ objectiveId, influence: 105 });
    tick(game, 0);
    tick(game, 3000);
    expect(services.campaign.claimObjective).toHaveBeenCalledExactlyOnceWith(HOME_ZONE, objectiveId, 'aegis');
    await settle(game);
    expect(useGameStore.getState().character).toMatchObject({ xp: 300, gold: 30 });
    expect(useGameStore.getState().inventory).toEqual([expect.objectContaining({
      key: 'jewel_amulet_bloodglass', equipSlot: 'neck', qty: 1,
      affix: { strengthBonus: expect.any(Number) },
    })]);
    expect(useGameStore.getState().campaignRewardNotice).toMatchObject({ xp: 300, gold: 30, pendingItems: [], itemNames: ["Brightfen Approach Victor's Amulet"] });
  });

  test('an in-flight activity cannot dispatch again and settles after a same-character zone transition', async () => {
    const game = createGame();
    const pending = deferredResult();
    vi.mocked(services.campaign.defendObjective).mockReturnValueOnce(pending.promise);
    tick(game, 0);
    tick(game, 8000);
    tick(game, 16000);
    tick(game, 24000);
    expect(services.campaign.defendObjective).toHaveBeenCalledTimes(1);
    expect(game.campaignActivity?.focus?.blocker).toMatch(/Securing objective/);
    expect(useGameStore.getState().character?.xp).toBe(0);
    useGameStore.getState().updateCharacter({ zoneId: 'glassriver_ford' });
    pending.resolve(claimResult(HOME_ZONE, `${HOME_ZONE}_west_objective`, 'aegis', 'defend'));
    await settle(game);
    expect(useGameStore.getState().character).toMatchObject({ id: 'char-test', zoneId: 'glassriver_ford', xp: 50 });
    expect(useGameStore.getState().campaignRewardNotice).toMatchObject({ characterId: 'char-test', zoneId: HOME_ZONE, xp: 50 });
  });

  test('a late result does not award the newly selected character', async () => {
    const game = createGame();
    const pending = deferredResult();
    vi.mocked(services.campaign.defendObjective).mockReturnValueOnce(pending.promise);
    tick(game, 0);
    tick(game, 8000);
    useGameStore.getState().setCharacter(makeCharacter({ id: 'different-character' }));
    pending.resolve(claimResult(HOME_ZONE, `${HOME_ZONE}_west_objective`, 'aegis', 'defend'));
    await settle(game);
    expect(useGameStore.getState().character).toMatchObject({ id: 'different-character', xp: 0, gold: 0 });
    expect(useGameStore.getState().campaignRewardNotice).toBeNull();
    expect(services.characters.save).not.toHaveBeenCalled();
  });
});

import { afterEach, describe, expect, test } from 'vitest';
import {
  DEFAULT_VIEW_DISTANCE,
  VIEW_DISTANCE_MAX,
  VIEW_DISTANCE_MIN,
  clampViewDistance,
  formatViewDistance,
  viewDistanceFogNear,
} from '../src/config/viewDistance';
import {
  buildCampaignSnapshot,
  CAMPAIGN_GRAPH_EDGES,
  CAMPAIGN_SIEGE_RULE,
  CAMPAIGN_ZONES,
} from '../src/data/campaign';
import { contextPromptKey, useGameStore, type GuidedTaskProgress } from '../src/state/gameStore';
import {
  GUIDED_TASKS,
  guidedTaskCompletion,
} from '../src/ui/hud/guidedTasks';

function emptyProgress(): GuidedTaskProgress {
  return {
    move: false,
    camera: false,
    interact: false,
    kill: false,
    gather: false,
    equip: false,
    guide: false,
    craft: false,
  };
}

function resetWindowState(): void {
  useGameStore.setState({
    settingsOpen: false,
    worldMapOpen: false,
    wikiOpen: false,
    activeQuestDialogNpcId: null,
    craftingOpen: false,
    activeCraftingStation: null,
    campaignOpen: false,
    questLogOpen: false,
    characterSheetOpen: false,
    inventoryOpen: false,
    debugOpen: false,
    gmMenuOpen: false,
    gmMoveSpeedMultiplier: 1,
    gmFlyingMode: false,
    gmBuildMode: false,
  });
}

afterEach(() => {
  resetWindowState();
});

describe('first-session guided task helpers', () => {
  test('starts with the movement goal and no completed tasks', () => {
    const progress = guidedTaskCompletion(emptyProgress());

    expect(progress.completed).toBe(0);
    expect(progress.total).toBe(8);
    expect(progress.percent).toBe(0);
    expect(GUIDED_TASKS.find((task) => !emptyProgress()[task.id])?.id).toBe('move');
  });

  test('summarizes completion for all guided tasks in order', () => {
    const completed = GUIDED_TASKS.reduce<GuidedTaskProgress>(
      (acc, task) => ({ ...acc, [task.id]: true }),
      emptyProgress(),
    );
    const progress = guidedTaskCompletion(completed);

    expect(GUIDED_TASKS.map((task) => task.id)).toEqual([
      'move',
      'camera',
      'interact',
      'kill',
      'gather',
      'equip',
      'guide',
      'craft',
    ]);
    expect(progress.completed).toBe(progress.total);
    expect(progress.percent).toBe(100);
  });

  test('store actions complete and reset guided task state', () => {
    useGameStore.setState({ guidedTasks: emptyProgress() });

    useGameStore.getState().completeGuidedTask('move');
    useGameStore.getState().completeGuidedTask('craft');
    expect(useGameStore.getState().guidedTasks.move).toBe(true);
    expect(useGameStore.getState().guidedTasks.craft).toBe(true);
    expect(guidedTaskCompletion(useGameStore.getState().guidedTasks).completed).toBe(2);

    useGameStore.getState().resetGuidedTasks();
    expect(guidedTaskCompletion(useGameStore.getState().guidedTasks).completed).toBe(0);
  });
});

describe('contextual prompt helpers', () => {
  test('keep prompt identity stable while only distance changes', () => {
    const prompt = {
      kind: 'target' as const,
      action: 'LMB',
      label: 'Target Training Dummy',
      detail: 'Lv 1',
      distance: 3.2,
    };
    const samePromptFartherAway = { ...prompt, distance: 9.6 };

    expect(contextPromptKey(prompt)).toBe(contextPromptKey(samePromptFartherAway));

    useGameStore.setState({ contextPrompt: null });
    useGameStore.getState().setContextPrompt(prompt);
    const firstPromptState = useGameStore.getState().contextPrompt;

    useGameStore.getState().setContextPrompt(samePromptFartherAway);
    expect(useGameStore.getState().contextPrompt).toBe(firstPromptState);

    useGameStore.getState().setContextPrompt(null);
    expect(useGameStore.getState().contextPrompt).toBeNull();
  });
});

describe('hud window close helpers', () => {
  test('closes the focused modal before lower-priority panels', () => {
    useGameStore.setState({
      settingsOpen: true,
      worldMapOpen: true,
      inventoryOpen: true,
    });

    expect(useGameStore.getState().closeTopWindow()).toBe(true);
    expect(useGameStore.getState().settingsOpen).toBe(false);
    expect(useGameStore.getState().worldMapOpen).toBe(true);

    expect(useGameStore.getState().closeTopWindow()).toBe(true);
    expect(useGameStore.getState().worldMapOpen).toBe(false);
    expect(useGameStore.getState().inventoryOpen).toBe(true);

    expect(useGameStore.getState().closeTopWindow()).toBe(true);
    expect(useGameStore.getState().inventoryOpen).toBe(false);
    expect(useGameStore.getState().closeTopWindow()).toBe(false);
  });

  test('closes crafting, campaign, debug, and GM editor windows', () => {
    useGameStore.setState({
      craftingOpen: true,
      activeCraftingStation: { kind: 'general', label: 'Test Station' },
      campaignOpen: true,
      debugOpen: true,
      gmMenuOpen: true,
      gmBuildMode: true,
    });

    expect(useGameStore.getState().closeTopWindow()).toBe(true);
    expect(useGameStore.getState().gmMenuOpen).toBe(false);

    expect(useGameStore.getState().closeTopWindow()).toBe(true);
    expect(useGameStore.getState().craftingOpen).toBe(false);
    expect(useGameStore.getState().activeCraftingStation).toBeNull();

    expect(useGameStore.getState().closeTopWindow()).toBe(true);
    expect(useGameStore.getState().campaignOpen).toBe(false);

    expect(useGameStore.getState().closeTopWindow()).toBe(true);
    expect(useGameStore.getState().debugOpen).toBe(false);

    expect(useGameStore.getState().closeTopWindow()).toBe(true);
    expect(useGameStore.getState().gmBuildMode).toBe(false);
  });
});

describe('GM movement helpers', () => {
  test('clamps the GM movement multiplier and toggles flying mode', () => {
    useGameStore.getState().setGmMoveSpeedMultiplier(12);
    expect(useGameStore.getState().gmMoveSpeedMultiplier).toBe(6);

    useGameStore.getState().setGmMoveSpeedMultiplier(0);
    expect(useGameStore.getState().gmMoveSpeedMultiplier).toBe(0.25);

    useGameStore.getState().setGmMoveSpeedMultiplier(2.5);
    expect(useGameStore.getState().gmMoveSpeedMultiplier).toBe(2.5);

    useGameStore.getState().setGmFlyingMode(true);
    expect(useGameStore.getState().gmFlyingMode).toBe(true);

    useGameStore.getState().toggleGmFlyingMode();
    expect(useGameStore.getState().gmFlyingMode).toBe(false);
  });
});

describe('view distance settings', () => {
  test('clamps and formats the persisted view distance range', () => {
    expect(clampViewDistance(50)).toBe(VIEW_DISTANCE_MIN);
    expect(clampViewDistance(5000)).toBe(VIEW_DISTANCE_MAX);
    expect(clampViewDistance('farther')).toBe(DEFAULT_VIEW_DISTANCE);
    expect(formatViewDistance(525)).toBe('525 m');
    expect(viewDistanceFogNear(500)).toBe(140);
  });

  test('store update keeps view distance inside supported bounds', () => {
    useGameStore.getState().updateSettings({ viewDistance: VIEW_DISTANCE_MAX + 500 });
    expect(useGameStore.getState().settings.viewDistance).toBe(VIEW_DISTANCE_MAX);

    useGameStore.getState().updateSettings({ viewDistance: VIEW_DISTANCE_MIN - 500 });
    expect(useGameStore.getState().settings.viewDistance).toBe(VIEW_DISTANCE_MIN);

    useGameStore.getState().resetSettings();
    expect(useGameStore.getState().settings.viewDistance).toBe(DEFAULT_VIEW_DISTANCE);
  });
});

describe('campaign status helpers', () => {
  test('keeps the full Aegis/Riftbound sketch graph explicit', () => {
    expect(CAMPAIGN_ZONES.map((zone) => zone.id)).toEqual([
      'aegis_capital',
      'aegis_gate_fortress',
      'aegis_crownworks',
      'dawnline_expanse',
      'shatterline_expanse',
      'rift_crownworks',
      'rift_gate_fortress',
      'riftspire_capital',
      'sunmeadow_march',
      'greybrook_crossing',
      'ironwood_redoubt',
      'brightfen_approach',
      'glassriver_ford',
      'highvale_rampart',
      'cinderfen_outskirts',
      'bleakroot_causeway',
      'vilemere_heights',
      'ashen_steppe',
      'gorepine_pass',
      'obsidian_scar',
      'wardens_hollow',
      'briarwatch_den',
      'stormbarrow_lair',
      'mireglass_den',
      'glassriver_depths',
      'highvale_sanctum',
      'cindermaw_pit',
      'rotwreath_nest',
      'nightglass_hollow',
      'ashfang_pit',
      'gorepine_warrens',
      'obsidian_maw',
    ]);
    expect(CAMPAIGN_GRAPH_EDGES).toContainEqual({ fromZoneId: 'dawnline_expanse', toZoneId: 'shatterline_expanse' });
    expect(CAMPAIGN_GRAPH_EDGES).toContainEqual({ fromZoneId: 'shatterline_expanse', toZoneId: 'dawnline_expanse' });
  });

  test('builds a local campaign status with contested middle front by default', () => {
    const status = buildCampaignSnapshot('dawnline_expanse');

    expect(status.activeZone?.id).toBe('dawnline_expanse');
    expect(status.contestedZones).toBe(2);
    expect(status.aegis.controlledZones).toBeGreaterThan(0);
    expect(status.riftbound.controlledZones).toBeGreaterThan(0);
    expect(status.aegis.citySiegeReady).toBe(false);
    expect(status.riftbound.citySiegeReady).toBe(false);
    expect(status.siegeRule).toBe(CAMPAIGN_SIEGE_RULE);
  });

  test('marks a realm city siege ready only after enemy T4 and fortress control', () => {
    const aegisStatus = buildCampaignSnapshot('rift_gate_fortress', {
      shatterline_expanse: 'aegis',
      rift_crownworks: 'aegis',
      rift_gate_fortress: 'aegis',
    });
    const riftboundStatus = buildCampaignSnapshot('aegis_gate_fortress', {
      dawnline_expanse: 'riftbound',
      aegis_crownworks: 'riftbound',
      aegis_gate_fortress: 'riftbound',
    });

    expect(aegisStatus.aegis.citySiegeReady).toBe(true);
    expect(aegisStatus.aegis.targetCityId).toBe('riftspire_capital');
    expect(aegisStatus.riftbound.citySiegeReady).toBe(false);

    expect(riftboundStatus.riftbound.citySiegeReady).toBe(true);
    expect(riftboundStatus.riftbound.targetCityId).toBe('aegis_capital');
    expect(riftboundStatus.aegis.citySiegeReady).toBe(false);
  });
});

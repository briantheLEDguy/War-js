import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { beforeEach, describe, expect, test, vi } from 'vitest';
import { buildCampaignSnapshot, type CampaignZoneStatus } from '../src/data/campaign';
import type { CampaignActivity } from '../src/game/CampaignObjectiveLogic';
import { useGameStore, type CampaignRewardNotice } from '../src/state/gameStore';
import { CampaignActivityCard, CampaignRewardCard } from '../src/ui/hud/CampaignActivityCard';
import { makeCharacter, resetGameStore } from './testUtils';

// SSR normally reads Zustand's initial snapshot. Use live selectors to render each HUD state.
vi.mock('../src/state/gameStore', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../src/state/gameStore')>();
  const useStore = Object.assign(
    (selector: (state: ReturnType<typeof actual.useGameStore.getState>) => unknown) => selector(actual.useGameStore.getState()),
    actual.useGameStore,
  );
  return { ...actual, useGameStore: useStore };
});

function zone(zoneId = 'brightfen_approach'): CampaignZoneStatus {
  return buildCampaignSnapshot(zoneId).activeZone!;
}

function focus(overrides: Partial<CampaignActivity> = {}, field = zone()): CampaignActivity {
  return {
    objective: field.objectives.find((entry) => entry.type === 'battle_objective') ?? field.objectives[0],
    activity: 'capture',
    distance: 0,
    defenders: 0,
    blocker: null,
    holdMs: 3000,
    ...overrides,
  };
}

function renderActivity(activity: CampaignActivity | null = focus(), field = zone(), progress = 0): string {
  return renderToStaticMarkup(createElement(CampaignActivityCard, { campaign: { zone: field, focus: activity, progress } }));
}

function receipt(overrides: Partial<CampaignRewardNotice> = {}): CampaignRewardNotice {
  return {
    characterId: 'char-test',
    title: 'Captured Brightfen Keep',
    zoneId: 'brightfen_approach',
    xp: 300,
    gold: 30,
    influence: 0,
    itemNames: ["Brightfen Approach Victor's Amulet"],
    zoneControlChanged: true,
    pendingItems: [],
    ...overrides,
  };
}

describe('campaign activity card rendering', () => {
  beforeEach(() => {
    resetGameStore();
    useGameStore.getState().setCharacter(makeCharacter());
    useGameStore.setState({ campaignRewardNotice: null });
  });

  test.each([
    { race: 'empire' as const, controlled: 1, influence: 35 },
    { race: 'greenskin' as const, controlled: 2, influence: 70 },
  ])('shows $race standards, realm influence and defense rewards', ({ race, controlled, influence }) => {
    useGameStore.getState().setCharacter(makeCharacter({ race }));
    const field = zone();
    let standardIndex = 0;
    field.objectives = field.objectives.map((objective) => objective.type === 'battle_objective'
      ? { ...objective, control: standardIndex++ === 0 ? 'aegis' : 'riftbound' }
      : objective);
    field.influence = { aegis: 35, riftbound: 70, keepSiegeRequired: 100 };
    const markup = renderActivity(focus({ activity: 'defend', holdMs: 8000 }, field), field);
    expect(markup).toContain(`Standards ${controlled}/3 · Influence ${influence}/100`);
    expect(markup).toContain('Defend ');
    expect(markup).toContain('Hold this area for 8 seconds');
    expect(markup).toContain('+50 XP, +35 influence');
    expect(markup).not.toContain('Victor');
  });

  test('shows capture rewards and guidance toward a distant standard', () => {
    const markup = renderActivity(focus({ distance: 48 }));
    expect(markup).toContain('Capture ');
    expect(markup).toContain('Reach the marked objective');
    expect(markup).toContain('<strong>50m</strong>');
    expect(markup).toContain('+75 XP, +25 influence');
    expect(markup).not.toContain('Hold this area');
    expect(markup).toContain('Show objectives</button>');
  });

  test.each([
    'Defeat 2 remaining defenders',
    'Build 100 realm influence first',
    'Defense ready in 120 seconds',
    'Collect your previous campaign gear first',
    'Make room in your inventory before claiming this objective reward.',
  ])('prioritizes the actionable blocker: %s', (blocker) => {
    const markup = renderActivity(focus({ blocker, distance: 4 }));
    expect(markup).toContain(blocker);
    expect(markup).not.toContain('Hold this area');
    expect(markup).not.toContain('Reach the marked objective');
  });

  test.each([
    { zoneId: 'brightfen_approach', xp: 300, gold: 30 },
    { zoneId: 'highvale_rampart', xp: 900, gold: 90 },
    { zoneId: 'aegis_gate_fortress', xp: 1500, gold: 150 },
  ])('shows the real keep reward in $zoneId', ({ zoneId, xp, gold }) => {
    const field = zone(zoneId);
    const objective = field.objectives.find((entry) => entry.type === 'keep')!;
    const markup = renderActivity(focus({ objective }, field), field);
    expect(markup).toContain(`Victory: ${xp} XP, ${gold} gold and a Victor’s Amulet.`);
    expect(markup).not.toContain('+75 XP');
  });

  test.each(['fortress', 'boss', 'city_gate'] as const)('does not invent XP, influence or gear for a %s capture', (type) => {
    const field = zone();
    const objective = { ...field.objectives[0], type };
    const markup = renderActivity(focus({ objective }, field), field);
    expect(markup).toContain('Secure this objective for your realm.');
    expect(markup).not.toContain(' XP');
    expect(markup).not.toContain(' gold');
    expect(markup).not.toContain('Amulet');
  });

  test('does not promise a keep reward outside a battlefield or fortress', () => {
    const field = zone('aegis_capital');
    const objective = { ...field.objectives[0], type: 'keep' as const };
    const markup = renderActivity(focus({ objective }, field), field);
    expect(markup).toContain('Secure this objective for your realm.');
    expect(markup).not.toContain('Amulet');
  });

  test('renders progress only during an active hold', () => {
    expect(renderActivity()).not.toContain('<progress');
    const markup = renderActivity(focus(), zone(), 0.5);
    expect(markup).toContain('<progress');
    expect(markup).toContain('aria-label="Objective secured"');
    expect(markup).toContain('value="0.5" max="1"');
  });

  test('renders a useful secured state and renders nothing without a character', () => {
    const markup = renderActivity(null);
    expect(markup).toContain('Area secured');
    expect(markup).toContain('Travel to the next front');
    expect(markup).toContain('Show objectives');
    expect(markup).not.toContain('campaign-activity-hint');
    useGameStore.getState().setCharacter(null);
    expect(renderActivity()).toBe('');
  });
});

describe('campaign reward receipt rendering', () => {
  beforeEach(() => {
    resetGameStore();
    useGameStore.getState().setCharacter(makeCharacter());
    useGameStore.setState({ campaignRewardNotice: null });
  });

  const renderReceipt = () => renderToStaticMarkup(createElement(CampaignRewardCard));

  test('shows victory rewards and Continue after gear reaches inventory', () => {
    useGameStore.getState().setCampaignRewardNotice(receipt());
    const markup = renderReceipt();
    expect(markup).toContain('aria-label="Campaign rewards" role="status"');
    expect(markup).toContain('Captured Brightfen Keep');
    expect(markup).toContain('+300 XP · +30 gold');
    expect(markup).toContain('Victor&#x27;s Amulet');
    expect(markup).toContain('Territory secured for your realm.');
    expect(markup).toContain('Continue</button>');
    expect(markup).not.toContain('Collect gear');
    expect(markup).not.toContain('+0 influence');
  });

  test('shows defense influence without gold, territory change or gear when absent', () => {
    useGameStore.getState().setCampaignRewardNotice(receipt({
      title: 'Defended West Standard', xp: 50, gold: 0, influence: 35, itemNames: [], zoneControlChanged: false,
    }));
    const markup = renderReceipt();
    expect(markup).toContain('+50 XP · +35 influence');
    expect(markup).not.toContain(' gold');
    expect(markup).not.toContain('Territory secured');
    expect(markup).not.toContain('Amulet');
  });

  test('keeps collection and inventory actions visible while gear is held and hides Continue', () => {
    useGameStore.getState().setCampaignRewardNotice(receipt({ pendingItems: [{
      key: 'jewel_amulet_bloodglass', name: 'Victor’s Amulet', qty: 1, equipSlot: 'neck',
    }] }));
    const markup = renderReceipt();
    expect(markup).toContain('Free an inventory slot');
    expect(markup).toContain('Your gear is held until you collect it.');
    expect(markup).toContain('Collect gear</button>');
    expect(markup).toContain('Inventory</button>');
    expect(markup).not.toContain('Continue');
  });

  test('shows no receipt for missing or different characters', () => {
    expect(renderReceipt()).toBe('');
    useGameStore.getState().setCampaignRewardNotice(receipt({ characterId: 'another-character' }));
    expect(renderReceipt()).toBe('');
    useGameStore.getState().setCampaignRewardNotice(receipt());
    useGameStore.getState().setCharacter(null);
    expect(renderReceipt()).toBe('');
  });
});

import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest';
import { CharacterLocal } from '../src/services/local/characterLocal';
import { InventoryLocal } from '../src/services/local/inventoryLocal';
import { EMBER_STAFF_KEY, EMBER_STAFF_MODEL } from '../src/data/emberArcanist';
import { getItemDefinition } from '../src/data/items';

describe('Ember Arcanist fitted outfit equipment', () => {
  beforeEach(() => {
    const storage = new Map<string, string>();
    vi.stubGlobal('localStorage', {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => storage.set(key, value),
    });
  });
  afterEach(() => vi.unstubAllGlobals());

  test('new male character equips the staff and receives it in inventory', async () => {
    const characters = new CharacterLocal();
    const created = await characters.create('test', { name: 'Ashward', race: 'empire', className: 'Ember Arcanist', bodyVariant: 'm' });
    const state = await characters.load(created.id);
    expect(state.equipment?.mainHand).toBe(EMBER_STAFF_KEY);
    expect(state.equipment?.offHand).toBeUndefined();
    const items = await new InventoryLocal().get(created.id);
    expect(items.filter(item => item.key === EMBER_STAFF_KEY)).toHaveLength(1);
    expect(items.some(item => item.key === 'shield_wood')).toBe(false);
    expect(getItemDefinition(EMBER_STAFF_KEY)?.visual?.model).toBe(EMBER_STAFF_MODEL);
    expect(getItemDefinition(EMBER_STAFF_KEY)?.weaponKind).toBe('staff');
  });

  test('existing equipment is retained while an empty weapon slot gains the staff', async () => {
    const characters = new CharacterLocal();
    const created = await characters.create('test', { name: 'Old Ember', race: 'empire', className: 'Ember Arcanist', bodyVariant: 'm' });
    const state = await characters.load(created.id);
    state.equipment = { ...state.equipment, chest: 'armor_chain', mainHand: undefined };
    localStorage.setItem('war-js:local-characters', JSON.stringify({ [state.id]: state }));
    const loaded = await new CharacterLocal().load(state.id);
    expect(loaded.equipment?.chest).toBe('armor_chain');
    expect(loaded.equipment?.mainHand).toBe(EMBER_STAFF_KEY);
    state.equipment.mainHand = 'sword_veteran';
    localStorage.setItem('war-js:local-characters', JSON.stringify({ [state.id]: state }));
    expect((await new CharacterLocal().load(state.id)).equipment?.mainHand).toBe('sword_veteran');
  });

  test('female profile keeps its existing equipment defaults', async () => {
    const characters = new CharacterLocal();
    const created = await characters.create('test', { name: 'Ember Sister', race: 'empire', className: 'Ember Arcanist', bodyVariant: 'f' });
    expect((await characters.load(created.id)).equipment?.mainHand).not.toBe(EMBER_STAFF_KEY);
  });
});

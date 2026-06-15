import { describe, expect, test } from 'vitest';
import { CharacterLocal } from '../src/services/local/characterLocal';

describe('local character service GM lookup', () => {
  test('finds characters by exact case-insensitive name', async () => {
    const characters = new CharacterLocal();

    const matches = await characters.findByName('sIgMuNd');

    expect(matches).toHaveLength(1);
    expect(matches[0].name).toBe('Sigmund');
  });

  test('returns an empty list when no saved character matches', async () => {
    const characters = new CharacterLocal();

    await expect(characters.findByName('Missing Hero')).resolves.toEqual([]);
  });

  test('returns duplicate character names for the GM menu to disambiguate', async () => {
    const characters = new CharacterLocal();
    await characters.create('user-test', {
      name: 'Mirror',
      className: 'Battle Prelate',
      race: 'empire',
      bodyVariant: 'm',
    });
    await characters.create('user-test', {
      name: 'Mirror',
      className: 'Stoneguard',
      race: 'dwarf',
      bodyVariant: 'f',
    });

    const matches = await characters.findByName('mirror');

    expect(matches.map((character) => character.name)).toEqual(['Mirror', 'Mirror']);
  });
});

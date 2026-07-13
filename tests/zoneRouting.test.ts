import { describe, expect, test } from 'vitest';
import {
  defaultZoneForRace,
  normalizePlayableZoneId,
} from '../src/data/zoneRouting';

describe('playable zone routing', () => {
  test('starts Aegis and Riftbound races in their campaign capitals', () => {
    expect(defaultZoneForRace('empire')).toBe('aegis_capital');
    expect(defaultZoneForRace('dwarf')).toBe('aegis_capital');
    expect(defaultZoneForRace('high_elf')).toBe('aegis_capital');
    expect(defaultZoneForRace('chaos')).toBe('riftspire_capital');
    expect(defaultZoneForRace('greenskin')).toBe('riftspire_capital');
    expect(defaultZoneForRace('dark_elf')).toBe('riftspire_capital');
  });

  test('migrates obsolete legacy zone ids onto the campaign guide', () => {
    expect(normalizePlayableZoneId('inevitable_city', 'chaos')).toBe('riftspire_capital');
  });

  test('keeps valid campaign zones and rejects unknown map ids', () => {
    expect(normalizePlayableZoneId('brightfen_approach', 'empire')).toBe('brightfen_approach');
    expect(normalizePlayableZoneId('zone1', 'greenskin')).toBe('riftspire_capital');
    expect(normalizePlayableZoneId(undefined, 'empire')).toBe('aegis_capital');
  });
});

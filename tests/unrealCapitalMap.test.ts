import { describe, expect, it } from 'vitest';
import { parseCapitalMap } from '../scripts/unreal/capital-map';

describe('official capital selection', () => {
  it('uses the selected owner map, ignoring unrelated sections', () => {
    expect(parseCapitalMap('[Other]\nGameDefaultMap=/Game/Old\n[/Script/EngineSettings.GameMapsSettings]\r\nGameDefaultMap=/Game/Capitals/crownward/Final/City\r\n[Other2]\nGameDefaultMap=/Game/Wrong'))
      .toBe('/Game/Capitals/crownward/Final/City');
  });
  it('rejects missing, unrelated and unsafe package paths', () => {
    for (const map of ['', '/Game/Old', '/Game/Capitals/crownward/../Old'])
      expect(() => parseCapitalMap('[/Script/EngineSettings.GameMapsSettings]\nGameDefaultMap=' + map)).toThrow();
  });
});

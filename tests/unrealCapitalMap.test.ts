import { describe, expect, it } from 'vitest';
import { parseCapitalMap } from '../scripts/unreal/capital-map';

describe('official capital selection', () => {
  it('uses the selected owner map, ignoring unrelated sections', () => {
    expect(parseCapitalMap('[Other]\nGameDefaultMap=/Game/Old\n[/Script/EngineSettings.GameMapsSettings]\r\nGameDefaultMap=/Game/Capitals/crownward/Final/City\r\n[Other2]\nGameDefaultMap=/Game/Wrong'))
      .toBe('/Game/Capitals/crownward/Final/City');
  });
  it('rejects missing, unrelated and unsafe package paths', () => {
    for (const map of ['', '/Game/Old', '/Game/Capitals/crownward/../Old',
      '/Game/WorldRebuild/AegisCitadel_abcdef123456/ReviewCandidate',
      '/Game/WorldRebuild/AegisCitadel_ABCDEF123456/CampaignCandidate',
      '/Game/WorldRebuild/AegisCitadel_abcdef123456/CampaignCandidate/Extra',
      '/Game/WorldRebuild/DutchBastion_abcdef123456/Preview'])
      expect(() => parseCapitalMap('[/Script/EngineSettings.GameMapsSettings]\nGameDefaultMap=' + map)).toThrow();
  });
  it('accepts exact migrated campaign defaults and rejects ambiguous selections', () => {
    for (const map of ['/Game/WorldRebuild/DutchBastion_abcdef123456/Bastion_Campaign_v3',
      '/Game/WorldRebuild/AegisCitadel_abcdef123456/CampaignCandidate']) {
      const config = '[/Script/EngineSettings.GameMapsSettings]\r\nGameDefaultMap=' + map;
      expect(parseCapitalMap(config)).toBe(map);
      expect(() => parseCapitalMap(config + '\nGameDefaultMap=' + map)).toThrow();
      expect(() => parseCapitalMap(config + '\nGameDefaultMap=')).toThrow();
    }
  });
});

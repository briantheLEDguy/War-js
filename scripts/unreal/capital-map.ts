import { readFileSync } from 'node:fs';
import path from 'node:path';
import { repoRoot } from './toolchain';

/** Packaging and proofs follow the owner's selected map, never a generation receipt. */
export function parseCapitalMap(config: string): string {
  const section = config.split('[/Script/EngineSettings.GameMapsSettings]')[1]?.split(/^\[/m)[0];
  const maps = [...(section?.matchAll(/^GameDefaultMap=(.*)$/gm) ?? [])];
  const map = maps.length === 1 ? maps[0][1].trim() : undefined;
  const supported = map && (/^\/Game\/Capitals\/crownward\/[A-Za-z0-9_/]+$/.test(map)
    || /^\/Game\/WorldRebuild\/DutchBastion_[a-f0-9]{12}\/Bastion_Campaign_v3$/.test(map)
    || /^\/Game\/WorldRebuild\/AegisCitadel_[a-f0-9]{12}\/CampaignCandidate$/.test(map));
  if (!map || !supported) throw new Error('Configure one supported capital GameDefaultMap before packaging or testing the city.');
  return map;
}

export function officialCapitalMap(): string {
  return parseCapitalMap(readFileSync(path.join(repoRoot, 'unreal/AegisWar/Config/DefaultEngine.ini'), 'utf8'));
}

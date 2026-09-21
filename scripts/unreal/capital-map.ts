import { readFileSync } from 'node:fs';
import path from 'node:path';
import { repoRoot } from './toolchain';

/** Packaging and proofs follow the owner's selected map, never a generation receipt. */
export function parseCapitalMap(config: string): string {
  const section = config.split('[/Script/EngineSettings.GameMapsSettings]')[1]?.split(/^\[/m)[0];
  const maps = section?.match(/^GameDefaultMap=(.+)$/m);
  const map = maps?.[1].trim();
  if (!map || !/^\/Game\/Capitals\/crownward\/[A-Za-z0-9_/]+$/.test(map))
    throw new Error('Configure a Crownward GameDefaultMap before packaging or testing the city.');
  return map;
}

export function officialCapitalMap(): string {
  return parseCapitalMap(readFileSync(path.join(repoRoot, 'unreal/AegisWar/Config/DefaultEngine.ini'), 'utf8'));
}

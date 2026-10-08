import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import path from 'node:path';
import { battlefieldScenes } from './t1-battlefield-scenes';
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { canonicalJson, sha256 } from './content-contract';
import { repoRoot, isMain } from './toolchain';
export function prepareScenes(): void {
  const base = path.join(repoRoot, 'artifacts/unreal/t1-redesign'), parentFile = path.join(base, 'battlefield-latest.json'), parent = JSON.parse(readFileSync(parentFile, 'utf8'));
  const qualifiedParent = 'artifacts/unreal/t1-redesign/battlefield-' + parent.signature.slice(0, 12) + '.json';
  if (sha256(readFileSync(path.join(repoRoot, qualifiedParent))) !== sha256(readFileSync(parentFile))) throw new Error('Frozen battlefield parent differs from latest');
  const inputs: Record<string, string> = { [qualifiedParent]: sha256(readFileSync(parentFile)) };
  const zones = parent.zones.map((z: { id: string; sourceDirectory: string }) => {
    const file = z.sourceDirectory + '/' + z.id + '.json', bytes = readFileSync(path.join(repoRoot, file)); inputs[file] = sha256(bytes);
    return { id: z.id, scenes: battlefieldScenes(JSON.parse(bytes.toString()) as ZoneDefinition) };
  });
  for (const file of ['scripts/unreal/t1-battlefield-scenes.ts', 'scripts/unreal/prepare-t1-battlefield-scenes.ts']) inputs[file] = sha256(readFileSync(path.join(repoRoot, file)));
  const signature = sha256(canonicalJson({ parent: parent.signature, inputs, zones })), directory = path.join(base, 'battlefield-scenes', signature.slice(0, 12));
  if (existsSync(directory)) throw new Error('Preserve the existing scene recipe');
  mkdirSync(directory, { recursive: true });
  const result = { signature, parent: parent.signature, inputs, zones, appearanceApproved: false, combatCoverAccepted: false };
  writeFileSync(path.join(directory, 'source.json'), canonicalJson(result)); writeFileSync(path.join(base, 'battlefield-scenes-source-latest.json'), canonicalJson(result));
  console.log(JSON.stringify({ signature: signature.slice(0, 12), zones: zones.map((z: { id: string; scenes: ReturnType<typeof battlefieldScenes> }) => ({ id: z.id, placements: z.scenes.reduce((n, c) => n + c.placements.length, 0) })) }));
}
if (isMain(import.meta.url)) prepareScenes();

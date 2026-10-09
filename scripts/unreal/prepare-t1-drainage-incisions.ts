/** Immutable drainage-incision source study; no native map, campaign or owner-document writes. */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import { drainageIncisions } from './t1-drainage-incisions';
import { outdoorTerrain, outdoorRoads } from './world-portals';
import { canonicalJson, sha256 } from './content-contract';
import { repoRoot, isMain } from './toolchain';

export function prepareDrainageIncisions(parentRevision?: string): void {
  const base = path.join(repoRoot, 'artifacts/unreal/t1-redesign');
  if (parentRevision && !/^[a-f0-9]{12}$/.test(parentRevision)) throw new Error('Invalid qualified terrain parent');
  const parentBytes = readFileSync(parentRevision ? path.join(base, 'battlefield', parentRevision, 'source.json') : path.join(base, 'battlefield-source-latest.json'));
  const parent = JSON.parse(parentBytes.toString());
  if (parent.study === 'drainage-incisions') throw new Error('Preserve existing drainage incision sources');
  const qualifiedParent = parent.directory + '/source.json';
  if (sha256(readFileSync(path.join(repoRoot, qualifiedParent))) !== sha256(parentBytes)) throw new Error('Qualified terrain parent differs');
  const inputs: Record<string, string> = { ...parent.inputs, ...parent.files, [qualifiedParent]: sha256(parentBytes) };
  // The new optional evaluator is a deliberate compatible tool revision. All other parent bindings stay exact.
  const previousFieldToolSha256 = inputs['shared/terrainField.ts'];
  inputs['shared/terrainField.ts'] = sha256(readFileSync(path.join(repoRoot,'shared/terrainField.ts')));
  for (const [file,digest] of Object.entries(inputs)) if (sha256(readFileSync(path.join(repoRoot,file))) !== digest) throw new Error('Preserve changed drainage parent binding: '+file);
  const read = (file: string) => JSON.parse(readFileSync(path.join(repoRoot, file), 'utf8'));
  const studies: ReturnType<typeof drainageIncisions>[] = parent.zones.map((r: { zone: string }) => drainageIncisions(read(parent.directory + '/' + r.zone + '.json')));
  const pockets = Object.fromEntries(studies.map((study: ReturnType<typeof drainageIncisions>) => {
    const id = study.zone.id, rows = read(parent.directory + '/' + id + '_pockets.json');
    const h = createOrvrGridHeightSampler(study.zone.orvrLayout!.terrain, study.zone.size, study.zone.segments, study.zone.spatial);
    for (const p of rows) {
      if (Math.abs(h(p.x, p.z) - p.bedY) > .01) throw new Error('Drainage incision study moves a retained pocket bed');
      if (p.cosmeticWater) for (let i = 0; i < 96; i++) {
        if (h(p.x + Math.cos(i * Math.PI / 48) * (p.radius + 60), p.z + Math.sin(i * Math.PI / 48) * (p.radius + 60)) < p.waterY + .03) throw new Error('Drainage incision study opens a retained water basin');
      }
    }
    return [id, rows];
  }));
  const maps: ZoneDefinition[] = read('artifacts/unreal/t1-redesign/plan.json').zones.map((z: { id: string }) => read(parent.directory + '/maps/' + z.id + '.json'));
  for (const study of studies) maps[maps.findIndex(z => z.id === study.zone.id)] = study.zone;
  for (const z of maps) for (const t of z.zoneTriggers ?? []) {
    if (!studies.some((s: ReturnType<typeof drainageIncisions>) => s.zone.id === t.targetZoneId)) continue;
    const reciprocal = maps.find(z => z.id === t.targetZoneId)!.zoneTriggers!.find(r => r.targetZoneId === z.id);
    if (!reciprocal?.arrivalPoint) throw new Error('Drainage incision study lacks reciprocal arrival');
    t.targetSpawn = { ...reciprocal.arrivalPoint };
  }
  for (const file of ['shared/terrainField.ts','scripts/unreal/t1-drainage-trace.ts','scripts/unreal/t1-drainage-incisions.ts','scripts/unreal/prepare-t1-drainage-incisions.ts']) inputs[file] = sha256(readFileSync(path.join(repoRoot, file)));
  const signature = sha256(canonicalJson({ parent: parent.signature, inputs, studies, pockets }));
  const directory = path.join(base, 'battlefield', signature.slice(0, 12));
  if (existsSync(directory)) throw new Error('Preserve existing drainage incision source revision');
  mkdirSync(path.join(directory, 'maps'), { recursive: true });
  const files: Record<string, string> = {};
  const save = (name: string, data: unknown) => {
    const bytes = JSON.stringify(data), file = path.join(directory, name);writeFileSync(file, bytes);files[path.relative(repoRoot, file).replaceAll('\\', '/')] = sha256(bytes);
  };
  for (const study of studies) {
    const z = study.zone;save(z.id + '.json', z);save(z.id + '_terrain.json', outdoorTerrain(z));save(z.id + '_roads.json', outdoorRoads(z));save(z.id + '_pockets.json', pockets[z.id]);save(z.id + '_links.json', read(parent.directory + '/' + z.id + '_links.json'));
  }
  for (const z of maps) save('maps/' + z.id + '.json', z);
  const receipt = { ...parent, signature, directory: path.relative(repoRoot, directory).replaceAll('\\', '/'), parentTerrain: parent.signature, study: 'drainage-incisions', previousFieldToolSha256, inputs, files,
    zones: studies.map((s: ReturnType<typeof drainageIncisions>) => ({ zone: s.zone.id, maximumGrade: Math.max(...s.grades.map(g => g.maximumGrade)), routeGrades: s.grades, flowChecks: s.flowChecks, rejectedSeeds: s.rejectedSeeds, appearanceApproved: false, drivingAccepted: false })), nativeBuilt: false, activeMapsChanged: false, appearanceApproved: false };
  writeFileSync(path.join(directory, 'source.json'), canonicalJson(receipt));writeFileSync(path.join(base, 'battlefield-source-latest.json'), canonicalJson(receipt));
  console.log(JSON.stringify({ signature: signature.slice(0, 12), zones: receipt.zones.map((z: { zone: string; maximumGrade: number; flowChecks: unknown[] }) => ({ id: z.zone, maximumGrade: z.maximumGrade, incisions: z.flowChecks.length })), nativeBuilt: false }));
}
if (isMain(import.meta.url)) prepareDrainageIncisions(process.argv.find(a => a.startsWith('--parent='))?.slice(9));

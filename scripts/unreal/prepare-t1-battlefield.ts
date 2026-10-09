/** Immutable terrain/Node source bundle; never rewrites previous plans, active maps or private scenes. */
import { existsSync, mkdirSync, readFileSync, writeFileSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { battlefieldLandscape, BATTLEFIELD_ZONES, offRoadLinks, scarpClimbs } from './t1-battlefield-landscape';
import { landscapePockets } from './t1-landscape-pockets';
import { battlefieldGrades } from './t1-battlefield-grades';
import { outdoorRoads, outdoorTerrain } from './world-portals';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { canonicalJson, sha256 } from './content-contract';
import { isMain, repoRoot } from './toolchain';

interface ReviewBaseline {
  signature: string; parentSignature: string; sourcePackagesUnchanged: boolean;
  ownerDocumentsPreserved: boolean; inputs: { createdUtc: string };
}
export function battlefieldBaseline(candidates: Array<{ name: string; receipt: ReviewBaseline }>, parent: string) {
  return candidates.filter(({ name, receipt }) => receipt.parentSignature === parent && receipt.sourcePackagesUnchanged
    && receipt.ownerDocumentsPreserved && name === `review-${receipt.signature.slice(0, 12)}.json`)
    .sort((a, b) => b.receipt.inputs.createdUtc.localeCompare(a.receipt.inputs.createdUtc))[0];
}

export function prepareBattlefield(): void {
  const base = path.join(repoRoot, 'artifacts/unreal/t1-redesign');
  const bindings: Record<string, string> = {};
  const read = (file: string) => { const bytes = readFileSync(path.join(repoRoot, file)); bindings[file] = sha256(bytes); return JSON.parse(bytes.toString().replace(/^\uFEFF/, '')); };
  const parent = read('artifacts/unreal/t1-redesign/relief-latest.json');
  // The latest walkthrough changes when this study is staged. Bind the preserved baseline by revision.
  const baseline = battlefieldBaseline(readdirSync(base).filter(name => /^review-[a-f0-9]{12}\.json$/.test(name)).map(name => ({
    name, receipt: JSON.parse(readFileSync(path.join(base, name), 'utf8'))
  })), parent.signature);
  if (parent.study !== 'dramatic-relief' || !baseline) throw new Error('Expected a preserved relief/walkthrough baseline');
  const parentWalkthroughFile = 'artifacts/unreal/t1-redesign/' + baseline.name, walkthrough = read(parentWalkthroughFile);
  const pocketPlans = BATTLEFIELD_ZONES.map(id => {
    const homes = parent.zones.find((z: { id: string }) => z.id === id).homes.map((h: { id: string; route: number[][]; approachPoints: number }) => ({
      id: h.id, points: h.route.slice(0, h.approachPoints).map(p => ({ x: p[1] / 100, z: p[0] / 100, y: p[2] / 100 }))
    }));
    return landscapePockets(battlefieldLandscape(read(`artifacts/unreal/t1-redesign/${id}.json`) as ZoneDefinition, homes));
  });
  const zones = pocketPlans.map(p=>p.zone);
  // Reciprocal arrivals remain explicit in the candidate-only 32-map bundle.
  const maps: ZoneDefinition[] = read('artifacts/unreal/t1-redesign/plan.json').zones.map((z: { id: string }) => read(`artifacts/unreal/t1-redesign/maps/${z.id}.json`) as ZoneDefinition);
  for (const z of zones) maps[maps.findIndex((m: ZoneDefinition) => m.id === z.id)] = z;
  for (const z of maps) for (const t of z.zoneTriggers ?? []) {
    if (!BATTLEFIELD_ZONES.includes(t.targetZoneId as typeof BATTLEFIELD_ZONES[number])) continue;
    t.targetSpawn = { ...maps.find((m: ZoneDefinition) => m.id === t.targetZoneId)!.zoneTriggers!.find(r => r.targetZoneId === z.id)!.arrivalPoint! };
  }
  const tools = ['shared/terrainField.ts', 'shared/orvrTerrain.ts', 'shared/world/RoadSurface.ts', 'scripts/unreal/t1-battlefield-grades.ts',
    'scripts/unreal/t1-battlefield-landscape.ts', 'scripts/unreal/t1-landscape-pockets.ts', 'scripts/unreal/prepare-t1-battlefield.ts', 'scripts/unreal/world-portals.ts'];
  for (const file of tools) bindings[file] = sha256(readFileSync(path.join(repoRoot, file)));
  const signature = sha256(canonicalJson({ bindings, zones })), directory = path.join(base, 'battlefield', signature.slice(0, 12));
  if (existsSync(directory)) throw new Error('Preserve an existing battlefield source revision');
  mkdirSync(path.join(directory, 'maps'), { recursive: true });
  const files: Record<string, string> = {}, save = (name: string, data: unknown) => {
    const bytes = JSON.stringify(data); writeFileSync(path.join(directory, name), bytes); files[path.relative(repoRoot, path.join(directory, name)).replaceAll('\\', '/')] = sha256(bytes);
  };
  const reports = [];
  for (const z of zones) {
    save(z.id + '_pockets.json', pocketPlans.find(p=>p.zone.id===z.id)!.pockets);
    save(z.id + '.json', z); save(z.id + '_terrain.json', outdoorTerrain(z)); save(z.id + '_roads.json', outdoorRoads(z));
    const links = offRoadLinks(z.id); save(z.id + '_links.json', links);
    const h = createOrvrGridHeightSampler(z.orvrLayout!.terrain, z.size, z.segments, z.spatial);
    const routeGrades = battlefieldGrades([...z.paths!, ...links, ...scarpClimbs(z.id), ...pocketPlans.find(p=>p.zone.id===z.id)!.pockets.map(p=>({id:p.id,width:6,points:p.approach}))], h);
    const maximumGrade = Math.max(...routeGrades.map(r => r.maximumGrade)), samples = routeGrades.reduce((sum, r) => sum + r.samples, 0);
    if (maximumGrade > .22) throw new Error(`Battlefield grades fail: ${z.id} ${JSON.stringify(routeGrades.filter(r => r.maximumGrade > .22))}`);
    reports.push({ zone: z.id, maximumGrade, fullWidthSamples: samples, routeGrades, offRoadLinks: links.length, scarpClimbs: 2, routeElevationsChanged: true,
      appearanceApproved: false, drivingAccepted: false, eighteenVersusEighteenAccepted: false });
  }
  for (const z of maps) save('maps/' + z.id + '.json', z);
  const receipt = { signature, directory: path.relative(repoRoot, directory).replaceAll('\\', '/'), parentRelief: parent.signature,
    parentWalkthrough: walkthrough.signature, parentWalkthroughFile, inputs: bindings, files, zones: reports, activeMapsChanged: false, nativeBuilt: false, appearanceApproved: false };
  writeFileSync(path.join(directory, 'source.json'), canonicalJson(receipt));
  writeFileSync(path.join(base, 'battlefield-source-latest.json'), canonicalJson(receipt));
  console.log(JSON.stringify({ signature: signature.slice(0, 12), zones: reports, activeMapsChanged: false, nativeBuilt: false }));
}
if (isMain(import.meta.url)) prepareBattlefield();

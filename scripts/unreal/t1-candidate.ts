import { mkdirSync, readFileSync, writeFileSync, existsSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { CAMPAIGN_NODES } from '../../shared/data/campaign.generated';
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { redesignT1, T1_REGIONS } from './t1-layouts';
import { moduleLocalPoint, villagePlan } from './t1-modules';
import { regionalSceneModules } from './t1-scene-modules';
import { outdoorTerrain, outdoorRoads, portalPlan, terrainHeight } from './world-portals';
import { canonicalJson, sha256 } from './content-contract';
import { isMain, repoRoot } from './toolchain';

const escape = (value: string) => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
export function topologyDrawing(zone: ZoneDefinition): string {
  const r = T1_REGIONS[zone.id], b = zone.spatial!.bounds;
  const project = (p: { x: number; z: number }) => `${(p.x - b.minX) / (b.maxX - b.minX) * 960 + 30},${(b.maxZ - p.z) / (b.maxZ - b.minZ) * 620 + 100}`;
  const xy = (p: number[]) => project({ x: p[0], z: p[1] });
  const text = (p: { x: number; z: number }, label: string) => `<text x="${project(p).split(',')[0]}" y="${Number(project(p).split(',')[1]) - 14}" class="label">${escape(label)}</text>`;
  const parts = [`<svg xmlns="http://www.w3.org/2000/svg" width="1020" height="840" viewBox="0 0 1020 840"><style>text{font-family:Segoe UI,Arial;fill:#e8e7db}.label{font-size:12px;paint-order:stroke;stroke:#172227;stroke-width:3px}.title{font-size:27px}.note{font-size:13px}</style><rect width="1020" height="840" fill="#172227"/><text x="30" y="38" class="title">${escape(zone.name)} — topology candidate</text><text x="30" y="66" class="note">${escape(r.theme)}</text><polygon points="${zone.spatial!.playableOutline.map(project).join(' ')}" fill="${r.palette[0]}" stroke="#d4c99d" stroke-width="2"/>`];
  for (const [x, z, rx, rz, h] of r.landforms) if (h > 0) parts.push(`<ellipse cx="${xy([x, z]).split(',')[0]}" cy="${xy([x, z]).split(',')[1]}" rx="${rx / (b.maxX - b.minX) * 960}" ry="${rz / (b.maxZ - b.minZ) * 620}" fill="#ddd6b1" opacity=".13"/>`);
  for (const [i, route] of (zone.paths ?? []).entries()) parts.push(`<polyline points="${route.points.map(project).join(' ')}" fill="none" stroke="${i === 0 ? '#ffe5a1' : i < 3 ? '#83d4e1' : i < 5 ? '#eea4e2' : '#c9c8ae'}" stroke-width="${i < 3 ? 5 : 3}" stroke-linejoin="round"/>`);
  for (const keep of zone.orvrLayout!.keeps) parts.push(`<rect x="${Number(project(keep).split(',')[0]) - 14}" y="${Number(project(keep).split(',')[1]) - 12}" width="28" height="24" fill="${keep.realm === 'aegis' ? '#244e7b' : '#842c38'}" stroke="#fff"/>`, text(keep, `${keep.realm} keep`));
  for (const [i, bo] of zone.orvrLayout!.battlefieldObjectives.entries()) parts.push(`<circle cx="${project(bo).split(',')[0]}" cy="${project(bo).split(',')[1]}" r="10" fill="#ffe5a1" stroke="#172227"/>`, text(bo, `Objective ${i + 1}`));
  for (const camp of zone.orvrLayout!.stagingCamps) parts.push(`<circle cx="${project(camp).split(',')[0]}" cy="${project(camp).split(',')[1]}" r="15" fill="none" stroke="#fff" stroke-dasharray="3 3"/>`, text(camp, `${camp.realm} staging`));
  const v = { x: r.village[0], z: r.village[1] };
  for (const module of villagePlan(zone).modules) parts.push(`<polygon points="${[[-1, -1], [-1, 1], [1, 1], [1, -1]].map(([x, z]) => project(moduleLocalPoint(module, { x: x * module.reservation.width / 2, z: z * module.reservation.depth / 2 }))).join(' ')}" fill="${module.interiorRequired ? '#91e0c4' : '#eed6b1'}"/>`);
  parts.push(text({ ...v, z: v.z + 90 }, 'Village: 20 building target'), text({ x: r.lair[0], z: r.lair[1] }, 'Optional lair approach'));
  for (const i of [3, 5]) parts.push(text(zone.paths![0].points[i], `Rotation ${i === 3 ? 1 : 2}`));
  parts.push(`<text x="30" y="757" class="note">${r.width} × ${r.depth} m playable target · main advance (gold) · two vehicle flanks (cyan) · rotation links (pink)</text><text x="30" y="782" class="note">Supply itineraries: ${zone.orvrLayout!.caravanRoutes.map(r => r.lengthMetres + ' m').join(' / ')}</text><text x="30" y="807" class="note">Building marks reserve capacity. Interiors, visual approval, drive tests and 18v18 acceptance remain pending.</text></svg>`);
  return parts.join('\n');
}

function privateMapHashes(directory: string): Record<string, string> {
  if (!existsSync(directory)) return {};
  return Object.fromEntries(readdirSync(directory, { recursive: true, withFileTypes: true }).filter(row => row.isFile() && !row.parentPath.includes('T1Redesign_') && /\.(umap|uasset)$/.test(row.name))
    .map(row => { const absolute = path.join(row.parentPath, row.name); return [path.relative(repoRoot, absolute).replaceAll('\\', '/'), sha256(readFileSync(absolute))]; }));
}
export function generateT1Candidates(): void {
  const directory = path.join(repoRoot, 'artifacts/unreal/t1-redesign'); mkdirSync(directory, { recursive: true });
  const inputs = CAMPAIGN_NODES.map(node => ({ id: node.id, bytes: readFileSync(path.join(repoRoot, 'public/assets/maps', node.id + '.json')) }));
  const maps = inputs.map(row => redesignT1(JSON.parse(row.bytes.toString()) as ZoneDefinition));
  for (const source of maps) for (const trigger of source.zoneTriggers ?? []) {
    const target = maps.find(map => map.id === trigger.targetZoneId)!;
    if (target.spatial) { const reverse = target.zoneTriggers!.find(row => row.targetZoneId === source.id)!; trigger.targetSpawn = { ...reverse.arrivalPoint! }; }
  }
  const plan = portalPlan(maps), terrainHashes: Record<string, string> = {}, prototypeHashes: Record<string, string> = {}, moduleHashes: Record<string, string> = {}, sceneHashes: Record<string, string> = {};
  const mapDirectory = path.join(directory, 'maps'); mkdirSync(mapDirectory, { recursive: true });
  for (const map of maps) writeFileSync(path.join(mapDirectory, map.id + '.json'), canonicalJson(map));
  for (const zone of maps.filter(z => T1_REGIONS[z.id])) {
    writeFileSync(path.join(directory, zone.id + '.json'), canonicalJson(zone));
    const svg = topologyDrawing(zone); writeFileSync(path.join(directory, zone.id + '.svg'), svg);
    const docs = path.join(repoRoot, 'docs/t1-topology'); mkdirSync(docs, { recursive: true }); writeFileSync(path.join(docs, zone.id + '.svg'), svg);
    for (const [suffix, data] of [['_terrain', outdoorTerrain(zone)], ['_roads', outdoorRoads(zone)]] as const) {
      if (!data) continue; const bytes = JSON.stringify(data); writeFileSync(path.join(directory, zone.id + suffix + '.json'), bytes); terrainHashes[zone.id + suffix] = sha256(bytes);
    }
    // Prototype only admitted, regional source models. Full village dressing follows camera review.
    const modules = villagePlan(zone);
    const moduleBytes = canonicalJson(modules); moduleHashes[zone.id] = sha256(moduleBytes);
    writeFileSync(path.join(directory, zone.id + '_modules.json'), moduleBytes);
    const landmarkKey = zone.id === 'sunmeadow_march' ? 'frontier_sunmeadow_oak_pasture' : zone.id === 'cinderfen_outskirts' ? 'frontier_cinderfen_basalt_outcrop' : undefined;
    const region = T1_REGIONS[zone.id];
    type Prototype = {
id: string; assetKey: string; x: number; z: number; rotY: number; scale: number; y?: number;
      reservation: { width: number; depth: number; height: number }; interiorRequired: boolean; practical?: { heightAboveFixture: number; lumens: number }
};
    const prototypes: Prototype[] = modules.modules.filter(module => module.assetKey).map(module => ({
id: module.id, assetKey: module.assetKey!,
      x: module.x, z: module.z, rotY: module.rotY, scale: 1, reservation: module.reservation, interiorRequired: module.interiorRequired
}));
    for (const module of modules.modules) if (module.practical) {
const fixture = module.practical;
      prototypes.push({
id: module.id + '_lantern', assetKey: fixture.assetKey, x: fixture.x, z: fixture.z, rotY: fixture.rotY, scale: 1, y: fixture.y,
        reservation: { width: 3, depth: 3, height: 5 }, interiorRequired: false, practical: { heightAboveFixture: fixture.heightAboveFixture, lumens: fixture.lumens }
});
    }
    if (landmarkKey) prototypes.push({
id: `${zone.id}_landmark`, assetKey: landmarkKey, x: region.lair[0], z: region.lair[1] - 35,
      rotY: 0, scale: zone.id === 'sunmeadow_march' ? 1.3 : 1, reservation: { width: 40, depth: 40, height: 40 }, interiorRequired: false
});
    const scenes = regionalSceneModules(zone), sceneBytes = canonicalJson(scenes);
    sceneHashes[zone.id] = sha256(sceneBytes); writeFileSync(path.join(directory, zone.id + '_scenes.json'), sceneBytes);
    prototypes.push(...scenes.flatMap(scene => scene.placements.map(placement => ({ ...placement, interiorRequired: false }))));
    const keeps = zone.props?.filter(prop => zone.orvrLayout!.keeps.some(keep => prop.id?.startsWith(keep.objectiveId))) ?? [];
    const prototypeBytes = canonicalJson({ zoneId: zone.id, prototypes: [...prototypes, ...keeps].map(p => ({ ...p, groundY: terrainHeight(zone, p.x, p.z) })), buildingTarget: 20, furnishedHomesTarget: 2, nativeArtApproved: false });
    prototypeHashes[zone.id] = sha256(prototypeBytes); writeFileSync(path.join(directory, zone.id + '_prototype.json'), prototypeBytes);
  }
  const baseline = JSON.parse(readFileSync(path.join(repoRoot, 'artifacts/unreal/world-portals/build.json'), 'utf8'));
  const toolFiles = ['scripts/unreal/t1-candidate.ts', 'scripts/unreal/t1-layouts.ts', 'scripts/unreal/t1-modules.ts', 'scripts/unreal/t1-scene-modules.ts',
    'scripts/unreal/prepare-t1-prototypes.py', 'scripts/unreal/build-t1-prototypes.py', 'scripts/unreal/world_build_assets.py',
    'unreal/AegisWar/Source/AegisWar/Private/WarZoneLightingSubsystem.cpp', 'unreal/AegisWar/Source/AegisWar/Private/WarPracticalLight.cpp'];
  const result = {
...plan, sourceHashes: Object.fromEntries(inputs.map(row => [row.id, sha256(row.bytes)])), terrainHashes, prototypeHashes, moduleHashes, sceneHashes,
    candidateHashes: Object.fromEntries(maps.map(zone => [zone.id, sha256(canonicalJson(zone))])),
    toolHashes: Object.fromEntries(toolFiles.map(file => [file, sha256(readFileSync(path.join(repoRoot, file)))])),
    baselineMap: baseline.map, baselineReceiptSha256: sha256(canonicalJson(baseline)), privateMapHashes: privateMapHashes(path.join(repoRoot, 'unreal/AegisWar/Content/WorldRebuild')),
    nativeBatch: ['sunmeadow_march', 'cinderfen_outskirts'], laterBatch: ['brightfen_approach', 'ashen_steppe'], visualApproved: false, productionAccepted: false
};
  writeFileSync(path.join(directory, 'plan.json'), canonicalJson(result));
  console.log(JSON.stringify({ candidates: 4, nativeBatch: result.nativeBatch, terrainFiles: 8, activeMapsChanged: false, visualApproved: false }));
}
if (isMain(import.meta.url)) generateT1Candidates();

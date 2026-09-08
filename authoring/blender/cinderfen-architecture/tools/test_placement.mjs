/** Exercise the actual shared movement/collision functions against staged placement contracts. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';
import crypto from 'node:crypto';
import { cinderfenKeepAssembly, composeCinderfenEnvironment, loadCinderfenContracts } from '../../../../scripts/campaign/cinderfen-environment.mjs';
import { composeCinderfenLandscape } from '../../../../scripts/campaign/cinderfen-landscape.mjs';
const work = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const root = path.resolve(work, '../../..');
const hash = value => crypto.createHash('sha256').update(value).digest('hex');
const sharedPaths = ['server/mapNavigation.ts', 'src/shared/worldNavigation.ts', 'src/shared/orvrTerrain.ts', 'src/shared/orvr/navigation.ts'];
const sharedSources = await Promise.all(sharedPaths.map(file => fs.readFile(path.join(root, file), 'utf8')));
const joined = sharedSources.map((source, index) => {
  const parsed = ts.createSourceFile(sharedPaths[index], source, ts.ScriptTarget.ESNext, true);
  const withoutImports = ts.factory.updateSourceFile(parsed, parsed.statements.filter(statement => !ts.isImportDeclaration(statement)));
  return ts.createPrinter().printFile(withoutImports);
}).join('\n');
const compiled = ts.transpileModule(joined, { compilerOptions: { target: ts.ScriptTarget.ESNext, module: ts.ModuleKind.ESNext } }).outputText;
const { mapPropNavigation, supportedGroundHeight, campaignColliderContains, campaignColliderBlocksHeight, createOrvrGridHeightSampler } = await import('data:text/javascript;base64,' + Buffer.from(compiled).toString('base64'));
const contracts = loadCinderfenContracts({ staged: true });
const source = JSON.parse(await fs.readFile(path.join(root, 'public/assets/maps/cinderfen_outskirts.json'), 'utf8'));
const oldIdentities = source.orvrLayout.keeps.map(keep => ({ commander: keep.commander, deliveryPoint: keep.deliveryPoint, quartermaster: keep.quartermaster, gates: keep.gates.map(gate => [gate.id, gate.propId]) }));
const zone = composeCinderfenEnvironment(structuredClone(source), { architecture: true }, { contracts });
composeCinderfenLandscape(zone);
const groundAt=createOrvrGridHeightSampler(zone.orvrLayout.terrain,zone.size,zone.segments);
for (const [index, keep] of zone.orvrLayout.keeps.entries()) {
  const expected = oldIdentities[index];
  for (const key of ['commander', 'deliveryPoint', 'quartermaster']) assert.deepEqual(keep[key], expected[key]);
  assert.deepEqual(keep.gates.map(gate => [gate.id, gate.propId]), expected.gates);
  assert.equal(keep.posterns.length, 2);
  assert.deepEqual(keep.postern, keep.posterns[0]);
}
const rotate = (x, z, yaw) => ({ x: x * Math.cos(yaw) + z * Math.sin(yaw), z: -x * Math.sin(yaw) + z * Math.cos(yaw) });
const first = structuredClone(zone.orvrLayout.keeps[0]);
const offset = first.x; first.x = 0;
for (const gate of first.gates) gate.x -= offset;
const props = cinderfenKeepAssembly(first, contracts);
const navigation = mapPropNavigation(props, (x,z) => groundAt(x+offset,z));
const bins = new Map(), surfaceBins = new Map(), binSize = 4;
function addBins(target, item, minX, maxX, minZ, maxZ) {
  for (let x = Math.floor(minX / binSize); x <= Math.floor(maxX / binSize); x += 1) for (let z = Math.floor(minZ / binSize); z <= Math.floor(maxZ / binSize); z += 1) {
    const key = `${x},${z}`; if (!target.has(key)) target.set(key, []); target.get(key).push(item);
  }
}
for (const collider of navigation.collision) addBins(bins, collider, collider.minX - .46, collider.maxX + .46, collider.minZ - .46, collider.maxZ + .46);
for (const surface of navigation.walkableSurfaces) {
  const radius = Math.hypot(surface.width, surface.depth) / 2;
  addBins(surfaceBins, surface, surface.x - radius, surface.x + radius, surface.z - radius, surface.z + radius);
}
const nearby = (map, x, z) => map.get(`${Math.floor(x / binSize)},${Math.floor(z / binSize)}`) ?? [];
const blocked = point => nearby(bins, point.x, point.z).some(collider => campaignColliderBlocksHeight(collider, point.y) && campaignColliderContains(collider, point, .4));
const targets = [
  { id: 'commander', x: 0, y: 0, z: 4 }, { id: 'quartermaster', x: -13, y: 0, z: -60 },
  { id: 'oil_platform', x: 1.8, y: 6.3, z: -24 },
  { id: 'catapult_west', x: -18, y: 0, z: 36 }, { id: 'catapult_east', x: 18, y: 0, z: 36 },
];
for (const prop of props.filter(prop => prop.assetKey.endsWith('wall_stair'))) {
  const top = contracts.frontier_cinderfen_wall_stair.top_socket_runtime;
  const p = rotate(top[0], top[2], prop.rotY);
  targets.push({ id: prop.id, x: prop.x + p.x, y: 6.3, z: prop.z + p.z });
}
const portals = first.gates.map(gate => [{ x: 0, y: 0, z: gate.z - 3 }, { x: 0, y: 0, z: gate.z + 3 }]);
const spacing = .3, queue = [], seen = new Set(), reached = new Map();
function offer(x, z, oldY) {
  x = Math.round(x / spacing) * spacing; z = Math.round(z / spacing) * spacing;
  if (x < -40 || x > 40 || z < -82 || z > 59) return;
  const y = supportedGroundHeight(x, z, oldY, groundAt(x+offset,z), nearby(surfaceBins, x, z));
  const point = { x, y, z }, key = `${Math.round(x / spacing)},${Math.round(z / spacing)},${Math.round(y * 1000)}`;
  if (seen.has(key) || blocked(point)) return;
  seen.add(key); queue.push(point);
}
offer(0, -78, 0);
for (let head = 0; head < queue.length && reached.size < targets.length; head += 1) {
  const p = queue[head];
  for (const target of targets) if (!reached.has(target.id) && Math.hypot(p.x - target.x, p.z - target.z) < .65 && Math.abs(p.y - target.y) < .15) reached.set(target.id, p);
  for (const [dx, dz] of [[spacing, 0], [-spacing, 0], [0, spacing], [0, -spacing]]) offer(p.x + dx, p.z + dz, p.y);
  for (const pair of portals) for (let side = 0; side < 2; side += 1) if (Math.hypot(p.x - pair[side].x, p.y - pair[side].y, p.z - pair[side].z) <= 2) offer(pair[1 - side].x, pair[1 - side].z, 0);
}
const missing = targets.filter(target => !reached.has(target.id));
const villageProps=zone.props.filter(prop=>Math.hypot(prop.x-435,prop.z+245)<100);
const villageNav=mapPropNavigation(villageProps,groundAt),villageQueue=[],villageSeen=new Set(),villageReached=new Map();
const villageTargets=[...(zone.npcs??[]).map(npc=>({id:npc.id,x:npc.x,z:npc.z,y:npc.y??0})),
  ...(zone.craftingStations??[]).map(station=>({id:station.id,x:station.x,z:station.z,y:station.y??0})),
  ...villageProps.filter(prop=>prop.assetKey==='frontier_cinderfen_dwelling').map(prop=>({id:prop.id,x:prop.x,z:prop.z,y:.6}))];
const villageBlocked=p=>villageNav.collision.some(collider=>campaignColliderBlocksHeight(collider,p.y)&&campaignColliderContains(collider,p,.4));
function visitVillage(x,z,oldY){
  x=Math.round(x/.3)*.3;z=Math.round(z/.3)*.3;
  if(x<379||x>497||z<-291||z>-201)return;
  const y=supportedGroundHeight(x,z,oldY,groundAt(x,z),villageNav.walkableSurfaces),p={x,y,z};
  const key=`${Math.round(x/.3)},${Math.round(z/.3)},${Math.round(y*1000)}`;
  if(villageSeen.has(key)||villageBlocked(p))return;
  villageSeen.add(key);villageQueue.push(p);
}
visitVillage(435,-245,0);
for(let head=0;head<villageQueue.length&&villageReached.size<villageTargets.length;head+=1){
  const p=villageQueue[head];
  for(const target of villageTargets)if(!villageReached.has(target.id)&&Math.hypot(p.x-target.x,p.z-target.z)<.6&&Math.abs(p.y-target.y)<.15)villageReached.set(target.id,p);
  for(const [dx,dz]of[[.3,0],[-.3,0],[0,.3],[0,-.3]])visitVillage(p.x+dx,p.z+dz,p.y);
}
const missingVillage=villageTargets.filter(target=>!villageReached.has(target.id));
const groundSurvey=[];
for(const prop of zone.props.filter(prop=>prop.assetKey?.startsWith('frontier_cinderfen_'))){
  const bounds=contracts[prop.assetKey].boundsYUp;
  for(const x of [bounds.minimum[0],0,bounds.maximum[0]])for(const z of [bounds.minimum[2],0,bounds.maximum[2]]){
    const offset=rotate(x*(prop.scaleX??1),z*(prop.scaleZ??1),prop.rotY??0),world={x:prop.x+offset.x,z:prop.z+offset.z};
    groundSurvey.push({id:prop.id,...world,height:groundAt(world.x,world.z)});
  }
}
const maximumGroundError=Math.max(...groundSurvey.map(sample=>Math.abs(sample.height)));
const stairExample=props.find(prop=>prop.assetKey.endsWith('wall_stair'));
const stairDiagnostics=contracts.frontier_cinderfen_wall_stair.walkableSurfaces.filter(surface=>surface.id.startsWith('tread_')).slice(0,3).map(surface=>{
  const offset=rotate(surface.x,surface.z,stairExample.rotY);const point={x:stairExample.x+offset.x,y:surface.fromY,z:stairExample.z+offset.z};
  return {surface:surface.id,point,blockingColliders:nearby(bins,point.x,point.z).filter(collider=>campaignColliderBlocksHeight(collider,point.y)&&campaignColliderContains(collider,point,.4))};
});
const placementBytes = await fs.readFile(path.join(root, 'scripts/campaign/cinderfen-environment.mjs'));
const result = { toolSha256: hash(await fs.readFile(fileURLToPath(import.meta.url))), placementSourceSha256: hash(placementBytes),
  sharedMovementSources: sharedPaths.map((file, index) => ({ file, sha256: hash(sharedSources[index]) })),
  navigationContracts: await Promise.all(['navigation-contract.json', 'junction/navigation-contract.json'].map(async file => ({ file, assetsSha256: hash(JSON.stringify(JSON.parse(await fs.readFile(path.join(work, file),'utf8')).assets)) }))),
  method: 'Actual shared support-height and oriented collider functions, 0.3m navigation grid, 0.4m body radius, 1.8m height, both owner passage pairs with closed gate colliders.',
  landscapeSourceSha256:hash(await fs.readFile(path.join(root,'scripts/campaign/cinderfen-landscape.mjs'))),groundSurvey,maximumGroundError,
  visited: seen.size, stairDiagnostics, targets: targets.map(target => ({ ...target, reached: reached.get(target.id) ?? null })), missing,
  village:{visited:villageSeen.size,targets:villageTargets.map(target=>({...target,reached:villageReached.get(target.id)??null})),missing:missingVillage} };
await fs.writeFile(path.join(work, 'review/placement-navigation.json'), JSON.stringify(result, null, 2) + '\n');
await fs.writeFile(path.join(work, 'review/keep-assembly-source.json'), JSON.stringify({ placementSourceSha256: hash(placementBytes), props, targets, keep: first }, null, 2) + '\n');
console.log(JSON.stringify({ visited: seen.size, reached: reached.size, targets: targets.length, maximumReachedHeight:Math.max(...new Set(queue.map(point=>point.y))), missing,
  village:{visited:villageSeen.size,reached:villageReached.size,targets:villageTargets.length,missing:missingVillage},maximumGroundError }, null, 2));
assert.equal(missing.length, 0, 'Closed enclosures must preserve commander, service, siege and every courtyard stair route.');
assert.equal(missingVillage.length,0,'Every village NPC, service station and dwelling must be reachable through its actual entrance.');
assert.ok(maximumGroundError<=.025,'Authored ground datum must match actual sampled regional terrain at the full exported footprint.');

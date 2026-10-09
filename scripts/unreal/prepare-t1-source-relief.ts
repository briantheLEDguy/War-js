/** Immutable private source-derived relief study; no native map, campaign or owner-document writes. */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import { sourceTerrainRelief } from './t1-source-relief';
import type { TerrainRelief } from '../../shared/terrainRelief';
import { outdoorTerrain, outdoorRoads } from './world-portals';
import { canonicalJson, sha256 } from './content-contract';
import { repoRoot, isMain } from './toolchain';

export function prepareSourceRelief(parentRevision?: string): void {
  const base = path.join(repoRoot, 'artifacts/unreal/t1-redesign');
  if (parentRevision && !/^[a-f0-9]{12}$/.test(parentRevision)) throw new Error('Invalid qualified terrain parent');
  const parentBytes = readFileSync(parentRevision ? path.join(base, 'battlefield', parentRevision, 'source.json') : path.join(base, 'battlefield-source-latest.json'));
  const parent = JSON.parse(parentBytes.toString());
  if (parent.study === 'source-relief') throw new Error('Preserve existing source relief sources');
  const qualifiedParent = parent.directory + '/source.json';
  if (sha256(readFileSync(path.join(repoRoot, qualifiedParent))) !== sha256(parentBytes)) throw new Error('Qualified terrain parent differs');
  const inputs: Record<string, string> = { ...parent.inputs, ...parent.files, [qualifiedParent]: sha256(parentBytes) };
  // The new optional evaluator is a deliberate compatible tool revision. All other parent bindings stay exact.
  const previousFieldToolSha256 = inputs['shared/terrainField.ts'];
  inputs['shared/terrainField.ts'] = sha256(readFileSync(path.join(repoRoot,'shared/terrainField.ts')));
  for (const [file,digest] of Object.entries(inputs)) if (sha256(readFileSync(path.join(repoRoot,file))) !== digest) throw new Error('Preserve changed relief parent binding: '+file);
  const read = (file: string) => JSON.parse(readFileSync(path.join(repoRoot, file), 'utf8'));
  const residualDirectory = 'artifacts/unreal/t1-redesign/eroded-surface-samples/';
  const kitFile='artifacts/unreal/licensed-kits/nature-backdrop-staged.json';
  const kit=read(kitFile), extraction=read(residualDirectory+'receipt.json'), residuals=read(residualDirectory+'residual-study.json');
  inputs[kitFile]=sha256(readFileSync(path.join(repoRoot,kitFile)));
  for (const name of ['receipt.json','residual-study.json']) inputs[residualDirectory+name]=sha256(readFileSync(path.join(repoRoot,residualDirectory+name)));
  for (const name of ['extract-eroded-surfaces.py','study-eroded-residuals.py']) {
    const file='artifacts/unreal/t1-redesign/'+name;inputs[file]=sha256(readFileSync(path.join(repoRoot,file)));
  }
  // Bind every staged dependency; private derivative samples never enter the public source tree.
  for (const row of kit.files) {
    const file='unreal/AegisWar/Content/'+row.path;
    if (sha256(readFileSync(path.join(repoRoot,file)))!==row.sha256) throw new Error('Preserve changed owned relief package: '+file);
    inputs[file]=row.sha256;
  }
  const studies = parent.zones.map((r: { zone: string }) => {
    const mesh=r.zone==='sunmeadow_march'?'01':r.zone==='cinderfen_outskirts'?'03':undefined;
    if (!mesh) throw new Error('Source relief requires the first terrain batch');
    const file=residualDirectory+'SM_Mountain_Eroded_'+mesh+'-residual.json';
    const row=residuals.find((p: { file: string })=>p.file===file);
    const source=extraction.meshes.find((p: { file: string })=>p.file===row?.source);
    if (!row || !source || row.missingSamples!==0 || row.nativeIntegrated!==false
      || sha256(readFileSync(path.join(repoRoot,file)))!==row.sha256
      || sha256(readFileSync(path.join(repoRoot,source.file)))!==source.sha256) throw new Error('Source relief derivative is missing or stale');
    const geometry=read(source.file), admitted=kit.meshes.find((p: { path: string })=>p.path===geometry.source?.path);
    if (geometry.sourceInventorySha256!==inputs[kitFile] || !admitted || geometry.source.sourceSha256!==admitted.sourceSha256
      || geometry.distributionApproved!==false || !geometry.licensedDerivative) throw new Error('Source relief geometry lacks exact owned-package provenance');
    inputs[file]=row.sha256;inputs[source.file]=source.sha256;
    const data=read(file);
    if (!data.licensedDerivative || data.distributionApproved!==false || data.nativeIntegrated!==false || data.sourceMeshSha256!==source.sha256)
      throw new Error('Source relief derivative ownership is unqualified');
    const relief: TerrainRelief={bounds:data.bounds,segmentsX:data.segmentsX,segmentsZ:data.segmentsZ,samples:data.samples,edgeFade:32,ridgeMaskHeight:40};
    return sourceTerrainRelief(read(parent.directory+'/'+r.zone+'.json'),relief);
  });
  const pockets = Object.fromEntries(studies.map((study: ReturnType<typeof sourceTerrainRelief>) => {
    const id = study.zone.id, rows = read(parent.directory + '/' + id + '_pockets.json');
    const h = createOrvrGridHeightSampler(study.zone.orvrLayout!.terrain, study.zone.size, study.zone.segments, study.zone.spatial);
    for (const p of rows) {
      if (Math.abs(h(p.x, p.z) - p.bedY) > .01) throw new Error('Source relief study moves a retained pocket bed');
      if (p.cosmeticWater) for (let i = 0; i < 96; i++) {
        if (h(p.x + Math.cos(i * Math.PI / 48) * (p.radius + 60), p.z + Math.sin(i * Math.PI / 48) * (p.radius + 60)) < p.waterY + .03) throw new Error('Source relief study opens a retained water basin');
      }
    }
    return [id, rows];
  }));
  const maps: ZoneDefinition[] = read('artifacts/unreal/t1-redesign/plan.json').zones.map((z: { id: string }) => read(parent.directory + '/maps/' + z.id + '.json'));
  for (const study of studies) maps[maps.findIndex(z => z.id === study.zone.id)] = study.zone;
  for (const z of maps) for (const t of z.zoneTriggers ?? []) {
    if (!studies.some((s: ReturnType<typeof sourceTerrainRelief>) => s.zone.id === t.targetZoneId)) continue;
    const reciprocal = maps.find(z => z.id === t.targetZoneId)!.zoneTriggers!.find(r => r.targetZoneId === z.id);
    if (!reciprocal?.arrivalPoint) throw new Error('Source relief study lacks reciprocal arrival');
    t.targetSpawn = { ...reciprocal.arrivalPoint };
  }
  for (const file of ['shared/terrainField.ts','shared/terrainRelief.ts','scripts/unreal/t1-source-relief.ts','scripts/unreal/prepare-t1-source-relief.ts']) inputs[file] = sha256(readFileSync(path.join(repoRoot, file)));
  const signature = sha256(canonicalJson({ parent: parent.signature, inputs, studies, pockets }));
  const directory = path.join(base, 'battlefield', signature.slice(0, 12));
  if (existsSync(directory)) throw new Error('Preserve existing source relief source revision');
  mkdirSync(path.join(directory, 'maps'), { recursive: true });
  const files: Record<string, string> = {};
  const save = (name: string, data: unknown) => {
    const bytes = JSON.stringify(data), file = path.join(directory, name);writeFileSync(file, bytes);files[path.relative(repoRoot, file).replaceAll('\\', '/')] = sha256(bytes);
  };
  for (const study of studies) {
    const z = study.zone;save(z.id + '.json', z);save(z.id + '_terrain.json', outdoorTerrain(z));save(z.id + '_roads.json', outdoorRoads(z));save(z.id + '_pockets.json', pockets[z.id]);save(z.id + '_links.json', read(parent.directory + '/' + z.id + '_links.json'));
  }
  for (const z of maps) save('maps/' + z.id + '.json', z);
  const receipt = { ...parent, signature, directory: path.relative(repoRoot, directory).replaceAll('\\', '/'), parentTerrain: parent.signature, study: 'source-relief', previousFieldToolSha256, inputs, files,
    zones: studies.map((s: ReturnType<typeof sourceTerrainRelief>) => ({ zone: s.zone.id, maximumGrade: Math.max(...s.grades.map(g => g.maximumGrade)), routeGrades: s.grades, reliefSamples: s.zone.orvrLayout!.terrain.naturalField!.relief!.samples.length, appearanceApproved: false, drivingAccepted: false })), nativeBuilt: false, activeMapsChanged: false, appearanceApproved: false };
  writeFileSync(path.join(directory, 'source.json'), canonicalJson(receipt));writeFileSync(path.join(base, 'battlefield-source-latest.json'), canonicalJson(receipt));
  console.log(JSON.stringify({ signature: signature.slice(0, 12), zones: receipt.zones.map((z: { zone: string; maximumGrade: number; reliefSamples: number }) => ({ id: z.zone, maximumGrade: z.maximumGrade, reliefSamples: z.reliefSamples })), nativeBuilt: false }));
}
if (isMain(import.meta.url)) prepareSourceRelief(process.argv.find(a => a.startsWith('--parent='))?.slice(9));

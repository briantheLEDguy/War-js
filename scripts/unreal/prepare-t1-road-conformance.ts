/** Immutable cosmetic-road repair; terrain, gameplay coordinates and owner documents remain byte-preserved. */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
import { resolveZoneSpatial } from '../../shared/worldSpatial';
import { createOrvrGridHeightSampler } from '../../shared/orvrTerrain';
import { conformRoadSurface, type NativeRoadSurface } from './t1-road-conformance';
import { canonicalJson, sha256 } from './content-contract';
import { isMain, repoRoot } from './toolchain';

interface RoadFitReport {
  zone: string; inputTriangles: number; outputTriangles: number; inputVertices: number; outputVertices: number;
  minimumClearance: number; maximumClearance: number; terrainChanged: false; routeCoordinatesChanged: false;
  softAlphaPreserved: true; nativeBuilt: false; appearanceApproved: false; performanceAccepted: false;
}

export function prepareRoadConformance(parentRevision?: string): void {
  const base = path.join(repoRoot, 'artifacts/unreal/t1-redesign');
  if (parentRevision && !/^[a-f0-9]{12}$/.test(parentRevision)) throw new Error('Invalid qualified road parent');
  const parentBytes = readFileSync(parentRevision ? path.join(base, 'battlefield', parentRevision, 'source.json') : path.join(base, 'battlefield-source-latest.json'));
  const parent = JSON.parse(parentBytes.toString());
  if (parent.study === 'terrain-conformed-roads') throw new Error('Preserve existing conformed-road sources');
  const qualifiedParent = parent.directory + '/source.json';
  if (sha256(readFileSync(path.join(repoRoot, qualifiedParent))) !== sha256(parentBytes)) throw new Error('Qualified road parent differs');
  const inputs: Record<string, string> = { ...parent.inputs, ...parent.files, [qualifiedParent]: sha256(parentBytes) };
  for (const [file, digest] of Object.entries(inputs)) if (sha256(readFileSync(path.join(repoRoot, file))) !== digest) throw new Error('Preserve changed road parent binding: ' + file);
  const replacements = new Map<string, NativeRoadSurface>(), reports: RoadFitReport[] = [];
  for (const row of parent.zones) {
    if (!['sunmeadow_march', 'cinderfen_outskirts'].includes(row.zone)) throw new Error('Road repair admits the first pair only');
    const zone = JSON.parse(readFileSync(path.join(repoRoot, parent.directory, row.zone + '.json'), 'utf8')) as ZoneDefinition;
    if (!zone.spatial || !zone.orvrLayout?.terrain) throw new Error('Road repair requires an explicit terrain grid');
    const height = createOrvrGridHeightSampler(zone.orvrLayout.terrain, zone.size, zone.segments, zone.spatial);
    const mesh = JSON.parse(readFileSync(path.join(repoRoot, parent.directory, row.zone + '_roads.json'), 'utf8')) as NativeRoadSurface;
    const repaired = conformRoadSurface(mesh, resolveZoneSpatial(zone), height);
    let minimumClearance = Infinity, maximumClearance = -Infinity;
    for (let i = 0; i < repaired.indices.length; i += 3) {
      const p = repaired.indices.slice(i, i + 3).map(j => repaired.positions[j]);
      for (const weights of [[1 / 3, 1 / 3, 1 / 3], [.5, .5, 0], [.5, 0, .5], [0, .5, .5]]) {
        const q = [0, 1, 2].map(k => p.reduce((sum, v, j) => sum + v[k] * weights[j] / 100, 0));
        const clearance = q[2] - height(q[1], q[0]);
        minimumClearance = Math.min(minimumClearance, clearance); maximumClearance = Math.max(maximumClearance, clearance);
      }
    }
    if (Math.abs(minimumClearance - .045) > 1e-5 || Math.abs(maximumClearance - .045) > 1e-5) throw new Error('Conformed road ground support failed');
    replacements.set(row.zone + '_roads.json', repaired);
    reports.push({ zone: row.zone, inputTriangles: mesh.indices.length / 3, outputTriangles: repaired.indices.length / 3,
      inputVertices: mesh.positions.length, outputVertices: repaired.positions.length, minimumClearance, maximumClearance,
      terrainChanged: false, routeCoordinatesChanged: false, softAlphaPreserved: true, nativeBuilt: false, appearanceApproved: false, performanceAccepted: false });
  }
  for (const file of ['scripts/unreal/t1-road-conformance.ts', 'scripts/unreal/prepare-t1-road-conformance.ts']) inputs[file] = sha256(readFileSync(path.join(repoRoot, file)));
  const signature = sha256(canonicalJson({ parent: parent.signature, inputs, reports }));
  const directory = path.join(base, 'battlefield', signature.slice(0, 12));
  if (existsSync(directory)) throw new Error('Preserve existing road-fit revision');
  mkdirSync(path.join(directory, 'maps'), { recursive: true });
  const files: Record<string, string> = {};
  for (const file of Object.keys(parent.files)) {
    const relative = path.relative(path.join(repoRoot, parent.directory), path.join(repoRoot, file));
    if (relative.startsWith('..') || path.isAbsolute(relative)) throw new Error('Road parent file escapes its qualified directory');
    const bytes = replacements.has(relative) ? Buffer.from(JSON.stringify(replacements.get(relative))) : readFileSync(path.join(repoRoot, file));
    const target = path.join(directory, relative); writeFileSync(target, bytes); files[path.relative(repoRoot, target).replaceAll('\\', '/')] = sha256(bytes);
  }
  const receipt = { ...parent, signature, directory: path.relative(repoRoot, directory).replaceAll('\\', '/'), parentTerrain: parent.signature,
    study: 'terrain-conformed-roads', inputs, files, zones: parent.zones.map((z: { zone: string }) => ({ ...z, roadFitting: reports.find(r => r.zone === z.zone) })),
    terrainChanged: false, routeCoordinatesChanged: false, nativeBuilt: false, activeMapsChanged: false, appearanceApproved: false, performanceAccepted: false };
  writeFileSync(path.join(directory, 'source.json'), canonicalJson(receipt)); writeFileSync(path.join(base, 'battlefield-source-latest.json'), canonicalJson(receipt));
  console.log(JSON.stringify({ signature: signature.slice(0, 12), reports, nativeBuilt: false }));
}
if (isMain(import.meta.url)) prepareRoadConformance(process.argv.find(a => a.startsWith('--parent='))?.slice(9));

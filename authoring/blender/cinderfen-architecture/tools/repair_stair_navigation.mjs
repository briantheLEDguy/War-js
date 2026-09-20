/** Derive stair rail blockers from the literal authored pieces without changing exported geometry. */
import fs from 'node:fs';
import crypto from 'node:crypto';
import { pathToFileURL } from 'node:url';
import { Matrix4, Vector3 } from 'three';

const root = new URL('../', import.meta.url);
const assetId = 'frontier_cinderfen_wall_stair';
const round = value => Math.round(value * 1e6) / 1e6;
const read = name => JSON.parse(fs.readFileSync(new URL(name, root), 'utf8'));

/** Clip polygons at horizontal stations so high rails leave the under-stair route clear. */
function clip(points, axis, bound, below) {
  const output = [];
  for (let i = 0; i < points.length; i += 1) {
    const a = points[i], b = points[(i + 1) % points.length];
    const inA = below ? a[axis] <= bound : a[axis] >= bound;
    const inB = below ? b[axis] <= bound : b[axis] >= bound;
    if (inA) output.push(a);
    if (inA !== inB) {
      const t = (bound - a[axis]) / (b[axis] - a[axis]);
      output.push(a.map((value, index) => value + (b[index] - value) * t));
    }
  }
  return output;
}

export function measuredStairRails(source) {
  const rails = [];
  const instances = source.assets[assetId].instances;
  for (const [index, instance] of instances.entries()) {
    if (instance.part !== 'scarf_tie' || instance.scale[1] !== .46) continue;
    const part = source.parts[instance.part];
    const [rx, ry, rz] = instance.rotation_degrees.map(value => value * Math.PI / 180);
    const transform = new Matrix4().makeTranslation(...instance.location)
      .multiply(new Matrix4().makeRotationZ(rz)).multiply(new Matrix4().makeRotationY(ry)).multiply(new Matrix4().makeRotationX(rx))
      .multiply(new Matrix4().makeScale(...instance.scale));
    const vertices = part.vertices.map(vertex => {
      const point = new Vector3(...vertex).applyMatrix4(transform);
      return [point.x, point.z, -point.y];
    });
    const slope = instance.rotation_degrees[1] !== 0;
    const low = Math.min(...vertices.map(vertex => vertex[2])), high = Math.max(...vertices.map(vertex => vertex[2]));
    const count = slope ? Math.ceil((high - low) / .16) : 1;
    for (let station = 0; station < count; station += 1) {
      const from = low + (high - low) * station / count, to = low + (high - low) * (station + 1) / count;
      const points = part.faces.flatMap(face => clip(clip(face.map(i => vertices[i]), 2, from, false), 2, to, true));
      if (!points.length) continue;
      const min = [0, 1, 2].map(axis => Math.min(...points.map(point => point[axis])));
      const max = [0, 1, 2].map(axis => Math.max(...points.map(point => point[axis])));
      rails.push({ x: round((min[0] + max[0]) / 2), z: round((min[2] + max[2]) / 2),
        width: round(max[0] - min[0]), depth: round(max[2] - min[2]), minY: round(min[1]), maxY: round(max[1]),
        sourcePiece: index, sourcePart: instance.part });
    }
  }
  return rails;
}

export function repairStairNavigation() {
  const source = read('source/architecture.json');
  const rails = measuredStairRails(source);
  const colliders = [...source.assets[assetId].contract.colliders, ...rails.map(({ sourcePiece, sourcePart, ...box }) => box)];
  const contracts = read('navigation-contract.json'), metadata = read('builder-metadata.json');
  contracts.assets.find(asset => asset.assetId === assetId).colliders = colliders;
  metadata.assets[assetId].colliders = colliders;
  for (const [file, value] of [['navigation-contract.json', contracts], ['builder-metadata.json', metadata]]) {
    const output = new URL(file, root), temporary = new URL(`${file}.pending`, root);
    fs.writeFileSync(temporary, JSON.stringify(value, null, 2) + '\n'); fs.renameSync(temporary, output);
  }
  const sha = file => crypto.createHash('sha256').update(fs.readFileSync(new URL(file, root))).digest('hex');
  fs.writeFileSync(new URL('review/stair-rail-collision.json', root), JSON.stringify({
    sourceSha256: sha('source/architecture.json'), modelSha256: contracts.assets.find(asset => asset.assetId === assetId).modelSha256,
    method: 'Four sloped handrails clipped at <=0.16m longitudinal intervals, plus rear landing rail; tight authored-cage bounds retain elevated clearance. Existing treads and posts retained.',
    originalColliderCount: source.assets[assetId].contract.colliders.length, railColliderCount: rails.length, rails,
  }, null, 2) + '\n');
  return rails.length;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) console.log(`Added ${repairStairNavigation()} measured stair rail collision segments.`);

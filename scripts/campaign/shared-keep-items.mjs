import fs from 'node:fs';
import { roadPropFootprints } from './orvr-road-network.mjs';

const KEEP_FURNISHINGS = [
  { key: 'frontier_siege_repair_bench', role: 'repair_bench', sign: -1, candidates: [[8, 8], [8, 4], [8, 0], [6, 8], [6, 0]] },
  { key: 'frontier_siege_ammunition_cradle', role: 'ammunition', sign: 1, candidates: [[8, 8], [8, 4], [8, 0], [6, 8], [6, 0]] },
  { key: 'frontier_field_apothecary', role: 'apothecary', sign: -1,
    candidates: [[8, -6], [6, -6], [8, 13], [6, 13], [8, 3], [6, 10], [5, -6]] },
];
export const SHARED_KEEP_ITEMS = KEEP_FURNISHINGS.map(item => item.key);

export function sharedKeepItemMetadata() {
  return Object.assign({}, ...['frontier-workshop-items', 'field-apothecary'].map(name => {
    const file = new URL(`../../authoring/blender/${name}/builder-metadata.json`, import.meta.url);
    return fs.existsSync(file) ? JSON.parse(fs.readFileSync(file, 'utf8')).assets : {};
  }));
}

const overlaps = (a, b, gap = 0) => a.minX < b.maxX + gap && a.maxX > b.minX - gap
  && a.minZ < b.maxZ + gap && a.maxZ > b.minZ - gap;
const pointBox = (point, radius) => ({ minX: point.x - radius, maxX: point.x + radius,
  minZ: point.z - radius, maxZ: point.z + radius });

/** Reserve the complete visible object and the measured standing/work area. */
export function sharedKeepItemEnvelopes(prop, contract) {
  const { minimum: lo, maximum: hi } = contract.boundsYUp;
  const source = contract.approachSource;
  const boxes = [
    { x: (lo[0] + hi[0]) / 2, z: (lo[2] + hi[2]) / 2, width: hi[0] - lo[0], depth: hi[2] - lo[2] },
    // Authoring is Z-up; glTF maps source -Y to runtime +Z.
    { x: (source.minimum[0] + source.maximum[0]) / 2, z: -(source.minimum[1] + source.maximum[1]) / 2,
      width: source.maximum[0] - source.minimum[0], depth: source.maximum[1] - source.minimum[1] },
  ];
  return roadPropFootprints({ ...prop, colliders: boxes });
}

/** No unmeasured placeholder collisions: wait for a hash-matched published contract. */
export function integrateSharedKeepItems(zone, assets, metadata = sharedKeepItemMetadata()) {
  const occupied = zone.props.flatMap(roadPropFootprints);
  const actors = [...zone.npcs ?? [], ...zone.enemies ?? []].map(actor => pointBox(actor, 1.5));
  for (const keep of zone.orvrLayout.keeps) {
    const protectedAreas = [pointBox({ x: keep.x, z: keep.z + 4 }, 4),
      ...keep.gates.map(gate => pointBox(gate, 4)),
      ...keep.siegeSlots.map(slot => pointBox(slot, 4)),
      ...[keep.postern, ...keep.posterns ?? []].filter(Boolean)
        .flatMap(postern => [pointBox(postern.inside, 2), pointBox(postern.outside, 2)]), ...actors];
    for (const { key, role, sign, candidates } of KEEP_FURNISHINGS) {
      const asset = assets.staticProps[key], contract = metadata[key];
      if (!asset?.runtimeReady || !contract?.runtimeReady || !asset.modelSha256
        || contract.modelSha256 !== asset.modelSha256 || !contract.colliders?.length
        || !contract.boundsYUp || !contract.approachSource) continue;
      // Human-scale inner-court work bays, away from the central commander route.
      // Candidates remain in the narrowest keep; measured solids reject conflicts.
      for (const [x, z] of candidates) {
        const prop = { id: `${zone.id}_delivered_${keep.realm}_${role}`,
          kind: key, assetKey: key, model: asset.model, x: keep.x + sign * x, z: keep.z + z,
          rotY: 0, scale: 1, colliderSpace: 'model', cameraSolid: contract.cameraSolid ?? true,
          colliders: structuredClone(contract.colliders), walkableSurfaces: structuredClone(contract.walkableSurfaces ?? []),
          ...(zone.orvrLayout.architecture?.floorDatum === undefined ? {} :
            { y: zone.orvrLayout.architecture.floorDatum, heightMode: 'absolute' }) };
        const envelopes = sharedKeepItemEnvelopes(prop, contract);
        if (envelopes.some(box => [...occupied, ...protectedAreas].some(other => overlaps(box, other, .5)))) continue;
        zone.props.push(prop);
        occupied.push(...envelopes);
        break;
      }
    }
  }
  return zone;
}

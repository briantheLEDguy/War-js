import { loadCampaignMapConfigs } from '../server/mapConfig';
import { campaignColliderContains, campaignColliderBlocksHeight, campaignGroundHeight } from '../shared/orvr/navigation';
import type { Position, ZoneConfig } from '../shared/orvr/protocol';

type GateStage = 'outer' | 'inner';
type KeepConfig = ZoneConfig['keeps'][number];

interface AuditOptions {
  breachedGates?: GateStage[];
  target?: Position;
}

/** Ground-level reachability, seeded from every free boundary cell to catch side and rear leaks. */
export function createKeepEnclosureAudit(config: ZoneConfig, keep: KeepConfig, step = .5) {
  const radius = .45;
  const minX = keep.position.x - 48, minZ = keep.outerGate.z - 20;
  const width = Math.round(96 / step) + 1, depth = Math.round(110 / step) + 1;
  const nearby = (config.collision ?? []).filter(collider => collider.maxX >= minX - radius
    && collider.minX <= minX + 96 + radius && collider.maxZ >= minZ - radius
    && collider.minZ <= minZ + 110 + radius);
  const mask = new Uint8Array(width * depth);
  const gateMasks = { outer: new Uint8Array(mask.length), inner: new Uint8Array(mask.length) };
  const heights = new Float64Array(mask.length);
  const point = (index: number): Position => ({ x: minX + (index % width) * step,
    y: heights[index], z: minZ + Math.floor(index / width) * step });
  for (let index = 0; index < mask.length; index += 1) {
    const position = point(index);
    position.y = heights[index] = campaignGroundHeight(config, position);
    if (nearby.some(collider => campaignColliderBlocksHeight(collider, position.y)
      && campaignColliderContains(collider, position, radius))) mask[index] = 1;
    for (const stage of ['outer', 'inner'] as const) {
      const gate = stage === 'outer' ? keep.outerGate : keep.innerGate;
      const footprint = keep.gateFootprints?.[stage];
      if (!footprint) continue;
      const cosine = Math.cos(footprint.rotY ?? 0), sine = Math.sin(footprint.rotY ?? 0);
      const x = (position.x - gate.x) * cosine + (position.z - gate.z) * sine;
      const z = -(position.x - gate.x) * sine + (position.z - gate.z) * cosine;
      if (position.y + 1.8 > gate.y && position.y < gate.y + (footprint.height ?? 10)
        && Math.abs(x) < footprint.width / 2 + radius && Math.abs(z) < footprint.depth / 2 + radius) {
        gateMasks[stage][index] = 1;
      }
    }
  }

  return ({ breachedGates = [], target = keep.position }: AuditOptions = {}) => {
    const visited = new Uint8Array(mask.length);
    const previous = new Int32Array(mask.length).fill(-1);
    const queue: number[] = [];
    const blocked = (index: number) => mask[index]
      || (!breachedGates.includes('outer') && gateMasks.outer[index])
      || (!breachedGates.includes('inner') && gateMasks.inner[index]);
    const visit = (index: number, from = -1) => {
      if (index < 0 || visited[index] || blocked(index)) return;
      visited[index] = 1; previous[index] = from; queue.push(index);
    };
    for (let x = 0; x < width; x += 1) { visit(x); visit((depth - 1) * width + x); }
    for (let z = 1; z < depth - 1; z += 1) { visit(z * width); visit(z * width + width - 1); }
    for (let head = 0; head < queue.length; head += 1) {
      const index = queue[head], x = index % width, z = Math.floor(index / width);
      for (const next of [x > 0 ? index - 1 : -1, x < width - 1 ? index + 1 : -1,
        z > 0 ? index - width : -1, z < depth - 1 ? index + width : -1]) visit(next, index);
    }
    const targetX = Math.round((target.x - minX) / step), targetZ = Math.round((target.z - minZ) / step);
    if (targetX < 0 || targetX >= width || targetZ < 0 || targetZ >= depth) throw new Error('Keep audit target outside sampled bounds');
    const targetIndex = targetZ * width + targetX;
    const path: Position[] = [];
    if (visited[targetIndex]) for (let index = targetIndex; index >= 0; index = previous[index]) path.push(point(index));
    return { keep: keep.id, reachable: Boolean(visited[targetIndex]), path: path.reverse(), staticColliders: nearby.length };
  };
}

export function auditKeepEnclosure(config: ZoneConfig, keep: KeepConfig, step = .5) {
  return createKeepEnclosureAudit(config, keep, step)();
}

if (process.argv[1]?.endsWith('audit-keep-enclosures.ts')) {
  void loadCampaignMapConfigs().then(configs => {
    for (const config of configs) for (const keep of config.keeps) {
      const audit = createKeepEnclosureAudit(config, keep);
      console.log(JSON.stringify({ zone: config.id, keep: keep.id, closed: audit().reachable,
        outerBreached: audit({ breachedGates: ['outer'] }).reachable,
        bothBreached: audit({ breachedGates: ['outer', 'inner'] }).reachable }));
    }
  });
}

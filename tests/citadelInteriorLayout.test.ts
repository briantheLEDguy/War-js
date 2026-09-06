import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { describe, expect, test } from 'vitest';
import { cityHeightAt } from '../src/world/CityElevation';
import { cityPositionBlocked } from '../src/world/CityNavigation';
import { propCollidersFromObject } from '../src/world/editor/WorldEditorRuntime';
import { prefabDefinitionForKind } from '../src/world/editor/PrefabCatalog';
import type { WorldPropObject } from '../src/services/types';
import type { PropSpawn, ZoneDefinition } from '../src/world/ZoneLoader';

const zone: ZoneDefinition = JSON.parse(fs.readFileSync('public/assets/maps/aegis_capital.json', 'utf8'));
const citadel = zone.cityCitadel!, siege = citadel.siege!, mountain = citadel.mountainExtension!;
const height = (x: number, z: number) => cityHeightAt(zone.cityElevation!, zone.size, x, z);
const definition = (p: PropSpawn): WorldPropObject => ({ ...p, id: p.id!, type: 'prop', createdAt: 0, updatedAt: 0,
  transform: { position: { x: p.x, y: height(p.x, p.z) + (p.y ?? 0), z: p.z },
    rotation: { x: 0, y: p.rotY ?? 0, z: 0 },
    scale: { x: (p.scale ?? 1) * (p.scaleX ?? 1), y: (p.scale ?? 1) * (p.scaleY ?? 1), z: (p.scale ?? 1) * (p.scaleZ ?? 1) } } });
const colliders = zone.props.flatMap(p => propCollidersFromObject(definition(p)));
const interiorColliders = colliders.filter(c => c.z > 270 && c.z < 390 && Math.abs(c.x) < 150);
const decorationKinds = ['throne', 'oath_statue', 'war_table', 'arms_rack', 'provision_rack', 'bunk', 'hearth',
  'feast_table', 'archive', 'counting_desk', 'treasury', 'reliquary', 'chandelier', 'tapestry'];

function clearPoint(x: number, z: number, label: string, radius = 1, y = 42.02) {
  const blocked = colliders.filter(c => cityPositionBlocked({ x, y, z }, [c], radius));
  expect(blocked.map(c => c.id), `${label} ${x.toFixed(2)}/${z.toFixed(2)}`).toEqual([]);
}

function clearRoute(points: Array<{ x: number; z: number }>, label: string, radius = 1) {
  for (let i = 1; i < points.length; i++) {
    const a = points[i - 1], b = points[i], steps = Math.max(1, Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) * 2));
    for (let step = 0; step <= steps; step++) {
      const x = a.x + (b.x - a.x) * step / steps, z = a.z + (b.z - a.z) * step / steps;
      expect(height(x, z), `${label} flat floor`).toBeCloseTo(42);
      clearPoint(x, z, label, radius);
    }
  }
}

describe('Crownwatch furnished siege interior', () => {
  test('orders the courtyard, vault and throne objectives with explicit prerequisites', () => {
    expect(siege.objectiveOrder).toEqual(['aegis_capital_courtyard', 'aegis_capital_vault', 'aegis_capital_throne_room']);
    expect(zone.rvrObjectives!.map(o => o.id)).toEqual(siege.objectiveOrder);
    for (const [i, objective] of zone.rvrObjectives!.entries()) {
      expect(objective.requiresObjectiveIds ?? []).toEqual(siege.objectiveOrder.slice(0, i));
      expect(objective.captureRadius).toBeGreaterThanOrEqual(10);
      expect(objective.label.startsWith(`${i + 1} · `)).toBe(true);
    }
    expect(siege.rooms.map(r => r.id)).toEqual(expect.arrayContaining([
      'barracks', 'mess', 'stores', 'counting', 'admission', 'courtyard', 'vault', 'throne_room',
    ]));
    expect(siege.rooms.find(r => r.id === 'counting')!.bounds.maxZ).toBeLessThan(mountain.vault!.minZ + 23);
    expect(siege.rooms.find(r => r.id === 'throne_room')!.bounds.minZ).toBeGreaterThan(322);
  });

  test('keeps the entire objective disks and their centers clear for combatants', () => {
    for (const objective of zone.rvrObjectives!) {
      const radius = objective.captureRadius!;
      for (let dx = -radius; dx <= radius; dx++) for (let dz = -radius; dz <= radius; dz++) {
        if (Math.hypot(dx, dz) <= radius) clearPoint(objective.x + dx, objective.z + dz, objective.id);
      }
      for (let i = 0; i < 72; i++) {
        const angle = i / 72 * Math.PI * 2;
        clearPoint(objective.x + Math.cos(angle) * radius, objective.z + Math.sin(angle) * radius, `${objective.id} ring`);
      }
    }
  });

  test('connects the objective sequence and retains wide central and flanking siege lanes', () => {
    clearRoute([{ x: 0, z: 158 }, { x: 0, z: 220 }, { x: 0, z: 314 }, { x: 114, z: 314 },
      { x: 114, z: 332 }, { x: 114, z: 356 }, { x: 50, z: 356 }, { x: 50, z: 344 }, { x: 0, z: 344 }, { x: 0, z: 350 }],
    'courtyard through vault to throne');
    for (const route of mountain.routes) {
      clearRoute(route.points, route.id);
      // A one-metre-radius combatant can use both edges of the declared aisle.
      for (let i = 1; i < route.points.length; i++) {
        const a = route.points[i - 1], b = route.points[i], length = Math.hypot(b.x - a.x, b.z - a.z);
        const normal = { x: -(b.z - a.z) / length, z: (b.x - a.x) / length };
        for (const side of [-1, 1]) {
          const offset = side * (route.width / 2 - 1);
          clearRoute([a, b].map(p => ({ x: p.x + normal.x * offset, z: p.z + normal.z * offset })), `${route.id} edge`);
        }
      }
    }
    for (const x of [-34, 0, 34]) clearRoute([{ x, z: 316 }, { x, z: 328 }], `throne portal ${x}`, 1);
  });

  test('keeps barracks, kitchen, stores and counting office doors connected to usable furniture aisles', () => {
    const furnitureAccess: Record<string, Array<{ x: number; z: number }>> = {
      barracks: [{ x: -.5, z: 0 }, { x: -.5, z: -3 }, { x: -.5, z: 3 }],
      mess: [{ x: 2, z: 0 }, { x: 2, z: 1.5 }, { x: 1, z: 1.5 }],
      stores: [{ x: -1, z: 0 }, { x: -1, z: -3 }, { x: -1, z: 3 }],
      counting: [{ x: 0, z: 0 }, { x: 2, z: 0 }],
    };
    for (const [id, offsets] of Object.entries(furnitureAccess)) {
      const room = siege.rooms.find(r => r.id === id)!;
      const points = offsets.map(p => ({ x: (room.bounds.minX + room.bounds.maxX) / 2 + p.x,
        z: (room.bounds.minZ + room.bounds.maxZ) / 2 + p.z }));
      expect(room.floorY).toBeCloseTo(42.02);
      const centralApproach = { x: Math.sign(room.entry.x) * 34, z: room.entry.z };
      clearRoute([centralApproach, room.entry, points[0]], `${id} door`, .65);
      for (const point of points) clearRoute([points[0], point], `${id} furniture access`, .65);
      const walls = zone.props.find(p => p.id === `aegis_interior_${id}_room`)!;
      expect(walls.walkableSurfaces).toHaveLength(1);
      expect(walls.colliders).toHaveLength(5);
    }
  });

  test('accommodates two eighteen-person vault formations connected to both entrance routes', () => {
    const { south, north } = siege.vaultStaging, slots = [...south, ...north];
    expect(south).toHaveLength(18); expect(north).toHaveLength(18);
    for (const [i, p] of slots.entries()) {
      clearPoint(p.x, p.z, `vault staging ${i}`);
      for (const q of slots.slice(i + 1)) expect(Math.hypot(p.x - q.x, p.z - q.z)).toBeGreaterThanOrEqual(5);
    }
    const key = (x: number, z: number) => `${x}/${z}`;
    const queue = [{ x: 114, z: 332 }], visited = new Set([key(114, 332)]);
    for (let i = 0; i < queue.length; i++) {
      const p = queue[i];
      for (const [x, z] of [[p.x - 1, p.z], [p.x + 1, p.z], [p.x, p.z - 1], [p.x, p.z + 1]]) {
        const next = key(x, z);
        if (x < 60 || x > 136 || z < 292 || z > 372 || visited.has(next)
          || cityPositionBlocked({ x, y: 42.02, z }, interiorColliders, 1)) continue;
        visited.add(next); queue.push({ x, z });
      }
    }
    for (const p of [...slots, { x: 60, z: 314 }, { x: 60, z: 356 }])
      expect(visited.has(key(p.x, p.z)), `connected vault position ${key(p.x, p.z)}`).toBe(true);
    expect(zone.cityBattlefield!.playersPerTeam).toBe(18);
    for (const team of Object.values(zone.cityBattlefield!.staging)) {
      expect(team).toHaveLength(18);
      for (const p of team) clearPoint(p.x, p.z, 'preserved courtyard staging');
    }
  });

  test('provides exactly fourteen distinct furnishings throughout the functional rooms', () => {
    expect([...siege.decorationKinds].sort()).toEqual(decorationKinds.map(k => `aegis_citadel_${k}`).sort());
    const furnishings = zone.props.filter(p => p.id?.startsWith('aegis_interior_') && p.kind.startsWith('aegis_citadel_'));
    expect(furnishings).toHaveLength(siege.decorationCount);
    expect(furnishings.length).toBeGreaterThan(60);
    expect(new Set(furnishings.map(p => p.id)).size).toBe(furnishings.length);
    for (const kind of siege.decorationKinds) expect(furnishings.some(p => p.kind === kind), kind).toBe(true);
    const vault = prefabDefinitionForKind('aegis_mountain_vault')!;
    expect(vault, 'vault shell GM catalog').toBeDefined();
    expect(vault.model).toBe('prop_aegis_mountain_vault.glb');
    expect(vault.lodModels).toEqual(['prop_aegis_mountain_vault_lod1.glb', 'prop_aegis_mountain_vault_lod2.glb']);
    expect(vault.walkableSurfaces?.length).toBeGreaterThan(0);
  });

  test.each(decorationKinds)('ships reviewed detailed %s assets, shared 2K textures and three GM-placeable LODs', kind => {
    const name = `prop_aegis_citadel_${kind}`;
    const manifest = JSON.parse(fs.readFileSync(`scripts/blender-character-pipeline/data/approved-assets/${name}.approved.json`, 'utf8'));
    expect(manifest.approvalState).toBe('approved');
    const prefab = prefabDefinitionForKind(`aegis_citadel_${kind}`)!;
    expect(prefab, `${kind} GM catalog`).toBeDefined();
    expect(prefab.model).toBe(`${name}.glb`);
    expect(prefab.lodModels).toEqual([`${name}_lod1.glb`, `${name}_lod2.glb`]);
    let previous = Infinity;
    for (const level of [0, 1, 2]) {
      const file = name + (level ? `_lod${level}` : '');
      const bytes = fs.readFileSync(`public/assets/models/${file}.glb`);
      const qc = JSON.parse(fs.readFileSync(`public/assets/models/${file}.qc.json`, 'utf8'));
      const sha = createHash('sha256').update(bytes).digest('hex');
      expect(qc.qcPassed).toBe(true); expect(qc.validationErrors).toBe(0); expect(qc.modelSha256).toBe(sha);
      if (!level) expect(manifest.hashes.modelSha256).toBe(sha);
      expect(qc.lod.triangles).toBeLessThanOrEqual(30_000);
      expect(qc.lod.triangles).toBeLessThan(previous); previous = qc.lod.triangles;
      expect(bytes.byteLength).toBeLessThanOrEqual(4_000_000);
      const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
      expect(gltf.materials.length).toBeLessThanOrEqual(8);
      expect(gltf.images.length).toBeGreaterThan(0);
      for (const image of gltf.images) {
        expect(image.uri).toMatch(/^\.\.\/textures\/aegis_citadel_interiors\/.+\.png$/);
        const texture = fs.readFileSync(path.resolve('public/assets/models', image.uri));
        expect(texture.toString('ascii', 1, 4)).toBe('PNG');
        expect(texture.readUInt32BE(16)).toBe(2048);
        expect(texture.readUInt32BE(20)).toBe(2048);
      }
      for (const mesh of gltf.meshes) for (const primitive of mesh.primitives) {
        expect(primitive.attributes.NORMAL).toBeDefined();
        expect(primitive.attributes.TEXCOORD_0).toBeDefined();
        expect(primitive.attributes.TANGENT).toBeDefined();
      }
    }
  });
});

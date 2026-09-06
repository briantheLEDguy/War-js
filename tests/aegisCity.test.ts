import { readFileSync } from 'node:fs';
import { describe, expect, test } from 'vitest';
import * as THREE from 'three';
import { citySurfaceGeometry, canalAt } from '../src/world/CityWater';
import { safeCityEntry, cityPositionBlocked } from '../src/world/CityNavigation';
import { architectureLods, cityFallback } from '../src/world/CityArchitecture';
import { applyZonePaths } from '../src/world/PathKit';
import type { WorldCollider } from '../src/world/Props';
import type { ZoneDefinition } from '../src/world/ZoneLoader';
import type { AssetLoader } from '../src/game/AssetLoader';
import { Terrain } from '../src/world/Terrain';
import { cityHeightAt } from '../src/world/CityElevation';
import { cityRoadGeometry } from '../src/world/CityRoad';
const zone: ZoneDefinition = JSON.parse(readFileSync('public/assets/maps/aegis_capital.json', 'utf8'));
const ground = (x: number, z: number) => zone.cityElevation ? cityHeightAt(zone.cityElevation, zone.size, x, z) : 0;
function colliders(): WorldCollider[] {
  return zone.props.flatMap(p => (p.colliders ?? []).map((c, i) => {
    const angle = p.rotY ?? 0, sx = (p.scale ?? 1) * (p.scaleX ?? 1), sz = (p.scale ?? 1) * (p.scaleZ ?? 1);
    return { id: `${p.id}-${i}`, x: p.x + (c.x ?? 0) * sx * Math.cos(angle) - (c.z ?? 0) * sz * Math.sin(angle), z: p.z + (c.x ?? 0) * sx * Math.sin(angle) + (c.z ?? 0) * sz * Math.cos(angle), width: c.width * sx, depth: c.depth * sz, rotY: angle + (c.rotY ?? 0), minY: ground(p.x, p.z) + (p.y ?? 0) + (c.minY ?? -100), maxY: ground(p.x, p.z) + (p.y ?? 0) + (c.maxY ?? 100), blocksWhen: c.blocksWhen ?? 'always' };
  }));
}
function modelBounds(filename: string): THREE.Box3 {
    const bytes = readFileSync(filename);
    const gltf = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
    const bounds = new THREE.Box3();
    const visit = (index: number, parent: THREE.Matrix4) => {
      const node = gltf.nodes[index];
      const local = node.matrix ? new THREE.Matrix4().fromArray(node.matrix) : new THREE.Matrix4().compose(
        new THREE.Vector3().fromArray(node.translation ?? [0, 0, 0]),
        new THREE.Quaternion().fromArray(node.rotation ?? [0, 0, 0, 1]),
        new THREE.Vector3().fromArray(node.scale ?? [1, 1, 1]));
      const world = parent.clone().multiply(local);
      if (node.mesh !== undefined) for (const primitive of gltf.meshes[node.mesh].primitives) {
        const accessor = gltf.accessors[primitive.attributes.POSITION];
        bounds.union(new THREE.Box3(new THREE.Vector3().fromArray(accessor.min), new THREE.Vector3().fromArray(accessor.max)).applyMatrix4(world));
      }
      for (const child of node.children ?? []) visit(child, world);
    };
    for (const root of gltf.scenes[gltf.scene ?? 0].nodes) visit(root, new THREE.Matrix4());
    return bounds;
}
describe('Aegis Gothic city', () => {
  test('ships a monumental keep and a broad mountain with a natural depth', () => {
    const keep = modelBounds('public/assets/models/prop_aegis_citadel.glb').getSize(new THREE.Vector3());
    const mountain = modelBounds('public/assets/models/prop_aegis_mountain_massif.glb').getSize(new THREE.Vector3());
    expect(keep.x).toBeGreaterThan(95);
    expect(keep.y).toBeGreaterThan(70);
    expect(mountain.x).toBeGreaterThan(900);
    expect(mountain.z).toBeGreaterThan(600);
    expect(mountain.y).toBeGreaterThan(200);
  });
  test('retains the Gothic skyline and architecture budget at all three keep LODs', () => {
    let previousTriangles = Infinity;
    for (const suffix of ['', '_lod1', '_lod2']) {
      const filename = `public/assets/models/prop_aegis_citadel${suffix}.glb`;
      const bounds = modelBounds(filename);
      expect(bounds.max.y).toBeGreaterThan(120);
      expect(bounds.max.y).toBeLessThan(128);
      expect(bounds.getSize(new THREE.Vector3()).x).toBeLessThan(102);
      expect(bounds.getSize(new THREE.Vector3()).z).toBeGreaterThan(65);
      expect(bounds.getSize(new THREE.Vector3()).z).toBeLessThan(71);
      const bytes = readFileSync(filename);
      const doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
      const triangles = doc.meshes.reduce((total: number, mesh: { primitives: { indices: number }[] }) =>
        total + mesh.primitives.reduce((count: number, p: { indices: number }) => count + doc.accessors[p.indices].count / 3, 0), 0);
      expect(triangles).toBeLessThanOrEqual(30000);
      expect(triangles).toBeLessThan(previousTriangles);
      previousTriangles = triangles;
    }
    const fallback = cityFallback('aegis_citadel');
    expect(new THREE.Box3().setFromObject(fallback).max.y).toBeCloseTo(125);
    fallback.updateMatrixWorld(true);
    const ray = new THREE.Raycaster(new THREE.Vector3(0, 2, 60), new THREE.Vector3(0, 0, -1), 0, 80);
    expect(ray.intersectObject(fallback, true)).toHaveLength(0);
    const materials = new Set<THREE.Material>();
    fallback.traverse(node => {
      if (node instanceof THREE.Mesh) {
        node.geometry.dispose();
        for (const material of Array.isArray(node.material) ? node.material : [node.material]) materials.add(material);
      }
    });
    materials.forEach(material => material.dispose());
  });
  test('keeps rotated brick paving exactly on the mountain surface between vertices', () => {
    const x = -48, z = 59, rotation = .37, lift = .04;
    const geometry = cityRoadGeometry(zone.cityElevation!, zone.size, x, z, rotation, 9, 8, ground(x, z), lift);
    const pos = geometry.getAttribute('position'), cos = Math.cos(rotation), sin = Math.sin(rotation);
    for (let i = 0; i < pos.count; i += 3) {
      const lx = (pos.getX(i) + pos.getX(i + 1) + pos.getX(i + 2)) / 3;
      const lz = (pos.getZ(i) + pos.getZ(i + 1) + pos.getZ(i + 2)) / 3;
      const y = (pos.getY(i) + pos.getY(i + 1) + pos.getY(i + 2)) / 3 + ground(x, z);
      expect(y - ground(x + lx * cos + lz * sin, z - lx * sin + lz * cos)).toBeCloseTo(lift, 4);
    }
  });
  test('raises the citadel above the canal district and keeps water level', () => {
    expect(ground(28, 130)).toBeCloseTo(42);
    expect(ground(0, -118)).toBe(0);
    expect(ground(0, 178)).toBe(42);
    expect(zone.props.some(p => p.kind === 'aegis_mountain_massif')).toBe(true);
    for (const canal of zone.canals!) {
      expect(ground(canal.x, canal.z)).toBe(0);
      expect(canal.waterY).toBe(-1.1);
    }
    let maxGrade = 0;
    for (const climb of zone.paths!.filter(p => ['aegis_city_gateward', 'aegis_city_citadel_ascent', 'aegis_city_north_lane'].includes(p.id))) for (let i = 1; i < climb.points.length; i++) {
      const a = climb.points[i - 1], b = climb.points[i];
      const length = Math.hypot(b.x - a.x, b.z - a.z);
      for (let d = .5; d <= length; d += .5) {
        const sample = (v: number) => ground(a.x + (b.x - a.x) * v / length, a.z + (b.z - a.z) * v / length);
        maxGrade = Math.max(maxGrade, Math.abs(sample(d) - sample(d - .5)) / .5);
      }
    }
    expect(maxGrade).toBeLessThan(.8);
  });
  test('uses the same elevation for terrain triangles and movement samples', async () => {
    const terrain = new Terrain({ size: zone.size, segments: zone.segments });
    const mesh = await terrain.build({ loadTexture: async () => null } as unknown as AssetLoader, {
      size: zone.size, segments: zone.segments, flatTerrain: true, canals: zone.canals, cityElevation: zone.cityElevation,
    }) as THREE.Mesh;
    const pos = mesh.geometry.getAttribute('position');
    for (let i = 0; i < pos.count; i += 17)
      expect(pos.getY(i)).toBeCloseTo(terrain.heightAt(pos.getX(i), pos.getZ(i)), 3);
    expect(terrain.heightAt(28, 130)).toBeCloseTo(42);
  });
  test('distributes additional buildings and furnishings across all districts', () => {
    expect(zone.cityDetailCounts).toEqual({ infillBuildings: 36, streetFurnishings: 135, courtFeatures: 8 });
    const furnishings = zone.props.filter(p => p.id?.includes('street_detail_'));
    expect(new Set(furnishings.map(p => p.kind)).size).toBeGreaterThanOrEqual(9);
    for (const district of zone.cityDistricts!) {
      const nearby = furnishings.filter(p => [...zone.cityDistricts!].sort((a, b) =>
        Math.hypot(p.x - a.x, p.z - a.z) - Math.hypot(p.x - b.x, p.z - b.z))[0].id === district.id);
      expect(nearby.length).toBeGreaterThanOrEqual(15);
    }
  });
  test('ships contrasting facade and roof materials in the house exports', () => {
    const materials = new Set<string>();
    for (let i = 1; i <= 6; i++) {
      const bytes = readFileSync(`public/assets/models/prop_aegis_house_${i}.glb`);
      const doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
      for (const material of doc.materials) materials.add(material.name);
    }
    for (const finish of ['plaster_ochre', 'plaster_lime', 'plaster_sage', 'limestone', 'terracotta', 'copper', 'slate']) {
      expect([...materials].some(name => name.includes(finish))).toBe(true);
    }
  });
  test('matches exported stair height to the authored flights and opens onto each wall walk', () => {
    const bounds = modelBounds('public/assets/models/prop_aegis_stairs.glb');
    expect(bounds.max.y).toBeCloseTo(6, 1);
    for (const x of [-140, 140]) {
      const lower = zone.props.find(p => p.id === `aegis_city_stairs_lower_${x}`)!;
      const upper = zone.props.find(p => p.id === `aegis_city_stairs_upper_${x}`)!;
      const landing = zone.props.find(p => p.id === `aegis_city_wall_landing_${x}`)!;
      expect(lower.z - upper.z).toBe(24);
      expect(upper.y).toBe(6);
      expect(landing.y).toBe(12);
      expect(upper.z - landing.z).toBe(12);
      for (let distance = 0; distance <= 5; distance += .25) {
        expect(cityPositionBlocked({ x: x + Math.sign(x) * distance, y: ground(landing.x, landing.z) + 12, z: landing.z }, colliders())).toBe(false);
      }
    }
  });
  test('contains five districts, six interiors and six bridge crossings', () => {
    expect(zone.cityDistricts).toHaveLength(5);
    expect(zone.explorationPlaces).toHaveLength(12);
    expect(zone.props.filter(p => p.interaction?.type === 'house_portal')).toHaveLength(6);
    expect(zone.props.filter(p => p.kind.startsWith('aegis_bridge'))).toHaveLength(6);
    expect(zone.props.filter(p => p.kind.startsWith('aegis_house')).length).toBeGreaterThanOrEqual(40);
  });
  test('does not infer road connections across waterways', () => {
    const paths = applyZonePaths(zone).props.filter(p => p.id?.includes('_to_') && p.kind.startsWith('path_'));
    expect(paths).toHaveLength(0);
    expect(applyZonePaths(zone).props.some(p => p.kind === 'path_brick')).toBe(true);
  });
  test('cuts every ground triangle away from water', () => {
    const geo = citySurfaceGeometry(zone.size, zone.canals!, 'ground');
    const pos = geo.getAttribute('position'), index = geo.getIndex()!;
    for (let i = 0; i < index.count; i += 3) {
      const ids = [index.getX(i), index.getX(i + 1), index.getX(i + 2)];
      expect(canalAt(zone.canals!, ids.reduce((n, j) => n + pos.getX(j), 0) / 3, ids.reduce((n, j) => n + pos.getZ(j), 0) / 3)).toBeUndefined();
    }
    geo.dispose();
  });
  test('uses channel cutouts in the actual flat terrain build', async () => {
    const terrain = new Terrain({ size: zone.size, segments: zone.segments });
    const object = await terrain.build({} as AssetLoader, { size: zone.size, segments: zone.segments, flatTerrain: true, canals: zone.canals });
    const ray = new THREE.Raycaster(new THREE.Vector3(70, 10, -50), new THREE.Vector3(0, -1, 0));
    object.updateMatrixWorld(true);
    expect(ray.intersectObject(object)).toHaveLength(0);
    ray.set(new THREE.Vector3(0, 10, -118), new THREE.Vector3(0, -1, 0));
    expect(ray.intersectObject(object).length).toBeGreaterThan(0);
  });
  test('keeps bridge centers clear while preventing channel entry', () => {
    const cs = colliders();
    for (const p of zone.props.filter(p => p.kind.startsWith('aegis_bridge'))) {
      for (let d = -5; d <= 5; d += .5)
        expect(cityPositionBlocked({ x: p.x + (p.rotY ? d : 0), z: p.z + (p.rotY ? 0 : d), y: 0 }, cs), p.id).toBe(false);
    }
    expect(cityPositionBlocked({ x: 70, z: -50, y: 0 }, cs)).toBe(true);
  });
  test('keeps every authored route center passable', () => {
    const cs = colliders();
    for (const path of zone.paths!)
      for (let i = 1; i < path.points.length; i++) {
        const a = path.points[i - 1], b = path.points[i];
        const n = Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) * 2);
        for (let j = 0; j <= n; j++) {
          const p = { x: a.x + (b.x - a.x) * j / n, z: a.z + (b.z - a.z) * j / n, y: ground(a.x + (b.x - a.x) * j / n, a.z + (b.z - a.z) * j / n) };
          expect(cityPositionBlocked(p, cs), `${path.id} at ${p.x.toFixed(1)}, ${p.z.toFixed(1)}`).toBe(false);
        }
      }
  });
  test('recovers obstructed saved positions without moving valid saves', () => {
    const cs = colliders(), spawn = zone.spawnPoint!;
    expect(safeCityEntry({ x: 70, y: 0, z: -50 }, spawn, cs)).toEqual(spawn);
    expect(safeCityEntry(spawn, spawn, cs)).toEqual(spawn);
    expect(cityPositionBlocked(spawn, cs)).toBe(false);
  });
  test('connects services, doors, discoveries and all campaign exits to spawn', () => {
    const size = 331, offset = 165, minZ = -165, maxZ = 400;
    const blocked = new Uint8Array(size * (maxZ - minZ + 1)), seen = new Uint8Array(blocked.length);
    for (const c of colliders().filter(c => c.blocksWhen === 'always')) {
      const reach = Math.hypot(c.width, c.depth) / 2 + 1;
      for (let z = Math.max(minZ, Math.floor(c.z - reach)); z <= Math.min(maxZ, Math.ceil(c.z + reach)); z++)
        for (let x = Math.max(-offset, Math.floor(c.x - reach)); x <= Math.min(offset, Math.ceil(c.x + reach)); x++)
          if (cityPositionBlocked({ x, y: ground(x, z), z }, [c], .5))
            blocked[(z - minZ) * size + x + offset] = 1;
    }
    const start = (Math.round(zone.spawnPoint!.z) - minZ) * size + Math.round(zone.spawnPoint!.x) + offset;
    const queue = [start];
    seen[start] = 1;
    for (let i = 0; i < queue.length; i++) {
      const v = queue[i], x = v % size;
      for (const next of [x > 0 ? v - 1 : -1, x < size - 1 ? v + 1 : -1, v - size, v + size])
        if (next >= 0 && next < seen.length && !seen[next] && !blocked[next]) {
          seen[next] = 1;
          queue.push(next);
        }
    }
    const destinations = [...zone.npcs!, ...zone.craftingStations!, ...zone.resourceNodes!, ...zone.zoneTriggers!, ...zone.explorationPlaces!,
      ...zone.props.filter(p => p.interaction?.type === 'house_portal').map(p => ({ ...p, z: p.z + 2 }))];
    for (const p of destinations)
      expect(seen[(Math.round(p.z) - minZ) * size + Math.round(p.x) + offset], JSON.stringify(p)).toBe(1);
  });
  test('surrounds the city at ground level except guarded road gates', () => {
    const cs = colliders();
    const perimeter = [
      ...Array.from({ length: 581 }, (_, i) => [-145 + i * .5, -145]),
      ...Array.from({ length: 581 }, (_, i) => [-145 + i * .5, 250]),
      ...Array.from({ length: 791 }, (_, i) => [-145, -145 + i * .5]),
      ...Array.from({ length: 791 }, (_, i) => [145, -145 + i * .5]),
    ];
      for (const [x, z] of perimeter) {
        if ((Math.abs(x) < 5 && z === -145) || (Math.abs(z) < 5 && Math.abs(x) === 145)
          || (Math.abs(x) < 9 && z === 250))
          continue;
        expect(cityPositionBlocked({ x, y: ground(x, z), z }, cs, .01), `wall gap ${x},${z}`).toBe(true);
      }
  });
  test('accommodates 18-versus-18 staging and connects every slot through the battle court', () => {
    const battle = zone.cityBattlefield!;
    expect(battle.playersPerTeam).toBe(18);
    expect(battle.staging.south).toHaveLength(18);
    expect(battle.staging.north).toHaveLength(18);
    // The deeper keep uses the rear court; the remaining forecourt still fits both formations.
    expect(battle.bounds.maxX - battle.bounds.minX).toBeGreaterThanOrEqual(120);
    expect(battle.bounds.maxZ - battle.bounds.minZ).toBeGreaterThanOrEqual(30);
    const slots = [...battle.staging.south, ...battle.staging.north], cs = colliders().filter(c => Math.abs(c.x) < 110 && c.z > 115);
    for (const [i, p] of slots.entries()) {
      expect(p.z).toBeGreaterThanOrEqual(battle.bounds.minZ);
      expect(p.z).toBeLessThanOrEqual(battle.bounds.maxZ);
      expect(ground(p.x, p.z)).toBe(42);
      expect(cityPositionBlocked({ ...p, y: 42 }, cs, 1)).toBe(false);
      for (const q of slots.slice(i + 1)) expect(Math.hypot(p.x - q.x, p.z - q.z)).toBeGreaterThanOrEqual(5);
    }
    // Flood with a generous one-metre collision radius, not point-sized agents.
    const width = 161, offset = 80, minZ = 120, maxZ = 207;
    const seen = new Set<number>(), queue = [{ x: 0, z: 158 }];
    const key = (x: number, z: number) => (z - minZ) * width + x + offset;
    seen.add(key(0, 158));
    for (let i = 0; i < queue.length; i++) {
      const p = queue[i];
      for (const [x, z] of [[p.x - 1, p.z], [p.x + 1, p.z], [p.x, p.z - 1], [p.x, p.z + 1]]) {
        const k = key(x, z);
        if (Math.abs(x) > offset || z < minZ || z > maxZ || seen.has(k) || cityPositionBlocked({ x, z, y: ground(x, z) }, cs, 1)) continue;
        seen.add(k); queue.push({ x, z });
      }
    }
    for (const p of [...slots, ...battle.approaches]) expect(seen.has(key(p.x, p.z))).toBe(true);
    for (const p of battle.approaches) for (let dx = -p.width / 2 + 1; dx <= p.width / 2 - 1; dx += .5)
      expect(cityPositionBlocked({ x: p.x + dx, z: p.z, y: ground(p.x + dx, p.z) }, cs, .75)).toBe(false);
  });
  test('switches architectural LODs at authored distances', async () => {
    const loader = { loadModel: async () => new THREE.Group() } as unknown as AssetLoader;
    const lod = await architectureLods(new THREE.Group(), ['one.glb', 'two.glb'], 'aegis_house_1', loader);
    const camera = new THREE.PerspectiveCamera();
    for (const [distance, level] of [[10, 0], [75, 1], [150, 2]]) {
      camera.position.z = distance;
      camera.updateMatrixWorld();
      lod.update(camera);
      expect(lod.getCurrentLevel()).toBe(level);
    }
  });
});

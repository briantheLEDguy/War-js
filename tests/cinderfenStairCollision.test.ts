import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { describe, expect, test } from 'vitest';
import { mapPropNavigation } from '../server/mapNavigation';
import { campaignColliderBlocksHeight, campaignColliderContains } from '../shared/orvr/navigation';
import { supportedGroundHeight, type NavigationProp } from '../shared/worldNavigation';
// @ts-expect-error Native ESM authoring utility.
import { measuredStairRails } from '../authoring/blender/cinderfen-architecture/tools/repair_stair_navigation.mjs';

const root = 'authoring/blender/cinderfen-architecture';
const read = (name: string) => JSON.parse(readFileSync(`${root}/${name}`, 'utf8'));
const stair = read('navigation-contract.json').assets.find((asset: { assetId: string }) => asset.assetId.endsWith('wall_stair'));
const source = read('source/architecture.json');
const original = source.assets.frontier_cinderfen_wall_stair.contract;
const asProp = (contract: typeof stair): NavigationProp => ({ id: 'stair', kind: 'structure', x: 0, z: 0, heightMode: 'absolute', colliderSpace: 'model',
  colliders: contract.colliders, walkableSurfaces: contract.walkableSurfaces });
const nav = mapPropNavigation([asProp(stair)], () => 0);
const before = mapPropNavigation([asProp(original)], () => 0);
const blocked = (navigation: typeof nav, x: number, y: number, z: number, radius = .45) => navigation.collision.some(collider =>
  campaignColliderBlocksHeight(collider, y) && campaignColliderContains(collider, { x, y, z }, radius));

describe('Cinderfen continuous stair rail collision', () => {
  test('blocks sideways walking between the visible rail posts at every flight elevation', () => {
    for (const flight of [0, 1]) for (const step of [2, 4, 8, 10, 14, 16]) {
      const tread = stair.walkableSurfaces.find((surface: { id: string }) => surface.id === `tread_${flight}_${String(step).padStart(2, '0')}`);
      for (const side of [-1, 1]) {
        const x = tread.x + side * 1.13;
        expect(blocked(nav, x, tread.fromY, tread.z), `flight ${flight}, step ${step}, side ${side}`).toBe(true);
      }
    }
    const tread = stair.walkableSurfaces.find((surface: { id: string }) => surface.id === 'tread_0_08');
    expect(blocked(before, -2.43, tread.fromY, tread.z)).toBe(false);
  });

  test('contains the rear landing without blocking its turn route or lower clearance', () => {
    expect(blocked(before, 0, 3.15, -3.7)).toBe(false);
    expect(blocked(nav, 0, 3.15, -3.7)).toBe(true);
    for (let x = -1.3; x <= 1.3; x += .1) expect(blocked(nav, x, 3.15, -2.5)).toBe(false);
    // The top-flight rail must not become a full-height invisible side wall.
    expect(blocked(nav, 2.43, 0, 2.75, .1)).toBe(false);
  });

  test('retains an unobstructed 90cm body route up both stepped flights', () => {
    let height = 0;
    for (const flight of [0, 1]) for (let step = 0; step < 18; step += 1) {
      const tread = stair.walkableSurfaces.find((surface: { id: string }) => surface.id === `tread_${flight}_${String(step).padStart(2, '0')}`);
      height = supportedGroundHeight(tread.x, tread.z, height, 0, nav.walkableSurfaces);
      expect(height).toBeCloseTo(tread.fromY, 6);
      expect(blocked(nav, tread.x, height, tread.z), tread.id).toBe(false);
    }
    expect(height).toBeCloseTo(6.3, 6);
  });

  test('walks the continuous switchback through the landing before turning across flights', () => {
    const flight = (index: number) => stair.walkableSurfaces.filter((surface: { id: string }) => surface.id.startsWith(`tread_${index}_`))
      .sort((a: { id: string }, b: { id: string }) => a.id.localeCompare(b.id));
    const route = [{ x: -1.3, z: 4.35 }, ...flight(0), { x: -1.3, z: -2.6 }, { x: 1.3, z: -2.6 },
      ...flight(1), { x: 1.3, z: 4.34 }];
    let height = 0;
    for (let index = 1; index < route.length; index += 1) {
      const a = route[index - 1], b = route[index];
      const count = Math.ceil(Math.hypot(b.x - a.x, b.z - a.z) / .08);
      for (let step = 1; step <= count; step += 1) {
        const x = a.x + (b.x - a.x) * step / count, z = a.z + (b.z - a.z) * step / count;
        height = supportedGroundHeight(x, z, height, 0, nav.walkableSurfaces);
        expect(blocked(nav, x, height, z), `route segment ${index}, sample ${step}`).toBe(false);
      }
    }
    expect(height).toBeCloseTo(6.3, 6);
  });

  test('reproduces runtime and GM collision from the unchanged authored rail pieces', () => {
    const rails = measuredStairRails(source).map(({ sourcePiece: _piece, sourcePart: _part, ...box }: Record<string, unknown>) => box);
    expect(rails.length).toBeGreaterThan(100);
    expect(stair.colliders).toEqual([...original.colliders, ...rails]);
    expect(read('builder-metadata.json').assets.frontier_cinderfen_wall_stair.colliders).toEqual(stair.colliders);
  });

  test('binds every placed stair and neighboring wall to the zero-intersection actual-mesh audit', () => {
    const audit = read('review/stair-wall-fit.json');
    const zone = JSON.parse(readFileSync('public/assets/maps/cinderfen_outskirts.json', 'utf8'));
    expect(audit.candidateDiagonalInset).toBe(0);
    expect(audit.stairs).toHaveLength(16);
    expect(audit.intersectingStairs).toBe(0);
    for (const model of audit.models) expect(createHash('sha256').update(readFileSync(`public/assets/models/${model.model}`)).digest('hex')).toBe(model.sha256);
    for (const placement of audit.placements) {
      const prop = zone.props.find((entry: { id: string }) => entry.id === placement.id);
      expect(prop, placement.id).toBeDefined();
      for (const [key, value] of Object.entries(placement)) expect(prop[key], `${placement.id}/${key}`).toEqual(value);
    }
    for (const prop of zone.props.filter((entry: { assetKey?: string }) => entry.assetKey === 'frontier_cinderfen_wall_stair')) {
      expect(prop.colliders).toEqual(stair.colliders);
      expect(prop.walkableSurfaces).toEqual(stair.walkableSurfaces);
    }
  });
});

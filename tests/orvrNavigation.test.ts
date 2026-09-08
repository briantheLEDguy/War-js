import { describe, expect, it } from 'vitest';
import { addPlayer, advanceSimulation, createCampaign, defaultZoneConfig, submitCommand } from '../src/shared/orvr';
import { campaignGroundHeight, campaignColliderContains } from '../src/shared/orvr/navigation';
import { mapPropNavigation } from '../server/mapNavigation';
import { colliderBlocksBody, supportedGroundHeight, walkableSurfaceHeight, type WalkableSurface } from '../src/shared/worldNavigation';
import { createOrvrGridHeightSampler, orvrGridHeightAt, type OrvrTerrainControls } from '../src/shared/orvrTerrain';

const surface = (overrides: Partial<WalkableSurface> = {}): WalkableSurface => ({
  id: 'deck', x: 0, z: 0, width: 4, depth: 4, rotY: 0, fromY: .6, toY: .6, axis: 'z', ...overrides,
});

describe('authored support shared by local and campaign movement', () => {
  it('climbs measured narrow stair treads while preserving underside and ordinary wall collision', () => {
    const config = defaultZoneConfig('sunmeadow_march');
    config.terrain = { sourceVersion: 'stair-test', landforms: [], flattenAreas: [], clearCorridors: [] };
    const treads = Array.from({ length: 12 }, (_, index) => ({ x: 0, z: index * .32,
      width: 2.25, depth: .32, minY: (index + 1) * .175 - .124, maxY: (index + 1) * .175 }));
    Object.assign(config, mapPropNavigation([{ kind: 'measured_stair', x: 0, z: 0,
      colliders: treads, walkableSurfaces: treads.map(tread => ({ ...tread, width: 2.15, fromY: tread.maxY, toY: tread.maxY })),
    }], () => 0));
    expect(config.collision!.every(collider => collider.walkableTop)).toBe(true);
    const upperSlab = config.collision![11];
    expect(colliderBlocksBody(upperSlab, .5)).toBe(true);
    expect(colliderBlocksBody(config.collision![0], 0, 3.5)).toBe(true);
    expect(colliderBlocksBody({ minY: 0, maxY: .5 }, 0)).toBe(true);
    const state = createCampaign({ zones: [config] });
    addPlayer(state, { id: 'climber', userId: 'user', characterId: 'character', realm: 'aegis' });
    const player = state.players.climber, zone = state.zones.sunmeadow_march;
    Object.values(zone.npcs).forEach(npc => { npc.health = 0; });
    player.position = { x: 0, y: 0, z: -.6 };
    for (let tick = 0; tick < 13; tick++) {
      submitCommand(state, player.id, { version: 1, sequence: player.lastSequence + 1, activationId: zone.activationId,
        action: { type: 'move', direction: { x: 0, z: 1 } } });
      advanceSimulation(state, .05);
    }
    expect(player.position.z).toBeGreaterThan(3.1);
    expect(player.position.y).toBeGreaterThan(1.9);
  });
  it('retains terrain grid precision and refreshes derived samples when the terrain revision changes', () => {
    const terrain: OrvrTerrainControls = { sourceVersion: 'terrain-v1',
      landforms: [{ id: 'hill', kind: 'ridge', x: 3, z: -7, radiusX: 30, radiusZ: 18, height: 8 }],
      flattenAreas: [{ id: 'pad', x: 0, z: 0, radius: 3, height: 1, feather: 2 }], clearCorridors: [] };
    const at = createOrvrGridHeightSampler(terrain, 100, 32);
    for (let i = 0; i < 300; i++) {
      const x = (i * 17.31 % 106) - 53, z = (i * 7.79 % 106) - 53;
      expect(at(x, z)).toBe(orvrGridHeightAt(terrain, 100, 32, x, z));
      expect(at(x, z)).toBe(orvrGridHeightAt(terrain, 100, 32, x, z));
    }
    for (const [x, z] of [[-50,-50],[50,50],[0,50],[NaN,0],[0,Infinity]]) {
      expect(at(x, z)).toBe(orvrGridHeightAt(terrain, 100, 32, x, z));
    }
    const config = defaultZoneConfig('sunmeadow_march');
    Object.assign(config, { terrain, terrainSize: 100, terrainSegments: 32 });
    const position = { x: 3, y: 0, z: -7 };
    const before = JSON.stringify(config);
    const initial = campaignGroundHeight(config, position);
    expect(JSON.stringify(config)).toBe(before);
    config.terrain = { ...terrain, sourceVersion: 'terrain-v2', landforms: terrain.landforms.map(form => ({ ...form, height: 3 })) };
    expect(campaignGroundHeight(config, position)).toBeLessThan(initial);
    config.terrainSegments = 64;
    expect(campaignGroundHeight(config, position)).toBe(orvrGridHeightAt(config.terrain, 100, 64, position.x, position.z));
  });

  it('follows a rotated ramp and selects the reachable floor beneath stacked decks', () => {
    const ramp = surface({ rotY: Math.PI / 2, fromY: 0, toY: 1.2 });
    expect(walkableSurfaceHeight(2, 0, ramp)).toBeCloseTo(0);
    expect(walkableSurfaceHeight(-2, 0, ramp)).toBeCloseTo(1.2);
    expect(walkableSurfaceHeight(0, 3, ramp)).toBeNull();
    const floors = [surface(), surface({ id: 'upper', fromY: 6.3, toY: 6.3 })];
    expect(supportedGroundHeight(0, 0, .6, 0, floors)).toBe(.6);
    expect(supportedGroundHeight(0, 0, 6.3, 0, floors)).toBe(6.3);
    expect(supportedGroundHeight(0, 0, 0, 0, [floors[1]])).toBe(0);
  });

  it('transforms scaled model floors and lintels into the same world-space footprint', () => {
    const navigation = mapPropNavigation([{ id: 'workshop', kind: 'frontier_workshop', x: 10, z: -10, y: 2,
      colliderSpace: 'model', rotY: Math.PI / 2, scale: 2, scaleX: 1.5, scaleY: .5,
      colliders: [{ x: 1, z: 2, width: 4, depth: 1, minY: 3, maxY: 5 }],
      walkableSurfaces: [{ x: 1, z: 2, width: 4, depth: 1, fromY: 0, toY: .6 }],
    }], () => 7);
    const floor = navigation.walkableSurfaces[0], lintel = navigation.collision[0];
    expect(floor.x).toBeCloseTo(14); expect(floor.z).toBeCloseTo(-13);
    expect(floor.width).toBe(12); expect(floor.depth).toBe(2);
    expect(floor.fromY).toBe(9); expect(floor.toY).toBe(9.6);
    expect(walkableSurfaceHeight(13.5, -13, floor)).toBeCloseTo(9.15);
    expect(lintel.minY).toBe(12); expect(lintel.maxY).toBe(14);
    expect(lintel.minX).toBeCloseTo(13); expect(lintel.maxX).toBeCloseTo(15);
    expect(lintel.minZ).toBeCloseTo(-19); expect(lintel.maxZ).toBeCloseTo(-7);
    const gate = { id: 'gate', kind: 'gate', x: 0, z: 0, y: 3, heightMode: 'absolute' as const,
      colliders: [{ width: 6, depth: 1 }], walkableSurfaces: [{ width: 6, depth: 1, fromY: 0, toY: 0 }] };
    const dynamic = mapPropNavigation([gate], () => 90, new Set(['gate']));
    expect(dynamic.collision).toEqual([]);
    expect(dynamic.walkableSurfaces[0].fromY).toBe(3);
  });

  it('keeps an angled doorway clear while blocking its actual wall faces', () => {
    const navigation = mapPropNavigation([{ kind: 'frontier_entry', x: 0, z: 0, rotY: Math.PI / 4,
      colliders: [{ x: -4, width: 5, depth: 4 }, { x: 4, width: 5, depth: 4 }] }], () => 0);
    const blocked = (x: number, z: number) => navigation.collision.some(collider => campaignColliderContains(collider, { x, y: 0, z }, .5));
    for (let z = -3; z <= 3; z += .25) expect(blocked(-z * Math.SQRT1_2, z * Math.SQRT1_2)).toBe(false);
    expect(blocked(4 * Math.SQRT1_2, 4 * Math.SQRT1_2)).toBe(true);
    expect(blocked(-4 * Math.SQRT1_2, -4 * Math.SQRT1_2)).toBe(true);
  });

  it('walks up a raised workshop ramp, crosses its floor and passes beneath its lintel', () => {
    const config = defaultZoneConfig('sunmeadow_march');
    config.terrain = { sourceVersion: 'flat-test', landforms: [], flattenAreas: [], clearCorridors: [] };
    config.walkableSurfaces = [
      surface({ id: 'ramp', z: -3, depth: 2, fromY: 0, toY: .6 }),
      surface(), surface({ id: 'roof', fromY: 5, toY: 5 }),
    ];
    config.collision = [{ minX: -2, maxX: 2, minZ: -2.2, maxZ: -1.8, minY: 3.2, maxY: 5 }];
    const state = createCampaign({ zones: [config] });
    addPlayer(state, { id: 'walker', userId: 'user', characterId: 'character', realm: 'aegis' });
    const player = state.players.walker, zone = state.zones.sunmeadow_march;
    Object.values(zone.npcs).forEach(npc => { npc.health = 0; });
    player.position = { x: 0, y: 0, z: -4.2 };
    let previous = player.position.y;
    for (let tick = 0; tick < 15; tick++) {
      submitCommand(state, player.id, { version: 1, sequence: player.lastSequence + 1, activationId: zone.activationId,
        action: { type: 'move', direction: { x: 0, z: 1 } } });
      advanceSimulation(state, .05);
      expect(Math.abs(player.position.y - previous)).toBeLessThan(.11);
      expect(player.position.y).toBeCloseTo(campaignGroundHeight(config, player.position));
      previous = player.position.y;
    }
    expect(player.position.z).toBeGreaterThan(0);
    expect(player.position.y).toBeCloseTo(.6);
  });

  it('blocks a low lintel at the raised floor height and keeps legacy full-height barriers solid', () => {
    const config = defaultZoneConfig('sunmeadow_march');
    config.walkableSurfaces = [surface({ width: 10, depth: 10 })];
    config.collision = [{ minX: .8, maxX: 1.2, minZ: -5, maxZ: 5, minY: 2.2, maxY: 4 }];
    const state = createCampaign({ zones: [config] });
    addPlayer(state, { id: 'walker', userId: 'user', characterId: 'character', realm: 'aegis' });
    const player = state.players.walker, zone = state.zones.sunmeadow_march;
    player.position = { x: 0, y: .6, z: 0 };
    const walk = () => {
      submitCommand(state, player.id, { version: 1, sequence: player.lastSequence + 1, activationId: zone.activationId,
        action: { type: 'move', direction: { x: 1, z: 0 } } });
      advanceSimulation(state, .25);
    };
    walk(); expect(player.position.x).toBeLessThan(.31);
    zone.config.collision![0] = { minX: .8, maxX: 1.2, minZ: -5, maxZ: 5 };
    player.position = { x: 0, y: 20, z: 0 };
    walk(); expect(player.position.x).toBeLessThan(.31);
  });

  it('permits a wallwalk over a closed gate while keeping the ground passage blocked', () => {
    const config = defaultZoneConfig('sunmeadow_march');
    config.keeps[0].outerGate = { x: 0, y: 0, z: 0 };
    config.keeps[0].gateFootprints = { outer: { width: 6, depth: .5, height: 4.8 } };
    config.walkableSurfaces = [surface({ width: 10, depth: 10, fromY: 6.3, toY: 6.3 })];
    config.collision = [];
    const state = createCampaign({ zones: [config] });
    addPlayer(state, { id: 'walker', userId: 'user', characterId: 'character', realm: 'aegis' });
    const player = state.players.walker, zone = state.zones.sunmeadow_march;
    const cross = (height: number) => {
      player.position = { x: 0, y: height, z: -1.5 };
      for (let tick=0; tick<12; tick++) {
        submitCommand(state, player.id, { version: 1, sequence: player.lastSequence + 1, activationId: zone.activationId,
          action: { type: 'move', direction: { x: 0, z: 1 } } });
        advanceSimulation(state,.05);
      }
    };
    cross(6.3); expect(player.position.z).toBeGreaterThan(1); expect(player.position.y).toBeCloseTo(6.3);
    cross(0); expect(player.position.z).toBeLessThan(-.7);
  });
});

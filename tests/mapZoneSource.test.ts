import { describe, expect, test } from 'vitest';
import { resolveMapZone } from '../src/world/mapZoneSource';
import { applyZonePaths } from '../src/world/PathKit';
import { createEmptyWorldEditDocument } from '../src/world/WorldEditValidation';
import { Game } from '../src/game/Game';
import { WorldEditorRuntime } from '../src/world/editor/WorldEditorRuntime';
import type { WorldPropObject } from '../src/services/types';
import type { ZoneDefinition } from '../src/world/ZoneLoader';

const zone: ZoneDefinition = { id: 'test', name: 'Test', size: 200, segments: 1, enemies: [], props: [
  { id: 'home', kind: 'aegis_house_1', x: 10, z: 20, scale: 2, colliders: [{ width: 10, depth: 10 }] },
  { kind: 'tree', x: 5, z: 5 },
] };
const object = (id: string, x = 40): WorldPropObject => ({ id, kind: 'aegis_house_1', type: 'prop', createdAt: 0, updatedAt: 0,
  transform: { position: { x, y: 4, z: 60 }, rotation: { x: 0, y: 1, z: 0 }, scale: { x: 3, y: 3, z: 3 } },
  colliders: [{ width: 10, depth: 10 }],
});

describe('map source follows zone edits', () => {
  test('applies moves/scales/additions/hides with runtime IDs and preserves source data', () => {
    const doc = createEmptyWorldEditDocument('test', 'draft');
    doc.objects = [object('home'), { ...object('static-prop-0001'), hidden: true }, object('new-home', 80)];
    const result = resolveMapZone(zone, doc);
    expect(result.props).toHaveLength(2);
    expect(result.props[0]).toMatchObject({ id: 'home', x: 40, y: 4, z: 60, scale: 1, scaleX: 3, rotY: 1 });
    expect(result.props[1].x).toBe(80);
    expect(zone.props[0]).toMatchObject({ x: 10, scale: 2 });
    expect(resolveMapZone(zone, null)).toBe(zone);
    expect(resolveMapZone(zone, { ...doc, zoneId: 'elsewhere' })).toBe(zone);
    doc.objects = [];
    expect(resolveMapZone(zone, doc).props).toEqual(zone.props);
  });

  test('uses edited road strips instead of leaving an obsolete centerline', () => {
    const source = applyZonePaths({ ...zone, paths: [{ id: 'street', style: 'dirt_trail', width: 5, points: [{ x: 0, z: 0 }, { x: 20, z: 0 }] }] });
    const doc = createEmptyWorldEditDocument('test', 'draft');
    doc.objects = [{ ...object('street_segment_0'), kind: 'path_dirt' }];
    const mapped = resolveMapZone(source, doc);
    expect(mapped.paths).toEqual([]);
    expect(mapped.props.find(p => p.id === 'street_segment_0')?.x).toBe(40);
    expect(mapped.props.some(p => p.id === 'street_segment_1')).toBe(true);
  });

  test('does not apply edits from an obsolete city layout and preserves authored labels', () => {
    const capital = { ...zone, cityLayoutVersion: 'current' };
    const doc = createEmptyWorldEditDocument('test', 'published');
    doc.cityLayoutVersion = 'old';
    doc.objects = [{ ...object('home'), label: 'North Workshop' }];
    expect(resolveMapZone(capital, doc)).toBe(capital);
    doc.cityLayoutVersion = 'current';
    expect(resolveMapZone(capital, doc).props[0].label).toBe('North Workshop');
  });

  test('projects the top surviving voxel material and removes erased columns', () => {
    const doc = createEmptyWorldEditDocument('test', 'draft');
    doc.voxelChunks = [{ key: '0', origin: { x: 10, y: 0, z: 20 }, size: 4, voxelSize: 2, updatedAt: 0, cells: {
      '0:0:0': { density: 1, material: 'stone' }, '0:1:0': { density: 0.5, material: 'grass' }, '1:0:0': { density: 0, material: 'water' },
    } }];
    const painted = resolveMapZone(zone, doc).props.filter(p => p.kind.startsWith('map_ground_'));
    expect(painted).toHaveLength(1);
    expect(painted[0]).toMatchObject({ kind: 'map_ground_grass', x: 11, z: 21, y: 3 });
    doc.voxelChunks = [];
    expect(resolveMapZone(zone, doc).props).toEqual(zone.props);
  });

  test('live game maps rebuild after editor changes and reuse geometry between changes', () => {
    const doc = createEmptyWorldEditDocument('test', 'draft');
    doc.objects = [object('home')];
    const editor = Object.assign(Object.create(WorldEditorRuntime.prototype), { document: doc, mapRevisionValue: 0 });
    const game = Object.assign(Object.create(Game.prototype), { currentZone: zone, worldEditor: editor });
    const first = game.mapZoneDefinition;
    expect(game.mapZoneDefinition).toBe(first);
    editor.document.objects[0] = object('home', 90);
    editor.emitChanged();
    expect(editor.mapRevision).toBe(1);
    expect(game.mapZoneDefinition).not.toBe(first);
    expect(game.mapZoneDefinition.props[0].x).toBe(90);
    editor.document.objects = [];
    editor.emitChanged();
    expect(game.mapZoneDefinition.props).toEqual(zone.props);
  });
});

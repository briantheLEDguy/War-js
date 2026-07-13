import type { Vec3, WorldPropObject } from '../../services/types';

export interface PrefabFootprint {
  width: number;
  depth: number;
  chainAxis: 'x' | 'z';
}

export interface WorldEditorPrefabDefinition {
  kind: string;
  label: string;
  group?: string;
  model?: string;
  assetKey?: string;
  fallbackKind?: string;
  footprint: PrefabFootprint;
  defaultScale?: Vec3;
  colliders?: WorldPropObject['colliders'];
  walkableSurfaces?: WorldPropObject['walkableSurfaces'];
  cameraSolid?: boolean;
}

const DEFAULT_SCALE: Vec3 = { x: 1, y: 1, z: 1 };
const GENERAL_PREFAB_GROUP = 'General';
const MODULAR_TOWN_KIT_GROUP = 'Modular Town Kit';
const FORTRESS_BUILD_PACK_GROUP = 'Fortress Build Pack';

export const WORLD_EDITOR_PREFABS: WorldEditorPrefabDefinition[] = [
  {
    kind: 'building',
    label: 'Aegis House',
    model: 'prop_town_house_1.glb',
    assetKey: 'town_house_1',
    fallbackKind: 'building',
    footprint: { width: 9.8, depth: 7.4, chainAxis: 'z' },
    colliders: [{ width: 9.8, depth: 7.4 }],
    cameraSolid: true,
  },
  {
    kind: 'rift_house',
    label: 'Rift House',
    model: 'prop_town_house_2.glb',
    assetKey: 'town_house_2',
    fallbackKind: 'rift_house',
    footprint: { width: 12.2, depth: 9, chainAxis: 'z' },
    colliders: [{ width: 12.2, depth: 9 }],
    cameraSolid: true,
  },
  {
    kind: 'castle_floor',
    label: 'Castle Floor',
    model: undefined,
    footprint: { width: 24, depth: 24, chainAxis: 'z' },
    walkableSurfaces: [{ width: 24, depth: 24, fromY: 0, toY: 0 }],
    cameraSolid: true,
  },
  {
    kind: 'wall_segment',
    label: 'Aegis Wall',
    footprint: { width: 12, depth: 2, chainAxis: 'x' },
    colliders: [{ width: 12, depth: 2 }],
    cameraSolid: true,
  },
  {
    kind: 'rift_wall_segment',
    label: 'Rift Wall',
    footprint: { width: 12, depth: 2, chainAxis: 'x' },
    colliders: [{ width: 12, depth: 2 }],
    cameraSolid: true,
  },
  {
    kind: 'tower',
    label: 'Aegis Tower',
    footprint: { width: 7, depth: 7, chainAxis: 'z' },
    colliders: [{ width: 7, depth: 7 }],
    cameraSolid: true,
  },
  {
    kind: 'rift_tower',
    label: 'Rift Tower',
    footprint: { width: 7, depth: 7, chainAxis: 'z' },
    colliders: [{ width: 7.5, depth: 7.5 }],
    cameraSolid: true,
  },
  { kind: 'gate', label: 'Field Gate', footprint: { width: 16, depth: 4, chainAxis: 'x' } },
  {
    kind: 'castle_gate',
    label: 'Fortress Gate',
    group: FORTRESS_BUILD_PACK_GROUP,
    model: 'castle_gate.glb',
    footprint: { width: 18, depth: 2.5, chainAxis: 'x' },
    colliders: [{ width: 18, depth: 2.5, blocksWhen: 'closed' }],
    cameraSolid: true,
  },
  {
    kind: 'castle_door',
    label: 'Castle Door',
    group: FORTRESS_BUILD_PACK_GROUP,
    model: 'castle_door.glb',
    footprint: { width: 5.2, depth: 0.5, chainAxis: 'x' },
    colliders: [{ width: 5.4, depth: 1.2, blocksWhen: 'closed' }],
    cameraSolid: true,
  },
  {
    kind: 'castle_stairs',
    label: 'Castle Stairs',
    group: FORTRESS_BUILD_PACK_GROUP,
    model: 'castle_stairs.glb',
    footprint: { width: 8, depth: 12, chainAxis: 'z' },
    walkableSurfaces: [
      { width: 8, depth: 12, fromY: 0, toY: 4, axis: 'z' },
      { z: 7, width: 10, depth: 6, fromY: 4, toY: 4 },
    ],
  },
  { kind: 'temple', label: 'Temple', footprint: { width: 12, depth: 20, chainAxis: 'z' }, cameraSolid: true },
  { kind: 'statue', label: 'Statue', footprint: { width: 1.8, depth: 1.8, chainAxis: 'z' }, cameraSolid: true },
  { kind: 'fountain', label: 'Fountain', footprint: { width: 5.6, depth: 5.6, chainAxis: 'z' }, cameraSolid: true },
  {
    kind: 'rift_obelisk',
    label: 'Rift Obelisk',
    footprint: { width: 2.5, depth: 2.5, chainAxis: 'z' },
    colliders: [{ width: 2.5, depth: 2.5 }],
    cameraSolid: true,
  },
  {
    kind: 'rift_brazier',
    label: 'Rift Brazier',
    footprint: { width: 1.8, depth: 1.8, chainAxis: 'z' },
    colliders: [{ width: 1.8, depth: 1.8 }],
    cameraSolid: true,
  },
  {
    kind: 'rift_spike_cluster',
    label: 'Rift Spikes',
    footprint: { width: 3.5, depth: 3.5, chainAxis: 'z' },
    colliders: [{ width: 3.5, depth: 3.5 }],
    cameraSolid: true,
  },
  { kind: 'banner_post', label: 'Banner Post', footprint: { width: 1.5, depth: 1.5, chainAxis: 'z' } },
  { kind: 'vendor_stall', label: 'Vendor Stall', footprint: { width: 3, depth: 2, chainAxis: 'x' }, cameraSolid: true },
  { kind: 'bridge', label: 'Bridge', footprint: { width: 4, depth: 12, chainAxis: 'z' } },
  { kind: 'dock', label: 'Dock', footprint: { width: 4, depth: 14, chainAxis: 'z' } },
  { kind: 'tree', label: 'Tree', footprint: { width: 3, depth: 3, chainAxis: 'z' } },
  { kind: 'rock', label: 'Rock', footprint: { width: 1.4, depth: 1.4, chainAxis: 'z' } },

  townPrefab('town_house_1', 'Town House 1', 'prop_town_house_1.glb', 14, 18, [{ width: 12, depth: 15 }]),
  townPrefab('town_house_2', 'Town House 2', 'prop_town_house_2.glb', 18, 22, [{ width: 15, depth: 18 }]),
  townPrefab('town_castle', 'Capital Castle', 'prop_town_castle.glb', 38, 34, [{ width: 38, depth: 34 }]),
  townPrefab('town_roof', 'Town Roof', 'prop_town_roof.glb', 6, 7),
  townPrefab('town_wooden_wall_light', 'Light Wood Wall', 'prop_town_wooden_wall_light.glb', 5, 0.6, [{ width: 5, depth: 0.6 }], 'x'),
  townPrefab('town_wooden_wall_dark', 'Dark Wood Wall', 'prop_town_wooden_wall_dark.glb', 5, 0.6, [{ width: 5, depth: 0.6 }], 'x'),
  townPrefab('town_rock_wall_large', 'Large Stone Wall', 'prop_town_rock_wall_large.glb', 4.5, 0.9, [{ width: 4.5, depth: 0.9 }], 'x'),
  townPrefab('town_rock_wall_small', 'Small Stone Wall', 'prop_town_rock_wall_small.glb', 2.6, 0.8, [{ width: 2.6, depth: 0.8 }], 'x'),
  townPrefab('town_door', 'Town Door', 'prop_town_door.glb', 1.6, 0.5, undefined, 'x'),
  townPrefab('town_door_2', 'Town Door 2', 'prop_town_door_2.glb', 1.6, 0.5, undefined, 'x'),
  townPrefab('town_window', 'Town Window', 'prop_town_window.glb', 1.6, 0.5, undefined, 'x'),
  townPrefab('town_diamond_window', 'Diamond Window', 'prop_town_diamond_window.glb', 1.6, 0.5, undefined, 'x'),
  townPrefab('town_chimney', 'Town Chimney', 'prop_town_chimney.glb', 1.2, 1.2, [{ width: 1.2, depth: 1.2 }]),
  townPrefab('town_spire', 'Town Spire', 'prop_town_spire.glb', 2.2, 2.2, [{ width: 2.2, depth: 2.2 }]),
  townPrefab('town_roof_plank_small', 'Small Roof Plank', 'prop_town_roof_plank_small.glb', 2.5, 1.2, undefined, 'x'),
  townPrefab('town_roof_plank_medium', 'Medium Roof Plank', 'prop_town_roof_plank_medium.glb', 3.6, 1.3, undefined, 'x'),
  townPrefab('town_roof_plank_large', 'Large Roof Plank', 'prop_town_roof_plank_large.glb', 4.8, 1.4, undefined, 'x'),
  townPrefab('town_horizontal_beam', 'Horizontal Beam', 'prop_town_horizontal_beam.glb', 4.8, 0.5, [{ width: 4.8, depth: 0.5 }], 'x'),
  townPrefab('town_vertical_beam', 'Vertical Beam', 'prop_town_vertical_beam.glb', 0.8, 0.8, [{ width: 0.8, depth: 0.8 }]),
  townPrefab('town_plank_arc', 'Plank Arc', 'prop_town_plank_arc.glb', 4.4, 1.2, [{ width: 4.4, depth: 1.2 }], 'x'),

  fortressPrefab('town_fortress_wall', 'Crenellated Curtain Wall', 'prop_town_fortress_wall.glb', 12, 3, [{ width: 12, depth: 3 }], [{ width: 11.6, depth: 2.2, fromY: 6.7, toY: 6.7 }], 'x'),
  fortressPrefab('town_fortress_corner_tower', 'Fortress Corner Tower', 'prop_town_fortress_corner_tower.glb', 10.4, 10.4, [{ width: 10.4, depth: 10.4 }]),
  fortressPrefab('town_fortress_gatehouse', 'Fortress Gatehouse', 'prop_town_fortress_gatehouse.glb', 28, 6, [
    { x: -10, width: 7, depth: 6 },
    { x: 10, width: 7, depth: 6 },
  ], [{ width: 26, depth: 5.4, fromY: 10.2, toY: 10.2 }], 'x'),
  fortressPrefab('town_fortress_wall_stairs', 'Wall Stairs', 'prop_town_fortress_wall_stairs.glb', 7.2, 11.5, undefined, [{ width: 6.2, depth: 10.8, fromY: 0, toY: 6.4, axis: 'z' }]),
  fortressPrefab('town_fortress_brazier', 'Ember Brazier', 'prop_town_fortress_brazier.glb', 2.7, 2.7, [{ width: 2.7, depth: 2.7 }]),
  fortressPrefab('town_fortress_banner', 'Torn War Banner', 'prop_town_fortress_banner.glb', 3.5, 1.5, [{ width: 1.5, depth: 1.5 }]),
  fortressPrefab('town_fortress_barricade', 'Siege Barricade', 'prop_town_fortress_barricade.glb', 6.5, 2.8, [{ width: 6.5, depth: 2.8 }], undefined, 'x'),
];

const PREFABS_BY_KIND = new Map(WORLD_EDITOR_PREFABS.map((prefab) => [prefab.kind, prefab]));

export const WORLD_EDITOR_PREFAB_GROUPS = Array.from(
  new Set(WORLD_EDITOR_PREFABS.map((prefab) => prefab.group ?? GENERAL_PREFAB_GROUP)),
);

export function prefabGroupForKind(kind: string): string {
  return prefabDefinitionForKind(kind)?.group ?? GENERAL_PREFAB_GROUP;
}

export function prefabsForGroup(group: string): WorldEditorPrefabDefinition[] {
  return WORLD_EDITOR_PREFABS.filter((prefab) => (prefab.group ?? GENERAL_PREFAB_GROUP) === group);
}

export function prefabDefinitionForKind(kind: string): WorldEditorPrefabDefinition | null {
  return PREFABS_BY_KIND.get(kind) ?? null;
}

export function prefabLabelForKind(kind: string): string {
  return prefabDefinitionForKind(kind)?.label ?? kind.replaceAll('_', ' ');
}

export function prefabDefaultModelForKind(kind: string): string | undefined {
  return prefabDefinitionForKind(kind)?.model;
}

export function prefabDefaultAssetKeyForKind(kind: string): string | undefined {
  return prefabDefinitionForKind(kind)?.assetKey;
}

export function prefabFallbackKindForKind(kind: string): string | undefined {
  return prefabDefinitionForKind(kind)?.fallbackKind;
}

export function prefabDefaultScaleForKind(kind: string): Vec3 {
  const scale = prefabDefinitionForKind(kind)?.defaultScale ?? DEFAULT_SCALE;
  return { ...scale };
}

export function prefabDefaultCollidersForKind(
  kind: string,
  interactionId?: string,
): WorldPropObject['colliders'] {
  const colliders = clone(prefabDefinitionForKind(kind)?.colliders);
  if (!colliders) return undefined;
  return colliders.map((collider) => ({
    ...collider,
    interactionId: collider.blocksWhen === 'closed' ? interactionId : collider.interactionId,
  }));
}

export function prefabDefaultWalkablesForKind(kind: string): WorldPropObject['walkableSurfaces'] {
  return clone(prefabDefinitionForKind(kind)?.walkableSurfaces);
}

export function prefabFootprintForKind(kind: string): PrefabFootprint {
  return prefabDefinitionForKind(kind)?.footprint ?? { width: 7, depth: 7, chainAxis: 'z' };
}

export function isPrefabCameraSolidKind(kind: string): boolean {
  return prefabDefinitionForKind(kind)?.cameraSolid === true;
}

export function prefabHouseInteriorVariantForKind(kind: string): 'small' | 'large' | undefined {
  if (kind === 'building' || kind === 'town_house_1') return 'small';
  if (kind === 'rift_house' || kind === 'town_house_2') return 'large';
  return undefined;
}

function townPrefab(
  kind: string,
  label: string,
  model: string,
  width: number,
  depth: number,
  colliders?: WorldPropObject['colliders'],
  chainAxis: 'x' | 'z' = 'z',
): WorldEditorPrefabDefinition {
  return {
    kind,
    label,
    group: MODULAR_TOWN_KIT_GROUP,
    model,
    assetKey: kind,
    fallbackKind: 'building',
    footprint: { width, depth, chainAxis },
    colliders,
    cameraSolid: Boolean(colliders),
  };
}

function fortressPrefab(
  kind: string,
  label: string,
  model: string,
  width: number,
  depth: number,
  colliders?: WorldPropObject['colliders'],
  walkableSurfaces?: WorldPropObject['walkableSurfaces'],
  chainAxis: 'x' | 'z' = 'z',
): WorldEditorPrefabDefinition {
  return {
    kind,
    label,
    group: FORTRESS_BUILD_PACK_GROUP,
    model,
    assetKey: kind,
    fallbackKind: 'building',
    footprint: { width, depth, chainAxis },
    colliders,
    walkableSurfaces,
    cameraSolid: Boolean(colliders),
  };
}

function clone<T>(value: T | undefined): T | undefined {
  return value === undefined ? undefined : JSON.parse(JSON.stringify(value)) as T;
}

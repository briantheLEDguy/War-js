import * as THREE from 'three';
import type { AssetLoader } from '../game/AssetLoader';
import { StaticPropInstances } from '../game/StaticPropInstances';
import type { PropSpawn } from './ZoneLoader';
import type { SpawnedStaticWorldObject } from './Props';

const ambientMixers = new WeakMap<THREE.Object3D, THREE.AnimationMixer[]>();

export function isFrontierProp(prop: Pick<PropSpawn, 'kind' | 'assetKey' | 'model'>): boolean {
  return Boolean(prop.kind.startsWith('frontier_') || prop.assetKey?.startsWith('frontier_') || /(?:^|\/)(?:prop_)?frontier_[^/]+\.glb$/i.test(prop.model ?? ''));
}

export function frontierPropDistances(key: string): { lod: number[]; cull: number } {
  if (/^frontier_siege_(repair_bench|ammunition_cradle)$/.test(key)) return { lod: [0, 16, 42], cull: 160 };
  if (key === 'frontier_sunmeadow_skylark') return { lod: [0], cull: 30 };
  if (/^frontier_sunmeadow_(roe_deer|red_fox|brown_hare|barrow_wolf)/.test(key)) return { lod: [0, 22, 60], cull: 150 };
  if (key === 'frontier_cinderfen_marsh_alder') return { lod: [0, 35, 90], cull: 450 };
  if (key === 'frontier_cinderfen_basalt_outcrop') return { lod: [0, 20, 50], cull: 550 };
  if (key === 'frontier_cinderfen_reed_clump') return { lod: [0, 18, 45], cull: 120 };
  if (key === 'frontier_cinderfen_sedge_horsetail') return { lod: [0, 12, 30], cull: 75 };
  if (/^frontier_sunmeadow_(wheat|meadow)/.test(key)) return { lod: [0, 12, 30], cull: 80 };
  if (/^frontier_sunmeadow_hawthorn/.test(key)) return { lod: [0, 18, 55], cull: 330 };
  if (/^frontier_sunmeadow_(oak|ash)/.test(key)) return { lod: [0, 30, 90], cull: 600 };
  if (/^frontier_sunmeadow_limestone/.test(key)) return { lod: [0, 40, 120], cull: 600 };
  return { lod: [0, 90, 240], cull: 700 };
}

/** Only manifest/QC-approved geometry can provide a frontier prop or its collision support. */
export async function loadApprovedFrontierProp(prop: PropSpawn, loader: Pick<AssetLoader, 'resolveApprovedAssetModels' | 'loadModelFull'>): Promise<{ object: THREE.LOD; animations: THREE.AnimationClip[] } | null> {
  const key = prop.assetKey ?? (prop.kind.startsWith('frontier_') ? prop.kind : undefined);
  if (!key) return null;
  const models = await loader.resolveApprovedAssetModels(key, 'staticProps');
  const lod = new THREE.LOD(); lod.autoUpdate = false;
  const distances = frontierPropDistances(key).lod;
  let animations: THREE.AnimationClip[] = [];
  const mixers: THREE.AnimationMixer[] = [];
  for (const [index, model] of models.entries()) {
    const loaded = await loader.loadModelFull(model, () => new THREE.Group());
    let meshes = 0;
    loaded.object.traverse(node => { if ((node as THREE.Mesh).isMesh) meshes++; });
    if (!meshes) continue;
    // Interactive gate animations remain on one authored hierarchy, without LOD track ambiguity.
    if (!lod.levels.length) animations = loaded.animations;
    lod.addLevel(loaded.object, distances[Math.min(index, distances.length - 1)], .12);
    const clip = !prop.interaction && loaded.animations.find(clip => clip.name === prop.defaultAnimation);
    if (clip) { const mixer = new THREE.AnimationMixer(loaded.object); mixer.clipAction(clip).play(); mixers.push(mixer); }
    if (prop.interaction) break;
  }
  if (!lod.levels.length) return null;
  lod.levels.forEach((level, index) => { level.object.visible = index === 0; });
  lod.userData.approvedFrontierAsset = key;
  if (mixers.length) ambientMixers.set(lod, mixers);
  return { object: lod, animations };
}

interface FrontierEntry { id: string; object: THREE.LOD; cull: number }
interface Cell { batcher: StaticPropInstances; group: THREE.Group; entries: FrontierEntry[] }

/** Spatial batches retain editor source objects/colliders; GM mode restores their individual meshes. */
export class FrontierInstances {
  private cells = new Map<string, Cell>();
  private elapsed = 1;
  private enabled = true;
  private position = new THREE.Vector3();
  private cameraPosition = new THREE.Vector3();
  private animationTime = 0;
  constructor(private readonly scene: THREE.Scene, objects: SpawnedStaticWorldObject[]) {
    for (const source of objects) {
      const key = source.object.userData.approvedFrontierAsset;
      if (typeof key !== 'string' || !(source.object instanceof THREE.LOD) || source.definition.interaction) continue;
      const position = source.object.position;
      const cellId = `${Math.floor(position.x / 160)},${Math.floor(position.z / 160)}`;
      let cell = this.cells.get(cellId);
      if (!cell) {
        const group = new THREE.Group(); group.name = `frontier-instances-${cellId}`; scene.add(group);
        cell = { group, batcher: new StaticPropInstances(group), entries: [] }; this.cells.set(cellId, cell);
      }
      cell.entries.push({ id: source.id, object: source.object, cull: frontierPropDistances(key).cull });
    }
  }

  update(camera: THREE.Camera, enabled: boolean, suppressed: (id: string) => boolean, dt: number): void {
    this.animationTime += dt;
    for (const cell of this.cells.values()) for (const entry of cell.entries) {
      if (!entry.object.visible || suppressed(entry.id)) continue;
      for (const mixer of ambientMixers.get(entry.object) ?? []) {
        if ((mixer.getRoot() as THREE.Object3D).visible) mixer.setTime(this.animationTime);
      }
    }
    this.elapsed += dt;
    if (this.elapsed < .25 && enabled === this.enabled) return;
    this.elapsed = 0; this.enabled = enabled;
    camera.getWorldPosition(this.cameraPosition);
    this.scene.updateMatrixWorld(true);
    for (const cell of this.cells.values()) {
      const visible: THREE.Object3D[] = [];
      const hidden: THREE.Object3D[] = [];
      for (const entry of cell.entries) {
        entry.object.getWorldPosition(this.position);
        if (suppressed(entry.id) || enabled && this.position.distanceTo(this.cameraPosition) > entry.cull) hidden.push(entry.object);
        else {
          entry.object.visible = true;
          entry.object.update(camera);
          visible.push(entry.object);
        }
      }
      // Batches compute their own bounds; renderer frustum culling still covers every shadow camera.
      cell.batcher.update(visible, enabled);
      for (const object of hidden) object.visible = false;
    }
  }

  dispose(): void {
    for (const cell of this.cells.values()) {
      for (const entry of cell.entries) for (const mixer of ambientMixers.get(entry.object) ?? []) {
        mixer.stopAllAction(); mixer.uncacheRoot(mixer.getRoot());
      }
      cell.batcher.dispose(); cell.group.removeFromParent();
    }
    this.cells.clear();
  }
}

import * as THREE from 'three';
import type { AssetLoader } from '../game/AssetLoader';
import { StaticPropInstances } from '../game/StaticPropInstances';
import type { PropSpawn } from './ZoneLoader';
import type { SpawnedStaticWorldObject } from './Props';

export function isFrontierProp(prop: Pick<PropSpawn, 'kind' | 'assetKey' | 'model'>): boolean {
  return Boolean(prop.kind.startsWith('frontier_') || prop.assetKey?.startsWith('frontier_') || /(?:^|\/)(?:prop_)?frontier_[^/]+\.glb$/i.test(prop.model ?? ''));
}

export function frontierPropDistances(key: string): { lod: number[]; cull: number } {
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
  for (const [index, model] of models.entries()) {
    const loaded = await loader.loadModelFull(model, () => new THREE.Group());
    let meshes = 0;
    loaded.object.traverse(node => { if ((node as THREE.Mesh).isMesh) meshes++; });
    if (!meshes) continue;
    // Interactive gate animations remain on one authored hierarchy, without LOD track ambiguity.
    if (!lod.levels.length) animations = loaded.animations;
    lod.addLevel(loaded.object, distances[Math.min(index, distances.length - 1)], .12);
    if (prop.interaction) break;
  }
  if (!lod.levels.length) return null;
  lod.levels.forEach((level, index) => { level.object.visible = index === 0; });
  lod.userData.approvedFrontierAsset = key;
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
    for (const cell of this.cells.values()) { cell.batcher.dispose(); cell.group.removeFromParent(); }
    this.cells.clear();
  }
}

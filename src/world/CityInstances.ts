import * as THREE from 'three';
import type { SpawnedStaticWorldObject } from './Props';
import { CITY_LOD_DISTANCES } from './CityArchitecture';
import { CityRenderBatch, cityBatchKey, supportsCityBatch } from './CityRenderBatch';
interface Part {
  batch: CityRenderBatch;
  slot: number;
  matrix: THREE.Matrix4;
  source: THREE.Mesh;
}
interface Entry {
  id: string;
  object: THREE.Object3D;
  position: THREE.Vector3;
  levels: Part[][];
  activeLevel: number;
  bounds: THREE.Sphere;
  detached: boolean;
  renderOriginal: boolean;
  detailCullDistance: number;
}
/** Batch repeated static architecture while retaining the individual authoring
* objects, colliders and interaction IDs. GM mode restores those originals. */
export class CityInstances {
  private entries: Entry[] = [];
  private batches = new Map<string, CityRenderBatch>();
  private enabled = true;
  private viewFrustum = new THREE.Frustum();
  private projection = new THREE.Matrix4();
  private identity = new THREE.Matrix4();
  private shadowLights: THREE.Light[] = [];
  private dirtyBatches = new Set<CityRenderBatch>();
  private revision = -1;
  constructor(private scene: THREE.Scene, objects: SpawnedStaticWorldObject[], multiDraw = false) {
    scene.traverse(node => { if (node instanceof THREE.Light) this.shadowLights.push(node); });
    const eligible = objects.filter(o => /^(aegis_|riftspire_)/.test(o.definition.kind)
      && o.definition.kind !== 'riftspire_lift' && !o.definition.interaction && supportsCityBatch(o.object));
    const cells = new Map<string, string>();
    for (const entry of eligible) {
      const p = entry.object.position;
      cells.set(entry.id, entry.definition.kind.startsWith('riftspire_')
        ? `${Math.floor((p.x+512)/512)},${Math.floor((p.z+512)/512)}` : 'shared');
    }
    const sources = new Map<string, THREE.Mesh[]>();
    for (const entry of eligible) {
      entry.object.traverse(node => {
        if (!(node instanceof THREE.Mesh) || Array.isArray(node.material)) return;
        const key = cityBatchKey(node, cells.get(entry.id)!, multiDraw);
        const group = sources.get(key) ?? [];
        group.push(node); sources.set(key, group);
      });
    }
    for (const entry of eligible) {
      const root = entry.object;
      root.updateMatrixWorld(true);
      const levels = root instanceof THREE.LOD ? root.levels.map(l => l.object) : [root];
      const parts = levels.map(level => {
        const result: Part[] = [];
        level.traverse(node => {
          if (!(node instanceof THREE.Mesh) || Array.isArray(node.material))
            return;
          const key = cityBatchKey(node, cells.get(entry.id)!, multiDraw);
          let batch = this.batches.get(key);
          if (!batch) {
            batch = new CityRenderBatch(sources.get(key)!, multiDraw);
            this.batches.set(key, batch);
            scene.add(batch.object);
          }
          const matrix = node.matrixWorld.clone();
          result.push({ batch, slot: batch.add(node, matrix), matrix, source: node });
        });
        return result;
      });
      if (parts.some(p => p.length))
        this.entries.push({ id: entry.id, object: root, position: root.getWorldPosition(new THREE.Vector3()), levels: parts,
          activeLevel: -2, bounds: new THREE.Box3().setFromObject(root).getBoundingSphere(new THREE.Sphere()), detached: false, renderOriginal: false,
          detailCullDistance: /^riftspire_(lantern|table|archive|rack|altar|forge|crate|bed|banner|war_brazier|arms_rack|checkpoint|market_stall|apothecary|provision_stall|supply_cart|barrel_stack|laundry_rig|communal_hearth|chain_winch|ore_cart|water_pump|war_table|hanging_cage)$/.test(entry.definition.kind) ? 220 : Infinity });
    }
  }
  update(camera: THREE.Camera, enabled: boolean, suppressed: (id: string) => boolean, revision = 0): void {
    this.dirtyBatches.clear();
    if (enabled !== this.enabled || revision !== this.revision) {
      for (const batch of this.batches.values()) this.dirtyBatches.add(batch);
    }
    if (enabled && (!this.enabled || revision !== this.revision)) {
      for (const entry of this.entries) {
        entry.object.updateMatrixWorld(true);
        entry.object.getWorldPosition(entry.position);
        new THREE.Box3().setFromObject(entry.object).getBoundingSphere(entry.bounds);
        for (const level of entry.levels)
          for (const part of level)
            part.matrix.copy(part.source.matrixWorld);
        // GM transforms can introduce a mirror after the initial compatibility check.
        entry.renderOriginal = entry.levels.some(level => level.some(part => part.matrix.determinant() <= 0));
      }
    }
    this.revision = revision;
    camera.updateWorldMatrix(true, false);
    this.viewFrustum.setFromProjectionMatrix(this.projection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
    const shadowFrusta: THREE.Frustum[] = [];
    let allowCulling = true;
    // Include nested light rigs. Point-light cube shadows need multiple views,
    // so retain all instances when one is present rather than dropping shadows.
    for (const child of this.shadowLights) {
      if (child instanceof THREE.PointLight && child.castShadow) allowCulling = false;
      if ((child instanceof THREE.DirectionalLight || child instanceof THREE.SpotLight) && child.castShadow) {
        child.updateWorldMatrix(true, false);
        child.target.updateWorldMatrix(true, false);
        child.shadow.updateMatrices(child);
        shadowFrusta.push(child.shadow.getFrustum());
      }
    }
    this.scene.updateWorldMatrix(true, false);
    this.enabled = enabled;
    for (const entry of this.entries) {
      const hidden = suppressed(entry.id);
      entry.object.visible = (!enabled || entry.renderOriginal) && !hidden;
      if (enabled && !entry.renderOriginal && entry.object.parent === this.scene && this.scene.matrixWorld.equals(this.identity)) {
        this.scene.remove(entry.object);
        entry.detached = true;
      } else if ((!enabled || entry.renderOriginal) && entry.detached) {
        this.scene.add(entry.object);
        entry.detached = false;
      }
      const distanceSq = camera.position.distanceToSquared(entry.position);
      const inView = !allowCulling || this.viewFrustum.intersectsSphere(entry.bounds)
        || shadowFrusta.some(frustum => frustum.intersectsSphere(entry.bounds));
      let level = Math.min(entry.levels.length - 1,
        distanceSq >= CITY_LOD_DISTANCES[2] ** 2 ? 2 : distanceSq >= CITY_LOD_DISTANCES[1] ** 2 ? 1 : 0);
      // Keep the current LOD around a boundary instead of flipping on tiny movements.
      if (entry.activeLevel >= 0 && level !== entry.activeLevel) {
        const boundary = CITY_LOD_DISTANCES[Math.max(level, entry.activeLevel)];
        if (level > entry.activeLevel && distanceSq < (boundary * 1.12) ** 2
          || level < entry.activeLevel && distanceSq > (boundary * 0.88) ** 2) level = entry.activeLevel;
      }
      if (!enabled || entry.renderOriginal || hidden || !inView || distanceSq > entry.detailCullDistance ** 2) level = -1;
      if (level !== entry.activeLevel) {
        for (const part of entry.levels[entry.activeLevel] ?? []) this.dirtyBatches.add(part.batch);
        for (const part of entry.levels[level] ?? []) this.dirtyBatches.add(part.batch);
      }
      entry.activeLevel = level;
    }
    // Static transforms only need GPU uploads/bounds rebuilds when membership changes.
    if (!this.dirtyBatches.size) return;
    for (const batch of this.dirtyBatches) batch.reset();
    for (const entry of this.entries) {
      if (entry.activeLevel < 0) continue;
      for (const { batch, slot, matrix } of entry.levels[entry.activeLevel]) {
        if (this.dirtyBatches.has(batch)) batch.include(slot, matrix);
      }
    }
    for (const batch of this.dirtyBatches) batch.commit(enabled);
  }
  dispose(): void {
    for (const batch of this.batches.values()) {
      batch.dispose();
    }
    if (this.enabled)
      for (const entry of this.entries) {
        if (entry.detached) this.scene.add(entry.object);
        entry.object.visible = true;
      }
    this.batches.clear();
    this.dirtyBatches.clear();
    this.entries = [];
  }
}

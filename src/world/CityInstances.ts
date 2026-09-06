import * as THREE from 'three';
import type { SpawnedStaticWorldObject } from './Props';
import { CITY_LOD_DISTANCES } from './CityArchitecture';
interface Part {
  batch: THREE.InstancedMesh;
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
}
/** Batch repeated static architecture while retaining the individual authoring
* objects, colliders and interaction IDs. GM mode restores those originals. */
export class CityInstances {
  private entries: Entry[] = [];
  private batches = new Map<string, THREE.InstancedMesh>();
  private enabled = true;
  private viewFrustum = new THREE.Frustum();
  private projection = new THREE.Matrix4();
  private identity = new THREE.Matrix4();
  private shadowLights: THREE.Light[] = [];
  private dirtyBatches = new Set<THREE.InstancedMesh>();
  constructor(private scene: THREE.Scene, objects: SpawnedStaticWorldObject[]) {
    scene.traverse(node => { if (node instanceof THREE.Light) this.shadowLights.push(node); });
    const eligible = objects.filter(o => o.definition.kind.startsWith('aegis_') && !o.definition.interaction);
    const capacities = new Map<string, number>();
    for (const entry of eligible) {
      entry.object.traverse(node => {
        if (!(node instanceof THREE.Mesh) || Array.isArray(node.material)) return;
        const key = `${node.geometry.uuid}:${node.material.uuid}`;
        capacities.set(key, (capacities.get(key) ?? 0) + 1);
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
          const key = `${node.geometry.uuid}:${node.material.uuid}`;
          let batch = this.batches.get(key);
          if (!batch) {
            // Count mesh occurrences, including repeated parts within one prop.
            batch = new THREE.InstancedMesh(node.geometry, node.material, capacities.get(key)!);
            batch.name = 'aegis-city-instances';
            batch.count = 0;
            batch.visible = false;
            batch.castShadow = node.castShadow;
            batch.receiveShadow = node.receiveShadow;
            batch.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
            this.batches.set(key, batch);
            scene.add(batch);
          }
          result.push({ batch, matrix: node.matrixWorld.clone(), source: node });
        });
        return result;
      });
      if (parts.some(p => p.length))
        this.entries.push({ id: entry.id, object: root, position: root.getWorldPosition(new THREE.Vector3()), levels: parts,
          activeLevel: -2, bounds: new THREE.Box3().setFromObject(root).getBoundingSphere(new THREE.Sphere()), detached: false });
    }
  }
  update(camera: THREE.Camera, enabled: boolean, suppressed: (id: string) => boolean): void {
    this.dirtyBatches.clear();
    if (enabled !== this.enabled) {
      for (const batch of this.batches.values()) this.dirtyBatches.add(batch);
    }
    if (enabled && !this.enabled) {
      for (const entry of this.entries) {
        entry.object.updateMatrixWorld(true);
        entry.object.getWorldPosition(entry.position);
        new THREE.Box3().setFromObject(entry.object).getBoundingSphere(entry.bounds);
        for (const level of entry.levels)
          for (const part of level)
            part.matrix.copy(part.source.matrixWorld);
      }
    }
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
      entry.object.visible = !enabled && !hidden;
      if (enabled && entry.object.parent === this.scene && this.scene.matrixWorld.equals(this.identity)) {
        this.scene.remove(entry.object);
        entry.detached = true;
      } else if (!enabled && entry.detached) {
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
      if (!enabled || hidden || !inView) level = -1;
      if (level !== entry.activeLevel) {
        for (const part of entry.levels[entry.activeLevel] ?? []) this.dirtyBatches.add(part.batch);
        for (const part of entry.levels[level] ?? []) this.dirtyBatches.add(part.batch);
      }
      entry.activeLevel = level;
    }
    // Static transforms only need GPU uploads/bounds rebuilds when membership changes.
    if (!this.dirtyBatches.size) return;
    for (const batch of this.dirtyBatches) {
      batch.count = 0;
      batch.visible = enabled;
    }
    for (const entry of this.entries) {
      if (entry.activeLevel < 0) continue;
      for (const { batch, matrix } of entry.levels[entry.activeLevel]) {
        if (this.dirtyBatches.has(batch)) batch.setMatrixAt(batch.count++, matrix);
      }
    }
    if (enabled)
      for (const batch of this.dirtyBatches) {
        // Zero instances can still incur renderer traversal and draw submission.
        batch.visible = batch.count > 0;
        if (!batch.visible) continue;
        batch.instanceMatrix.needsUpdate = true;
        batch.computeBoundingSphere();
      }
  }
  dispose(): void {
    for (const batch of this.batches.values()) {
      this.scene.remove(batch);
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

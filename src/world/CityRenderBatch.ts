import * as THREE from 'three';

export function cityBatchKey(mesh: THREE.Mesh, cell: string, multiDraw: boolean): string {
  const material = mesh.material as THREE.Material;
  const layout = Object.entries(mesh.geometry.attributes).sort(([a], [b]) => a.localeCompare(b))
    .map(([name, attribute]) => `${name}:${attribute.itemSize}:${attribute.normalized}:${attribute.array.constructor.name}`).join('|');
  return [multiDraw ? layout : mesh.geometry.uuid, material.uuid, cell, !!mesh.geometry.index,
    mesh.castShadow, mesh.receiveShadow, mesh.layers.mask, mesh.renderOrder,
    mesh.customDepthMaterial?.uuid, mesh.customDistanceMaterial?.uuid].join(':');
}

/** Whole roots are accepted or rejected; never detach a partially batched asset. */
export function supportsCityBatch(root: THREE.Object3D): boolean {
  root.updateWorldMatrix(true, true);
  let supported = true, meshes = 0;
  root.traverse(node => {
    if (node.animations.length || (!node.visible && !(node.parent instanceof THREE.LOD))) supported = false;
    if (node instanceof THREE.Mesh) {
      meshes++;
      const material = node.material;
      if (node instanceof THREE.SkinnedMesh || node instanceof THREE.InstancedMesh || node instanceof THREE.BatchedMesh
        || node.morphTargetInfluences?.length || Array.isArray(material) || material.transparent
        || material instanceof THREE.ShaderMaterial
        || Object.values(node.geometry.attributes).some(attribute => attribute instanceof THREE.InterleavedBufferAttribute)
        || node.matrixWorld.determinant() <= 0 || !node.geometry.attributes.position
        || node.geometry.drawRange.start !== 0
        || Number.isFinite(node.geometry.drawRange.count)
        || node.customDepthMaterial || node.customDistanceMaterial
        || node.onBeforeRender !== THREE.Object3D.prototype.onBeforeRender
        || node.onAfterRender !== THREE.Object3D.prototype.onAfterRender
        || node.onBeforeShadow !== THREE.Object3D.prototype.onBeforeShadow
        || node.onAfterShadow !== THREE.Object3D.prototype.onAfterShadow) supported = false;
    } else if (!(node instanceof THREE.Group || node instanceof THREE.LOD || node.type === 'Object3D')) supported = false;
  });
  return supported && meshes > 0;
}

/** Owns only GPU batch buffers; source geometry/material lifetime stays with AssetLoader. */
export class CityRenderBatch {
  readonly object: THREE.InstancedMesh | THREE.BatchedMesh;
  private geometryIds = new Map<THREE.BufferGeometry, number>();
  private matrices: THREE.Matrix4[] = [];
  private active = new Set<number>();
  private nextActive = new Set<number>();
  private count = 0;
  private boundsDirty = true;

  constructor(sources: THREE.Mesh[], multiDraw: boolean) {
    const source = sources[0];
    if (multiDraw) {
      const geometries = [...new Set(sources.map(mesh => mesh.geometry))];
      const vertices = geometries.reduce((sum, geometry) => sum + geometry.attributes.position.count, 0);
      const indices = geometries.reduce((sum, geometry) => sum + (geometry.index?.count ?? 0), 0);
      const batch = new THREE.BatchedMesh(sources.length, vertices, indices, source.material as THREE.Material);
      for (const geometry of geometries) this.geometryIds.set(geometry, batch.addGeometry(geometry));
      batch.perObjectFrustumCulled = true;
      batch.sortObjects = true;
      this.object = batch;
    } else {
      const batch = new THREE.InstancedMesh(source.geometry, source.material, sources.length);
      batch.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      batch.count = 0;
      this.object = batch;
    }
    this.object.name = 'capital-city-instances';
    this.object.visible = false;
    this.object.castShadow = source.castShadow;
    this.object.receiveShadow = source.receiveShadow;
    this.object.layers.mask = source.layers.mask;
    this.object.renderOrder = source.renderOrder;
    this.object.updateMatrix();
    this.object.matrixAutoUpdate = false;
  }

  add(source: THREE.Mesh, matrix: THREE.Matrix4): number {
    if (!(this.object instanceof THREE.BatchedMesh)) return -1;
    const slot = this.object.addInstance(this.geometryIds.get(source.geometry)!);
    this.object.setMatrixAt(slot, matrix);
    this.object.setVisibleAt(slot, false);
    this.matrices[slot] = matrix.clone();
    return slot;
  }

  reset(): void { this.count = 0; this.nextActive.clear(); }

  include(slot: number, matrix: THREE.Matrix4): void {
    this.count++;
    if (this.object instanceof THREE.BatchedMesh) {
      this.nextActive.add(slot);
      if (!this.matrices[slot].equals(matrix)) {
        this.object.setMatrixAt(slot, matrix);
        this.matrices[slot].copy(matrix);
        this.boundsDirty = true;
      }
    } else this.object.setMatrixAt(this.count - 1, matrix);
  }

  commit(enabled: boolean): void {
    this.object.visible = enabled && this.count > 0;
    if (this.object instanceof THREE.BatchedMesh) {
      for (const slot of this.active) if (!this.nextActive.has(slot)) this.object.setVisibleAt(slot, false);
      for (const slot of this.nextActive) if (!this.active.has(slot)) this.object.setVisibleAt(slot, true);
      [this.active, this.nextActive] = [this.nextActive, this.active];
      if (this.boundsDirty) {
        this.object.computeBoundingBox();
        this.object.computeBoundingSphere();
        this.boundsDirty = false;
      }
    } else {
      this.object.count = this.count;
      if (this.object.visible) {
        this.object.instanceMatrix.needsUpdate = true;
        this.object.computeBoundingSphere();
      }
    }
  }

  dispose(): void { this.object.removeFromParent(); this.object.dispose(); this.geometryIds.clear(); this.matrices = []; }
}

import * as THREE from 'three';

interface Part { mesh: THREE.Mesh; matrix: THREE.Matrix4 }
interface Batch { mesh: THREE.InstancedMesh; signature: string }

/** Batches caller-approved static props. The source loader still owns geometry, materials and textures. */
export class StaticPropInstances {
  private batches = new Map<string, Batch>();
  private hiddenRoots = new Map<THREE.Object3D, boolean>();
  constructor(private readonly container: THREE.Object3D) {}

  update(roots: readonly THREE.Object3D[], enabled = true): void {
    this.restoreRoots();
    if (!enabled) { this.clearBatches(); return; }
    this.container.updateWorldMatrix(true, true);
    const inverse = this.container.matrixWorld.clone().invert();
    const grouped = new Map<string, Part[]>();
    for (const root of roots) {
      if (!root.visible) continue;
      const parts: Part[] = [];
      let supported = true;
      const visit = (object: THREE.Object3D) => {
        if (!object.visible) return;
        const mesh = object as THREE.Mesh;
        if (mesh.isMesh) {
          if ((mesh as THREE.SkinnedMesh).isSkinnedMesh || (mesh as THREE.InstancedMesh).isInstancedMesh || mesh.morphTargetInfluences?.length) supported = false;
          const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          if (materials.some(material => material.transparent)) supported = false;
          const matrix = inverse.clone().multiply(mesh.matrixWorld);
          // THREE instancing cannot represent mirrored transforms correctly.
          if (matrix.determinant() <= 0) supported = false;
          parts.push({ mesh, matrix });
        } else if (!(object.type === 'Group' || object.type === 'Object3D' || object.type === 'Scene' || object.type === 'LOD')) supported = false;
        for (const child of object.children) visit(child);
      };
      visit(root);
      if (!supported || !parts.length) continue;
      for (const part of parts) {
        const mesh = part.mesh;
        const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
        const key = [mesh.geometry.uuid, materials.map(material => material.uuid).join(','), mesh.castShadow, mesh.receiveShadow,
          mesh.renderOrder, mesh.layers.mask, mesh.frustumCulled, mesh.customDepthMaterial?.uuid, mesh.customDistanceMaterial?.uuid].join(':');
        const group = grouped.get(key);
        if (group) group.push(part); else grouped.set(key, [part]);
      }
      this.hiddenRoots.set(root, root.visible);
      root.visible = false;
    }
    for (const [key, batch] of this.batches) if (!grouped.has(key)) {
      batch.mesh.removeFromParent(); batch.mesh.dispose(); this.batches.delete(key);
    }
    for (const [key, parts] of grouped) {
      const signature = parts.map(part => `${part.mesh.uuid}:${part.matrix.elements.join(',')}`).join('|');
      let batch = this.batches.get(key);
      if (batch?.signature === signature) continue;
      if (!batch || batch.mesh.instanceMatrix.count < parts.length) {
        if (batch) { batch.mesh.removeFromParent(); batch.mesh.dispose(); }
        const source = parts[0].mesh;
        const mesh = new THREE.InstancedMesh(source.geometry, source.material, parts.length);
        mesh.name = 'approved-static-prop-instances';
        mesh.castShadow = source.castShadow; mesh.receiveShadow = source.receiveShadow;
        mesh.renderOrder = source.renderOrder; mesh.layers.mask = source.layers.mask; mesh.frustumCulled = source.frustumCulled;
        mesh.customDepthMaterial = source.customDepthMaterial; mesh.customDistanceMaterial = source.customDistanceMaterial;
        mesh.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
        batch = { mesh, signature };
        this.batches.set(key, batch); this.container.add(mesh);
      }
      batch.mesh.count = parts.length;
      parts.forEach((part, index) => batch!.mesh.setMatrixAt(index, part.matrix));
      batch.mesh.instanceMatrix.needsUpdate = true;
      batch.mesh.computeBoundingBox(); batch.mesh.computeBoundingSphere();
      batch.signature = signature;
    }
  }

  private restoreRoots(): void {
    for (const [root, visible] of this.hiddenRoots) root.visible = visible;
    this.hiddenRoots.clear();
  }
  private clearBatches(): void {
    for (const batch of this.batches.values()) { batch.mesh.removeFromParent(); batch.mesh.dispose(); }
    this.batches.clear();
  }
  dispose(): void { this.restoreRoots(); this.clearBatches(); }
}

import * as THREE from 'three';

/** Static service NPCs keep animation-safe meshes; cull their entire rig using a
 * generous whole-character envelope instead of unsafe per-skinned-mesh bounds. */
export class CharacterVisibility {
  private entries: { object: THREE.Object3D; sphere: THREE.Sphere; meshes: {
    mesh: THREE.Mesh & { boundingSphere?: THREE.Sphere | null };
    bounds: THREE.Sphere | null | undefined; culled: boolean; hadBounds: boolean;
  }[] }[];
  private projection = new THREE.Matrix4();
  private inverse = new THREE.Matrix4();
  private frustum = new THREE.Frustum();
  private lights: THREE.Light[] = [];

  constructor(scene: THREE.Scene, objects: readonly THREE.Object3D[]) {
    scene.traverse(node => { if (node instanceof THREE.Light) this.lights.push(node); });
    this.entries = objects.map(object => {
      object.updateWorldMatrix(true, true);
      const sphere = new THREE.Box3().setFromObject(object).getBoundingSphere(new THREE.Sphere());
      // Service NPCs idle in place. Leave a full body diameter around the bind
      // envelope for articulated arms, weapons, and the authored idle sway.
      sphere.radius = Math.max(4, sphere.radius * 3);
      const meshes: CharacterVisibility['entries'][number]['meshes'] = [];
      object.traverse(node => {
        if (!(node instanceof THREE.Mesh)) return;
        const mesh = node as THREE.Mesh & { boundingSphere?: THREE.Sphere | null };
        meshes.push({ mesh, bounds: mesh.boundingSphere, culled: mesh.frustumCulled,
          hadBounds: Object.prototype.hasOwnProperty.call(mesh, 'boundingSphere') });
        // Three's frustum test prefers object-owned bounds, including on ordinary
        // Meshes. Never replace a shared geometry's bounds with character bounds.
        mesh.boundingSphere = sphere.clone().applyMatrix4(this.inverse.copy(mesh.matrixWorld).invert());
        mesh.frustumCulled = true;
      });
      return { object, sphere, meshes };
    });
  }

  update(camera: THREE.Camera): void {
    camera.updateWorldMatrix(true, false);
    this.frustum.setFromProjectionMatrix(this.projection.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse));
    const shadows: THREE.Frustum[] = [];
    let uncullable = false;
    for (const light of this.lights) {
      if (!light.castShadow) continue;
      if (light instanceof THREE.PointLight) uncullable = true;
      if (light instanceof THREE.DirectionalLight || light instanceof THREE.SpotLight) {
        light.updateWorldMatrix(true, false); light.target.updateWorldMatrix(true, false);
        light.shadow.updateMatrices(light); shadows.push(light.shadow.getFrustum());
      }
    }
    for (const entry of this.entries) {
      entry.object.visible = uncullable || this.frustum.intersectsSphere(entry.sphere)
        || shadows.some(frustum => frustum.intersectsSphere(entry.sphere));
      if (!entry.object.visible) continue;
      entry.object.updateWorldMatrix(true, true);
      // Each pass now applies the same animation-safe envelope independently:
      // retaining a rig for its shadow no longer submits it to the main camera.
      for (const { mesh } of entry.meshes) mesh.boundingSphere!.copy(entry.sphere)
        .applyMatrix4(this.inverse.copy(mesh.matrixWorld).invert());
    }
  }

  dispose(): void {
    for (const { object, meshes } of this.entries) {
      object.visible = true;
      for (const { mesh, bounds, culled, hadBounds } of meshes) {
        mesh.frustumCulled = culled;
        if (hadBounds) mesh.boundingSphere = bounds;
        else delete mesh.boundingSphere;
      }
    }
    this.entries = []; this.lights = [];
  }
}

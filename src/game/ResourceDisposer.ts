import * as THREE from 'three';

/** Terminal cleanup for a scene and its loader, which share GPU resources. */
export class ResourceDisposer {
  private disposed = new WeakSet<object>();

  resource(value: { dispose(): void }): void {
    if (this.disposed.has(value)) return;
    this.disposed.add(value);
    value.dispose();
  }

  texture(texture: THREE.Texture): void {
    this.resource(texture);
    const image: unknown = texture.source.data;
    if (image && typeof image === 'object' && !this.disposed.has(image)
      && 'close' in image && typeof image.close === 'function') {
      this.disposed.add(image);
      image.close();
    }
  }

  object(root: THREE.Object3D): void {
    root.traverse(node => {
      const mesh = node as THREE.Mesh;
      if (mesh.geometry) this.resource(mesh.geometry);
      if (mesh.material) {
        for (const material of Array.isArray(mesh.material) ? mesh.material : [mesh.material]) {
          for (const value of Object.values(material)) {
            if (value instanceof THREE.Texture) this.texture(value);
          }
          if (material instanceof THREE.ShaderMaterial) {
            for (const uniform of Object.values(material.uniforms)) {
              const values: unknown[] = Array.isArray(uniform.value) ? uniform.value : [uniform.value];
              for (const value of values) if (value instanceof THREE.Texture) this.texture(value);
            }
          }
          this.resource(material);
        }
      }
      if (node instanceof THREE.SkinnedMesh) this.resource(node.skeleton);
      if (node instanceof THREE.InstancedMesh) this.resource(node);
      if (node instanceof THREE.Light && 'shadow' in node) {
        const shadow = node.shadow as THREE.LightShadow | undefined;
        if (shadow) this.resource(shadow);
      }
    });
    if (root instanceof THREE.Scene) {
      if (root.background instanceof THREE.Texture) this.texture(root.background);
      if (root.environment) this.texture(root.environment);
      root.background = null;
      root.environment = null;
    }
  }
}

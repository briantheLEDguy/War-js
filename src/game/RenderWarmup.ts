import * as THREE from 'three';

async function compileScene(renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera,
  cancelled: () => boolean): Promise<void> {
  const materials = renderer.compile(scene, camera);
  // r167's compileAsync keeps polling disposed material properties after a zone
  // departure. Use the same readiness query, checking cancellation before every
  // poll. Missing readiness support falls back to the offscreen warmup draw.
  while (!cancelled()) {
    let pending = false;
    for (const material of materials) {
      const program = renderer.properties.get(material).currentProgram as { isReady?(): boolean } | undefined;
      if (program?.isReady && !program.isReady()) pending = true;
    }
    if (!pending) return;
    await new Promise(resolve => setTimeout(resolve, 10));
  }
}

/** Upload once while loading; one offscreen draw also initializes shadow programs.
 * Room light configurations are compiled before the player first enters them. */
export async function warmScene(
  renderer: THREE.WebGLRenderer, scene: THREE.Scene, camera: THREE.Camera,
  cancelled: () => boolean, rooms: readonly THREE.Object3D[] = [],
): Promise<void> {
  const textures = new Set<THREE.Texture>();
  scene.traverse(object => {
    const mesh = object as THREE.Mesh;
    for (const material of Array.isArray(mesh.material) ? mesh.material : mesh.material ? [mesh.material] : []) {
      for (const value of Object.values(material)) if (value instanceof THREE.Texture) textures.add(value);
      if (material instanceof THREE.ShaderMaterial) {
        for (const { value } of Object.values(material.uniforms)) if (value instanceof THREE.Texture) textures.add(value);
      }
    }
  });
  let count = 0;
  for (const texture of textures) {
    if (cancelled()) return;
    // Environment/render target textures are already uploaded by their owner.
    if (!texture.isRenderTargetTexture && texture.image) renderer.initTexture(texture);
    if (++count % 8 === 0) await new Promise(resolve => setTimeout(resolve, 0));
  }
  const target = new THREE.WebGLRenderTarget(8, 8);
  const previous = renderer.getRenderTarget();
  try {
    for (const room of [null, ...rooms]) {
      if (cancelled()) return;
      const visible = room?.visible;
      try {
        if (room) room.visible = true;
        const view = room ? camera.clone() : camera;
        if (room) {
          room.getWorldPosition(view.position);
          view.position.add(new THREE.Vector3(0, 2, 4));
          view.lookAt(view.position.clone().add(new THREE.Vector3(0, 0, -4)));
          view.updateMatrixWorld(true);
        }
        await compileScene(renderer, scene, view, cancelled);
        if (cancelled()) return;
        renderer.setRenderTarget(target);
        renderer.render(scene, view);
      } finally {
        if (room) room.visible = visible!;
      }
    }
  } finally {
    if (!cancelled()) renderer.setRenderTarget(previous);
    target.dispose();
  }
}

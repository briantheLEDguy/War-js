import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';

/** Supplies neutral PBR reflections without replacing the themed preview backdrop. */
export function setupPreviewReflections(scene: THREE.Scene, renderer: THREE.WebGLRenderer): () => void {
  const environment = new RoomEnvironment();
  const pmrem = new THREE.PMREMGenerator(renderer);
  let target: THREE.WebGLRenderTarget;
  try {
    target = pmrem.fromScene(environment, 0.04);
  } finally {
    environment.dispose();
    pmrem.dispose();
  }
  scene.environment = target.texture;

  let disposed = false;
  return () => {
    if (disposed) return;
    disposed = true;
    if (scene.environment === target.texture) scene.environment = null;
    target.dispose();
  };
}

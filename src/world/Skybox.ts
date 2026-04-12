import * as THREE from 'three';
import type { AssetLoader } from '../game/AssetLoader';

/**
 * Skybox + scene lighting. Uses HDRI environment if available, otherwise
 * a gradient sky + sun+ambient lights. Returns the objects the caller should
 * add to the scene.
 */
export async function setupSky(
  scene: THREE.Scene,
  loader: AssetLoader,
  hdriPath?: string,
): Promise<{ sun: THREE.DirectionalLight }> {
  // Gradient sky fallback via a large inverted sphere.
  const geo = new THREE.SphereGeometry(500, 32, 32);
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      topColor: { value: new THREE.Color(0x6a8ec9) },
      bottomColor: { value: new THREE.Color(0xe6c892) },
      offset: { value: 33 },
      exponent: { value: 0.6 },
    },
    vertexShader: `
      varying vec3 vWorldPosition;
      void main() {
        vec4 p = modelMatrix * vec4(position, 1.0);
        vWorldPosition = p.xyz;
        gl_Position = projectionMatrix * viewMatrix * p;
      }`,
    fragmentShader: `
      uniform vec3 topColor;
      uniform vec3 bottomColor;
      uniform float offset;
      uniform float exponent;
      varying vec3 vWorldPosition;
      void main() {
        float h = normalize(vWorldPosition + vec3(0.0, offset, 0.0)).y;
        gl_FragColor = vec4(mix(bottomColor, topColor, max(pow(max(h, 0.0), exponent), 0.0)), 1.0);
      }`,
    side: THREE.BackSide,
  });
  const skyMesh = new THREE.Mesh(geo, mat);
  scene.add(skyMesh);

  if (hdriPath) {
    const tex = await loader.loadHDRI(hdriPath);
    if (tex) {
      scene.environment = tex;
    }
  }

  scene.fog = new THREE.Fog(0xbfc8d4, 60, 220);

  const ambient = new THREE.AmbientLight(0xffffff, 0.35);
  scene.add(ambient);
  const sun = new THREE.DirectionalLight(0xfff2d1, 1.1);
  sun.position.set(40, 60, 25);
  sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  sun.shadow.camera.left = -60;
  sun.shadow.camera.right = 60;
  sun.shadow.camera.top = 60;
  sun.shadow.camera.bottom = -60;
  sun.shadow.camera.near = 0.5;
  sun.shadow.camera.far = 200;
  sun.shadow.bias = -0.0005;
  scene.add(sun);

  return { sun };
}

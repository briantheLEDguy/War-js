import * as THREE from 'three';
import type { AssetLoader } from '../game/AssetLoader';

/**
 * Skybox + scene lighting. Uses HDRI environment if available, otherwise
 * a gradient sky + sun+ambient lights. Dark fantasy atmosphere inspired
 * by Warhammer's grim, war-torn aesthetic.
 */
export async function setupSky(
  scene: THREE.Scene,
  loader: AssetLoader,
  renderer: THREE.WebGLRenderer,
  hdriPath?: string,
): Promise<{ sun: THREE.DirectionalLight }> {
  // Gradient sky fallback via a large inverted sphere.
  // Dark, brooding sky with stormy undertones.
  const geo = new THREE.SphereGeometry(500, 32, 32);
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      topColor:     { value: new THREE.Color(0x2c3f5c) },
      midColor:     { value: new THREE.Color(0x4a5a6a) },
      bottomColor:  { value: new THREE.Color(0x8a7a60) },
      horizonColor: { value: new THREE.Color(0xc49a50) },
      offset:       { value: 33 },
      exponent:     { value: 0.5 },
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
      uniform vec3 midColor;
      uniform vec3 bottomColor;
      uniform vec3 horizonColor;
      uniform float offset;
      uniform float exponent;
      varying vec3 vWorldPosition;
      void main() {
        float h = normalize(vWorldPosition + vec3(0.0, offset, 0.0)).y;
        float hClamped = max(h, 0.0);
        // Multi-stop gradient: bottom -> horizon -> mid -> top
        // Initialize color to avoid undefined-variable warnings on strict GLSL compilers
        vec3 color = bottomColor;
        if (hClamped < 0.15) {
          color = mix(bottomColor, horizonColor, hClamped / 0.15);
        } else if (hClamped < 0.4) {
          color = mix(horizonColor, midColor, (hClamped - 0.15) / 0.25);
        } else {
          color = mix(midColor, topColor, pow((hClamped - 0.4) / 0.6, exponent));
        }
        gl_FragColor = vec4(color, 1.0);
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

  // If no HDRI was supplied (or the asset was missing), bake the procedural
  // gradient sky into a PMREM environment map. Without this, PBR materials
  // with high metalness (gold 0.95, steel 0.85) have nothing to reflect and
  // render nearly black everywhere except where direct sunlight hits.
  if (!scene.environment) {
    const pmrem = new THREE.PMREMGenerator(renderer);
    pmrem.compileEquirectangularShader();
    // Render the sky mesh into a tiny scene and generate the env map from it.
    const envScene = new THREE.Scene();
    const envSky = new THREE.Mesh(geo.clone(), mat.clone());
    envScene.add(envSky);
    scene.environment = pmrem.fromScene(envScene, 0.04).texture;
    pmrem.dispose();
  }

  // Atmospheric fog — slightly warm, hazy
  scene.fog = new THREE.Fog(0x8a7a60, 50, 200);

  // Warm ambient for the grim look
  const ambient = new THREE.AmbientLight(0xc8b090, 0.75);
  scene.add(ambient);

  // Hemisphere light for better outdoor fill
  const hemi = new THREE.HemisphereLight(0x6a8ec9, 0x4a3a20, 0.45);
  scene.add(hemi);

  // Sun — warm, slightly orange directional light
  const sun = new THREE.DirectionalLight(0xffe0b0, 1.8);
  sun.position.set(40, 55, 30);
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

  // Secondary fill light from opposite side — bumped so the side of the
  // character that isn't catching direct sun still reads as armored plate
  // rather than a flat black silhouette.
  const fill = new THREE.DirectionalLight(0x8090c0, 0.35);
  fill.position.set(-30, 20, -25);
  scene.add(fill);

  return { sun };
}

import * as THREE from 'three';

/** Large world-space stains cross individual mesh/tile boundaries. Instanced
 * copies sample their own location, so batching does not repeat the weathering. */
export function applyCityWeathering(material: THREE.MeshStandardMaterial): void {
  if (material.userData.aegisWeathering) return;
  material.userData.aegisWeathering = true;
  material.onBeforeCompile = shader => {
    shader.vertexShader = shader.vertexShader
      .replace('#include <common>', '#include <common>\nvarying vec3 vCityPosition;')
      .replace('#include <project_vertex>', `#include <project_vertex>
        vec4 cityPosition = vec4(transformed, 1.0);
        #ifdef USE_INSTANCING
          cityPosition = instanceMatrix * cityPosition;
        #endif
        vCityPosition = (modelMatrix * cityPosition).xyz;
      `);
    shader.fragmentShader = shader.fragmentShader
      .replace('#include <common>', `#include <common>
        varying vec3 vCityPosition;
        float cityHash(vec2 p) {
          vec3 p3 = fract(vec3(p.xyx) * .1031);
          p3 += dot(p3, p3.yzx + 33.33);
          return fract((p3.x + p3.y) * p3.z);
        }
        float cityNoise(vec2 p) {
          vec2 cell = floor(p), f = fract(p);
          f = f * f * (3.0 - 2.0 * f);
          return mix(mix(cityHash(cell), cityHash(cell + vec2(1,0)), f.x),
                     mix(cityHash(cell + vec2(0,1)), cityHash(cell + vec2(1,1)), f.x), f.y);
        }
      `)
      .replace('#include <color_fragment>', `#include <color_fragment>
        vec2 cityXZ = vCityPosition.xz + vec2(vCityPosition.y * .37, vCityPosition.y * .19);
        float age = .55 * cityNoise(cityXZ * .075) + .3 * cityNoise(cityXZ * .27) + .15 * cityNoise(cityXZ * .83);
        vec3 weather = mix(vec3(.68,.74,.68), vec3(1.08,1.025,.94), smoothstep(.15,.85,age));
        diffuseColor.rgb *= weather;
      `);
  };
  material.customProgramCacheKey = () => 'aegis-world-weathering-v1';
  material.needsUpdate = true;
}

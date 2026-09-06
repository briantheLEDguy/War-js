import { readFileSync } from 'node:fs';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { describe, expect, test } from 'vitest';
import { CIVIC_WALK_DURATION, CIVIC_WALK_SPEED, createCivicWalkClip } from '../src/world/CivicLocomotion';

/** Use the shipped mesh, skin and rig, omitting only image/material loading in Node. */
async function loadCivicModel(variant: string) {
  const bytes = readFileSync(`public/assets/models/chr_aegis_people_${variant}_walk.glb`);
  const jsonLength = bytes.readUInt32LE(12);
  const gltf = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength));
  delete gltf.images; delete gltf.textures; delete gltf.materials;
  for (const mesh of gltf.meshes) for (const primitive of mesh.primitives) delete primitive.material;
  const json = Buffer.from(JSON.stringify(gltf));
  const padded = Buffer.alloc(Math.ceil(json.length / 4) * 4, 0x20); json.copy(padded);
  const bin = bytes.subarray(20 + jsonLength);
  const header = Buffer.alloc(20);
  header.write('glTF'); header.writeUInt32LE(2, 4); header.writeUInt32LE(20 + padded.length + bin.length, 8);
  header.writeUInt32LE(padded.length, 12); header.writeUInt32LE(0x4e4f534a, 16);
  const rebuilt = Buffer.concat([header, padded, bin]);
  return new GLTFLoader().parseAsync(rebuilt.buffer.slice(rebuilt.byteOffset, rebuilt.byteOffset + rebuilt.byteLength), '');
}

describe('reviewed civic rig locomotion', () => {
  test.each(['civilian_male', 'civilian_female'])('%s walks on its own bind axes with planted feet and actual skin deformation', async variant => {
    const { scene, animations } = await loadCivicModel(variant);
    const bones: THREE.Bone[] = [];
    const meshes: THREE.SkinnedMesh[] = [];
    let mesh!: THREE.SkinnedMesh;
    scene.traverse(node => {
      if (node instanceof THREE.Bone) bones.push(node);
      if (node instanceof THREE.SkinnedMesh) meshes.push(node);
    });
    const initial = bones.map(bone => bone.quaternion.clone());
    const baked = createCivicWalkClip(scene)!;
    expect(baked).toBeInstanceOf(THREE.AnimationClip);
    const clip = animations.find(animation => animation.name === 'walk')!;
    expect(clip).toBeInstanceOf(THREE.AnimationClip);
    expect(clip.duration).toBeCloseTo(CIVIC_WALK_DURATION);
    expect(clip.tracks.every(track => bones.some(bone => track.name.startsWith(`${bone.name}.`)))).toBe(true);
    bones.forEach((bone, i) => expect(bone.quaternion.toArray()).toEqual(initial[i].toArray()));
    const foot = scene.getObjectByName('foot_L')!;
    const restFoot = foot.getWorldPosition(new THREE.Vector3());
    let vertex = -1, lowest = Infinity;
    for (const candidate of meshes) {
      const footIndex = candidate.skeleton.bones.findIndex(bone => bone.name === 'foot_L');
      const indices = candidate.geometry.getAttribute('skinIndex'), weights = candidate.geometry.getAttribute('skinWeight');
      const position = candidate.geometry.getAttribute('position');
      for (let i = 0; i < position.count; i++) for (let component = 0; component < 4; component++) {
        if (indices.getComponent(i, component) === footIndex && weights.getComponent(i, component) > .999 && position.getY(i) < lowest) {
          lowest = position.getY(i); vertex = i; mesh = candidate;
        }
      }
    }
    expect(vertex).toBeGreaterThanOrEqual(0);
    const position = mesh.geometry.getAttribute('position');
    const skinPoint = () => mesh.applyBoneTransform(vertex, new THREE.Vector3().fromBufferAttribute(position, vertex)).applyMatrix4(mesh.matrixWorld);
    const restVertex = skinPoint();
    const mixer = new THREE.AnimationMixer(scene); mixer.clipAction(clip).play();
    const contact: THREE.Vector3[] = [], deformed: THREE.Vector3[] = [];
    for (const phase of [.1, .2, .3, .4, .5]) {
      const time = phase * CIVIC_WALK_DURATION;
      mixer.setTime(time);
      scene.position.z = time * CIVIC_WALK_SPEED;
      scene.updateMatrixWorld(true);
      contact.push(foot.getWorldPosition(new THREE.Vector3()));
      deformed.push(skinPoint());
    }
    // Both the foot joint and a fully weighted boot vertex stay planted as the body advances.
    for (const points of [contact, deformed]) {
      expect(Math.max(...points.map(point => point.z)) - Math.min(...points.map(point => point.z))).toBeLessThan(.01);
      expect(Math.max(...points.map(point => point.y)) - Math.min(...points.map(point => point.y))).toBeLessThan(.01);
    }
    expect(Math.abs(contact[0].y - restFoot.y)).toBeLessThan(.01);
    expect(deformed[0].distanceTo(restVertex)).toBeGreaterThan(.15);
    mixer.setTime(CIVIC_WALK_DURATION * .8); scene.updateMatrixWorld(true);
    expect(foot.getWorldPosition(new THREE.Vector3()).y - restFoot.y).toBeGreaterThan(.05);
    if (variant === 'civilian_female') {
      for (const phase of [.1, .4, .8]) {
        mixer.setTime(CIVIC_WALK_DURATION * phase); scene.updateMatrixWorld(true);
        for (const candidate of meshes) {
          const original = candidate.geometry.getAttribute('position'), indices = candidate.geometry.index!;
          const deformed = Array.from({ length: original.count }, (_, i) => candidate.applyBoneTransform(i, new THREE.Vector3().fromBufferAttribute(original, i)));
          expect(Math.min(...deformed.map(point => point.y))).toBeGreaterThan(-.015);
          for (let i = 0; i < indices.count; i += 3) for (const [a, b] of [[0, 1], [1, 2], [2, 0]]) {
            const v1 = indices.getX(i + a), v2 = indices.getX(i + b);
            const y1 = original.getY(v1), y2 = original.getY(v2);
            if (Math.min(y1, y2) < .28 || Math.max(y1, y2) > .8) continue;
            const length = new THREE.Vector3().fromBufferAttribute(original, v1).distanceTo(new THREE.Vector3().fromBufferAttribute(original, v2));
            // Continuous garment weights avoid the torn panels caused by sharp radial thresholds.
            if (length > .005) expect(deformed[v1].distanceTo(deformed[v2]) / length).toBeLessThan(3);
          }
        }
      }
    }
    mixer.stopAllAction(); mixer.uncacheRoot(scene);
    for (const candidate of meshes) { candidate.geometry.dispose(); (candidate.material as THREE.Material).dispose(); candidate.skeleton.dispose(); }
  });

  test('does not manufacture incompatible tracks for a missing or unrelated rig', () => {
    expect(createCivicWalkClip(new THREE.Group())).toBeNull();
  });

  test.each(['civilian_male', 'civilian_female'])('%s retains the reviewed source geometry, materials, textures, skeleton and idle clip', variant => {
    const parse = (path: string) => {
      const bytes = readFileSync(path), length = bytes.readUInt32LE(12);
      return { json: JSON.parse(bytes.toString('utf8', 20, 20 + length)), binary: bytes.subarray(28 + length) };
    };
    const source = parse(`public/assets/models/chr_aegis_people_${variant}_lod1.glb`);
    const result = parse(`public/assets/models/chr_aegis_people_${variant}_walk.glb`);
    for (const field of ['nodes', 'skins', 'meshes', 'materials', 'images', 'textures']) expect(result.json[field]).toEqual(source.json[field]);
    expect(result.json.animations[0]).toEqual(source.json.animations[0]);
    const edited = new Set(source.json.meshes.flatMap((mesh: { primitives: Array<{ attributes: Record<string, number> }> }) => mesh.primitives.flatMap(p =>
      ['JOINTS_0', 'WEIGHTS_0'].map(name => source.json.accessors[p.attributes[name]].bufferView))));
    source.json.bufferViews.forEach((view: { byteOffset?: number; byteLength: number }, index: number) => {
      if (edited.has(index)) return;
      const start = view.byteOffset ?? 0;
      expect(result.binary.subarray(start, start + view.byteLength).equals(source.binary.subarray(start, start + view.byteLength))).toBe(true);
    });
  });
});

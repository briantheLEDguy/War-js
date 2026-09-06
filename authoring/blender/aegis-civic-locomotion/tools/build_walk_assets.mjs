import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';
import ts from 'typescript';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

const ROOT = fileURLToPath(new URL('../../../../', import.meta.url));
const require = createRequire(import.meta.url);
let validator;
try { validator = require('gltf-validator'); }
catch (error) {
  if (error.code !== 'MODULE_NOT_FOUND') throw error;
  validator = require(path.join(ROOT, 'authoring/blender/aegis-city/.deps/node_modules/gltf-validator'));
}
const WORK = path.join(ROOT, 'authoring/blender/aegis-civic-locomotion');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const sourceCode = fs.readFileSync(path.join(ROOT, 'src/world/CivicLocomotion.ts'), 'utf8');
const compiled = ts.transpileModule(sourceCode, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022 } }).outputText
  .replace("from 'three'", `from ${JSON.stringify(import.meta.resolve('three'))}`);
const { createCivicWalkClip } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
for (const folder of ['runtime', 'review']) fs.mkdirSync(path.join(WORK, folder), { recursive: true });
const encode = (gltf, binary) => {
  const json = Buffer.from(JSON.stringify(gltf)), padded = Buffer.alloc(Math.ceil(json.length / 4) * 4, 0x20);
  json.copy(padded);
  const bin = Buffer.alloc(Math.ceil(binary.length / 4) * 4); binary.copy(bin);
  const header = Buffer.alloc(20); header.write('glTF'); header.writeUInt32LE(2, 4);
  header.writeUInt32LE(28 + padded.length + bin.length, 8); header.writeUInt32LE(padded.length, 12); header.writeUInt32LE(0x4e4f534a, 16);
  const binHeader = Buffer.alloc(8); binHeader.writeUInt32LE(bin.length); binHeader.writeUInt32LE(0x004e4942, 4);
  return Buffer.concat([header, padded, binHeader, bin]);
};
const reports = [];
for (const variant of ['civilian_male', 'civilian_female']) {
  const source = `chr_aegis_people_${variant}_lod1.glb`, model = `chr_aegis_people_${variant}_walk.glb`;
  const bytes = fs.readFileSync(path.join(ROOT, 'public/assets/models', source));
  const jsonLength = bytes.readUInt32LE(12), gltf = JSON.parse(bytes.toString('utf8', 20, 20 + jsonLength));
  let bin = Buffer.from(bytes.subarray(28 + jsonLength));
  const originalBin = Buffer.from(bin);
  const access = (index, vertex, channel, value) => {
    const a = gltf.accessors[index], v = gltf.bufferViews[a.bufferView], size = a.type === 'SCALAR' ? 1 : a.type === 'VEC3' ? 3 : 4;
    const unit = a.componentType === 5126 || a.componentType === 5125 ? 4 : a.componentType === 5123 ? 2 : 1;
    const offset = (v.byteOffset ?? 0) + (a.byteOffset ?? 0) + vertex * (v.byteStride ?? size * unit) + channel * unit;
    if (value !== undefined) { if (unit === 4) bin.writeFloatLE(value, offset); else if (unit === 2) bin.writeUInt16LE(value, offset); else bin[offset] = value; }
    return a.componentType === 5126 ? bin.readFloatLE(offset) : unit === 4 ? bin.readUInt32LE(offset) : unit === 2 ? bin.readUInt16LE(offset) : bin[offset];
  };
  const joints = gltf.skins[0].joints.map(index => gltf.nodes[index].name);
  const joint = name => joints.indexOf(name);
  const smooth = (low, high, value) => { const t = Math.max(0, Math.min(1, (value - low) / (high - low))); return t * t * (3 - 2 * t); };
  let repaired = 0;
  const changedViews = new Set();
  for (const mesh of gltf.meshes) for (const primitive of mesh.primitives) {
    const attributes = primitive.attributes, count = gltf.accessors[attributes.POSITION].count;
    const parent = Array.from({ length: count }, (_, i) => i), welds = new Map();
    const find = v => parent[v] === v ? v : (parent[v] = find(parent[v]));
    const union = (a, b) => { parent[find(a)] = find(b); };
    for (let v = 0; v < count; v++) {
      const key = [0, 1, 2].map(k => Math.round(access(attributes.POSITION, v, k) * 1e5)).join(',');
      if (welds.has(key)) union(v, welds.get(key)); else welds.set(key, v);
    }
    for (let i = 0; i < gltf.accessors[primitive.indices].count; i += 3) {
      union(access(primitive.indices, i, 0), access(primitive.indices, i + 1, 0));
      union(access(primitive.indices, i, 0), access(primitive.indices, i + 2, 0));
    }
    const parts = new Map();
    for (let v = 0; v < count; v++) {
      const id = find(v), part = parts.get(id) ?? { min: [Infinity, Infinity, Infinity], max: [-Infinity, -Infinity, -Infinity], count: 0 };
      for (let k = 0; k < 3; k++) { part.min[k] = Math.min(part.min[k], access(attributes.POSITION, v, k)); part.max[k] = Math.max(part.max[k], access(attributes.POSITION, v, k)); }
      part.count++; parts.set(id, part);
    }
    for (let vertex = 0; vertex < count; vertex++) {
      let hipsWeight = 0;
      for (let k = 0; k < 4; k++) if (access(attributes.JOINTS_0, vertex, k) === joint('hips')) hipsWeight += access(attributes.WEIGHTS_0, vertex, k);
      const x = access(attributes.POSITION, vertex, 0), y = access(attributes.POSITION, vertex, 1);
      if (hipsWeight < .95 || y >= .98) continue;
      const hip = smooth(.80, .98, y), thigh = smooth(.45, .64, y), foot = 1 - smooth(.16, .27, y);
      const left = smooth(-.045, .045, x);
      const part = parts.get(find(vertex));
      // A connected skirt/apron (including separate sewn trim) must share one continuous
      // weight field. Radial vertex thresholds tear folds when adjacent faces bend apart.
      const robe = variant === 'civilian_female' && part.min[1] < .8
        && (part.max[1] > .3 || part.max[0] - part.min[0] > .3);
      const robeSwing = .9 * (1 - smooth(.12, .95, y));
      const influences = new Map([[joint('hips'), robe ? 1 - robeSwing : hip]]);
      for (const [side, blend] of [['L', left], ['R', 1 - left]]) {
        const amount = (robe ? (side === 'L' ? smooth(-.13, .13, x) : 1 - smooth(-.13, .13, x)) : blend) * (robe ? robeSwing : 1 - hip);
        influences.set(joint(`thigh_${side}`), robe ? 0 : amount * thigh);
        influences.set(joint(`shin_${side}`), robe ? 0 : amount * (1 - thigh) * (1 - foot));
        influences.set(joint(`foot_${side}`), robe ? amount : amount * (1 - thigh) * foot);
      }
      const strongest = [...influences].filter(([, weight]) => weight > 0).sort((a, b) => b[1] - a[1]).slice(0, 4);
      const total = strongest.reduce((sum, [, weight]) => sum + weight, 0);
      for (let k = 0; k < 4; k++) {
        access(attributes.JOINTS_0, vertex, k, strongest[k]?.[0] ?? 0);
        access(attributes.WEIGHTS_0, vertex, k, (strongest[k]?.[1] ?? 0) / total);
      }
      changedViews.add(gltf.accessors[attributes.JOINTS_0].bufferView); changedViews.add(gltf.accessors[attributes.WEIGHTS_0].bufferView);
      repaired++;
    }
  }
  const preservedViews = gltf.bufferViews.map((view, index) => {
    if (changedViews.has(index)) return null;
    const start = view.byteOffset ?? 0, end = start + view.byteLength;
    if (!bin.subarray(start, end).equals(originalBin.subarray(start, end))) throw new Error(`Unexpected channel edit: ${variant}/${index}`);
    return { index, sha256: hash(originalBin.subarray(start, end)) };
  }).filter(Boolean);
  // Headless animation bake reads the actual repaired skin; all appearance bytes remain untouched.
  const headless = structuredClone(gltf); delete headless.materials; delete headless.images; delete headless.textures;
  for (const mesh of headless.meshes) for (const primitive of mesh.primitives) delete primitive.material;
  const packed = encode(headless, bin);
  const { scene } = await new GLTFLoader().parseAsync(packed.buffer.slice(packed.byteOffset, packed.byteOffset + packed.byteLength), '');
  const clip = createCivicWalkClip(scene);
  if (!clip) throw new Error(`No valid weighted civic gait for ${variant}`);
  const appendAccessor = (array, type) => {
    const data = Buffer.from(array.buffer, array.byteOffset, array.byteLength);
    const offset = bin.length, padded = Buffer.alloc(Math.ceil(data.length / 4) * 4); data.copy(padded);
    bin = Buffer.concat([bin, padded]);
    const bufferView = gltf.bufferViews.push({ buffer: 0, byteOffset: offset, byteLength: data.length }) - 1;
    return gltf.accessors.push({ bufferView, componentType: 5126, count: array.length / (type === 'VEC4' ? 4 : type === 'VEC3' ? 3 : 1), type,
      ...(type === 'SCALAR' ? { min: [array[0]], max: [array[array.length - 1]] } : {}) }) - 1;
  };
  const animation = { name: 'walk', samplers: [], channels: [] };
  for (const track of clip.tracks) {
    const [name, property] = track.name.split('.');
    const node = gltf.nodes.findIndex(node => node.name === name), targetPath = property === 'quaternion' ? 'rotation' : property === 'position' ? 'translation' : property;
    animation.channels.push({ sampler: animation.samplers.length, target: { node, path: targetPath } });
    animation.samplers.push({ input: appendAccessor(track.times, 'SCALAR'), output: appendAccessor(track.values, property === 'quaternion' ? 'VEC4' : 'VEC3'), interpolation: 'LINEAR' });
  }
  gltf.animations.push(animation); gltf.buffers[0].byteLength = bin.length;
  const output = encode(gltf, bin);
  const validation = await validator.validateBytes(new Uint8Array(output), { maxIssues: 100 });
  if (validation.issues.numErrors) throw new Error(JSON.stringify(validation.issues));
  fs.writeFileSync(path.join(WORK, 'runtime', model), output);
  const weightedBones = new Set();
  for (const mesh of gltf.meshes) for (const p of mesh.primitives) for (let v = 0; v < gltf.accessors[p.attributes.POSITION].count; v++) for (let k = 0; k < 4; k++) {
    if (access(p.attributes.WEIGHTS_0, v, k) > .05) weightedBones.add(joints[access(p.attributes.JOINTS_0, v, k)]);
  }
  reports.push({ variant, source, model, sourceSha256: hash(bytes), modelSha256: hash(output), repairedVertices: repaired,
    triangles: gltf.meshes.flatMap(mesh => mesh.primitives).reduce((sum, p) => sum + gltf.accessors[p.indices].count / 3, 0),
    weightedBones: [...weightedBones], preservedViews, validationErrors: validation.issues.numErrors, validationWarnings: validation.issues.numWarnings,
    clips: gltf.animations.map(clip => clip.name) });
  scene.traverse(node => { if (node.isMesh) { node.geometry.dispose(); node.material.dispose(); if (node.isSkinnedMesh) node.skeleton.dispose(); } });
}
fs.writeFileSync(path.join(WORK, 'build-report.json'), JSON.stringify(reports, null, 2) + '\n');
console.log(JSON.stringify(reports.map(({ preservedViews, ...summary }) => summary), null, 2));

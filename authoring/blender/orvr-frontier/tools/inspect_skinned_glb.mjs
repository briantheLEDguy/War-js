/** Read literal glTF accessors and poses for authoring verification. */
import { Quaternion } from 'three';
import { worldMatrices } from './inspect_mechanical_glb.mjs';

const sizes = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
const components = { 5120: [1, 'readInt8'], 5121: [1, 'readUInt8'], 5122: [2, 'readInt16LE'], 5123: [2, 'readUInt16LE'], 5125: [4, 'readUInt32LE'], 5126: [4, 'readFloatLE'] };
export function accessorValues(document, binary, index) {
  const accessor = document.accessors[index];
  if (accessor.sparse) throw new Error('Sparse accessors require a separate explicit audit');
  const view = document.bufferViews[accessor.bufferView];
  const [bytes, read] = components[accessor.componentType]; const count = sizes[accessor.type];
  const stride = view.byteStride ?? bytes * count;
  const offset = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
  return Array.from({ length: accessor.count }, (_, row) => Array.from({ length: count }, (_, column) => {
    const value = binary[read](offset + row * stride + column * bytes);
    if (!accessor.normalized || accessor.componentType === 5126) return value;
    return accessor.componentType === 5121 ? value / 255 : accessor.componentType === 5123 ? value / 65535
      : accessor.componentType === 5120 ? Math.max(-1, value / 127) : Math.max(-1, value / 32767);
  }));
}

export function animatedWorldMatrices(document, binary, clipName, seconds) {
  const clip = document.animations?.find(animation => animation.name === clipName);
  if (!clip) throw new Error(`Missing clip ${clipName}`);
  const posed = { ...document, nodes: document.nodes.map(node => ({ ...node })) };
  for (const channel of clip.channels) {
    if (channel.target.path === 'weights') throw new Error('Morph target motion requires an explicit audit');
    const sampler = clip.samplers[channel.sampler];
    const times = accessorValues(document, binary, sampler.input).map(row => row[0]);
    const values = accessorValues(document, binary, sampler.output);
    let right = times.findIndex(time => time >= seconds);
    if (right < 0) right = times.length - 1;
    const left = Math.max(0, right - 1);
    const amount = right === left || sampler.interpolation === 'STEP' ? 0 : Math.max(0, Math.min(1, (seconds - times[left]) / (times[right] - times[left])));
    if (sampler.interpolation && !['LINEAR', 'STEP'].includes(sampler.interpolation)) throw new Error(`Unsupported audit interpolation ${sampler.interpolation}`);
    const result = channel.target.path === 'rotation'
      ? new Quaternion().fromArray(values[left]).slerp(new Quaternion().fromArray(values[right]), amount).toArray()
      : values[left].map((value, axis) => value + (values[right][axis] - value) * amount);
    delete posed.nodes[channel.target.node].matrix;
    posed.nodes[channel.target.node][channel.target.path] = result;
  }
  return worldMatrices(posed);
}

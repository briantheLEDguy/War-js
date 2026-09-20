import fs from 'node:fs';
import { Matrix4, Quaternion, Triangle, Vector3 } from 'three';
import { expect } from 'vitest';

/** Decode delivered triangles, not just accessor bounds or authored collision. */
export function modelTriangles(model: string): Triangle[] {
  const bytes = fs.readFileSync(`public/assets/models/${model}`);
  const doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)).toString());
  let bin = Buffer.alloc(0);
  for (let at = 12; at < bytes.length;) {
    const length = bytes.readUInt32LE(at);
    if (bytes.readUInt32LE(at + 4) === 0x004e4942) bin = bytes.subarray(at + 8, at + 8 + length);
    at += 8 + length;
  }
  const component = (index: number, vertex: number, channel = 0): number => {
    const a = doc.accessors[index], view = doc.bufferViews[a.bufferView];
    const size = a.componentType === 5123 ? 2 : a.componentType === 5121 ? 1 : 4;
    const offset = (view.byteOffset ?? 0) + (a.byteOffset ?? 0)
      + vertex * (view.byteStride ?? (a.type === 'VEC3' ? 3 : 1) * size) + channel * size;
    return a.componentType === 5126 ? bin.readFloatLE(offset)
      : size === 4 ? bin.readUInt32LE(offset) : size === 2 ? bin.readUInt16LE(offset) : bin.readUInt8(offset);
  };
  const result: Triangle[] = [];
  const visit = (index: number, parent: Matrix4) => {
    const node = doc.nodes[index];
    const local = node.matrix ? new Matrix4().fromArray(node.matrix) : new Matrix4().compose(
      new Vector3().fromArray(node.translation ?? [0, 0, 0]),
      new Quaternion().fromArray(node.rotation ?? [0, 0, 0, 1]), new Vector3().fromArray(node.scale ?? [1, 1, 1]));
    const world = parent.clone().multiply(local);
    for (const primitive of doc.meshes?.[node.mesh]?.primitives ?? []) {
      expect(primitive.mode ?? 4).toBe(4);
      const count = doc.accessors[primitive.indices ?? primitive.attributes.POSITION].count;
      for (let i = 0; i < count; i += 3) {
        const points = [0, 1, 2].map(k => {
          const vertex = primitive.indices === undefined ? i + k : component(primitive.indices, i + k);
          return new Vector3(...[0, 1, 2].map(axis => component(primitive.attributes.POSITION, vertex, axis)) as [number, number, number]).applyMatrix4(world);
        });
        result.push(new Triangle(points[0], points[1], points[2]));
      }
    }
    for (const child of node.children ?? []) visit(child, world);
  };
  for (const index of doc.scenes[doc.scene ?? 0].nodes) visit(index, new Matrix4());
  return result;
}

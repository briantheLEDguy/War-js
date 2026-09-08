import { Matrix4, Quaternion, Vector3 } from 'three';

export function readGlb(bytes) {
  if (bytes.readUInt32LE(0) !== 0x46546c67 || bytes.readUInt32LE(4) !== 2 || bytes.readUInt32LE(8) !== bytes.length) throw new Error('Invalid GLB header');
  const length = bytes.readUInt32LE(12);
  const document = JSON.parse(bytes.subarray(20, 20 + length).toString('utf8'));
  return { document, binary: bytes.subarray(28 + length) };
}

export function worldMatrices(document) {
  const parents = new Map();
  document.nodes.forEach((node, parent) => (node.children ?? []).forEach(child => {
    if (parents.has(child)) throw new Error('Multiple node parents');
    parents.set(child, parent);
  }));
  const results = new Map();
  function evaluate(index, visiting = new Set()) {
    if (results.has(index)) return results.get(index);
    if (visiting.has(index)) throw new Error('Cyclic node hierarchy');
    visiting.add(index);
    const node = document.nodes[index];
    const local = node.matrix ? new Matrix4().fromArray(node.matrix) : new Matrix4().compose(
      new Vector3().fromArray(node.translation ?? [0, 0, 0]),
      new Quaternion().fromArray(node.rotation ?? [0, 0, 0, 1]),
      new Vector3().fromArray(node.scale ?? [1, 1, 1]),
    );
    if (parents.has(index)) local.premultiply(evaluate(parents.get(index), visiting));
    visiting.delete(index); results.set(index, local); return local;
  }
  document.nodes.forEach((_, index) => evaluate(index));
  return results;
}

export function inspectMechanics(document, report) {
  const issues = []; const matrices = worldMatrices(document);
  const names = new Map(document.nodes.map((node, index) => [node.name, index]));
  for (const component of report.rigid_nodes ?? []) {
    const index = names.get(component.node);
    if (index === undefined) { issues.push(`Missing component ${component.node}`); continue; }
    const [x, y, z] = component.pivot_z_up;
    const actual = new Vector3().setFromMatrixPosition(matrices.get(index));
    if (actual.distanceTo(new Vector3(x, z, -y)) > 1e-5) issues.push(`${component.node}: default world pivot differs from the source assembly`);
    if (component.pivot_node && !names.has(component.pivot_node)) issues.push(`${component.node}: missing fixed pivot parent`);
  }
  const animations = new Map((document.animations ?? []).map(clip => [clip.name, clip]));
  for (const expected of report.clips ?? []) {
    const actual = animations.get(expected.name);
    if (!actual) { issues.push(`Missing clip ${expected.name}`); continue; }
    const inputs = actual.samplers.map(sampler => document.accessors[sampler.input]);
    if (Math.abs(Math.min(...inputs.map(input => input.min[0]))) > 1e-6) issues.push(`${expected.name}: runtime action must start at zero`);
    if (Math.abs(Math.max(...inputs.map(input => input.max[0])) - expected.duration_seconds) > 1e-5) issues.push(`${expected.name}: duration differs from the source action`);
    for (const channel of actual.channels) {
      const name = document.nodes[channel.target.node].name;
      if (name === 'body' || name.startsWith('pivot.')) issues.push(`${expected.name}: animation changes a fixed assembly node`);
    }
  }
  return issues;
}

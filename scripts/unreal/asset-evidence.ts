import { createHash } from 'node:crypto';
import { closeSync, existsSync, openSync, readFileSync, readSync, statSync } from 'node:fs';
import path from 'node:path';

export interface GlbEvidence {
  path: string;
  exists: boolean;
  valid: boolean;
  bytes: number;
  sha256: string | null;
  meshes: number;
  triangles: number;
  skins: number;
  joints: number[];
  clips: string[];
  externalResources: string[];
  errors: string[];
}

export function containedPath(root: string, relative: string): string {
  const target = path.resolve(root, relative);
  const within = path.relative(path.resolve(root), target);
  if (path.isAbsolute(relative) || within === '..' || within.startsWith(`..${path.sep}`) || path.isAbsolute(within)) {
    throw new Error(`Path escapes asset root: ${relative}`);
  }
  return target;
}

export function fileHash(filename: string): string {
  const hash = createHash('sha256');
  const descriptor = openSync(filename, 'r');
  try {
    const buffer = Buffer.alloc(1024 * 1024);
    let length: number;
    while ((length = readSync(descriptor, buffer, 0, buffer.length, null)) > 0) hash.update(buffer.subarray(0, length));
    return hash.digest('hex');
  } finally { closeSync(descriptor); }
}

/** Inspect the binary, not a QC claim. This is structural evidence, not a visual/Unreal import approval. */
export function inspectGlb(repoRoot: string, relativePath: string): GlbEvidence {
  const result: GlbEvidence = { path: relativePath.replaceAll('\\', '/'), exists: false, valid: false,
    bytes: 0, sha256: null, meshes: 0, triangles: 0, skins: 0, joints: [], clips: [], externalResources: [], errors: [] };
  let descriptor: number | undefined;
  try {
    const filename = containedPath(repoRoot, relativePath);
    if (!existsSync(filename)) { result.errors.push('file_missing'); return result; }
    result.exists = true;
    result.bytes = statSync(filename).size;
    result.sha256 = fileHash(filename);
    descriptor = openSync(filename, 'r');
    const header = Buffer.alloc(20);
    if (readSync(descriptor, header, 0, 20, 0) !== 20 || header.readUInt32LE(0) !== 0x46546c67
      || header.readUInt32LE(4) !== 2 || header.readUInt32LE(8) !== result.bytes
      || header.readUInt32LE(16) !== 0x4e4f534a) throw new Error('invalid_glb_header');
    const jsonLength = header.readUInt32LE(12);
    if (jsonLength > 64 * 1024 * 1024 || jsonLength % 4 || jsonLength + 20 > result.bytes) throw new Error('invalid_json_chunk');
    const jsonBuffer = Buffer.alloc(jsonLength);
    if (readSync(descriptor, jsonBuffer, 0, jsonLength, 20) !== jsonLength) throw new Error('truncated_json_chunk');
    const gltf = JSON.parse(jsonBuffer.toString('utf8'));
    if (gltf.asset?.version !== '2.0') throw new Error('invalid_gltf_version');
    let offset = jsonLength + 20;
    while (offset < result.bytes) {
      const chunk = Buffer.alloc(8);
      if (readSync(descriptor, chunk, 0, 8, offset) !== 8) throw new Error('truncated_chunk');
      const length = chunk.readUInt32LE(0);
      if (length % 4 || offset + 8 + length > result.bytes) throw new Error('invalid_chunk_length');
      offset += length + 8;
    }
    const meshes = gltf.meshes ?? [];
    const accessors = gltf.accessors ?? [];
    result.meshes = meshes.length;
    for (const mesh of meshes) for (const primitive of mesh.primitives ?? []) {
      const accessor = accessors[primitive.indices ?? primitive.attributes?.POSITION];
      const positions = accessors[primitive.attributes?.POSITION];
      if (!accessor || !positions || !Number.isSafeInteger(accessor.count) || accessor.count <= 0) {
        result.errors.push('invalid_mesh_accessor'); continue;
      }
      const mode = primitive.mode ?? 4;
      result.triangles += mode === 4 ? accessor.count / 3 : mode === 5 || mode === 6 ? Math.max(0, accessor.count - 2) : 0;
    }
    const nodes = gltf.nodes ?? [];
    const skins = gltf.skins ?? [];
    result.skins = skins.length;
    result.joints = skins.map((skin: { joints?: number[] }) => skin.joints?.length ?? 0);
    for (const skin of skins) {
      // Animation-only GLBs legitimately retain a skeleton without a bound render mesh.
      if (!skin.joints?.length || skin.joints.some((joint: number) => !nodes[joint])) result.errors.push('invalid_skin');
    }
    for (const animation of gltf.animations ?? []) {
      if (!animation.channels?.length || !animation.samplers?.length
        || animation.channels.some((channel: { sampler: number; target?: { node?: number } }) =>
          !animation.samplers[channel.sampler] || !nodes[channel.target?.node ?? -1])) {
        result.errors.push('invalid_animation'); continue;
      }
      if (typeof animation.name === 'string') result.clips.push(animation.name);
    }
    result.clips = [...new Set(result.clips)].sort();
    result.externalResources = [...new Set<string>([...(gltf.images ?? []), ...(gltf.buffers ?? [])]
      .map(item => item.uri).filter(uri => typeof uri === 'string' && !uri.startsWith('data:')))].sort();
    for (const uri of result.externalResources) {
      if (/^[a-z]+:/i.test(uri)) { result.errors.push(`external_resource_url:${uri}`); continue; }
      const resource = containedPath(path.join(repoRoot, 'public/assets'), path.relative(path.join(repoRoot, 'public/assets'), path.resolve(path.dirname(filename), uri)));
      if (!existsSync(resource)) result.errors.push(`external_resource_missing:${uri}`);
    }
    result.errors = [...new Set(result.errors)].sort();
    result.valid = result.errors.length === 0;
  } catch (error) { result.errors.push(error instanceof Error ? error.message : String(error)); }
  finally { if (descriptor !== undefined) closeSync(descriptor); }
  return result;
}

export function readJson<T>(root: string, relative: string): T {
  return JSON.parse(readFileSync(containedPath(root, relative), 'utf8')) as T;
}

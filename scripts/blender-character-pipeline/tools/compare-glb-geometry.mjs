import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import path from 'node:path';

const COMPONENT_BYTES = new Map([
  [5120, 1], [5121, 1], [5122, 2], [5123, 2], [5125, 4], [5126, 4],
]);
const TYPE_COMPONENTS = new Map([
  ['SCALAR', 1], ['VEC2', 2], ['VEC3', 3], ['VEC4', 4],
  ['MAT2', 4], ['MAT3', 9], ['MAT4', 16],
]);

function option(name) {
  const prefix = `--${name}=`;
  return process.argv.slice(2).find((value) => value.startsWith(prefix))?.slice(prefix.length);
}

function parseGlb(filePath) {
  const payload = readFileSync(filePath);
  if (payload.toString('ascii', 0, 4) !== 'glTF' || payload.readUInt32LE(4) !== 2) {
    throw new Error(`Not a GLB 2.0 file: ${filePath}`);
  }
  let offset = 12;
  let document;
  let binary;
  while (offset + 8 <= payload.length) {
    const length = payload.readUInt32LE(offset);
    const kind = payload.readUInt32LE(offset + 4);
    const chunk = payload.subarray(offset + 8, offset + 8 + length);
    if (kind === 0x4E4F534A) document = JSON.parse(chunk.toString('utf8').replace(/\u0000+$/gu, '').trimEnd());
    if (kind === 0x004E4942) binary = chunk;
    offset += 8 + length;
  }
  if (!document || !binary) throw new Error(`GLB is missing JSON or BIN chunk: ${filePath}`);
  return { document, binary };
}

function accessorPayload(glb, accessorIndex) {
  const accessor = glb.document.accessors?.[accessorIndex];
  if (!accessor || accessor.bufferView === undefined) throw new Error(`Accessor ${accessorIndex} has no bufferView`);
  if (accessor.sparse) throw new Error(`Sparse accessor ${accessorIndex} is not supported by the exact geometry audit`);
  const view = glb.document.bufferViews?.[accessor.bufferView];
  if (!view || (view.buffer ?? 0) !== 0) throw new Error(`Accessor ${accessorIndex} does not use the GLB binary buffer`);
  const componentBytes = COMPONENT_BYTES.get(accessor.componentType);
  const componentCount = TYPE_COMPONENTS.get(accessor.type);
  if (!componentBytes || !componentCount) throw new Error(`Accessor ${accessorIndex} has an unsupported layout`);
  const elementBytes = componentBytes * componentCount;
  const stride = view.byteStride ?? elementBytes;
  const start = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
  const logical = Buffer.alloc(accessor.count * elementBytes);
  for (let index = 0; index < accessor.count; index += 1) {
    glb.binary.copy(logical, index * elementBytes, start + index * stride, start + index * stride + elementBytes);
  }
  return {
    accessor: accessorIndex,
    count: accessor.count,
    componentType: accessor.componentType,
    type: accessor.type,
    normalized: accessor.normalized === true,
    sha256: createHash('sha256').update(logical).digest('hex'),
  };
}

function geometryManifest(filePath) {
  const glb = parseGlb(filePath);
  const meshes = (glb.document.meshes ?? []).map((mesh, meshIndex) => ({
    name: mesh.name ?? `mesh_${meshIndex}`,
    primitives: mesh.primitives.map((primitive, primitiveIndex) => {
      if (primitive.attributes?.POSITION === undefined || primitive.indices === undefined) {
        throw new Error(`${mesh.name ?? meshIndex} primitive ${primitiveIndex} lacks POSITION or indices`);
      }
      return {
        primitive: primitiveIndex,
        mode: primitive.mode ?? 4,
        position: accessorPayload(glb, primitive.attributes.POSITION),
        indices: accessorPayload(glb, primitive.indices),
      };
    }),
  }));
  return { file: path.resolve(filePath), meshes };
}

function comparable(manifest) {
  return manifest.meshes.map((mesh) => ({
    name: mesh.name,
    primitives: mesh.primitives.map((primitive) => ({
      primitive: primitive.primitive,
      mode: primitive.mode,
      position: {
        count: primitive.position.count,
        componentType: primitive.position.componentType,
        type: primitive.position.type,
        normalized: primitive.position.normalized,
        sha256: primitive.position.sha256,
      },
      indices: {
        count: primitive.indices.count,
        componentType: primitive.indices.componentType,
        type: primitive.indices.type,
        normalized: primitive.indices.normalized,
        sha256: primitive.indices.sha256,
      },
    })),
  }));
}

const baselinePath = option('baseline');
const candidatePath = option('candidate');
const outputPath = option('output');
if (!baselinePath || !candidatePath || !outputPath) {
  throw new Error('Usage: node compare-glb-geometry.mjs --baseline=<v18.glb> --candidate=<v19.glb> --output=<report.json>');
}
const baseline = geometryManifest(baselinePath);
const candidate = geometryManifest(candidatePath);
const matches = JSON.stringify(comparable(baseline)) === JSON.stringify(comparable(candidate));
const report = {
  schemaVersion: 1,
  comparison: 'exact_logical_position_and_index_accessor_payloads',
  baseline,
  candidate,
  meshCount: baseline.meshes.length,
  matches,
};
mkdirSync(path.dirname(path.resolve(outputPath)), { recursive: true });
writeFileSync(outputPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');
console.log(JSON.stringify({ output: path.resolve(outputPath), matches, meshCount: report.meshCount }));
if (!matches) process.exitCode = 1;

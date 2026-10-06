import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { requireCitadelRouteSurfaceBindings } from './citadel-route-surface';

export const CITADEL_NATIVE_IMPORT_CONVENTION = {
  schemaVersion: 1,
  sourceTriangleWinding: 'counter_clockwise_cross_aligned_with_outward_normals',
  nativeTriangleWinding: 'clockwise_cross_opposed_to_outward_normals',
  normalPolicy: 'preserve_outward_source_normals',
};
export const CITADEL_NATIVE_MESH_BUILD_SETTINGS = {
  recompute_normals: false, recompute_tangents: true, use_mikk_t_space: true,
  compute_weighted_normals: false, generate_lightmap_u_vs: true, src_lightmap_index: 0, dst_lightmap_index: 1,
  min_lightmap_resolution: 64, use_full_precision_u_vs: true, use_high_precision_tangent_basis: true,
};
export const CITADEL_NATIVE_TANGENT_POLICY = {
  version: 1, diagnosticOnly: true, highPrecision: true,
  basisSource: 'actual_render_buffer_x_z_and_native_reconstructed_y',
  nearZeroComponentTolerance: Math.fround(.0001), orthogonalityAbsoluteNormalizedDotTolerance: Math.fround(.02),
  badVertexSampleLimit: 64, sampleComponentPolicy: 'actual_buffer_values_nonfinite_as_null',
};
const tangentUnitTolerances = { x: Math.fround(.02), y: Math.fround(.04), z: Math.fround(.02) };
const hash = (value: string | Buffer) => createHash('sha256').update(value).digest('hex');
export const CITADEL_MATTE_NAVY = { tint: [.0035,.012,.034], roughness: .92, metallic: 0, specular: .25 };

/** The cloth graph is scalar-only; texture connections would invalidate its measured matte treatment. */
export function requireNativeCitadelMaterials(receipt: any, source: any): void {
  const fail = () => { throw new Error('The owned matte navy material needs its exact signed constants, native graph readback and package hash.'); };
  const rows=receipt.materialBindings, packageName=`/Game/WorldRebuild/AegisCitadel_${receipt.revision}/Materials/M_blue`;
  if (!Array.isArray(rows) || rows.length!==1) fail();
  const row=rows[0], spec=source.materialSpecs?.blue;
  const exactSpec=(v:any) => v && Object.keys(v).sort().join(',')==='metallic,roughness,specular,tint'
    && Array.isArray(v.tint) && v.tint.length===3 && v.tint.every((n:any,i:number) => n===CITADEL_MATTE_NAVY.tint[i])
    && ['roughness','metallic','specular'].every(k => v[k]===CITADEL_MATTE_NAVY[k as keyof typeof CITADEL_MATTE_NAVY]);
  if (!row || Object.keys(row).sort().join(',')!=='actualConstantReadback,package,role,sha256,sourceSpec'
    || row.role!=='blue' || row.package!==packageName || !/^[a-f0-9]{64}$/.test(row.sha256 ?? '')
    || row.sha256!==receipt.packageHashes?.[packageName] || !exactSpec(spec) || !exactSpec(row.sourceSpec)) fail();
  const actual=row.actualConstantReadback;
  if (!actual || Object.keys(actual).sort().join(',')!=='ambientOcclusionInputConnected,metallic,normalInputConnected,roughness,specular,tint'
    || !Array.isArray(actual.tint) || actual.tint.length!==3
    || actual.tint.some((v:any,i:number) => typeof v!=='number' || !Number.isFinite(v) || Math.abs(v-spec.tint[i])>1e-6)
    || ['roughness','metallic','specular'].some(k => typeof actual[k]!=='number' || !Number.isFinite(actual[k]) || Math.abs(actual[k]-spec[k])>1e-6)
    || actual.normalInputConnected!==false || actual.ambientOcclusionInputConnected!==false) fail();
}
function renderTangentBasis(row: any): void {
  const basis = row.tangentBasis;
  const fail = () => { throw new Error('Actual native render tangent basis is missing, degenerate or uses an unknown diagnostic policy.'); };
  if (!basis || Object.entries(CITADEL_NATIVE_TANGENT_POLICY).some(([key, value]) => basis[key] !== value)
    || basis.invalidVertices !== 0 || basis.orthogonalVertices !== row.vertices
    || !Array.isArray(basis.badVertexSamples) || basis.badVertexSamples.length !== 0 || basis.badVertexSamplesTruncated !== false
    || Object.keys(basis.axes ?? {}).length !== 3 || Object.keys(basis.pairs ?? {}).length !== 3) fail();
  for (const [axis, tolerance] of Object.entries(tangentUnitTolerances)) {
    const value = basis.axes[axis];
    if (!value || value.finite !== row.vertices || value.unit !== row.vertices
      || ['nonFinite', 'nearZero', 'nonUnit'].some(key => value[key] !== 0) || value.unitSquaredTolerance !== tolerance
      || !Number.isFinite(value.minimumLength) || !Number.isFinite(value.maximumLength)
      || value.minimumLength <= 0 || value.maximumLength < value.minimumLength
      // The API records float32 square roots; aggregate unit counts retain the exact native threshold.
      || value.minimumLength < Math.sqrt(1 - tolerance) - 1e-6 || value.maximumLength > Math.sqrt(1 + tolerance) + 1e-6) fail();
  }
  for (const pair of ['xy', 'xz', 'yz']) {
    const value = basis.pairs[pair];
    if (!value || value.evaluated !== row.vertices || value.orthogonal !== row.vertices || value.skipped !== 0 || value.nonOrthogonal !== 0
      || !Number.isFinite(value.maximumAbsoluteNormalizedDot) || value.maximumAbsoluteNormalizedDot < 0
      || value.maximumAbsoluteNormalizedDot > CITADEL_NATIVE_TANGENT_POLICY.orthogonalityAbsoluteNormalizedDotTolerance) fail();
  }
}
function sourceArray(text: string, key: string): string {
  const marker = `"${key}":`, start = text.indexOf(marker);
  if (start < 0 || text.indexOf(marker, start + marker.length) >= 0) throw new Error('Missing or duplicate source array.');
  let first = start + marker.length;
  while (/\s/.test(text[first] ?? '')) first++;
  if (text[first] !== '[') throw new Error('Source member is not an array.');
  let depth = 0, quoted = false, escaped = false;
  for (let i = first; i < text.length; i++) {
    const ch = text[i];
    if (quoted) { if (escaped) escaped = false; else if (ch === '\\') escaped = true; else if (ch === '"') quoted = false; }
    else if (ch === '"') quoted = true;
    else if (ch === '[') depth++;
    else if (ch === ']' && --depth === 0) return text.slice(first, i + 1);
  }
  throw new Error('Unterminated source array.');
}
function renderBuffers(binding: any, sourceText: string): void {
  if (binding.sourceArrayHashConvention !== 'sha256_raw_utf8_mesh_json_member_array'
    || Object.keys(binding.nativeMeshBuildSettings ?? {}).length !== Object.keys(CITADEL_NATIVE_MESH_BUILD_SETTINGS).length
    || Object.entries(CITADEL_NATIVE_MESH_BUILD_SETTINGS).some(([key, value]) => binding.nativeMeshBuildSettings?.[key] !== value)
    || ['Positions', 'Normals', 'UVs'].some((key, i) => binding[`source${key}Sha256`] !== hash(sourceArray(sourceText, ['positions', 'normals', 'uvs'][i])))
    || typeof binding.renderDataAuditPayload !== 'string' || binding.renderDataAuditPayload.length > 1_000_000
    || hash(binding.renderDataAuditPayload) !== binding.renderDataAuditSha256)
    throw new Error('Actual render buffers require authored normal/UV source hashes and the preserved native build policy.');
  const audit = JSON.parse(binding.renderDataAuditPayload);
  const canonical = (v: any): any => Array.isArray(v) ? v.map(canonical) : v && typeof v === 'object'
    ? Object.fromEntries(Object.keys(v).sort().map(key => [key, canonical(v[key])])) : v;
  if (JSON.stringify(canonical(audit)) !== JSON.stringify(canonical(binding.renderDataAudit))
    || audit.readOnly !== true || audit.available !== true || audit.mesh !== `${binding.mesh}.${binding.mesh.split('/').at(-1)}`
    || !Array.isArray(audit.lods) || !audit.lods.length || audit.lods.length !== binding.triangles.length)
    throw new Error('Actual native render-buffer audit is unavailable, stale or belongs to another mesh.');
  const rows = new Map<number, any>(audit.lods.map((row: any) => [row.lod, row]));
  if (rows.size !== audit.lods.length) throw new Error('Duplicate native render LOD audit.');
  for (let i = 0; i < rows.size; i++) {
    const row = rows.get(i);
    if (!row || row.cpuReadable !== true || ['vertices', 'indices', 'uvChannels'].some(key => !Number.isSafeInteger(row[key]) || row[key] <= 0)
      || ['invalidPositions', 'invalidNormals', 'nonUnitNormals', 'invalidUVs'].some(key => row[key] !== 0)
      || i === 0 && (row.committedSourcePositionMissing !== 0 || row.committedSourceNormalDifferent !== 0
        || row.committedSourceNormalMatches !== row.vertices || row.sourcePositionToleranceCm !== .1
        || row.sourceNormalDotThreshold !== .995 || row.sourceMatchingPolicy !== 'oriented_triangle_corners_material_and_uv0'
        || row.indices % 3 !== 0 || row.committedSourceTriangleMatches !== row.indices / 3
        || row.committedSourceTrianglesMissing !== 0 || row.committedSourceTrianglesDifferent !== 0
        || row.sourceUvAbsoluteTolerance !== .0005 || row.sourceUvRelativeTolerance !== .001))
      throw new Error('Actual native render positions, UVs or source normals are invalid or unavailable.');
    renderTangentBasis(row);
  }
}
const relativeFile = (root: string, relative: unknown) => {
  if (typeof relative !== 'string' || !relative || relative.includes('\\') || relative.includes(':')
    || relative.split('/').some(part => !part || part === '.' || part === '..')) throw new Error('Invalid signed citadel source path.');
  const file = path.resolve(root, relative);
  if (!file.startsWith(path.resolve(root) + path.sep)) throw new Error('Citadel source escaped its signed revision.');
  return file;
};

export function requireVersionedCitadelMeshBindings(blueprint: any, assets: any, bindings: any): void {
  const version = Object.hasOwn(blueprint, 'recipeVersion') ? blueprint.recipeVersion : 1;
  if (!Number.isInteger(version) || version < 1 || version > 9)
    throw new Error('Unsupported citadel mesh recipe version.');
  const count = version === 9 ? 39 : 38;
  if (!Array.isArray(assets) || assets.length !== count || !Array.isArray(bindings) || bindings.length !== count
    || [...assets, ...bindings].some(row => !row || typeof row.id !== 'string'))
    throw new Error('Every versioned native binding must match the signed source manifest.');
  const ids = new Set<string>(assets.map(row => row.id)), native = new Set<string>(bindings.map(row => row.id));
  if (ids.size !== count || native.size !== count || [...ids].some(id => !native.has(id)))
    throw new Error('Duplicate or mismatched native/source citadel mesh identity.');
  if (ids.has('wing_foundation_repairs') !== (version === 9))
    throw new Error('Wing foundation binding differs from the recorded recipe version.');
}

/** Bind the native boundary adaptation to every unchanged authored source mesh. */
export function requireNativeCitadelImport(directory: string, receipt: any, blueprint: any): void {
  const convention = receipt.nativeImportConvention;
  if (!convention || Object.keys(convention).length !== 4
    || Object.entries(CITADEL_NATIVE_IMPORT_CONVENTION).some(([key, value]) => convention[key] !== value))
    throw new Error('The explicit source CCW to native CW outward-normal import convention is required.');
  const source = JSON.parse(readFileSync(path.join(directory, 'assets-source.json'), 'utf8').replace(/^\uFEFF/, ''));
  requireNativeCitadelMaterials(receipt,source);
  if (source.schemaVersion !== 1 || source.revision !== receipt.revision || source.blueprintSignature !== receipt.signature
    || source.geometrySignature !== receipt.geometrySignature)
    throw new Error('Native bindings must match the signed source manifest.');
  requireVersionedCitadelMeshBindings(blueprint, source.assets, receipt.bindings);
  const bindings = new Map<string, any>();
  for (const row of receipt.bindings) {
    if (!row || typeof row.id !== 'string' || !/^[a-z0-9_]+$/.test(row.id) || bindings.has(row.id))
      throw new Error('Duplicate or invalid native citadel binding.');
    bindings.set(row.id, row);
  }
  const ids = new Set<string>();
  const sourceMeshes=new Map<string,any>();
  for (const asset of source.assets) {
    if (!asset || typeof asset.id !== 'string' || !/^[a-z0-9_]+$/.test(asset.id) || ids.has(asset.id))
      throw new Error('Duplicate or invalid signed citadel source identity.');
    ids.add(asset.id);
    const binding = bindings.get(asset.id), packageName = `/Game/WorldRebuild/AegisCitadel_${receipt.revision}/Meshes/SM_${asset.id}`;
    if (!binding || binding.mesh !== packageName || binding.sha256 !== receipt.packageHashes?.[packageName]
      || binding.gateLeaf !== asset.gateLeaf || typeof asset.gateLeaf !== 'boolean'
      || !Array.isArray(binding.triangles) || !binding.triangles.length || binding.triangles[0] !== asset.triangles)
      throw new Error(`Native citadel mesh ownership or source triangle count differs: ${asset.id}`);
    const bytes = readFileSync(relativeFile(directory, asset.meshFile));
    if (hash(bytes) !== asset.sha256) throw new Error(`Signed citadel source mesh changed: ${asset.id}`);
    const sourceText = bytes.toString('utf8'), mesh = JSON.parse(sourceText);
    sourceMeshes.set(asset.id,mesh);
    const point = (v: any) => Array.isArray(v) && v.length === 3 && v.every((n: any) => typeof n === 'number' && Number.isFinite(n));
    if (!Array.isArray(mesh.positions) || !Array.isArray(mesh.normals) || mesh.positions.length !== mesh.normals.length
      || !mesh.positions.every(point) || !mesh.normals.every(point) || !Array.isArray(mesh.indices)
      || !mesh.indices.length || mesh.indices.length % 3 || mesh.indices.length / 3 !== asset.triangles
      || mesh.indices.some((n: any) => !Number.isSafeInteger(n) || n < 0 || n >= mesh.positions.length))
      throw new Error(`Invalid signed source triangle arrays: ${asset.id}`);
    const native: number[] = [];
    for (let i = 0; i < mesh.indices.length; i += 3) {
      const [a, b, c] = mesh.indices.slice(i, i + 3), p = mesh.positions;
      const ab = p[b].map((v: number, j: number) => v - p[a][j]), ac = p[c].map((v: number, j: number) => v - p[a][j]);
      const cross = [ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2], ab[0] * ac[1] - ab[1] * ac[0]];
      if (cross.reduce((sum, v) => sum + v * v, 0) < 1e-12
        || [a, b, c].some(index => cross.reduce((sum, v, j) => sum + v * mesh.normals[index][j], 0) <= 0))
        throw new Error(`Source triangles violate their declared outward-normal winding: ${asset.id}`);
      native.push(a, c, b);
    }
    if (binding.sourceIndicesSha256 !== hash(JSON.stringify(mesh.indices))
      || binding.nativeIndicesSha256 !== hash(JSON.stringify(native)))
      throw new Error(`Native source-to-import index hashes differ: ${asset.id}`);
    renderBuffers(binding, sourceText);
  }
  requireCitadelRouteSurfaceBindings(source,blueprint,sourceMeshes);
  if (source.geometrySignature !== hash(JSON.stringify(source.assets.map((row: any) => [row.id, row.sha256])))
    || !source.sourceMaster || hash(readFileSync(relativeFile(directory, source.sourceMaster.path))) !== source.sourceMaster.sha256)
    throw new Error('The authored geometry manifest or Blender master changed.');
  const start = receipt.proofStart, floor = blueprint.teamSpawns?.[1];
  const point = (value: any) => Array.isArray(value) && value.length === 3 && value.every((n: any) => typeof n === 'number' && Number.isFinite(n));
  if (!point(floor) || !start || typeof start.actor !== 'string' || !start.actor.startsWith(receipt.siegeMap + '.')
    || start.sourceTeamSpawnIndex !== 1 || !point(start.signedFloorCm) || !point(start.locationCm)
    || start.signedFloorCm.some((v: number, i: number) => Math.abs(v - floor[i]) > .1)
    || start.locationCm.some((v: number, i: number) => Math.abs(v - floor[i] - (i === 2 ? 99 : 0)) > .1)
    || !Number.isFinite(start.actualFloorZCm) || Math.abs(start.actualFloorZCm - floor[2]) > 15
    || start.capsuleRadiusCm !== 42 || start.capsuleHalfHeightCm !== 96 || start.capsuleClear !== true
    || start.traceChannel !== 'Visibility' || start.traceComplex !== true
    || !Number.isInteger(start.otherStartsPreserved) || start.otherStartsPreserved < 0)
    throw new Error('The private proof start does not match its signed lower-city spawn or actual capsule clearance.');
}

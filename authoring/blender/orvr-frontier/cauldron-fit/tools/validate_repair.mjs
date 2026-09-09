/** Validate one replacement against the retained original assembly and exact reimports. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';
import { readGlb, inspectMechanics, worldMatrices } from '../../tools/inspect_mechanical_glb.mjs';

export const work = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const repo = path.resolve(work, '../../../..');
export const key = 'frontier_oil_cauldron';
export const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
export const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));
export const hashFile = async file => hash(await fs.readFile(file));
export async function save(file, value) {
  const temporary = file + '.' + crypto.randomUUID() + '.tmp';
  try { await fs.writeFile(temporary, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' }); await fs.rename(temporary, file); }
  finally { await fs.rm(temporary, { force: true }); }
}

function accessorBytes({ document, binary }, index) {
  const accessor = document.accessors[index], view = document.bufferViews[accessor.bufferView];
  assert(!accessor.sparse, 'Unexpected sparse mechanical animation');
  const width = { SCALAR: 1, VEC3: 3, VEC4: 4 }[accessor.type];
  assert.equal(accessor.componentType, 5126);
  const bytes = width * 4, offset = (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0);
  return Array.from({ length: accessor.count }, (_, i) => binary.subarray(offset + i * (view.byteStride ?? bytes), offset + i * (view.byteStride ?? bytes) + bytes).toString('hex'));
}

export function animationSignature(glb) {
  return glb.document.animations.map(clip => ({ name: clip.name, channels: clip.channels.map(channel => {
    const sampler = clip.samplers[channel.sampler];
    return { node: glb.document.nodes[channel.target.node].name, path: channel.target.path,
      interpolation: sampler.interpolation ?? 'LINEAR', input: accessorBytes(glb, sampler.input), output: accessorBytes(glb, sampler.output) };
  }) }));
}

export function verifyContacts(contacts) {
  assert.equal(contacts.length, 6);
  assert.equal(new Set(contacts.map(c => `${c.x},${c.z}`)).size, 6);
  for (const c of contacts) {
    assert([-.3, 0, .3].includes(c.x) && [.48, .75].includes(c.z));
    assert(Number.isFinite(c.minimum_signed_distance_m) && Number.isFinite(c.maximum_signed_distance_m));
    assert(c.minimum_signed_distance_m <= .001 && c.minimum_signed_distance_m >= -.005, 'Washer must be seated within the shell thickness');
    assert(c.maximum_signed_distance_m > .006 && c.maximum_signed_distance_m < .025, 'Retain the raised clinch relief without a floating ornament');
  }
}

export async function validateRepair() {
  const original = path.dirname(work), built = await read(path.join(work, 'review', key + '_build.json'));
  const sourceFile = path.join(work, 'source/frontier_collection.json'), source = await read(sourceFile);
  assert.deepEqual(Object.keys(source.assets), [key]);
  assert.equal(source.surface_fit.source_sha256, await hashFile(path.join(original, 'source/frontier_collection.json')));
  assert.equal(source.surface_fit.tool_sha256, await hashFile(path.join(work, 'tools/fit_cauldron.py')));
  assert.equal(built.source_sha256, await hashFile(sourceFile));
  for (const [field, file] of [['builder_sha256', 'build_collection.py'], ['mechanics_sha256', 'mechanical_animation.py']])
    assert.equal(built[field], await hashFile(path.join(original, 'tools', file)));
  assert.equal(built.paint_record_sha256, await hashFile(path.join(work, 'textures/paint_records.json')));
  assert.equal(built.baker_sha256, await hashFile(path.join(original, '../battle-prelate-reference-rebuild/tools/bake_atlas.py')));
  for (const [file, digest] of Object.entries(built.source_texture_sha256)) assert.equal(digest, await hashFile(path.join(work, file)));
  const fitting = await read(path.join(work, 'review/fit-samples.json'));
  assert.equal(fitting.tool_sha256, source.surface_fit.tool_sha256);
  const actual = await read(path.join(work, 'review/actual-export-review.json'));
  assert.equal(actual.toolSha256, await hashFile(path.join(work, 'tools/review_exports.py')));
  assert.deepEqual(actual.models.map(m => m.lod), [0, 1, 2]);
  assert.deepEqual(built.lods.map(l => l.level), [0, 1, 2]);
  const inventory = { assetId: key, sourceSha256: built.source_sha256, buildSha256: await hashFile(path.join(work, 'review', key + '_build.json')),
    fittingSha256: await hashFile(path.join(work, 'review/fit-samples.json')), actualReviewSha256: await hashFile(path.join(work, 'review/actual-export-review.json')),
    validationToolSha256: await hashFile(fileURLToPath(import.meta.url)), masters: {}, textures: {}, models: [], images: {} };
  for (const [file, expected] of [[built.master, built.master_sha256], [built.animated_master, built.animated_master_sha256],
    [built.lods[2].lod_refinement.master, built.lods[2].lod_refinement.master_sha256]]) {
    assert.equal(await hashFile(path.join(work, file)), expected); inventory.masters[file.replaceAll('\\', '/')] = expected;
  }
  assert.equal(built.lods[2].lod_refinement.tool_sha256, await hashFile(path.join(original, 'tools/refine_mechanism_lod2.py')));
  for (const lod of built.lods) {
    const file = path.join(work, lod.path), bytes = await fs.readFile(file), glb = readGlb(bytes);
    const baseline = readGlb(await fs.readFile(path.join(original, 'runtime', path.basename(file))));
    assert.equal(hash(bytes), lod.sha256); assert.equal(bytes.length, lod.bytes);
    assert.deepEqual(inspectMechanics(glb.document, lod), []);
    assert.deepEqual(animationSignature(glb), animationSignature(baseline), 'Pour animation data must be unchanged');
    const originalMatrices = worldMatrices(baseline.document), matrices = worldMatrices(glb.document);
    for (const [i, node] of baseline.document.nodes.entries()) {
      const replacement = glb.document.nodes.findIndex(n => n.name === node.name);
      assert(replacement >= 0, 'Missing retained assembly node ' + node.name);
      assert.deepEqual(matrices.get(replacement).elements, originalMatrices.get(i).elements, 'Assembly transform changed: ' + node.name);
    }
    assert.equal(glb.document.materials.length, 2); assert.equal(glb.document.meshes.length, 2);
    for (const material of glb.document.materials) assert(material.pbrMetallicRoughness.baseColorTexture && material.pbrMetallicRoughness.metallicRoughnessTexture && material.normalTexture && material.occlusionTexture);
    const triangles = glb.document.nodes.reduce((sum, node) => sum + (node.mesh === undefined ? 0 : glb.document.meshes[node.mesh].primitives.reduce((n, p) => n + glb.document.accessors[p.indices].count / 3, 0)), 0);
    assert.equal(triangles, lod.triangles); assert(triangles <= [24000, 6100, 2900][lod.level]);
    if (lod.level) assert(triangles < built.lods[lod.level - 1].triangles);
    const result = await validator.validateBytes(new Uint8Array(bytes), { uri: path.basename(file) });
    assert.equal(result.issues.numErrors, 0); assert.equal(result.issues.numWarnings, 0);
    await save(path.join(work, 'review', path.basename(file) + '.validation.json'), result);
    const review = actual.models[lod.level]; assert.equal(review.modelSha256, lod.sha256); verifyContacts(review.contacts);
    assert.deepEqual(Object.keys(review.views).sort(), (lod.level === 0 ? ['contact_detail', 'pour', 'ready'] : ['pour', 'ready']));
    for (const view of Object.values(review.views)) { assert.equal(await hashFile(path.join(work, view.file)), view.sha256); inventory.images[view.file.replaceAll('\\', '/')] = view.sha256; }
    for (const files of Object.values(lod.textures)) for (const file of Object.values(files)) {
      const relative = path.relative(work, file).replaceAll('\\', '/'); assert(relative.startsWith('textures/baked/') && !relative.includes('..'));
      inventory.textures[relative] = await hashFile(file);
    }
    inventory.models.push({ level: lod.level, model: path.basename(file), sha256: lod.sha256, triangles, bytes: bytes.length, errors: 0, warnings: 0 });
  }
  await save(path.join(work, 'review/validated-inventory.json'), inventory);
  return inventory;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const inventory = await validateRepair(); console.log(JSON.stringify({ models: inventory.models, contactAndMotionChecks: 'passed' }, null, 2));
}

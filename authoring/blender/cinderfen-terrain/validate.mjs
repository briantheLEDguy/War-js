import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';
import validator from 'gltf-validator';

export const work = path.dirname(fileURLToPath(import.meta.url));
export const sha = bytes => createHash('sha256').update(bytes).digest('hex');
export const requiredViews = ['terrain_overview_lod0.png', 'road_material.png', 'terrain_overview_lod1.png', 'terrain_overview_lod2.png', 'road_junction_lod0.png'];

export function textureFile(uri, directory = work) {
  assert.match(uri, /^\.\.\/textures\/cinderfen_terrain\/[a-f0-9]{20}\.png$/, 'Unexpected external terrain texture path');
  return path.resolve(directory, 'runtime', uri);
}

export function roadAlphaRange(bytes, doc, primitive) {
  const accessor = doc.accessors[primitive.attributes.COLOR_0];
  if (accessor?.type !== 'VEC4') return null;
  const view = doc.bufferViews[accessor.bufferView], size = accessor.componentType === 5126 ? 4 : accessor.componentType === 5123 ? 2 : 1;
  const start = 28 + bytes.readUInt32LE(12) + (view.byteOffset ?? 0) + (accessor.byteOffset ?? 0), stride = view.byteStride ?? size * 4;
  let min = Infinity, max = -Infinity;
  for (let index = 0; index < accessor.count; index += 1) {
    const offset = start + index * stride + size * 3;
    const value = size === 4 ? bytes.readFloatLE(offset) : size === 2 ? bytes.readUInt16LE(offset) / 65535 : bytes.readUInt8(offset) / 255;
    min = Math.min(min, value); max = Math.max(max, value);
  }
  return { min, max };
}

/** A review must depict the exact survey, models and external texture bytes. */
export function assertRenderReceipt(receipt, evidence, images) {
  assert.equal(receipt.schemaVersion, 1, 'Unsupported render receipt');
  assert.equal(receipt.buildSha256, evidence.buildSha256, 'Renders depict an older build');
  assert.equal(receipt.sourceSha256, evidence.sourceSha256, 'Renders depict an older survey');
  assert.deepEqual(receipt.views.map(view => view.image).sort(), [...requiredViews].sort(), 'Four actual-export overview/material views and the junction close-up required');
  for (const view of receipt.views) {
    const level = view.image === 'road_material.png' ? 0 : Number(view.image.match(/lod([012])/)[1]);
    const expected = evidence.models.filter(model => model.level === level).map(({ level: _, ...model }) => model);
    assert.deepEqual(view.models, expected, `${view.image}: mesh or external texture evidence changed`);
    assert.equal(view.imageSha256, images[view.image], `${view.image}: review image changed`);
  }
}

export async function validateTerrain(directory = work) {
  const reportBytes = await readFile(path.join(directory, 'build-report.json'));
  const sourceBytes = await readFile(path.join(directory, 'terrain-source.json'));
  const report = JSON.parse(reportBytes), source = JSON.parse(sourceBytes);
  const { sourceSha256, ...survey } = source;
  assert.equal(sourceSha256, sha(JSON.stringify(survey)), 'Survey content hash is stale');
  assert.equal(report.length, 16, 'Sixteen terrain sectors required');
  assert.equal(new Set(report.map(asset => asset.key)).size, 16, 'Duplicate terrain sector');
  const results = [], models = [];
  for (const asset of report) {
    assert.equal(asset.buildToolSha256,sha(await readFile(path.join(directory,'build_terrain.py'))),'Terrain builder provenance changed');
    assert.equal(asset.junctionToolSha256,sha(await readFile(path.join(directory,'road_junctions.py'))),'Junction authoring provenance changed');
    assert.deepEqual(asset.lods.map(lod => lod.level), [0, 1, 2], `${asset.key}: three LODs required`);
    for (const lod of asset.lods) {
      assert.match(lod.model, /^frontier_cinderfen_outskirts_terrain_[0-3]_[0-3](?:_lod[12])?\.glb$/);
      const file = path.join(directory, 'runtime', lod.model), bytes = await readFile(file);
      const result = await validator.validateBytes(new Uint8Array(bytes), {
        uri: lod.model, externalResourceFunction: uri => readFile(textureFile(uri, directory)),
      });
      const doc = JSON.parse(bytes.subarray(20, 20 + bytes.readUInt32LE(12)));
      const errors = result.issues.messages.filter(message => message.severity === 0).map(message => message.message);
      if (sha(bytes) !== lod.sha256) errors.push('Build hash mismatch');
      if (bytes.length !== lod.bytes) errors.push('Build byte count mismatch');
      const primitives = doc.meshes.flatMap(mesh => mesh.primitives);
      const triangles = primitives.reduce((sum, primitive) => sum + doc.accessors[primitive.indices].count / 3, 0);
      if (triangles !== lod.triangles) errors.push('Build triangle count mismatch');
      for (const primitive of primitives) for (const key of ['POSITION', 'NORMAL', 'TANGENT', 'TEXCOORD_0', 'COLOR_0']) {
        if (primitive.attributes[key] === undefined) errors.push(`Missing ${key}`);
      }
      for (const primitive of primitives.filter(primitive => doc.materials[primitive.material].name === 'Cinderfen_limestone_road')) {
        const alpha = roadAlphaRange(bytes, doc, primitive);
        if (!alpha || alpha.min > .01 || alpha.max < .99 || doc.materials[primitive.material].alphaMode !== 'BLEND') {
          errors.push('Road COLOR_0 does not retain the authored transparent verge and opaque center');
        }
      }
      if (lod.level && triangles >= asset.lods[lod.level - 1].triangles) errors.push('LOD did not reduce');
      if (doc.materials.some(material => !material.normalTexture)) errors.push('Missing normal detail');
      for (const node of doc.nodes.filter(node => node.mesh !== undefined)) {
        if (node.extras?.source_sha256 !== sourceSha256) errors.push('Mesh was exported from an older survey');
      }
      const externalTextures = [];
      for (const image of doc.images ?? []) {
        const imagePath = textureFile(image.uri, directory), hash = sha(await readFile(imagePath));
        if (path.basename(imagePath) !== hash.slice(0, 20) + '.png') errors.push(`External texture bytes changed: ${image.uri}`);
        externalTextures.push({ uri: image.uri, sha256: hash });
      }
      externalTextures.sort((a, b) => a.uri.localeCompare(b.uri));
      models.push({ level: lod.level, model: lod.model, sha256: sha(bytes), externalTextures });
      results.push({ model: lod.model, errors, warnings: result.issues.numWarnings, messages: result.issues.messages });
    }
  }
  await writeFile(path.join(directory, 'validation.json'), JSON.stringify(results, null, 2) + '\n');
  const errorCount = results.reduce((sum, result) => sum + result.errors.length, 0);
  console.log(`${results.length} terrain GLBs: ${errorCount} errors; ${results.reduce((sum, result) => sum + result.warnings, 0)} warnings.`);
  assert.equal(errorCount, 0, 'Terrain technical validation failed; inspect validation.json');
  return { report, results, evidence: { buildSha256: sha(reportBytes), sourceSha256: sha(sourceBytes), models } };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) await validateTerrain();

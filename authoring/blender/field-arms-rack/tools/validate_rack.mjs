/** Current-byte publication gate; --check never writes receipts or metadata. */
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const key = 'frontier_field_arms_rack';
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const local = relative => {
  const resolved = path.resolve(root, relative);
  assert(resolved.startsWith(root + path.sep), `Path leaves package: ${relative}`);
  return resolved;
};
const bytes = relative => fs.readFile(local(relative));
const read = async relative => JSON.parse(await bytes(relative));
const checked = async (relative, expected, size) => {
  const data = await bytes(relative);
  assert.equal(hash(data), expected, `Stale file: ${relative}`);
  if (size !== undefined) assert.equal(data.length, size, `Changed length: ${relative}`);
  return data;
};
const buildPath = `review/${key}_build.json`;
const buildBytes = await bytes(buildPath), build = JSON.parse(buildBytes);
assert.equal(build.key, key);
assert.deepEqual(build.lods.map(lod => lod.level), [0, 1, 2]);
assert(build.sourceFiles.length > 40, 'Retain actual PBR sources and construction tools');
for (const source of build.sourceFiles) await checked(source.path, source.sha256, source.bytes);
const textures = await read('textures/sources.json');
assert.equal(hash(await bytes('tools/make_textures.py')), textures.generatorSha256);
for (const [relative, texture] of Object.entries(textures.textures)) await checked(relative, texture.sha256);
const masterAudit = await read('review/master-audit.json');
assert(masterAudit.passed); assert.equal(masterAudit.records.length, 6);
assert.equal(masterAudit.toolSha256, hash(await bytes('tools/audit_masters.py')));
const construction = await read('review/construction-contacts.json');
assert(construction.passed); assert.equal(construction.records.length, 3);
assert.equal(construction.toolSha256, hash(await bytes('tools/inspect_construction.py')));
for (const record of construction.records) {
  assert.equal(record.sourceMasterSha256, build.lods[record.level].sourceMasterSha256);
  assert.equal(record.modelSha256, build.lods[record.level].sha256);
  assert(record.contacts.length >= 21 && record.contacts.every(contact => contact.passed));
}

function accessor(doc, bin, index) {
  const item = doc.accessors[index], view = doc.bufferViews[item.bufferView];
  assert.equal(item.componentType, 5126, 'Float attribute required');
  const components = { VEC2: 2, VEC3: 3, VEC4: 4 }[item.type];
  assert(components);
  const stride = view.byteStride ?? components * 4;
  const offset = (view.byteOffset ?? 0) + (item.byteOffset ?? 0);
  return Array.from({ length: item.count }, (_, i) => Array.from({ length: components }, (_, j) => bin.readFloatLE(offset + i * stride + j * 4)));
}

const records = [];
for (const lod of build.lods) {
  const data = await checked(`runtime/${lod.model}`, lod.sha256, lod.bytes);
  assert.equal(data.readUInt32LE(0), 0x46546c67); assert.equal(data.readUInt32LE(8), data.length);
  const jsonLength = data.readUInt32LE(12), doc = JSON.parse(data.subarray(20, 20 + jsonLength));
  const bin = data.subarray(28 + jsonLength);
  assert.equal(doc.materials.length, 5, 'Five deliberate material sets');
  assert.equal(doc.meshes.length, 5, 'Five material batches, no hidden construction meshes');
  assert(!doc.animations?.length && !doc.skins?.length, 'Static workshop asset');
  assert(doc.images.length >= 15 && doc.images.every(image => image.uri === undefined && Number.isInteger(image.bufferView)), 'Embedded runtime PBR images');
  for (const material of doc.materials) {
    assert(material.pbrMetallicRoughness?.baseColorTexture);
    assert(material.pbrMetallicRoughness?.metallicRoughnessTexture);
    assert(material.normalTexture);
  }
  let triangles = 0, vertices = 0;
  for (const mesh of doc.meshes) for (const primitive of mesh.primitives) {
    assert.equal(primitive.mode ?? 4, 4);
    triangles += doc.accessors[primitive.indices].count / 3;
    const normals = accessor(doc, bin, primitive.attributes.NORMAL);
    const tangents = accessor(doc, bin, primitive.attributes.TANGENT);
    const uv = accessor(doc, bin, primitive.attributes.TEXCOORD_0);
    assert.equal(normals.length, tangents.length); assert.equal(uv.length, normals.length);
    vertices += normals.length;
    for (let i = 0; i < normals.length; i++) {
      const n = normals[i], t = tangents[i];
      assert([...n, ...t, ...uv[i]].every(Number.isFinite), `${lod.model}: finite PBR basis`);
      assert(Math.abs(Math.hypot(...n) - 1) < .001, `${lod.model}: unit normal`);
      assert(Math.abs(Math.hypot(...t.slice(0, 3)) - 1) < .001, `${lod.model}: unit tangent`);
      assert(Math.abs(n.reduce((sum, value, j) => sum + value * t[j], 0)) < .001, `${lod.model}: orthogonal tangent`);
      assert(Math.abs(t[3]) === 1);
    }
  }
  assert.equal(triangles, lod.triangles);
  if (lod.level) assert(triangles < build.lods[lod.level - 1].triangles * .75, 'Real authored LOD reduction');
  for (const kind of ['sourceMaster', 'master']) {
    await checked(lod[kind], lod[`${kind}Sha256`]);
    const master = masterAudit.records.find(record => record.level === lod.level && record.kind === kind);
    assert(master); assert.equal(master.sha256, lod[`${kind}Sha256`]); assert(master.packedImages >= 15);
    for (const field of ['boundary', 'multi', 'loose']) assert.equal(master.audit[field], 0, `${kind} ${lod.level} ${field}`);
  }
  const review = await read(`review/${key}_lod${lod.level}_reimport.json`);
  assert.equal(review.sha256, lod.sha256, 'Preview must show final exact GLB');
  assert.equal(review.reviewerSha256, hash(await bytes('tools/review_rack.py')));
  assert.equal(review.audit.triangles, triangles);
  for (const field of ['boundary', 'multi', 'loose']) assert.equal(review.audit[field], 0, `Imported ${lod.level} ${field}`);
  for (const view of lod.level ? ['neutral', 'gameplay'] : ['neutral', 'gameplay', 'detail', 'joinery', 'rear']) assert(review.views[view], `Missing ${view}`);
  for (const view of Object.values(review.views)) await checked(`review/${view.image}`, view.sha256);
  const report = await validator.validateBytes(new Uint8Array(data), { uri: lod.model });
  assert.equal(report.issues.numErrors, 0); assert.equal(report.issues.numWarnings, 0);
  records.push({ level: lod.level, model: lod.model, sha256: lod.sha256, bytes: data.length, triangles, vertices, materials: doc.materials.length, errors: 0, warnings: 0 });
}

const contract = (await read('builder-contract.json')).assets[key];
assert.equal(contract.sourceMasterSha256, build.lods[0].sourceMasterSha256);
assert.equal(contract.colliderSpace, 'model'); assert.equal(contract.cameraSolid, true);
assert.deepEqual(contract.defaultScale, { x: 1, y: 1, z: 1 });
assert.deepEqual(contract.walkableSurfaces, []);
const master = masterAudit.records.find(record => record.level === 0 && record.kind === 'sourceMaster');
assert.equal(master.feet.length, 2);
assert(master.feet.every(foot => Math.abs(foot.minimumZ) < 1e-6 && foot.contactVertices >= 4));
assert.equal(contract.colliders.length, contract.collisionMeasurements.length);
assert.equal(contract.colliders.length, master.collisionMeasurements.length);
const lo = contract.boundsYUp.minimum, hi = contract.boundsYUp.maximum;
assert.equal(lo[1], 0); assert(Math.abs(contract.footprint.width - (hi[0] - lo[0])) < 1e-6);
assert(Math.abs(contract.footprint.depth - (hi[2] - lo[2])) < 1e-6);
const front = contract.workingFront;
for (const [index, collider] of contract.colliders.entries()) {
  const measured = contract.collisionMeasurements[index].boundsZUp;
  const expected = { x: (measured.minimum[0] + measured.maximum[0]) / 2,
    z: -(measured.minimum[1] + measured.maximum[1]) / 2, width: measured.maximum[0] - measured.minimum[0],
    depth: measured.maximum[1] - measured.minimum[1], minY: Math.max(0, measured.minimum[2]), maxY: measured.maximum[2] };
  assert.deepEqual(collider, expected, 'Each collider derives from its named structural mass');
  assert.equal(master.collisionMeasurements[index].name, contract.collisionMeasurements[index].name);
  const intersects = Math.max(collider.x - collider.width / 2, front.minimum[0]) < Math.min(collider.x + collider.width / 2, front.maximum[0])
    && Math.max(collider.z - collider.depth / 2, front.minimum[2]) < Math.min(collider.z + collider.depth / 2, front.maximum[2]);
  assert(!intersects, 'Structural collider intrudes into reserved working front');
  for (let z = 1.02; z < 2.5; z += .05) {
    const dx = Math.max(0, Math.abs(collider.x) - collider.width / 2), dz = Math.max(0, Math.abs(collider.z - z) - collider.depth / 2);
    assert(Math.hypot(dx, dz) >= .5, 'Half-metre actor cannot approach station standing point');
  }
}
assert.deepEqual(contract.approachSource, { minimum: [front.minimum[0], -front.maximum[2], front.minimum[1]], maximum: [front.maximum[0], -front.minimum[2], front.maximum[1]] });
const result = { passed: true, key, buildSha256: hash(buildBytes), validationToolSha256: hash(await fs.readFile(fileURLToPath(import.meta.url))), records,
  colliders: contract.colliders.length, limitations: ['Static racked weapons; no pickup or equipment interaction claimed.', 'Placement and gameplay acceptance are outside this authoring gate.'] };
if (process.argv.includes('--check')) {
  assert.deepEqual(await read('validation.json'), result, 'Current validation receipt is stale');
} else {
  await fs.writeFile(local('validation.json'), JSON.stringify(result, null, 2) + '\n');
}
console.log(JSON.stringify(result, null, 2));

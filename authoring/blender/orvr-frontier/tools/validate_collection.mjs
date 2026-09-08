/** Audit actual exported binaries and bind the report to their hashes. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';
import { inspectMechanics } from './inspect_mechanical_glb.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sourceBytes = await fs.readFile(path.join(root, 'source/frontier_collection.json'));
const source = JSON.parse(sourceBytes);
const digest = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
const issues = [];
const assets = [];
for (const [assetId, definition] of Object.entries(source.assets)) {
  const record = { assetId, lods: [], limitations: definition.limitations };
  const buildFile = path.join(root, 'review', `${assetId}_build.json`);
  let build;
  try { build = JSON.parse(await fs.readFile(buildFile, 'utf8')); }
  catch { issues.push(`${assetId}: missing measured build report`); continue; }
  if (build.source_sha256 !== digest(sourceBytes)) issues.push(`${assetId}: stale source hash`);
  if (build.builder_sha256 !== digest(await fs.readFile(path.join(root, 'tools/build_collection.py')))) issues.push(`${assetId}: stale builder hash`);
  if (build.mechanics_sha256 !== digest(await fs.readFile(path.join(root, 'tools/mechanical_animation.py')))) issues.push(`${assetId}: stale mechanical action source`);
  if (build.paint_record_sha256 !== digest(await fs.readFile(path.join(root, 'textures/paint_records.json')))) issues.push(`${assetId}: stale paint records`);
  for (const [texture, hash] of Object.entries(build.source_texture_sha256 ?? {})) {
    if (hash !== digest(await fs.readFile(path.join(root, texture)))) issues.push(`${assetId}: source texture changed: ${texture}`);
  }
  const master = await fs.readFile(path.join(root, build.master.replaceAll('\\', '/')));
  if (digest(master) !== build.master_sha256) issues.push(`${assetId}: master hash mismatch`);
  if (!build.animated_master || digest(await fs.readFile(path.join(root, build.animated_master.replaceAll('\\', '/')))) !== build.animated_master_sha256) issues.push(`${assetId}: missing or stale animated master`);
  for (const level of [0, 1, 2]) {
    const filename = `${assetId}_lod${level}.glb`;
    let buffer;
    try { buffer = await fs.readFile(path.join(root, 'runtime', filename)); }
    catch { issues.push(`${assetId}: missing LOD${level}`); continue; }
    const measured = build.lods.find((lod) => lod.level === level);
    if (!measured || measured.sha256 !== digest(buffer)) issues.push(`${filename}: missing or stale build measurements`);
    const refinement = measured?.lod_refinement;
    if (refinement) {
      if (refinement.tool_sha256 !== digest(await fs.readFile(path.join(root, refinement.tool)))) issues.push(`${filename}: stale LOD refinement source`);
      if (refinement.master_sha256 !== digest(await fs.readFile(path.join(root, refinement.master.replaceAll('\\', '/'))))) issues.push(`${filename}: stale LOD refinement master`);
    }
    const projection = measured?.normal_projection_repair;
    if (projection) {
      for (const image of projection.maps) {
        if (image.input_image_sha256 !== digest(await fs.readFile(path.join(root, image.original_map)))) issues.push(`${filename}: original normal projection pixels no longer match their recorded hash`);
      }
      const currentTool = await fs.readFile(path.join(root, 'tools/repair_normal_projection.py'));
      const archivedTool = path.join(root, 'review/tool_sources', `repair_normal_projection_${projection.tool_sha256}.py`);
      if (projection.tool_sha256 !== digest(currentTool)) {
        try {
          if (projection.tool_sha256 !== digest(await fs.readFile(archivedTool))) issues.push(`${filename}: archived normal repair source hash mismatch`);
        } catch { issues.push(`${filename}: missing historical normal repair source`); }
      }
    }
    const tangent = measured?.degenerate_tangent_repair;
    if (tangent) {
      if (tangent.tool_sha256 !== digest(await fs.readFile(path.join(root, 'tools/repair_degenerate_tangents.py')))) issues.push(`${filename}: stale tangent repair source`);
      if (tangent.output_glb_sha256 !== digest(buffer)) issues.push(`${filename}: stale tangent repair output`);
      if (projection && tangent.input_glb_sha256 !== projection.output_glb_sha256) issues.push(`${filename}: broken projection/tangent provenance chain`);
    } else if (projection && projection.output_glb_sha256 !== digest(buffer)) issues.push(`${filename}: stale projection repair output`);
    if (buffer.readUInt32LE(0) !== 0x46546c67 || buffer.readUInt32LE(4) !== 2 || buffer.readUInt32LE(8) !== buffer.length) issues.push(`${filename}: invalid GLB header`);
    const jsonLength = buffer.readUInt32LE(12);
    const document = JSON.parse(buffer.subarray(20, 20 + jsonLength).toString('utf8'));
    for (const issue of inspectMechanics(document, measured ?? {})) issues.push(`${filename}: ${issue}`);
    const nodes = new Set((document.nodes ?? []).map((node) => node.name));
    for (const component of measured?.rigid_nodes ?? []) if (!nodes.has(component.node)) issues.push(`${filename}: missing mechanical node ${component.node}`);
    const meshTriangles = (document.meshes ?? []).map((mesh) => mesh.primitives.reduce((sum, primitive) => sum + (primitive.indices === undefined ? document.accessors[primitive.attributes.POSITION].count : document.accessors[primitive.indices].count) / 3, 0));
    const sceneTriangles = (document.nodes ?? []).reduce((sum, node) => sum + (node.mesh === undefined ? 0 : meshTriangles[node.mesh]), 0);
    if (measured && measured.triangles !== sceneTriangles) issues.push(`${filename}: measured scene triangle count changed`);
    if (measured && measured.materials !== (document.materials ?? []).length) issues.push(`${filename}: measured material count changed`);
    for (const material of document.materials ?? []) {
      if (!material.pbrMetallicRoughness?.baseColorTexture || !material.pbrMetallicRoughness?.metallicRoughnessTexture || !material.normalTexture || !material.occlusionTexture) issues.push(`${filename}: missing baked PBR channel`);
    }
    if ((document.images ?? []).some((image) => image.uri)) issues.push(`${filename}: unexpected external image dependency`);
    if ((document.meshes ?? []).some((mesh) => mesh.primitives.some((primitive) => primitive.attributes.TANGENT === undefined || primitive.attributes.TEXCOORD_0 === undefined))) issues.push(`${filename}: missing UVs or tangents`);
    const result = await validator.validateBytes(new Uint8Array(buffer), { uri: filename, maxIssues: 1000 });
    if (result.issues.numErrors > 0) issues.push(`${filename}: ${result.issues.numErrors} Khronos validation errors`);
    await fs.writeFile(path.join(root, 'review', `${filename}.validation.json`), `${JSON.stringify(result, null, 2)}\n`);
    record.lods.push({ level, path: `runtime/${filename}`, sha256: digest(buffer), bytes: buffer.length, triangles: sceneTriangles, uniqueMeshTriangles: meshTriangles.reduce((sum, count) => sum + count, 0), errors: result.issues.numErrors, warnings: result.issues.numWarnings });
  }
  if (record.lods.length === 3 && !(record.lods[0].triangles > record.lods[1].triangles && record.lods[1].triangles > record.lods[2].triangles)) issues.push(`${assetId}: LOD triangle counts must strictly decrease`);
  assets.push(record);
}
const report = { sourceSha256: digest(sourceBytes), passed: issues.length === 0, issues, assets, visualApproval: false, note: 'Technical validation does not establish model quality or authorize runtime promotion.' };
await fs.writeFile(path.join(root, 'review', 'validation.json'), `${JSON.stringify(report, null, 2)}\n`);
const candidates = assets.map((asset) => ({ assetId: asset.assetId, approved: false, qcPassed: issues.length === 0, validationErrors: asset.lods.reduce((count, lod) => count + lod.errors, 0), stagedDirectory: 'authoring/blender/orvr-frontier/runtime', lods: asset.lods.map((lod) => ({ level: lod.level, model: path.basename(lod.path), sha256: lod.sha256 })), limitations: asset.limitations, note: 'Internal visual acceptance is still required; this file does not publish or approve the asset.' }));
await fs.writeFile(path.join(root, 'review', 'registry_candidates.json'), `${JSON.stringify({ assets: candidates }, null, 2)}\n`);
console.log(JSON.stringify(report, null, 2));
if (issues.length) process.exitCode = 1;

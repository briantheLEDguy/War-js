/** Verify delivered anatomy and motion; technical success never grants visual approval. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import validator from 'gltf-validator';
import { embeddedPngEvidence } from './texture_evidence.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));
const source = await read(path.join(root, 'source/anatomy.json'));
const resolve = key => ({ ...(source.assets[key].inherits ? resolve(source.assets[key].inherits) : {}), ...source.assets[key] });
const selected = process.argv.find(a => a.startsWith('--assets='))?.slice(9).split(',') ?? Object.keys(source.assets);
const widths = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 };
const formats = { 5120: ['readInt8', 1, 127], 5121: ['readUInt8', 1, 255], 5122: ['readInt16LE', 2, 32767],
  5123: ['readUInt16LE', 2, 65535], 5125: ['readUInt32LE', 4, 4294967295], 5126: ['readFloatLE', 4, 1] };
function accessor(doc, binary, index) {
  const a = doc.accessors[index], view = doc.bufferViews[a.bufferView];
  const [method, bytes, divisor] = formats[a.componentType], width = widths[a.type], stride = view.byteStride ?? width * bytes;
  return Array.from({ length: a.count }, (_, row) => Array.from({ length: width }, (_, col) => {
    const value = binary[method]((view.byteOffset ?? 0) + (a.byteOffset ?? 0) + row * stride + col * bytes);
    return a.normalized ? Math.max(-1, value / divisor) : value;
  }));
}
const reports = [];
for (const kind of selected) {
  const definition = resolve(kind), asset = `frontier_sunmeadow_${kind}`, issues = [], lods = [];
  const fail = message => issues.push(message);
  let build;
  try { build = await read(path.join(root, 'review', `${asset}_build.json`)); }
  catch { reports.push({ asset, passed: false, issues: ['No authored build exists'], visualApproval: false }); continue; }
  for (const [key, file] of [['source_sha256', 'source/anatomy.json'], ['builder_sha256', 'tools/build_fauna.py'],
    ['rig_helper_sha256', 'tools/quadruped_rig.py'], ['motion_source_sha256', 'tools/motion.py'], ['master_sha256', build.master]]) {
    if (build[key] !== sha(await fs.readFile(path.join(root, file)))) fail(`Changed source/master: ${file}`);
  }
  const sourceFiles = ['source/anatomy.json', ...['build_fauna.py', 'quadruped_rig.py', 'motion.py', 'bird_geometry.py',
    'stitched_skin.py', 'atlas_checks.py', 'surface_detail.py', 'texture_detail.py', 'texture_lods.py', 'gait_curves.py'].map(name => `tools/${name}`)];
  for (const file of sourceFiles) if (build.source_files?.[file] !== sha(await fs.readFile(path.join(root, file)))) fail(`Changed or unsigned build dependency: ${file}`);
  for (const [file, digest] of Object.entries(build.source_files ?? {})) if (digest !== sha(await fs.readFile(path.join(root, file)))) fail(`Changed recorded source: ${file}`);
  for (const channel of ['basecolor', 'normal', 'orm']) {
    const file = `textures/${kind}_${channel}.png`;
    if (build.texture_sources?.[file] !== sha(await fs.readFile(path.join(root, file)))) fail(`Changed or unsigned texture source: ${file}`);
  }
  for (const [file, digest] of Object.entries(build.texture_sources ?? {})) if (digest !== sha(await fs.readFile(path.join(root, file)))) fail(`Changed recorded texture: ${file}`);
  if (!build.cage || build.cage_sha256 !== sha(await fs.readFile(path.join(root, build.cage)))) fail('Changed or unsigned editable cage');
  if (build.lods.length !== 3) fail('Exactly three authored LODs required');
  const budgets = kind === 'skylark' ? [22000, 12000, 5000] : kind === 'brown_hare' ? [35000, 18000, 7000] : [65000, 30000, 11000];
  for (const lod of build.lods) {
    const bytes = await fs.readFile(path.join(root, 'runtime', lod.model)), hash = sha(bytes);
    if (hash !== lod.sha256) fail(`${lod.model}: changed binary`);
    const jsonLength = bytes.readUInt32LE(12), doc = JSON.parse(bytes.subarray(20, 20 + jsonLength)), binary = bytes.subarray(28 + jsonLength);
    const result = await validator.validateBytes(new Uint8Array(bytes), { uri: lod.model, maxIssues: 2000 });
    // Revalidation time is not part of the reviewed geometry. Bind the
    // deterministic diagnostic to its actual binary; approval carries its date.
    delete result.validatedAt;
    result.modelSha256 = hash;
    await fs.writeFile(path.join(root, 'review', `${lod.model}.validation.json`), JSON.stringify(result, null, 2) + '\n');
    if (result.issues.numErrors || result.issues.numWarnings) fail(`${lod.model}: Khronos ${result.issues.numErrors} errors/${result.issues.numWarnings} warnings`);
    if (doc.images.some(image => image.uri)) fail(`${lod.model}: unsigned external images`);
    let textureEvidence = [];
    try {
      textureEvidence = embeddedPngEvidence(doc, binary);
      const width = 4096 >> lod.level, height = 2048 >> lod.level;
      if (textureEvidence.length !== 3 || textureEvidence.some(image => image.width !== width || image.height !== height)) fail(`${lod.model}: actual atlas sizes do not match the descending LOD contract`);
      if (textureEvidence.reduce((sum, image) => sum + image.rgba8MipBytes, 0) !== lod.estimated_rgba8_mipped_bytes) fail(`${lod.model}: inaccurate decoded texture memory evidence`);
    } catch (error) { fail(`${lod.model}: ${error.message}`); }
    if (doc.materials.length > 2) fail(`${lod.model}: excessive material count`);
    for (const material of doc.materials) {
      const pbr = material.pbrMetallicRoughness;
      if (!pbr?.baseColorTexture || !pbr.metallicRoughnessTexture || !material.normalTexture || !material.occlusionTexture) fail(`${lod.model}: incomplete PBR`);
      if (material.alphaMode && material.alphaMode !== 'OPAQUE') fail(`${lod.model}: transparent proxy surface`);
    }
    const primitives = doc.meshes.flatMap(mesh => mesh.primitives); let triangles = 0, maximumWeightError = 0, degenerate = 0;
    if (!doc.skins?.length || doc.skins[0].joints.length < 20) fail(`${lod.model}: missing anatomical rig`);
    for (const primitive of primitives) {
      for (const attribute of ['POSITION', 'NORMAL', 'TANGENT', 'TEXCOORD_0', 'COLOR_0', 'JOINTS_0', 'WEIGHTS_0']) {
        if (primitive.attributes[attribute] === undefined) fail(`${lod.model}: missing ${attribute}`);
      }
      const positions = accessor(doc, binary, primitive.attributes.POSITION), indices = accessor(doc, binary, primitive.indices).flat(); triangles += indices.length / 3;
      if (positions.some(point => point.some(value => !Number.isFinite(value)))) fail(`${lod.model}: nonfinite surface`);
      for (let i = 0; i < indices.length; i += 3) {
        const a = positions[indices[i]], b = positions[indices[i + 1]], c = positions[indices[i + 2]];
        const u = b.map((v, k) => v - a[k]), v = c.map((n, k) => n - a[k]);
        const cross = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]];
        if (Math.hypot(...cross) < 1e-12) degenerate++;
      }
      const weights = accessor(doc, binary, primitive.attributes.WEIGHTS_0), joints = accessor(doc, binary, primitive.attributes.JOINTS_0);
      for (let i = 0; i < weights.length; i++) {
        maximumWeightError = Math.max(maximumWeightError, Math.abs(weights[i].reduce((a, b) => a + b, 0) - 1));
        if (weights[i].some(value => value < 0 || !Number.isFinite(value)) || joints[i].some(j => j >= doc.skins[0].joints.length)) fail(`${lod.model}: invalid skin influence`);
      }
    }
    if (degenerate) fail(`${lod.model}: ${degenerate} degenerate delivery triangles`);
    if (maximumWeightError > .001) fail(`${lod.model}: weights do not normalize`);
    if (triangles !== lod.triangles || triangles > budgets[lod.level]) fail(`${lod.model}: invalid triangle count/budget ${triangles}`);
    if (bytes.length > 12 * 1024 * 1024) fail(`${lod.model}: exceeded 12 MiB delivery budget`);
    const clips = doc.animations ?? [];
    if (JSON.stringify(clips.map(c => c.name).sort()) !== JSON.stringify([...definition.clips].sort())) fail(`${lod.model}: required clips missing or renamed`);
    for (const clip of clips) {
      const durations = clip.samplers.map(s => accessor(doc, binary, s.input).at(-1)[0]);
      const expected = build.motion.find(m => m.clip === clip.name);
      if (!expected || Math.abs(Math.max(...durations) - expected.duration) > .002) fail(`${lod.model}: ${clip.name} has wrong duration`);
      for (const channel of clip.channels) if (doc.nodes[channel.target.node].name === 'root' && channel.target.path === 'translation') {
        const points = accessor(doc, binary, clip.samplers[channel.sampler].output);
        if (points.some(point => point.some(value => Math.abs(value) > 1e-6))) fail(`${lod.model}: clip moves authority root`);
      }
    }
    try {
      const motion = await read(path.join(root, 'review', `${asset}_lod${lod.level}_motion_inspection.json`));
      if (motion.model_sha256 !== hash) fail(`${lod.model}: stale reimport motion inspection`);
      if (motion.build_sha256 !== sha(await fs.readFile(path.join(root, 'review', `${asset}_build.json`)))) fail(`${lod.model}: stale motion authority contract`);
      if (motion.sampling !== 'exported_keys_and_midpoints'
        || motion.inspector_sha256 !== sha(await fs.readFile(path.join(root, 'tools/inspect_motion.py')))
        || motion.sampling_helper_sha256 !== sha(await fs.readFile(path.join(root, 'tools/glb_sampling.py')))) fail(`${lod.model}: stale or incomplete motion sampling method`);
      if (JSON.stringify(motion.clips.map(c => c.name).sort()) !== JSON.stringify([...definition.clips].sort())) fail(`${lod.model}: incomplete reimport clip inspection`);
      for (const clip of motion.clips) {
        if (!(clip.exported_key_count >= 2) || clip.inspected_sample_count !== clip.exported_key_count * 2 - 1
          || clip.sample_times_seconds?.length !== clip.inspected_sample_count) fail(`${lod.model}: ${clip.name} missing key/subframe samples`);
        if (clip.maximum_root_translation > 1e-6) fail(`${lod.model}: root displacement in reimport`);
        if (clip.maximum_edge_stretch > 4 || clip.p99_edge_stretch > 1.8) fail(`${lod.model}: ${clip.name} skin distortion exceeds review gate`);
        if (!['death', 'attack', 'hit'].includes(clip.name) && clip.loop_vertex_difference_m > .002) fail(`${lod.model}: ${clip.name} loop seam`);
        if (clip.bounds_blender.min[2] < -.012) fail(`${lod.model}: ${clip.name} penetrates ground`);
        if (build.motion.find(c => c.clip === clip.name)?.locomotion && (!clip.locomotion?.planted_foot_samples
          || clip.locomotion.maximum_plant_error_m > .006)) fail(`${lod.model}: ${clip.name} exported foot plant deviates over 6 mm from authored ground trajectory`);
      }
    } catch { fail(`${lod.model}: actual reimport motion inspection required`); }
    lods.push({ ...lod, triangles, maximumWeightError, degenerateTriangles: degenerate, actualEmbeddedTextures: textureEvidence,
      validationErrors: result.issues.numErrors, validationWarnings: result.issues.numWarnings });
  }
  if (lods.length === 3 && !(lods[0].triangles > lods[1].triangles && lods[1].triangles > lods[2].triangles)) fail('LOD triangle counts must decrease');
  const report = { asset, passed: issues.length === 0, issues, lods, visualApproval: false };
  reports.push(report); await fs.writeFile(path.join(root, 'review', `${asset}_technical.json`), JSON.stringify(report, null, 2) + '\n');
}
console.log(JSON.stringify(reports.map(r => ({ asset: r.asset, passed: r.passed, issues: r.issues })), null, 2));
if (reports.some(r => !r.passed)) process.exitCode = 1;

/** Evidence comes from the actual delivered GLBs and their matching clean imports. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

export const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
export const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));
export const fileSha = async file => sha(await fs.readFile(file));
export function localPath(root, relative) {
  const target = path.resolve(root, relative);
  assert(target.startsWith(path.resolve(root) + path.sep), `Evidence path escapes package: ${relative}`);
  return target;
}
export async function verifyFiles(root, files) {
  for (const [file, digest] of Object.entries(files)) assert.equal(await fileSha(localPath(root, file)), digest, `Changed evidence: ${file}`);
}
export function requireViews(renders, clips) {
  for (let lod = 0; lod < 3; lod++) assert(renders.some(r => r.level === lod && r.state === 'rest' && r.view === 'full'), `LOD${lod} resting import missing`);
  assert(renders.some(r => r.level === 0 && r.state === 'rest' && r.view === 'head'), 'Close anatomy/material import missing');
  for (const clip of clips) {
    const phases = new Set(renders.filter(r => r.level === 0 && r.view === 'profile' && r.state.startsWith(`${clip}@`)).map(r => Number(r.state.split('@')[1])));
    const minimum = ['walk', 'run', 'fly'].includes(clip) ? 8 : clip === 'idle' ? 2 : 4;
    assert(phases.size >= minimum && [...phases].every(p => p >= 0 && p <= 1), `${clip}: incomplete actual cycle views`);
    if (minimum === 8) assert.equal(new Set([...phases].map(p => Math.min(7, Math.floor(p * 8)))).size, 8, `${clip}: cycle phases do not cover its duration`);
    else assert(Math.max(...phases) - Math.min(...phases) >= (clip === 'idle' ? .4 : .7), `${clip}: cycle phases are clustered`);
    if (['death', 'attack', 'hit'].includes(clip)) assert(phases.has(1), `${clip}: final pose missing`);
  }
}

export async function collectEvidence(root, asset, clips) {
  const buildName = `review/${asset}_build.json`, build = await read(localPath(root, buildName));
  const buildHash = await fileSha(localPath(root, buildName));
  const files = { ...build.source_files, ...build.texture_sources, [buildName]: buildHash,
    [build.master]: build.master_sha256, [build.cage]: build.cage_sha256 };
  const technicalName = `review/${asset}_technical.json`, technical = await read(localPath(root, technicalName));
  assert(technical.passed && technical.lods.length === 3, 'Technical export validation must pass before review');
  files[technicalName] = await fileSha(localPath(root, technicalName));
  for (const lod of build.lods) {
    files[`runtime/${lod.model}`] = lod.sha256;
    const inspection = `review/${asset}_lod${lod.level}_motion_inspection.json`, report = await read(localPath(root, inspection));
    assert.equal(report.model_sha256, lod.sha256, 'Stale actual motion report');
    assert.equal(report.build_sha256, buildHash, 'Stale movement contract');
    files[inspection] = await fileSha(localPath(root, inspection));
    files[`review/${lod.model}.validation.json`] = await fileSha(localPath(root, `review/${lod.model}.validation.json`));
  }
  const renderName = `review/${asset}_renders.json`, receipts = await read(localPath(root, renderName));
  const renders = receipts.renders;
  requireViews(renders, clips);
  const ids = new Set();
  for (const render of renders) {
    const id = `${render.level}/${render.state}/${render.view}`;
    assert(!ids.has(id), `Duplicate review view: ${id}`); ids.add(id);
    assert.equal(render.build_sha256, buildHash, 'Render displays a previous authored build');
    assert.equal(render.model_sha256, build.lods[render.level].sha256, 'Render displays a previous model');
    assert.equal(render.reviewer_source_sha256, await fileSha(localPath(root, 'tools/reimport_review.py')), 'Changed render source');
    await verifyFiles(root, render.authored_files);
    files[render.image.replaceAll('\\', '/')] = render.image_sha256;
  }
  files[renderName] = await fileSha(localPath(root, renderName));
  files['tools/reimport_review.py'] = await fileSha(localPath(root, 'tools/reimport_review.py'));
  files['tools/inspect_motion.py'] = await fileSha(localPath(root, 'tools/inspect_motion.py'));
  files['tools/glb_sampling.py'] = await fileSha(localPath(root, 'tools/glb_sampling.py'));
  files['tools/validate_fauna.mjs'] = await fileSha(localPath(root, 'tools/validate_fauna.mjs'));
  const compositeName = `review/${asset}_composites.json`, composites = await read(localPath(root, compositeName));
  assert.equal(composites.build_sha256, buildHash, 'Stale contact sheets');
  assert.equal(composites.composer_sha256, await fileSha(localPath(root, 'tools/compose_review.py')), 'Changed contact composer');
  assert(composites.composites.some(c => c.kind === 'lod_contact'), 'Three-LOD contact sheet missing');
  for (const composite of composites.composites) {
    for (const input of composite.inputs) assert(renders.some(r => r.image === input.image && r.image_sha256 === input.image_sha256 && r.model_sha256 === input.model_sha256), 'Contact sheet contains an unsigned/stale image');
    files[composite.image] = composite.image_sha256;
  }
  files[compositeName] = await fileSha(localPath(root, compositeName));
  files['tools/compose_review.py'] = composites.composer_sha256;
  await verifyFiles(root, files);
  return { asset, buildHash, files: Object.fromEntries(Object.entries(files).sort(([a], [b]) => a.localeCompare(b))),
    modelHashes: build.lods.map(l => l.sha256), clips: [...clips], defaultAnimation: 'idle', units: 'metres', runtimeScale: 1 };
}

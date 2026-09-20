/** Bind portable corrective delivery to its literal GLBs and editable master. */
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileSha, localPath, read, requireViews, verifyFiles } from './review_evidence.mjs';

export function candidatePath(root, relative) {
  const target = localPath(root, relative);
  const directory = path.join(path.resolve(root), 'review', 'candidates') + path.sep;
  assert(target.startsWith(directory), 'Corrective delivery must stay inside review/candidates');
  return path.relative(root, target).replaceAll('\\', '/');
}

export function requireCandidateViews(renders, clips) {
  requireViews(renders, clips);
  for (let level = 0; level < 3; level++) {
    for (const state of ['rest', 'run@0.35', 'graze@0.5']) {
      assert(renders.some(r => r.level === level && r.state === state && r.view === 'full'), `LOD${level}: ${state} comparison missing`);
    }
  }
}

export async function collectCandidateDelivery(root, asset, clips, relative, { standingApproval = false } = {}) {
  const directory = candidatePath(root, relative);
  const buildName = `review/${asset}_build.json`, buildHash = await fileSha(localPath(root, buildName));
  const base = await read(localPath(root, buildName));
  const metadataName = `${directory}/candidate.json`, candidate = await read(localPath(root, metadataName));
  assert.equal(candidate.base_build_sha256, buildHash, 'Corrective candidate belongs to a different base build');
  assert.deepEqual(candidate.lods.map(lod => lod.level), [0, 1, 2], 'Three ordered corrective LODs required');
  const files = { ...base.source_files, ...base.texture_sources, [buildName]: buildHash,
    [base.master]: base.master_sha256, [base.cage]: base.cage_sha256,
    [metadataName]: await fileSha(localPath(root, metadataName)) };
  assert(candidate.master && candidate.master_sha256, 'Editable corrective master required');
  assert.equal(path.basename(candidate.master), candidate.master, 'Corrective master must be a local filename');
  files[`${directory}/${candidate.master}`] = candidate.master_sha256;
  for (const [name, digest] of Object.entries(candidate.sources)) {
    assert.equal(path.basename(name), name, 'Corrective source must be a tools filename');
    files[`tools/${name}`] = digest;
  }
  const lods = base.lods.map(baseLod => {
    const corrected = candidate.lods[baseLod.level];
    assert.equal(corrected.model, baseLod.model, 'Corrective LOD filename changed');
    assert.notEqual(corrected.sha256, baseLod.sha256, 'Corrective delivery silently substituted the uncorrected base');
    // Retain the literal base exports used by static-normal preservation too.
    files[`runtime/${baseLod.model}`] = baseLod.sha256;
    files[`${directory}/${corrected.model}`] = corrected.sha256;
    return { ...baseLod, sha256: corrected.sha256, bytes: corrected.bytes, correctiveModes: corrected.modes };
  });
  const technicalName = `${directory}/${asset}_technical.json`, technical = await read(localPath(root, technicalName));
  assert(technical.passed && technical.lods.length === 3, 'Corrective technical validation must pass');
  files[technicalName] = await fileSha(localPath(root, technicalName));
  const helper = await fileSha(localPath(root, 'tools/imported_actions.py'));
  for (const lod of lods) {
    assert.equal(technical.lods[lod.level].sha256, lod.sha256, 'Technical report displays an older candidate');
    const motionName = `${directory}/${asset}_lod${lod.level}_motion_inspection.json`;
    const motion = await read(localPath(root, motionName));
    assert.equal(motion.model_sha256, lod.sha256, 'Stale corrective motion report');
    assert.equal(motion.build_sha256, buildHash, 'Stale corrective movement contract');
    assert.equal(motion.imported_action_helper_sha256, helper, 'Stale corrective animation evaluator');
    assert.equal(motion.inspector_sha256, await fileSha(localPath(root, 'tools/inspect_motion.py')), 'Stale corrective motion inspector');
    assert.equal(motion.sampling_helper_sha256, await fileSha(localPath(root, 'tools/glb_sampling.py')), 'Stale corrective sampling helper');
    files[motionName] = await fileSha(localPath(root, motionName));
    const diagnostic = `${directory}/${lod.model}.validation.json`;
    files[diagnostic] = await fileSha(localPath(root, diagnostic));
  }
  const receiptName = `${directory}/render_receipts.json`, receipts = await read(localPath(root, receiptName));
  const reviewer = await fileSha(localPath(root, 'tools/review_candidate.py'));
  // Standing art approval accepts the saved views; it does not manufacture the
  // cancelled cycle renders or relax model/source/motion identity checks.
  const currentRenders = standingApproval ? receipts.renders.filter(render =>
    render.model_sha256 === lods[render.level]?.sha256 && render.reviewer_sha256 === reviewer
      && render.action_helper_sha256 === helper) : receipts.renders;
  if (!standingApproval) requireCandidateViews(currentRenders, clips);
  else {
    for (const level of [0, 1, 2]) assert(currentRenders.some(r => r.level === level && r.state === 'rest' && r.view === 'full'), `LOD${level}: resting preview required`);
    assert(currentRenders.some(r => r.level === 0 && r.view === 'head'), 'Head preview required');
  }
  const identities = new Set();
  const renders = currentRenders.map(render => {
    const identity = `${render.level}/${render.state}/${render.view}/${render.focus ?? ''}`;
    assert(!identities.has(identity), 'Duplicate corrective render'); identities.add(identity);
    assert.equal(render.model_sha256, lods[render.level]?.sha256, 'Render displays another corrective model');
    assert.equal(render.reviewer_sha256, reviewer, 'Corrective renderer changed');
    assert.equal(render.action_helper_sha256, helper, 'Corrective render animation evaluator changed');
    assert.equal(path.basename(render.image), render.image, 'Corrective image must be a local filename');
    const image = `${directory}/${render.image}`;
    files[image] = render.image_sha256;
    return { ...render, image, model: lods[render.level].model };
  });
  files[receiptName] = await fileSha(localPath(root, receiptName));
  for (const name of ['review_candidate.py', 'inspect_motion.py', 'glb_sampling.py', 'imported_actions.py',
    'validate_fauna.mjs', 'texture_evidence.mjs', 'review_evidence.mjs', 'candidate_evidence.mjs', 'publish_fauna.mjs']) {
    files[`tools/${name}`] = await fileSha(localPath(root, `tools/${name}`));
  }
  await verifyFiles(root, files);
  const delivery = { kind: 'corrected_candidate', modelDirectory: directory, reviewDirectory: directory,
    master: `${directory}/${candidate.master}`, masterSha256: candidate.master_sha256 };
  return { build: { ...base, lods, master: delivery.master, master_sha256: delivery.masterSha256 }, technical, renders,
    modelDirectory: directory, reviewDirectory: directory,
    evidence: { asset, buildHash, files: Object.fromEntries(Object.entries(files).sort(([a], [b]) => a.localeCompare(b))),
      modelHashes: lods.map(lod => lod.sha256), clips: [...clips], defaultAnimation: 'idle', units: 'metres', runtimeScale: 1, delivery } };
}

import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { candidatePath, collectCandidateDelivery, requireCandidateViews } from './candidate_evidence.mjs';
import { sha } from './review_evidence.mjs';

const asset = 'frontier_sunmeadow_roe_deer_buck', directory = 'review/candidates/buck';
const clips = ['idle', 'walk', 'run', 'graze'];

async function fixture(run) {
  const root = await fs.mkdtemp(path.join(os.tmpdir(), 'fauna-candidate-'));
  const files = new Map();
  async function write(name, value) {
    const bytes = typeof value === 'string' ? value : JSON.stringify(value);
    await fs.mkdir(path.dirname(path.join(root, name)), { recursive: true });
    await fs.writeFile(path.join(root, name), bytes); files.set(name, bytes); return sha(bytes);
  }
  try {
    for (const name of ['review_candidate.py', 'inspect_motion.py', 'glb_sampling.py', 'imported_actions.py',
      'validate_fauna.mjs', 'texture_evidence.mjs', 'review_evidence.mjs', 'candidate_evidence.mjs', 'publish_fauna.mjs', 'bake_joint_correctives.py']) {
      await write(`tools/${name}`, `source ${name}`);
    }
    const base = { master: 'masters/base.blend', master_sha256: await write('masters/base.blend', 'editable base'),
      cage: 'source/cage.json', cage_sha256: await write('source/cage.json', 'authored cage'), source_files: {}, texture_sources: {}, lods: [] };
    const candidate = { sources: { 'bake_joint_correctives.py': sha(files.get('tools/bake_joint_correctives.py')) },
      master: 'corrected.blend', master_sha256: await write(`${directory}/corrected.blend`, 'editable morph master'), lods: [] };
    for (let level = 0; level < 3; level++) {
      const model = `${asset}_lod${level}.glb`;
      base.lods.push({ level, model, sha256: await write(`runtime/${model}`, `base ${level}`), triangles: 300 - level * 100 });
      candidate.lods.push({ level, model, sha256: await write(`${directory}/${model}`, `corrected ${level}`), modes: 8, bytes: 11 });
    }
    candidate.base_build_sha256 = await write(`review/${asset}_build.json`, base);
    await write(`${directory}/candidate.json`, candidate);
    await write(`${directory}/${asset}_technical.json`, { passed: true, lods: candidate.lods });
    for (const lod of candidate.lods) {
      await write(`${directory}/${asset}_lod${lod.level}_motion_inspection.json`, { model_sha256: lod.sha256,
        build_sha256: candidate.base_build_sha256, imported_action_helper_sha256: sha(files.get('tools/imported_actions.py')),
        inspector_sha256: sha(files.get('tools/inspect_motion.py')), sampling_helper_sha256: sha(files.get('tools/glb_sampling.py')) });
      await write(`${directory}/${lod.model}.validation.json`, { errors: 0 });
    }
    const renders = [];
    async function render(level, state, view) {
      const image = `image_${renders.length}.png`;
      renders.push({ level, state, view, image, model_sha256: candidate.lods[level].sha256,
        image_sha256: await write(`${directory}/${image}`, `${level} ${state} ${view}`),
        reviewer_sha256: sha(files.get('tools/review_candidate.py')), action_helper_sha256: sha(files.get('tools/imported_actions.py')) });
    }
    for (let level = 0; level < 3; level++) for (const state of ['rest', 'run@0.35', 'graze@0.5']) await render(level, state, 'full');
    await render(0, 'rest', 'head');
    for (const clip of ['walk', 'run']) for (let i = 0; i < 8; i++) await render(0, `${clip}@${i / 8}`, 'profile');
    for (const phase of [0, .5]) await render(0, `idle@${phase}`, 'profile');
    for (const phase of [0, .25, .5, .875]) await render(0, `graze@${phase}`, 'profile');
    await write(`${directory}/render_receipts.json`, { renders });
    await run({ root, write, files, candidate, base, renders });
  } finally {
    assert(path.resolve(root).startsWith(path.resolve(os.tmpdir()) + path.sep + 'fauna-candidate-'));
    await fs.rm(root, { recursive: true, force: true });
  }
}

test('candidate promotion binds corrected bytes and editable master while retaining the base inputs', () => fixture(async ({ root, candidate, base }) => {
  const delivery = await collectCandidateDelivery(root, asset, clips, directory);
  assert.equal(delivery.modelDirectory, directory);
  assert.deepEqual(delivery.evidence.modelHashes, candidate.lods.map(lod => lod.sha256));
  assert.equal(delivery.build.master, `${directory}/corrected.blend`);
  assert.equal(delivery.evidence.files[`${directory}/corrected.blend`], candidate.master_sha256);
  assert.equal(delivery.evidence.files[`runtime/${base.lods[0].model}`], base.lods[0].sha256);
  assert.equal(delivery.renders[0].image, `${directory}/image_0.png`);
}));

test('candidate evidence rejects changed corrected geometry, editable morph master and images', () => fixture(async ({ root, files }) => {
  for (const name of [`${directory}/${asset}_lod0.glb`, `${directory}/corrected.blend`, `${directory}/image_0.png`]) {
    const original = files.get(name); await fs.writeFile(path.join(root, name), 'changed bytes');
    await assert.rejects(collectCandidateDelivery(root, asset, clips, directory), /Changed evidence/);
    await fs.writeFile(path.join(root, name), original);
  }
}));

test('candidate evidence cannot substitute the base model or drop an other-LOD posed review', () => fixture(async ({ root, write, candidate, base, renders }) => {
  candidate.lods[0].sha256 = base.lods[0].sha256;
  await write(`${directory}/candidate.json`, candidate);
  await assert.rejects(collectCandidateDelivery(root, asset, clips, directory), /substituted/);
  assert.throws(() => requireCandidateViews(renders.filter(r => !(r.level === 2 && r.state === 'graze@0.5')), clips), /comparison missing/);
}));

test('candidate paths stay inside the package candidate directory', () => {
  assert.throws(() => candidatePath(path.resolve('package'), 'runtime'), /inside review\/candidates/);
  assert.throws(() => candidatePath(path.resolve('package'), '../foreign'), /escapes/);
});

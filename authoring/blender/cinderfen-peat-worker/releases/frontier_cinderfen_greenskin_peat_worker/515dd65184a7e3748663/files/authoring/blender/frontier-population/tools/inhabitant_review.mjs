import assert from 'node:assert/strict';
import path from 'node:path';

export const INHABITANT_CLIPS = ['attack_melee', 'attack_ranged', 'cast', 'combat_idle', 'death', 'idle', 'jump', 'run', 'walk'];

export function inside(root, relative) {
  assert(typeof relative === 'string' && relative.length && !path.isAbsolute(relative), 'Expected a repository-relative evidence path');
  const target = path.resolve(root, relative.replaceAll('\\', '/'));
  assert(target.startsWith(path.resolve(root) + path.sep), 'Evidence path escapes its source root');
  return target;
}

export function requireCharacterViews(close, motion) {
  for (const name of ['front', 'head', 'run_side', 'death:2']) {
    assert(close.some(view => view.view === name), `Missing character close view: ${name}`);
  }
  for (const clip of INHABITANT_CLIPS) {
    const times = new Set(motion.filter(view => view.clip === clip).map(view => view.seconds));
    assert(times.size >= 3, `${clip}: three distinct actual-export poses required`);
  }
}

export function requireCurrentApproval(review, evidence) {
  assert.equal(review?.status, 'approved', 'The complete character still needs actual-export visual acceptance');
  assert(review.reviewedBy?.trim() && Number.isFinite(Date.parse(review.reviewedAt)), 'Reviewer and date required');
  assert.deepEqual(review.evidence, evidence, 'Source, model, audit or image evidence changed after visual acceptance');
}

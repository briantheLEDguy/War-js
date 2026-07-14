import { createHash, randomUUID } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { reviewMutationAuthorized } from '../scripts/blender-character-pipeline/tools/local-roster-review-plugin.mjs';
import { rosterGroup } from '../scripts/blender-character-pipeline/tools/roster-spec.mjs';
import {
  createRevisionManifest,
  recordRosterReview,
  revisionDir,
  revisionManifestPath,
  updateRevision,
} from '../scripts/blender-character-pipeline/tools/roster-runs.mjs';

let testRoot: string;
let runRoot: string;
let authoringRoot: string;

const creatureChecks = {
  materialsPbr: true,
  seamsAcceptable: true,
  clippingAcceptable: true,
  stressPosesAcceptable: true,
  rigMarkersAcceptable: true,
};

const humanoidChecks = {
  anatomyNatural: true,
  materialsPbr: true,
  seamsAcceptable: true,
  clippingAcceptable: true,
  stressPosesAcceptable: true,
  weaponSocketsAcceptable: true,
};

beforeEach(() => {
  testRoot = path.resolve('artifacts', 'model-jobs', `vitest-roster-review-${randomUUID()}`);
  runRoot = path.join(testRoot, 'runs');
  authoringRoot = path.join(testRoot, 'authoring');
  mkdirSync(testRoot, { recursive: true });
});

afterEach(() => rmSync(testRoot, { recursive: true, force: true }));

function readyRevision(kind: 'playable' | 'npc' | 'creature', key: string, revision: number) {
  const group = rosterGroup(kind, key);
  createRevisionManifest({ runId: 'review-run', group, revision, root: runRoot });
  const directory = revisionDir('review-run', kind, key, revision, runRoot);
  const artifactPath = path.join(directory, `${key}-${revision}.glb`);
  writeFileSync(artifactPath, `review artifact ${kind}:${key}:${revision}`);
  const sha256 = createHash('sha256').update(readFileSync(artifactPath)).digest('hex');
  const manifestPath = revisionManifestPath('review-run', kind, key, revision, runRoot);
  updateRevision(manifestPath, {
    status: 'ready_for_review',
    modelStage: 'pending_review',
    qc: { passed: true, errors: [] },
    artifacts: [{ kind: 'model', path: path.relative(path.resolve('.'), artifactPath).replaceAll('\\', '/'), sha256 }],
  });
  return { artifactPath, manifestPath };
}

describe('hash-bound staged roster review', () => {
  it('requires rejection notes and rejects stale artifact hashes', () => {
    const { artifactPath } = readyRevision('creature', 'barrow_wolf', 1);
    expect(() => recordRosterReview({
      runId: 'review-run', kind: 'creature', key: 'barrow_wolf', revision: 1,
      decision: 'rejected', reviewer: 'Reviewer', notes: '',
    }, { root: runRoot, authoringRoot })).toThrow('Disapproval requires notes');

    writeFileSync(artifactPath, 'mutated after QC');
    expect(() => recordRosterReview({
      runId: 'review-run', kind: 'creature', key: 'barrow_wolf', revision: 1,
      decision: 'approved', reviewer: 'Reviewer', checks: creatureChecks,
    }, { root: runRoot, authoringRoot })).toThrow('Artifact changed');
  });

  it('freezes approved model-stage content, safely cleans unselected versions, and audits reapproval', () => {
    readyRevision('creature', 'barrow_wolf', 1);
    readyRevision('creature', 'barrow_wolf', 2);
    recordRosterReview({
      runId: 'review-run', kind: 'creature', key: 'barrow_wolf', revision: 2,
      decision: 'approved', reviewer: 'First Reviewer', checks: creatureChecks,
    }, { root: runRoot, authoringRoot });
    expect(existsSync(revisionDir('review-run', 'creature', 'barrow_wolf', 1, runRoot))).toBe(false);
    expect(existsSync(revisionDir('review-run', 'creature', 'barrow_wolf', 2, runRoot))).toBe(true);
    const canonical = path.join(authoringRoot, 'creature', 'barrow_wolf', 'model-stage-approved.json');
    expect(JSON.parse(readFileSync(canonical, 'utf8'))).toMatchObject({
      sourceRevision: 2,
      modelStage: 'approved',
      animationStage: 'pending',
      runtimeEligible: false,
    });

    readyRevision('creature', 'barrow_wolf', 3);
    recordRosterReview({
      runId: 'review-run', kind: 'creature', key: 'barrow_wolf', revision: 3,
      decision: 'approved', reviewer: 'Second Reviewer', checks: creatureChecks,
    }, { root: runRoot, authoringRoot });
    expect(JSON.parse(readFileSync(canonical, 'utf8')).sourceRevision).toBe(3);
    const audit = JSON.parse(readFileSync(path.join(authoringRoot, 'history', 'creature_barrow_wolf.json'), 'utf8'));
    expect(audit.entries.some((entry: { sourceRevision: number }) => entry.sourceRevision === 2)).toBe(true);
    expect(audit.entries.some((entry: { sourceRevision: number }) => entry.sourceRevision === 3)).toBe(true);
  });

  it('requires both playable variants and every humanoid weapon mode', () => {
    readyRevision('playable', 'battle_prelate', 1);
    const base = {
      runId: 'review-run', kind: 'playable' as const, key: 'battle_prelate', revision: 1,
      decision: 'approved' as const, reviewer: 'Class Reviewer', checks: humanoidChecks,
      visitedWeaponModes: ['one_handed', 'two_handed', 'dual_wield'],
    };
    expect(() => recordRosterReview({ ...base, visitedVariants: ['m'] }, { root: runRoot, authoringRoot })).toThrow(
      'requires reviewing f',
    );
    expect(() => recordRosterReview({
      ...base,
      visitedVariants: ['m', 'f'],
      visitedWeaponModes: ['one_handed', 'two_handed'],
    }, { root: runRoot, authoringRoot })).toThrow('requires dual_wield');
    expect(recordRosterReview({
      ...base,
      visitedVariants: ['m', 'f'],
    }, { root: runRoot, authoringRoot }).approved).toMatchObject({ runtimeEligible: false, animationStage: 'pending' });
  });

  it('requires secondary review for captain and failed NPC combinations', () => {
    const { manifestPath } = readyRevision('npc', 'empire_m', 1);
    const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
    updateRevision(manifestPath, {
      qc: { ...manifest.qc, secondaryReviewProfileKeys: ['enemy_aegis_keep_captain'] },
    });
    const base = {
      runId: 'review-run', kind: 'npc' as const, key: 'empire_m', revision: 1,
      decision: 'approved' as const, reviewer: 'NPC Reviewer', checks: humanoidChecks,
      visitedWeaponModes: ['one_handed', 'two_handed', 'dual_wield'],
    };
    expect(() => recordRosterReview(base, { root: runRoot, authoringRoot })).toThrow(
      'secondary review of enemy_aegis_keep_captain',
    );
    expect(recordRosterReview({
      ...base,
      reviewedNpcProfiles: ['enemy_aegis_keep_captain'],
    }, { root: runRoot, authoringRoot }).approved).toMatchObject({ runtimeEligible: false });
  });
});

describe('local review server mutation boundary', () => {
  it('requires both the ephemeral token and an exact same-origin host', () => {
    const token = 'secret-token';
    expect(reviewMutationAuthorized({ headers: {
      'x-war-review-token': token,
      origin: 'http://127.0.0.1:5173',
      host: '127.0.0.1:5173',
    } }, token)).toBe(true);
    expect(reviewMutationAuthorized({ headers: {
      'x-war-review-token': 'wrong',
      origin: 'http://127.0.0.1:5173',
      host: '127.0.0.1:5173',
    } }, token)).toBe(false);
    expect(reviewMutationAuthorized({ headers: {
      'x-war-review-token': token,
      origin: 'http://evil.invalid',
      host: '127.0.0.1:5173',
    } }, token)).toBe(false);
  });
});

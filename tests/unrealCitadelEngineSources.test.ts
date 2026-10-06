import { createHash, randomUUID } from 'node:crypto';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, expect, test } from 'vitest';
import { requireCitadelPackageOwnership, requireNativePackageHash, REVIEWED_CITADEL_ENGINE_SOURCE as parent } from '../scripts/unreal/native-package-evidence';
import { verifyCityPackages, verifySharedCities } from '../server/scenarios/city-content';
import { scenarioCandidateProof } from '../server/scenarios/candidate-proof';
import { sharedCityFixture } from './fixtures/sharedCityContent';
import { scenarioCandidateFixture } from './fixtures/scenarioCandidate';

// Injected package bytes test confinement only; they are unusable as native evidence.
const roots: string[] = [];
afterEach(() => roots.splice(0).forEach(root => rmSync(root, { recursive: true, force: true })));
function fixture() {
  const root = mkdtempSync(path.join(os.tmpdir(), 'citadel-engine-source-')); roots.push(root);
  const engineRoot = path.join(root, 'portable-engine'), file = path.join(engineRoot, 'Engine/Content', parent.slice(8)) + '.uasset';
  mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, 'PORTABLE CLOUD PARENT ONLY');
  const sha = createHash('sha256').update(readFileSync(file)).digest('hex');
  return { root, engineRoot, file, sha };
}
test('the exact Engine cloud parent is preserved input while all Engine ownership is forbidden', () => {
  const f = fixture(); const hashes = { [parent]: f.sha };
  requireCitadelPackageOwnership(hashes, false);
  requireNativePackageHash(f.root, parent, f.sha, f.engineRoot);
  expect(() => requireCitadelPackageOwnership(hashes, true)).toThrow(/ownership/);
  expect(() => requireCitadelPackageOwnership({ '/Engine/Unreviewed': f.sha }, false)).toThrow(/exact preserved/);
  expect(() => requireNativePackageHash(f.root, '/Engine/../outside', f.sha, f.engineRoot)).toThrow(/identity/);
  writeFileSync(f.file.replace(/\.uasset$/, '.umap'), 'PORTABLE AMBIGUOUS PACKAGE');
  expect(() => requireNativePackageHash(f.root, parent, f.sha, f.engineRoot)).toThrow(/ambiguous/);
});
test('future shared city verification checks actual configured cloud bytes without Engine ownership', () => {
  const f = fixture(), city = sharedCityFixture(f.root);
  city.receipt.cities[0].dependencyHashes[parent] = f.sha; city.save();
  expect(verifySharedCities(f.root, f.engineRoot)).toHaveLength(2);
  expect(() => verifyCityPackages(f.root, { [parent]: f.sha }, false, f.engineRoot)).toThrow(/ownership/);
  expect(() => verifyCityPackages(f.root, { '/Engine/Other': f.sha }, true, f.engineRoot)).toThrow(/unreviewed/);
  writeFileSync(f.file, 'TAMPERED PORTABLE PARENT');
  expect(() => verifySharedCities(f.root, f.engineRoot)).toThrow(/dependency changed/);
});
test('candidate queue authority retains the real Engine source hash and rejects changed or misowned sources', () => {
  const f = fixture(), candidate = scenarioCandidateFixture(f.root);
  const options = { repositoryRoot: f.root, map: candidate.map, fixtureId: randomUUID(), engineRoot: candidate.engineRoot };
  const proof = scenarioCandidateProof(options);
  const file = path.join(candidate.engineRoot!, 'Engine/Content', parent.slice(8)) + '.uasset';
  expect(proof.packageHashes[parent]).toBe(createHash('sha256').update(readFileSync(file)).digest('hex'));
  const receiptPath = path.join(candidate.directory, 'candidate.json'), receipt = JSON.parse(readFileSync(receiptPath, 'utf8'));
  receipt.packageHashes[parent] = proof.packageHashes[parent]; writeFileSync(receiptPath, JSON.stringify(receipt));
  expect(() => scenarioCandidateProof(options)).toThrow(/ownership/);
  delete receipt.packageHashes[parent]; receipt.sourceHashes['/Engine/Unreviewed'] = proof.packageHashes[parent];
  writeFileSync(receiptPath, JSON.stringify(receipt)); expect(() => scenarioCandidateProof(options)).toThrow(/exact preserved/);
  delete receipt.sourceHashes['/Engine/Unreviewed']; writeFileSync(receiptPath, JSON.stringify(receipt));
  writeFileSync(file, 'TAMPERED PORTABLE PARENT'); expect(() => scenarioCandidateProof(options)).toThrow(/dependency changed/);
});

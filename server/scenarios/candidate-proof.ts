import { createHash } from 'node:crypto';
import { existsSync, readFileSync, readdirSync, realpathSync, statSync } from 'node:fs';
import path from 'node:path';
import { candidateSiegeContentEvidence, type CandidateSiegeContentEvidence } from '../../scripts/unreal/siege-content-evidence';
import { defaultEngineRoot } from '../../scripts/unreal/toolchain';
import { scenarioCatalog, type ScenarioDefinition, type ScenarioJournal } from '../../shared/scenarios/types';

export interface ScenarioCandidateProofOptions {
  repositoryRoot: string;
  map: string;
  fixtureId: string;
  /** Portable tests inject unusable fixture packages, never native acceptance. */
  engineRoot?: string;
}
export interface ScenarioCandidateProof extends CandidateSiegeContentEvidence {
  schemaVersion: 1;
  fixtureId: string;
  proofOnly: true;
  contentReviewOverride: true;
  productionAdmission: false;
  steamAdmission: false;
  territorialAcceptance: false;
  releaseApproved: false;
  scenario: 'lower_city';
  capacity: 18;
  rulesVersion: 2;
  battlefield: 'FullSiege';
  statsMode: 'scenario';
  cityDefinition: string;
  candidateReceiptPath: string;
  candidateReceiptSha256: string;
  blueprintPath: string;
  blueprintSha256: string;
  binaryPath: string;
  binarySha256: string;
  sourceHashes: Record<string, string>;
  packageHashes: Record<string, string>;
  definition: ScenarioDefinition;
}
const digest = (file: string) => createHash('sha256').update(readFileSync(file)).digest('hex');
export const scenarioProofCanonical = (value: unknown): string => {
  if (Array.isArray(value)) return '[' + value.map(scenarioProofCanonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.entries(value).sort(([a], [b]) => a.localeCompare(b))
    .map(([key, item]) => JSON.stringify(key) + ':' + scenarioProofCanonical(item)).join(',') + '}';
  const result = JSON.stringify(value);
  if (result === undefined) throw new Error('Scenario proof contains a non-JSON value.');
  return result;
};
function confinedFile(root: string, filename: string) {
  const resolved = realpathSync(filename), relative = path.relative(realpathSync(root), resolved);
  if (!relative || relative === '..' || relative.startsWith('..' + path.sep) || path.isAbsolute(relative)
    || !statSync(resolved).isFile()) throw new Error('Scenario proof file escaped its configured project.');
  return resolved;
}

/** A fresh private authority can exercise entry before publication; it grants no admission review. */
export function scenarioCandidateProof(options: ScenarioCandidateProofOptions): ScenarioCandidateProof {
  if (!/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(options.fixtureId))
    throw new Error('An isolated scenario-menu proof UUID is required.');
  const repository = realpathSync(options.repositoryRoot);
  const evidence = candidateSiegeContentEvidence(repository, options.map, options.engineRoot ?? defaultEngineRoot());
  const revision = /^\/Game\/WorldRebuild\/AegisCitadel_([a-f0-9]{12})\/SiegeCandidate$/.exec(options.map)![1];
  if (evidence.signature.slice(0, 12) !== revision) throw new Error('Scenario candidate namespace differs from its signed source revision.');
  const directory = path.join(repository, 'artifacts/unreal/aegis-citadel', revision);
  const candidateReceiptPath = confinedFile(repository, path.join(directory, 'candidate.json'));
  const blueprintPath = confinedFile(repository, path.join(directory, 'blueprint.json'));
  const receipt = JSON.parse(readFileSync(candidateReceiptPath, 'utf8').replace(/^\uFEFF/, ''));
  const packageHashes: Record<string, string> = {};
  for (const hashes of [receipt.sourceHashes, receipt.packageHashes, receipt.city.dependencyHashes, receipt.city.packageHashes])
    for (const [name, hash] of Object.entries(hashes) as [string, string][]) {
      if (packageHashes[name] && packageHashes[name] !== hash) throw new Error('Conflicting scenario candidate package ownership.');
      packageHashes[name] = hash;
    }
  const nativeRoot = path.join(repository, 'unreal/AegisWar/Source');
  const sourceHashes: Record<string, string> = {};
  const visit = (directory: string) => {
    for (const entry of readdirSync(directory, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (entry.isSymbolicLink()) throw new Error('Scenario proof native source symlinks are unsupported.');
      const filename = path.join(directory, entry.name);
      if (entry.isDirectory()) visit(filename);
      else if (/\.(cpp|h|cs)$/.test(entry.name)) { const file = confinedFile(nativeRoot, filename); sourceHashes[file] = digest(file); }
    }
  };
  visit(nativeRoot);
  if (!Object.keys(sourceHashes).length || Object.keys(sourceHashes).length > 1024
    || !Object.keys(sourceHashes).some(name => name.endsWith(path.join('Private', 'WarScenarioInstance.cpp')))
    || !Object.keys(sourceHashes).some(name => name.endsWith(path.join('Private', 'WarScenarioMenuProof.cpp'))))
    throw new Error('Scenario proof requires the actual bounded native scenario source set.');
  const binaryPath = confinedFile(repository, path.join(repository, 'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll'));
  const definition: ScenarioDefinition = { ...scenarioCatalog.find(row => row.id === 'lower_city')!,
    map: evidence.map, contentRevision: evidence.cityRevision };
  if (definition.capacity !== 18 || definition.rulesVersion !== 2 || definition.battlefield !== 'FullSiege'
    || definition.gatherMs !== 30_000 || definition.acceptMs !== 30_000 || definition.reconnectMs !== 120_000)
    throw new Error('The existing lower_city rules changed; review the fixture instead of reinterpreting it.');
  return { schemaVersion: 1, fixtureId: options.fixtureId, ...evidence, proofOnly: true, contentReviewOverride: true,
    productionAdmission: false, steamAdmission: false, territorialAcceptance: false, releaseApproved: false,
    scenario: 'lower_city', capacity: 18, rulesVersion: 2, battlefield: 'FullSiege', statsMode: 'scenario',
    cityDefinition: receipt.city.definition, candidateReceiptPath, candidateReceiptSha256: digest(candidateReceiptPath),
    blueprintPath, blueprintSha256: digest(blueprintPath), binaryPath, binarySha256: digest(binaryPath),
    sourceHashes, packageHashes, definition };
}

export function scenarioCandidateProofDirectory(options: ScenarioCandidateProofOptions): string {
  return path.join(path.resolve(options.repositoryRoot), 'artifacts/unreal/scenario-menu', options.fixtureId, 'host');
}
export function requireScenarioCandidateStorage(options: ScenarioCandidateProofOptions, directory: string): void {
  const expected = scenarioCandidateProofDirectory({ ...options, repositoryRoot: realpathSync(options.repositoryRoot) });
  if (path.resolve(directory) !== expected) throw new Error('Candidate queue proof storage must use its exact isolated directory.');
  let parent = expected;
  while (!existsSync(parent)) {
    const next = path.dirname(parent);
    if (next === parent) throw new Error('Candidate proof storage has no configured project ancestor.');
    parent = next;
  }
  if (realpathSync(parent) !== parent) throw new Error('Candidate queue proof storage cannot redirect through a filesystem link.');
}
/** Restart only the same fixture; never rebind an ordinary or historical journal to a candidate. */
export function requireScenarioCandidateJournal(journal: ScenarioJournal | undefined, proof: ScenarioCandidateProof): void {
  if (!journal) return;
  if (journal.version !== 1 || Object.values(journal.matches).some(match => !match.definition
    || scenarioProofCanonical(match.definition) !== scenarioProofCanonical(proof.definition)))
    throw new Error('Scenario candidate journal contains a foreign or historical allocation contract.');
}

export function requireSameScenarioCandidate(options: ScenarioCandidateProofOptions, expected: ScenarioCandidateProof): void {
  if (scenarioProofCanonical(scenarioCandidateProof(options)) !== scenarioProofCanonical(expected))
    throw new Error('Scenario candidate, catalog, receipt, binary or native source changed during the private proof.');
}
export function hasScenarioCandidateMarker(directory: string): boolean {
  return existsSync(path.join(directory, 'candidate-proof.json'));
}

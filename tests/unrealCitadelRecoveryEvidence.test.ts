import { expect, test } from 'vitest';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { recoveryEvidenceFixture } from './fixtures/citadelRecoveryEvidence';
import { citadelCharacterRecoveryEvidence, recoveryCanonical, validateCitadelCharacterRecovery } from '../scripts/unreal/citadel-recovery-evidence';

const expected = (f: ReturnType<typeof recoveryEvidenceFixture>) => Object.fromEntries(['map', 'mapSha256', 'signature', 'cityRevision', 'geometrySignature'].map(k => [k, f.report[k]])) as any;
test('binds the narrow synthetic fixture shape without accepting victory, death or equipment mutation', () => {
  const f = recoveryEvidenceFixture(); expect(() => validateCitadelCharacterRecovery(f, expected(f))).not.toThrow();
  for (const flag of ['outcomeRecoveryVerified', 'equipmentMutationVerified', 'deadIntentVerified', 'releaseAcceptance', 'fullSiegeAdmission']) {
    const bad = structuredClone(f); bad.report[flag] = true;
    expect(() => validateCitadelCharacterRecovery(bad, expected(f))).toThrow(/broader/);
  }
});
test.each([
  ['stale candidate', (f: any) => { f.report.cityRevision = 'f'.repeat(64); }],
  ['missing third process', (f: any) => { f.processes.attempts.pop(); }],
  ['invented interruption', (f: any) => { f.processes.attempts[0].killRequested = false; }],
  ['reused process identity', (f: any) => { f.processes.attempts[1].pid = f.processes.attempts[0].pid; }],
  ['forged initial ACK', (f: any) => { f.report.http[0].at(-1).forwarded = true; }],
  ['WAL tamper', (f: any) => { f.wals[1].body.character.document.inventory.items = []; }],
  ['missing genuine catalog cast', (f: any) => { delete f.mutations[0].cast; }],
  ['failed catalog cast', (f: any) => { f.mutations[0].cast.succeeded=false; }],
  ['wrong original WAL sequence', (f: any) => { f.mutations[0].wal.walSequence++; }],
  ['historical partial recovery runtime', (f: any) => { f.recovered[0].character.document.runtime.version=1; }],
  ['lost unexpired buff', (f: any) => { const c=f.recovered[0].character.document.runtime.combat;c.statuses=[];c.definitions=[]; }],
  ['renewed recovered deadline', (f: any) => { f.recovered[0].character.document.runtime.combat.statuses[0].expiresAtUnixMs++; }],
  ['lost unexpired class cooldown', (f: any) => { f.recovered[0].character.document.runtime.abilities.cooldowns=[]; }],
  ['lost equipment', (f: any) => { f.recovered[1].character.document.inventory.equipment = []; }],
  ['lost quest receipt', (f: any) => { f.nativeReport.characters[1].document.runtime.questKills = []; }],
  ['missing native character', (f: any) => { f.nativeReport.characters.pop(); }],
  ['return ACK raced evacuation', (f: any) => { const rows = f.report.http[2]; const participant = rows.find((r: any) => r.scope === 'participant'); participant.index = 9999; }],
  ['flag-only restored return', (f: any) => { f.report.http[1].find((r: any) => r.route === 'restored').returned = true; }],
  ['unsafe return', (f: any) => { f.nativeReport.returnWitnesses[0].physicalReady = false; }],
  ['unreleased return movement hold', (f: any) => { f.nativeReport.returnWitnesses[0].movementHeld = true; }],
  ['unreturned canonical document', (f: any) => { const records = f.checkpoints[2].state.nativeSiegeJournal.characters; (Object.values(records)[0] as any).returned = false; }],
  ['completed encounter', (f: any) => { f.nativeReport.unfinishedSiege.phase = 'finished'; f.nativeReport.unfinishedSiege.attackersWon = true; }],
] as const)('rejects %s', (_label, change) => {
  const f = recoveryEvidenceFixture(), e = expected(f); change(f);
  expect(() => validateCitadelCharacterRecovery(f, e)).toThrow();
});
test('verifies every individual file and current binary/native source before consuming a private recovery receipt', () => {
  const root = mkdtempSync(path.join(tmpdir(), 'citadel-recovery-evidence-'));
  try {
    const f = recoveryEvidenceFixture(root), put = (file: string, value: string) => { mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, value); };
    put(f.report.binaryPath, 'portable native binary');
    put(path.join(root, 'unreal/AegisWar/Content', f.report.map.slice(6) + '.umap'), 'portable campaign package');
    const sources = Object.keys(f.report.sourceHashes); put(sources[0], 'portable proof source'); put(sources[1], 'portable bridge source');
    const save = (binding: any, value: any) => { const text = recoveryCanonical(value); put(path.join(root, binding.path), text);
      expect(createHash('sha256').update(text).digest('hex')).toBe(binding.sha256); };
    for (const key of ['mutations', 'recovered', 'wals', 'configs', 'checkpoints'] as const) f[key].forEach((value, i) => save(f.report.evidence[key][i], value));
    save(f.report.evidence.nativeReport, f.nativeReport); save(f.report.evidence.http, f.http); save(f.report.evidence.processes, f.processes);
    const binding = { path: f.report.evidence.http.path.replace('http.json', 'report.json'), sha256: createHash('sha256').update(recoveryCanonical(f.report)).digest('hex') };
    save(binding, f.report);
    expect(() => citadelCharacterRecoveryEvidence(root, binding, expected(f))).not.toThrow();
    put(sources[1], 'changed bridge source');
    expect(() => citadelCharacterRecoveryEvidence(root, binding, expected(f))).toThrow(/every current native source/);
    put(sources[1], 'portable bridge source'); put(f.report.binaryPath, 'changed native binary');
    expect(() => citadelCharacterRecoveryEvidence(root, binding, expected(f))).toThrow(/binary is stale/);
    put(f.report.binaryPath, 'portable native binary'); put(path.join(root, f.report.evidence.wals[0].path), '{}');
    expect(() => citadelCharacterRecoveryEvidence(root, binding, expected(f))).toThrow(/file changed/);
    expect(() => citadelCharacterRecoveryEvidence(root, { ...binding, path: '../report.json' }, expected(f))).toThrow();
  } finally { rmSync(root, { recursive: true, force: true }); }
});

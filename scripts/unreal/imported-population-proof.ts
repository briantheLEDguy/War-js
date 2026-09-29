import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';
import { officialCapitalMap } from './capital-map';

const args = parseArguments(process.argv.slice(2), ['--population-only', '--combat-only'], ['--enemy']);
const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand) throw new Error('Unreal editor is unavailable.');
const ledgerFile = path.join(repoRoot, 'shared/data/importedPopulation.json');
const ledger = JSON.parse(readFileSync(ledgerFile, 'utf8')) as {
  camps: Array<{ zone: string; allegiance: string; members: Array<{ id: string; model: string }> }>;
};
const output = path.join(repoRoot, 'artifacts/unreal/imported-population/runtime', `${Date.now()}`);
mkdirSync(output, { recursive: true });
const results: Array<{ name: string; report: unknown }> = [];
function run(name: string, savedFolder: string, flags: string[]) {
  const report = path.join(repoRoot, 'unreal/AegisWar/Saved', savedFolder, 'report.json');
  rmSync(report, { force: true });
  const code = runEngineCommand(engine.editorCommand!, [projectPath, officialCapitalMap(), '-game', '-unattended',
    '-nop4', '-nosound', '-nosplash', '-nullrhi', '-WarDevelopmentGM', '-ExecCmds=t.MaxFPS 60',
    ...flags, `-abslog=${path.join(output, `${name}.log`)}`]);
  if (!existsSync(report)) throw new Error(`Runtime proof produced no fresh report: ${name}; ${output}`);
  copyFileSync(report, path.join(output, `${name}.json`));
  const data = JSON.parse(readFileSync(report, 'utf8').replace(/^\uFEFF/, ''));
  if (code !== 0 || data.passed !== true) throw new Error(`Runtime proof failed: ${name}; ${output}`);
  results.push({ name, report: data });
  console.log(`Passed ${name}`);
}
if (!args.has('--combat-only') && !args.get('--enemy')) run('inhabitants', 'ImportedPopulationProof', ['-WarImportedPopulationProof']);
if (!args.has('--population-only')) {
  const seen = new Set<string>();
  for (const camp of ledger.camps.filter(row => row.allegiance === 'hostile')) {
    const map = JSON.parse(readFileSync(path.join(repoRoot, `public/assets/maps/${camp.zone}.json`), 'utf8'));
    for (const member of camp.members) {
      if (args.get('--enemy') ? args.get('--enemy') !== member.id : seen.has(member.model)) continue;
      seen.add(member.model);
      run(member.id, 'EnemyProof', ['-WarEnemyProof', `-WarEnemyProofZone=${camp.zone}`,
        `-WarEnemyProofId=${member.id}`, `-WarEnemyProofCount=${map.enemies.length}`, '-WarEnemyProofAttachments=2']);
    }
  }
  if (!seen.size) throw new Error('No matching hostile imported character.');
}
writeFileSync(path.join(output, 'report.json'), JSON.stringify({
  ledgerSha256: createHash('sha256').update(readFileSync(ledgerFile)).digest('hex'), results,
  productionAccepted: false, multiplayerAccepted: false,
}, null, 2));
console.log(JSON.stringify({ output, proofsPassed: results.length }));

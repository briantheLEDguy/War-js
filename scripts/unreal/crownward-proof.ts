import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { defaultEngineRoot, inspectToolchain, projectPath, repoRoot, runEngineCommand } from './toolchain';

const receipt = JSON.parse(readFileSync(path.join(repoRoot, 'artifacts/unreal/licensed-kits/capital-kit-build.json'), 'utf8'));
if (receipt.map !== '/Game/Capitals/crownward/AegisCapital_Workbench' || receipt.placements.length < 1)
  throw new Error('Build Crownward before testing it.');
const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand) throw new Error('Unreal command executable unavailable.');
const run = `crownward-${Date.now()}`;
const draft = randomUUID().replaceAll('-', '');
const output = path.join(repoRoot, 'artifacts/unreal/capital-proof', run);
mkdirSync(output, { recursive: true });
const reports = [];
for (const reload of [false, true]) {
  const id = run + (reload ? '-reload' : '');
  const code = runEngineCommand(engine.editorCommand, [projectPath, receipt.map, '-game', '-unattended', '-nullrhi',
    '-nosplash', '-nosound', '-nop4', '-stdout', '-FullStdOutLogOutput', '-WarDevelopmentGM', '-WarCapitalProof',
    '-WarCrownwardProof', `-WarProofRun=${id}`, `-WarProofDraftId=${draft}`,
    `-WarCapitalExpectedModels=${new Set(receipt.placements.map((row: { mesh: string }) => row.mesh)).size}`,
    `-WarCapitalExpectedObjects=${receipt.placements.length}`, `-abslog=${path.join(output, id + '.log')}`,
    ...(reload ? ['-WarCapitalReloadProof'] : [])]);
  const result = path.join(repoRoot, 'unreal/AegisWar/Saved/CapitalProof', id, 'report.json');
  if (code !== 0 || !existsSync(result)) throw new Error(`Crownward proof failed: ${output}`);
  const report = JSON.parse(readFileSync(result, 'utf8').replace(/^\uFEFF/, ''));
  if (!report.passed || report.editableObjects !== receipt.placements.length + 1 || report.fullCapitalAcceptance !== false
    || !report.catalogSearchVerified || (!reload && !report.developmentTraversalVerified))
    throw new Error(`Crownward runtime checks failed: ${output}`);
  reports.push(report);
}
writeFileSync(path.join(output, 'report.json'), JSON.stringify({ passed: true, freshProcessReload: true,
  map: receipt.map, reports, fullCapitalAcceptance: false }, null, 2));
console.log(JSON.stringify({ crownwardProofPassed: true, output }));

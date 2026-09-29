import { randomUUID } from 'node:crypto';
import { mkdirSync, existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, projectPath, repoRoot, runEngineCommand } from './toolchain';

const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run = randomUUID();
const output = path.join(repoRoot, 'artifacts/unreal/targeting', run);
const proof = path.join(repoRoot, 'unreal/AegisWar/Saved/InterfaceProof', run.replaceAll('-', ''));
mkdirSync(output, { recursive: true });
const code = runEngineCommand(engine.editorCommand, [projectPath, '/Game/Capitals/aegis_capital/AegisCapital_Workbench',
  '-game', '-unattended', '-nop4', '-nosound', '-nosplash', '-RenderOffscreen', '-windowed', '-ForceRes', '-ResX=1920', '-ResY=1080',
  '-WarDevelopmentGM', '-WarInterfaceProof', '-WarTargetingProof', `-WarTargetingRun=${run}`,
  `-GameUserSettingsINI=${path.join(output, 'preferences.ini')}`, '-ExecCmds=t.MaxFPS 30', `-abslog=${path.join(output, 'game.log')}`]);
const reportFile = path.join(proof, 'report.json');
if (code !== 0 || !existsSync(reportFile)) throw new Error(`Targeting proof failed: ${output}; ${proof}`);
const report = JSON.parse(readFileSync(reportFile, 'utf8').replace(/^\uFEFF/, ''));
if (!report.passed) throw new Error(`Targeting proof failed: ${JSON.stringify(report)}`);
for (const name of ['target-enemy.png', 'target-friendly.png'])
  if (!existsSync(path.join(proof, name))) throw new Error(`Missing reticle capture: ${name}`);
console.log(JSON.stringify({ output, proof, ...report, visualApproval: false }, null, 2));

import { randomUUID } from 'node:crypto';
import { mkdirSync, existsSync, readFileSync, copyFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, projectPath, repoRoot, runEngineCommand } from './toolchain';

const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run = randomUUID();
const output = path.join(repoRoot, 'artifacts/unreal/ability-deployment', run);
const receipt = path.join(repoRoot, 'unreal/AegisWar/Saved/AbilityWorkshopProof', run.replaceAll('-', ''));
mkdirSync(output, { recursive: true });
for (const phase of ['deployment', 'restart']) {
  const code = runEngineCommand(engine.editorCommand, [projectPath, '/Game/Capitals/aegis_capital/AegisCapital_Workbench',
    '-game', '-unattended', '-nop4', '-nosound', '-nosplash', '-RenderOffscreen', '-windowed', '-ResX=1280', '-ResY=800',
    '-WarDevelopmentGM', '-WarWorkshopDeploymentProof', `-WarWorkshopRun=${run}`,
    ...(phase === 'restart' ? ['-WarWorkshopRestart'] : []),
    `-GameUserSettingsINI=${path.join(output, 'preferences.ini')}`, '-ExecCmds=t.MaxFPS 30', `-abslog=${path.join(output, `${phase}.log`)}`]);
  const resultPath = path.join(receipt, `${phase}.json`);
  if (code !== 0 || !existsSync(resultPath)) throw new Error(`Personal ${phase} proof failed: ${output}`);
  const result = JSON.parse(readFileSync(resultPath, 'utf8').replace(/^\uFEFF/, ''));
  copyFileSync(resultPath, path.join(output, `${phase}.json`));
  if (!result.passed) throw new Error(`Personal ${phase}: ${result.detail}`);
}
console.log(JSON.stringify({ personalDeployment: true, restartRestored: true, sharedAdmission: false, output }));

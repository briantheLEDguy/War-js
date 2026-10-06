import { randomUUID } from 'node:crypto';
import { mkdirSync, existsSync, readFileSync, copyFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';

const args = parseArguments(process.argv.slice(2), [], ['--width', '--height']);
const width = Number(args.get('--width') ?? 1920), height = Number(args.get('--height') ?? 1080);
if (![[1280, 720], [1920, 1080], [2560, 1080]].some(([w, h]) => w === width && h === height)) throw new Error('Use 1280×720, 1920×1080 or 2560×1080.');
const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run = randomUUID(), output = path.join(repoRoot, 'artifacts/unreal/combat-ui', `${width}x${height}-${run}`);
const receipt = path.join(repoRoot, 'unreal/AegisWar/Saved/CombatUiProof', run.replaceAll('-', ''));
mkdirSync(output, { recursive: true });
const launch = (reload: boolean) => runEngineCommand(engine.editorCommand!, [projectPath, '/Game/Capitals/aegis_capital/AegisCapital_Workbench', '-game', '-unattended', '-nop4', '-nosound', '-nosplash',
  '-RenderOffscreen', '-windowed', '-ForceRes', `-ResX=${width}`, `-ResY=${height}`, '-WarDevelopmentGM', '-WarInterfaceProof', '-WarCombatUiProof', `-WarCombatUiRun=${run}`,
  `-GameUserSettingsINI=${path.join(output, 'preferences.ini')}`, `-ExecCmds=r.SetRes ${width}x${height}w,t.MaxFPS 30`,
  `-abslog=${path.join(output, reload ? 'restart.log' : 'game.log')}`, ...(reload ? ['-WarCombatUiReload'] : [])]);
const code = launch(false);
if (code !== 0 || !existsSync(path.join(receipt, 'report.json'))) throw new Error(`Combat UI proof failed: ${output}; ${receipt}`);
const result = JSON.parse(readFileSync(path.join(receipt, 'report.json'), 'utf8').replace(/^\uFEFF/, ''));
if (!result.passed) throw new Error(`Failed combat UI interactions: ${receipt}`);
for (const name of ['report.json', 'default.png', 'hidden.png', 'extreme.png']) {
  if (!existsSync(path.join(receipt, name))) throw new Error(`Missing combat UI evidence: ${name}`);
  copyFileSync(path.join(receipt, name), path.join(output, name));
}
if (launch(true) !== 0 || !existsSync(path.join(receipt, 'restart.json'))) throw new Error(`Combat UI restart proof failed: ${output}`);
const restart = JSON.parse(readFileSync(path.join(receipt, 'restart.json'), 'utf8').replace(/^\uFEFF/, ''));
if (restart.passed !== true || !existsSync(path.join(receipt, 'restart.png'))) throw new Error(`Missing successful restart evidence: ${receipt}`);
for (const name of ['restart.json', 'restart.png']) copyFileSync(path.join(receipt, name), path.join(output, name));
console.log(JSON.stringify({ combatUiInteractions: true, freshProcessPreferences: true, output, visualReviewRequired: true, networkAcceptance: false }));

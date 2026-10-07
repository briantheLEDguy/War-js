import { randomUUID } from 'node:crypto';
import { mkdirSync, existsSync, readFileSync, copyFileSync } from 'node:fs';
import path from 'node:path';
import { officialCapitalMap } from './capital-map';
import { citadelReviewArguments } from './citadel-review-launch';
import { defaultEngineRoot, inspectToolchain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';

const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run = randomUUID().replaceAll('-', '');
const output = path.join(repoRoot, 'artifacts/unreal/world-builder', run);
const receipt = path.join(repoRoot, 'unreal/AegisWar/Saved/WorldEditProof', run);
const args = parseArguments(process.argv.slice(2), [], ['--review-receipt']);
const review = args.get('--review-receipt');
const base = review ? citadelReviewArguments(repoRoot,
  JSON.parse(readFileSync(review, 'utf8').replace(/^\uFEFF/, '')), projectPath, defaultEngineRoot())
  : [projectPath, officialCapitalMap(), '-game', '-WarDevelopmentGM'];
mkdirSync(output, { recursive: true });
for (const reload of [false, true]) {
  const code = runEngineCommand(engine.editorCommand, [...base, '-unattended', '-nop4', '-nosound', '-nosplash',
    '-RenderOffscreen', '-windowed', '-ForceRes', '-ResX=1920', '-ResY=1080', '-WarDevelopmentGM', '-WarInterfaceProof', '-WarBuilderProof',
    `-WarProofDraftId=${run}`, ...(reload ? ['-WarBuilderReload'] : []),
    `-GameUserSettingsINI=${path.join(output, 'preferences.ini')}`, '-ExecCmds=t.MaxFPS 30',
    `-abslog=${path.join(output, reload ? 'reload.log' : 'game.log')}`]);
  const name = reload ? 'reload-report.json' : 'report.json';
  const file = path.join(receipt, name);
  if (code !== 0 || !existsSync(file)) throw new Error(`World builder proof failed: ${output}; ${receipt}`);
  const result = JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
  if (result.passed !== true || (reload && result.restoredPublication !== true)) throw new Error(`Invalid world builder evidence: ${file}`);
  copyFileSync(file, path.join(output, name));
}
for (const name of ['before.png', 'builder.png', 'preview.png']) copyFileSync(path.join(receipt, name), path.join(output, name));
console.log(JSON.stringify({ worldBuilderProof: true, output,
  map: review ? JSON.parse(readFileSync(review, 'utf8').replace(/^\uFEFF/, '')).map : officialCapitalMap(), sharedPublication: false }));

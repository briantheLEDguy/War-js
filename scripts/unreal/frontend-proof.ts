import { randomUUID } from 'node:crypto';
import { mkdirSync, existsSync, readFileSync, copyFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';

const args = parseArguments(process.argv.slice(2), [], ['--width', '--height']);
const width = Number(args.get('--width') ?? 1920), height = Number(args.get('--height') ?? 1080);
if (![[1280, 720], [1920, 1080], [2560, 1080]].some(([w, h]) => w === width && h === height)) {
  throw new Error('Use 1280×720, 1920×1080 or 2560×1080.');
}
const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run = randomUUID();
const output = path.join(repoRoot, 'artifacts/unreal/frontend', `${width}x${height}-${run}`);
const receipt = path.join(repoRoot, 'unreal/AegisWar/Saved/FrontendProof', run.replaceAll('-', ''));
mkdirSync(output, { recursive: true });
const code = runEngineCommand(engine.editorCommand, [projectPath, '-game', '-unattended', '-nop4', '-nosound', '-nosplash',
  '-RenderOffscreen', '-windowed', '-ForceRes', `-ResX=${width}`, `-ResY=${height}`, '-WarFrontendProof', `-WarFrontendRun=${run}`,
  `-GameUserSettingsINI=${path.join(output, 'preferences.ini')}`, `-ExecCmds=r.SetRes ${width}x${height}w,t.MaxFPS 60`,
  `-abslog=${path.join(output, 'game.log')}`]);
if (code !== 0 || !existsSync(path.join(receipt, 'report.json'))) throw new Error(`Frontend proof failed: ${output}; ${receipt}`);
const report = JSON.parse(readFileSync(path.join(receipt, 'report.json'), 'utf8').replace(/^\uFEFF/, ''));
if (!report.passed) throw new Error(`Frontend proof did not pass: ${JSON.stringify(report)}`);
for (const name of ['report.json', 'login.png', 'prelate.png', 'review.png', 'rotated.png', 'templar.png',
  'arcanist.png', 'warbrute.png', 'riftspire.png', 'reduced-motion.png', 'missing-character.png', 'crossfade.png']) {
  if (!existsSync(path.join(receipt, name))) throw new Error(`Missing frontend evidence: ${name}`);
  copyFileSync(path.join(receipt, name), path.join(output, name));
}
console.log(JSON.stringify({ output, ...report }));

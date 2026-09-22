import { copyFileSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot } from './toolchain';

export function graphicsProofArguments(mode: string, profile: string): string[] {
  if (!['smoke', 'interrupt', 'restart', 'safe'].includes(mode)) throw new Error('Unknown graphics proof mode.');
  if (!/^[a-zA-Z0-9_-]+$/.test(profile)) throw new Error('Profile must be a simple local identifier.');
  const folder = path.join(repoRoot, 'unreal/AegisWar/Saved/GraphicsProof');
  const extra = mode === 'interrupt' ? ['-WarGraphicsProofExit'] : mode === 'restart' ? ['-WarGraphicsProofRestart']
    : mode === 'safe' ? ['-WarSafeGraphics', '-WarGraphicsProofSafeStartup'] : [];
  return [projectPath, '-game', '-windowed', '-ResX=1280', '-ResY=800',
    '-WarDevelopmentGM', '-WarGraphicsProof', '-unattended', '-nosound', '-nop4', '-stdout',
    `-GameUserSettingsINI=${path.join(folder, `GraphicsProof-${profile}.ini`)}`,
    `-abslog=${path.join(folder, `${mode}.log`)}`, ...extra];
}

if (isMain(import.meta.url)) {
  try {
    const args = parseArguments(process.argv.slice(2), [], ['--engine-root', '--mode', '--profile']);
    const mode = args.get('--mode') ?? 'smoke';
    const invocation = graphicsProofArguments(mode, args.get('--profile') ?? 'default');
    const engine = inspectToolchain(args.get('--engine-root') ?? defaultEngineRoot());
    if (engine.blockers.length || !engine.editorCommand) throw new Error(engine.blockers.join('\n'));
    const folder = path.join(repoRoot, 'unreal/AegisWar/Saved/GraphicsProof');
    mkdirSync(folder, { recursive: true });
    const reportPath = path.join(folder, 'report.json');
    rmSync(reportPath, { force: true });
    if (mode === 'interrupt') rmSync(path.join(folder, 'interrupted-cap.txt'), { force: true });
    const result = spawnSync(engine.editorCommand, invocation, { cwd: repoRoot, stdio: 'inherit', timeout: 240_000, windowsHide: true });
    if (result.error || result.status !== 0) throw new Error(`Graphics proof process failed: ${result.error?.message ?? result.status}`);
    if (mode === 'interrupt') {
      const cap = Number(readFileSync(path.join(folder, 'interrupted-cap.txt'), 'utf8').replace(/^\uFEFF/, '').trim());
      if (!Number.isFinite(cap) || cap < 30 || cap > 240) throw new Error('Missing valid forced-exit baseline.');
      console.log(JSON.stringify({ mode, interruptedPreview: true, restartVerificationRequired: true }));
    } else {
      const report = JSON.parse(readFileSync(reportPath, 'utf8').replace(/^\uFEFF/, ''));
      if (report.passed !== true) throw new Error(`Graphics proof failed: ${report.detail}`);
      copyFileSync(reportPath, path.join(folder, `report-${mode}.json`));
      console.log(JSON.stringify({ mode, ...report, reportPath }));
    }
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}

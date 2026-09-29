import { spawnSync } from 'node:child_process';
import { copyFileSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, isMain, projectPath, repoRoot } from './toolchain';

export function validateSiegeTraversal(report: any): void {
  if (report?.passed !== true || report.routesCompleted !== 7 || report.traversalReviewGranted !== false
    || report.gameplayVerified !== false || !Array.isArray(report.walkers) || report.walkers.length !== 12
    || new Set(report.walkers.map((w: any) => w.walker)).size !== 12
    || report.walkers.some((w: any) => !Number.isInteger(w.walker) || w.walker < 0 || w.walker > 11
      || w.jumped !== true || !Number.isFinite(w.distanceCm) || w.distanceCm < 1000)) {
    throw new Error(`Siege traversal did not pass: ${report?.detail ?? 'incomplete movement evidence'}`);
  }
}

if (isMain(import.meta.url)) {
  try {
    const engine = inspectToolchain(defaultEngineRoot());
    if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
    const output = path.join(repoRoot, 'artifacts/unreal/siege/traversal', `${Date.now()}-${process.pid}`);
    mkdirSync(output, { recursive: true });
    const report = path.join(repoRoot, 'unreal/AegisWar/Saved/SiegeTraversal.json');
    rmSync(report, { force: true });
    const invocation = [projectPath, '/Game/Capitals/Siege/AegisCapital_Siege?game=/Script/Engine.GameModeBase',
      '-server', '-nullrhi', '-unattended', '-nop4', '-nosplash', '-nosound', '-stdout', '-FullStdOutLogOutput',
      '-MULTIHOME=127.0.0.1', '-port=0', '-WarDevelopmentNetworking', '-WarSiegeTraversalProof',
      `-abslog=${path.join(output, 'server.log')}`];
    const result = spawnSync(engine.editorCommand, invocation, { cwd: repoRoot, stdio: 'inherit', windowsHide: true, timeout: 950_000 });
    if (result.error) throw result.error;
    copyFileSync(report, path.join(output, 'report.json'));
    const evidence = JSON.parse(readFileSync(report, 'utf8').replace(/^\uFEFF/, ''));
    if (result.status !== 0) throw new Error(`Traversal failed: ${evidence.detail}. See ${output}`);
    validateSiegeTraversal(evidence);
    console.log(JSON.stringify({ traversalPassed: true, output, gameplayVerified: false, reviewGranted: false }));
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}

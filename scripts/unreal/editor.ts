import { mkdirSync, readFileSync, rmSync } from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';

export const requiredNativeTests = [
  'VerifiedVisualImportBindings', 'ContentContract', 'CombatBoundaries',
  'ClosedProductionAdmission', 'NoPrimitiveVisualFallback',
  'PlayerStateAbilityOwnership', 'SpawnFailureReporting',
  'InventoryRewardParity', 'InventoryAuthority', 'CraftingCatalogAndRules',
].map(name => `AegisWar.Foundation.${name}`);

export function validateAutomationReport(report: unknown): number {
  if (!report || typeof report !== 'object') throw new Error('Unreal did not produce an automation report.');
  const data = report as Record<string, unknown>;
  const tests = data.tests as Array<{ fullTestPath?: string; state?: string; errors?: number }> | undefined;
  if (!Array.isArray(tests) || tests.length < requiredNativeTests.length) throw new Error('The complete native foundation suite did not run.');
  for (const field of ['succeeded', 'succeededWithWarnings', 'failed', 'notRun', 'inProcess']) {
    if (typeof data[field] !== 'number' || !Number.isInteger(data[field]) || Number(data[field]) < 0) throw new Error(`Missing or invalid automation total ${field}.`);
  }
  if (data.failed !== 0 || data.notRun !== 0 || data.inProcess !== 0) throw new Error('Native tests failed or did not finish.');
  if (Number(data.succeeded) + Number(data.succeededWithWarnings) !== tests.length) throw new Error('Native result counts do not match the executed tests.');
  for (const test of tests) {
    if (!test.fullTestPath?.startsWith('AegisWar.Foundation.') || test.state !== 'Success' || test.errors !== 0) {
      throw new Error(`Unexpected or unsuccessful native test: ${test.fullTestPath ?? 'unnamed'}`);
    }
  }
  const names = new Set(tests.map(test => test.fullTestPath));
  if (names.size !== tests.length || requiredNativeTests.some(name => !names.has(name))) {
    throw new Error('The complete native foundation suite did not run exactly once.');
  }
  return tests.length;
}

export function validateImportReceipt(report: unknown, profile: string, conversionHash: string): void {
  const data = report as Record<string, unknown> | null;
  if (!data || data.schemaVersion !== 1 || data.profileKey !== profile || data.importSucceeded !== true
    || data.status !== 'editor-import-succeeded-unreviewed' || data.conversionSha256 !== conversionHash
    || data.artApproved !== false || data.unrealApproved !== false || !String(data.unrealVersion).startsWith('5.8.2-')
    || !Array.isArray(data.meshes) || data.meshes.length === 0) throw new Error('Missing, stale or invalid Unreal import evidence.');
  if (data.kind === 'characterProfiles') {
    const poses = data.poseParity as { status?: string; toleranceCm?: number; clips?: unknown[] } | undefined;
    if (poses?.status !== 'passed' || poses.toleranceCm !== 0.1 || !Array.isArray(poses.clips)
      || !Array.isArray(data.animations) || poses.clips.length !== data.animations.length * 2 || !poses.clips.length) {
      throw new Error('Missing or invalid Unreal skinning parity evidence.');
    }
  }
}

if (isMain(import.meta.url)) {
  try {
    const args = parseArguments(process.argv.slice(2), [], ['--engine-root', '--mode', '--profile']);
    const mode = args.get('--mode') ?? 'test';
    if (!['test', 'import'].includes(mode)) throw new Error('Editor mode must be test or import.');
    const report = inspectToolchain(args.get('--engine-root') ?? defaultEngineRoot());
    if (report.blockers.length || !report.editorCommand) throw new Error(report.blockers.join('\n'));
    const output = path.join(repoRoot, 'artifacts/unreal/editor', `${mode}-${Date.now()}-${process.pid}`);
    mkdirSync(output, { recursive: true });
    const common = [projectPath, '-unattended', '-nop4', '-nosplash', '-nosound', '-stdout', '-FullStdOutLogOutput', `-abslog=${path.join(output, 'editor.log')}`];
    let invocation: string[];
    if (mode === 'test') invocation = [...common, '-nullrhi', '-ExecCmds=Automation RunTests AegisWar.Foundation', '-TestExit=Automation Test Queue Empty', `-ReportExportPath=${output}`];
    else {
      const profile = args.get('--profile');
      if (!profile || !/^[a-zA-Z0-9_-]+$/.test(profile)) throw new Error('Model import requires a safe --profile registry key.');
      // An editor exit code cannot attest that Python ran or wrote fresh evidence.
      rmSync(path.join(repoRoot, 'artifacts/unreal/converted', profile, 'editor-import.json'), { force: true });
      const script = path.join(repoRoot, 'scripts/unreal/import-models.py');
      invocation = [...common, '-nullrhi', '-run=pythonscript', `-script=${script} --profile ${profile}`];
    }
    const code = runEngineCommand(report.editorCommand, invocation);
    if (code !== 0) throw new Error(`Unreal editor exited ${code}; see ${output}`);
    if (mode === 'test') {
      const data = JSON.parse(readFileSync(path.join(output, 'index.json'), 'utf8').replace(/^\uFEFF/, ''));
      console.log(JSON.stringify({ nativeTestsPassed: validateAutomationReport(data), report: output, graphicalAcceptance: false }));
    } else {
      const profile = args.get('--profile')!;
      const directory = path.join(repoRoot, 'artifacts/unreal/converted', profile);
      const hash = createHash('sha256').update(readFileSync(path.join(directory, 'conversion.json'))).digest('hex');
      validateImportReceipt(JSON.parse(readFileSync(path.join(directory, 'editor-import.json'), 'utf8')), profile, hash);
      console.log(JSON.stringify({ importEvidenceVerified: true, profile, log: output, visualApproval: false }));
    }
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}

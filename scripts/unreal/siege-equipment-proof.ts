import { spawnSync } from 'node:child_process';
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { siegeContentEvidence, candidateSiegeContentEvidence, requireSameSiegeContent } from './siege-content-evidence';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot } from './toolchain';

export function validateSiegeEquipment(report: any): void {
  if (report?.passed !== true || report.checkpoints !== 3 || report.stoppedWithoutEscort !== true
    || report.overlapRecoveredWithoutDamage !== true || report.gateCollisionVerified !== true
    || report.stoppedWithoutCrew !== true || report.ramStrikeAdvanced !== true || !Array.isArray(report.vehicles) || report.vehicles.length !== 2
    || report.vehicles.some((vehicle: any) => !Number.isFinite(vehicle.travelCm) || vehicle.travelCm < 24000)) {
    throw new Error(`Siege equipment proof failed: ${report?.detail ?? 'missing movement evidence'}`);
  }
}

if (isMain(import.meta.url)) {
  try {
    const args = parseArguments(process.argv.slice(2), [], ['--map']);
    const map = args.get('--map') ?? '/Game/Capitals/Siege/AegisCapital_Siege';
    const engine = inspectToolchain(defaultEngineRoot());
    if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
    const output = path.join(repoRoot, 'artifacts/unreal/siege/equipment/traversal', `${Date.now()}-${process.pid}`);
    mkdirSync(output, { recursive: true });
    const report = path.join(repoRoot, 'unreal/AegisWar/Saved/SiegeEquipment.json');
    const content = map === '/Game/Capitals/Siege/AegisCapital_Siege'
      ? siegeContentEvidence(repoRoot) : candidateSiegeContentEvidence(repoRoot, map);
    rmSync(report, { force: true });
    const result = spawnSync(engine.editorCommand, [projectPath,
      `${map}?game=/Script/Engine.GameModeBase`, '-server', '-nullrhi',
      '-unattended', '-nop4', '-nosplash', '-nosound', '-MULTIHOME=127.0.0.1', '-port=0',
      '-WarDevelopmentNetworking', '-WarSiegeEquipmentProof', `-WarSiegeEquipmentProofMap=${map}`,
      `-abslog=${path.join(output, 'server.log')}`],
    { cwd: repoRoot, stdio: 'inherit', windowsHide: true, timeout: 460_000 });
    if (result.error) throw result.error;
    const evidence = JSON.parse(readFileSync(report, 'utf8').replace(/^\uFEFF/, ''));
    requireSameSiegeContent(content, map === '/Game/Capitals/Siege/AegisCapital_Siege'
      ? siegeContentEvidence(repoRoot) : candidateSiegeContentEvidence(repoRoot, map));
    writeFileSync(path.join(output, 'report.json'), JSON.stringify({ ...evidence, ...content }, null, 2) + '\n');
    validateSiegeEquipment(evidence);
    if (result.status !== 0) throw new Error(`Native equipment proof exited ${result.status}`);
    console.log(JSON.stringify({ passed: true, output }));
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}

import { spawn } from 'node:child_process';
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { candidateSiegeContentEvidence, requireSameSiegeContent, type CandidateSiegeContentEvidence } from './siege-content-evidence';
import { campaignCandidateContentEvidence, startNativeSiegeProofAuthority } from '../../server/nativeSiegeProof';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot } from './toolchain';
import { citadelPerformanceConfig, requireSamePerformanceFiles, validateCitadelPerformance,
  type CitadelPerformanceConfig } from './citadel-performance';
import { citadelPerformanceBaselineEvidence } from './citadel-performance-baseline';

export interface CitadelSiegeProofConfig extends CandidateSiegeContentEvidence {
  proofOnly: true;
  contentReviewOverride: true;
  players?: string[];
  performance?: CitadelPerformanceConfig;
  performanceBaseline?: true;
  isolatedStageWindows?: false;
  fixtureMode?: 'earned_progression';
  campaignOutcome?: 'city_captured' | 'city_defended';
}
export function citadelDefendedProofConfig(config: CitadelSiegeProofConfig): CitadelSiegeProofConfig {
  if (!config.map.endsWith('/CampaignCandidate') || config.performance || config.performanceBaseline)
    throw new Error('The defended fixture requires a fresh CampaignCandidate authority without performance orders.');
  return { ...config, campaignOutcome: 'city_defended' };
}
export function citadelSiegeProofConfig(repositoryRoot: string, map: string): CitadelSiegeProofConfig {
  const evidence = map.endsWith('/CampaignCandidate') ? campaignCandidateContentEvidence(repositoryRoot, map)
    : candidateSiegeContentEvidence(repositoryRoot, map);
  return { ...evidence, proofOnly: true, contentReviewOverride: true,
    ...(map.endsWith('/CampaignCandidate') ? { players: ['aegis', 'riftbound'].flatMap(realm =>
      Array.from({ length: 18 }, (_, i) => `proof-${evidence.signature.slice(0, 12)}-${realm}-${i}`)) } : {}) };
}
export function validateCitadelSiegeProof(report: any, config: CitadelSiegeProofConfig): void {
  const live = config.map.endsWith('/CampaignCandidate');
  const defended = live && config.campaignOutcome === 'city_defended';
  if (config.campaignOutcome && (!live || !['city_captured', 'city_defended'].includes(config.campaignOutcome)))
    throw new Error('The requested campaign outcome is not a live private fixture.');
  if (report?.passed !== true || report.map !== config.map || report.signature !== config.signature
    || report.mapSha256 !== config.mapSha256 || report.cityRevision !== config.cityRevision
    || report.proofOnly !== true || report.transientReviewOverride !== true
    || report.productionAdmission !== false || report.steamAdmission !== false || report.visualApproval !== false
    || report.humanPlaytest !== false || report.reconnectVerified !== false
    || report.normalCharacterRecoveryVerified !== false || report.campaignHumanEnrollmentVerified !== false
    || report.encounterScopedCleanupVerified !== !live
    || report.syntheticNormalControllers !== live || report.trustedSettlementAcknowledged !== live
    || report.maxAegis !== 18 || report.maxRiftbound !== 18 || report.concurrentSides !== !defended
    || report.lockedCenterObserved !== !defended || !Number.isFinite(report.movementCm) || report.movementCm <= 10_000
    || !Number.isInteger(report.normalAbilityActivations) || report.normalAbilityActivations < 1
    || !Array.isArray(report.rounds) || report.rounds.length !== (live ? 1 : 2)
    || !Array.isArray(report.samples) || !report.samples.length)
    throw new Error('Physical siege fixture is failed, incomplete, for another candidate, or claims unverified admission.');
  const win = report.rounds[0];
  if (live && (report.campaignOutcome !== (defended ? 'city_defended' : 'city_captured')
    || report.trustedSettlementResult !== report.campaignOutcome
    || typeof report.settledActivationId !== 'string' || !report.settledActivationId))
    throw new Error('The actual owning native host did not receive its matching durable Node settlement.');
  if (defended) {
    if (win.phase !== 'finished' || win.stage !== 0 || win.attackersWon !== false
      || JSON.stringify(win.completed) !== '[]' || !Number.isFinite(win.elapsed) || win.elapsed < 840 - 1e-6 || win.elapsed > 840.05 + 1e-6
      || !report.samples.every((sample: any) => sample.stage === 0 && JSON.stringify(sample.completed) === '[]')
      || report.preparationObserved !== true || report.servicesSuspendedObserved !== true
      || report.servicesRestoredObserved !== true || report.custodyMovementHeldObserved !== true)
      throw new Error('The live defense did not retain real preparation, zero claims, custody and the ordinary stage timeout.');
    const expected = config.players;
    const rows = report.normalCharacters;
    if (!Array.isArray(expected) || expected.length !== 36 || new Set(expected).size !== 36
      || !Array.isArray(rows) || rows.length !== 36 || new Set(rows.map((row: any) => row.characterId)).size !== 36
      || rows.some((row: any, i: number) => row.characterId !== expected[i]
        || row.realm !== (i < 18 ? 'aegis' : 'riftbound') || row.normalized !== false || row.combatLevel !== 40
        || row.inventoryUnchanged !== true || !/^[a-f0-9]{64}$/.test(row.inventorySha256)
        || row.initialInventorySha256 !== row.inventorySha256 || !Number.isInteger(row.inventoryRevision) || row.inventoryRevision < 0
        || typeof row.transferPending !== 'boolean' || typeof row.movementHeld !== 'boolean'
        || typeof row.hasAvatar !== 'boolean' || typeof row.alive !== 'boolean' || typeof row.modelReady !== 'boolean'
        || (row.transferPending && row.hasAvatar && !row.movementHeld)
        || (row.alive && (!row.hasAvatar || !row.modelReady)) || typeof row.zone !== 'string' || !row.zone
        || !Number.isFinite(row.health) || row.health < 0 || !Number.isFinite(row.mana) || row.mana < 0))
      throw new Error('The actual normal 18v18 character inventories, progression or custody witnesses are incomplete.');
    return;
  }
  if (win.phase !== 'finished' || win.stage !== 2 || win.attackersWon !== true
    || JSON.stringify(win.completed) !== '[0,1,2,3,4,5,6,7]' || win.elapsed <= 0 || win.elapsed > 3001)
    throw new Error('The attacker fixture did not physically complete all eight objectives.');
  if (!live && (report.rounds[1].phase !== 'finished' || report.rounds[1].attackersWon !== false
    || report.rounds[1].stage !== 0 || report.rounds[1].elapsed < 840 - 1e-6 || report.rounds[1].elapsed > 960))
    throw new Error('The defended fixture did not use the ordinary bounded stage timeout.');
  if (!report.samples.some((sample: any) => sample.stage === 1 && sample.leftProgress > 0 && sample.rightProgress > 0))
    throw new Error('Concurrent physical side objective evidence is missing.');
}

async function execute(command: string, args: string[], output: string): Promise<number> {
  return await new Promise<number>((resolve, reject) => {
    const process = spawn(command, args, { cwd: repoRoot, stdio: 'inherit', windowsHide: true });
    const timer = setTimeout(() => { process.kill(); reject(new Error(`Physical siege fixture exceeded its real-time deadline. See ${output}`)); }, 4_050_000);
    process.once('error', error => { clearTimeout(timer); reject(error); });
    process.once('exit', code => { clearTimeout(timer); resolve(code ?? -1); });
  });
}

if (isMain(import.meta.url)) {
  const args = parseArguments(process.argv.slice(2), ['--dry-run', '--performance', '--performance-baseline', '--defended'],
    ['--map', '--blueprint', '--performance-binary', '--graphics-settings']);
  const map = args.get('--map') ?? '';
  let authority: Awaited<ReturnType<typeof startNativeSiegeProofAuthority>> | undefined;
  try {
    const baseline = args.has('--performance-baseline') ? citadelPerformanceBaselineEvidence(repoRoot, map) : undefined;
    let config: CitadelSiegeProofConfig = baseline ? { ...baseline, proofOnly: true, contentReviewOverride: true,
      performanceBaseline: true, isolatedStageWindows: false, fixtureMode: 'earned_progression' } : citadelSiegeProofConfig(repoRoot, map);
    if (args.has('--defended')) {
      if (args.has('--performance')) throw new Error('The defended fixture retains ordinary timeout tactics without benchmark orders.');
      config = citadelDefendedProofConfig(config);
    }
    const engine = inspectToolchain(defaultEngineRoot());
    if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
    const id = `siege-${Date.now()}-${process.pid}`;
    const saved = path.join(repoRoot, 'unreal/AegisWar/Saved/CitadelSiegeProof', id);
    const output = path.join(repoRoot, 'artifacts/unreal/citadel-reference/siege-proofs', id);
    const configFile = path.join(saved, 'config.json');
    if (args.has('--performance') || baseline) {
      const revision = /^\/Game\/WorldRebuild\/AegisCitadel_([a-f0-9]{12})\//.exec(map)?.[1];
      if (!revision || !args.get('--graphics-settings'))
        throw new Error('Rendered performance needs an exact signed candidate and an existing normal --graphics-settings INI.');
      config.performance = citadelPerformanceConfig(repoRoot, config,
        path.resolve(args.get('--blueprint') ?? baseline?.baselinePath ?? path.join(repoRoot, 'artifacts/unreal/aegis-citadel', revision, 'blueprint.json')),
        args.get('--graphics-settings')!, path.join(saved, 'benchmark.ini'), args.get('--performance-binary'));
    }
    const invocation = [projectPath, `${map}?game=/Script/AegisWar.${map.endsWith('/CampaignCandidate') ? 'WarGameMode' : 'WarSiegeGameMode'}`,
      '-game', '-unattended', '-nop4', '-nosplash', '-nosound', '-WarDevelopmentNetworking',
      ...(config.performance ? ['-WarCitadelSiegePerformance', '-RenderOffscreen', '-windowed', '-ForceRes',
        '-ResX=1920', '-ResY=1080', '-ExecCmds=t.MaxFPS 0,r.VSync 0,r.ScreenPercentage 100,r.DynamicRes.OperationMode 0',
        '-ini:Engine:[/Script/Engine.Engine]:bSmoothFrameRate=False,bUseFixedFrameRate=False',
        `-GameUserSettingsINI=${config.performance.settingsPath}`] : ['-nullrhi']),
      ...(baseline ? ['-WarCitadelSiegePerformanceBaseline'] : []),
      '-WarCitadelSiegeProof', `-WarCitadelSiegeProofConfig=${configFile}`, `-abslog=${path.join(output, 'native.log')}`];
    if (args.has('--dry-run')) {
      console.log(JSON.stringify({ command: engine.editorCommand, arguments: invocation, config,
        realTimers: true, automatedTactics: true, humanAcceptance: false, executed: false }, null, 2));
    } else {
      mkdirSync(saved, { recursive: true }); mkdirSync(output, { recursive: true });
      if (config.performance) copyFileSync(path.resolve(args.get('--graphics-settings')!), config.performance.settingsPath);
      writeFileSync(configFile, JSON.stringify(config, null, 2) + '\n');
      if (config.performance) requireSamePerformanceFiles(config.performance);
      if (map.endsWith('/CampaignCandidate')) {
        authority = await startNativeSiegeProofAuthority({ repositoryRoot: repoRoot, map, fixtureId: id });
        invocation.push(`-WarCampaignSiegeHostConfig=${authority.hostConfigPath}`);
      }
      const exitCode = await execute(engine.editorCommand, invocation, output);
      for (const file of ['config.json', 'report.json', ...(config.performance ? ['performance-report.json', 'performance-frames.json'] : [])])
        if (existsSync(path.join(saved, file))) copyFileSync(path.join(saved, file), path.join(output, file));
      if (exitCode !== 0) throw new Error(`Native siege fixture exited ${exitCode}. See ${output}`);
      const report = JSON.parse(readFileSync(path.join(saved, 'report.json'), 'utf8').replace(/^\uFEFF/, ''));
      const after = baseline ? citadelPerformanceBaselineEvidence(repoRoot, map) : citadelSiegeProofConfig(repoRoot, map);
      requireSameSiegeContent(config, after);
      if (config.performance) requireSamePerformanceFiles(config.performance);
      writeFileSync(path.join(output, 'report.json'), JSON.stringify(report, null, 2) + '\n');
      if (!baseline) validateCitadelSiegeProof(report, config);
      let performanceWindows;
      if (config.performance) {
        const performanceFile = path.join(saved, 'performance-report.json'), framesFile = path.join(saved, 'performance-frames.json');
        copyFileSync(performanceFile, path.join(output, 'performance-report.json'));
        copyFileSync(framesFile, path.join(output, 'performance-frames.json'));
        const performance = JSON.parse(readFileSync(performanceFile, 'utf8').replace(/^\uFEFF/, ''));
        const frames = JSON.parse(readFileSync(framesFile, 'utf8').replace(/^\uFEFF/, ''));
        const { createHash } = await import('node:crypto');
        const digest = (file: string) => createHash('sha256').update(readFileSync(file)).digest('hex');
        if (performance.configSha256 !== digest(configFile) || path.resolve(performance.frames.path) !== path.resolve(framesFile)
          || performance.frames.sha256 !== digest(framesFile))
          throw new Error('Rendered native report is not bound to the actual config and flushed frame file.');
        performanceWindows = validateCitadelPerformance(performance, frames, config, !baseline);
      }
      console.log(JSON.stringify({ passed: true, output, fixtureOnly: true, fullSiegeAdmission: false,
        ...(performanceWindows ? { performanceWindows, baselineVerified: false, isolatedStageWindows: false,
          ...(baseline ? { fixtureMode: 'earned_progression' } : {}) } : {}) }));
    }
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
  finally { await authority?.close(); }
}

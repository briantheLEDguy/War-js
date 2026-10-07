import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { requireNativePackageHash } from './native-package-evidence';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot } from './toolchain';

/** Launch preserved review content or the exact configured Development campaign. */
export function citadelReviewArguments(repository: string, receipt: any, project: string, engineRoot?: string): string[] {
  const campaign = /^\/Game\/WorldRebuild\/AegisCitadel_([a-f0-9]{12})\/CampaignCandidate$/.exec(receipt?.map ?? '');
  const match = /^\/Game\/WorldRebuild\/CitadelHumanReview_(\d{8})_([a-f0-9]{12})\/Walkthrough$/.exec(receipt?.map ?? '');
  const date = match && `${match[1].slice(0, 4)}-${match[1].slice(4, 6)}-${match[1].slice(6, 8)}`;
  const parsed = date ? new Date(date + 'T00:00:00Z') : undefined;
  const validReview = match && parsed && Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === date
    && parsed.getUTCFullYear() >= 1;
  if ((!campaign && !validReview) || receipt.schemaVersion !== 1
    || !/^[a-f0-9]{64}$/.test(receipt.signature ?? '') || receipt.signature.slice(0, 12) !== (campaign?.[1] ?? match?.[2])
    || !/^[a-f0-9]{12}$/.test(receipt.sourceRevision ?? '') || receipt.sourcePackagesUnchanged !== true
    || receipt.requiresDevelopmentGM !== true || receipt.ordinaryLocalDevelopmentEntry !== true
    || receipt.servicesRetained !== true || receipt.residentPopulationPrivateReviewOnly !== !campaign
    || receipt.visualApproved !== false || receipt.gameplayApproved !== false || receipt.published !== false
    || receipt.directedRoutes !== 70 || receipt.zones !== 32
    || !Array.isArray(receipt.streamingDeclarations) || receipt.streamingDeclarations.length < 70
    || receipt.streamingDeclarations.length > 512)
    throw new Error('Expected a complete, preserved private citadel review receipt.');
  const prefix = receipt.map.slice(0, -(campaign ? '/CampaignCandidate' : '/Walkthrough').length);
  if (receipt.routing !== prefix + (campaign ? '/CampaignRoutingCandidate' : '/ReviewRouting')
    || receipt.population !== prefix + (campaign ? '/Layers/Residents' : '/Residents_' + match![2])
    || receipt.city !== `/Game/WorldRebuild/AegisCitadel_${receipt.sourceRevision}/City`
    || !/^[a-f0-9]{64}$/.test(receipt.cityRevision ?? ''))
    throw new Error('Private review package identities differ from the staged revision.');
  const owned = receipt.packageHashes, sources = receipt.sourcePackageHashes;
  if (!owned || !sources || Object.keys(owned).length !== 3 || !Object.keys(sources).length
    || owned[receipt.map] !== receipt.mapSha256 || !owned[receipt.routing] || !owned[receipt.population]
    || !sources[receipt.city] || Object.keys(owned).some(name => !name.startsWith(prefix + '/'))
    || Object.keys(sources).some(name => Object.hasOwn(owned, name)))
    throw new Error('Private review package ownership or protected source evidence is incomplete.');
  const declarations: unknown[] = receipt.streamingDeclarations;
  if (!declarations.includes(receipt.routing) || !declarations.includes(receipt.population)
    || declarations.includes(receipt.map) || declarations.some(name => typeof name !== 'string'
      || !/^\/Game\/[A-Za-z0-9_]+(?:\/[A-Za-z0-9_]+)+$/.test(name)
      || (!Object.hasOwn(owned, name) && !Object.hasOwn(sources, name))))
    throw new Error('Every native streaming declaration must retain its protected package binding.');
  for (const [name, hash] of Object.entries({ ...sources, ...owned }))
    requireNativePackageHash(repository, name, hash, engineRoot);
  if (campaign) {
    const config = readFileSync(path.join(repository, 'unreal/AegisWar/Config/DefaultEngine.ini'), 'utf8');
    const selected = config.split(/\r?\n/).filter(line => line.startsWith('GameDefaultMap='));
    if (receipt.developmentOnly !== true || receipt.defaultMapSelected !== true || receipt.fullSiegeAdmissionApproved !== false
      || receipt.sourceRevision !== campaign[1] || receipt.launchSelectedMapArgument !== ''
      || selected.length !== 1 || selected[0] !== 'GameDefaultMap=' + receipt.map)
      throw new Error('Development campaign proof requires the actual configured default without overrides or acceptance.');
    return [project, '-game', '-WarDevelopmentGM', '-windowed', '-nosplash', '-nop4'];
  }
  const selected = `-ini:Engine:[/Script/EngineSettings.GameMapsSettings]:GameDefaultMap=${receipt.map}`;
  if (receipt.launchSelectedMapArgument !== selected)
    throw new Error('Review map selection must match the staged process-local override.');
  return [project, receipt.map, '-game', '-WarDevelopmentGM', selected, '-windowed', '-nosplash', '-nop4'];
}

if (isMain(import.meta.url)) {
  try {
    const args = parseArguments(process.argv.slice(2), ['--dry-run'], ['--receipt']);
    if (!args.get('--receipt')) throw new Error('Pass the exact staged private review receipt with --receipt.');
    const receipt = JSON.parse(readFileSync(args.get('--receipt')!, 'utf8').replace(/^\uFEFF/, ''));
    const invocation = citadelReviewArguments(repoRoot, receipt, projectPath, defaultEngineRoot());
    const engine = inspectToolchain(defaultEngineRoot());
    if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
    const executable = engine.editorCommand.replace(/-Cmd\.exe$/i, '.exe');
    if (args.has('--dry-run')) console.log(JSON.stringify({ executable, arguments: invocation,
      nativePackagesVerified: true, executed: false, visualApproved: false }, null, 2));
    else {
      const result = spawnSync(executable, invocation, { cwd: repoRoot, stdio: 'inherit', windowsHide: false });
      if (result.error || result.status !== 0) throw new Error(`Private review exited unsuccessfully: ${result.error?.message ?? result.status}`);
    }
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}

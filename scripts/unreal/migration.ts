import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { buildContentManifest, canonicalJson } from './export-content';
import { buildAssetLedger } from './asset-ledger';
import { parityFeatures, validateParityLedger } from './feature-parity';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, repoRoot, type ToolchainReport } from './toolchain';
import { stageDevelopmentContent } from './stage-content';

export interface ReadinessInput {
  assets: { assignmentCount: number; ready: number; packagingReady: boolean; blocked: number };
  features: Array<{ id: string; unrealStatus: string }>;
  toolchain: ToolchainReport;
}

export function releaseBlockers(input: ReadinessInput): string[] {
  const blockers = [...input.toolchain.blockers];
  if (!input.assets.packagingReady || input.assets.assignmentCount === 0 || input.assets.ready !== input.assets.assignmentCount) {
    blockers.push(`Model coverage is not approved in Unreal: ${input.assets.ready}/${input.assets.assignmentCount} ready, ${input.assets.blocked} blocked before import review.`);
  }
  const pending = input.features.filter(feature => feature.unrealStatus !== 'verified');
  if (!input.features.length) blockers.push('The feature parity ledger is empty.');
  if (pending.length) blockers.push(`Native gameplay acceptance is pending for ${pending.length} contracts: ${pending.map(feature => feature.id).join(', ')}.`);
  // No native build/Steam/QA receipt importer exists yet; absence must not become success.
  blockers.push('Windows, Linux and macOS packaged build/playtest acceptance has not been recorded.');
  blockers.push('Production Steam ownership, hosted persistence and 18v18 resilience acceptance have not been recorded.');
  return blockers;
}

export async function runMigration(args: string[]): Promise<number> {
  const options = parseArguments(args, ['--strict', '--stage-development'], ['--engine-root']);
  if (options.has('--strict') && options.has('--stage-development')) throw new Error('Strict release checking cannot stage development content.');
  const ledgerErrors = validateParityLedger();
  if (ledgerErrors.length) throw new Error(ledgerErrors.join('\n'));
  const content = await buildContentManifest();
  const assets = await buildAssetLedger();
  const toolchain = inspectToolchain(options.get('--engine-root') ?? defaultEngineRoot());
  const blockers = releaseBlockers({ assets: assets.summary, features: parityFeatures, toolchain });
  const readiness = {
    schemaVersion: 1, readyForRelease: blockers.length === 0,
    contentSourceSha256: content.source.sha256, contentSha256: content.source.contentSha256,
    content: { campaignMaps: content.maps.length, developmentMaps: content.developmentMaps.length,
      playableVariants: content.careers.playableProfiles.length, abilities: content.abilities.definitions.length,
      items: content.items.definitions.length, quests: content.quests.length, builderPrefabs: content.builder.prefabs.length },
    assets: assets.summary, featureContracts: parityFeatures.length, toolchain, blockers,
    stages: [
      { stage: 0, status: 'inventory-implemented-review-pending' },
      { stage: 1, status: 'foundation-in-progress-native-verification-pending' },
      ...[2, 3, 4, 5, 6, 7].map(stage => ({ stage, status: 'not-complete' })),
    ],
  };
  const output = path.join(repoRoot, 'artifacts/unreal');
  await mkdir(output, { recursive: true });
  await writeFile(path.join(output, 'content.json'), canonicalJson(content));
  await writeFile(path.join(output, 'asset-ledger.json'), JSON.stringify(assets, null, 2) + '\n');
  await writeFile(path.join(output, 'feature-parity.json'), canonicalJson({ schemaVersion: 1, features: parityFeatures }));
  await writeFile(path.join(output, 'readiness.json'), canonicalJson(readiness));
  if (options.has('--stage-development')) {
    await stageDevelopmentContent(content, repoRoot);
  }
  console.log(JSON.stringify({ content: readiness.content, assets: assets.summary,
    featureContracts: readiness.featureContracts, readyForRelease: readiness.readyForRelease,
    blockerCount: blockers.length, report: 'artifacts/unreal/readiness.json', developmentContentStaged: options.has('--stage-development') }, null, 2));
  return options.has('--strict') && blockers.length ? 1 : 0;
}

if (isMain(import.meta.url)) runMigration(process.argv.slice(2)).then(code => { process.exitCode = code; })
  .catch(error => { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; });

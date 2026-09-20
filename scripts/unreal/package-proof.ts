import { existsSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';

// This packages a Development feasibility map; release acceptance remains a separate closed gate.
const args = parseArguments(process.argv.slice(2), ['--dry-run'], ['--engine-root', '--platform']);
const platform = args.get('--platform') ?? 'Win64';
if (!['Win64', 'Linux', 'Mac'].includes(platform)) throw new Error('Unsupported proof platform.');
const engine = inspectToolchain(args.get('--engine-root') ?? defaultEngineRoot());
if (engine.blockers.length || !engine.automationCommand) throw new Error(engine.blockers.join('\n'));
if (!existsSync(path.join(repoRoot, 'artifacts/unreal/proof-map.json'))) throw new Error('Prepare the proof map first.');
const archive = path.join(repoRoot, 'artifacts/unreal/packages', platform);
const options = ['BuildCookRun', `-project=${projectPath}`, '-target=AegisWar', '-noP4', `-platform=${platform}`,
  '-clientconfig=Development', '-build', '-cook', '-map=/Game/MigrationProof/EngineProof', '-stage', '-pak',
  '-archive', `-archivedirectory=${archive}`, '-utf8output', '-unattended'];
console.log(JSON.stringify({ developmentProofOnly: true, platform, archive, command: engine.automationCommand, options }));
if (!args.has('--dry-run')) process.exitCode = runEngineCommand(engine.automationCommand, options);

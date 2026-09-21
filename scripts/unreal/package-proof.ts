import { existsSync } from 'node:fs';
import path from 'node:path';
import { officialCapitalMap } from './capital-map';
import { defaultEngineRoot, inspectToolchain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';

// This packages a Development feasibility map; release acceptance remains a separate closed gate.
const args = parseArguments(process.argv.slice(2), ['--dry-run', '--include-capital', '--include-kit-pilot', '--include-crownward'], ['--engine-root', '--platform']);
const platform = args.get('--platform') ?? 'Win64';
if (!['Win64', 'Linux', 'Mac'].includes(platform)) throw new Error('Unsupported proof platform.');
const engine = inspectToolchain(args.get('--engine-root') ?? defaultEngineRoot());
if (engine.blockers.length || !engine.automationCommand) throw new Error(engine.blockers.join('\n'));
if (!existsSync(path.join(repoRoot, 'artifacts/unreal/proof-map.json'))) throw new Error('Prepare the proof map first.');
const archive = path.join(repoRoot, 'artifacts/unreal/packages', platform);
const maps = ['/Game/MigrationProof/EngineProof'];
if (args.has('--include-capital')) {
  if (!existsSync(path.join(repoRoot, 'artifacts/unreal/capitals/aegis_capital/buildings-import.json')))
    throw new Error('Prepare the authored capital workbench before including it in a development package.');
  maps.push('/Game/Capitals/aegis_capital/AegisCapital_Workbench');
}
if (args.has('--include-kit-pilot')) {
  if (!existsSync(path.join(repoRoot, 'artifacts/unreal/licensed-kits/house-kit-pilot.json')))
    throw new Error('Prepare the local licensed-kit pilot before including it in a development package.');
  maps.push('/Game/Capitals/kit_pilot/AegisCapital_Workbench');
}
if (args.has('--include-crownward')) {
  if (!existsSync(path.join(repoRoot, 'artifacts/unreal/licensed-kits/capital-kit-build.json')))
    throw new Error('Build the integrated kit capital before packaging it.');
  maps.push(officialCapitalMap());
}
const options = ['BuildCookRun', `-project=${projectPath}`, '-target=AegisWar', '-noP4', `-platform=${platform}`,
  '-clientconfig=Development', '-build', '-cook', `-map=${maps.join('+')}`, '-stage', '-pak',
  '-archive', `-archivedirectory=${archive}`, '-utf8output', '-unattended'];
console.log(JSON.stringify({ developmentProofOnly: true, platform, archive, command: engine.automationCommand, options }));
if (!args.has('--dry-run')) process.exitCode = runEngineCommand(engine.automationCommand, options);

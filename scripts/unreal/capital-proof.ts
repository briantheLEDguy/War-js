import { mkdirSync, readFileSync, existsSync, copyFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { sha256 } from './content-contract';
import { CAPITAL_HOUSE_PROFILES } from './capital-props';
import { defaultEngineRoot, inspectToolchain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';

const args = parseArguments(process.argv.slice(2), ['--rendered'], ['--engine-root', '--packaged-root']);
const packagedRoot = args.get('--packaged-root') ? path.resolve(repoRoot, args.get('--packaged-root')!) : undefined;
const packagedClient = packagedRoot ? path.join(packagedRoot, 'AegisWar/Binaries/Win64/AegisWar.exe') : undefined;
if (packagedClient && !existsSync(packagedClient)) throw new Error('Packaged Windows client is missing.');
const engine = inspectToolchain(args.get('--engine-root') ?? defaultEngineRoot());
if (!packagedClient && !engine.editorCommand) throw new Error('Unreal Editor command executable is unavailable.');
const directory = path.join(repoRoot, 'artifacts/unreal/capitals/aegis_capital');
const placements = JSON.parse(readFileSync(path.join(directory, 'buildings-import.json'), 'utf8'));
if (placements.sourceSha256 !== sha256(readFileSync(path.join(repoRoot, 'public/assets/maps/aegis_capital.json')))
  || placements.propsInputSha256 !== sha256(readFileSync(path.join(directory, 'props.json')))) throw new Error('Rebuild capital placements before runtime acceptance.');
const propDocument = JSON.parse(readFileSync(path.join(directory, 'props.json'), 'utf8'));
const expectedIds = new Set(propDocument.housePlacements.map((row: { id: string }) => row.id));
if (!Array.isArray(placements.placed) || placements.placed.length !== expectedIds.size
  || new Set(placements.placed.map((row: { id: string }) => row.id)).size !== expectedIds.size
  || placements.placed.some((row: { id: string }) => !expectedIds.has(row.id))) throw new Error('Capital placement identities are incomplete.');
const expectedObjects = expectedIds.size;
for (const [profile, expected] of Object.entries(placements.modelImports)) {
  if (!CAPITAL_HOUSE_PROFILES.includes(profile)
    || sha256(readFileSync(path.join(repoRoot, 'artifacts/unreal/converted', profile, 'editor-import.json'))) !== expected)
    throw new Error('Capital model import evidence changed.');
}
const run = `${Date.now()}-${process.pid}`;
const draftId = randomUUID().replaceAll('-', '');
const output = path.join(repoRoot, 'artifacts/unreal/capital-proof', run);
const native = path.join(packagedRoot ? path.join(packagedRoot, 'AegisWar/Saved') : path.join(repoRoot, 'unreal/AegisWar/Saved'), 'CapitalProof', run);
mkdirSync(output, { recursive: true });
const options = [...(packagedClient ? [] : [projectPath]), '/Game/Capitals/aegis_capital/AegisCapital_Workbench', '-game',
  '-unattended', '-nop4', '-nosplash', '-nosound', '-stdout', '-FullStdOutLogOutput',
  '-WarDevelopmentGM', '-WarCapitalProof', `-WarProofRun=${run}`, `-WarProofDraftId=${draftId}`, '-ExecCmds=t.MaxFPS 60',
  `-WarCapitalExpectedObjects=${expectedObjects}`,
  `-abslog=${path.join(output, 'game.log')}`,
  ...(args.has('--rendered') ? ['-RenderOffscreen', '-WarProofScreenshot', '-windowed', '-ForceRes', '-ResX=1280', '-ResY=800'] : ['-nullrhi'])];
const code = runEngineCommand(packagedClient ?? engine.editorCommand!, options);
const reportPath = path.join(native, 'report.json');
if (code !== 0 || !existsSync(reportPath)) throw new Error(`Capital proof failed; see ${output}.`);
const report = JSON.parse(readFileSync(reportPath, 'utf8').replace(/^\uFEFF/, ''));
if (report.schemaVersion !== 1 || report.passed !== true || report.editableObjects !== expectedObjects || report.retainedBaselineAdditions !== 1
  || report.developmentTraversalVerified !== true
  || report.fullCapitalAcceptance !== false || report.sharedGmAuthorization !== false) throw new Error('Capital runtime acceptance failed.');
copyFileSync(reportPath, path.join(output, 'native-report.json'));
if (args.has('--rendered')) {
  const image = path.join(native, 'builder.png');
  if (!existsSync(image)) throw new Error('Capital builder screenshot was not produced.');
  copyFileSync(image, path.join(output, 'builder.png'));
}
const reloadRun = `${run}-reload`;
const reloadOptions = options.map(value => value === `-WarProofRun=${run}` ? `-WarProofRun=${reloadRun}`
  : value.startsWith('-abslog=') ? `-abslog=${path.join(output, 'reload.log')}` : value);
reloadOptions.push('-WarCapitalReloadProof');
const reloadCode = runEngineCommand(packagedClient ?? engine.editorCommand!, reloadOptions);
const reloadReportPath = path.join(path.dirname(native), reloadRun, 'report.json');
if (reloadCode !== 0 || !existsSync(reloadReportPath)) throw new Error(`Fresh-process construction reload failed; see ${output}.`);
const reloadReport = JSON.parse(readFileSync(reloadReportPath, 'utf8').replace(/^\uFEFF/, ''));
if (reloadReport.passed !== true || reloadReport.constructionReload !== true || reloadReport.editableObjects !== expectedObjects + 1 || reloadReport.retainedBaselineAdditions !== 1
  || reloadReport.fullCapitalAcceptance !== false || reloadReport.sharedGmAuthorization !== false)
  throw new Error('Fresh-process construction runtime acceptance failed.');
copyFileSync(reloadReportPath, path.join(output, 'reload-report.json'));
writeFileSync(path.join(output, 'report.json'), JSON.stringify({ ...report,
  freshProcessConstructionReload: true,
  buildingImportSha256: sha256(readFileSync(path.join(directory, 'buildings-import.json'))),
  rendered: args.has('--rendered'), packagedClient: Boolean(packagedClient), platform: 'Win64', fullCapitalAcceptance: false }, null, 2));
console.log(JSON.stringify({ capitalWorkbenchProofPassed: true, report: output, fullCapitalAcceptance: false }));

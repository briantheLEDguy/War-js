import { copyFileSync, existsSync, mkdirSync, readFileSync, rmSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';
import { officialCapitalMap } from './capital-map';

const args = parseArguments(process.argv.slice(2), ['--rendered'], []);
const engine = inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand) throw new Error('Unreal editor is unavailable.');
const saved = path.join(repoRoot, 'unreal/AegisWar/Saved/CityPopulationProof');
const report = path.join(saved, 'report.json');
const image = path.join(saved, 'merchant.png');
rmSync(report, { force: true }); rmSync(image, { force: true });
const output = path.join(repoRoot, 'artifacts/unreal/population', `proof-${Date.now()}`);
mkdirSync(output, { recursive: true });
const code = runEngineCommand(engine.editorCommand, [projectPath, officialCapitalMap(), '-game', '-unattended', '-nop4', '-nosound', '-nosplash',
  '-WarDevelopmentGM', '-WarCityPopulationProof', ...(args.has('--rendered')
    ? ['-RenderOffscreen', '-WarProofScreenshot', '-windowed', '-ForceRes', '-ResX=1280', '-ResY=960'] : ['-nullrhi']),
  `-abslog=${path.join(output, 'game.log')}`]);
if (code !== 0 || !existsSync(report)) throw new Error(`Population gameplay proof failed: ${output}`);
const result = JSON.parse(readFileSync(report, 'utf8').replace(/^\uFEFF/, ''));
copyFileSync(report, path.join(output, 'report.json'));
if (!result.passed || result.map !== officialCapitalMap()) throw new Error(result.detail ?? 'Population proof rejected.');
if (args.has('--rendered')) {
  if (!existsSync(image)) throw new Error('Merchant UI screenshot was not produced.');
  copyFileSync(image, path.join(output, 'merchant.png'));
}
console.log(JSON.stringify({ populationProofPassed: true, output }));

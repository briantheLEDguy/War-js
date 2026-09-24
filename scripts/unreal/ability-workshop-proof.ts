import { randomUUID } from 'node:crypto';
import { mkdirSync, existsSync, readFileSync, copyFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';

const args=parseArguments(process.argv.slice(2),[],['--width','--height']);
const width=Number(args.get('--width')??1920),height=Number(args.get('--height')??1080);
if (![[1280,800],[1920,1080]].some(([w,h])=>w===width&&h===height)) throw new Error('Use 1280×800 or 1920×1080.');
const engine=inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run=randomUUID(),output=path.join(repoRoot,'artifacts/unreal/ability-workshop',`${width}x${height}-${run}`);
const receipt=path.join(repoRoot,'unreal/AegisWar/Saved/AbilityWorkshopProof',run.replaceAll('-',''));
mkdirSync(output,{recursive:true});
const code=runEngineCommand(engine.editorCommand,[projectPath,'/Game/Capitals/aegis_capital/AegisCapital_Workbench','-game','-unattended','-nop4','-nosound','-nosplash',
  '-RenderOffscreen','-windowed','-ForceRes',`-ResX=${width}`,`-ResY=${height}`,'-WarDevelopmentGM','-WarInterfaceProof','-WarWorkshopProof',`-WarWorkshopRun=${run}`,
  `-GameUserSettingsINI=${path.join(output,'preferences.ini')}`,`-ExecCmds=r.SetRes ${width}x${height}w,t.MaxFPS 30`,`-abslog=${path.join(output,'game.log')}`]);
if (code!==0 || !existsSync(path.join(receipt,'report.json'))) throw new Error(`Workshop proof failed: ${output}; ${receipt}`);
const result=JSON.parse(readFileSync(path.join(receipt,'report.json'),'utf8').replace(/^\uFEFF/,''));
if (!result.passed || !existsSync(path.join(receipt,'workshop.png'))) throw new Error(`Incomplete workshop evidence: ${receipt}`);
copyFileSync(path.join(receipt,'report.json'),path.join(output,'report.json'));
copyFileSync(path.join(receipt,'workshop.png'),path.join(output,'workshop.png'));
for (const name of ['analysis.png','review.png']) {
  if (!existsSync(path.join(receipt,name))) throw new Error(`Missing workshop page evidence: ${name}`);
  copyFileSync(path.join(receipt,name),path.join(output,name));
}
console.log(JSON.stringify({workshopUiProof:true,output,sharedAdmission:false,nativeArena:false}));

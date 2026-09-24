import { spawn, type ChildProcess } from 'node:child_process';
import { createSocket } from 'node:dgram';
import { randomUUID } from 'node:crypto';
import { createWriteStream, existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, projectPath, repoRoot } from './toolchain';

const engine=inspectToolchain(defaultEngineRoot());
if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
const run=randomUUID(),output=path.join(repoRoot,'artifacts/unreal/ability-workshop-combat',run);
const receipts=path.join(repoRoot,'unreal/AegisWar/Saved/AbilityWorkshopCombatProof',run.replaceAll('-',''));
mkdirSync(output,{recursive:true});
const socket=createSocket('udp4');
await new Promise<void>((resolve,reject)=>{socket.once('error',reject);socket.bind(0,'127.0.0.1',resolve);});
const port=socket.address().port; await new Promise<void>(resolve=>socket.close(resolve));
const children: ChildProcess[]=[];
const logs: ReturnType<typeof createWriteStream>[]=[];
function readReport(file:string) {
  const bytes=readFileSync(file);
  return JSON.parse(bytes.toString(bytes[0]===0xff && bytes[1]===0xfe ? 'utf16le' : 'utf8').replace(/^\uFEFF/,''));
}
function start(server:boolean) {
  const role=server?'server':'client',log=createWriteStream(path.join(output,`${role}.log`)); logs.push(log);
  const options=server?['/Game/MigrationProof/EngineProof','-server',`-port=${port}`,'-MULTIHOME=127.0.0.1']:[`127.0.0.1:${port}`,'-game'];
  const child=spawn(engine.editorCommand!,[projectPath,...options,'-unattended','-nop4','-nosound','-nosplash','-nullrhi','-stdout','-FullStdOutLogOutput',
    '-WarDevelopmentNetworking','-WarWorkshopCombatProof',`-WarWorkshopRun=${run}`,'-ExecCmds=t.MaxFPS 30'],{cwd:repoRoot,windowsHide:true,stdio:['ignore','pipe','pipe']});
  child.stdout!.pipe(log); child.stderr!.pipe(log); children.push(child);
}
const delay=()=>new Promise(resolve=>setTimeout(resolve,500));
try {
  start(true); const deadline=Date.now()+240000;
  while (!existsSync(path.join(output,'server.log')) || !readFileSync(path.join(output,'server.log'),'utf8').includes(`IpNetDriver listening on port ${port}`)) {
    if (Date.now()>deadline || children[0].exitCode!==null) throw new Error(`Server did not listen: ${output}`); await delay();
  }
  start(false);
  while (!['server','client'].every(role=>existsSync(path.join(receipts,`${role}.json`)))) {
    for (const role of ['server','client']) { const file=path.join(receipts,`${role}.json`); if (existsSync(file) && !readReport(file).passed) throw new Error(`Failed native proof: ${JSON.stringify(readReport(file))}; ${output}`); }
    if (Date.now()>deadline || children.some(child=>child.exitCode!==null)) throw new Error(`Incomplete native proof: ${output}`); await delay();
  }
  const reports=['server','client'].map(role=>readReport(path.join(receipts,`${role}.json`)));
  if (reports.some(report=>report.passed!==true || report.onlineExecutor!==true || report.sharedAdmission!==false)) throw new Error('Invalid native evidence.');
  copyFileSync(path.join(receipts,'traces.json'),path.join(output,'traces.json'));
  writeFileSync(path.join(output,'report.json'),JSON.stringify({run,transport:'loopback UDP',passed:true,sharedAdmission:false,steamAcceptance:false,reports},null,2)+'\n');
  console.log(JSON.stringify({workshopCombatProof:true,output,sharedAdmission:false}));
} finally {
  for (const child of children) if (child.exitCode===null) child.kill();
  await Promise.all(children.map(child=>child.exitCode!==null?Promise.resolve():new Promise<void>(resolve=>{child.once('exit',()=>resolve());setTimeout(resolve,5000);}))); for (const log of logs) log.end();
}

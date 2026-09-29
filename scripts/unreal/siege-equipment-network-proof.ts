import { spawn, type ChildProcess } from 'node:child_process';
import { createSocket } from 'node:dgram';
import { existsSync, readFileSync, mkdirSync, rmSync, copyFileSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, projectPath, repoRoot } from './toolchain';
import { validateSiegeEquipment } from './siege-equipment-proof';

async function run() {
  const engine = inspectToolchain(defaultEngineRoot());
  if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
  const socket = createSocket('udp4');
  await new Promise<void>((resolve, reject) => { socket.once('error', reject); socket.bind(0, '127.0.0.1', resolve); });
  const port = socket.address().port;
  await new Promise<void>(resolve => socket.close(() => resolve()));
  const output = path.join(repoRoot, 'artifacts/unreal/siege/equipment/network', `${Date.now()}-${process.pid}`);
  mkdirSync(output, { recursive: true });
  const saved = path.join(repoRoot, 'unreal/AegisWar/Saved');
  const names = ['SiegeEquipment.json', 'SiegeEquipmentClient.json'];
  names.forEach(name => rmSync(path.join(saved, name), { force: true }));
  const captures = ['convoy-start', 'checkpoint-owned', 'convoy-ramp', 'gate-owned'];
  captures.forEach(name => rmSync(path.join(saved, 'SiegeEquipmentProof', `${name}.png`), { force: true }));
  const children: ChildProcess[] = [];
  let failure: Error | undefined;
  const start = (role: string, args: string[]) => {
    const child = spawn(engine.editorCommand!, [projectPath, ...args, '-WarDevelopmentNetworking', '-WarSiegeEquipmentProof',
      '-unattended', '-nop4', '-nosplash', '-nosound', `-abslog=${path.join(output, `${role}.log`)}`],
    { cwd: repoRoot, windowsHide: true, stdio: 'ignore' });
    child.once('error', error => { failure = error; }); children.push(child);
  };
  const delay = () => new Promise(resolve => setTimeout(resolve, 500));
  const ended = (child: ChildProcess) => child.exitCode !== null || child.signalCode !== null;
  const stop = () => children.forEach(child => { if (!ended(child)) child.kill(); });
  process.once('SIGINT', stop); process.once('SIGTERM', stop);
  try {
    start('server', ['/Game/Capitals/Siege/AegisCapital_Siege?game=/Script/Engine.GameModeBase', '-server', '-nullrhi',
      '-MULTIHOME=127.0.0.1', `-port=${port}`]);
    const deadline = Date.now() + 460_000;
    while (true) {
      const log = path.join(output, 'server.log');
      if (failure) throw failure;
      if (ended(children[0]) || Date.now() > deadline) throw new Error(`Server failed: ${output}`);
      if (existsSync(log) && readFileSync(log, 'utf8').includes('IpNetDriver listening on port')) break;
      await delay();
    }
    start('client', [`127.0.0.1:${port}`, '-game', '-RenderOffscreen', '-windowed', '-ForceRes', '-ResX=1280', '-ResY=720',
      '-ExecCmds=t.MaxFPS 30']);
    while (!children.every(ended)) {
      if (failure) throw failure;
      if (Date.now() > deadline) throw new Error(`Network proof timed out: ${output}`);
      if (existsSync(path.join(saved, names[0]))) {
        const server = JSON.parse(readFileSync(path.join(saved, names[0]), 'utf8').replace(/^\uFEFF/, ''));
        if (!server.passed) throw new Error(server.detail);
      }
      await delay();
    }
    for (const name of names) copyFileSync(path.join(saved, name), path.join(output, name));
    const read = (name: string) => JSON.parse(readFileSync(path.join(output, name), 'utf8').replace(/^\uFEFF/, ''));
    validateSiegeEquipment(read(names[0]));
    const client = read(names[1]);
    if (!client.passed || client.client !== true || client.ownershipStandards !== 4 || client.engineersReady !== 4 || client.captures !== 4
      || children.some(child => child.exitCode !== 0)) throw new Error(`Client proof incomplete: ${JSON.stringify(client)}`);
    for (const name of captures) copyFileSync(path.join(saved, 'SiegeEquipmentProof', `${name}.png`), path.join(output, `${name}.png`));
    console.log(JSON.stringify({ passed: true, output }));
  } finally { stop(); process.removeListener('SIGINT', stop); process.removeListener('SIGTERM', stop); }
}
run().catch(error => { console.error(error); process.exitCode = 1; });

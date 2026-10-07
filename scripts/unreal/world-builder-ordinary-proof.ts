import { spawn } from 'node:child_process';
import { runGmOrdinaryPersistence, type OrdinaryProofLauncher } from './gm-ordinary-persistence';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, repoRoot } from './toolchain';

export const launchOrdinaryProof: OrdinaryProofLauncher = request => new Promise((resolve, reject) => {
  const child = spawn(request.executable, request.args,
    { cwd: request.repository, stdio: 'inherit', windowsHide: true });
  let timedOut = false;
  let exitTimeout: ReturnType<typeof setTimeout> | undefined;
  // Only this spawned process is owned. Its final exit precedes preservation checks.
  const timeout = setTimeout(() => {
    timedOut = true;
    if (!child.kill('SIGKILL')) reject(new Error('Could not stop timed-out owned ordinary proof PID ' + child.pid));
    else exitTimeout = setTimeout(() => reject(new Error('Owned ordinary proof PID did not exit after termination: ' + child.pid)), 30000);
  }, 300000);
  child.once('error', error => { clearTimeout(timeout); clearTimeout(exitTimeout); reject(error); });
  child.once('exit', (code, signal) => {
    clearTimeout(timeout); clearTimeout(exitTimeout);
    if (timedOut) reject(new Error('Owned ordinary proof process timed out after five minutes; PID ' + child.pid));
    else resolve({ pid: child.pid ?? 0, exitCode: code ?? 1, signal });
  });
});

if (isMain(import.meta.url)) {
  try {
    const args = parseArguments(process.argv.slice(2), [], ['--receipt', '--binding', '--engine-root']);
    if (!args.get('--receipt') || !args.get('--binding'))
      throw new Error('Pass --receipt <fresh staged wrapper receipt> and --binding <explicit DLL/source binding JSON>.');
    const engineRoot = args.get('--engine-root') ?? defaultEngineRoot(), engine = inspectToolchain(engineRoot);
    if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
    const executable = engine.editorCommand.replace(/-Cmd\.exe$/i, '.exe');
    runGmOrdinaryPersistence({ repository: repoRoot, receiptPath: args.get('--receipt')!, bindingPath: args.get('--binding')!,
      executable, engineRoot }, launchOrdinaryProof).then(result => console.log(JSON.stringify(result, null, 2)))
      .catch(error => { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; });
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}

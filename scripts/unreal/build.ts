import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, runEngineCommand } from './toolchain';

export function buildArguments(target: string, platform: string, configuration: string): string[] {
  if (!['Editor', 'Client', 'Server', 'Game'].includes(target)) throw new Error(`Invalid target: ${target}`);
  if (!['Win64', 'Linux', 'Mac'].includes(platform)) throw new Error(`Invalid platform: ${platform}`);
  if (!['Development', 'DebugGame'].includes(configuration)) throw new Error('This bootstrap build command supports Development/DebugGame only; Shipping requires release acceptance.');
  const targetName = `AegisWar${target === 'Game' ? '' : target}`;
  return [targetName, platform, configuration, `-Project=${projectPath}`, '-WaitMutex', '-NoHotReloadFromIDE'];
}

if (isMain(import.meta.url)) {
  try {
    const args = parseArguments(process.argv.slice(2), ['--dry-run'], ['--engine-root', '--target', '--platform', '--configuration']);
    const hostPlatform = process.platform === 'win32' ? 'Win64' : process.platform === 'darwin' ? 'Mac' : 'Linux';
    const invocation = buildArguments(args.get('--target') ?? 'Editor', args.get('--platform') ?? hostPlatform, args.get('--configuration') ?? 'Development');
    const report = inspectToolchain(args.get('--engine-root') ?? defaultEngineRoot());
    if (args.has('--dry-run')) console.log(JSON.stringify({ command: report.buildCommand, arguments: invocation, blockers: report.blockers, executed: false }, null, 2));
    else {
      if (report.blockers.length || !report.buildCommand) throw new Error(report.blockers.join('\n'));
      process.exitCode = runEngineCommand(report.buildCommand, invocation);
    }
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}

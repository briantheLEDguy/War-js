import { existsSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';
import { refreshFrontend } from './frontend-content';

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
      // A fresh checkout has no private world yet; installed worlds must refresh
      // their scenery snapshot after the Editor module is available.
      if (process.exitCode === 0 && (args.get('--target') ?? 'Editor') === 'Editor'
          && existsSync(path.join(repoRoot, 'artifacts/unreal/world-portals/build.json'))) refreshFrontend(report);
    }
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}

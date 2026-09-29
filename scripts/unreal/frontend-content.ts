import { spawnSync } from 'node:child_process';
import { mkdirSync, existsSync } from 'node:fs';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot, runEngineCommand, type ToolchainReport } from './toolchain';

export function refreshFrontend(engine: ToolchainReport, checkOnly = false): void {
  if (engine.blockers.length || !engine.editorCommand || !engine.engineRoot) throw new Error(engine.blockers.join('\n'));
  const bundledPython = path.join(engine.engineRoot, 'Engine/Binaries/ThirdParty/Python3',
    process.platform === 'win32' ? 'Win64/python.exe' : process.platform === 'darwin' ? 'Mac/bin/python3' : 'Linux/bin/python3');
  const check = () => {
    const result = spawnSync(existsSync(bundledPython) ? bundledPython : 'python3',
      [path.join(repoRoot, 'scripts/unreal/frontend_sources.py')], { cwd: repoRoot, encoding: 'utf8', windowsHide: true });
    if (result.error) throw result.error;
    if (result.status !== 0 && result.status !== 1) throw new Error(result.stdout + result.stderr);
    return result;
  };
  const before = check();
  if (before.status === 0) { console.log(before.stdout.trim()); return; }
  if (checkOnly) throw new Error(`${before.stdout.trim()} Run npm run unreal:frontend-refresh with the project Editor closed.`);
  // A loaded editor can retain and later save an older copy over the new asset.
  if (process.platform === 'win32') {
    const running = spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command',
      'Get-Process UnrealEditor -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id; exit 0'], { encoding: 'utf8', windowsHide: true });
    if (running.error || running.status !== 0) throw new Error('Cannot check for an open Unreal Editor. Close it and retry.');
    if (running.stdout.trim()) throw new Error('Save and close Unreal Editor and standalone game windows before refreshing lobby content.');
  }
  console.log(`Refreshing lobby: ${before.stdout.trim()}`);
  const output = path.join(repoRoot, 'artifacts/unreal/frontend');
  mkdirSync(output, { recursive: true });
  const code = runEngineCommand(engine.editorCommand, [projectPath, '-run=pythonscript',
    `-script=${path.join(repoRoot, 'scripts/unreal/build-frontend-presentation.py')}`, '-unattended', '-nop4', '-nullrhi', '-nosplash',
    `-abslog=${path.join(output, 'refresh.log')}`]);
  if (code !== 0) throw new Error(`Frontend refresh failed (${code}); see ${output}/refresh.log`);
  const after = check();
  if (after.status !== 0) throw new Error(`Frontend refresh did not produce current content: ${after.stdout}`);
  console.log(after.stdout.trim());
}

if (isMain(import.meta.url)) {
  try {
    const args = parseArguments(process.argv.slice(2), ['--check'], ['--engine-root']);
    refreshFrontend(inspectToolchain(args.get('--engine-root') ?? defaultEngineRoot()), args.has('--check'));
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}

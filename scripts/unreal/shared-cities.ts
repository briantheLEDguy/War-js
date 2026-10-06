import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { verifySharedCities } from '../../server/scenarios/city-content';
import { refreshFrontend } from './frontend-content';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot, runEngineCommand } from './toolchain';

if (isMain(import.meta.url)) {
  try {
    const args = parseArguments(process.argv.slice(2), ['--check'], ['--engine-root']);
    if (args.has('--check')) {
      verifySharedCities(repoRoot);
      console.log('Active shared city routing and package hashes are current. Run native verification to inspect consumer bindings.');
    } else {
      const engine = inspectToolchain(args.get('--engine-root') ?? defaultEngineRoot());
      if (engine.blockers.length || !engine.editorCommand) throw new Error(engine.blockers.join('\n'));
      if (process.platform === 'win32') {
        const open = spawnSync('powershell.exe', ['-NoProfile', '-NonInteractive', '-Command',
          'Get-Process UnrealEditor -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id; exit 0'], { encoding: 'utf8', windowsHide: true });
        if (open.error || open.status !== 0 || open.stdout.trim()) throw new Error('Save and close Unreal Editor and game windows before synchronizing city content.');
      }
      let current = false;
      try { verifySharedCities(repoRoot); current = true; } catch { /* A changed source needs a new revision and review. */ }
      if (!current) {
        const status = runEngineCommand(engine.editorCommand, [projectPath, '-run=pythonscript',
          `-script=${path.join(repoRoot, 'scripts/unreal/sync-shared-cities.py')}`, '-unattended', '-nop4', '-nullrhi', '-nosplash',
          `-abslog=${path.join(repoRoot, 'artifacts/unreal/shared-city-sync.log')}`]);
        if (status !== 0) throw new Error('City synchronization stopped. Inspect artifacts/unreal/shared-cities/pending.json and its backups before retrying.');
      }
      verifySharedCities(repoRoot);
      refreshFrontend(engine);
      const inspected = runEngineCommand(engine.editorCommand, [projectPath, '-run=pythonscript',
        `-script=${path.join(repoRoot, 'scripts/unreal/verify-shared-cities.py')}`, '-unattended', '-nop4', '-nullrhi', '-nosplash',
        `-abslog=${path.join(repoRoot, 'artifacts/unreal/shared-cities/verify.log')}`]);
      if (inspected !== 0) throw new Error('Shared city consumer verification failed. Inspect the native log before using these bindings.');
    }
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}

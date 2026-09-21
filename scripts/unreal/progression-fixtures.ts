import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { repoRoot } from './toolchain';

// Execute the browser implementation in its existing Vitest environment, without changing browser code.
const result = spawnSync(process.execPath, [path.join(repoRoot, 'node_modules/vitest/vitest.mjs'), 'run',
  'tests/unrealProgressionFixtures.test.ts'], { cwd: repoRoot, stdio: 'inherit',
  env: { ...process.env, WAR_UPDATE_PROGRESSION_FIXTURES: '1' } });
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;

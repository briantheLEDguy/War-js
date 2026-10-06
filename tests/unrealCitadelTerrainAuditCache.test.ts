import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, readFileSync, realpathSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { expect, test, vi } from 'vitest';
import { requireNativeCitadelTerrain } from '../scripts/unreal/citadel-terrain-evidence';

vi.mock('node:child_process', () => ({ spawnSync: vi.fn() }));
const digest = (file: string) => createHash('sha256').update(readFileSync(file)).digest('hex');

test('reuses a reconstruction only for identical input bytes and never stores a failed audit', () => {
  const repository = mkdtempSync(path.join(os.tmpdir(), 'citadel-terrain-cache-'));
  try {
    const run = path.join(repository, 'artifacts/unreal/aegis-citadel/0123456789ab');
    mkdirSync(run, { recursive: true });
    const data = ['blueprint.json', 'candidate.json', 'corners.json'].map(name => path.join(run, name));
    data.forEach(file => writeFileSync(file, '{}'));
    const helperNames = ['citadel_terrain_evidence.py', 'aegis_citadel_terrain.py',
      'aegis_citadel_terrain_readback.py', 'aegis_citadel_terrain_render_readback.py'];
    const files = [...data, ...helperNames.map(name => path.resolve('scripts/unreal', name))].map(file => realpathSync(file));
    const receipt = { schemaVersion: 1, passed: true, physicalApproval: false, visualApproval: false,
      inputHashes: Object.fromEntries(files.map(file => [file, digest(file)])) };
    const runner = vi.mocked(spawnSync);
    runner.mockReset(); runner.mockReturnValue({ status: 0, stdout: JSON.stringify(receipt), stderr: '' } as any);
    requireNativeCitadelTerrain(repository, run);
    requireNativeCitadelTerrain(repository, run);
    expect(runner).toHaveBeenCalledTimes(1);
    // Equal-sized replacement still invalidates the successful reconstruction.
    writeFileSync(data[2], '[]');
    expect(() => requireNativeCitadelTerrain(repository, run)).toThrow('input custody');
    expect(runner).toHaveBeenCalledTimes(2);
    expect(() => requireNativeCitadelTerrain(repository, run)).toThrow('input custody');
    expect(runner).toHaveBeenCalledTimes(3);
    writeFileSync(data[2], '{}');
    requireNativeCitadelTerrain(repository, run);
    requireNativeCitadelTerrain(repository, run);
    expect(runner).toHaveBeenCalledTimes(4);
    rmSync(data[2]);
    expect(() => requireNativeCitadelTerrain(repository, run)).toThrow();
    expect(runner).toHaveBeenCalledTimes(4);
  } finally { rmSync(repository, { recursive: true, force: true }); }
});

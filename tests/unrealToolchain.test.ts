import { afterEach, describe, expect, it } from 'vitest';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { buildArguments } from '../scripts/unreal/build';
import { inspectToolchain, parseArguments } from '../scripts/unreal/toolchain';

const roots: string[] = [];
function fixture(version = '5.8.2') {
  const root = mkdtempSync(path.join(tmpdir(), 'war-unreal-toolchain-')); roots.push(root);
  const [MajorVersion, MinorVersion, PatchVersion] = version.split('.').map(Number);
  for (const relative of ['Engine/Build/Build.version', 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe', 'Engine/Build/BatchFiles/Build.bat', 'Engine/Build/BatchFiles/RunUAT.bat']) {
    const target = path.join(root, relative); mkdirSync(path.dirname(target), { recursive: true });
    writeFileSync(target, relative.endsWith('Build.version') ? JSON.stringify({ MajorVersion, MinorVersion, PatchVersion }) : 'fixture');
  }
  return root;
}
afterEach(() => { for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true }); });

describe('Unreal build prerequisite gates', () => {
  it('does not mistake a launcher directory for an installed engine', () => {
    const root = mkdtempSync(path.join(tmpdir(), 'war-unreal-toolchain-')); roots.push(root);
    mkdirSync(path.join(root, '.egstore'));
    expect(inspectToolchain(root, 'win32').blockers).toHaveLength(4);
  });
  it('requires the exact engine pin and every executable/script', () => {
    expect(inspectToolchain(fixture(), 'win32').blockers).toEqual([]);
    expect(inspectToolchain(fixture('5.8.1'), 'win32').blockers).toEqual(['Expected Unreal 5.8.2; found 5.8.1.']);
  });
  it('keeps native success distinct from file discovery', () => {
    expect(inspectToolchain(fixture(), 'win32').limitations.join(' ')).toContain('does not prove');
  });
  it('does not allow the development wrapper to bypass Shipping acceptance', () => {
    expect(() => buildArguments('Client', 'Win64', 'Shipping')).toThrow('release acceptance');
    expect(() => buildArguments('Client;evil', 'Win64', 'Development')).toThrow('Invalid target');
    expect(buildArguments('Server', 'Linux', 'Development').slice(0, 3)).toEqual(['AegisWarServer', 'Linux', 'Development']);
  });
  it('rejects unknown, duplicate and missing command options', () => {
    expect(() => parseArguments(['--engine-root'], [], ['--engine-root'])).toThrow();
    expect(() => parseArguments(['--skip-validation'], [], [])).toThrow();
    expect(() => parseArguments(['--dry-run', '--dry-run'], ['--dry-run'], [])).toThrow('Duplicate');
  });
});

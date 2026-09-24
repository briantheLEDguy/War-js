import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { buildContentManifest } from '../scripts/unreal/export-content';
import { readBrowserReference } from '../scripts/unreal/browser-reference';
import { repoRoot } from '../scripts/unreal/toolchain';

describe('browser retirement boundary', () => {
  it('preserves the complete pre-retirement gameplay content', async () => {
    const original = JSON.parse(readFileSync(path.join(repoRoot, 'migration/browser-reference.json'), 'utf8'));
    const revisions = JSON.parse(readFileSync(path.join(repoRoot, 'migration/content-revisions.json'), 'utf8'));
    expect(revisions.historicalContentSha256).toBe(original.contentSha256);
    expect((await buildContentManifest()).source.contentSha256).toBe(revisions.currentContentSha256);
  });
  it('has no browser application or deployment entrypoints', () => {
    for (const file of ['src', 'index.html', 'vite.config.ts', '.github/workflows/deploy-pages.yml'])
      expect(existsSync(path.join(repoRoot, file)), file).toBe(false);
    const packageJson = JSON.parse(readFileSync(path.join(repoRoot, 'package.json'), 'utf8'));
    for (const dependency of ['react', 'react-dom', 'zustand', 'three-mesh-bvh'])
      expect(packageJson.dependencies[dependency]).toBeUndefined();
  });
  it('requires registered immutable historical evidence', () => {
    expect(readBrowserReference('src/game/QuestLogic.ts')).toContain('export function checkLevelUp');
    expect(() => readBrowserReference('../.env')).toThrow('Unregistered');
    expect(() => readBrowserReference('src/does-not-exist.ts')).toThrow('Unregistered');
  });
});

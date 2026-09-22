import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { repoRoot } from '../scripts/unreal/toolchain';
import { verifyBrowserFixture } from '../scripts/unreal/verify-browser-fixtures';

describe('archived expedition reference consumed by native automation', () => {
  it('preserves both complete chains and their rejection/retry scenarios', () => {
    verifyBrowserFixture('quests');
    const fixture = JSON.parse(readFileSync(path.join(repoRoot, 'migration/fixtures/quests.json'), 'utf8'));
    expect(fixture.cases.map((entry: { realm: string }) => entry.realm)).toEqual(['aegis', 'riftbound']);
    for (const entry of fixture.cases) {
      const actions: string[] = entry.steps.map((step: { action: string }) => step.action);
      for (const suffix of ['duplicate_accept', 'reject_wrong_kill_zone', 'reject_full_bag', 'duplicate_turnin'])
        expect(actions.some(action => action.endsWith(suffix))).toBe(true);
      const last = entry.steps.at(-1);
      expect(last.quests).toHaveLength(4);
      expect(last.quests.every((quest: { status: string }) => quest.status === 'completed')).toBe(true);
      expect(last.character.gold).toBe(108);
    }
  });
});

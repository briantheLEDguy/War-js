import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const source = readFileSync(path.resolve('src/ui/screens/ModelReviewScreen.tsx'), 'utf8');
const styles = readFileSync(path.resolve('src/ui/styles.css'), 'utf8');
const viteSource = readFileSync(path.resolve('vite.config.ts'), 'utf8');
const serverSource = readFileSync(
  path.resolve('scripts/blender-character-pipeline/tools/local-roster-review-plugin.mjs'),
  'utf8',
);

describe('full roster model-stage review screen', () => {
  it('provides all queues, navigation, evidence modes, and decisions', () => {
    for (const label of [
      'Classes', 'NPCs', 'Creatures', 'Previous Item', 'Next Item',
      'Previous Version', 'Next Version', 'Male', 'Female', 'Bare', 'Equipped',
      'One-handed', 'Two-handed', 'Dual wield', 'Turntable', 'Stress pose',
      'Approve', 'Disapprove', 'Regenerate',
    ]) expect(source).toContain(label);
    expect(source).not.toContain('window.prompt');
    expect(source).toContain("localStorage.getItem('war-js-model-reviewer')");
    expect(source).toContain('Disapproval requires notes.');
    expect(source).toContain('Runtime promotion remains blocked by LOD and animation stages.');
    expect(viteSource).toContain('localRosterReviewPlugin()');
  });

  it('keeps the model and controls in separate mobile regions with touch-sized inputs', () => {
    expect(styles).toContain('right: min(390px, 44vw);');
    expect(styles).toContain('@media (max-width: 720px) and (orientation: portrait)');
    expect(styles).toContain('inset: 42dvh 0 0;');
    expect(styles).toContain('@media (pointer: coarse)');
    expect(styles).toContain('min-height: 44px;');
    expect(source).toContain('model-review-short-label');
    expect(source).toContain('model-review-mobile-status');
  });

  it('removes the hard-coded Battle Prelate review route and protects mutations', () => {
    expect(source).not.toContain('BATTLE_PRELATE_DEVELOPMENT');
    expect(viteSource).not.toContain('battle-prelate');
    expect(serverSource).toContain('x-war-review-token');
    expect(serverSource).toContain('parsed.host === host');
    expect(serverSource).toContain('assertPathWithin(REPO_ROOT');
    expect(serverSource).toContain('sha256File(target) !== artifact.sha256');
  });
});

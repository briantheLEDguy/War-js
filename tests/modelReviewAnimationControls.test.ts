import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const source = readFileSync(path.resolve('src/ui/screens/ModelReviewScreen.tsx'), 'utf8');
const viteSource = readFileSync(path.resolve('vite.config.ts'), 'utf8');

describe('model review animation controls', () => {
  it('exposes every canonical runtime clip without changing geometry approval state', () => {
    for (const clip of [
      'idle', 'walk', 'run', 'combat_idle', 'attack_melee',
      'attack_ranged', 'cast', 'death', 'jump',
    ]) {
      expect(source).toContain(`'${clip}'`);
    }
    expect(source).toContain('GEOMETRY v18 ACCEPTED · ANIMATION v19 REVIEW');
    expect(source).toContain('v18 animation was rejected. Play every revised runtime clip');
    expect(source).toContain('setLoop(THREE.LoopRepeat, Infinity)');
    expect(source).toContain('THREE.LoopOnce');
    expect(source).toContain("const ASSEMBLED_MODEL = '/__model-review/battle-prelate-m.glb'");
    expect(source).toContain('Exact formal assembly loaded');
    expect(source).not.toContain('weapon.scene.scale.setScalar(0.8)');
    expect(viteSource.indexOf('local-armor-pilot-v19')).toBeLessThan(
      viteSource.indexOf('local-armor-pilot-v18'),
    );
    expect(source).toContain("aria-label=\"Animation review controls\"");
  });
});

import { describe, expect, it } from 'vitest';
import { graphicsProofArguments } from '../scripts/unreal/graphics-proof';

describe('native graphics proof isolation', () => {
  it('always isolates preferences and requests a rendered game', () => {
    for (const mode of ['smoke', 'interrupt', 'restart', 'safe']) {
      const args = graphicsProofArguments(mode, 'test-profile');
      expect(args).toContain('-game');
      expect(args).not.toContain('-nullrhi');
      expect(args.some(arg => arg.startsWith('-GameUserSettingsINI=') && arg.endsWith('GraphicsProof-test-profile.ini'))).toBe(true);
    }
  });
  it('requires explicit interrupt/restart and recovery modes', () => {
    expect(graphicsProofArguments('smoke', 'a')).not.toContain('-WarGraphicsProofExit');
    expect(graphicsProofArguments('interrupt', 'a')).toContain('-WarGraphicsProofExit');
    expect(graphicsProofArguments('restart', 'a')).toContain('-WarGraphicsProofRestart');
    expect(graphicsProofArguments('safe', 'a')).toContain('-WarSafeGraphics');
  });
  it('rejects profile paths and unknown commands', () => {
    for (const profile of ['../player', 'C:\\user', 'a b', '']) expect(() => graphicsProofArguments('smoke', profile)).toThrow();
    expect(() => graphicsProofArguments('anything', 'a')).toThrow();
  });
});

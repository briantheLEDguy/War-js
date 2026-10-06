import { describe, expect, it } from 'vitest';
import { gmRenderingArguments } from '../scripts/unreal/gm-rendering-proof';

describe('GM rendering proof isolation', () => {
  const run = '1234567890abcdef1234567890abcdef';
  const map = '/Game/WorldRebuild/DutchBastion_test/Bastion_Campaign_v3';
  it('uses a distinct preference file and world draft for every run', () => {
    const args = gmRenderingArguments('pointer', run, map);
    expect(args).toContain(map);
    expect(args).toContain(`-WarProofDraftId=${run}`);
    expect(args.find(value => value.startsWith('-GameUserSettingsINI='))).toContain(run);
    expect(args.find(value => value.startsWith('-GameUserSettingsINI='))).toContain('GmRenderingProof.ini');
    expect(args).toContain('-WarGmRenderingProof');
  });
  it('keeps direct and idle controls separate from pointer interaction', () => {
    expect(gmRenderingArguments('direct', run, map)).toContain('-WarGmRenderingDirect');
    expect(gmRenderingArguments('idle', run, map)).toContain('-WarGmRenderingIdle');
    expect(gmRenderingArguments('pointer', run, map)).not.toContain('-WarGmRenderingDirect');
    expect(gmRenderingArguments('input', run, map)).toContain('-WarGmRenderingHitTest');
    expect(gmRenderingArguments('keyboard', run, map)).toContain('-WarGmRenderingKeyboard');
  });
  it('provides a visible manual capture session without automatic commands', () => {
    const args = gmRenderingArguments('manual', run, map);
    expect(args).toContain('-WarGmRenderingManual');
    expect(args).not.toContain('-RenderOffscreen');
    expect(args).not.toContain('-WarGmRenderingDirect');
  });
  it('rejects nonisolated identifiers and invalid launch inputs', () => {
    expect(() => gmRenderingArguments('pointer', '../owner', map)).toThrow();
    expect(() => gmRenderingArguments('unknown', run, map)).toThrow();
    expect(() => gmRenderingArguments('pointer', run, '/Game/map -ExecCmds=quit')).toThrow();
    expect(() => gmRenderingArguments('pointer', run, map, 'unknown')).toThrow();
  });
  it('launches embedded PIE through an isolated editor rather than silently testing standalone again', () => {
    const args = gmRenderingArguments('pointer', run, map, 'pie');
    expect(args).not.toContain('-game');
    expect(args.some(value => value.startsWith('-ExecCmds=') && value.includes('gm-rendering-pie.py'))).toBe(true);
    expect(args.some(value => value.startsWith('-ExecutePythonScript='))).toBe(false);
  });
});

import { spawnSync } from 'node:child_process';
import { expect, test } from 'vitest';
import { privateLumenStudyRequest } from '../scripts/unreal/citadel-lumen-study';

test('private Lumen diagnostics preserve scenery and reject missing renderer evidence', () => {
  const run = spawnSync('python', ['-B', 'tests/unrealCitadelLumenStudy.test.py'], { encoding: 'utf8', windowsHide: true });
  expect(run.error, run.error?.message).toBeUndefined();
  expect(run.status, run.stdout + run.stderr).toBe(0);
}, 30_000);

const expected = { map: '/Game/WorldRebuild/AegisCitadel_123456789abc/LightingStudy', mapSha256: 'a'.repeat(64),
  cityRevision: 'b'.repeat(64), blueprintSha256: 'c'.repeat(64) };
const study = () => ({ ...expected, diagnosticOnly: true, mode: 'lumen_hardware', sourceAndCandidateHashesUnchanged: true,
  rendererStateVerified: false, visualApproved: false, lightingApproved: false, physicalTraversalApproved: false,
  gameplayApproved: false, releaseAcceptance: false, privateLumen: { diagnosticOnly: true, mode: 'lumen_hardware',
    requestedBackend: 'hardware', overrideScope: 'private_process_after_graphics_init', rendererStateVerified: false,
    lightingApproved: false, runtimeCvars: { 'r.Lumen.DiffuseIndirect.Allow': 1, 'r.Lumen.Reflections.Allow': 1,
      'r.Lumen.FinalGatherMethod': 1, 'r.Lumen.HardwareRayTracing': 1,
      'r.Lumen.ScreenProbeGather.HardwareRayTracing': 1, 'r.Lumen.Reflections.HardwareRayTracing': 1 } } });

test('private Lumen startup uses explicit process-only settings', () => {
  expect(privateLumenStudyRequest(study(), expected)).toEqual({ mode: 'lumen_hardware', startupArguments: [
    '-ini:Engine:[/Script/Engine.RendererSettings]:r.RayTracing=1',
    '-ini:Engine:[/Script/Engine.RendererSettings]:r.SkinCache.CompileShaders=1',
  ] });
});

test('changed or falsely approved Lumen studies cannot request a capture', () => {
  for (const patch of [{ mapSha256: 'changed' }, { blueprintSha256: 'changed' }, { lightingApproved: true },
    { rendererStateVerified: true }, { sourceAndCandidateHashesUnchanged: false }])
    expect(() => privateLumenStudyRequest({ ...study(), ...patch }, expected)).toThrow();
  const edited = study(); edited.privateLumen.runtimeCvars['r.Lumen.HardwareRayTracing'] = 0;
  expect(() => privateLumenStudyRequest(edited, expected)).toThrow();
  expect(() => privateLumenStudyRequest(undefined, expected)).toThrow();
});

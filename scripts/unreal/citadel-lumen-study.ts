/** Isolated native lighting comparisons; these requests never certify a renderer. */
export function privateLumenStudyRequest(study: any, expected: {
  map: string; mapSha256: string; cityRevision: string; blueprintSha256: string;
}): { mode: 'lumen_software' | 'lumen_hardware'; startupArguments: string[] } {
  const mode = study?.mode;
  const hardware = mode === 'lumen_hardware';
  const cvars: Record<string, number> = {
    'r.Lumen.DiffuseIndirect.Allow': 1, 'r.Lumen.Reflections.Allow': 1,
    'r.Lumen.FinalGatherMethod': 1, 'r.Lumen.HardwareRayTracing': hardware ? 1 : 0,
    ...(hardware ? { 'r.Lumen.ScreenProbeGather.HardwareRayTracing': 1, 'r.Lumen.Reflections.HardwareRayTracing': 1 }
      : { 'r.Lumen.TraceMeshSDFs': 1, 'r.Lumen.TraceMeshSDFs.Allow': 1,
        'r.Lumen.ScreenProbeGather.TraceMeshSDFs': 1, 'r.Lumen.Reflections.TraceMeshSDFs': 1 }),
  };
  const requested = study?.privateLumen;
  if (!['lumen_software', 'lumen_hardware'].includes(mode) || study.diagnosticOnly !== true
    || Object.entries(expected).some(([key, value]) => study[key] !== value)
    || study.sourceAndCandidateHashesUnchanged !== true || study.rendererStateVerified !== false
    || ['visualApproved', 'lightingApproved', 'physicalTraversalApproved', 'gameplayApproved', 'releaseAcceptance']
      .some(key => study[key] !== false)
    || requested?.mode !== mode || requested.diagnosticOnly !== true
    || requested.requestedBackend !== (hardware ? 'hardware' : 'software')
    || requested.overrideScope !== 'private_process_after_graphics_init'
    || requested.rendererStateVerified !== false || requested.lightingApproved !== false
    || !requested.runtimeCvars || Object.keys(requested.runtimeCvars).length !== Object.keys(cvars).length
    || Object.entries(cvars).some(([key, value]) => requested.runtimeCvars[key] !== value))
    throw new Error('Private Lumen requests require the exact unapproved native study, map and source bindings.');
  const startup = hardware ? ['r.RayTracing=1', 'r.SkinCache.CompileShaders=1']
    : ['r.GenerateMeshDistanceFields=1', 'r.DistanceFields.SupportEvenIfHardwareRayTracingSupported=1'];
  return { mode, startupArguments: startup.map(value => `-ini:Engine:[/Script/Engine.RendererSettings]:${value}`) };
}

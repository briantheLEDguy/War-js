/** Render-resource diagnostics are independent of capture, visual and gameplay acceptance. */
export function citadelCloudRenderState(report: any, map: string, viewIds: string[]) {
  const frames = report?.viewPerformance;
  const failures: { view: string; reason: string }[] = [];
  for (const id of viewIds) {
    const matching = Array.isArray(frames) ? frames.filter((row: any) => row?.id === id) : [];
    const witness = matching.length === 1 ? matching[0].lightingWitness : undefined;
    if (witness?.schemaVersion !== 1 || witness.available !== true || witness.map !== map
      || witness.viewportAvailable !== true || witness.showCloud !== true) {
      failures.push({ view: id, reason: 'Missing exact-map native cloud witness.' });
      continue;
    }
    const clouds = witness.clouds;
    if (!Array.isArray(clouds) || clouds.length !== 1) {
      failures.push({ view: id, reason: 'Expected one native cloud component.' });
      continue;
    }
    const cloud = clouds[0], resource = cloud.renderMaterial;
    if (cloud.visible !== true || cloud.hiddenInGame !== false || cloud.actorHidden !== false
      || cloud.registered !== true || cloud.renderStateCreated !== true
      || cloud.renderInMainPass !== true || cloud.holdout !== false || cloud.volumeDomain !== true
      || resource?.usedFallback !== false || resource.volumeDomain !== true
      || resource.shaderMapPresent !== true || resource.shaderMapValidForRendering !== true) {
      failures.push({ view: id, reason: 'Cloud is hidden, unavailable or uses an invalid/fallback render material.' });
    }
  }
  return { schemaVersion: 1, diagnosticOnly: true, map, requestedViews: viewIds.length,
    available: viewIds.length > 0 && failures.length === 0, failures,
    visibleCloudPixelsVerified: false, lightingApproved: false, visualApproved: false };
}

/** Effective proxy readiness is required for private captures; submitted batches and pixels remain separate evidence. */
export type PrivateMaterialExpectation = Readonly<{ material: string; baseMaterial: string }>;

const privateCragSurface = (material: unknown): material is string => typeof material === 'string'
  && /^\/Game\/WorldRebuild\/AegisCitadel_[a-f0-9]{12}\/Materials\/(M_DistantCrag_(?:rock|dark_seam|snow))\.\1$/.test(material);

export function validatePrivateMaterialReadiness(readiness: any, bindings: any,
  expectedBindings?: readonly PrivateMaterialExpectation[]): void {
  if (!readiness || readiness.schemaVersion !== 1 || readiness.readOnly !== true
    || readiness.available !== true || readiness.ready !== true || readiness.renderBuffersReady !== true
    || !Number.isInteger(readiness.materialCount) || readiness.materialCount < 0 || readiness.materialCount > 256
    || readiness.readyMaterialCount !== readiness.materialCount
    || readiness.submittedMeshBatchVerified !== false || readiness.screenshotPixelBindingVerified !== false
    || !Array.isArray(bindings) || bindings.length > 4096)
    throw new Error('Private capture material readiness is missing or incomplete.');
  // Required interfaces come from the signed study audit, independently of discovered inventory.
  const expected = new Map<string, string>();
  if (expectedBindings !== undefined) {
    if (!Array.isArray(expectedBindings) || expectedBindings.length > 256)
      throw new Error('Expected private material bindings are invalid.');
    for (const row of expectedBindings) {
      const mountain = typeof row?.material === 'string'
        ? /^([/]Game[/]WorldRebuild[/]AegisCitadel_[a-f0-9]{12})[/]Materials[/]MI_PrivateSurface_mountain[.]MI_PrivateSurface_mountain$/.exec(row.material)
        : null;
      const expectedBase = mountain
        ? `${mountain[1]}/Materials/M_PrivateSurface_mountain.M_PrivateSurface_mountain` : row?.material;
      if (!row || typeof row.material !== 'string' || typeof row.baseMaterial !== 'string'
        || (!mountain && !row.material.includes('/M_PrivateSurface_') && !privateCragSurface(row.material)) || row.baseMaterial !== expectedBase
        || expected.has(row.material))
        throw new Error('Expected private material bindings contain duplicate or mismatched interfaces.');
      expected.set(row.material, row.baseMaterial);
    }
  }
  const sectionsSeen = new Set<string>();
  const used = bindings.filter((row: any) => row?.registered === true && row.visible === true
    && row.hiddenInGame === false && row.actorHidden === false
    && Array.isArray(row.renderSections) && row.renderSections.length > 0);
  const materials = new Set<string>();
  for (const row of used) {
    const resource = row.renderMaterial;
    const mountain = typeof row.material === 'string'
      ? /^([/]Game[/]WorldRebuild[/]AegisCitadel_[a-f0-9]{12})[/]Materials[/]MI_PrivateSurface_mountain[.]MI_PrivateSurface_mountain$/.exec(row.material)
      : null;
    const expectedBase = mountain
      ? `${mountain[1]}/Materials/M_PrivateSurface_mountain.M_PrivateSurface_mountain` : row.material;
    const knownBinding = mountain
      ? row.proxyInterface === row.material && row.hasStaticPermutationResource === false
        && typeof row.component === 'string' && row.component.startsWith(`${mountain[1]}/`) && row.materialSlot === 0
        && resource?.materialDomain === 0
      : typeof row.material === 'string' && (row.material.includes('/M_PrivateSurface_') || privateCragSurface(row.material));
    if (!knownBinding || row.baseMaterial !== expectedBase || row.renderBuffersAvailable !== true || row.rendererAvailable !== true
      || row.renderSections.some((section: any) => !Number.isInteger(section?.lod) || section.lod < 0
        || !Number.isInteger(section?.triangles) || section.triangles <= 0)
      || resource?.available !== true || resource.usedFallback !== false
      || resource.effectiveInterface !== row.baseMaterial || resource.shaderMapPresent !== true
      || resource.shaderMapValidForRendering !== true
      || row.submittedMeshBatchVerified !== false || row.screenshotPixelBindingVerified !== false || row.visualApproved !== false)
      throw new Error('Private capture uses a missing, fallback or mismatched effective material resource.');
    if (expectedBindings !== undefined) {
      if (typeof row.component !== 'string' || !Number.isInteger(row.materialSlot) || row.materialSlot < 0 || row.materialSlot > 255)
        throw new Error('Expected material coverage needs an actual component and material slot.');
      const sectionKey = `${row.component}:${row.materialSlot}`;
      if (sectionsSeen.has(sectionKey))
        throw new Error('Private material inventory duplicates a component slot.');
      sectionsSeen.add(sectionKey);
    }
    if (expected.has(row.material) && row.baseMaterial !== expected.get(row.material))
      throw new Error('Private capture differs from its signed material/base binding.');
    materials.add(row.material);
  }
  if (materials.size !== readiness.materialCount)
    throw new Error('Private capture material count differs from its visible render-section bindings.');
  if ([...expected.keys()].some(material => !materials.has(material)))
    throw new Error('Private capture omitted a required signed material binding.');
}

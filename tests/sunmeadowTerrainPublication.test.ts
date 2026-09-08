import { describe, expect, it } from 'vitest';
import { assertRenderReceipt, requiredViews, textureFile } from '../authoring/blender/sunmeadow-terrain/validate.mjs';

function fixture() {
  const models = [0, 1, 2].map(level => ({ level, model: `sector_lod${level}.glb`, sha256: `model${level}`,
    externalTextures: [{ uri: '../textures/sunmeadow_terrain/' + 'a'.repeat(20) + '.png', sha256: 'texture' }] }));
  const evidence = { buildSha256: 'build', sourceSha256: 'survey', models };
  const images = Object.fromEntries(requiredViews.map((image: string) => [image, image + '_sha']));
  const receipt = { schemaVersion: 1, buildSha256: 'build', sourceSha256: 'survey', views: requiredViews.map((image: string) => {
    const level = image === 'road_material.png' ? 0 : Number(image.match(/lod([012])/)![1]);
    return { image, imageSha256: images[image], models: models.filter(model => model.level === level).map(({ level: _, ...model }) => structuredClone(model)) };
  }) };
  return { receipt, evidence, images };
}

describe('terrain actual-export review evidence', () => {
  it('accepts complete matching render inputs and rejects stale mesh, texture, survey or image evidence', () => {
    const matching = fixture();
    expect(() => assertRenderReceipt(matching.receipt, matching.evidence, matching.images)).not.toThrow();
    const staleModel = fixture(); staleModel.evidence.models[1].sha256 = 'rebuilt';
    expect(() => assertRenderReceipt(staleModel.receipt, staleModel.evidence, staleModel.images)).toThrow(/mesh or external texture/);
    const staleTexture = fixture(); staleTexture.evidence.models[0].externalTextures[0].sha256 = 'repainted';
    expect(() => assertRenderReceipt(staleTexture.receipt, staleTexture.evidence, staleTexture.images)).toThrow(/mesh or external texture/);
    const staleSurvey = fixture(); staleSurvey.evidence.sourceSha256 = 'reshaped';
    expect(() => assertRenderReceipt(staleSurvey.receipt, staleSurvey.evidence, staleSurvey.images)).toThrow(/older survey/);
    const staleImage = fixture(); staleImage.images['road_material.png'] = 'replaced';
    expect(() => assertRenderReceipt(staleImage.receipt, staleImage.evidence, staleImage.images)).toThrow(/image changed/);
  });

  it('requires every reviewed LOD and the material view', () => {
    const missing = fixture(); missing.receipt.views.pop();
    expect(() => assertRenderReceipt(missing.receipt, missing.evidence, missing.images)).toThrow(/Four actual-export/);
    const duplicate = fixture(); duplicate.receipt.views[3] = duplicate.receipt.views[0];
    expect(() => assertRenderReceipt(duplicate.receipt, duplicate.evidence, duplicate.images)).toThrow(/Four actual-export/);
  });

  it('restricts external textures to the package texture directory', () => {
    expect(textureFile('../textures/sunmeadow_terrain/' + 'a'.repeat(20) + '.png')).toContain('sunmeadow_terrain');
    for (const unsafe of ['https://example.com/a.png', '../../secret.png', '../textures/sunmeadow_terrain/../a.png']) {
      expect(() => textureFile(unsafe)).toThrow(/Unexpected external terrain texture path/);
    }
  });
});

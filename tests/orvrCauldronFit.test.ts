import fs from 'node:fs';
import crypto from 'node:crypto';
import { describe, expect, it } from 'vitest';
// @ts-expect-error Authoring validation is an executable ESM module.
import { animationSignature, verifyContacts } from '../authoring/blender/orvr-frontier/cauldron-fit/tools/validate_repair.mjs';
// @ts-expect-error Authoring inspection is an executable ESM module.
import { readGlb } from '../authoring/blender/orvr-frontier/tools/inspect_mechanical_glb.mjs';

const draft = 'authoring/blender/orvr-frontier/cauldron-fit';
const read = (file: string) => JSON.parse(fs.readFileSync(file, 'utf8'));
const hash = (file: string) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');

describe('fitted cauldron export', () => {
  it('retains the actual six bowl contacts in every decreasing LOD', () => {
    const review = read(`${draft}/review/actual-export-review.json`);
    expect(review.models.map((m: { lod: number }) => m.lod)).toEqual([0, 1, 2]);
    for (const model of review.models) {
      expect(model.modelSha256).toBe(hash(`${draft}/runtime/${model.model}`));
      expect(() => verifyContacts(model.contacts)).not.toThrow();
    }
  });

  it('rejects a floating, buried, flattened, duplicated or invalid ornament', () => {
    const contacts = read(`${draft}/review/actual-export-review.json`).models[0].contacts;
    for (const change of [{ minimum_signed_distance_m: .015 }, { minimum_signed_distance_m: -.02 },
      { maximum_signed_distance_m: .001 }, { minimum_signed_distance_m: NaN }, { maximum_signed_distance_m: Infinity }]) {
      const changed = structuredClone(contacts); Object.assign(changed[0], change);
      expect(() => verifyContacts(changed)).toThrow();
    }
    expect(() => verifyContacts([...contacts.slice(1), contacts[1]])).toThrow();
  });

  it('publishes the reviewed replacement with every original pour key intact', () => {
    const manifest = read('scripts/blender-character-pipeline/data/approved-assets/frontier_oil_cauldron.approved.json');
    const qc = read(`public/assets/models/${manifest.qc}`);
    expect(manifest.hashes.qcSha256).toBe(hash(`public/assets/models/${manifest.qc}`));
    for (const lod of qc.lods) {
      const file = `public/assets/models/${lod.model}`;
      expect(hash(file)).toBe(hash(`${draft}/runtime/${lod.model}`));
      const original = readGlb(fs.readFileSync(`authoring/blender/orvr-frontier/runtime/${lod.model}`));
      expect(animationSignature(readGlb(fs.readFileSync(file)))).toEqual(animationSignature(original));
    }
    const catalog = read('shared/world/editor/prefabs.generated.json');
    const entry = catalog.find((item: { assetKey: string }) => item.assetKey === 'frontier_oil_cauldron');
    expect([entry.model, ...entry.lodModels]).toEqual(qc.lods.map((lod: { model: string }) => lod.model));
  });
});

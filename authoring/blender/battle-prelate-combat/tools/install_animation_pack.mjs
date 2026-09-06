import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { compileRuntimeRegistry } from '../../../../scripts/blender-character-pipeline/tools/runtime-registry.mjs';
import { writeJsonAtomic } from '../../../../scripts/blender-character-pipeline/tools/workspace-paths.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../../..');
const read = (p) => JSON.parse(fs.readFileSync(path.join(root, p), 'utf8'));
const write = (p, value) => {
  const destination = path.join(root, p);
  const text = JSON.stringify(value, null, 2) + '\n';
  if (fs.existsSync(destination) && fs.readFileSync(destination, 'utf8') === text) return;
  writeJsonAtomic(destination, value);
};
const audit = read('authoring/blender/battle-prelate-combat/review/bake_audit.json');
const model = 'anim_battle_prelate_combat.glb';
const sha256 = createHash('sha256').update(fs.readFileSync(path.join(root, 'public/assets/models', model))).digest('hex');
if (sha256 !== audit.sha256 || audit.clips.some((c) => c.maxFootTargetErrorM > .001 || c.maxWristTargetErrorM > .001)) throw new Error('Bake/contact verification failed');
const pack = { model, skeletonId: audit.skeletonId, bindPoseId: audit.bindPoseId, sha256 };
for (const variant of ['m', 'f']) {
  const p = `scripts/blender-character-pipeline/data/approved-assets/chr_civic_battle_prelate_t1_${variant}.approved.json`;
  const manifest = read(p);
  manifest.runtime.animationPack = pack;
  write(p, manifest);
}
// A rigid hammer fits the identical canonical hand sockets on either body.
// Register the female compatibility explicitly; do not weaken general equipment gates.
const femaleWeapon = read('scripts/blender-character-pipeline/data/approved-assets/wep_civic_battle_prelate_dawn_maul.approved.json');
femaleWeapon.assetId = 'wep.civic.battle_prelate.dawn_maul.t1.f';
femaleWeapon.runtime.bodyVariant = 'f';
femaleWeapon.compatibility.bodyVariant = 'f';
femaleWeapon.compatibility.bodyFamily = 'civic_battle_prelate_f';
femaleWeapon.provenance.animationCompatibility = 'Same canonical hand sockets; Battle Prelate combat pack grip tests cover both body variants. Geometry and textures unchanged.';
write('scripts/blender-character-pipeline/data/approved-assets/wep_civic_battle_prelate_dawn_maul_f.approved.json', femaleWeapon);
// Preserve unrelated in-progress registry entries rather than replacing the index.
const index = read('public/assets/models/asset-index.json');
for (const variant of ['m', 'f']) index.characterProfiles[`civic_battle_prelate_${variant}`].animationPack = pack;
const compiled = compileRuntimeRegistry();
index.equipment.weapon_hammer_reliquary_2h.variants.f = compiled.equipment.weapon_hammer_reliquary_2h.variants.f;
index.assetVersion = compiled.assetVersion;
write('public/assets/models/asset-index.json', index);
console.log(`Installed ${model} (${sha256}) for both Battle Prelate variants.`);

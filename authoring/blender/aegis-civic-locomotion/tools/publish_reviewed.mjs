import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const ROOT = fileURLToPath(new URL('../../../../', import.meta.url));
const WORK = path.join(ROOT, 'authoring/blender/aegis-civic-locomotion');
const PUBLIC = path.join(ROOT, 'public/assets/models');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const write = (file, value) => fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');
const reports = JSON.parse(fs.readFileSync(path.join(WORK, 'build-report.json')));
const reviewBytes = fs.readFileSync(path.join(WORK, 'review/approval.json'));
const review = JSON.parse(reviewBytes);
if (review.status !== 'approved' || !review.reviewedBy || !review.reviewedAt) throw new Error('Exported walking visual review is required');
const previewRoot = 'reviews/aegis-civic-locomotion';
fs.mkdirSync(path.join(PUBLIC, previewRoot), { recursive: true });
for (const [file, expected] of Object.entries(review.images)) {
  const bytes = fs.readFileSync(path.join(WORK, 'review', file));
  if (hash(bytes) !== expected) throw new Error(`Reviewed image changed: ${file}`);
  fs.writeFileSync(path.join(PUBLIC, previewRoot, file), bytes);
}
fs.writeFileSync(path.join(PUBLIC, previewRoot, 'approval.json'), reviewBytes);
for (const report of reports) {
  const model = fs.readFileSync(path.join(WORK, 'runtime', report.model));
  if (hash(model) !== report.modelSha256 || review.models[report.model] !== report.modelSha256) throw new Error(`Unreviewed model change: ${report.model}`);
  if (hash(fs.readFileSync(path.join(PUBLIC, report.source))) !== report.sourceSha256) throw new Error(`Reviewed source changed: ${report.source}`);
  if (report.validationErrors || report.validationWarnings) throw new Error(`Invalid export: ${report.model}`);
  fs.writeFileSync(path.join(PUBLIC, report.model), model);
  const stem = report.model.replace('.glb', ''), assetId = `chr.aegis.people.${report.variant}_walk`;
  const qc = { assetId, model: report.model, modelSha256: report.modelSha256, triangles: report.triangles,
    skeletonId: 'aegis_people_v1', bindPoseId: 'civic_relaxed_v1', clips: report.clips,
    usage: 'Aegis ambient walking civilians', authoredWalkSpeed: .9, validationErrors: 0, validationWarnings: 0,
    sourceModel: report.source, sourceSha256: report.sourceSha256, repairedVertices: report.repairedVertices,
    preservedChannels: 'Positions, topology, normals, tangents, UVs, embedded images, materials, skeleton and original idle clip unchanged',
    review: `${previewRoot}/approval.json` };
  write(path.join(PUBLIC, `${stem}.qc.json`), qc);
  const previews = { front: `${previewRoot}/walking_phase_10.png`, side: `${previewRoot}/walking_side.png`, walk: `${previewRoot}/walking_phase_80.png` };
  const approved = { schemaVersion: 1, assetId, displayName: `Aegis Walking Civilian ${report.variant.endsWith('female') ? 'Female' : 'Male'}`,
    category: 'character', model: report.model, qc: `${stem}.qc.json`, runtime: { profileKey: `npc_aegis_people_${report.variant}_walk` },
    compatibility: { bodyFamily: 'aegis_people', bodyVariant: report.variant.endsWith('female') ? 'f' : 'm', skeletonId: 'aegis_people_v1', bindPoseId: 'civic_relaxed_v1' },
    hashes: { modelSha256: report.modelSha256, qcSha256: hash(fs.readFileSync(path.join(PUBLIC, `${stem}.qc.json`))),
      previews: Object.fromEntries(Object.entries(previews).map(([name, file]) => [name, hash(fs.readFileSync(path.join(PUBLIC, file)))])) },
    previews, approvalState: 'approved', review: { reviewedBy: review.reviewedBy, reviewedAt: review.reviewedAt, reviewHash: hash(reviewBytes) },
    provenance: { sourceModel: report.source, sourceSha256: report.sourceSha256,
      authoring: 'authoring/blender/aegis-civic-locomotion', limitations: 'Middle-LOD ambient-only derivative with idle and gentle walk; no canonical combat animation compatibility. Original static reviewed models are unchanged.',
      triangles: report.triangles, preservedViews: report.preservedViews } };
  write(path.join(ROOT, 'scripts/blender-character-pipeline/data/approved-assets', `${stem}.approved.json`), approved);
  console.log(`Published reviewed ${report.model}`);
}

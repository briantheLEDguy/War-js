/** Register authoring intent and measurements without publishing runtime assets. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const repository = path.resolve(root, '../../..');
const directory = path.join(repository, 'scripts/blender-character-pipeline/data/asset-blueprints');
const sourceBytes = await fs.readFile(path.join(root, 'source/frontier_collection.json'));
const source = JSON.parse(sourceBytes);
const digest = (bytes) => crypto.createHash('sha256').update(bytes).digest('hex');
const sourceHash = digest(sourceBytes);
const topology = JSON.parse(await fs.readFile(path.join(root, 'review/topology_audit.json'), 'utf8'));
const records = [];
for (const [key, definition] of Object.entries(source.assets)) {
  if (!/^frontier_(supply_wagon|battering_ram|oil_cauldron|field_catapult|keep_gate)$/.test(key)) throw new Error(`Unexpected blueprint target: ${key}`);
  const report = JSON.parse(await fs.readFile(path.join(root, 'review', `${key}_build.json`), 'utf8'));
  if (report.source_sha256 !== sourceHash || report.lods.length !== 3) throw new Error(`Current three-LOD build is required: ${key}`);
  for (const lod of report.lods) {
    if (digest(await fs.readFile(path.join(root, lod.path.replaceAll('\\', '/')))) !== lod.sha256) throw new Error(`Stale LOD hash: ${key}/${lod.level}`);
  }
  const filename = `${key}_lod0.glb`;
  const materials = report.lods.map((lod) => lod.materials).join('/');
  const audit = topology.assets.find((entry) => entry.asset_id === key);
  if (!audit || audit.lods.some((lod) => lod.glb_sha256 !== report.lods.find((item) => item.level === lod.level)?.sha256)) throw new Error(`Current topology audit required: ${key}`);
  const edgeCounts = audit.lods.map((lod) => lod.meshes.reduce((sum, mesh) => sum + mesh.position_welded_boundary_edges + mesh.position_welded_multi_face_edges, 0));
  const sharedMesh = audit.lods.some((lod) => lod.meshes.some((mesh) => mesh.instances > 1));
  const topologyNote = `Export UV/normal seams were checked with coincident-position welding; boundary or multi-face edge counts LOD0/1/2 are ${edgeCounts.join('/')}. ${edgeCounts.some(Boolean) ? 'Nonmanifold allowance covers the assembled wheel patch joints; these are rendered surfaces, not certified watertight collision solids.' : 'The positional topology audit found no boundary or multi-face edges.'} ${sharedMesh ? 'UV overlap allowance deliberately shares the finished wheel mesh and atlas across four wheel instances; it does not approve arbitrary atlas-interior overlap.' : 'No repeated mesh-instance UV sharing is required.'} See authoring/blender/orvr-frontier/review/topology_audit.json for the exact method and hash-bound measurements.`;
  const blueprint = {
    assetId: `prop.frontier.${key.slice('frontier_'.length)}`,
    displayName: definition.name,
    category: 'prop',
    version: '1.0.0',
    sets: ['orvr_frontier_authored_siege'],
    runtime: { staticKey: key },
    output: { model: filename, artifactDir: 'authoring/blender/orvr-frontier/runtime' },
    generator: { kind: 'copyExisting', copyFrom: `authoring/blender/orvr-frontier/runtime/${filename}` },
    geometry: {
      originRule: key === 'frontier_oil_cauldron' ? 'parapet_mount_anchor' : 'root_grounded_mechanical_assembly',
      upAxis: '+Y', forwardAxis: '+Z',
      lods: report.lods.map((lod) => ({ name: `LOD${lod.level}`, triTarget: lod.triangles, screenCoverageMin: [0.2, 0.08, 0][lod.level] })),
    },
    materials: { master: 'MM_FrontierAuthoredPbr', textureSet: key, channels: ['baseColor', 'roughness', 'metallic', 'normal', 'occlusion'], maxTextureResolution: 2048 },
    rigging: { skinned: false, requiredClips: [] },
    collision: { policy: 'authoritative_orvr_hull', primitives: [] },
    compatibility: { occupiesSlots: ['prop'], requires: [], conflictsWith: [] },
    provenance: {
      createdBy: 'original_authored_mesh_control_cages', aiAssisted: true,
      aiStages: ['art_direction', 'literal_control_cage_authoring', 'material_painting', 'blender_finishing', 'pbr_baking', 'lod_authoring', 'technical_validation'],
      referencePackId: 'original_frontier_siege_v1', similarityReview: 'not_required',
      author: 'Codex frontier asset authoring', source: 'authoring/blender/orvr-frontier/source/frontier_collection.json', sourceSha256: sourceHash,
    },
    qc: {
      allowNonManifold: edgeCounts.some(Boolean), allowUvOverlap: sharedMesh,
      maxDrawCalls: Math.max(...report.lods.map((lod) => lod.rigid_nodes.length)),
      maxFileSizeMb: Math.ceil(Math.max(...report.lods.map((lod) => lod.bytes)) / 1_000_000),
      maxMeshObjects: Math.max(...report.lods.map((lod) => lod.rigid_nodes.length)),
      maxTris: Math.max(...report.lods.map((lod) => lod.triangles)), requiresSkinnedMeshes: false, requiresPreview: true,
      expectedHeightM: report.lods[0].bounds_z_up.maximum[2] - report.lods[0].bounds_z_up.minimum[2], heightToleranceM: 0.02,
    },
    lifecycle: {
      status: 'review_pending',
      notes: `Staged authored geometry only; internal visual acceptance is pending and runtime registry remains unchanged. Measured material counts for LOD0/1/2: ${materials}. Exact triangle counts, bounds, file hashes, mechanical pivots and texture provenance are retained in authoring/blender/orvr-frontier/review/${key}_build.json. ${topologyNote} ${definition.limitations.join(' ')}`,
    },
  };
  records.push({ file: path.join(directory, `${key}.asset.json`), blueprint });
}
for (const { file, blueprint } of records) await fs.writeFile(file, `${JSON.stringify(blueprint, null, 2)}\n`);
console.log(`Wrote ${records.length} review-pending manifest blueprints; no runtime models or registry entries were published.`);

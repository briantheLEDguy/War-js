import { execFile } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import {
  ASSET_INDEX_PATH,
  BLUEPRINT_DIR,
  MODEL_DIR,
  PIPELINE_ROOT,
  readConfig,
} from "./pipeline-lib.mjs";

const SPEC_PATH = path.join(PIPELINE_ROOT, "data", "external-imports.json");
const IMPORTER_SCRIPT = path.join(PIPELINE_ROOT, "blender", "import_external_assets.py");
const VERSION = "1.0.0";

const args = new Set(process.argv.slice(2));
const blueprintsOnly = args.has("--blueprints-only");
const skipBlender = args.has("--skip-blender");
const onlyArg = process.argv.slice(2).find((arg) => arg.startsWith("--only="));
const onlyOutput = onlyArg ? onlyArg.slice("--only=".length) : null;

const spec = JSON.parse(readFileSync(SPEC_PATH, "utf8"));

mkdirSync(BLUEPRINT_DIR, { recursive: true });
mkdirSync(MODEL_DIR, { recursive: true });

for (const record of spec.imports) {
  writeBlueprint(record);
}
console.log(`[external-import] wrote ${spec.imports.length} external asset blueprint(s).`);

if (!blueprintsOnly && !skipBlender) {
  await runBlenderImporter();
}

updateAssetIndex(spec.imports);
console.log("[external-import] asset-index updated.");

function writeBlueprint(record) {
  const fileName = `${record.output.replace(/\.glb$/i, "")}.asset.json`;
  const blueprint = {
    assetId: record.assetId,
    displayName: record.displayName,
    category: record.category,
    version: VERSION,
    sets: record.sets ?? ["external_imports"],
    runtime: record.runtime ?? {},
    output: {
      model: record.output,
      artifactDir: `artifacts/blender/external/${record.output.replace(/\.glb$/i, "")}`,
    },
    generator: {
      kind: "externalImport",
      source: record.source,
      sourceType: record.sourceType,
      objects: record.objects ?? undefined,
    },
    geometry: {
      originRule: record.ground === false ? "source_origin" : "root_grounded",
      upAxis: "+Y",
      forwardAxis: "+Z",
      lods: [
        {
          name: "LOD0",
          triTarget: record.decimate?.maxTris ?? record.qc?.maxTris ?? triTargetFor(record.category),
          screenCoverageMin: 0.2,
        },
      ],
    },
    materials: {
      master: record.category === "character" ? "MM_ExternalCharacterPbr" : "MM_ExternalPropPbr",
      textureSet: record.output.replace(/\.glb$/i, ""),
      channels: ["baseColor", "roughness", "metallic", "normal", "occlusion"],
    },
    rigging: record.exportAnimations
      ? {
          skinned: Boolean(record.exportSkins),
          maxInfluences: 4,
          requiredClips: [],
        }
      : undefined,
    collision: collisionPolicyFor(record.category),
    compatibility: {
      occupiesSlots: [record.category === "character" ? "character" : record.category],
      requires: [],
      conflictsWith: [],
    },
    provenance: {
      createdBy: "external_asset_import",
      aiAssisted: false,
      aiStages: [],
      promptIds: [],
      referencePackId: "external_user_supplied_assets",
      similarityReview: "not_required",
      source: record.source,
    },
    qc: {
      allowNonManifold: true,
      allowUvOverlap: true,
      maxDrawCalls: record.qc?.maxDrawCalls ?? 24,
      maxFileSizeMb: record.qc?.maxFileSizeMb ?? 12,
      maxMeshObjects: record.qc?.maxMeshObjects ?? 48,
      maxTris: record.qc?.maxTris,
      requiresSkinnedMeshes: Boolean(record.exportSkins),
    },
  };

  writeFileSync(
    path.join(BLUEPRINT_DIR, fileName),
    `${JSON.stringify(stripUndefined(blueprint), null, 2)}\n`,
    "utf8",
  );
}

function triTargetFor(category) {
  if (category === "terrain") return 250000;
  if (category === "character") return 70000;
  return 30000;
}

function collisionPolicyFor(category) {
  if (category === "character") {
    return {
      policy: "simple_capsule",
      primitives: [{ type: "capsule", tag: "body" }],
    };
  }
  if (category === "terrain") {
    return {
      policy: "authored_world_colliders",
      primitives: [{ type: "box", tag: "city_blockers" }],
    };
  }
  return {
    policy: "editor_prefab_default",
    primitives: [{ type: "box", tag: "prefab_footprint" }],
  };
}

function stripUndefined(value) {
  if (Array.isArray(value)) return value.map(stripUndefined);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(
    Object.entries(value)
      .filter(([, entry]) => entry !== undefined)
      .map(([key, entry]) => [key, stripUndefined(entry)]),
  );
}

function runBlenderImporter() {
  const config = readConfig();
  const blenderPath = config.blenderPath ?? "blender";
  if (!existsSync(blenderPath)) {
    throw new Error(`Blender not found at ${blenderPath}. Update ${path.join(PIPELINE_ROOT, "config.json")}.`);
  }
  if (!existsSync(IMPORTER_SCRIPT)) {
    throw new Error(`Missing external importer: ${IMPORTER_SCRIPT}`);
  }
  const blenderArgs = [
    "--background",
    "--python",
    IMPORTER_SCRIPT,
    "--",
    "--spec",
    SPEC_PATH,
  ];
  if (onlyOutput) blenderArgs.push("--only", onlyOutput);

  return new Promise((resolve, reject) => {
    execFile(
      blenderPath,
      blenderArgs,
      { cwd: PIPELINE_ROOT, timeout: 1_800_000, maxBuffer: 1024 * 1024 * 32 },
      (err, stdout, stderr) => {
        if (stdout) process.stdout.write(stdout);
        if (stderr) process.stderr.write(stderr);
        if (err) {
          reject(new Error(`${err.message}\n${stderr}`));
          return;
        }
        resolve();
      },
    );
  });
}

function updateAssetIndex(records) {
  const index = existsSync(ASSET_INDEX_PATH)
    ? JSON.parse(readFileSync(ASSET_INDEX_PATH, "utf8"))
    : { schemaVersion: 1 };

  index.generatedFrom = index.generatedFrom ?? "scripts/blender-character-pipeline/data/asset-blueprints";
  index.assetVersion = "2026-06-13-npc-variants";
  index.characterProfiles = index.characterProfiles ?? {};
  index.staticProps = index.staticProps ?? {};

  for (const record of records) {
    const runtime = record.runtime ?? {};
    if (runtime.profileKey) {
      index.characterProfiles[runtime.profileKey] = {
        assetId: record.assetId,
        model: record.output,
      };
    }
    if (runtime.staticKey) {
      index.staticProps[runtime.staticKey] = {
        assetId: record.assetId,
        model: record.output,
      };
    }
  }

  if (index.characterProfiles.aegis_warrior_guard) {
    index.characterProfiles.npc_external_warrior_guard = {
      ...index.characterProfiles.aegis_warrior_guard,
    };
  }

  writeFileSync(ASSET_INDEX_PATH, `${JSON.stringify(index, null, 2)}\n`, "utf8");
}

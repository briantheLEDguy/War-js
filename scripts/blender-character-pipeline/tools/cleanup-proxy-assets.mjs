import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  renameSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TOOL_DIR = path.dirname(fileURLToPath(import.meta.url));
const PIPELINE_ROOT = path.resolve(TOOL_DIR, "..");
const REPO_ROOT = path.resolve(PIPELINE_ROOT, "..", "..");
const BLUEPRINT_DIR = path.join(PIPELINE_ROOT, "data", "asset-blueprints");
const EXTERNAL_IMPORTS_PATH = path.join(PIPELINE_ROOT, "data", "external-imports.json");
const MODEL_DIR = path.join(REPO_ROOT, "public", "assets", "models");
const ASSET_INDEX_PATH = path.join(MODEL_DIR, "asset-index.json");

const RETIRED_GENERATOR_KINDS = new Set(["characterPreset", "armorModule", "bodyModule"]);
const RETIRED_DIRECT_CHARACTER_MODELS = ["guard_male.glb"];
const PUBLIC_SOURCE_PREFIX = "public/assets/new_models/";
const QUARANTINE_SOURCE_PREFIX = "authoring/quarantine/external-sources/";
const args = new Set(process.argv.slice(2));
const apply = args.has("--apply");
const check = args.has("--check");

assertRepositoryRoot();

const blueprintRecords = listBlueprintFiles().map((filePath) => ({
  filePath,
  blueprint: readJson(filePath),
}));
const removals = blueprintRecords.filter(({ blueprint }) => shouldRemoveBlueprint(blueprint));
const retainedExternalImports = blueprintRecords.filter(
  ({ blueprint }) => blueprint.generator?.kind === "externalImport" && !shouldRemoveBlueprint(blueprint),
);
const removedAssetIds = new Set(removals.map(({ blueprint }) => blueprint.assetId).filter(Boolean));
const removedModels = new Set(removals.map(({ blueprint }) => blueprint.output?.model).filter(Boolean));
const directCharacterModels = RETIRED_DIRECT_CHARACTER_MODELS.filter((model) =>
  existsSync(safePath(MODEL_DIR, model)),
);
for (const model of RETIRED_DIRECT_CHARACTER_MODELS) removedModels.add(model);

const filesToDelete = [];
for (const { filePath, blueprint } of removals) {
  filesToDelete.push(filePath);
  if (blueprint.output?.model) {
    const modelPath = safePath(MODEL_DIR, blueprint.output.model);
    filesToDelete.push(modelPath, modelPath.replace(/\.glb$/i, ".qc.json"));
  }
}
for (const model of directCharacterModels) {
  const modelPath = safePath(MODEL_DIR, model);
  filesToDelete.push(modelPath);
  const qcPath = modelPath.replace(/\.glb$/i, ".qc.json");
  if (existsSync(qcPath)) filesToDelete.push(qcPath);
}

const indexBefore = existsSync(ASSET_INDEX_PATH) ? readJson(ASSET_INDEX_PATH) : null;
const { index: indexAfter, removedBySection } = filterAssetIndex(indexBefore, removedAssetIds, removedModels);
const externalSpecBefore = existsSync(EXTERNAL_IMPORTS_PATH) ? readJson(EXTERNAL_IMPORTS_PATH) : null;
const externalSpecAfter = migrateExternalSpec(externalSpecBefore);
const pendingChanges =
  removals.length > 0 ||
  directCharacterModels.length > 0 ||
  Object.values(removedBySection).some((count) => count > 0) ||
  (externalSpecBefore?.imports ?? []).some((record) => record.category === "character") ||
  containsPublicSourcePrefix(externalSpecBefore) ||
  retainedExternalImports.some(({ blueprint }) => containsPublicSourcePrefix(blueprint)) ||
  existsSync(path.join(REPO_ROOT, "public", "assets", "new_models"));

const summary = {
  mode: apply ? "apply" : "dry-run",
  pendingChanges,
  retiredBlueprints: {
    total: removals.length,
    byReason: countBy(removals, ({ blueprint }) => removalReason(blueprint)),
  },
  retiredDirectCharacterModels: directCharacterModels.length,
  runtimeFiles: {
    planned: filesToDelete.length,
    present: filesToDelete.filter(existsSync).length,
    missing: filesToDelete.filter((filePath) => !existsSync(filePath)).length,
  },
  indexEntriesRemoved: removedBySection,
  externalImports: {
    characterRecordsRemoved: (externalSpecBefore?.imports ?? []).filter((record) => record.category === "character").length,
    retainedRecords: externalSpecAfter?.imports?.length ?? 0,
    retainedBlueprintsRepointed: retainedExternalImports.filter(({ blueprint }) =>
      containsPublicSourcePrefix(blueprint),
    ).length,
  },
  sourceMigration: {
    from: PUBLIC_SOURCE_PREFIX,
    to: QUARANTINE_SOURCE_PREFIX,
    filesystemMoveRequired: existsSync(path.join(REPO_ROOT, "public", "assets", "new_models")),
  },
};

if (apply) {
  for (const filePath of filesToDelete) {
    if (existsSync(filePath)) unlinkSync(filePath);
  }

  if (indexAfter) writeJsonAtomic(ASSET_INDEX_PATH, indexAfter);
  if (externalSpecAfter) writeJsonAtomic(EXTERNAL_IMPORTS_PATH, externalSpecAfter);

  for (const { filePath, blueprint } of retainedExternalImports) {
    const migratedBlueprint = rewriteSourcePaths(blueprint);
    writeJsonAtomic(filePath, migratedBlueprint);

    const model = migratedBlueprint.output?.model;
    if (!model) continue;
    const qcPath = safePath(MODEL_DIR, model.replace(/\.glb$/i, ".qc.json"));
    if (existsSync(qcPath)) writeJsonAtomic(qcPath, rewriteSourcePaths(readJson(qcPath)));
  }
}

process.stdout.write(`${JSON.stringify(summary, null, 2)}\n`);
if (check && pendingChanges) process.exitCode = 1;

function assertRepositoryRoot() {
  const packagePath = safePath(REPO_ROOT, "package.json");
  if (!existsSync(packagePath)) {
    throw new Error(`Refusing cleanup because package.json is missing from ${REPO_ROOT}.`);
  }
  const packageJson = readJson(packagePath);
  if (packageJson.name !== "war-js") {
    throw new Error(`Refusing cleanup in unexpected repository ${REPO_ROOT}.`);
  }
}

function safePath(root, ...segments) {
  const resolvedRoot = path.resolve(root);
  const resolved = path.resolve(root, ...segments);
  const relative = path.relative(resolvedRoot, resolved);
  if (relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    throw new Error(`Path escapes cleanup root: ${resolved}`);
  }
  return resolved;
}

function listBlueprintFiles() {
  if (!existsSync(BLUEPRINT_DIR)) return [];
  return readdirSync(BLUEPRINT_DIR)
    .filter((file) => file.endsWith(".asset.json"))
    .sort()
    .map((file) => safePath(BLUEPRINT_DIR, file));
}

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8"));
}

function writeJsonAtomic(filePath, value) {
  const safeFilePath = safePath(REPO_ROOT, path.relative(REPO_ROOT, filePath));
  mkdirSync(path.dirname(safeFilePath), { recursive: true });
  const temporary = `${safeFilePath}.${process.pid}.tmp`;
  writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, "utf8");
  renameSync(temporary, safeFilePath);
}

function shouldRemoveBlueprint(blueprint) {
  return (
    RETIRED_GENERATOR_KINDS.has(blueprint.generator?.kind) ||
    (blueprint.generator?.kind === "externalImport" && blueprint.category === "character")
  );
}

function removalReason(blueprint) {
  if (RETIRED_GENERATOR_KINDS.has(blueprint.generator?.kind)) return blueprint.generator.kind;
  return "unverifiedExternalCharacter";
}

function countBy(records, selector) {
  const counts = {};
  for (const record of records) {
    const key = selector(record);
    counts[key] = (counts[key] ?? 0) + 1;
  }
  return Object.fromEntries(Object.entries(counts).sort(([left], [right]) => left.localeCompare(right)));
}

function entryReferencesRemovedAsset(entry, removedAssetIds, removedModels) {
  if (!entry || typeof entry !== "object") return false;
  if (removedAssetIds.has(entry.assetId)) return true;
  if (removedModels.has(entry.model) || removedModels.has(entry.bodyModel)) return true;
  if (entry.variants && typeof entry.variants === "object") {
    return Object.values(entry.variants).some((variant) =>
      entryReferencesRemovedAsset(variant, removedAssetIds, removedModels),
    );
  }
  return false;
}

function filterAssetIndex(index, removedAssetIds, removedModels) {
  if (!index) return { index: null, removedBySection: {} };
  const result = structuredClone(index);
  const removedBySection = {};

  for (const section of ["characterProfiles", "baseBodies", "equipment", "staticProps"]) {
    const entries = result[section];
    if (!entries || typeof entries !== "object" || Array.isArray(entries)) continue;
    const retained = {};
    let removed = 0;
    for (const [key, entry] of Object.entries(entries)) {
      if (entryReferencesRemovedAsset(entry, removedAssetIds, removedModels)) {
        removed += 1;
      } else {
        retained[key] = entry;
      }
    }
    result[section] = retained;
    removedBySection[section] = removed;
  }

  result.assetVersion = "2026-07-11-character-proxy-cleanup";
  return { index: result, removedBySection };
}

function migrateExternalSpec(spec) {
  if (!spec) return null;
  return rewriteSourcePaths({
    ...spec,
    imports: (spec.imports ?? []).filter((record) => record.category !== "character"),
  });
}

function containsPublicSourcePrefix(value) {
  if (typeof value === "string") return value.startsWith(PUBLIC_SOURCE_PREFIX);
  if (Array.isArray(value)) return value.some(containsPublicSourcePrefix);
  if (!value || typeof value !== "object") return false;
  return Object.values(value).some(containsPublicSourcePrefix);
}

function rewriteSourcePaths(value) {
  if (typeof value === "string") {
    return value.startsWith(PUBLIC_SOURCE_PREFIX)
      ? `${QUARANTINE_SOURCE_PREFIX}${value.slice(PUBLIC_SOURCE_PREFIX.length)}`
      : value;
  }
  if (Array.isArray(value)) return value.map(rewriteSourcePaths);
  if (!value || typeof value !== "object") return value;
  return Object.fromEntries(Object.entries(value).map(([key, entry]) => [key, rewriteSourcePaths(entry)]));
}

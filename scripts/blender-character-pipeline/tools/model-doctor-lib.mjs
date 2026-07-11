import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import {
  createReadStream,
  existsSync,
  readFileSync,
  readdirSync,
  statSync,
} from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const TOOL_DIR = path.dirname(fileURLToPath(import.meta.url));
export const PIPELINE_ROOT = path.resolve(TOOL_DIR, "..");
export const BODY_FAMILY_DIR = path.join(PIPELINE_ROOT, "data", "body-families");
const CONFIG_PATH = path.join(PIPELINE_ROOT, "config.json");

const FAMILY_FILES = [
  "civic_humanoid_v2.body-family.json",
  "mire_brutish_v1.body-family.json",
];
const TEMPLATE_FILES = [
  "templates/mpfb-local.provenance.template.json",
  "templates/stable-fast-3d-cpu.provenance.template.json",
];
const EXPECTED_SLOTS = [
  "head",
  "shoulders",
  "chest",
  "hands",
  "waist",
  "legs",
  "feet",
  "back",
  "tabard",
];
const EXPECTED_SOCKETS = [
  "socket_root",
  "socket_hand_L",
  "socket_hand_R",
  "socket_back",
];

function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8"));
}

function normalizeVersion(version) {
  return String(version ?? "")
    .match(/\d+(?:\.\d+){1,3}/)?.[0]
    ?.split(".")
    .map((part) => Number.parseInt(part, 10)) ?? [];
}

export function compareVersions(actual, required) {
  const left = normalizeVersion(actual);
  const right = normalizeVersion(required);
  const length = Math.max(left.length, right.length);
  for (let index = 0; index < length; index += 1) {
    const difference = (left[index] ?? 0) - (right[index] ?? 0);
    if (difference !== 0) return Math.sign(difference);
  }
  return 0;
}

function unique(values) {
  return [...new Set(values.filter(Boolean).map((value) => path.resolve(value)))];
}

function sameList(actual, expected) {
  return (
    Array.isArray(actual) &&
    actual.length === expected.length &&
    actual.every((value, index) => value === expected[index])
  );
}

function isSha256(value) {
  return /^[a-f0-9]{64}$/i.test(value ?? "");
}

function addCheck(checks, id, status, message, details = undefined) {
  checks.push({ id, status, message, ...(details ? { details } : {}) });
}

function loadDefinition(fileName, checks) {
  const filePath = path.join(BODY_FAMILY_DIR, fileName);
  if (!existsSync(filePath)) {
    addCheck(checks, `definition:${fileName}`, "fail", `Missing definition: ${filePath}`);
    return null;
  }
  try {
    return readJson(filePath);
  } catch (error) {
    addCheck(
      checks,
      `definition:${fileName}`,
      "fail",
      `Invalid JSON in ${filePath}: ${error.message}`,
    );
    return null;
  }
}

function validateBoneGraph(skeleton, checks) {
  const bones = Array.isArray(skeleton?.bones) ? skeleton.bones : [];
  const names = bones.map((bone) => bone.name);
  const nameSet = new Set(names);
  const duplicates = names.filter((name, index) => names.indexOf(name) !== index);
  const invalidParents = bones
    .filter((bone) => bone.parent !== null && !nameSet.has(bone.parent))
    .map((bone) => `${bone.name}->${bone.parent}`);

  const cycleNodes = [];
  for (const bone of bones) {
    const visited = new Set();
    let current = bone;
    while (current?.parent) {
      if (visited.has(current.name)) {
        cycleNodes.push(bone.name);
        break;
      }
      visited.add(current.name);
      current = bones.find((candidate) => candidate.name === current.parent);
    }
  }

  const maximum = skeleton?.limits?.maxBones;
  const valid =
    skeleton?.skeletonId === "humanoid_game_v2" &&
    skeleton?.bindPose?.bindPoseId === "a_pose_v2" &&
    bones.length > 0 &&
    Number.isInteger(maximum) &&
    bones.length <= maximum &&
    duplicates.length === 0 &&
    invalidParents.length === 0 &&
    cycleNodes.length === 0;

  addCheck(
    checks,
    "definitions:skeleton",
    valid ? "pass" : "fail",
    valid
      ? `Canonical humanoid_game_v2 contains ${bones.length} acyclic bones within its ${maximum}-bone budget.`
      : "Canonical skeleton hierarchy or budget is invalid.",
    valid
      ? undefined
      : { boneCount: bones.length, maximum, duplicates, invalidParents, cycleNodes },
  );

  const socketNames = skeleton?.sockets?.map((socket) => socket.name) ?? [];
  const socketParentsValid =
    skeleton?.sockets?.every((socket) => nameSet.has(socket.parentBone)) ?? false;
  const socketsValid = sameList(socketNames, EXPECTED_SOCKETS) && socketParentsValid;
  addCheck(
    checks,
    "definitions:sockets",
    socketsValid ? "pass" : "fail",
    socketsValid
      ? "Canonical root, left/right hand, and back sockets are present and parented to valid bones."
      : "Canonical sockets are missing, out of order, or parented to unknown bones.",
    socketsValid ? undefined : { expected: EXPECTED_SOCKETS, actual: socketNames },
  );
}

function validateFamilies(families, policy, toolchain, checks) {
  const packIds = new Set(toolchain?.assetPacks?.map((pack) => pack.id) ?? []);
  const expectedFamilies = policy?.bodyFamilies ?? [];
  const outputs = new Set();
  const errors = [];

  for (const family of families) {
    if (!expectedFamilies.includes(family?.bodyFamily)) {
      errors.push(`unexpected body family ${family?.bodyFamily ?? "<missing>"}`);
    }
    if (family?.sourceTopology?.generator !== "MPFB") {
      errors.push(`${family?.bodyFamily}: generator must be MPFB`);
    }
    if (family?.sourceTopology?.generatorVersion !== "2.0.16") {
      errors.push(`${family?.bodyFamily}: MPFB version must be 2.0.16`);
    }
    if (family?.sourceTopology?.baseMesh !== "hm08") {
      errors.push(`${family?.bodyFamily}: base mesh must be hm08`);
    }
    if (family?.skeletonId !== "humanoid_game_v2" || family?.bindPoseId !== "a_pose_v2") {
      errors.push(`${family?.bodyFamily}: canonical skeleton/bind pose mismatch`);
    }
    if (!sameList(family?.armorSlots, EXPECTED_SLOTS)) {
      errors.push(`${family?.bodyFamily}: armor slots must match the nine-slot contract`);
    }
    for (const packId of family?.requiredAssetPacks ?? []) {
      if (!packIds.has(packId)) errors.push(`${family?.bodyFamily}: unknown asset pack ${packId}`);
    }
    for (const variantKey of ["m", "f"]) {
      const variant = family?.variants?.[variantKey];
      if (!variant || variant.variant !== variantKey) {
        errors.push(`${family?.bodyFamily}: missing or mismatched ${variantKey} variant`);
        continue;
      }
      if (variant?.mpfbPreset?.creationApi !== "HumanService.create_human") {
        errors.push(`${family?.bodyFamily}/${variantKey}: unsupported MPFB creation API`);
      }
      if (variant?.mpfbPreset?.rig !== "game_engine") {
        errors.push(`${family?.bodyFamily}/${variantKey}: MPFB source rig must be game_engine`);
      }
      const propertyValues = variant?.mpfbPreset?.propertyValues ?? {};
      const expectedGender = variantKey === "m" ? 1.0 : 0.0;
      if (propertyValues.gender !== expectedGender) {
        errors.push(
          `${family?.bodyFamily}/${variantKey}: MPFB gender must be ${expectedGender} (${variantKey === "m" ? "male" : "female"})`,
        );
      }
      if (!Number.isFinite(propertyValues.proportions) || "bodyproportions" in propertyValues) {
        errors.push(`${family?.bodyFamily}/${variantKey}: use the MPFB macro key proportions`);
      }
      if (outputs.has(variant.outputModel)) {
        errors.push(`duplicate body output ${variant.outputModel}`);
      }
      outputs.add(variant.outputModel);
    }
    if (
      family?.promotion?.promotionEligible !== false ||
      !["specification", "candidate"].includes(family?.promotion?.state)
    ) {
      errors.push(`${family?.bodyFamily}: unreviewed recipe must remain non-promotable`);
    }
  }

  const actualFamilyIds = families.map((family) => family?.bodyFamily).sort();
  const expectedFamilyIds = [...expectedFamilies].sort();
  if (!sameList(actualFamilyIds, expectedFamilyIds)) {
    errors.push(`family set mismatch (${actualFamilyIds.join(", ")})`);
  }

  addCheck(
    checks,
    "definitions:body-families",
    errors.length === 0 ? "pass" : "fail",
    errors.length === 0
      ? "Civic Humanoid and Mire Brutish each define deterministic male/female MPFB recipes."
      : "Body-family definitions violate the pilot contract.",
    errors.length === 0 ? undefined : { errors },
  );
}

function validatePolicy(policy, toolchain, checks) {
  const policySlots = policy?.armorSlots?.map((entry) => entry.slot);
  const noCost =
    policy?.costPolicy?.currencyBudget === 0 &&
    policy?.costPolicy?.paidServicesAllowed === false &&
    policy?.costPolicy?.remoteGenerationAllowed === false &&
    Array.isArray(toolchain?.paidProviders) &&
    toolchain.paidProviders.length === 0;
  addCheck(
    checks,
    "definitions:zero-cost-policy",
    noCost ? "pass" : "fail",
    noCost
      ? "Pilot policy forbids paid and remote generation and has a currency budget of zero."
      : "Pilot/toolchain configuration permits a paid or remote generation path.",
  );

  const slotsValid = sameList(policySlots, EXPECTED_SLOTS);
  addCheck(
    checks,
    "definitions:armor-slots",
    slotsValid ? "pass" : "fail",
    slotsValid
      ? "Pilot policy defines the required nine modular armor slots."
      : "Pilot armor slots do not match the required nine-slot order.",
    slotsValid ? undefined : { expected: EXPECTED_SLOTS, actual: policySlots },
  );

  const qc = policy?.qc;
  const budgetsValid =
    qc?.equippedCharacter?.maxTriangles === 120000 &&
    qc?.equippedCharacter?.maxDrawCalls === 16 &&
    qc?.rigging?.maxInfluencesPerVertex === 4 &&
    qc?.materials?.maxTextureDimension === 2048 &&
    qc?.topology?.declaredLodsMustExist === true &&
    Array.isArray(qc?.rigging?.requiredClips) &&
    qc.rigging.requiredClips.length === 9;
  addCheck(
    checks,
    "definitions:qc-budgets",
    budgetsValid ? "pass" : "fail",
    budgetsValid
      ? "Pilot QC caps equipped characters at 120k triangles, 16 draw calls, four influences, and 2K textures."
      : "Pilot QC budgets are incomplete or have drifted from the acceptance contract.",
  );
}

function validateTemplates(templates, checks) {
  const errors = [];
  for (const template of templates) {
    if (template?.provider?.costCurrency !== 0) errors.push("candidate provider cost must be zero");
    if (!['local_open_source', 'manual_local'].includes(template?.provider?.kind)) {
      errors.push(`non-local provider kind ${template?.provider?.kind}`);
    }
    if (template?.review?.state !== "draft" || template?.qc?.status !== "not_run") {
      errors.push(`${template?.creationMethod}: template must start draft with QC not run`);
    }
    if (template?.skeletonId !== "humanoid_game_v2" || template?.bindPoseId !== "a_pose_v2") {
      errors.push(`${template?.creationMethod}: canonical skeleton/bind pose mismatch`);
    }
    if (template?.creationMethod === "stable_fast_3d_local_handoff") {
      if (template?.inputs?.device !== "cpu" || template?.provider?.gitRevision !== null) {
        errors.push("Stable Fast 3D template must be CPU-only and require the operator to fill a revision");
      }
    }
  }
  addCheck(
    checks,
    "definitions:provenance-templates",
    errors.length === 0 ? "pass" : "fail",
    errors.length === 0
      ? "Local MPFB and optional Stable Fast 3D CPU provenance templates are draft-only and zero-cost."
      : "Local provenance templates violate the candidate contract.",
    errors.length === 0 ? undefined : { errors },
  );
}

export function validateDefinitions() {
  const checks = [];
  const policy = loadDefinition("pilot-policy.json", checks);
  const toolchain = loadDefinition("free-toolchain.json", checks);
  const skeleton = loadDefinition("humanoid_game_v2.skeleton.json", checks);
  const families = FAMILY_FILES.map((fileName) => loadDefinition(fileName, checks)).filter(Boolean);
  const templates = TEMPLATE_FILES.map((fileName) => loadDefinition(fileName, checks)).filter(Boolean);
  loadDefinition("body-family.schema.json", checks);
  loadDefinition("local-candidate-provenance.schema.json", checks);

  if (skeleton) validateBoneGraph(skeleton, checks);
  if (policy && toolchain) validatePolicy(policy, toolchain, checks);
  if (policy && toolchain && families.length === FAMILY_FILES.length) {
    validateFamilies(families, policy, toolchain, checks);
  }
  if (templates.length === TEMPLATE_FILES.length) validateTemplates(templates, checks);

  if (!checks.some((check) => check.id.startsWith("definition:") && check.status === "fail")) {
    addCheck(
      checks,
      "definitions:json",
      "pass",
      `Loaded ${3 + FAMILY_FILES.length + TEMPLATE_FILES.length + 2} pilot definition files as valid JSON.`,
    );
  }

  return { checks, policy, toolchain, skeleton, families, templates };
}

function configuredBlenderPath() {
  if (!existsSync(CONFIG_PATH)) return null;
  try {
    return readJson(CONFIG_PATH).blenderPath ?? null;
  } catch {
    return null;
  }
}

function runBlenderVersion(candidate) {
  const result = spawnSync(candidate, ["--version"], {
    encoding: "utf8",
    timeout: 10000,
    windowsHide: true,
  });
  if (result.error || result.status !== 0) return null;
  const text = `${result.stdout ?? ""}\n${result.stderr ?? ""}`;
  const version = text.match(/Blender\s+(\d+(?:\.\d+){1,3})/i)?.[1];
  return version ? { path: candidate, version } : null;
}

function discoverBlender(options) {
  const platformCandidates = process.platform === "win32" ? [
    "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe",
    "C:\\Program Files\\Blender Foundation\\Blender 4.3\\blender.exe",
    "C:\\Program Files\\Blender Foundation\\Blender 4.2\\blender.exe",
  ] : [];
  const candidates = unique([
    options.blenderPath,
    process.env.BLENDER_PATH,
    configuredBlenderPath(),
    ...platformCandidates,
  ]);
  for (const candidate of candidates) {
    if (!existsSync(candidate)) continue;
    const discovered = runBlenderVersion(candidate);
    if (discovered) return { ...discovered, attempted: [...candidates, "blender"] };
  }
  const fromPath = runBlenderVersion("blender");
  return fromPath
    ? { ...fromPath, attempted: [...candidates, "blender"] }
    : { path: null, version: null, attempted: [...candidates, "blender"] };
}

function blenderUserRoots(version) {
  const majorMinor = normalizeVersion(version).slice(0, 2).join(".");
  if (!majorMinor) return [];
  if (process.platform === "win32") {
    return process.env.APPDATA
      ? [path.join(process.env.APPDATA, "Blender Foundation", "Blender", majorMinor)]
      : [];
  }
  if (process.platform === "darwin") {
    return [path.join(os.homedir(), "Library", "Application Support", "Blender", majorMinor)];
  }
  return [path.join(os.homedir(), ".config", "blender", majorMinor)];
}

function mpfbCandidates(options, blenderVersion) {
  const explicit = [options.mpfbPath, process.env.MPFB_PATH];
  const discovered = [];
  for (const userRoot of blenderUserRoots(blenderVersion)) {
    for (const extensionSource of ["blender_org", "user_default"]) {
      for (const extensionId of ["mpfb", "mpfb2"]) {
        discovered.push(path.join(userRoot, "extensions", extensionSource, extensionId));
      }
    }
    for (const extensionId of ["mpfb", "mpfb2"]) {
      discovered.push(path.join(userRoot, "scripts", "addons", extensionId));
    }
  }
  return unique([...explicit, ...discovered]);
}

function readMpfbVersion(rootPath) {
  const manifestPath = path.join(rootPath, "blender_manifest.toml");
  if (existsSync(manifestPath)) {
    const contents = readFileSync(manifestPath, "utf8");
    const version = contents.match(/^version\s*=\s*["']([^"']+)["']/m)?.[1];
    if (version) return { version, manifestPath };
  }
  const legacyPath = path.join(rootPath, "__init__.py");
  if (existsSync(legacyPath)) {
    const contents = readFileSync(legacyPath, "utf8");
    const tuple = contents.match(/["']version["']\s*:\s*\(([^)]+)\)/)?.[1];
    if (tuple) {
      const version = [...tuple.matchAll(/\d+/g)].map((match) => match[0]).join(".");
      if (version) return { version, manifestPath: legacyPath };
    }
  }
  return null;
}

function discoverMpfb(options, blenderVersion) {
  const candidates = mpfbCandidates(options, blenderVersion);
  for (const candidate of candidates) {
    if (!existsSync(candidate)) continue;
    const versionInfo = readMpfbVersion(candidate);
    if (versionInfo) return { path: candidate, ...versionInfo, attempted: candidates };
  }
  return { path: null, version: null, manifestPath: null, attempted: candidates };
}

function normalizeAssetRoot(candidate) {
  if (!candidate || !existsSync(candidate)) return null;
  for (const possible of [candidate, path.join(candidate, "data")]) {
    if (existsSync(path.join(possible, "packs"))) return possible;
  }
  return null;
}

function assetRootCandidates(options, blenderVersion, mpfbRoot) {
  const candidates = [options.assetRoot, process.env.MPFB_ASSET_ROOT];
  for (const userRoot of blenderUserRoots(blenderVersion)) {
    for (const extensionSource of ["blender_org", "user_default"]) {
      for (const extensionId of ["mpfb", "mpfb2"]) {
        candidates.push(
          path.join(userRoot, "extensions", ".user", extensionSource, extensionId, "data"),
        );
      }
    }
  }
  if (mpfbRoot) {
    candidates.push(path.join(mpfbRoot, "data"), path.join(mpfbRoot, "user_data", "data"));
  }
  candidates.push(
    path.join(os.homedir(), "mpfb-data"),
    path.join(os.homedir(), "Documents", "makehuman", "v1py3", "data"),
  );
  return unique(candidates);
}

function discoverAssetRoot(options, blenderVersion, mpfbRoot) {
  const candidates = assetRootCandidates(options, blenderVersion, mpfbRoot);
  for (const candidate of candidates) {
    const normalized = normalizeAssetRoot(candidate);
    if (normalized) return { path: normalized, attempted: candidates };
  }
  return { path: null, attempted: candidates };
}

function packMetadataFiles(assetRoot) {
  const packDir = path.join(assetRoot, "packs");
  if (!existsSync(packDir)) return [];
  return readdirSync(packDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.toLowerCase().endsWith(".json"))
    .map((entry) => path.join(packDir, entry.name))
    .sort();
}

function normalizedToken(value) {
  return String(value ?? "").toLowerCase().replace(/[^a-z0-9]/g, "");
}

function findPackMetadata(files, aliases) {
  const normalizedAliases = aliases.map(normalizedToken);
  for (const filePath of files) {
    let searchable = path.basename(filePath);
    try {
      searchable += ` ${readFileSync(filePath, "utf8")}`;
    } catch {
      continue;
    }
    const normalized = normalizedToken(searchable);
    if (normalizedAliases.some((alias) => normalized.includes(alias))) return filePath;
  }
  return null;
}

function loadChecksumLock(filePath) {
  if (!filePath) return {};
  const record = readJson(filePath);
  return record.archives ?? record;
}

async function sha256File(filePath) {
  return new Promise((resolve, reject) => {
    const hash = createHash("sha256");
    const stream = createReadStream(filePath);
    stream.on("error", reject);
    stream.on("data", (chunk) => hash.update(chunk));
    stream.on("end", () => resolve(hash.digest("hex")));
  });
}

function archiveRoots(options) {
  return unique([
    options.packArchiveRoot,
    process.env.MPFB_PACK_ARCHIVE_DIR,
    path.join(os.homedir(), "Downloads"),
  ]);
}

function findArchive(fileName, roots) {
  for (const root of roots) {
    const candidate = path.join(root, fileName);
    if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
  }
  return null;
}

async function checkAssetPacks(toolchain, assetRoot, options, checks) {
  const metadataFiles = packMetadataFiles(assetRoot);
  let checksumLock = {};
  if (options.checksumLock) {
    try {
      checksumLock = loadChecksumLock(path.resolve(options.checksumLock));
    } catch (error) {
      addCheck(
        checks,
        "packs:checksum-lock",
        "fail",
        `Could not read checksum lock ${options.checksumLock}: ${error.message}`,
      );
    }
  }

  const roots = archiveRoots(options);
  for (const pack of toolchain.assetPacks ?? []) {
    const metadataPath = findPackMetadata(metadataFiles, pack.packIdAliases ?? [pack.id]);
    addCheck(
      checks,
      `pack:${pack.id}:installed`,
      metadataPath ? "pass" : pack.required ? "fail" : "warn",
      metadataPath
        ? `${pack.id} is registered in MPFB pack metadata.`
        : `${pack.id} is not registered under ${path.join(assetRoot, "packs")}.`,
      metadataPath ? { metadataPath } : { downloadPage: pack.downloadPage },
    );

    const missingMarkers = (pack.requiredMarkers ?? []).filter(
      (relativePath) => !existsSync(path.join(assetRoot, ...relativePath.split("/"))),
    );
    addCheck(
      checks,
      `pack:${pack.id}:contents`,
      missingMarkers.length === 0 ? "pass" : "fail",
      missingMarkers.length === 0
        ? `${pack.id} contains the required pilot assets.`
        : `${pack.id} is registered but its extraction is incomplete.`,
      missingMarkers.length === 0 ? undefined : { missingMarkers },
    );

    const pinned = pack.checksum?.expectedSha256?.toLowerCase();
    const fromEnvironment = process.env[pack.checksum?.expectedEnvironmentVariable]?.toLowerCase();
    const fromLock = String(checksumLock[pack.id] ?? "").toLowerCase() || null;
    for (const [source, value] of [
      ["pinned manifest", pinned],
      ["environment", fromEnvironment],
      ["checksum lock", fromLock],
    ]) {
      if (value && !isSha256(value)) {
        addCheck(
          checks,
          `pack:${pack.id}:expected-sha-format:${source}`,
          "fail",
          `${pack.id} has an invalid SHA-256 value from ${source}.`,
        );
      }
    }
    const configuredValues = [pinned, fromEnvironment, fromLock].filter(isSha256);
    const disagree = new Set(configuredValues).size > 1;
    if (disagree) {
      addCheck(
        checks,
        `pack:${pack.id}:expected-sha-conflict`,
        "fail",
        `${pack.id} checksum sources disagree; the pinned digest must not be overridden silently.`,
      );
    }
    const expected = pinned ?? fromEnvironment ?? fromLock;
    const archivePath = findArchive(pack.archiveFile, roots);
    if (!archivePath) {
      addCheck(
        checks,
        `pack:${pack.id}:archive-sha256`,
        "warn",
        `Installed ${pack.id} can be used, but ${pack.archiveFile} was not retained so its pinned SHA-256 could not be rechecked.`,
        { expectedSha256: expected ?? null, searchedRoots: roots },
      );
      continue;
    }
    const actual = await sha256File(archivePath);
    const matches = isSha256(expected) && actual === expected;
    addCheck(
      checks,
      `pack:${pack.id}:archive-sha256`,
      matches ? "pass" : "fail",
      matches
        ? `${pack.archiveFile} matches its pinned SHA-256.`
        : `${pack.archiveFile} does not match its pinned SHA-256.`,
      { archivePath, expectedSha256: expected ?? null, actualSha256: actual },
    );
  }
}

function checkFamilySources(families, checks) {
  const checkedPaths = new Set();
  for (const family of families) {
    for (const variant of Object.values(family.variants ?? {})) {
      for (const target of variant.customTargets ?? []) {
        if (!target.required) continue;
        const targetPath = path.resolve(BODY_FAMILY_DIR, target.relativePath);
        if (checkedPaths.has(targetPath)) continue;
        checkedPaths.add(targetPath);
        const exists = existsSync(targetPath) && statSync(targetPath).isFile();
        if (!exists) {
          addCheck(
            checks,
            `family-source:${family.bodyFamily}:${target.id}`,
            "fail",
            `Required original target ${target.id} has not been authored at ${targetPath}.`,
          );
          continue;
        }
        if (!isSha256(target.sha256)) {
          addCheck(
            checks,
            `family-source:${family.bodyFamily}:${target.id}`,
            "fail",
            `Required original target ${target.id} exists but has no pinned SHA-256.`,
          );
          continue;
        }
        const actual = createHash("sha256").update(readFileSync(targetPath)).digest("hex");
        addCheck(
          checks,
          `family-source:${family.bodyFamily}:${target.id}`,
          actual === target.sha256.toLowerCase() ? "pass" : "fail",
          actual === target.sha256.toLowerCase()
            ? `Original target ${target.id} matches its pinned SHA-256.`
            : `Original target ${target.id} has changed since its SHA-256 was pinned.`,
          { targetPath, expectedSha256: target.sha256, actualSha256: actual },
        );
      }
    }
  }
}

function readGitRevision(repositoryPath) {
  const gitPath = path.join(repositoryPath, ".git");
  if (!existsSync(gitPath)) return null;
  let gitDir = gitPath;
  if (statSync(gitPath).isFile()) {
    const line = readFileSync(gitPath, "utf8").trim();
    const relative = line.match(/^gitdir:\s*(.+)$/i)?.[1];
    if (!relative) return null;
    gitDir = path.resolve(repositoryPath, relative);
  }
  const headPath = path.join(gitDir, "HEAD");
  if (!existsSync(headPath)) return null;
  const head = readFileSync(headPath, "utf8").trim();
  const ref = head.match(/^ref:\s*(.+)$/)?.[1];
  if (!ref) return /^[a-f0-9]{40}$/i.test(head) ? head.toLowerCase() : null;
  const refPath = path.join(gitDir, ...ref.split("/"));
  if (existsSync(refPath)) return readFileSync(refPath, "utf8").trim().toLowerCase();
  const packedRefs = path.join(gitDir, "packed-refs");
  if (!existsSync(packedRefs)) return null;
  return readFileSync(packedRefs, "utf8")
    .split(/\r?\n/)
    .map((line) => line.trim().split(" "))
    .find((parts) => parts[1] === ref)?.[0]
    ?.toLowerCase() ?? null;
}

async function checkStableFast3d(options, toolchain, checks) {
  const repositoryPath = options.sf3dPath ?? process.env.STABLE_FAST_3D_PATH;
  if (!repositoryPath) {
    addCheck(
      checks,
      "optional:stable-fast-3d",
      "skip",
      "Stable Fast 3D CPU handoff is optional and is not configured.",
      { enabledByDefault: toolchain?.stableFast3dHandoff?.enabledByDefault ?? false },
    );
    return;
  }
  const resolved = path.resolve(repositoryPath);
  const requiredFiles = ["run.py", "sf3d", "LICENSE.md"];
  const missing = requiredFiles.filter((relative) => !existsSync(path.join(resolved, relative)));
  const revision = readGitRevision(resolved);
  const revisionValid = /^[a-f0-9]{40}$/i.test(revision ?? "");
  addCheck(
    checks,
    "optional:stable-fast-3d:repository",
    missing.length === 0 && revisionValid ? "pass" : "fail",
    missing.length === 0 && revisionValid
      ? `Stable Fast 3D local repository is pinned at ${revision}.`
      : "Stable Fast 3D path is missing required files or a readable Git revision.",
    { repositoryPath: resolved, revision, missing },
  );

  const checkpointPath = options.sf3dCheckpoint ?? process.env.STABLE_FAST_3D_CHECKPOINT;
  const expected = (
    options.sf3dCheckpointSha256 ?? process.env.STABLE_FAST_3D_CHECKPOINT_SHA256 ?? ""
  ).toLowerCase();
  if (!checkpointPath || !existsSync(checkpointPath)) {
    addCheck(
      checks,
      "optional:stable-fast-3d:checkpoint",
      "fail",
      "Stable Fast 3D was requested but no local checkpoint path was supplied.",
    );
    return;
  }
  const actual = await sha256File(path.resolve(checkpointPath));
  const matches = isSha256(expected) && expected === actual;
  addCheck(
    checks,
    "optional:stable-fast-3d:checkpoint",
    matches ? "pass" : "fail",
    matches
      ? "Stable Fast 3D local checkpoint matches its supplied SHA-256."
      : "Stable Fast 3D checkpoint needs a matching STABLE_FAST_3D_CHECKPOINT_SHA256 before handoff.",
    { checkpointPath: path.resolve(checkpointPath), expectedSha256: expected || null, actualSha256: actual },
  );
}

export async function runDoctor(options = {}) {
  const definitions = validateDefinitions();
  const checks = [...definitions.checks];
  const paths = { pipelineRoot: PIPELINE_ROOT, bodyFamilyDir: BODY_FAMILY_DIR };

  if (!options.definitionsOnly) {
    checkFamilySources(definitions.families, checks);

    const blender = discoverBlender(options);
    paths.blender = blender.path;
    const minimumBlender = definitions.toolchain?.dependencies?.blender?.minimumVersion ?? "4.2.0";
    const blenderReady = blender.version && compareVersions(blender.version, minimumBlender) >= 0;
    addCheck(
      checks,
      "tool:blender",
      blenderReady ? "pass" : "fail",
      blenderReady
        ? `Blender ${blender.version} satisfies the minimum ${minimumBlender}.`
        : `Blender ${minimumBlender}+ was not found or is too old.`,
      blenderReady ? { path: blender.path } : { attempted: blender.attempted },
    );

    const mpfb = discoverMpfb(options, blender.version);
    paths.mpfb = mpfb.path;
    const requiredMpfb = definitions.toolchain?.dependencies?.mpfb?.requiredVersion ?? "2.0.16";
    const mpfbReady = mpfb.version === requiredMpfb;
    addCheck(
      checks,
      "tool:mpfb",
      mpfbReady ? "pass" : "fail",
      mpfbReady
        ? `MPFB ${mpfb.version} is installed at the pinned version.`
        : `MPFB ${requiredMpfb} was not found at a supported extension path.`,
      mpfbReady
        ? { path: mpfb.path, manifestPath: mpfb.manifestPath }
        : { detectedVersion: mpfb.version, attempted: mpfb.attempted },
    );

    const assetRoot = discoverAssetRoot(options, blender.version, mpfb.path);
    paths.mpfbAssetRoot = assetRoot.path;
    addCheck(
      checks,
      "tool:mpfb-asset-root",
      assetRoot.path ? "pass" : "fail",
      assetRoot.path
        ? `MPFB user asset data was found at ${assetRoot.path}.`
        : "MPFB user asset data with a packs directory was not found.",
      assetRoot.path ? undefined : { attempted: assetRoot.attempted },
    );
    if (assetRoot.path && definitions.toolchain) {
      await checkAssetPacks(definitions.toolchain, assetRoot.path, options, checks);
    }

    await checkStableFast3d(options, definitions.toolchain, checks);
  }

  const failed = checks.filter((check) => check.status === "fail").length;
  const warnings = checks.filter((check) => check.status === "warn").length;
  const passed = checks.filter((check) => check.status === "pass").length;
  const skipped = checks.filter((check) => check.status === "skip").length;
  const ready = failed === 0 && (!options.strict || warnings === 0);
  return {
    schemaVersion: 1,
    tool: "war-js-model-doctor",
    mode: options.definitionsOnly ? "definitions-only" : "full",
    strict: Boolean(options.strict),
    ready,
    summary: { passed, warnings, failed, skipped },
    paths,
    checks,
  };
}

export function formatDoctorReport(report) {
  const labels = { pass: "PASS", warn: "WARN", fail: "FAIL", skip: "SKIP" };
  const lines = ["War-js Free Character Model Doctor", ""];
  for (const check of report.checks) {
    lines.push(`[${labels[check.status]}] ${check.message}`);
  }
  lines.push(
    "",
    `Result: ${report.ready ? "READY" : "NOT READY"} (${report.summary.passed} passed, ${report.summary.warnings} warnings, ${report.summary.failed} failed, ${report.summary.skipped} skipped)`,
  );
  if (report.strict && report.summary.warnings > 0) {
    lines.push("Strict mode treats warnings as not ready.");
  }
  return lines.join("\n");
}

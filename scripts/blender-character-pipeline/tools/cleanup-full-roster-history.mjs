#!/usr/bin/env node
import { existsSync, unlinkSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  ASSET_INDEX_PATH,
  REPO_ROOT,
  assertPathWithin,
  readJson,
  repoRelative,
  writeJsonAtomic,
} from "./workspace-paths.mjs";

const MANIFEST_PATH = path.join(REPO_ROOT, "scripts", "blender-character-pipeline", "data", "full-roster-cleanup.json");
const ALLOWLIST_PATH = path.join(REPO_ROOT, "scripts", "blender-character-pipeline", "data", "runtime-compatibility-allowlist.json");

export function cleanupPlan() {
  const manifest = readJson(MANIFEST_PATH);
  const files = manifest.files.map((relativePath) => {
    const absolute = assertPathWithin(REPO_ROOT, path.join(REPO_ROOT, relativePath), "historical cleanup target");
    return { relativePath: repoRelative(absolute), absolute, exists: existsSync(absolute) };
  });
  const index = readJson(ASSET_INDEX_PATH);
  const allowlist = readJson(ALLOWLIST_PATH);
  return {
    cleanupId: manifest.cleanupId,
    preserve: manifest.preserve,
    files,
    registryKeys: manifest.registryKeys.filter((key) => Boolean(index.staticProps?.[key])),
    allowlistModels: manifest.allowlistModels.filter((model) => allowlist.assets.some((entry) => entry.model === model)),
  };
}

export function applyCleanup() {
  const manifest = readJson(MANIFEST_PATH);
  const plan = cleanupPlan();
  const index = readJson(ASSET_INDEX_PATH);
  const allowlist = readJson(ALLOWLIST_PATH);
  for (const file of plan.files) {
    if (file.exists) unlinkSync(file.absolute);
  }
  for (const key of manifest.registryKeys) delete index.staticProps?.[key];
  index.assetVersion = "authoring-roster-review-pending";
  allowlist.assets = allowlist.assets.filter((entry) => !manifest.allowlistModels.includes(entry.model));
  writeJsonAtomic(ASSET_INDEX_PATH, index);
  writeJsonAtomic(ALLOWLIST_PATH, allowlist);
  const after = cleanupPlan();
  if (after.files.some((file) => file.exists) || after.registryKeys.length || after.allowlistModels.length) {
    throw new Error("Historical full-roster cleanup did not converge.");
  }
  return { ...after, removedFileCount: plan.files.filter((file) => file.exists).length };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1])) {
  const apply = process.argv.includes("--apply");
  const report = apply ? applyCleanup() : cleanupPlan();
  console.log(JSON.stringify({ mode: apply ? "apply" : "dry-run", ...report }, null, 2));
}

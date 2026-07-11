import {
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  realpathSync,
  renameSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const TOOL_DIR = path.dirname(fileURLToPath(import.meta.url));
export const PIPELINE_ROOT = path.resolve(TOOL_DIR, "..");
export const REPO_ROOT = path.resolve(PIPELINE_ROOT, "..", "..");
export const BLUEPRINT_DIR = path.join(PIPELINE_ROOT, "data", "asset-blueprints");
export const BODY_FAMILY_DIR = path.join(PIPELINE_ROOT, "data", "body-families");
export const APPROVED_ASSET_DIR = path.join(PIPELINE_ROOT, "data", "approved-assets");
export const MODEL_DIR = path.join(REPO_ROOT, "public", "assets", "models");
export const ASSET_INDEX_PATH = path.join(MODEL_DIR, "asset-index.json");
export const JOB_ROOT = path.join(REPO_ROOT, "artifacts", "model-jobs");

function normalizedForComparison(value) {
  const normalized = path.resolve(value).replace(/[\\/]+$/, "");
  return process.platform === "win32" ? normalized.toLowerCase() : normalized;
}

function nearestExistingParent(value) {
  let current = path.resolve(value);
  while (!existsSync(current)) {
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
  return current;
}

/**
 * Rejects traversal and symlink escapes before a path is read or written.
 * Returned paths are absolute but are not created by this function.
 */
export function assertPathWithin(root, candidate, label = "path") {
  if (typeof candidate !== "string" || candidate.length === 0 || candidate.includes("\0")) {
    throw workflowError("INVALID_PATH", `${label} must be a non-empty filesystem path.`);
  }

  const absoluteRoot = path.resolve(root);
  const absoluteCandidate = path.resolve(candidate);
  const relative = path.relative(absoluteRoot, absoluteCandidate);
  if (relative === ".." || relative.startsWith(`..${path.sep}`) || path.isAbsolute(relative)) {
    throw workflowError("PATH_OUTSIDE_WORKSPACE", `${label} must remain inside ${absoluteRoot}.`, {
      path: absoluteCandidate,
    });
  }

  const existingRoot = nearestExistingParent(absoluteRoot);
  const existingCandidate = nearestExistingParent(absoluteCandidate);
  if (existingRoot && existingCandidate) {
    const realRoot = normalizedForComparison(realpathSync.native(existingRoot));
    const realCandidate = normalizedForComparison(realpathSync.native(existingCandidate));
    const realRelative = path.relative(realRoot, realCandidate);
    if (realRelative === ".." || realRelative.startsWith(`..${path.sep}`) || path.isAbsolute(realRelative)) {
      throw workflowError("PATH_SYMLINK_ESCAPE", `${label} resolves outside the workspace.`, {
        path: absoluteCandidate,
      });
    }
  }

  return absoluteCandidate;
}

export function resolveRepoPath(value, label = "path") {
  const resolved = path.isAbsolute(value) ? value : path.join(REPO_ROOT, value);
  return assertPathWithin(REPO_ROOT, resolved, label);
}

export function repoRelative(value) {
  const absolute = assertPathWithin(REPO_ROOT, value);
  return path.relative(REPO_ROOT, absolute).split(path.sep).join("/");
}

export function readJson(filePath) {
  return JSON.parse(readFileSync(filePath, "utf8"));
}

/** Write a small state file with same-directory rename semantics. */
export function writeJsonAtomic(filePath, value) {
  const safePath = assertPathWithin(REPO_ROOT, filePath, "JSON output");
  mkdirSync(path.dirname(safePath), { recursive: true });
  const temporary = `${safePath}.${process.pid}.${Date.now()}.tmp`;
  let descriptor;
  try {
    descriptor = openSync(temporary, "wx");
    writeFileSync(descriptor, `${JSON.stringify(value, null, 2)}\n`, "utf8");
    closeSync(descriptor);
    descriptor = undefined;
    renameSync(temporary, safePath);
  } catch (error) {
    if (descriptor !== undefined) closeSync(descriptor);
    throw error;
  }
}

export function workflowError(code, message, details = undefined, retryable = false) {
  const error = new Error(message);
  error.code = code;
  error.details = details;
  error.retryable = retryable;
  return error;
}

export function structuredError(error) {
  if (error?.name === "AbortError" || error?.code === "ABORT_ERR") {
    return {
      code: "JOB_CANCELLED",
      message: "The model job was cancelled.",
      retryable: true,
    };
  }
  return {
    code: typeof error?.code === "string" ? error.code : "MODEL_PIPELINE_ERROR",
    message: error instanceof Error ? error.message : String(error),
    ...(error?.details === undefined ? {} : { details: error.details }),
    retryable: error?.retryable === true,
  };
}

import { randomBytes } from "node:crypto";
import { createReadStream, existsSync, statSync } from "node:fs";
import path from "node:path";
import {
  REPO_ROOT,
  assertPathWithin,
  readJson,
  structuredError,
} from "./workspace-paths.mjs";
import {
  buildReviewCatalog,
  recordRosterReview,
  revisionManifestPath,
} from "./roster-runs.mjs";
import {
  getRosterGenerationJob,
  startRosterGeneration,
} from "./roster-generation.mjs";
import { sha256File } from "./pipeline-lib.mjs";

const MAX_REQUEST_BYTES = 64 * 1024;
const CONTENT_TYPES = {
  ".glb": "model/gltf-binary",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
};

function json(res, status, value) {
  res.statusCode = status;
  res.setHeader("Content-Type", "application/json; charset=utf-8");
  res.setHeader("Cache-Control", "no-store");
  res.end(JSON.stringify(value));
}

export function reviewMutationAuthorized(req, token) {
  if (req.headers["x-war-review-token"] !== token) return false;
  const origin = req.headers.origin;
  const host = req.headers.host;
  if (typeof origin !== "string" || typeof host !== "string") return false;
  try {
    const parsed = new URL(origin);
    return ["http:", "https:"].includes(parsed.protocol) && parsed.host === host;
  } catch {
    return false;
  }
}

async function readBody(req) {
  if (!String(req.headers["content-type"] ?? "").toLowerCase().startsWith("application/json")) {
    throw Object.assign(new Error("Review mutations require application/json."), { code: "INVALID_CONTENT_TYPE" });
  }
  const chunks = [];
  let size = 0;
  for await (const chunk of req) {
    size += chunk.length;
    if (size > MAX_REQUEST_BYTES) throw Object.assign(new Error("Review request exceeds 64 KiB."), { code: "REQUEST_TOO_LARGE" });
    chunks.push(chunk);
  }
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function query(req) {
  return new URL(req.url ?? "/", "http://localhost").searchParams;
}

function streamArtifact(req, res) {
  const params = query(req);
  const runId = params.get("runId") ?? "";
  const kind = params.get("kind") ?? "";
  const key = params.get("key") ?? "";
  const revision = Number(params.get("revision"));
  const artifactIndex = Number(params.get("artifact"));
  if (!Number.isInteger(artifactIndex) || artifactIndex < 0) throw Object.assign(new Error("Invalid artifact index."), { code: "INVALID_ARTIFACT" });
  const manifestPath = revisionManifestPath(runId, kind, key, revision);
  if (!existsSync(manifestPath)) throw Object.assign(new Error("Roster revision not found."), { code: "ROSTER_REVISION_NOT_FOUND" });
  const manifest = readJson(manifestPath);
  const artifact = manifest.artifacts?.[artifactIndex];
  if (!artifact) throw Object.assign(new Error("Artifact is not part of the selected revision."), { code: "INVALID_ARTIFACT" });
  const target = assertPathWithin(REPO_ROOT, path.resolve(REPO_ROOT, artifact.path), "roster review artifact");
  if (!existsSync(target)) throw Object.assign(new Error("Review artifact is missing."), { code: "MODEL_STAGE_ARTIFACT_MISSING" });
  if (sha256File(target) !== artifact.sha256) throw Object.assign(new Error("Review artifact hash is stale."), { code: "MODEL_STAGE_HASH_MISMATCH" });
  const extension = path.extname(target).toLowerCase();
  if (!Object.hasOwn(CONTENT_TYPES, extension)) throw Object.assign(new Error("Artifact type is not review-streamable."), { code: "INVALID_ARTIFACT_TYPE" });
  res.statusCode = 200;
  res.setHeader("Content-Type", CONTENT_TYPES[extension]);
  res.setHeader("Content-Length", String(statSync(target).size));
  res.setHeader("Cache-Control", "no-store");
  res.setHeader("X-War-Model-Sha256", artifact.sha256);
  const stream = createReadStream(target);
  stream.on("error", () => res.destroy());
  res.on("close", () => stream.destroy());
  stream.pipe(res);
}

export function localRosterReviewPlugin() {
  const reviewToken = randomBytes(32).toString("hex");
  return {
    name: "war-js-local-roster-review",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use("/__model-review/catalog", (req, res) => {
        try {
          if (req.method !== "GET") return json(res, 405, { error: "Method not allowed." });
          const catalog = buildReviewCatalog({ runId: query(req).get("runId") ?? undefined });
          return json(res, 200, { ...catalog, reviewToken });
        } catch (error) {
          return json(res, 400, { error: structuredError(error) });
        }
      });
      server.middlewares.use("/__model-review/artifact", (req, res) => {
        try {
          if (req.method !== "GET") return json(res, 405, { error: "Method not allowed." });
          return streamArtifact(req, res);
        } catch (error) {
          const structured = structuredError(error);
          return json(res, structured.code === "ROSTER_REVISION_NOT_FOUND" ? 404 : 409, { error: structured });
        }
      });
      server.middlewares.use("/__model-review/review", async (req, res) => {
        try {
          if (req.method !== "POST") return json(res, 405, { error: "Method not allowed." });
          if (!reviewMutationAuthorized(req, reviewToken)) return json(res, 403, { error: "Invalid local review origin or token." });
          const input = await readBody(req);
          return json(res, 200, recordRosterReview(input));
        } catch (error) {
          return json(res, 400, { error: structuredError(error) });
        }
      });
      server.middlewares.use("/__model-review/regenerate", async (req, res) => {
        try {
          if (req.method !== "POST") return json(res, 405, { error: "Method not allowed." });
          if (!reviewMutationAuthorized(req, reviewToken)) return json(res, 403, { error: "Invalid local review origin or token." });
          const input = await readBody(req);
          const job = startRosterGeneration({ ...input, revision: "next" });
          return json(res, 202, job);
        } catch (error) {
          return json(res, 400, { error: structuredError(error) });
        }
      });
      server.middlewares.use("/__model-review/job", (req, res) => {
        try {
          if (req.method !== "GET") return json(res, 405, { error: "Method not allowed." });
          return json(res, 200, getRosterGenerationJob(query(req).get("jobId") ?? ""));
        } catch (error) {
          return json(res, 404, { error: structuredError(error) });
        }
      });
    },
  };
}

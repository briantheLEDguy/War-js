import {
  closeSync,
  existsSync,
  mkdirSync,
  openSync,
  readFileSync,
  rmSync,
  statSync,
  unlinkSync,
  writeFileSync,
} from "node:fs";
import path from "node:path";
import { randomUUID, createHash } from "node:crypto";
import {
  JOB_ROOT,
  REPO_ROOT,
  assertPathWithin,
  repoRelative,
  structuredError,
  workflowError,
  writeJsonAtomic,
} from "./workspace-paths.mjs";

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);
const JOB_ID_PATTERN = /^job_[0-9]{8}t[0-9]{6}z_[a-f0-9]{12}$/;
const activeControllers = new Map();
const activePromises = new Map();

function timestampId() {
  const stamp = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "").toLowerCase();
  return `job_${stamp}_${randomUUID().replace(/-/g, "").slice(0, 12)}`;
}

function lockFileName(assetKey) {
  const readable = String(assetKey).toLowerCase().replace(/[^a-z0-9_.-]+/g, "_").slice(0, 64) || "asset";
  const suffix = createHash("sha256").update(String(assetKey)).digest("hex").slice(0, 12);
  return `${readable}.${suffix}.lock`;
}

function processIsRunning(pid) {
  if (!Number.isInteger(pid) || pid <= 0) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    return error?.code === "EPERM";
  }
}

function publicJob(record) {
  return {
    jobId: record.jobId,
    kind: record.kind,
    status: record.status,
    progress: record.progress,
    message: record.message,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
    startedAt: record.startedAt ?? null,
    finishedAt: record.finishedAt ?? null,
    cancelRequested: record.cancelRequested === true,
    artifacts: record.artifacts ?? [],
    result: record.result ?? null,
    error: record.error ?? null,
  };
}

export class ModelJobStore {
  constructor(root = JOB_ROOT) {
    this.root = assertPathWithin(REPO_ROOT, path.resolve(root), "model job root");
    this.lockRoot = path.join(this.root, ".locks");
  }

  ensureRoot() {
    mkdirSync(this.root, { recursive: true });
    mkdirSync(this.lockRoot, { recursive: true });
  }

  jobDir(jobId) {
    if (!JOB_ID_PATTERN.test(jobId)) {
      throw workflowError("INVALID_JOB_ID", `Invalid model job ID: ${jobId}`);
    }
    return assertPathWithin(this.root, path.join(this.root, jobId), "model job directory");
  }

  statePath(jobId) {
    return path.join(this.jobDir(jobId), "job.json");
  }

  create(kind, input = {}, assetKeys = []) {
    this.ensureRoot();
    const jobId = timestampId();
    const jobDir = this.jobDir(jobId);
    mkdirSync(path.join(jobDir, "artifacts"), { recursive: true });
    mkdirSync(path.join(jobDir, "staging"), { recursive: true });
    const now = new Date().toISOString();
    const record = {
      schemaVersion: 1,
      jobId,
      kind,
      status: "queued",
      progress: 0,
      message: "Queued",
      input,
      assetKeys: [...new Set(assetKeys.map(String))].sort(),
      cancelRequested: false,
      ownerPid: process.pid,
      createdAt: now,
      updatedAt: now,
      artifacts: [],
      result: null,
      error: null,
    };
    writeJsonAtomic(this.statePath(jobId), record);
    return publicJob(record);
  }

  read(jobId) {
    const statePath = this.statePath(jobId);
    if (!existsSync(statePath)) {
      throw workflowError("JOB_NOT_FOUND", `Unknown model job: ${jobId}`);
    }
    return JSON.parse(readFileSync(statePath, "utf8"));
  }

  update(jobId, patch) {
    const current = this.read(jobId);
    const next = {
      ...current,
      ...patch,
      updatedAt: new Date().toISOString(),
    };
    writeJsonAtomic(this.statePath(jobId), next);
    return next;
  }

  get(jobId) {
    const record = this.read(jobId);
    if (record.status === "running" && record.ownerPid !== process.pid && !processIsRunning(record.ownerPid)) {
      const interrupted = this.update(jobId, {
        status: "failed",
        finishedAt: new Date().toISOString(),
        message: "Interrupted when the owning process stopped",
        error: {
          code: "JOB_PROCESS_INTERRUPTED",
          message: "The process running this job is no longer active.",
          retryable: true,
        },
      });
      return publicJob(interrupted);
    }
    return publicJob(record);
  }

  async acquireLocks(jobId, assetKeys) {
    this.ensureRoot();
    const releases = [];
    try {
      for (const assetKey of [...new Set(assetKeys.map(String))].sort()) {
        const lockPath = assertPathWithin(this.lockRoot, path.join(this.lockRoot, lockFileName(assetKey)), "asset lock");
        let descriptor;
        try {
          descriptor = openSync(lockPath, "wx");
        } catch (error) {
          if (error?.code !== "EEXIST") throw error;
          let owner = null;
          try {
            owner = JSON.parse(readFileSync(lockPath, "utf8"));
          } catch {
            // A malformed lock is never silently broken while it is fresh.
          }
          const ageMs = Date.now() - statSync(lockPath).mtimeMs;
          const provenDeadOwner = owner?.jobId && Number.isInteger(owner?.pid)
            && !processIsRunning(owner.pid);
          const staleMalformedLock = !owner?.jobId && ageMs > 12 * 60 * 60 * 1000;
          if (provenDeadOwner || staleMalformedLock) {
            unlinkSync(lockPath);
            descriptor = openSync(lockPath, "wx");
          } else {
            throw workflowError(
              "ASSET_LOCKED",
              `Asset ${assetKey} is already being changed by ${owner?.jobId ?? "another job"}.`,
              { assetKey, ownerJobId: owner?.jobId ?? null },
              true,
            );
          }
        }
        writeFileSync(descriptor, JSON.stringify({ jobId, assetKey, pid: process.pid, createdAt: new Date().toISOString() }));
        closeSync(descriptor);
        releases.push(() => {
          if (!existsSync(lockPath)) return;
          try {
            const owner = JSON.parse(readFileSync(lockPath, "utf8"));
            if (owner.jobId === jobId) unlinkSync(lockPath);
          } catch {
            // Do not remove a lock whose ownership cannot be proven.
          }
        });
      }
      return () => releases.reverse().forEach((release) => release());
    } catch (error) {
      releases.reverse().forEach((release) => release());
      throw error;
    }
  }

  start(kind, input, handler, options = {}) {
    const job = this.create(kind, input, options.assetKeys ?? []);
    const controller = new AbortController();
    activeControllers.set(job.jobId, controller);
    const promise = this.#run(job.jobId, handler, controller.signal);
    activePromises.set(job.jobId, promise);
    promise.finally(() => {
      activeControllers.delete(job.jobId);
      activePromises.delete(job.jobId);
    });
    return job;
  }

  async wait(jobId) {
    const active = activePromises.get(jobId);
    if (active) await active;
    return this.get(jobId);
  }

  cancel(jobId) {
    const current = this.read(jobId);
    if (TERMINAL_STATUSES.has(current.status)) return publicJob(current);
    const next = this.update(jobId, {
      cancelRequested: true,
      message: current.status === "queued" ? "Cancellation requested before start" : "Cancellation requested",
    });
    activeControllers.get(jobId)?.abort();
    return publicJob(next);
  }

  async #run(jobId, handler, signal) {
    const initial = this.read(jobId);
    let releaseLocks = () => {};
    try {
      if (initial.cancelRequested || signal.aborted) {
        throw workflowError("JOB_CANCELLED", "The model job was cancelled before it started.", undefined, true);
      }
      releaseLocks = await this.acquireLocks(jobId, initial.assetKeys ?? []);
      this.update(jobId, {
        status: "running",
        progress: 1,
        message: "Started",
        startedAt: new Date().toISOString(),
        ownerPid: process.pid,
      });
      const jobDir = this.jobDir(jobId);
      const context = {
        jobId,
        jobDir,
        artifactDir: path.join(jobDir, "artifacts"),
        stagingDir: path.join(jobDir, "staging"),
        signal,
        input: initial.input,
        checkCancelled: () => {
          if (signal.aborted || this.read(jobId).cancelRequested) {
            throw workflowError("JOB_CANCELLED", "The model job was cancelled.", undefined, true);
          }
        },
        update: (progress, message, extra = {}) => this.update(jobId, {
          progress: Math.max(0, Math.min(99, Math.round(progress))),
          message,
          ...extra,
        }),
        addArtifact: (filePath, kind = "file") => {
          const safePath = assertPathWithin(jobDir, filePath, "job artifact");
          const current = this.read(jobId);
          const artifact = { kind, path: repoRelative(safePath) };
          const artifacts = [...(current.artifacts ?? []).filter((entry) => entry.path !== artifact.path), artifact];
          this.update(jobId, { artifacts });
          return artifact;
        },
      };
      const result = await handler(context);
      context.checkCancelled();
      const complete = this.update(jobId, {
        status: "completed",
        progress: 100,
        message: "Completed",
        finishedAt: new Date().toISOString(),
        result: result ?? {},
        error: null,
      });
      return publicJob(complete);
    } catch (error) {
      const structured = structuredError(error);
      const status = structured.code === "JOB_CANCELLED" ? "cancelled" : "failed";
      const failed = this.update(jobId, {
        status,
        message: structured.message,
        finishedAt: new Date().toISOString(),
        error: structured,
      });
      return publicJob(failed);
    } finally {
      releaseLocks();
    }
  }

  removeForTest(jobId) {
    const target = this.jobDir(jobId);
    assertPathWithin(this.root, target, "test job cleanup");
    if (existsSync(target)) rmSync(target, { recursive: true, force: true });
  }
}

export const modelJobStore = new ModelJobStore();

export function startModelJob(kind, input, handler, options) {
  return modelJobStore.start(kind, input, handler, options);
}

export function getModelJob(jobId) {
  return modelJobStore.get(jobId);
}

export function cancelModelJob(jobId) {
  return modelJobStore.cancel(jobId);
}

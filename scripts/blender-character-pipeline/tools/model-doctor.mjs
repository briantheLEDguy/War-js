#!/usr/bin/env node

import { formatDoctorReport, runDoctor } from "./model-doctor-lib.mjs";

const HELP = `War-js free character model doctor

Usage:
  node scripts/blender-character-pipeline/tools/model-doctor.mjs [options]

Options:
  --definitions-only          Validate checked-in pilot definitions without local tools
  --strict                    Treat unverifiable retained-archive checks as not ready
  --json                      Emit a machine-readable JSON report
  --blender <path>            Blender executable (or set BLENDER_PATH)
  --mpfb <path>               MPFB extension root (or set MPFB_PATH)
  --assets <path>             MPFB user data/data root (or set MPFB_ASSET_ROOT)
  --pack-archives <path>      Directory containing original asset-pack ZIPs
  --checksum-lock <path>      Optional JSON map of pack IDs to SHA-256 digests
  --sf3d <path>               Optional local Stable Fast 3D repository
  --sf3d-checkpoint <path>    Optional local Stable Fast 3D checkpoint
  --sf3d-checkpoint-sha <hex> SHA-256 for the optional checkpoint
  --help                      Show this help

This command performs no downloads, installs, network requests, or model generation.`;

function parseArgs(argv) {
  const options = {};
  const valueOptions = new Map([
    ["--blender", "blenderPath"],
    ["--mpfb", "mpfbPath"],
    ["--assets", "assetRoot"],
    ["--pack-archives", "packArchiveRoot"],
    ["--checksum-lock", "checksumLock"],
    ["--sf3d", "sf3dPath"],
    ["--sf3d-checkpoint", "sf3dCheckpoint"],
    ["--sf3d-checkpoint-sha", "sf3dCheckpointSha256"],
  ]);

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help" || arg === "-h") return { help: true };
    if (arg === "--json") {
      options.json = true;
      continue;
    }
    if (arg === "--strict") {
      options.strict = true;
      continue;
    }
    if (arg === "--definitions-only") {
      options.definitionsOnly = true;
      continue;
    }
    const key = valueOptions.get(arg);
    if (!key) throw new Error(`Unknown option: ${arg}`);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`Missing value for ${arg}`);
    options[key] = value;
    index += 1;
  }
  return options;
}

let options;
try {
  options = parseArgs(process.argv.slice(2));
} catch (error) {
  console.error(error.message);
  console.error("Run with --help for usage.");
  process.exitCode = 2;
}

if (options?.help) {
  console.log(HELP);
} else if (options) {
  const report = await runDoctor(options);
  console.log(options.json ? JSON.stringify(report, null, 2) : formatDoctorReport(report));
  process.exitCode = report.ready ? 0 : 1;
}

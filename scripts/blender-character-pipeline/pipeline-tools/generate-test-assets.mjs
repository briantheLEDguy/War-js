#!/usr/bin/env node

import { existsSync, mkdirSync } from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { PIPELINE_ROOT, readJson, repoRelative } from "../tools/workspace-paths.mjs";
import { readConfig } from "../tools/pipeline-lib.mjs";

const asset = process.argv[2] ?? "all";
if (!["all", "body", "rigid", "skinned"].includes(asset)) {
  console.error("Usage: node scripts/blender-character-pipeline/pipeline-tools/generate-test-assets.mjs [all|body|rigid|skinned]");
  process.exit(2);
}

const config = readConfig();
const blender = config.blenderPath ?? "blender";
const script = path.join(PIPELINE_ROOT, "pipeline-tools", "generate_pipeline_test_assets.py");
const outputDir = path.join(PIPELINE_ROOT, "test-assets");
mkdirSync(outputDir, { recursive: true });
if (path.isAbsolute(blender) && !existsSync(blender)) {
  console.error(`Blender was not found at ${blender}. Set BLENDER_PATH or update config.json.`);
  process.exit(1);
}
const result = spawnSync(blender, ["--background", "--python", script, "--", "--output-dir", outputDir, "--asset", asset], {
  cwd: PIPELINE_ROOT,
  encoding: "utf8",
  windowsHide: true,
  maxBuffer: 32 * 1024 * 1024,
});
if (result.stdout) process.stdout.write(result.stdout);
if (result.stderr) process.stderr.write(result.stderr);
if (result.status !== 0) {
  console.error(`Fixture generation failed with exit code ${result.status}.`);
  process.exit(result.status ?? 1);
}
if (!existsSync(path.join(outputDir, "fixture-index.json"))) {
  console.error("Fixture generation did not produce fixture-index.json; Blender may have reported a Python error.");
  process.exit(1);
}
console.log(`Generated review-only character fixtures under ${repoRelative(outputDir)}.`);

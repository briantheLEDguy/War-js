import { validateBlueprints } from "./pipeline-lib.mjs";

const args = new Set(process.argv.slice(2));
const strict = args.has("--strict");
const json = args.has("--json");
const refs = process.argv.slice(2)
  .filter((arg) => arg.startsWith("--ref="))
  .map((arg) => arg.slice("--ref=".length));
const results = validateBlueprints({ strict, refs: refs.length ? refs : undefined });
const failed = results.filter((result) => !result.ok);

if (json) {
  process.stdout.write(`${JSON.stringify({ strict, ok: failed.length === 0, results }, null, 2)}\n`);
} else {
  for (const result of failed) {
    console.error(`FAIL ${result.assetId}`);
    for (const error of result.errors) console.error(`  - ${error}`);
  }
  if (failed.length > 0) console.error(`\n${failed.length} validation record(s) failed${strict ? " in strict mode" : ""}.`);
  else console.log(`OK: ${results.length} manifest, asset-index, and generated-QC validation records passed${strict ? " in strict mode" : ""}.`);
}

if (failed.length > 0) process.exitCode = 1;

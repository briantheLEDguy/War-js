import { validateBlueprints } from "./pipeline-lib.mjs";

const results = validateBlueprints();
const failed = results.filter((result) => !result.ok);

for (const result of results) {
  if (result.ok) continue;
  console.error(`FAIL ${result.assetId}`);
  for (const error of result.errors) console.error(`  - ${error}`);
}

if (failed.length > 0) {
  console.error(`\n${failed.length} validation record(s) failed.`);
  process.exit(1);
}

console.log(`OK: ${results.length} manifest, asset-index, and generated-QC validation records passed.`);

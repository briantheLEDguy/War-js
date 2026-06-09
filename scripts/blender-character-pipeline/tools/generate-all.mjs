import { loadBlueprints, runBlenderForBlueprint } from "./pipeline-lib.mjs";

const setName = process.argv[2] ?? "smoke";
const refs = loadBlueprints()
  .filter(({ blueprint }) => (blueprint.sets ?? []).includes(setName))
  .map(({ blueprint }) => blueprint.assetId);

if (refs.length === 0) {
  console.error(`No blueprints found for set "${setName}".`);
  process.exit(1);
}

let failed = false;
for (const ref of refs) {
  try {
    const result = await runBlenderForBlueprint(ref);
    console.log(`OK ${result.blueprint.assetId} -> ${result.outPath}`);
  } catch (err) {
    failed = true;
    console.error(`FAIL ${ref}`);
    console.error(err.message);
  }
}

if (failed) process.exit(1);

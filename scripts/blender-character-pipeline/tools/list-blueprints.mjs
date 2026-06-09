import { loadBlueprints, listGeneratedAssets } from "./pipeline-lib.mjs";

const generated = new Map(listGeneratedAssets().map((asset) => [asset.assetId, asset]));
const rows = loadBlueprints().map(({ blueprint }) => {
  const asset = generated.get(blueprint.assetId);
  const status = asset?.generated ? "OK" : "MISSING";
  const qc = asset?.qcPassed === true ? "QC_PASS" : asset?.qc ? "QC_FAIL" : "NO_QC";
  return `${status.padEnd(7)} ${qc.padEnd(7)} ${blueprint.category.padEnd(9)} ${blueprint.assetId.padEnd(42)} ${blueprint.output.model}`;
});

console.log(`Asset blueprints (${rows.length})`);
console.log(rows.join("\n"));

import { runBlenderForBlueprint } from "./pipeline-lib.mjs";

const ref = process.argv[2];
if (!ref) {
  console.error("Usage: npm run models:generate -- <assetId|profileKey|itemKey|manifest filename>");
  process.exit(1);
}

try {
  const result = await runBlenderForBlueprint(ref);
  console.log(`OK: generated ${result.blueprint.assetId}`);
  console.log(`path=${result.outPath}`);
  const lines = result.stdout
    .split(/\r?\n/)
    .filter((line) => line.startsWith("[asset-pipeline]") || line.startsWith("[WAR]"));
  if (lines.length > 0) console.log(lines.join("\n"));
  if (result.stderr.trim()) console.error(result.stderr.trim());
} catch (err) {
  console.error(err.message);
  process.exit(1);
}

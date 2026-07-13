import { ASSET_INDEX_PATH, repoRelative } from "./pipeline-lib.mjs";
import { compileRuntimeRegistry, writeRuntimeRegistry } from "./runtime-registry.mjs";

const checkOnly = process.argv.includes("--check");
const registry = checkOnly ? compileRuntimeRegistry() : writeRuntimeRegistry();
console.log(`${checkOnly ? "OK: compiled" : "OK: wrote"} ${repoRelative(ASSET_INDEX_PATH)}`);
console.log(`assetVersion=${registry.assetVersion}`);
console.log(`characterProfiles=${Object.keys(registry.characterProfiles).length}`);
console.log(`baseBodies=${Object.keys(registry.baseBodies).length}`);
console.log(`equipment=${Object.keys(registry.equipment).length}`);
console.log(`staticProps=${Object.keys(registry.staticProps).length}`);

import { spawn } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { runDoctor } from "../blender-character-pipeline/tools/model-doctor-lib.mjs";
import { assertDraftReceipt, classCharacterSpecs, digest } from "./class-character-spec.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const args = process.argv.slice(2);
const option = (name) => args.includes(name) ? args[args.indexOf(name) + 1] : undefined;
const runId = option("--run-id");
const jobs = Number(option("--jobs") ?? 2);
if (!Number.isInteger(jobs) || jobs < 1 || jobs > 4) throw new Error("--jobs must be between 1 and 4.");
if (!runId || !/^[a-z0-9][a-z0-9-]{0,70}$/.test(runId)) throw new Error("Supply --run-id <new-immutable-run>.");
for (let index = 0; index < args.length; index += 2) {
  if (!["--run-id", "--class", "--variant", "--jobs"].includes(args[index]) || !args[index + 1]) throw new Error(`Invalid argument: ${args[index]}`);
}
const all = classCharacterSpecs();
const selected = all.filter((request) => (!option("--class") || request.classKey === option("--class")) &&
  (!option("--variant") || request.bodyVariant === option("--variant")));
if (!selected.length) throw new Error("No matching class/variant.");
const doctor = await runDoctor({ strict: true });
if (!doctor.ready) throw new Error(`Local toolchain not ready: ${JSON.stringify(doctor.summary)}`);
const run = path.join(ROOT, "artifacts/unreal/class-characters", runId);
mkdirSync(run, { recursive: true });
const inputs = ["scripts/unreal/class-character-spec.mjs", "scripts/unreal/build-class-character.py",
  "scripts/unreal/class_character_audit.py", "scripts/blender-character-pipeline/blender/generate_mpfb_body.py",
  "scripts/blender-character-pipeline/blender/glb_roundtrip_audit.py",
  "scripts/blender-character-pipeline/data/full-roster-policy.json", "scripts/blender-character-pipeline/data/playable-character-roster.json",
  ...[...new Set(all.map((request) => request.bodyFamily))].map((family) => `scripts/blender-character-pipeline/data/body-families/${family}.body-family.json`),
  "scripts/blender-character-pipeline/data/body-families/humanoid_game_v2.skeleton.json"];
const source = { requests: all, tools: inputs.map((file) => ({ file, sha256: digest(readFileSync(path.join(ROOT, file))) })) };
const sourcePath = path.join(run, "inputs.json");
const serialized = JSON.stringify(source, null, 2) + "\n";
if (existsSync(sourcePath) && readFileSync(sourcePath, "utf8") !== serialized) throw new Error("Run inputs changed. Choose a new --run-id.");
writeFileSync(sourcePath, serialized);
writeFileSync(path.join(run, "doctor.json"), JSON.stringify(doctor, null, 2) + "\n");

const result = { schemaVersion: 1, runId, requested: selected.length, characters: [], runtimeEligible: false, nativeAccepted: false };
async function build(request) {
  const identity = `${request.classKey}_${request.bodyVariant}`;
  const directory = path.join(run, identity);
  mkdirSync(directory, { recursive: true });
  const requestPath = path.join(directory, "request.json");
  const receiptPath = path.join(directory, "receipt.json");
  writeFileSync(requestPath, JSON.stringify(request, null, 2) + "\n");
  try {
    if (!existsSync(receiptPath)) {
      console.log(`Building ${request.className} (${request.bodyVariant})`);
      const log = (await import("node:fs")).openSync(path.join(directory, "build.log"), "w");
      try {
        await new Promise((resolve, reject) => {
          const child = spawn(doctor.paths.blender, ["--background", "--threads", "2", "--addons", "bl_ext.blender_org.mpfb",
            "--python-exit-code", "1", "--python", "scripts/unreal/build-class-character.py", "--", "--request", requestPath,
            "--output", directory], { cwd: ROOT, windowsHide: true, stdio: ["ignore", log, log] });
          child.on("error", reject);
          child.on("close", (code) => code === 0 ? resolve() : reject(new Error(`Blender exited ${code}; inspect ${identity}/build.log`)));
        });
      } finally { (await import("node:fs")).closeSync(log); }
    }
    const receipt = assertDraftReceipt(JSON.parse(readFileSync(receiptPath, "utf8")), request, directory);
    result.characters.push({ identity, className: request.className, race: request.race, technicalPassed: true,
      receipt: `${identity}/receipt.json`, receiptSha256: digest(readFileSync(receiptPath)) });
    console.log(`Verified ${identity}`);
  } catch (error) {
    result.characters.push({ identity, technicalPassed: false, error: error.message });
    console.error(`${identity}: ${error.message}`);
  }
  writeFileSync(path.join(run, "report.json"), JSON.stringify(result, null, 2) + "\n");
}
// Each worker owns a different character directory. Only this coordinator
// writes the shared report; existing receipts are fully verified before reuse.
let next = 0;
await Promise.all(Array.from({ length: Math.min(jobs, selected.length) }, async () => {
  while (next < selected.length) await build(selected[next++]);
}));
if (result.characters.some((entry) => !entry.technicalPassed)) process.exitCode = 1;
console.log(`Draft bodies: ${result.characters.filter((entry) => entry.technicalPassed).length}/${selected.length}; native equipped acceptance remains open.`);

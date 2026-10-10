import { existsSync, readFileSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { assertDraftReceipt, classCharacterSpecs, digest } from "./class-character-spec.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const runId = process.argv[2];
if (!runId || !/^[a-z0-9][a-z0-9-]{0,70}$/.test(runId)) throw new Error("Supply the immutable character run id.");
const run = path.join(root, "artifacts/unreal/class-characters", runId);
const inputs = JSON.parse(readFileSync(path.join(run, "inputs.json"), "utf8"));
if (JSON.stringify(inputs.requests) !== JSON.stringify(classCharacterSpecs())) throw new Error("Character request snapshot changed.");
for (const source of inputs.tools) {
  if (!/^scripts\/[a-zA-Z0-9_./-]+$/.test(source.file) || source.file.split("/").includes("..")) throw new Error("Unsafe generating source path");
  if (digest(readFileSync(path.join(root, source.file))) !== source.sha256) throw new Error(`Generating input changed: ${source.file}`);
}
const escape = (text) => String(text).replace(/[&<>"']/g, (value) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[value]);
const rows = [];
const cards = [];
for (const request of inputs.requests) {
  const identity = `${request.classKey}_${request.bodyVariant}`;
  const directory = path.join(run, identity);
  const receiptPath = path.join(directory, "receipt.json");
  if (!existsSync(receiptPath)) {
    rows.push({ identity, status: "missing" });
    continue;
  }
  const receipt = JSON.parse(readFileSync(receiptPath, "utf8"));
  if (receipt.technicalPassed) assertDraftReceipt(receipt, request, directory);
  let anatomy = JSON.parse(readFileSync(path.join(directory, "anatomy.json"), "utf8"));
  const atlasPath = path.join(directory, "optimized-v2/review.json");
  const atlas = existsSync(atlasPath) ? JSON.parse(readFileSync(atlasPath, "utf8")) : null;
  if (atlas) {
    if (atlas.sourceReceiptSha256 !== digest(readFileSync(receiptPath)) || atlas.sourceModelSha256 !== digest(readFileSync(path.join(directory, "body.glb"))) || atlas.nativeAccepted !== false || atlas.runtimeEligible !== false) throw new Error(`Invalid atlas source: ${identity}`);
    for (const [field, file] of [["toolSha256", "scripts/unreal/atlas-class-characters.py"], ["deformationAuditSha256", "scripts/unreal/class_character_audit.py"], ["skinRefinementToolSha256", "scripts/unreal/class_character_skin.py"], ["skinRecipeSha256", "scripts/unreal/class-character-skin-recipes.json"], ["policySha256", "scripts/blender-character-pipeline/data/body-families/pilot-policy.json"]]) {
      if (atlas[field] !== digest(readFileSync(path.join(root, file)))) throw new Error(`Changed atlas input: ${file}`);
    }
    for (const file of atlas.files) {
      if (!/^[a-zA-Z0-9_.-]+$/.test(file.path) || file.path.includes("..")) throw new Error("Unsafe atlas evidence path");
      if (file.sha256 !== digest(readFileSync(path.join(directory, "optimized-v2", file.path)))) throw new Error(`Changed atlas evidence: ${identity}/${file.path}`);
    }
    if (atlas.skinCorrection) {
      const correction = atlas.skinCorrection;
      if (!/^[a-z_]+_[mf]\.json$/.test(correction.file) || correction.sha256 !== digest(readFileSync(path.join(root, "scripts/unreal/class-character-skin-corrections", correction.file))) || correction.solverSha256 !== digest(readFileSync(path.join(root, "scripts/unreal/fit-class-character-skin.py")))) throw new Error(`Changed skin correction: ${identity}`);
    }
  }
  let candidate = atlas?.passed ? "optimized-v2/" : "";
  if (candidate) anatomy = JSON.parse(readFileSync(path.join(directory, candidate, "anatomy.json"), "utf8"));
  let model = `${candidate}body.glb`;
  let front = candidate ? `${candidate}front.png` : "export-front.png";
  let head = candidate ? `${candidate}head.png` : "export-head.png";
  const motionPath = path.join(directory, candidate, "supplied-motion/review.json");
  let motion = existsSync(motionPath) ? JSON.parse(readFileSync(motionPath, "utf8")) : null;
  if (motion) {
    if (Object.keys(motion.clips).sort().join(",") !== ["two.walk", "two.run", "two.slash", "shield.walk", "shield.slash", "spell.bolt"].sort().join(",") || Object.values(motion.clips).some((clip) => clip.samples.length !== 17)) throw new Error(`Incomplete supplied-motion sample set: ${identity}`);
    if (motion.nativeAccepted !== false || motion.runtimeEligible !== false) throw new Error(`Invalid supplied-motion draft state: ${identity}`);
    if (motion.bodyReceiptSha256 !== digest(readFileSync(receiptPath)) || motion.modelRelativePath !== model || motion.modelSha256 !== digest(readFileSync(path.join(directory, model))) || (candidate && motion.atlasReceiptSha256 !== digest(readFileSync(atlasPath)))) throw new Error(`Stale supplied-motion evidence: ${identity}`);
    for (const [field, file] of [["sourceToolSha256", "review-class-character-motion.py"], ["chainContractSha256", "animation_replacement.py"], ["deformationAuditSha256", "class_character_audit.py"]]) {
      if (motion[field] !== digest(readFileSync(path.join(root, "scripts/unreal", file)))) throw new Error(`Changed motion review input: ${file}`);
    }
    for (const render of motion.renders) {
      if (!/^[a-zA-Z0-9_.-]+\.png$/.test(render.path)) throw new Error(`Unsafe motion render path: ${render.path}`);
      if (digest(readFileSync(path.join(directory, candidate, "supplied-motion", render.path))) !== render.sha256) throw new Error(`Changed motion render: ${identity}/${render.path}`);
    }
    for (const clip of Object.values(motion.clips)) {
      if (!/^[a-zA-Z0-9_ /-]+\.fbx$/.test(clip.file) || clip.file.split("/").includes("..")) throw new Error("Unsafe supplied clip path");
      if (clip.sourceSha256 !== digest(readFileSync(path.join(root, "unreal/AegisWar/AnimationImport", clip.file)))) throw new Error(`Changed supplied clip: ${clip.file}`);
    }
  }
  const dentitionPath = path.join(directory, "dentition-v1/review.json");
  const dentition = existsSync(dentitionPath) ? JSON.parse(readFileSync(dentitionPath, "utf8")) : null;
  if (dentition?.passed) {
    if (request.race !== "greenskin" || dentition.identity !== identity || dentition.sourceCandidate !== "optimized-v2" || dentition.nativeAccepted !== false || dentition.runtimeEligible !== false || dentition.sourceReceiptSha256 !== digest(readFileSync(atlasPath)) || dentition.bodyReceiptSha256 !== digest(readFileSync(receiptPath)) || dentition.sourceModelSha256 !== digest(readFileSync(path.join(directory, "optimized-v2/body.glb")))) throw new Error(`Invalid dentition source: ${identity}`);
    for (const [field, file] of [["toolSha256", "fit-class-character-dentition.py"], ["profileToolSha256", "class_character_dentition.py"], ["atlasToolSha256", "atlas-class-characters.py"], ["sourceMotionToolSha256", "review-class-character-motion.py"], ["chainContractSha256", "animation_replacement.py"], ["deformationAuditSha256", "class_character_audit.py"]]) {
      if (dentition[field] !== digest(readFileSync(path.join(root, "scripts/unreal", file)))) throw new Error(`Changed dentition input: ${file}`);
    }
    if (dentition.jawWeights.sourceSha256 !== digest(readFileSync(path.join(root, "scripts/unreal/class-character-jaw-weights.json"))) || Object.values(dentition.checks).some((passed) => passed !== true) || dentition.jawReview.length !== 3 || dentition.jawReview.some((row) => !row.passed)) throw new Error(`Incomplete dentition/jaw review: ${identity}`);
    for (const file of dentition.files) {
      if (!/^[a-zA-Z0-9_.-]+$/.test(file.path) || file.path.includes("..") || file.sha256 !== digest(readFileSync(path.join(directory, "dentition-v1", file.path)))) throw new Error(`Changed dentition evidence: ${identity}`);
    }
    if (!motion?.passed || Object.keys(dentition.clips).sort().join(",") !== Object.keys(motion.clips).sort().join(",") || Object.values(dentition.clips).some((clip) => clip.samples.length !== 17 || !clip.passed)) throw new Error(`Incomplete dentition motion: ${identity}`);
    for (const [key, clip] of Object.entries(dentition.clips)) {
      if (clip.file !== motion.clips[key].file || clip.sourceSha256 !== motion.clips[key].sourceSha256) throw new Error(`Changed dentition source clip: ${identity}`);
    }
    candidate = "dentition-v1/";
    model = `${candidate}body.glb`;
    front = `${candidate}front.png`;
    head = `${candidate}head.png`;
    anatomy = JSON.parse(readFileSync(path.join(directory, candidate, "anatomy.json"), "utf8"));
    motion = dentition;
  }
  const poses = Object.entries(anatomy.staticPoses);
  const worst = Math.max(...poses.map(([, pose]) => pose.maxEdgeExtensionM));
  rows.push({ identity, className: request.className, race: request.race, variant: request.bodyVariant,
    technicalPassed: receipt.technicalPassed, heightM: anatomy.heightM, staticMaxEdgeExtensionM: worst,
    atlasPassed: atlas?.passed ?? null, drawCalls: atlas?.after.drawCalls ?? null, triangles: atlas?.after.triangles ?? null,
    dentitionPassed: dentition?.passed ?? null,
    failedChecks: receipt.failedChecks, suppliedPosePassed: motion?.passed ?? null,
    suppliedPoseFailures: motion ? Object.entries(motion.clips).filter(([, clip]) => !clip.passed).map(([key]) => key) : [],
    model: `${identity}/${model}`, modelSha256: digest(readFileSync(path.join(directory, model))),
    receiptSha256: digest(readFileSync(receiptPath)) });
  const image = (file, label) => `<figure><a href="${identity}/${file}"><img loading="lazy" src="${identity}/${file}" alt="${escape(label)}"></a><figcaption>${escape(label)}</figcaption></figure>`;
  const views = [[front, "Exported body"], [head, "Exported face"], ["side.png", "Authoring side"], ["back.png", "Authoring back"],
    ["clay-front.png", "Authoring neutral anatomy"], ["clay-side.png", "Authoring neutral side"], ...poses.map(([key]) => [`${candidate}pose-${key}.png`, key.replaceAll("_", " ")])];
  const motionPrefix = dentition?.passed ? candidate : `${candidate}supplied-motion/`;
  const motionViews = motion ? Object.keys(motion.clips).flatMap((key) => [
    [`${motionPrefix}${key}.png`, `${key} midpoint — ${motion.clips[key].passed ? "sample checks pass" : "deformation needs repair"}`],
    [`${motionPrefix}${key}-worst.png`, `${key} maximum extension (sample ${motion.clips[key].worstSample})`],
  ]) : [];
  const jawViews = dentition?.passed ? [0, 12, 24].flatMap((degrees) => ["front", "three-quarter", "profile"].map((view) => image(`${candidate}jaw-${degrees}-${view}.png`, `Jaw ${degrees} degrees · ${view}`))) : [];
  cards.push(`<article data-race="${escape(request.race)}" data-class="${escape(request.className.toLowerCase())}">
    <div class="caption"><h2>${escape(request.className)}</h2><p>${escape(request.race.replaceAll("_", " "))} · ${request.bodyVariant === "m" ? "Male" : "Female"} · ${anatomy.heightM.toFixed(2)} m</p>
    <p class="${receipt.technicalPassed ? "pass" : "issue"}">${receipt.technicalPassed ? "Anatomy / static rig checks pass" : escape(receipt.failedChecks.join(", "))}</p>
    <p>Atlas: ${atlas ? `${atlas.passed ? "checks pass" : "needs repair"} · ${atlas.after.triangles.toLocaleString()} triangles · ${atlas.after.drawCalls} draws` : "pending"}.</p>
    <p>Supplied poses: ${motion ? motion.passed ? "sample checks pass" : "deformation repair required" : "pending"}. Native equipped review: pending.</p></div>
    ${image(front, request.className + " body")}
    <details><summary>Inspect face, topology silhouette and bends</summary><div class="views">${views.slice(1).map(([file, label]) => image(file, label)).join("")}</div></details>
    <details><summary>Supplied source pose samples</summary><div class="views">${motionViews.map(([file, label]) => image(file, label)).join("") || "Pending"}</div></details>
    ${jawViews.length ? `<details><summary>Fitted tusks and moving lower jaw</summary><div class="views">${jawViews.join("")}</div></details>` : ""}
    <p class="links"><a href="${identity}/${candidate}character.blend">Rigged candidate</a> · <a href="${identity}/fitting-source.blend">Live fit source</a> · <a href="${identity}/${model}">GLB</a> · <a href="${identity}/anatomy.json">Measurements</a></p></article>`);
}
const summary = { schemaVersion: 1, runId, expected: inputs.requests.length,
  built: rows.filter((row) => row.status !== "missing").length,
  technicalPassed: rows.filter((row) => row.technicalPassed).length,
  atlasPassed: rows.filter((row) => row.atlasPassed).length,
  sourcePoseReviewed: rows.filter((row) => row.suppliedPosePassed !== null && row.suppliedPosePassed !== undefined).length,
  sourcePosePassed: rows.filter((row) => row.suppliedPosePassed).length,
  dentitionPassed: rows.filter((row) => row.dentitionPassed).length,
  nativeAccepted: false, runtimeEligible: false, characters: rows };
let lineup = "";
if (existsSync(path.join(run, "race-lineup.json"))) {
  const evidence = JSON.parse(readFileSync(path.join(run, "race-lineup.json"), "utf8"));
  if (evidence.nativeAccepted !== false || evidence.runtimeEligible !== false || evidence.models.length !== 6 || evidence.renderToolSha256 !== digest(readFileSync(path.join(root, "scripts/unreal/render-class-character-lineup.py"))) || evidence.imageSha256 !== digest(readFileSync(path.join(run, "race-lineup.png")))) throw new Error("Invalid race lineup evidence");
  for (const model of evidence.models) {
    if (!/^[a-zA-Z0-9_/-]+\.glb$/.test(model.model) || model.model.split("/").includes("..") || !rows.some((row) => row.model === model.model && row.modelSha256 === model.sha256) || model.sha256 !== digest(readFileSync(path.join(run, model.model)))) throw new Error("Changed race lineup model");
  }
  summary.lineup = { path: "race-lineup.png", sha256: evidence.imageSha256 };
  lineup = '<figure><a href="race-lineup.png"><img src="race-lineup.png" alt="Six races rendered at the same metre scale"></a><figcaption>Shared metre scale · six representative male bodies · draft anatomy</figcaption></figure>';
}
writeFileSync(path.join(run, "checkpoint.json"), JSON.stringify(summary, null, 2) + "\n");
writeFileSync(path.join(run, "review.html"), `<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AegisWar class character review</title><style>
*{box-sizing:border-box}body{margin:0;background:#171b20;color:#e9edf1;font:16px/1.5 system-ui,sans-serif}header{padding:36px;max-width:1100px}h1{font-size:30px;margin:0}p{margin:8px 0;color:#bfc7cf}strong{color:#f3d79b}.controls{position:sticky;top:0;background:#20262ded;padding:16px 36px;display:flex;gap:16px;z-index:1}input,select{padding:10px;background:#11161b;color:#eee;border:1px solid #62707e;border-radius:6px}main{padding:24px;display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:22px}article{background:#232a31;border:1px solid #3a444f;border-radius:10px;overflow:hidden}h2{font-size:20px;margin:0}.caption{padding:20px}.caption p{font-size:13px}.pass{color:#a5d6b0!important}.issue{color:#f1b38b!important}figure{margin:0}img{display:block;width:100%;height:auto}figcaption{font-size:12px;padding:6px 12px;color:#c7d0d9}summary{padding:12px 18px;cursor:pointer}.views{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}.links{padding:12px 18px;font-size:12px}a{color:#b4d7ef}article[hidden]{display:none}
</style><header><h1>AegisWar · Class character foundations</h1><p>${summary.built} / ${summary.expected} bodies built · ${summary.atlasPassed} derived candidates pass anatomy/export checks · ${summary.sourcePosePassed} / ${summary.sourcePoseReviewed} supplied-pose reviews pass</p><p><strong>Draft authoring models.</strong> Armor fitting guides are editor-only offsets. Native equipment, deformation corrections, foot locking, LODs and final appearance acceptance remain open.</p><p>All pictures are actual Blender renders of the local mesh. Exported body and face pictures use the re-imported GLB.</p>${lineup}</header>
<div class="controls"><input id="search" type="search" placeholder="Filter classes" aria-label="Filter classes"><select id="race" aria-label="Filter races"><option value="">All races</option>${[...new Set(inputs.requests.map((request) => request.race))].map((race) => `<option value="${race}">${escape(race.replaceAll("_", " "))}</option>`).join("")}</select></div><main>${cards.join("")}</main><script>
function filter(){const term=document.querySelector('#search').value.toLowerCase(),race=document.querySelector('#race').value;document.querySelectorAll('article').forEach(card=>card.hidden=(!card.dataset.class.includes(term)||(race&&card.dataset.race!==race)))}document.querySelector('#search').addEventListener('input',filter);document.querySelector('#race').addEventListener('change',filter);
</script></html>\n`);
console.log(JSON.stringify({ built: summary.built, technicalPassed: summary.technicalPassed, sourcePoseReviewed: summary.sourcePoseReviewed, review: path.join(run, "review.html") }));

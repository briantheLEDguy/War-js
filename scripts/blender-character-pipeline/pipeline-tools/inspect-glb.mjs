import { existsSync, readFileSync } from "node:fs";
import path from "node:path";
import { resolveRepoPath, workflowError } from "../tools/workspace-paths.mjs";

const JSON_CHUNK = 0x4e4f534a;

export function readGlbJson(inputPath) {
  const filePath = resolveRepoPath(inputPath, "GLB");
  if (!existsSync(filePath)) throw workflowError("MODEL_SOURCE_MISSING", `GLB does not exist: ${inputPath}`);
  const buffer = readFileSync(filePath);
  if (buffer.length < 20 || buffer.toString("ascii", 0, 4) !== "glTF" || buffer.readUInt32LE(4) !== 2) {
    throw workflowError("MODEL_FORMAT_INVALID", `Expected a GLB 2.0 file: ${inputPath}`);
  }
  const declaredLength = buffer.readUInt32LE(8);
  if (declaredLength !== buffer.length) throw workflowError("MODEL_LENGTH_INVALID", `GLB length header does not match ${inputPath}.`);
  let offset = 12;
  while (offset + 8 <= buffer.length) {
    const length = buffer.readUInt32LE(offset);
    const type = buffer.readUInt32LE(offset + 4);
    const chunk = buffer.subarray(offset + 8, offset + 8 + length);
    if (type === JSON_CHUNK) return JSON.parse(chunk.toString("utf8").replace(/[\0\s]+$/g, ""));
    offset += 8 + length;
  }
  throw workflowError("MODEL_JSON_CHUNK_MISSING", `GLB has no JSON chunk: ${inputPath}`);
}

export function inspectGlb(inputPath, requirements = {}) {
  const document = readGlbJson(inputPath);
  const nodes = document.nodes ?? [];
  const meshes = document.meshes ?? [];
  const skins = document.skins ?? [];
  const animations = document.animations ?? [];
  const nodeNames = new Set(nodes.map((node) => node.name).filter(Boolean));
  const animationNames = animations.map((animation) => animation.name).filter(Boolean);
  const errors = [];
  if (requirements.requireMesh !== false && meshes.length === 0) errors.push("GLB contains no meshes");
  if (requirements.skeletonId && !nodes.some((node) => node.name === requirements.skeletonId)) {
    errors.push(`GLB does not expose canonical skeleton node ${requirements.skeletonId}`);
  }
  if (requirements.requiredNodes) {
    for (const name of requirements.requiredNodes) if (!nodeNames.has(name)) errors.push(`GLB is missing required node ${name}`);
  }
  if (requirements.requiredAnimations) {
    for (const name of requirements.requiredAnimations) if (!animationNames.includes(name)) errors.push(`GLB is missing required animation ${name}`);
  }
  if (requirements.requireSkin && skins.length === 0) errors.push("GLB contains no skin");
  if (requirements.minJointCount !== undefined) {
    const jointCount = Math.max(0, ...(skins.map((skin) => skin.joints?.length ?? 0)));
    if (jointCount < requirements.minJointCount) errors.push(`GLB skin has ${jointCount} joints; expected at least ${requirements.minJointCount}`);
  }
  const rootExtras = nodes.flatMap((node) => node.extras ? [node.extras] : []);
  return {
    file: path.basename(inputPath),
    version: document.asset?.version ?? null,
    meshCount: meshes.length,
    nodeCount: nodes.length,
    skinCount: skins.length,
    animationNames,
    nodeNames: [...nodeNames].sort(),
    extras: rootExtras,
    valid: errors.length === 0,
    errors,
  };
}

import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, realpathSync, statSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const verifiedInputs = new Map<string, Readonly<Record<string, string>>>();
const hash = (file: string) => createHash('sha256').update(readFileSync(file)).digest('hex');
const helpers = ['citadel_terrain_evidence.py', 'aegis_citadel_terrain.py',
  'aegis_citadel_terrain_readback.py', 'aegis_citadel_terrain_render_readback.py'];
const toolDirectory = path.dirname(fileURLToPath(import.meta.url));
const confined = (root: string, file: string) => {
  const relative = path.relative(root, file);
  return relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
};

/** A successful reconstruction is reusable only while every consumed byte remains identical. */
export function terrainAuditInputsUnchanged(inputs: Readonly<Record<string, string>>): boolean {
  return Object.entries(inputs).every(([file, expected]) => hash(file) === expected);
}

/** Python reproduces clipping once per exact input set; package checks still run separately on every call. */
export function requireNativeCitadelTerrain(repository: string, run: string): void {
  const root = realpathSync(repository), directory = realpathSync(run);
  if (!confined(path.join(root, 'artifacts/unreal/aegis-citadel'), directory))
    throw new Error('Native terrain audit escaped its candidate directory.');
  const key = JSON.stringify([root, directory]);
  const previous = verifiedInputs.get(key);
  if (previous && terrainAuditInputsUnchanged(previous)) return;
  verifiedInputs.delete(key);
  const sources = Object.fromEntries(helpers.map(name => {
    const file = realpathSync(path.join(toolDirectory, name)); return [file, hash(file)];
  }));
  const script = path.join(toolDirectory, 'citadel_terrain_evidence.py');
  const result = spawnSync('python', ['-B', script, repository, run], { encoding: 'utf8', windowsHide: true,
    timeout: 60_000, maxBuffer: 256 * 1024 });
  if (result.error || result.status !== 0)
    throw new Error('Native terrain preservation evidence failed: ' + (result.error?.message ?? result.stderr.trim()));
  const receipt = JSON.parse(result.stdout), inputs = receipt.inputHashes;
  if (receipt.schemaVersion !== 1 || receipt.passed !== true || receipt.physicalApproval !== false || receipt.visualApproval !== false
    || !inputs || typeof inputs !== 'object' || Array.isArray(inputs) || Object.keys(inputs).length < 6
    || [path.join(directory, 'blueprint.json'), path.join(directory, 'candidate.json')].some(file => !inputs[file])
    || Object.entries(sources).some(([file, expected]) => inputs[file] !== expected)
    || Object.entries(inputs).some(([file, expected]) => typeof expected !== 'string' || !/^[a-f0-9]{64}$/.test(expected)
      || !path.isAbsolute(file) || realpathSync(file) !== file || !statSync(file).isFile()
      || (!confined(root, file) && !confined(realpathSync(toolDirectory), file)))
    || !terrainAuditInputsUnchanged(inputs))
    throw new Error('Native terrain reconstruction input custody changed or is incomplete.');
  verifiedInputs.set(key, Object.freeze({ ...inputs }));
}

import { createHash, randomUUID } from 'node:crypto';
import { closeSync, existsSync, lstatSync, mkdirSync, openSync, readFileSync, readdirSync, realpathSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { citadelReviewArguments } from './citadel-review-launch';
import { requireCitadelPackageOwnership } from './native-package-evidence';

export type OrdinaryProofPhase = 'save' | 'publish' | 'restore';
export type FileHashes = Record<string, string>;
export interface OrdinaryProofBinding {
  schemaVersion: 1; binaryPath: string; binarySha256: string; sourceHashes: FileHashes;
}
export interface OrdinaryProofConfig {
  schemaVersion: 1; runId: string; phase: OrdinaryProofPhase; map: string; signature: string;
  mapSha256: string; sourceRevision: string; cityRevision: string; receiptPath: string; receiptSha256: string;
  binaryPath: string; binarySha256: string; sourceHashes: FileHashes; packageHashes: FileHashes;
  outputDir: string; draftPath: string; publicationPath: string; manifestPath: string; manifestSha256: string;
  preexistingWorldEditHashes: FileHashes;
}
export interface OrdinaryProofManifest {
  schemaVersion: 1; runId: string; map: string; id: string; templateId: string; sourceIdentity: string;
  meshPath: string; hidden: boolean; location: number[]; rotation: number[]; scale: number[];
}
export interface OrdinaryProofOptions {
  repository: string; receiptPath: string; bindingPath: string; executable: string; engineRoot?: string; runId?: string;
}
export interface OrdinaryProofLaunch {
  phase: OrdinaryProofPhase; configPath: string; config: OrdinaryProofConfig; args: string[]; outputDir: string;
  executable: string; repository: string;
}
export interface OrdinaryProofProcess { pid: number; exitCode: number; signal?: string | null }
export type OrdinaryProofLauncher = (request: OrdinaryProofLaunch) => Promise<OrdinaryProofProcess>;
export interface OrdinaryProofResult {
  schemaVersion: 1; passed: true; runId: string; outputDir: string; reports: Record<OrdinaryProofPhase, any>;
  manifest: OrdinaryProofManifest; preexistingWorldEditHashes: FileHashes; ownedWorldEditHashes: FileHashes;
  leasePath: string; leaseSha256: string;
  evidenceHashes: FileHashes;
  fixtureAdmission: true; ordinaryLoginVerified: false; sharedPublication: false; visualApproved: false; gameplayApproved: false;
}

const digest = (bytes: Buffer | string) => createHash('sha256').update(bytes).digest('hex');
const sha = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const object = (value: any): value is Record<string, any> => Boolean(value) && typeof value === 'object' && !Array.isArray(value);
const readJson = (file: string): any => JSON.parse(readFileSync(file, 'utf8').replace(/^\uFEFF/, ''));
const nativePath = (file: string) => file.replaceAll('\\', '/');
const nativeHashes = (hashes: FileHashes): FileHashes => Object.fromEntries(Object.entries(hashes)
  .map(([file, hash]) => [nativePath(file), hash]));
const samePath = (left: string, right: string) => process.platform === 'win32'
  ? path.resolve(left).toLowerCase() === path.resolve(right).toLowerCase() : path.resolve(left) === path.resolve(right);
const confined = (root: string, file: string) => {
  const relative = path.relative(root, file);
  return Boolean(relative) && relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
};
function exactKeys(value: any, keys: string[], description: string): void {
  if (!object(value) || Object.keys(value).sort().join('\n') !== [...keys].sort().join('\n'))
    throw new Error('Unexpected or missing ' + description + ' fields.');
}

/** Reject links at every existing ancestor, including Windows directory junctions. */
export function requireOrdinarySafePath(file: string, root?: string): string {
  if (!path.isAbsolute(file)) throw new Error('Ordinary proof paths must be absolute: ' + file);
  const resolved = path.resolve(file);
  if (root && !samePath(root, resolved) && !confined(path.resolve(root), resolved))
    throw new Error('Ordinary proof path escaped its configured root: ' + file);
  const parsed = path.parse(resolved); let current = parsed.root;
  for (const part of resolved.slice(parsed.root.length).split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    const state = lstatSync(current, { throwIfNoEntry: false });
    if (!state) break;
    if (state.isSymbolicLink() || !samePath(realpathSync(current), current))
      throw new Error('Ordinary proof rejects symbolic links or reparse escapes: ' + current);
  }
  return resolved;
}

function files(directory: string, accept: (name: string) => boolean): string[] {
  requireOrdinarySafePath(directory);
  if (!existsSync(directory)) return [];
  if (!lstatSync(directory).isDirectory()) throw new Error('Expected ordinary proof directory: ' + directory);
  const result: string[] = [];
  for (const row of readdirSync(directory, { withFileTypes: true })) {
    const file = requireOrdinarySafePath(path.join(directory, row.name), directory);
    if (row.isSymbolicLink()) throw new Error('Ordinary proof rejects linked entries: ' + file);
    if (row.isDirectory()) result.push(...files(file, accept));
    else if (row.isFile() && accept(row.name)) result.push(file);
    else if (!row.isFile()) throw new Error('Ordinary proof rejects nonregular entries: ' + file);
  }
  return result.sort();
}

/** Complete permitted source inventory; a binding cannot omit newly added source files. */
export function sourceInventory(repository: string): string[] {
  const root = requireOrdinarySafePath(repository);
  const source = path.join(root, 'unreal/AegisWar/Source');
  for (const module of ['AegisWar', 'AegisWarEditorTools'])
    if (!existsSync(requireOrdinarySafePath(path.join(source, module), root)))
      throw new Error('Both native module source inventories are required.');
  const config = path.join(root, 'unreal/AegisWar/Config'), scripts = path.join(root, 'scripts/unreal');
  if (!existsSync(requireOrdinarySafePath(config, root)) || !existsSync(requireOrdinarySafePath(scripts, root)))
    throw new Error('Project Config and Unreal tooling source inventories are required.');
  return [...files(source, name => /\.(cpp|h|hpp|inl|c|cs)$/i.test(name)),
    ...files(config, name => /\.ini$/i.test(name)), ...files(scripts, name => /\.(ts|py|cs)$/i.test(name))].sort();
}

export function requireOrdinaryBinding(repository: string, binding: any): asserts binding is OrdinaryProofBinding {
  exactKeys(binding, ['schemaVersion', 'binaryPath', 'binarySha256', 'sourceHashes'], 'binary/source binding');
  const binaries = path.join(repository, 'unreal/AegisWar/Binaries');
  if (binding.schemaVersion !== 1 || typeof binding.binaryPath !== 'string' || !sha(binding.binarySha256)
    || !object(binding.sourceHashes) || !Object.keys(binding.sourceHashes).length
    || !/^(?:UnrealEditor-)?AegisWar\.dll$/.test(path.basename(binding.binaryPath)))
    throw new Error('Explicit configured AegisWar DLL/source binding is required.');
  const binary = requireOrdinarySafePath(binding.binaryPath, binaries);
  if (!lstatSync(binary).isFile() || digest(readFileSync(binary)) !== binding.binarySha256)
    throw new Error('Configured native binary bytes changed.');
  const expected = sourceInventory(repository), supplied = Object.keys(binding.sourceHashes).sort();
  if (expected.length !== supplied.length || expected.some((file, index) => file !== supplied[index]))
    throw new Error('Binding must contain the complete, exact native/Config/Unreal tooling source inventory.');
  for (const file of expected) if (!sha(binding.sourceHashes[file])
    || digest(readFileSync(requireOrdinarySafePath(file, repository))) !== binding.sourceHashes[file])
    throw new Error('Bound native or tooling source bytes changed: ' + file);
}

export function snapshotWorldEdit(repository: string): FileHashes {
  const root = path.join(requireOrdinarySafePath(repository), 'unreal/AegisWar/Saved/WorldEdit');
  return Object.fromEntries(files(root, () => true).map(file => [file, digest(readFileSync(file))]));
}
export function requireWorldEditPreserved(before: FileHashes, after: FileHashes): void {
  for (const [file, hash] of Object.entries(before)) if (after[file] !== hash)
    throw new Error('Preexisting ordinary WorldEdit bytes changed or disappeared: ' + file);
}

/** Matches FCrc::StrCrc32: each character contributes four little-endian bytes. */
export function ordinaryPublicationPath(map: string, draftPath: string): string {
  if (!/^\/Game\/[A-Za-z0-9_/]+$/.test(map)) throw new Error('Invalid ordinary publication map.');
  let crc = 0xffffffff;
  for (const character of map) {
    const value = character.charCodeAt(0);
    for (let shift = 0; shift < 32; shift += 8) {
      crc ^= (value >>> shift) & 255;
      for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
  }
  const hash = ((~crc) >>> 0).toString(16).padStart(8, '0');
  return path.join(path.dirname(draftPath), path.posix.basename(map) + '-' + hash + '-live.json');
}

/** There is no caller-supplied native-argument escape hatch. */
export function requireOrdinaryArguments(args: string[]): void {
  for (const argument of args) {
    const name = argument.replace(/^-+/, '').split('=')[0].toLowerCase();
    if (/^(?:saved|savedir|saveddir|saved-directory|userdir|user-directory|usersettingsdir|warproofdraftid)$/.test(name)
      || (/^war.*proof(?:config|draftid|reload)?$/.test(name)
        && !['warinterfaceproof', 'warbuilderordinaryproof', 'warbuilderordinaryconfig'].includes(name)))
      throw new Error('Storage redirects and conflicting interface proof modes are forbidden: ' + argument);
    if (['warinterfaceproof', 'warbuilderordinaryproof'].includes(name) && argument.includes('='))
      throw new Error('Ordinary proof admission flags cannot carry values.');
  }
  for (const required of ['-WarDevelopmentGM', '-WarInterfaceProof', '-WarBuilderOrdinaryProof'])
    if (args.filter(argument => argument === required).length !== 1) throw new Error('Missing or duplicate ordinary proof admission: ' + required);
  if (args.filter(argument => argument.startsWith('-WarBuilderOrdinaryConfig=')).length !== 1)
    throw new Error('One explicit ordinary proof config is required.');
}

export function validateOrdinaryManifest(value: any, runId: string, map: string): asserts value is OrdinaryProofManifest {
  exactKeys(value, ['schemaVersion', 'runId', 'map', 'id', 'templateId', 'sourceIdentity', 'meshPath', 'hidden',
    'location', 'rotation', 'scale'], 'native ordinary manifest');
  const vector = (row: any, count: number) => Array.isArray(row) && row.length === count
    && row.every((number: any) => typeof number === 'number' && Number.isFinite(number));
  if (value.schemaVersion !== 1 || value.runId !== runId || value.map !== map
    || ![value.id, value.templateId].every(item => typeof item === 'string' && item.length > 0 && item.length <= 128)
    || typeof value.meshPath !== 'string' || !/^\/Game\/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+$/.test(value.meshPath)
    || typeof value.sourceIdentity !== 'string' || !value.sourceIdentity.startsWith(value.meshPath + ':')
    || !sha(value.sourceIdentity.slice(value.meshPath.length + 1)) || value.hidden !== false
    || !vector(value.location, 3) || !vector(value.rotation, 4) || !vector(value.scale, 3)
    || Math.abs(Math.hypot(...value.rotation) - 1) > .0001
    || value.scale.some((scale: number) => scale < .05 || scale > 20))
    throw new Error('Native ordinary sentinel identity, model or transform is invalid.');
}

function requireStoredSentinel(file: string, manifest: OrdinaryProofManifest): void {
  const draft = readJson(file);
  if (draft.schemaVersion !== 2 || draft.zoneId !== 'aegis_capital' || typeof draft.baseline !== 'string'
    || !draft.baseline || !Array.isArray(draft.objects)) throw new Error('Expected actual production WorldEdit draft schema.');
  const matches = draft.objects.filter((row: any) => row?.id === manifest.id);
  const expected = [...manifest.location, ...manifest.rotation, ...manifest.scale], row = matches[0];
  if (matches.length !== 1 || row.templateId !== manifest.templateId || row.sourceIdentity !== manifest.sourceIdentity
    || row.hidden !== manifest.hidden || !Array.isArray(row.transform) || row.transform.length !== 10
    || row.transform.some((number: any, index: number) => typeof number !== 'number' || !Number.isFinite(number)
      || Math.abs(number - expected[index]) > .0001))
    throw new Error('Ordinary stored sentinel differs from its native manifest: ' + file);
}

const reportKeys = ['schemaVersion', 'passed', 'runId', 'phase', 'map', 'configSha256', 'receiptSha256', 'binarySha256',
  'draftPath', 'publicationPath', 'manifestSha256', 'draftSha256', 'publicationSha256', 'guiOpened', 'saveClicked',
  'loadClicked', 'publishClicked', 'startupRestored', 'fixtureAdmission', 'ordinaryLoginVerified', 'sharedPublication',
  'visualApproved', 'gameplayApproved', 'detail', 'nativePid'];
export function validateOrdinaryPhaseReport(report: any, config: OrdinaryProofConfig, configSha256: string,
  nativePid: number, manifestSha256: string): void {
  exactKeys(report, reportKeys, 'native ordinary phase report');
  const phase = config.phase, publication = ordinaryPublicationPath(config.map, config.draftPath);
  if (report.schemaVersion !== 1 || report.passed !== true || report.runId !== config.runId || report.phase !== phase
    || report.map !== config.map || report.configSha256 !== configSha256 || report.receiptSha256 !== config.receiptSha256
    || report.binarySha256 !== config.binarySha256 || report.nativePid !== nativePid
    || typeof report.nativePid !== 'number' || !Number.isSafeInteger(report.nativePid) || report.nativePid <= 0
    || !samePath(report.draftPath, config.draftPath) || !samePath(report.publicationPath, publication)
    || report.manifestSha256 !== manifestSha256 || !sha(report.draftSha256)
    || (phase === 'save' ? report.publicationSha256 !== '' : !sha(report.publicationSha256))
    || report.guiOpened !== (phase !== 'restore') || report.saveClicked !== (phase === 'save')
    || report.loadClicked !== (phase === 'publish') || report.publishClicked !== (phase === 'publish')
    || report.startupRestored !== (phase === 'restore') || report.fixtureAdmission !== true
    || ['ordinaryLoginVerified', 'sharedPublication', 'visualApproved', 'gameplayApproved'].some(key => report[key] !== false)
    || typeof report.detail !== 'string' || !report.detail.length)
    throw new Error('Native ordinary phase report is not exact successful evidence for its independent process.');
}

function writeEvidence(file: string, value: unknown): void {
  requireOrdinarySafePath(file); writeFileSync(file, JSON.stringify(value, null, 2) + '\n', { flag: 'wx' });
}
function preserveBytes(output: string, repository: string, hashes: FileHashes): void {
  for (const file of Object.keys(hashes)) {
    const relative = path.relative(path.join(repository, 'unreal/AegisWar/Saved/WorldEdit'), file);
    const copy = requireOrdinarySafePath(path.join(output, relative), output);
    mkdirSync(path.dirname(copy), { recursive: true }); writeFileSync(copy, readFileSync(file), { flag: 'wx' });
  }
}
function requireState(before: FileHashes, after: FileHashes, owned: FileHashes): void {
  requireWorldEditPreserved(before, after);
  const expected = { ...before, ...owned };
  if (Object.keys(after).length !== Object.keys(expected).length || Object.keys(after).some(file => after[file] !== expected[file]))
    throw new Error('Unexpected or changed ordinary WorldEdit files; preserve all files for owner review.');
}

/** Three independent native processes; filesystem checks also run on every failure path. */
export async function runGmOrdinaryPersistence(options: OrdinaryProofOptions, launch: OrdinaryProofLauncher): Promise<OrdinaryProofResult> {
  if (Object.keys(options).some(key => !['repository', 'receiptPath', 'bindingPath', 'executable', 'engineRoot', 'runId'].includes(key)))
    throw new Error('Ordinary proof does not accept extra native arguments or storage overrides.');
  const repository = requireOrdinarySafePath(options.repository), project = path.join(repository, 'unreal/AegisWar/AegisWar.uproject');
  const receiptPath = requireOrdinarySafePath(options.receiptPath), bindingPath = requireOrdinarySafePath(options.bindingPath);
  const receiptBytes = readFileSync(receiptPath), bindingBytes = readFileSync(bindingPath);
  const receipt = readJson(receiptPath), binding = readJson(bindingPath);
  const receiptSha256 = digest(receiptBytes), bindingSha256 = digest(bindingBytes);
  const verifyInputs = () => {
    if (digest(readFileSync(requireOrdinarySafePath(receiptPath))) !== receiptSha256
      || digest(readFileSync(requireOrdinarySafePath(bindingPath))) !== bindingSha256)
      throw new Error('Explicit staged receipt or binary/source binding changed during proof.');
    requireOrdinaryBinding(repository, binding);
    requireCitadelPackageOwnership(receipt.packageHashes, true); requireCitadelPackageOwnership(receipt.sourcePackageHashes, false);
    for (const name of Object.keys({ ...receipt.sourcePackageHashes, ...receipt.packageHashes })) {
      const root = name.startsWith('/Game/') ? path.join(repository, 'unreal/AegisWar/Content')
        : options.engineRoot && path.join(options.engineRoot, 'Engine/Content');
      if (!root) throw new Error('Bound native Engine content root is required.');
      const stem = path.join(root, name.slice(name.startsWith('/Game/') ? 6 : 8));
      for (const extension of ['.umap', '.uasset']) requireOrdinarySafePath(stem + extension, root);
    }
    return citadelReviewArguments(repository, receipt, project, options.engineRoot);
  };
  verifyInputs(); requireOrdinarySafePath(options.executable);
  const runId = options.runId ?? randomUUID().replaceAll('-', '');
  if (!/^[a-f0-9]{32}$/.test(runId)) throw new Error('Ordinary proof run ID must be a fresh 32-digit GUID.');
  const saved = path.join(repository, 'unreal/AegisWar/Saved');
  const wrapper = /^\/Game\/WorldRebuild\/(CitadelHumanReview_\d{8}_[a-f0-9]{12})\/Walkthrough$/.exec(receipt.map);
  const campaign = /^\/Game\/WorldRebuild\/(AegisCitadel_[a-f0-9]{12})\/CampaignCandidate$/.exec(receipt.map);
  const target = requireOrdinarySafePath(wrapper
    ? path.join(saved, 'WorldEdit/PrivateReviews', wrapper[1], 'Walkthrough')
    : path.join(saved, 'WorldEdit', campaign![1]), saved);
  const draftPath = path.join(target, 'draft.json'), publication = ordinaryPublicationPath(receipt.map, draftPath);
  if (existsSync(target) && (!lstatSync(target).isDirectory() || readdirSync(target).length))
    throw new Error('Ordinary target must be entirely empty, including locks, temporary files and subdirectories.');
  const before = snapshotWorldEdit(repository);
  const outputDir = requireOrdinarySafePath(path.join(saved, 'WorldEditOrdinaryProof', runId), saved);
  if (existsSync(outputDir)) throw new Error('Ordinary proof evidence run already exists; use a fresh GUID.');
  const leaseDir = requireOrdinarySafePath(path.join(saved, 'WorldEditOrdinaryProof/leases'), saved);
  mkdirSync(leaseDir, { recursive: true });
  const leasePath = path.join(leaseDir, digest(target) + '.lock'), lease = openSync(leasePath, 'wx');
  let owned: FileHashes = {}, manifest: OrdinaryProofManifest | undefined, manifestSha256 = '';
  let leaseSha256 = '';
  const reports = {} as Record<OrdinaryProofPhase, any>, pids = new Set<number>();
  const evidenceHashes: FileHashes = {};
  const verifyEvidence = () => {
    for (const [file, hash] of Object.entries(evidenceHashes))
      if (digest(readFileSync(requireOrdinarySafePath(file, outputDir))) !== hash)
        throw new Error('Previously bound ordinary proof evidence bytes changed: ' + file);
  };
  try {
    writeFileSync(lease, JSON.stringify({ runId, target, ownerPid: process.pid }) + '\n');
    leaseSha256 = digest(readFileSync(leasePath));
    mkdirSync(outputDir); writeEvidence(path.join(outputDir, 'before-snapshot.json'), before);
    preserveBytes(path.join(outputDir, 'before-bytes'), repository, before);
    for (const phase of ['save', 'publish', 'restore'] as const) {
      const phaseBefore = snapshotWorldEdit(repository); requireState(before, phaseBefore, owned);
      verifyEvidence();
      if (digest(readFileSync(requireOrdinarySafePath(leasePath, leaseDir))) !== leaseSha256)
        throw new Error('Ordinary proof target lease changed; preserve it for owner review.');
      writeEvidence(path.join(outputDir, phase + '-before-snapshot.json'), phaseBefore);
      const base = verifyInputs(), configPath = path.join(outputDir, phase + '-config.json');
      const config: OrdinaryProofConfig = { schemaVersion: 1, runId, phase, map: receipt.map, signature: receipt.signature,
        mapSha256: receipt.mapSha256, sourceRevision: receipt.sourceRevision, cityRevision: receipt.cityRevision,
        receiptPath: nativePath(receiptPath), receiptSha256, binaryPath: nativePath(binding.binaryPath), binarySha256: binding.binarySha256,
        sourceHashes: nativeHashes(binding.sourceHashes), packageHashes: { ...receipt.sourcePackageHashes, ...receipt.packageHashes },
        outputDir: nativePath(outputDir), draftPath: nativePath(draftPath), publicationPath: phase === 'save' ? '' : nativePath(publication),
        manifestPath: nativePath(path.join(outputDir, 'manifest.json')), manifestSha256: phase === 'save' ? '' : manifestSha256,
        preexistingWorldEditHashes: nativeHashes(before) };
      writeEvidence(configPath, config); const configSha256 = digest(readFileSync(configPath));
      evidenceHashes[configPath] = configSha256; verifyEvidence();
      const args = [...base, '-WarInterfaceProof', '-WarBuilderOrdinaryProof', '-WarBuilderOrdinaryConfig=' + configPath,
        '-unattended', '-nosound', '-RenderOffscreen', '-ForceRes', '-ResX=1920', '-ResY=1080',
        '-abslog=' + path.join(outputDir, phase + '.log')];
      requireOrdinaryArguments(args);
      const processResult = await launch({ phase, configPath, config, args, outputDir, executable: options.executable, repository });
      const after = snapshotWorldEdit(repository); writeEvidence(path.join(outputDir, phase + '-after-snapshot.json'), after);
      requireWorldEditPreserved(before, after); verifyInputs(); verifyEvidence();
      if (digest(readFileSync(requireOrdinarySafePath(leasePath, leaseDir))) !== leaseSha256)
        throw new Error('Ordinary proof target lease changed during execution.');
      if (digest(readFileSync(requireOrdinarySafePath(configPath, outputDir))) !== configSha256)
        throw new Error('Native phase config changed during execution.');
      if (!Number.isSafeInteger(processResult.pid) || processResult.pid <= 0 || pids.has(processResult.pid)
        || processResult.exitCode !== 0 || processResult.signal)
        throw new Error('Ordinary proof requires three distinct successfully exited native processes.');
      pids.add(processResult.pid);
      const actualManifestSha = digest(readFileSync(requireOrdinarySafePath(config.manifestPath, outputDir)));
      if (phase !== 'save' && actualManifestSha !== manifestSha256) throw new Error('Native sentinel manifest bytes changed.');
      const actualManifest = readJson(config.manifestPath); validateOrdinaryManifest(actualManifest, runId, receipt.map);
      if (phase === 'save') {
        manifest = actualManifest; manifestSha256 = actualManifestSha;
        evidenceHashes[path.resolve(config.manifestPath)] = actualManifestSha;
      }
      const reportPath = requireOrdinarySafePath(path.join(outputDir, phase + '-report.json'), outputDir);
      const reportBytes = readFileSync(reportPath), report = JSON.parse(reportBytes.toString('utf8').replace(/^\uFEFF/, ''));
      validateOrdinaryPhaseReport(report, config, configSha256, processResult.pid, manifestSha256);
      evidenceHashes[reportPath] = digest(reportBytes);
      if (campaign) {
        const scenePath = requireOrdinarySafePath(path.join(outputDir, phase + '-scene.json'), outputDir);
        const scene = readJson(scenePath);
        if (scene.schemaVersion !== 1 || scene.passed !== true || scene.phase !== phase || scene.map !== receipt.map
          || scene.city !== receipt.city || scene.cityRevision !== receipt.cityRevision
          || scene.zones !== 32 || scene.directedPortals !== 70 || scene.decorObjects !== 56
          || scene.practicalLights !== 34 || scene.residents !== 8 || scene.mouseAxesUnattenuated !== true
          || scene.actualCameraPixelHandlerVerified !== true || scene.cameraStateRestored !== true
          || scene.physicalMouseHardwareVerified !== false || scene.fullSiegeAdmissionApproved !== false || scene.releaseAcceptance !== false
          || ![scene.cameraYawBefore, scene.cameraYawAfter, scene.cameraYawExpected, scene.cameraPitchAfter, scene.cameraPitchExpected]
            .every(value => typeof value === 'number' && Number.isFinite(value))
          || Math.abs(scene.cameraYawAfter - scene.cameraYawExpected) > .0001
          || Math.abs(scene.cameraPitchAfter - scene.cameraPitchExpected) > .0001
          || Math.abs(scene.cameraYawAfter - scene.cameraYawBefore) < .0001)
          throw new Error('Actual normal Development scene/camera witness is incomplete or mismatched.');
        evidenceHashes[scenePath] = digest(readFileSync(scenePath));
      }
      requireStoredSentinel(requireOrdinarySafePath(draftPath, target), manifest!);
      if (after[draftPath] !== report.draftSha256 || (owned[draftPath] && after[draftPath] !== owned[draftPath]))
        throw new Error('Ordinary draft hash or ownership changed.');
      owned = { ...owned, [draftPath]: report.draftSha256 };
      if (phase !== 'save') {
        requireStoredSentinel(requireOrdinarySafePath(publication, target), manifest!);
        if (after[publication] !== report.publicationSha256 || (owned[publication] && after[publication] !== owned[publication]))
          throw new Error('Ordinary publication hash or ownership changed.');
        owned[publication] = report.publicationSha256;
      }
      requireState(before, after, owned); reports[phase] = report;
    }
    verifyEvidence(); verifyInputs(); requireState(before, snapshotWorldEdit(repository), owned);
    const result: OrdinaryProofResult = { schemaVersion: 1, passed: true, runId, outputDir, reports, manifest: manifest!,
      preexistingWorldEditHashes: before, ownedWorldEditHashes: owned, fixtureAdmission: true,
      leasePath, leaseSha256, evidenceHashes, ordinaryLoginVerified: false, sharedPublication: false, visualApproved: false, gameplayApproved: false };
    writeEvidence(path.join(outputDir, 'report.json'), result); return result;
  } catch (error) {
    let after: FileHashes | undefined, preservationError: string | undefined, bindingError: string | undefined, evidenceError: string | undefined;
    try { after = snapshotWorldEdit(repository); requireWorldEditPreserved(before, after); }
    catch (failure) { preservationError = failure instanceof Error ? failure.message : String(failure); }
    try { verifyInputs(); }
    catch (failure) { bindingError = failure instanceof Error ? failure.message : String(failure); }
    try { verifyEvidence(); }
    catch (failure) { evidenceError = failure instanceof Error ? failure.message : String(failure); }
    if (existsSync(outputDir)) {
      writeEvidence(path.join(outputDir, 'failure-report.json'), { schemaVersion: 1, passed: false, runId, outputDir,
        detail: error instanceof Error ? error.message : String(error), preservationPassed: !preservationError,
        preservationError: preservationError ?? '', inputPreservationPassed: !bindingError, inputPreservationError: bindingError ?? '',
        evidencePreservationPassed: !evidenceError, evidencePreservationError: evidenceError ?? '', evidenceHashes,
        before, after: after ?? null, ownedWorldEditHashes: owned, leasePath, leaseSha256,
        fixtureAdmission: true, ordinaryLoginVerified: false, sharedPublication: false, visualApproved: false, gameplayApproved: false });
      if (after) preserveBytes(path.join(outputDir, 'failure-bytes'), repository, after);
    }
    throw new Error((error instanceof Error ? error.message : String(error))
      + (preservationError ? '; preservation failed: ' + preservationError : '')
      + (bindingError ? '; input preservation failed: ' + bindingError : '')
      + (evidenceError ? '; evidence preservation failed: ' + evidenceError : '') + '; evidence retained at ' + outputDir);
  } finally { closeSync(lease); }
}

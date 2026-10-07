import { afterEach, expect, test } from 'vitest';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import * as ordinary from '../scripts/unreal/gm-ordinary-persistence';

const roots: string[] = [];
afterEach(() => {
  for (const root of roots.splice(0)) rmSync(root, { recursive: true, force: true });
});
const sha = (bytes: string | Buffer) => createHash('sha256').update(bytes).digest('hex');
const put = (file: string, bytes: string | Buffer) => {
  mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, bytes);
};
const json = (file: string, value: unknown) => put(file, JSON.stringify(value, null, 2) + '\n');

function fixture() {
  const repository = mkdtempSync(path.join(tmpdir(), 'gm-ordinary-persistence-'));
  roots.push(repository);
  const project = path.join(repository, 'unreal/AegisWar/AegisWar.uproject');
  put(project, '{"FileVersion":3}');
  put(path.join(repository, 'mock-UnrealEditor.exe'), 'mock executable; never executed');
  const binaryPath = path.join(repository, 'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll');
  put(binaryPath, Buffer.from([0x4d, 0x5a, 0, 0xff, 0x80, 0x0d, 0x0a]));
  const sourceHashes: Record<string, string> = {};
  for (const relative of [
    'unreal/AegisWar/Source/AegisWar/AegisWar.Build.cs',
    'unreal/AegisWar/Source/AegisWar/Public/WarFixture.h',
    'unreal/AegisWar/Source/AegisWar/Private/WarFixture.cpp',
    'unreal/AegisWar/Source/AegisWarEditorTools/AegisWarEditorTools.Build.cs',
    'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarImport.cpp',
    'unreal/AegisWar/Config/DefaultEngine.ini',
    'scripts/unreal/fixture.ts', 'scripts/unreal/fixture.py', 'scripts/unreal/fixture.cs',
  ]) {
    const file = path.join(repository, relative);
    put(file, relative + '\r\n'); sourceHashes[file] = sha(readFileSync(file));
  }
  const prefix = '/Game/WorldRebuild/CitadelHumanReview_20261007_0123456789ab';
  const map = prefix + '/Walkthrough', routing = prefix + '/ReviewRouting';
  const population = prefix + '/Residents_0123456789ab';
  const city = '/Game/WorldRebuild/AegisCitadel_abcdef123456/City';
  const levels = Array.from({ length: 68 }, (_, i) => `/Game/Campaign/Zone_${i}/Scenery`);
  const packageHashes: Record<string, string> = {}, packageFiles: Record<string, string> = {};
  for (const name of [map, routing, population, city, ...levels]) {
    const file = path.join(repository, 'unreal/AegisWar/Content', name.slice(6) + (name === city ? '.uasset' : '.umap'));
    put(file, Buffer.from([0, 0xff, ...Buffer.from(name)]));
    packageFiles[name] = file; packageHashes[name] = sha(readFileSync(file));
  }
  const receipt = { schemaVersion: 1, signature: '0123456789ab' + '0'.repeat(52), sourceRevision: 'abcdef123456',
    map, routing, population, city, cityRevision: 'a'.repeat(64), mapSha256: packageHashes[map],
    packageHashes: Object.fromEntries([map, routing, population].map(name => [name, packageHashes[name]])),
    sourcePackageHashes: Object.fromEntries([city, ...levels].map(name => [name, packageHashes[name]])),
    sourcePackagesUnchanged: true, requiresDevelopmentGM: true, ordinaryLocalDevelopmentEntry: true,
    servicesRetained: true, residentPopulationPrivateReviewOnly: true,
    visualApproved: false, gameplayApproved: false, published: false,
    directedRoutes: 70, zones: 32, streamingDeclarations: [routing, population, ...levels],
    launchSelectedMapArgument: `-ini:Engine:[/Script/EngineSettings.GameMapsSettings]:GameDefaultMap=${map}` };
  const binding = { schemaVersion: 1, binaryPath, binarySha256: sha(readFileSync(binaryPath)), sourceHashes };
  const receiptPath = path.join(repository, 'proof-inputs/staged.json');
  const bindingPath = path.join(repository, 'proof-inputs/binding.json');
  json(receiptPath, receipt); json(bindingPath, binding);
  const worldEdit = path.join(repository, 'unreal/AegisWar/Saved/WorldEdit');
  const draftPath = path.join(worldEdit, 'PrivateReviews', prefix.slice('/Game/WorldRebuild/'.length), 'Walkthrough/draft.json');
  const preexistingFile = path.join(worldEdit, 'ExistingCapital/original-live.json');
  const originalBytes = Buffer.from([0xef, 0xbb, 0xbf, 0xff, 0x00, 0x80, 0xc3, 0x28, 0x0d, 0x0a]);
  put(preexistingFile, originalBytes);
  return { repository, project, receipt, binding, receiptPath, bindingPath, binaryPath, sourceHashes,
    packageHashes, packageFiles, worldEdit, draftPath, preexistingFile, originalBytes };
}

const runId = '0123456789abcdef0123456789abcdef';
const options = (f: ReturnType<typeof fixture>) => ({ repository: f.repository, receiptPath: f.receiptPath,
  bindingPath: f.bindingPath, executable: path.join(f.repository, 'mock-UnrealEditor.exe'), runId });

type Launch = Parameters<typeof ordinary.runGmOrdinaryPersistence>[1];
type LaunchRequest = Parameters<Launch>[0];
function mockedNative(f: ReturnType<typeof fixture>, change?: (request: LaunchRequest, report: any) => void) {
  const phases: string[] = [], configs: LaunchRequest['config'][] = [];
  const manifest = { schemaVersion: 1, runId, map: f.receipt.map, id: 'gm_' + '1'.repeat(32),
    templateId: 'authored_fixture', meshPath: '/Game/Models/ReviewedFixture.ReviewedFixture',
    sourceIdentity: '/Game/Models/ReviewedFixture.ReviewedFixture:' + 'b'.repeat(64), hidden: false,
    location: [100, 200, 300], rotation: [0, 0, 0, 1], scale: [1, 1, 1] };
  const row = { id: manifest.id, templateId: manifest.templateId, sourceIdentity: manifest.sourceIdentity,
    hidden: manifest.hidden, transform: [...manifest.location, ...manifest.rotation, ...manifest.scale] };
  const draft = { schemaVersion: 2, zoneId: 'aegis_capital', baseline: JSON.stringify({ objects: [] }), objects: [row] };
  const launch: Launch = async request => {
    const { phase, config, configPath } = request;
    phases.push(phase); configs.push(config);
    const publicationPath = ordinary.ordinaryPublicationPath(config.map, config.draftPath);
    if (phase === 'save') {
      expect(!existsSync(path.dirname(config.draftPath)) || readdirSync(path.dirname(config.draftPath)).length === 0).toBe(true);
      json(config.manifestPath, manifest); json(config.draftPath, draft);
    } else if (phase === 'publish') {
      expect(existsSync(publicationPath)).toBe(false);
      put(publicationPath, readFileSync(config.draftPath));
    }
    const report: any = { schemaVersion: 1, passed: true, runId, phase, map: config.map,
      configSha256: sha(readFileSync(configPath)), receiptSha256: sha(readFileSync(f.receiptPath)),
      binarySha256: f.binding.binarySha256, draftPath: config.draftPath, publicationPath,
      manifestSha256: sha(readFileSync(config.manifestPath)), draftSha256: sha(readFileSync(config.draftPath)),
      publicationSha256: phase === 'save' ? '' : sha(readFileSync(publicationPath)),
      guiOpened: phase !== 'restore', saveClicked: phase === 'save', loadClicked: phase === 'publish',
      publishClicked: phase === 'publish', startupRestored: phase === 'restore', fixtureAdmission: true,
      ordinaryLoginVerified: false, sharedPublication: false, visualApproved: false, gameplayApproved: false,
      nativePid: 101 + phases.length, detail: 'Mock filesystem evidence; no Unreal execution.' };
    change?.(request, report);
    if (f.receipt.map.endsWith('/CampaignCandidate')) json(path.join(request.outputDir, phase + '-scene.json'), {
      schemaVersion: 1, passed: true, map: f.receipt.map, phase, city: f.receipt.city, cityRevision: f.receipt.cityRevision,
      zones: 32, directedPortals: 70, decorObjects: 56, practicalLights: 34, residents: 8, mouseAxesUnattenuated: true,
      actualCameraPixelHandlerVerified: true, cameraStateRestored: true, physicalMouseHardwareVerified: false,
      cameraYawBefore: 0, cameraYawAfter: 20, cameraYawExpected: 20, cameraPitchAfter: 5, cameraPitchExpected: 5,
      fullSiegeAdmissionApproved: false, releaseAcceptance: false,
    });
    json(path.join(request.outputDir, `${phase}-report.json`), report);
    return { pid: report.nativePid, exitCode: 0, signal: null };
  };
  return { launch, phases, configs, manifest };
}

test('uses three independent ordered phases, exact ordinary paths and owned hashes while preserving raw originals', async () => {
  const f = fixture(), native = mockedNative(f), before = ordinary.snapshotWorldEdit(f.repository);
  const result = await ordinary.runGmOrdinaryPersistence(options(f), native.launch);
  expect(result).toBeDefined(); expect(native.phases).toEqual(['save', 'publish', 'restore']);
  expect(native.configs).toHaveLength(3);
  const outputDir = path.join(f.repository, 'unreal/AegisWar/Saved/WorldEditOrdinaryProof', runId);
  const publicationPath = ordinary.ordinaryPublicationPath(f.receipt.map, f.draftPath);
  const manifestSha256 = sha(readFileSync(path.join(outputDir, 'manifest.json')));
  for (const [index, config] of native.configs.entries()) {
    expect(path.resolve(config.outputDir)).toBe(outputDir); expect(path.resolve(config.draftPath)).toBe(f.draftPath);
    expect(path.resolve(config.manifestPath)).toBe(path.join(outputDir, 'manifest.json'));
    expect(path.resolve(config.receiptPath)).toBe(f.receiptPath); expect(config.receiptSha256).toBe(sha(readFileSync(f.receiptPath)));
    expect(config.packageHashes).toEqual(f.packageHashes);
    expect(config.preexistingWorldEditHashes).toEqual(Object.fromEntries(
      Object.entries(before).map(([file, hash]) => [file.replaceAll('\\', '/'), hash])));
    expect(config.publicationPath === '' ? '' : path.resolve(config.publicationPath)).toBe(index === 0 ? '' : publicationPath);
    expect(config.manifestSha256).toBe(index === 0 ? '' : manifestSha256);
    const report = JSON.parse(readFileSync(path.join(outputDir, `${config.phase}-report.json`), 'utf8'));
    expect(report.ordinaryLoginVerified).toBe(false); expect(report.fixtureAdmission).toBe(true);
    expect(report.visualApproved).toBe(false); expect(report.gameplayApproved).toBe(false);
  }
  expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
  expect(readdirSync(path.dirname(f.draftPath)).sort()).toEqual([path.basename(f.draftPath), path.basename(publicationPath)].sort());
  expect(readFileSync(f.draftPath)).toEqual(readFileSync(publicationPath));
});

function normalFixture() {
  const f = fixture(), revision = '0123456789ab', prefix = '/Game/WorldRebuild/AegisCitadel_' + revision;
  const map = prefix + '/CampaignCandidate', routing = prefix + '/CampaignRoutingCandidate';
  const population = prefix + '/Layers/Residents', city = prefix + '/City';
  const hashes: Record<string, string> = {};
  for (const name of [map, routing, population, city]) {
    const file = path.join(f.repository, 'unreal/AegisWar/Content', name.slice(6) + (name === city ? '.uasset' : '.umap'));
    put(file, name); hashes[name] = sha(readFileSync(file));
  }
  const configPath = path.join(f.repository, 'unreal/AegisWar/Config/DefaultEngine.ini');
  put(configPath, '[/Script/EngineSettings.GameMapsSettings]\r\nGameDefaultMap=' + map + '\r\n');
  f.sourceHashes[configPath] = sha(readFileSync(configPath));
  Object.assign(f.receipt, { map, routing, population, city, sourceRevision: revision,
    mapSha256: hashes[map], packageHashes: Object.fromEntries([map, routing, population].map(name => [name, hashes[name]])),
    sourcePackageHashes: { ...f.receipt.sourcePackageHashes, [city]: hashes[city] },
    streamingDeclarations: [routing, population, ...f.receipt.streamingDeclarations.slice(2)],
    residentPopulationPrivateReviewOnly: false, developmentOnly: true, defaultMapSelected: true,
    fullSiegeAdmissionApproved: false, launchSelectedMapArgument: '' });
  json(f.receiptPath, f.receipt); json(f.bindingPath, f.binding);
  f.draftPath = path.join(f.worldEdit, 'AegisCitadel_' + revision, 'draft.json');
  return f;
}

test('normal configured Development campaign uses ordinary revision storage in all three processes', async () => {
  const f = normalFixture(), map = f.receipt.map;
  const native = mockedNative(f);
  const result = await ordinary.runGmOrdinaryPersistence(options(f), async request => {
    expect(request.args.some(argument => argument.startsWith('-ini:'))).toBe(false);
    expect(request.args).not.toContain(map);
    expect(path.resolve(request.config.draftPath)).toBe(f.draftPath);
    return native.launch(request);
  });
  expect(result.passed).toBe(true); expect(native.phases).toEqual(['save', 'publish', 'restore']);
  expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
  expect(result.sharedPublication).toBe(false); expect(result.ordinaryLoginVerified).toBe(false);
});

test.each(['missing', 'city-revision', 'population', 'camera-handler', 'camera-result', 'hardware-claim', 'approval'] as const)
('normal campaign rejects scene witness %s and preserves proof-owned storage', async kind => {
  const f = normalFixture(), native = mockedNative(f);
  await expect(ordinary.runGmOrdinaryPersistence(options(f), async request => {
    const result = await native.launch(request), file = path.join(request.outputDir, request.phase + '-scene.json');
    if (kind === 'missing') rmSync(file);
    else {
      const scene = JSON.parse(readFileSync(file, 'utf8'));
      if (kind === 'city-revision') scene.cityRevision = 'f'.repeat(64);
      else if (kind === 'population') scene.residents = 7;
      else if (kind === 'camera-handler') scene.actualCameraPixelHandlerVerified = false;
      else if (kind === 'camera-result') scene.cameraYawAfter += 1;
      else if (kind === 'hardware-claim') scene.physicalMouseHardwareVerified = true;
      else scene.fullSiegeAdmissionApproved = true;
      json(file, scene);
    }
    return result;
  })).rejects.toThrow();
  expect(native.phases).toEqual(['save']); expect(existsSync(f.draftPath)).toBe(true);
  expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
});

test.each(['WarPortalProof', 'WarCapitalProof', 'WarBuilderProof', 'WarGmRenderingProof',
  'WarExpansionProof', 'WarDutchBastionProof', 'WarTargetingProof', 'WarCombatUiProof',
  'WarWorkshopProof', 'WarProofDraftId=0123456789abcdef0123456789abcdef', 'SavedDir=C:/foreign', 'UserDir=C:/foreign'])
('rejects storage redirection or conflicting mode %s', flag => {
  expect(() => ordinary.requireOrdinaryArguments(['-WarDevelopmentGM', '-WarInterfaceProof', '-WarBuilderOrdinaryProof', '-' + flag])).toThrow();
});

test('admits only the ordinary proof flags without fabricating ordinary login evidence', () => {
  expect(() => ordinary.requireOrdinaryArguments(['-WarDevelopmentGM', '-WarInterfaceProof', '-WarBuilderOrdinaryProof',
    '-WarBuilderOrdinaryConfig=C:/proof/config.json', '-game', '-windowed'])).not.toThrow();
});

test('inventories every native module, project config and Unreal tooling source by resolved path', () => {
  const f = fixture();
  expect(ordinary.sourceInventory(f.repository).sort()).toEqual(Object.keys(f.sourceHashes).sort());
  const later = path.join(f.repository, 'unreal/AegisWar/Source/AegisWar/Private/AddedAfterBinding.inl');
  put(later, 'new source');
  expect(ordinary.sourceInventory(f.repository)).toContain(later);
  put(path.join(f.repository, 'scripts/unreal/not-source.json'), '{}');
  expect(ordinary.sourceInventory(f.repository)).not.toContain(path.join(f.repository, 'scripts/unreal/not-source.json'));
});

test('matches the production four-byte character CRC publication filename', () => {
  const f = fixture();
  expect(ordinary.ordinaryPublicationPath(f.receipt.map, f.draftPath)).toBe(
    path.join(path.dirname(f.draftPath), 'Walkthrough-fa0b2214-live.json'));
});

test('snapshots raw WorldEdit bytes and rejects changes or disappearance without repairing either', () => {
  const f = fixture(), before = ordinary.snapshotWorldEdit(f.repository);
  expect(before[f.preexistingFile]).toBe(sha(f.originalBytes));
  expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
  expect(() => ordinary.requireWorldEditPreserved(before, ordinary.snapshotWorldEdit(f.repository))).not.toThrow();
  const changed = Buffer.from([0xff, 0, 0x81, 0x0a]);
  put(f.preexistingFile, changed);
  expect(() => ordinary.requireWorldEditPreserved(before, ordinary.snapshotWorldEdit(f.repository))).toThrow();
  expect(readFileSync(f.preexistingFile)).toEqual(changed);
  rmSync(f.preexistingFile);
  expect(() => ordinary.requireWorldEditPreserved(before, ordinary.snapshotWorldEdit(f.repository))).toThrow();
  expect(existsSync(f.preexistingFile)).toBe(false);
});

test('refuses a source junction instead of binding bytes outside the source tree', () => {
  const f = fixture(), other = mkdtempSync(path.join(tmpdir(), 'gm-ordinary-external-'));
  roots.push(other); put(path.join(other, 'Foreign.h'), 'foreign source');
  symlinkSync(other, path.join(f.repository, 'unreal/AegisWar/Source/AegisWar/Public/Escape'), 'junction');
  expect(() => ordinary.sourceInventory(f.repository)).toThrow();
  expect(readFileSync(path.join(other, 'Foreign.h'), 'utf8')).toBe('foreign source');
});

test('refuses a WorldEdit junction and does not read or alter its external draft', () => {
  const f = fixture(), other = mkdtempSync(path.join(tmpdir(), 'gm-ordinary-external-storage-'));
  roots.push(other); const file = path.join(other, 'foreign-draft.json'), bytes = Buffer.from([0xff, 0, 0x80]);
  put(file, bytes); symlinkSync(other, path.join(f.worldEdit, 'EscapedStorage'), 'junction');
  expect(() => ordinary.snapshotWorldEdit(f.repository)).toThrow();
  expect(readFileSync(file)).toEqual(bytes);
});

test('refuses a dangling WorldEdit junction even though existsSync cannot follow it', () => {
  const f = fixture(), link = path.join(f.worldEdit, 'DanglingStorage');
  symlinkSync(path.join(f.repository, 'missing-storage'), link, 'junction');
  expect(existsSync(link)).toBe(false);
  expect(() => ordinary.snapshotWorldEdit(f.repository)).toThrow();
  expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
});

test.each(['draft.json', 'Walkthrough-deadbeef-live.json', 'draft.json.lock',
  'draft.json.0123456789abcdef.tmp', 'unexpected.bin'])('refuses occupied ordinary storage: %s', async name => {
  const f = fixture(), occupied = path.join(path.dirname(f.draftPath), name);
  const bytes = Buffer.from([0xff, 0, 0x8f, ...Buffer.from(name)]); put(occupied, bytes);
  let launches = 0;
  await expect(ordinary.runGmOrdinaryPersistence(options(f), async () => {
    ++launches; throw new Error('The occupied target must be rejected before launch.');
  })).rejects.toThrow();
  expect(launches).toBe(0);
  expect(readFileSync(occupied)).toEqual(bytes);
  expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
});

test.each([
  ['changed binary', (f: ReturnType<typeof fixture>) => put(f.binaryPath, 'replacement binary')],
  ['changed runtime source', (f: ReturnType<typeof fixture>) => put(Object.keys(f.sourceHashes).find(p => p.endsWith('WarFixture.cpp'))!, 'new native behavior')],
  ['changed config', (f: ReturnType<typeof fixture>) => put(Object.keys(f.sourceHashes).find(p => p.endsWith('DefaultEngine.ini'))!, 'new config')],
  ['changed tooling source', (f: ReturnType<typeof fixture>) => put(Object.keys(f.sourceHashes).find(p => p.endsWith('fixture.py'))!, 'new script')],
  ['changed owned native map', (f: ReturnType<typeof fixture>) => put(f.packageFiles[f.receipt.map], 'new native map')],
  ['changed protected native city', (f: ReturnType<typeof fixture>) => put(f.packageFiles[f.receipt.city], 'new city')],
  ['missing source binding', (f: ReturnType<typeof fixture>) => { delete f.binding.sourceHashes[Object.keys(f.sourceHashes)[0]]; json(f.bindingPath, f.binding); }],
  ['new unbound native source', (f: ReturnType<typeof fixture>) => put(path.join(f.repository, 'unreal/AegisWar/Source/AegisWar/Public/Unbound.hpp'), 'not in binding')],
  ['missing EditorTools module', (f: ReturnType<typeof fixture>) => {
    const module = path.join(f.repository, 'unreal/AegisWar/Source/AegisWarEditorTools');
    rmSync(module, { recursive: true });
    for (const file of Object.keys(f.binding.sourceHashes)) if (file.startsWith(module + path.sep)) delete f.binding.sourceHashes[file];
    json(f.bindingPath, f.binding);
  }],
  ['foreign source binding', (f: ReturnType<typeof fixture>) => { const file = path.join(f.repository, 'foreign.cpp');
    put(file, 'foreign'); f.binding.sourceHashes[file] = sha(readFileSync(file)); json(f.bindingPath, f.binding); }],
  ['binary outside project Binaries', (f: ReturnType<typeof fixture>) => { const file = path.join(f.repository, 'foreign/UnrealEditor-AegisWar.dll');
    put(file, readFileSync(f.binaryPath)); f.binding.binaryPath = file; json(f.bindingPath, f.binding); }],
  ['receipt broader approval', (f: ReturnType<typeof fixture>) => { f.receipt.visualApproved = true; json(f.receiptPath, f.receipt); }],
] as const)('rejects %s before launcher admission', async (_name, change) => {
  const f = fixture(); change(f);
  let launches = 0;
  await expect(ordinary.runGmOrdinaryPersistence(options(f), async () => {
    ++launches; throw new Error('Invalid bindings must be rejected before launch.');
  })).rejects.toThrow();
  expect(launches).toBe(0);
  expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
  expect(existsSync(f.draftPath)).toBe(false);
});

test.each([
  ['wrong run', (r: any) => { r.runId = 'f'.repeat(32); }],
  ['wrong phase', (r: any) => { r.phase = 'restore'; }],
  ['wrong map', (r: any) => { r.map += '_Other'; }],
  ['wrong config hash', (r: any) => { r.configSha256 = '0'.repeat(64); }],
  ['wrong receipt hash', (r: any) => { r.receiptSha256 = '0'.repeat(64); }],
  ['wrong binary hash', (r: any) => { r.binarySha256 = '0'.repeat(64); }],
  ['wrong manifest hash', (r: any) => { r.manifestSha256 = '0'.repeat(64); }],
  ['wrong draft hash', (r: any) => { r.draftSha256 = '0'.repeat(64); }],
  ['foreign draft path', (r: any) => { r.draftPath += '.other'; }],
  ['foreign publication path', (r: any) => { r.publicationPath += '.other'; }],
  ['save falsely published', (r: any) => { r.publicationSha256 = 'a'.repeat(64); }],
  ['failed native result', (r: any) => { r.passed = false; }],
  ['missing GUI witness', (r: any) => { r.guiOpened = false; }],
  ['missing save witness', (r: any) => { r.saveClicked = false; }],
  ['unused load witness', (r: any) => { r.loadClicked = true; }],
  ['ordinary login claim', (r: any) => { r.ordinaryLoginVerified = true; }],
  ['visual approval claim', (r: any) => { r.visualApproved = true; }],
  ['gameplay approval claim', (r: any) => { r.gameplayApproved = true; }],
  ['shared publication claim', (r: any) => { r.sharedPublication = true; }],
  ['missing fixture disclosure', (r: any) => { r.fixtureAdmission = false; }],
] as const)('rejects phase report with %s and retains the new owned files', async (_name, mutate) => {
  const f = fixture(), native = mockedNative(f, (_request, report) => mutate(report));
  await expect(ordinary.runGmOrdinaryPersistence(options(f), native.launch)).rejects.toThrow();
  expect(native.phases).toEqual(['save']);
  expect(existsSync(f.draftPath)).toBe(true);
  expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
});

test.each(['binary', 'source', 'package', 'receipt', 'config', 'original', 'unexpected-file', 'leftover-lock', 'leftover-temp'] as const)
('rejects %s mutation during a launch, stops later phases, and preserves evidence', async kind => {
  const f = fixture(); let changedFile = '', changedBytes = Buffer.from([0xff, 0, 0x82, 0x0a]);
  const native = mockedNative(f, (request, _report) => {
    changedFile = kind === 'binary' ? f.binaryPath : kind === 'source' ? Object.keys(f.sourceHashes)[0]
      : kind === 'package' ? f.packageFiles[f.receipt.city] : kind === 'receipt' ? f.receiptPath
      : kind === 'config' ? request.configPath : kind === 'original' ? f.preexistingFile
      : path.join(path.dirname(f.draftPath), kind === 'leftover-lock' ? 'draft.json.lock'
        : kind === 'leftover-temp' ? 'draft.json.unfinished.tmp' : 'unowned.bin');
    put(changedFile, changedBytes);
  });
  await expect(ordinary.runGmOrdinaryPersistence(options(f), native.launch)).rejects.toThrow();
  expect(native.phases).toEqual(['save']);
  expect(readFileSync(changedFile)).toEqual(changedBytes);
  expect(existsSync(f.draftPath)).toBe(true);
  if (kind !== 'original') expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
});

test.each([
  ['wrong schema', (m: any) => { m.schemaVersion = 2; }],
  ['wrong run', (m: any) => { m.runId = 'f'.repeat(32); }],
  ['wrong map', (m: any) => { m.map += '_Other'; }],
  ['missing id', (m: any) => { delete m.id; }],
  ['wrong template', (m: any) => { m.templateId = 'another_template'; }],
  ['wrong provenance', (m: any) => { m.sourceIdentity = m.meshPath + ':' + 'c'.repeat(64); }],
  ['non-Game mesh', (m: any) => { m.meshPath = '/Engine/BasicShapes/Cube.Cube'; }],
  ['hidden sentinel', (m: any) => { m.hidden = true; }],
  ['wrong position', (m: any) => { m.location[0] += 1; }],
  ['nonunit quaternion', (m: any) => { m.rotation = [0, 0, 0, 2]; }],
  ['zero scale', (m: any) => { m.scale[0] = 0; }],
] as const)('rejects a freshly hashed manifest with %s instead of trusting the hash alone', async (_name, mutate) => {
  const f = fixture(), native = mockedNative(f, (request, report) => {
    const manifest = JSON.parse(readFileSync(request.config.manifestPath, 'utf8'));
    mutate(manifest); json(request.config.manifestPath, manifest);
    report.manifestSha256 = sha(readFileSync(request.config.manifestPath));
  });
  await expect(ordinary.runGmOrdinaryPersistence(options(f), native.launch)).rejects.toThrow();
  expect(native.phases).toEqual(['save']); expect(existsSync(f.draftPath)).toBe(true);
});

test.each(['missing', 'duplicate', 'template', 'source', 'hidden', 'transform'] as const)
('rejects saved sentinel %s mismatch even when the report gives its actual draft hash', async kind => {
  const f = fixture(), native = mockedNative(f, (request, report) => {
    const draft = JSON.parse(readFileSync(request.config.draftPath, 'utf8'));
    if (kind === 'missing') draft.objects = [];
    else if (kind === 'duplicate') draft.objects.push({ ...draft.objects[0] });
    else if (kind === 'template') draft.objects[0].templateId = 'other';
    else if (kind === 'source') draft.objects[0].sourceIdentity += 'other';
    else if (kind === 'hidden') draft.objects[0].hidden = true;
    else draft.objects[0].transform[0] += 1;
    json(request.config.draftPath, draft); report.draftSha256 = sha(readFileSync(request.config.draftPath));
  });
  await expect(ordinary.runGmOrdinaryPersistence(options(f), native.launch)).rejects.toThrow();
  expect(native.phases).toEqual(['save']); expect(existsSync(f.draftPath)).toBe(true);
});

test('rejects a reused native PID rather than accepting three reports from one process', async () => {
  const f = fixture(), native = mockedNative(f, (_request, report) => { report.nativePid = 100; });
  await expect(ordinary.runGmOrdinaryPersistence(options(f), native.launch)).rejects.toThrow();
  expect(native.phases).toEqual(['save', 'publish']);
  expect(existsSync(ordinary.ordinaryPublicationPath(f.receipt.map, f.draftPath))).toBe(true);
});

test('requires the report native PID to match the launcher process identity', async () => {
  const f = fixture(), native = mockedNative(f);
  await expect(ordinary.runGmOrdinaryPersistence(options(f), async request => {
    const result = await native.launch(request); return { ...result, pid: result.pid + 1000 };
  })).rejects.toThrow();
  expect(native.phases).toEqual(['save']);
});

test.each(['publication-hash', 'missing-load', 'manifest-rewrite', 'startup-false', 'restore-gui'] as const)
('rejects later-phase evidence %s', async kind => {
  const f = fixture(), native = mockedNative(f, (request, report) => {
    if (request.phase === 'publish' && kind === 'publication-hash') report.publicationSha256 = 'f'.repeat(64);
    if (request.phase === 'publish' && kind === 'missing-load') report.loadClicked = false;
    if (request.phase === 'publish' && kind === 'manifest-rewrite') {
      put(request.config.manifestPath, readFileSync(request.config.manifestPath, 'utf8') + '\n');
      report.manifestSha256 = sha(readFileSync(request.config.manifestPath));
    }
    if (request.phase === 'restore' && kind === 'startup-false') report.startupRestored = false;
    if (request.phase === 'restore' && kind === 'restore-gui') report.guiOpened = true;
  });
  await expect(ordinary.runGmOrdinaryPersistence(options(f), native.launch)).rejects.toThrow();
  expect(native.phases).toEqual(kind === 'startup-false' || kind === 'restore-gui'
    ? ['save', 'publish', 'restore'] : ['save', 'publish']);
  expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
});

test.each(['save-report.json', 'save-config.json'])
('rejects raw prior evidence tamper in %s during a later native phase', async name => {
  const f = fixture(); let changedFile = '', changedBytes: Buffer | undefined;
  const native = mockedNative(f, (request, _report) => {
    if (request.phase !== 'publish') return;
    changedFile = path.join(request.outputDir, name);
    changedBytes = Buffer.concat([readFileSync(changedFile), Buffer.from('\n')]);
    put(changedFile, changedBytes);
  });
  await expect(ordinary.runGmOrdinaryPersistence(options(f), native.launch)).rejects.toThrow();
  expect(native.phases).toEqual(['save', 'publish']);
  expect(readFileSync(changedFile)).toEqual(changedBytes);
  const report = JSON.parse(readFileSync(path.join(f.repository, 'unreal/AegisWar/Saved/WorldEditOrdinaryProof', runId,
    'failure-report.json'), 'utf8'));
  expect(report.passed).toBe(false); expect(report.evidencePreservationPassed).toBe(false);
  expect(report.evidencePreservationError).toMatch(/evidence|changed|bound/i);
  expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
});

test('checks preservation when the launcher itself throws and retains the unexpected changed bytes', async () => {
  const f = fixture(), changed = Buffer.from([0xff, 0, 0x91, 0x0d]);
  let failure: unknown;
  try {
    await ordinary.runGmOrdinaryPersistence(options(f), async () => {
      put(f.preexistingFile, changed); throw new Error('mock process crashed');
    });
  } catch (error) { failure = error; }
  expect(failure).toBeInstanceOf(Error);
  expect(String(failure)).toMatch(/preserv|WorldEdit|original/i);
  expect(readFileSync(f.preexistingFile)).toEqual(changed);
});

test.each(['binary', 'source', 'package'] as const)
('checks %s input preservation when the launcher throws', async kind => {
  const f = fixture(), changed = Buffer.from([0xff, 0, 0x92, 0x0d]);
  const changedFile = kind === 'binary' ? f.binaryPath : kind === 'source' ? Object.keys(f.sourceHashes)[0]
    : f.packageFiles[f.receipt.city];
  await expect(ordinary.runGmOrdinaryPersistence(options(f), async () => {
    put(changedFile, changed); throw new Error('mock process crashed');
  })).rejects.toThrow();
  const report = JSON.parse(readFileSync(path.join(f.repository, 'unreal/AegisWar/Saved/WorldEditOrdinaryProof', runId,
    'failure-report.json'), 'utf8'));
  expect(report.passed).toBe(false); expect(report.inputPreservationPassed).toBe(false);
  expect(report.inputPreservationError).toMatch(/changed|binding|native|source/i);
  expect(readFileSync(changedFile)).toEqual(changed);
  expect(readFileSync(f.preexistingFile)).toEqual(f.originalBytes);
});

test('rejects a process failure despite a success-shaped report and preserves its owned draft', async () => {
  const f = fixture(), native = mockedNative(f);
  await expect(ordinary.runGmOrdinaryPersistence(options(f), async request => {
    const result = await native.launch(request); return { ...result, exitCode: 7 };
  })).rejects.toThrow();
  expect(native.phases).toEqual(['save']); expect(existsSync(f.draftPath)).toBe(true);
});

test('reads only the exact phase report path; a success report at another path is insufficient', async () => {
  const f = fixture(), native = mockedNative(f);
  await expect(ordinary.runGmOrdinaryPersistence(options(f), async request => {
    const result = await native.launch(request);
    const file = path.join(request.outputDir, `${request.phase}-report.json`);
    put(path.join(request.outputDir, 'unrelated-report.json'), readFileSync(file)); rmSync(file);
    return result;
  })).rejects.toThrow();
  expect(native.phases).toEqual(['save']); expect(existsSync(f.draftPath)).toBe(true);
});

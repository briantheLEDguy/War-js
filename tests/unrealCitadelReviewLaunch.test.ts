import { expect, test } from 'vitest';
import { createHash } from 'node:crypto';
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { citadelReviewArguments } from '../scripts/unreal/citadel-review-launch';

test('launch binds preserved native bytes and the exact private map without granting approval or altering configuration', () => {
  const root = mkdtempSync(path.join(os.tmpdir(), 'citadel-review-launch-'));
  try {
    const prefix = '/Game/WorldRebuild/CitadelHumanReview_20261007_0123456789ab';
    const map = prefix + '/Walkthrough', routing = prefix + '/ReviewRouting', population = prefix + '/Residents_0123456789ab';
    const city = '/Game/WorldRebuild/AegisCitadel_abcdef123456/City';
    const levels = Array.from({ length: 71 }, (_, i) => `/Game/Campaign/Zone_${i}/Scenery`);
    const hashes: Record<string, string> = {}, files: Record<string, string> = {};
    for (const name of [map, routing, population, city, ...levels]) {
      const file = path.join(root, 'unreal/AegisWar/Content', name.slice(6) + (name === city ? '.uasset' : '.umap'));
      mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, name);
      files[name] = file; hashes[name] = createHash('sha256').update(name).digest('hex');
    }
    const receipt = { schemaVersion: 1, signature: '0123456789ab' + '0'.repeat(52), sourceRevision: 'abcdef123456',
      map, routing, population, city, cityRevision: 'a'.repeat(64), mapSha256: hashes[map],
      packageHashes: Object.fromEntries([map, routing, population].map(name => [name, hashes[name]])),
      sourcePackageHashes: Object.fromEntries([city, ...levels].map(name => [name, hashes[name]])), sourcePackagesUnchanged: true,
      requiresDevelopmentGM: true, ordinaryLocalDevelopmentEntry: true, servicesRetained: true,
      residentPopulationPrivateReviewOnly: true, visualApproved: false, gameplayApproved: false, published: false,
      directedRoutes: 70, zones: 32, streamingDeclarations: [routing, population, ...levels],
      launchSelectedMapArgument: `-ini:Engine:[/Script/EngineSettings.GameMapsSettings]:GameDefaultMap=${map}` };
    const make = (r: any = receipt) => citadelReviewArguments(root, r, '/project.uproject');
    expect(make()).toContain(receipt.launchSelectedMapArgument);
    expect(make().filter(arg => arg.includes('GameDefaultMap'))).toHaveLength(1);
    expect(() => make({ ...receipt, streamingDeclarations: [...receipt.streamingDeclarations, levels[0]] })).not.toThrow();
    for (const mutate of [
      (r: any) => { r.map = '/Game/Capitals/aegis_capital/AegisCapital_Workbench'; },
      (r: any) => { r.map = r.map.replace('20261007', '20260230'); },
      (r: any) => { r.routing = '/Game/Foreign/Routing'; },
      (r: any) => { r.population = prefix + '/Population'; },
      (r: any) => { r.directedRoutes = 68; },
      (r: any) => { r.streamingDeclarations = 73; },
      (r: any) => { r.streamingDeclarations = ['unprotected']; },
      (r: any) => { r.streamingDeclarations.pop(); delete r.sourcePackageHashes[levels[0]]; },
      (r: any) => { r.streamingDeclarations[2] = '/Game/Foreign/Scenery'; },
      (r: any) => { r.streamingDeclarations = r.streamingDeclarations.filter((p: string) => p !== population); },
      (r: any) => { r.streamingDeclarations.push(map); },
      (r: any) => { r.sourcePackagesUnchanged = false; },
      (r: any) => { delete r.sourcePackageHashes[city]; },
      (r: any) => { r.launchSelectedMapArgument += ' -WarDevelopmentGM'; },
    ]) { const changed = structuredClone(receipt); mutate(changed); expect(() => make(changed)).toThrow(); }
    for (const name of [city, routing, map]) {
      writeFileSync(files[name], 'independently changed native work');
      expect(make).toThrow(/dependency changed/);
      writeFileSync(files[name], name);
    }
  } finally { rmSync(root, { recursive: true, force: true }); }
});

test('normal Development launch uses the configured campaign without map overrides or approval', () => {
  const root = mkdtempSync(path.join(os.tmpdir(), 'citadel-development-launch-'));
  try {
    const revision = '0123456789ab', prefix = '/Game/WorldRebuild/AegisCitadel_' + revision;
    const map = prefix + '/CampaignCandidate', routing = prefix + '/CampaignRoutingCandidate';
    const population = prefix + '/Layers/Residents', city = prefix + '/City';
    const levels = Array.from({ length: 68 }, (_, i) => `/Game/Campaign/Zone_${i}/Scenery`);
    const hashes: Record<string, string> = {};
    for (const name of [map, routing, population, city, ...levels]) {
      const file = path.join(root, 'unreal/AegisWar/Content', name.slice(6) + (name === city ? '.uasset' : '.umap'));
      mkdirSync(path.dirname(file), { recursive: true }); writeFileSync(file, name);
      hashes[name] = createHash('sha256').update(name).digest('hex');
    }
    const config = path.join(root, 'unreal/AegisWar/Config/DefaultEngine.ini');
    mkdirSync(path.dirname(config), { recursive: true });
    writeFileSync(config, '[/Script/EngineSettings.GameMapsSettings]\r\nGameDefaultMap=' + map + '\r\n');
    const receipt = { schemaVersion: 1, signature: revision + '0'.repeat(52), sourceRevision: revision,
      map, routing, population, city, cityRevision: 'a'.repeat(64), mapSha256: hashes[map],
      packageHashes: Object.fromEntries([map, routing, population].map(name => [name, hashes[name]])),
      sourcePackageHashes: Object.fromEntries([city, ...levels].map(name => [name, hashes[name]])), sourcePackagesUnchanged: true,
      requiresDevelopmentGM: true, ordinaryLocalDevelopmentEntry: true, servicesRetained: true,
      residentPopulationPrivateReviewOnly: false, visualApproved: false, gameplayApproved: false, published: false,
      directedRoutes: 70, zones: 32, streamingDeclarations: [routing, population, ...levels],
      developmentOnly: true, defaultMapSelected: true, fullSiegeAdmissionApproved: false, launchSelectedMapArgument: '' };
    const make = (value: any = receipt) => citadelReviewArguments(root, value, '/project.uproject');
    expect(make()).not.toContain(map);
    expect(make().some(argument => argument.includes('GameDefaultMap=') || argument.startsWith('-ini:'))).toBe(false);
    for (const changed of [{ developmentOnly: false }, { defaultMapSelected: false },
      { fullSiegeAdmissionApproved: true }, { residentPopulationPrivateReviewOnly: true },
      { launchSelectedMapArgument: '-ini:Engine:GameDefaultMap=' + map }, { sourceRevision: 'abcdef123456' }])
      expect(() => make({ ...receipt, ...changed })).toThrow();
    writeFileSync(config, 'GameDefaultMap=/Game/Other\n'); expect(make).toThrow(/configured default/);
    writeFileSync(config, 'GameDefaultMap=' + map + '\nGameDefaultMap=' + map + '\n'); expect(make).toThrow(/configured default/);
  } finally { rmSync(root, { recursive: true, force: true }); }
});

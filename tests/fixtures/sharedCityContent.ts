import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';

export function sharedCityFixture(root: string) {
  const json = (file: string, value: unknown) => {
    const target = path.join(root, file); mkdirSync(path.dirname(target), { recursive: true });
    writeFileSync(target, JSON.stringify(value));
  };
  const pkg = (name: string) => {
    const target = path.join(root, 'unreal/AegisWar/Content', `${name.slice(6)}.umap`);
    mkdirSync(path.dirname(target), { recursive: true }); writeFileSync(target, name);
    return createHash('sha256').update(name).digest('hex');
  };
  const cities = ['aegis_capital', 'riftspire_capital'].map(id => {
    const scene = `/Game/${id}/Scenery`, game = `/Game/${id}/Gameplay`, definition = `/Game/${id}/City`, model = `/Game/${id}/Model`;
    return { id, definition, revision: 'current', origin: [0, 0, 0], sceneryLevels: [scene], gameplayLevels: [game],
      packageHashes: { [scene]: pkg(scene), [game]: pkg(game), [definition]: pkg(definition) }, dependencyHashes: { [model]: pkg(model) } };
  });
  const build = { map: '/Game/Campaign', layer: '/Game/Routing', partitionManifest: 'active.json' };
  const manifest = { zones: cities.map(city => ({ id: city.id, origin: city.origin, cityDefinition: city.definition,
    cityRevision: city.revision, levels: { scenery: city.sceneryLevels[0], gameplay: city.gameplayLevels[0] } })) };
  const receipt = { schemaVersion: 1, campaignMap: build.map, cities, campaignHashes: { [build.map]: pkg(build.map), [build.layer]: pkg(build.layer) } };
  const siege = { version: 2, revision: cities[0].revision, cityDefinition: cities[0].definition, layers: cities[0].sceneryLevels,
    map: '/Game/Capitals/Siege/AegisCapital_Siege', mapSha256: pkg('/Game/Capitals/Siege/AegisCapital_Siege'), navigationVerified: true, visualVerified: true };
  mkdirSync(path.join(root, 'unreal/AegisWar/Config'), { recursive: true });
  writeFileSync(path.join(root, 'unreal/AegisWar/Config/DefaultEngine.ini'), `GameDefaultMap=${build.map}\n`);
  const save = () => {
    json('artifacts/unreal/world-portals/build.json', build); json('artifacts/unreal/world-portals/active.json', manifest);
    json('artifacts/unreal/shared-cities/current.json', receipt); json('artifacts/unreal/scenario-queues/capital-scenery.json', siege);
  };
  save(); return { build, manifest, receipt, siege, save };
}

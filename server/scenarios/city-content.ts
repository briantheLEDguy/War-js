import { createHash } from 'node:crypto';
import { readFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { requireNativePackageHash, REVIEWED_CITADEL_ENGINE_SOURCE } from '../../scripts/unreal/native-package-evidence';

export interface SharedCity {
  id: string;
  definition: string;
  revision: string;
  origin: number[];
  sceneryLevels: string[];
  gameplayLevels: string[];
  packageHashes: Record<string, string>;
  dependencyHashes: Record<string, string>;
}

function child(root: string, relative: string) {
  if (!relative || relative.includes('\\') || relative.includes(':') || path.isAbsolute(relative)
      || relative.split('/').some(part => !part || part === '.' || part === '..')) throw new Error('Invalid city content path.');
  const result = path.resolve(root, relative);
  if (!result.startsWith(path.resolve(root) + path.sep)) throw new Error('Invalid city content path.');
  return result;
}

export function verifyCityPackages(repository: string, hashes: Record<string, string>, preservedDependencies = false, engineRoot?: string) {
  if (!hashes || !Object.keys(hashes).length) throw new Error('City package evidence is missing.');
  for (const [name, expected] of Object.entries(hashes)) {
    if (name.startsWith('/Engine/')) {
      if (!preservedDependencies || name !== REVIEWED_CITADEL_ENGINE_SOURCE) throw new Error('Engine city ownership or an unreviewed Engine dependency is forbidden.');
      requireNativePackageHash(repository, name, expected, engineRoot);
      continue;
    }
    if (!name.startsWith('/Game/') || !/^[a-f0-9]{64}$/.test(expected)) throw new Error('Invalid city package evidence.');
    const base = child(path.join(repository, 'unreal/AegisWar/Content'), name.slice(6));
    const file = ['.umap', '.uasset'].map(extension => base + extension).find(existsSync);
    if (!file || createHash('sha256').update(readFileSync(file)).digest('hex') !== expected)
      throw new Error(`Shared city content is stale or missing: ${name}. Run npm run unreal:city-sync and repeat affected reviews.`);
  }
}

/** Compare against live routing as well as bytes; old but intact receipts must fail. */
export function verifySharedCities(repository: string, engineRoot?: string): SharedCity[] {
  const read = (relative: string) => JSON.parse(readFileSync(child(repository, relative), 'utf8'));
  const build = read('artifacts/unreal/world-portals/build.json');
  const manifest = read(`artifacts/unreal/world-portals/${build.partitionManifest}`);
  const receipt = read('artifacts/unreal/shared-cities/current.json');
  const defaults = readFileSync(path.join(repository, 'unreal/AegisWar/Config/DefaultEngine.ini'), 'utf8')
    .split(/\r?\n/).filter(line => line.startsWith('GameDefaultMap='))
    .map(line => line.slice('GameDefaultMap='.length).trim().split('.')[0]);
  if (defaults.length !== 1 || defaults[0] !== build.map || receipt.campaignMap !== build.map || receipt.schemaVersion !== 1
      || !Array.isArray(receipt.cities) || receipt.cities.map((city: SharedCity) => city.id).join(',') !== 'aegis_capital,riftspire_capital')
    throw new Error('Shared city routing is stale or incomplete. Run npm run unreal:city-sync.');
  const cities = receipt.cities as SharedCity[];
  for (const city of cities) {
    const zone = manifest.zones.find((entry: { id: string }) => entry.id === city.id);
    const all = [...city.sceneryLevels, ...city.gameplayLevels];
    if (!zone || !city.revision || !city.sceneryLevels.length || new Set(all).size !== all.length
        || zone.cityDefinition !== city.definition || zone.cityRevision !== city.revision
        || JSON.stringify(zone.origin) !== JSON.stringify(city.origin)
        || JSON.stringify(Object.values(zone.levels).sort()) !== JSON.stringify([...all].sort())
        || [city.definition, ...all].some(name => !city.packageHashes[name]))
      throw new Error(`Shared city routing is stale or duplicated: ${city.id}.`);
    verifyCityPackages(repository, city.packageHashes);
    if (!city.dependencyHashes || !Object.keys(city.dependencyHashes).length) throw new Error('City model dependency evidence is missing.');
    verifyCityPackages(repository, city.dependencyHashes, true, engineRoot);
  }
  if (!receipt.campaignHashes[build.map] || !receipt.campaignHashes[build.layer]) throw new Error('City routing package evidence is missing.');
  verifyCityPackages(repository, receipt.campaignHashes);
  return cities;
}

/** Lower-city receipts cannot approve a new ruleset or live-capital authority. */
export function verifyFullCapitalSiege(repository: string): string {
  const city = verifySharedCities(repository).find(row => row.id === 'aegis_capital')!;
  const receipt = JSON.parse(readFileSync(child(repository, 'artifacts/unreal/citadel-siege/full-siege-approval.json'), 'utf8'));
  const checks = ['geometryVerified', 'navigationVerified', 'traversalVerified', 'visualVerified',
    'rulesVerified', 'liveCapitalVerified', 'scenarioVerified', 'evacuationVerified'];
  if (receipt.version !== 1 || receipt.rulesVersion !== 2 || receipt.battlefieldDefinitionVersion !== 2
    || receipt.revision !== city.revision || receipt.capacity !== 18 || receipt.objectiveCount !== 8 || receipt.optionalCount !== 3
    || !/^[a-f0-9]{64}$/.test(receipt.routePlanSha256 ?? '') || checks.some(key => receipt[key] !== true))
    throw new Error('Full capital siege proof is missing, stale or incomplete. Repeat the native route, gameplay and visual reviews.');
  const routePlan = child(repository, 'artifacts/unreal/citadel-siege/route-plan.json');
  if (createHash('sha256').update(readFileSync(routePlan)).digest('hex') !== receipt.routePlanSha256)
    throw new Error('Full capital siege route proof is stale.');
  verifyCityPackages(repository, receipt.packageHashes);
  if (!receipt.packageHashes['/Game/Capitals/Siege/AegisCapital_Siege']) throw new Error('Full siege scenario package proof is missing.');
  return city.revision;
}

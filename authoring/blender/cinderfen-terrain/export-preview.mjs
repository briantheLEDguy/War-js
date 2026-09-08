import fs from 'node:fs/promises';
import { composeCinderfenEnvironment, loadCinderfenContracts } from '../../../scripts/campaign/cinderfen-environment.mjs';
import { composeCinderfenLandscape } from '../../../scripts/campaign/cinderfen-landscape.mjs';
import { integrateCinderfen } from '../../../scripts/campaign/cinderfen-integration.mjs';
const read = async file => JSON.parse(await fs.readFile(file, 'utf8'));
const contracts = loadCinderfenContracts({ staged: true });
const zone = integrateCinderfen(composeCinderfenEnvironment(composeCinderfenLandscape(await read('public/assets/maps/cinderfen_outskirts.json')),
  { architecture: true }, { contracts }));
const registry = (await read('public/assets/models/asset-index.json')).staticProps;
const assets = {};
for (const [key, contract] of Object.entries(contracts)) {
  const folder = key.endsWith('corner_access') ? '../cinderfen-architecture/junction/runtime/' : '../cinderfen-architecture/runtime/';
  assets[key] = { lods: contract.lods.map(lod => ({ url: folder + lod.model, sha256: lod.sha256 })) };
}
const props = zone.props.filter(prop => assets[prop.assetKey ?? prop.kind]);
for (const prop of zone.props) {
  const key = prop.assetKey ?? prop.kind, asset = registry[key];
  if (assets[key] || !asset?.runtimeReady || asset.approvalState !== 'approved' || !asset.modelSha256) continue;
  assets[key] = { lods: [{ url: '/assets/models/' + asset.model, sha256: asset.modelSha256 }] };
  props.push(...zone.props.filter(entry => (entry.assetKey ?? entry.kind) === key));
}
await fs.writeFile('authoring/blender/cinderfen-terrain/review/zone-preview.json', JSON.stringify({
  zoneId: zone.id, status: 'staged', assets, props,
  terrain: await read('authoring/blender/cinderfen-terrain/build-report.json'),
}, null, 2) + '\n');
console.log(`Prepared staged composition: ${props.length} props and sixteen terrain sectors.`);

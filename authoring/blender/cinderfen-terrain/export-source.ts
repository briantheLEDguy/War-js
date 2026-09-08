import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { orvrHeightAt } from '../../../src/shared/orvrTerrain';
import { composeCinderfenLandscape } from '../../../scripts/campaign/cinderfen-landscape.mjs';

const zone = composeCinderfenLandscape(JSON.parse(await readFile('public/assets/maps/cinderfen_outskirts.json', 'utf8')));
const { size, segments } = zone;
const terrain = structuredClone(zone.orvrLayout.terrain);
for (const chunk of terrain.chunks) chunk.status = 'planned';
const heights = Array.from({ length: (segments + 1) ** 2 }, (_, index) => Math.fround(orvrHeightAt(
  terrain, (index % (segments + 1)) / segments * size - size / 2,
  Math.floor(index / (segments + 1)) / segments * size - size / 2,
)));
const source = { zoneId: zone.id, size, segments, terrain, paths: zone.paths, heights, waterLevel: -.35 };
const sourceSha256 = createHash('sha256').update(JSON.stringify(source)).digest('hex');
await writeFile('authoring/blender/cinderfen-terrain/terrain-source.json', JSON.stringify({ ...source, sourceSha256 }, null, 2) + '\n');
console.log(`Exported ${heights.length} Cinderfen Float32 heights (${sourceSha256.slice(0, 12)}).`);

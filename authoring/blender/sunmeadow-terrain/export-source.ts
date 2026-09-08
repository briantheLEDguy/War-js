import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { orvrHeightAt } from '../../../src/shared/orvrTerrain';
import { composeSunmeadowEnvironment } from '../../../scripts/campaign/sunmeadow-environment.mjs';

const zone = composeSunmeadowEnvironment(JSON.parse(await readFile('public/assets/maps/sunmeadow_march.json', 'utf8')));
const { size, segments } = zone;
// Runtime promotion changes availability, never the authored survey or its hash.
const terrain = structuredClone(zone.orvrLayout.terrain);
for (const chunk of terrain.chunks) chunk.status = 'planned';
const heights = Array.from({ length: (segments + 1) ** 2 }, (_, i) => Math.fround(orvrHeightAt(
  terrain, (i % (segments + 1)) / segments * size - size / 2,
  Math.floor(i / (segments + 1)) / segments * size - size / 2,
)));
const source = { zoneId: zone.id, size, segments, terrain, paths: zone.paths, heights };
const sourceSha256 = createHash('sha256').update(JSON.stringify(source)).digest('hex');
await writeFile('authoring/blender/sunmeadow-terrain/terrain-source.json', JSON.stringify({ ...source, sourceSha256 }, null, 2) + '\n');
console.log(`Exported ${heights.length} authoritative Float32 heights (${sourceSha256.slice(0, 12)}).`);

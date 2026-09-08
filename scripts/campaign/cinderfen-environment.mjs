/** Cinderfen's authored construction and measured navigation. Activation belongs to the campaign generator. */
import { readFileSync } from 'node:fs';

export const CINDERFEN_RELEASE = Object.freeze({ architecture: false });
const packageRoot = new URL('../../authoring/blender/cinderfen-architecture/', import.meta.url);
const read = name => JSON.parse(readFileSync(new URL(name, packageRoot), 'utf8'));
const round = value => Math.round(value * 1e6) / 1e6;
const clone = value => structuredClone(value);
const rotate = (x, z, yaw) => ({ x: x * Math.cos(yaw) + z * Math.sin(yaw), z: -x * Math.sin(yaw) + z * Math.cos(yaw) });

/** Exported for offline assembly review; staged contracts never activate a live zone. */
export function loadCinderfenContracts({ staged = false } = {}) {
  const documents = [read('navigation-contract.json'), read('junction/navigation-contract.json')];
  if (!staged && documents.some(document => !document.runtimeReady)) throw new Error('Cinderfen architecture awaits exact-export visual acceptance.');
  return Object.fromEntries(documents.flatMap(document => document.assets).map(asset => [asset.assetId, asset]));
}

function authoredProp(contracts, id, kind, x, z, extra = {}) {
  const assetKey = `frontier_cinderfen_${kind}`, contract = contracts[assetKey];
  if (!contract) throw new Error(`Missing measured Cinderfen contract: ${assetKey}`);
  return { id, kind: assetKey, assetKey, x: round(x), z: round(z), y: 0, heightMode: 'absolute', rotY: 0, scale: 1,
    colliderSpace: 'model', cameraSolid: true, colliders: clone(contract.colliders ?? []),
    walkableSurfaces: clone(contract.walkableSurfaces ?? []), ...extra };
}

/** All transforms are real metres; the same entries feed runtime and actual-GLB assembly review. */
export function cinderfenKeepAssembly(keep, contracts) {
  const entries = [], prefix = keep.objectiveId;
  const add = (suffix, kind, x, z, extra) => {
    const entry = authoredProp(contracts, `${prefix}_${suffix}`, kind, keep.x + x, keep.z + z, extra);
    entries.push(entry); return entry;
  };
  for (const [stage, halfWidth, front, rear, sideCount] of [
    ['outer', 32.4, -24, 52.8, 9], ['inner', 24.4, -7.5, 21.3, 3],
  ]) {
    add(`${stage}_gatehouse`, 'gatehouse', 0, front, { rotY: Math.PI });
    for (const x of stage === 'outer' ? [-26, -18, 18, 26] : [-18, 18])
      add(`${stage}_front_wall_${x}`, 'curtain_walk', x, front, { rotY: Math.PI });
    for (let i = 0; i < sideCount; i += 1) for (const sign of [-1, 1])
      add(`${stage}_side_wall_${sign}_${i}`, 'curtain_walk', sign * halfWidth, front + 6.4 + i * 8, { rotY: sign * Math.PI / 2 });
    const rearHalf = halfWidth - 2.4;
    for (const sign of [-1, 1]) add(`${stage}_rear_end_${sign}`, 'curtain_walk', sign * (rearHalf - 3), rear, { scaleX: .75 });
    for (let x = -rearHalf + 10; x < rearHalf - 6; x += 8) add(`${stage}_rear_wall_${x}`, 'curtain_walk', x, rear);
    for (const [corner, x, z, yaw] of [
      ['front_right', halfWidth, front, Math.PI / 2], ['front_left', -halfWidth, front, Math.PI],
      ['rear_right', halfWidth, rear, 0], ['rear_left', -halfWidth, rear, -Math.PI / 2],
    ]) {
      add(`${stage}_${corner}_landing`, 'corner_access', x, z, { rotY: yaw });
      const socket = contracts.frontier_cinderfen_corner_access.stair_socket_runtime;
      const top = contracts.frontier_cinderfen_wall_stair.top_socket_runtime;
      const join = rotate(socket[0], socket[2], yaw), stairYaw = yaw + Math.PI / 4;
      const offset = rotate(top[0], top[2], stairYaw);
      add(`${stage}_${corner}_stair`, 'wall_stair', x + join.x - offset.x, z + join.z - offset.z, { rotY: stairYaw });
    }
    const gate = keep.gates.find(item => item.stage === stage);
    if (!gate) throw new Error(`Missing campaign gate identity: ${prefix}/${stage}`);
    const interaction = { id: `${gate.propId}_interaction`, type: 'gate', label: `${stage === 'outer' ? 'Outer' : 'Inner'} keep gate`,
      maxDistance: 12, startsOpen: false, openClip: 'gate_open', closeClip: 'gate_close' };
    add(`${stage}_leaves`, 'gate_leaves', 0, front - 6, { id: gate.propId, rotY: Math.PI, interaction,
      colliders: [{ ...clone(contracts.frontier_cinderfen_gate_leaves.closed_collision_runtime), blocksWhen: 'closed', interactionId: interaction.id }] });
  }
  add('quartermaster_shelter', 'supply_shelter', -13, -65);
  return entries;
}

function placeVillage(zone, contracts) {
  const entries = [], id = zone.id;
  const add = (suffix, kind, x, z, extra = {}) => entries.push(authoredProp(contracts, `${id}_${suffix}`, kind, x, z, extra));
  for (const [suffix, x, z, rotY] of [
    ['west_dwelling', 390, -275, Math.PI / 2], ['north_dwelling', 419, -211, Math.PI],
    ['east_dwelling', 482, -230, -Math.PI / 2], ['south_dwelling', 488, -281, -Math.PI / 2],
  ]) add(suffix, 'dwelling', x, z, { rotY });
  add('salvage_station_visual', 'workshop', 484, -255, { rotY: -Math.PI / 2 });
  add('apothecary_station_visual', 'supply_shelter', 436, -273);
  const replacements = new Set(entries.map(entry => entry.id));
  for (const previous of zone.props) if (!replacements.has(previous.id) && ['vendor_stall', 'life_supply_tent'].includes(previous.kind)) {
    const outfit = previous.id === `${id}_life_outfitter_1`;
    entries.push(authoredProp(contracts, previous.id, 'supply_shelter', previous.x, previous.z, { rotY: outfit ? 0 : previous.rotY ?? 0 }));
  }
  for (const station of zone.craftingStations ?? []) {
    if (station.id === `${id}_salvage_station`) Object.assign(station, { x: 484, z: -255, y: .6, heightMode: 'absolute' });
    if (station.id === `${id}_apothecary_station`) Object.assign(station, { x: 436, z: -273, y: .35, heightMode: 'absolute' });
  }
  const mentor = zone.npcs?.find(npc => npc.id === `${id}_craft_mentor`);
  if (mentor) Object.assign(mentor, { x: 481, z: -257, y: .6, heightMode: 'absolute', rotY: -Math.PI / 2 });
  const frontCrate = zone.props.find(entry => entry.id === `${id}_life_outfitter_6`);
  if (frontCrate) Object.assign(frontCrate, { x: 448, z: -271 });
  return entries;
}

export function composeCinderfenEnvironment(zone, release = CINDERFEN_RELEASE, options = {}) {
  if (zone.id !== 'cinderfen_outskirts' || !zone.orvrLayout || !release.architecture) return zone;
  const contracts = options.contracts ?? loadCinderfenContracts();
  const entries = zone.orvrLayout.keeps.flatMap(keep => {
    const composed = cinderfenKeepAssembly(keep, contracts);
    for (const gate of keep.gates) Object.assign(gate, { x: keep.x, z: keep.z + (gate.stage === 'outer' ? -30 : -13.5),
      width: 6, height: 4.8, depth: .72, assetKey: 'frontier_cinderfen_gate_leaves' });
    keep.posterns = keep.gates.map(gate => ({ id: `${keep.objectiveId}_${gate.stage}_postern`,
      label: `${gate.stage === 'outer' ? 'Outer' : 'Inner'} gate passage`, propId: gate.propId,
      outside: { x: keep.x, y: 0, z: gate.z - 3 }, inside: { x: keep.x, y: 0, z: gate.z + 3 }, interactionRadius: 2 }));
    keep.postern = clone(keep.posterns.find(pair => pair.id.endsWith('_outer_postern')));
    keep.collisionSlots = [
      { id: `${keep.objectiveId}_outer_enclosure`, x: keep.x, z: keep.z + 14.4, width: 69.6, depth: 81.6, height: 12.1 },
      { id: `${keep.objectiveId}_inner_enclosure`, x: keep.x, z: keep.z + 6.9, width: 53.6, depth: 33.6, height: 12.1 },
    ];
    for (const slot of keep.siegeSlots) {
      if (slot.kind === 'oil') Object.assign(slot, { x: keep.x, z: keep.z - 27, y: 6.3,
        operatorPosition: { x: keep.x + 1.8, y: 6.3, z: keep.z - 24 } });
      if (slot.kind === 'catapult') Object.assign(slot, { x: keep.x + (slot.x < keep.x ? -18 : 18), z: keep.z + 36, y: 0 });
    }
    return composed;
  });
  entries.push(...placeVillage(zone, contracts));
  const replaced = new Set(entries.map(entry => entry.id));
  zone.props = zone.props.filter(entry => !/_keep_keep_/.test(entry.id ?? '') && !replaced.has(entry.id)
    && entry.id !== `${zone.id}_tree_17`).concat(entries);
  const keys = Object.keys(contracts);
  zone.orvrLayout.assetPolicy.optionalAssetKeys = [...new Set([...(zone.orvrLayout.assetPolicy.optionalAssetKeys ?? []), ...keys])];
  zone.orvrLayout.architecture = { package: 'cinderfen-architecture', assets: keys, floorDatum: 0, defenseDeckHeight: 6.3,
    note: 'Measured original Cinderfen modules; pierced gatehouses, connected corners and courtyard stairs. Shared passage identities preserve campaign gates.' };
  return zone;
}

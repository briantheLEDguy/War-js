import { roadPropFootprints } from './orvr-road-network.mjs';

/** Named civilians stand at their actual field/workyard; existing services keep their identities. */
export const REGIONAL_INHABITANTS = {
  sunmeadow_march: [{ suffix: 'homefield_farmer', name: 'Edric Hayward', title: 'Homefield Steward',
    race: 'empire', profile: 'npc_frontier_sunmeadow_empire_farmer', assetId: 'chr.frontier.sunmeadow.empire_farmer',
    x: -374, z: -317, rotY: Math.PI / 2 }],
  cinderfen_outskirts: [{ suffix: 'peat_worker', name: 'Barrek Reedhauler', title: 'Peat Yard Worker',
    race: 'greenskin', profile: 'npc_frontier_cinderfen_greenskin_peat_worker', assetId: 'chr.frontier.cinderfen.greenskin_peat_worker',
    x: 468, z: -291, rotY: -Math.PI / 2 }],
};

/** Replace service art without replacing the NPC used by quests and services. */
export const REGIONAL_SERVICE_PRESENTATIONS = {
  sunmeadow_march: [{ suffix: 'forager', race: 'empire',
    profile: 'npc_frontier_sunmeadow_empire_herbalist', assetId: 'chr.frontier.sunmeadow.empire_herbalist' }],
  cinderfen_outskirts: [{ suffix: 'marshal', race: 'dark_elf',
    profile: 'npc_frontier_cinderfen_dark_elf_supply_officer', assetId: 'chr.frontier.cinderfen.dark_elf_supply_officer' }],
};

function approvedCharacter(assets, character) {
  const asset = assets.characterProfiles?.[character.profile];
  return asset?.runtimeReady && asset.assetId === character.assetId && asset.approvalState === 'approved'
    && asset.lifecycleStatus === 'approved' && asset.reviewStatus === 'approved'
    && /^[a-f0-9]{64}$/.test(asset.modelSha256 ?? '');
}

export function integrateRegionalServicePresentations(zone, assets) {
  if (!zone.orvrLayout) return zone;
  for (const character of REGIONAL_SERVICE_PRESENTATIONS[zone.id] ?? []) {
    if (!approvedCharacter(assets, character)) continue;
    const id = `${zone.id}_${character.suffix}`, npc = zone.npcs?.find(entry => entry.id === id);
    const assignment = zone.orvrLayout.populationAssignments.find(entry => entry.entityId === id);
    if (!npc || !assignment) continue;
    Object.assign(npc, { characterProfileKey: character.profile, approvedOnly: true });
    Object.assign(assignment, { race: character.race, desiredProfileKey: character.profile, status: 'approved' });
  }
  return zone;
}

function clearStandingSpace(zone, point) {
  if (zone.props.flatMap(roadPropFootprints).some(box => point.x > box.minX - 1.1 && point.x < box.maxX + 1.1
    && point.z > box.minZ - 1.1 && point.z < box.maxZ + 1.1)) return false;
  if ([...zone.npcs ?? [], ...zone.enemies ?? []].some(actor => Math.hypot(actor.x - point.x, actor.z - point.z) < 2.2)) return false;
  return !(zone.paths ?? []).some(path => path.points.slice(1).some((b, index) => {
    const a = path.points[index], dx = b.x - a.x, dz = b.z - a.z;
    const t = Math.max(0, Math.min(1, ((point.x - a.x) * dx + (point.z - a.z) * dz) / (dx * dx + dz * dz || 1)));
    return Math.hypot(point.x - a.x - t * dx, point.z - a.z - t * dz) < path.width / 2 + 1.1;
  }));
}

export function integrateRegionalInhabitants(zone, assets) {
  const cast = REGIONAL_INHABITANTS[zone.id];
  if (!cast || !zone.orvrLayout) return zone;
  const prefix = `${zone.id}_inhabitant_`;
  zone.npcs = (zone.npcs ?? []).filter(npc => !npc.id.startsWith(prefix));
  zone.orvrLayout.populationAssignments = zone.orvrLayout.populationAssignments.filter(npc => !npc.entityId.startsWith(prefix));
  for (const civilian of cast) {
    if (!approvedCharacter(assets, civilian) || !clearStandingSpace(zone, civilian)) continue;
    const id = prefix + civilian.suffix;
    zone.npcs.push({ id, name: civilian.name, title: civilian.title, role: 'ambient', approvedOnly: true,
      characterProfileKey: civilian.profile, x: civilian.x, z: civilian.z, rotY: civilian.rotY });
    zone.orvrLayout.populationAssignments.push({ entityId: id, race: civilian.race, role: 'ambient',
      desiredProfileKey: civilian.profile, status: 'approved' });
  }
  return zone;
}

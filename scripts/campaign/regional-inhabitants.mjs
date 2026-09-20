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
    const asset = assets.characterProfiles?.[civilian.profile];
    if (!asset?.runtimeReady || asset.assetId !== civilian.assetId || asset.approvalState !== 'approved'
      || asset.lifecycleStatus !== 'approved' || asset.reviewStatus !== 'approved'
      || !/^[a-f0-9]{64}$/.test(asset.modelSha256 ?? '') || !clearStandingSpace(zone, civilian)) continue;
    const id = prefix + civilian.suffix;
    zone.npcs.push({ id, name: civilian.name, title: civilian.title, role: 'ambient', approvedOnly: true,
      characterProfileKey: civilian.profile, x: civilian.x, z: civilian.z, rotY: civilian.rotY });
    zone.orvrLayout.populationAssignments.push({ entityId: id, race: civilian.race, role: 'ambient',
      desiredProfileKey: civilian.profile, status: 'approved' });
  }
  return zone;
}

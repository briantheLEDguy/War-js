import { readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { defaultZoneConfigs } from '../src/shared/orvr/config';
import { orvrGridHeightAt } from '../src/shared/orvrTerrain';
import type { NavigationProp } from '../src/shared/worldNavigation';
import type { ZoneConfig, Position, Realm } from '../src/shared/orvr/protocol';
import type { OrvrZoneLayout } from '../src/world/orvrTypes';
import { mapPropNavigation } from './mapNavigation';

interface CampaignMap {
  id: string; size: number; segments: number; spawnPoint?: Position; orvrLayout?: OrvrZoneLayout;
  rvrObjectives?: Array<{ id: string; x: number; y?: number; z: number; captureRadius: number; requiresObjectiveIds?: string[] }>;
  props?: NavigationProp[];
}

const point = (entry: { x: number; y?: number; z: number }): Position => ({ x: entry.x, y: entry.y ?? 0, z: entry.z });

/** Keep the hinge origin for animation; authority uses the actual closed leaf footprint. */
export function campaignGateNavigation(gate: { x: number; y?: number; z: number; width: number; depth: number; height: number },
  prop: NavigationProp | undefined, groundAt: (x: number, z: number) => number) {
  const closed = prop?.colliders?.filter(collider => collider.blocksWhen === 'closed');
  if (prop && closed?.length === 1) {
    const collider = mapPropNavigation([{ ...prop, colliders: closed, walkableSurfaces: [] }], groundAt).collision[0];
    const box = collider.footprint!;
    const y = collider.minY ?? (prop.heightMode === 'absolute' ? 0 : groundAt(prop.x, prop.z)) + (prop.y ?? 0);
    return { position: { x: box.x, y, z: box.z }, footprint: { width: box.width, depth: box.depth,
      height: collider.maxY === undefined ? gate.height : collider.maxY - y, rotY: box.rotY } };
  }
  return { position: point(prop ?? gate), footprint: { width: gate.width, depth: gate.depth, height: gate.height, rotY: -(prop?.rotY ?? 0) } };
}

/** Reads the same generated maps served to clients; no parallel hand-maintained campaign coordinates. */
export async function loadCampaignMapConfigs(mapDirectory = resolve('public/assets/maps')): Promise<ZoneConfig[]> {
  return Promise.all(defaultZoneConfigs().map(async fallback => {
    const map = JSON.parse(await readFile(resolve(mapDirectory, `${fallback.id}.json`), 'utf8')) as CampaignMap;
    const layout = map.orvrLayout;
    const bounds = { minX: -map.size / 2, maxX: map.size / 2, minZ: -map.size / 2, maxZ: map.size / 2 };
    if (!layout) {
      if (fallback.kind !== 'city') throw new Error(`Regenerate expanded campaign maps before starting the server: ${fallback.id}`);
      const objectives = (map.rvrObjectives ?? []).map(objective => ({
        id: objective.id, position: point(objective), captureRadius: objective.captureRadius,
        requiresObjectiveIds: objective.requiresObjectiveIds, guardCount: 2,
      }));
      const attacker: Realm = fallback.defender === 'aegis' ? 'riftbound' : 'aegis';
      // City staging uses existing entrance/last-objective elevations until authored server navigation is supplied.
      const staging = { ...fallback.staging, [attacker]: point(map.spawnPoint ?? fallback.staging[attacker]), [fallback.defender!]: point(objectives.at(-1)!.position) };
      return { ...fallback, bounds, objectives, staging };
    }
    const config: ZoneConfig = {
      id: map.id, kind: fallback.kind, bounds,
      staging: Object.fromEntries(layout.stagingCamps.map(camp => [camp.realm, point(camp)])) as Record<Realm, Position>,
      objectives: layout.battlefieldObjectives.map(objective => ({
        id: objective.objectiveId, position: point(objective), captureRadius: objective.captureRadius, guardCount: 2,
        routes: Object.fromEntries(layout.caravanRoutes.filter(route => route.objectiveId === objective.objectiveId)
          .map(route => [route.realm, route.points.map(point)])),
      })),
      keeps: layout.keeps.map(keep => {
        const gates = Object.fromEntries(keep.gates.map(gate => [gate.stage, campaignGateNavigation(gate,
          map.props?.find(prop => prop.id === gate.propId),
          (x, z) => orvrGridHeightAt(layout.terrain, map.size, map.segments, x, z))]));
        return {
        id: keep.objectiveId, realm: keep.realm, position: point(keep.commander),
        outerGate: gates.outer.position, innerGate: gates.inner.position, quartermaster: point(keep.quartermaster),
        deliveryPoint: point(keep.deliveryPoint),
        ...(keep.postern ? { postern: { outside: point(keep.postern.outside), inside: point(keep.postern.inside), interactionRadius: keep.postern.interactionRadius } } : {}),
        ...(keep.posterns ? { posterns: keep.posterns.map(postern => ({ id: postern.id, label: postern.label,
          outside: point(postern.outside), inside: point(postern.inside), interactionRadius: postern.interactionRadius })) } : {}),
        gateFootprints: Object.fromEntries(Object.entries(gates).map(([stage, gate]) => [stage, gate.footprint])),
        siegePositions: { ram: [point(keep.ramSpawn)], oil: keep.siegeSlots.filter(slot => slot.kind === 'oil').map(point), catapult: keep.siegeSlots.filter(slot => slot.kind === 'catapult').map(point) },
        ...(keep.siegeSlots.some(slot => slot.operatorPosition) ? { siegeOperatorPositions: Object.fromEntries(
          (['oil', 'catapult'] as const).filter(kind => keep.siegeSlots.some(slot => slot.kind === kind && slot.operatorPosition))
            .map(kind => [kind, keep.siegeSlots.filter(slot => slot.kind === kind).map(slot => point(slot.operatorPosition ?? slot))]),
        ) } : {}),
      }; }),
      terrain: layout.terrain, terrainSize: map.size, terrainSegments: map.segments,
      collision: [],
      walkableSurfaces: [],
    };
    // Retain separate collision footprints. Dynamic siege gates are handled by the simulation.
    const dynamicGateProps = new Set(layout.keeps.flatMap(keep => keep.gates.map(gate => gate.propId)));
    Object.assign(config, mapPropNavigation(map.props ?? [],
      (x, z) => orvrGridHeightAt(layout.terrain, map.size, map.segments, x, z), dynamicGateProps));
    return config;
  }));
}

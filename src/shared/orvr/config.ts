import type { Realm, ZoneConfig } from './protocol';

export const ORVR_RULES = Object.freeze({
  playerSpeed: 6,
  playerHealth: 100,
  respawnSeconds: 15,
  captureSeconds: 30,
  shipmentSeconds: 180,
  shipmentSupplies: 100,
  supplyCap: 1_000,
  caravanSpeed: 3.5,
  escortRadius: 25,
  abandonmentSeconds: 240,
  ramReplacementSeconds: 180,
  preparationSeconds: 180,
  citySeconds: 1_800,
  recoverySeconds: 300,
  realmCapacity: 18,
  interactionRadius: 12,
  snapshotRadius: 220,
});

export const ORVR_TRACKS = {
  west: ['ironwood_redoubt', 'greybrook_crossing', 'sunmeadow_march', 'cinderfen_outskirts', 'bleakroot_causeway', 'vilemere_heights'],
  east: ['highvale_rampart', 'glassriver_ford', 'brightfen_approach', 'ashen_steppe', 'gorepine_pass', 'obsidian_scar'],
  central: ['aegis_gate_fortress', 'aegis_crownworks', 'dawnline_expanse', 'shatterline_expanse', 'rift_crownworks', 'rift_gate_fortress'],
} as const;

export function opposite(realm: Realm): Realm { return realm === 'aegis' ? 'riftbound' : 'aegis'; }

/** Collision and routes are simulation data, never a request to generate primitive visual models. */
export function defaultZoneConfig(id: string): ZoneConfig {
  const city = id === 'aegis_capital' || id === 'riftspire_capital';
  const defender: Realm = id === 'aegis_capital' ? 'aegis' : 'riftbound';
  const point = (x: number, z: number, y = 0) => ({ x, y, z });
  if (city) {
    const entries = id === 'aegis_capital'
      ? [['courtyard', 0, 158], ['vault', 114, 332], ['throne_room', 0, 350]] as const
      : [['city_gate', 0, 12], ['vault', 0, -420], ['plaza', 0, -480]] as const;
    const elevation = id === 'riftspire_capital' ? -105 : 0;
    return {
      id, kind: 'city', defender,
      bounds: { minX: -600, maxX: 600, minZ: -600, maxZ: 600 },
      staging: { aegis: point(-505, 80, elevation), riftbound: point(505, 80, elevation) },
      keeps: [],
      objectives: entries.map(([suffix, x, z], index) => ({
        id: `${id}_${suffix}`, position: point(x, z, elevation), captureRadius: 12, guardCount: 2,
        requiresObjectiveIds: entries.slice(0, index).map(([prior]) => `${id}_${prior}`),
      })),
    };
  }
  const keeps = (['aegis', 'riftbound'] as const).map(realm => {
    const sign = realm === 'aegis' ? -1 : 1;
    return {
      id: `${id}_${realm}_keep`, realm, position: point(sign * 350, 0),
      outerGate: point(sign * 310, 0), innerGate: point(sign * 335, 0), quartermaster: point(sign * 370, 0),
      siegePositions: { ram: [point(sign * 285, 0)], oil: [point(sign * 310, 4)], catapult: [point(sign * 320, -18), point(sign * 320, 18)] },
    };
  });
  return {
    id, kind: id.endsWith('_fortress') ? 'fortress' : 'battlefield',
    bounds: { minX: -600, maxX: 600, minZ: -600, maxZ: 600 },
    staging: { aegis: point(-505, 80), riftbound: point(505, 80) }, keeps,
    objectives: [['west', 0, -260], ['central', 0, 0], ['east', 0, 260]].map(([name, x, z]) => ({
      id: `${id}_${name}_objective`, position: point(Number(x), Number(z)), captureRadius: 18, guardCount: 2,
      routes: {
        aegis: [point(Number(x), Number(z)), point(-170, Number(z) / 2), point(-280, -55), point(-370, -55), point(-370, 0)],
        riftbound: [point(Number(x), Number(z)), point(170, Number(z) / 2), point(280, 55), point(370, 55), point(370, 0)],
      },
    })),
  };
}

export function defaultZoneConfigs(): ZoneConfig[] {
  return [...ORVR_TRACKS.west, ...ORVR_TRACKS.east, ...ORVR_TRACKS.central, 'aegis_capital', 'riftspire_capital'].map(defaultZoneConfig);
}

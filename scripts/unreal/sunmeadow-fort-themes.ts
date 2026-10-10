import type { ZoneDefinition } from '../../shared/world/ZoneDefinition';
export type SunmeadowFortTheme = {
  objectiveId: string; realm: 'aegis' | 'riftbound'; theme: string;
  additions: Array<{ id: string; assetKey: string; x: number; z: number; yawDegrees: number; uniformScale: number }>;
  wallMaterial: 'retained_limestone' | 'riftspire_basalt';
  gatehouseMaterials: string[]; bannerAsset: string;
  gameplayAnchorsMoved: false; appearanceApproved: false;
};

/** Visual additions retain the complete keep assembly and all gate/siege/delivery coordinates. */
export function sunmeadowFortThemes(zone: ZoneDefinition): SunmeadowFortTheme[] {
  const keeps = zone.orvrLayout?.keeps;
  if (zone.id !== 'sunmeadow_march' || keeps?.length !== 2 || new Set(keeps.map(k => k.realm)).size !== 2)
    throw new Error('Sunmeadow faction themes require both retained keeps');
  return keeps.map(keep => {
    const heading = keep.heading ?? 0;
    if (!['aegis', 'riftbound'].includes(keep.realm) || ![keep.x, keep.z, heading].every(Number.isFinite))
      throw new Error('Invalid themed keep transform');
    const aegis = keep.realm === 'aegis', c = Math.cos(heading), s = Math.sin(heading);
    const offsets = aegis ? [[-29, -18], [29, -18]] : [[-29, -18], [29, -18], [-29, 11], [29, 11]];
    return {
      objectiveId: keep.objectiveId, realm: keep.realm,
      theme: aegis ? 'Limestone curtain, square watchtowers and oak garrison' : 'Basalt curtain, iron fittings and four standing finials',
      additions: offsets.map(([x, z], i) => ({ id: `${keep.objectiveId}_faction_tower_${i}`,
        assetKey: aegis ? 'aegis_tower' : 'riftspire_ritual_obelisk',
        x: keep.x + x * c + z * s, z: keep.z + z * c - x * s, yawDegrees: heading * 180 / Math.PI, uniformScale: aegis ? 1 : 1.65 })),
      wallMaterial: aegis ? 'retained_limestone' : 'riftspire_basalt',
      gatehouseMaterials: aegis ? [] : ['basalt', 'basalt', 'basalt', 'basalt', 'basalt', 'timber', 'cloth', 'iron', 'basalt', 'basalt'],
      bannerAsset: aegis ? 'aegis_civic_waymarker' : 'riftspire_banner',
      gameplayAnchorsMoved: false, appearanceApproved: false,
    } as SunmeadowFortTheme;
  });
}
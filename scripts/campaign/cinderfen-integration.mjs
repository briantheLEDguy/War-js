/** Regional dressing and exclusions live outside frozen architecture review inputs. */
import { WORLD_LIFE_FOOTPRINTS } from './world-life-source.mjs';

const distance = (p, a, b) => {
  const dx = b.x - a.x, dz = b.z - a.z, length = dx * dx + dz * dz;
  const t = length ? Math.max(0, Math.min(1, ((p.x-a.x)*dx+(p.z-a.z)*dz)/length)) : 0;
  return Math.hypot(p.x-a.x-dx*t, p.z-a.z-dz*t);
};
const radiusOf = prop => WORLD_LIFE_FOOTPRINTS[prop.kind] ?? 6;

export function integrateCinderfen(zone) {
  if (zone.id !== 'cinderfen_outskirts' || !zone.orvrLayout) return zone;
  // The old bridge had no water crossing at this settlement location.
  zone.props = zone.props.filter(prop => prop.id !== `${zone.id}_field_bridge`);
  const life = zone.props.filter(prop => prop.id?.startsWith(`${zone.id}_life_`));
  const protectedPoints = [
    { ...zone.spawnPoint, radius: 8 },
    ...(zone.npcs ?? []).map(p => ({ ...p, radius: 4 })),
    ...(zone.craftingStations ?? []).map(p => ({ ...p, radius: p.radius + 1 })),
    ...(zone.resourceNodes ?? []).map(p => ({ ...p, radius: 3 })),
    ...(zone.rvrObjectives ?? []).map(p => ({ ...p, radius: p.captureRadius + 1 })),
    ...(zone.zoneTriggers ?? []).map(p => ({ ...p, radius: p.radius + 5 })),
  ];
  const clear = (candidate, radius, prop) => {
    if (protectedPoints.some(p => Math.hypot(candidate.x-p.x,candidate.z-p.z) < radius+p.radius+.1)) return false;
    if (life.some(p => p !== prop && Math.hypot(candidate.x-p.x,candidate.z-p.z) < radius+radiusOf(p)+.4)) return false;
    if (zone.paths.some(path => path.points.slice(1).some((p,i) => distance(candidate,path.points[i],p) < path.width/2+radius+.85))) return false;
    for (const other of zone.props) {
      if (other === prop) continue;
      const sx=(other.scale??1)*(other.scaleX??1), sz=(other.scale??1)*(other.scaleZ??1);
      const sign=other.colliderSpace==='model'?-1:1, yaw=(other.rotY??0)*sign;
      for (const box of other.colliders??[]) {
        if ((box.minY??0)+(other.y??0) >= 1.8) continue;
        const x=other.x+(box.x??0)*sx*Math.cos(yaw)-(box.z??0)*sz*Math.sin(yaw);
        const z=other.z+(box.x??0)*sx*Math.sin(yaw)+(box.z??0)*sz*Math.cos(yaw);
        const angle=yaw+(box.rotY??0)*sign, dx=candidate.x-x, dz=candidate.z-z;
        const localX=dx*Math.cos(angle)+dz*Math.sin(angle),localZ=-dx*Math.sin(angle)+dz*Math.cos(angle);
        if (Math.hypot(Math.max(0,Math.abs(localX)-box.width*sx/2),Math.max(0,Math.abs(localZ)-box.depth*sz/2)) < radius+1.1) return false;
      }
    }
    return true;
  };
  for (const prop of life.filter(p => WORLD_LIFE_FOOTPRINTS[p.kind])) {
    const radius=radiusOf(prop), origin={x:prop.x,z:prop.z};
    if (clear(origin,radius,prop)) continue;
    let target;
    for (let ring=1; ring<=24 && !target; ring++) {
      for (let step=0; step<32; step++) {
        const angle=step*Math.PI/16;
        const point={x:Math.round((origin.x+ring*Math.cos(angle))*1000)/1000,z:Math.round((origin.z+ring*Math.sin(angle))*1000)/1000};
        if (clear(point,radius,prop)) { target=point; break; }
      }
    }
    if (!target) throw new Error(`No clear Cinderfen furniture position for ${prop.id}`);
    Object.assign(prop,target);
    for (const emitter of zone.ambientLife?.emitters??[]) if (emitter.id.startsWith(prop.id+'_')) Object.assign(emitter,target);
  }
  for (const patch of zone.orvrLayout.biome.placements??[]) {
    const ids=new Set(zone.paths.map(path=>path.id));
    patch.excludeCorridors=(patch.excludeCorridors??[]).filter(path=>!ids.has(path.id)).concat(zone.paths.map(path=>({
      id:path.id,points:structuredClone(path.points),radius:path.width/2+3,height:0,feather:0,
    })));
    for (const prop of life) {
      const radius=radiusOf(prop)+3;
      if (!patch.exclude.some(p=>Math.hypot(p.x-prop.x,p.z-prop.z)+radius<=p.radius)) patch.exclude.push({x:prop.x,z:prop.z,radius});
    }
  }
  zone.props.sort((a,b)=>(a.id??'').localeCompare(b.id??''));
  return zone;
}

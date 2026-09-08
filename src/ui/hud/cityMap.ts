import { drawMapFeatures, drawMapWater } from './zoneMapGeometry';
import type { ZoneDefinition } from '../../world/ZoneLoader';
/** Map geometry is drawn from the same authored paths and canal boundaries. */
export function drawCityMap(ctx: CanvasRenderingContext2D, zone: ZoneDefinition, player: {
  x: number;
  y?: number;
  z: number;
}, cx: number, cy: number, radius: number, range: number): void {
  const scale = radius / range;
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.clip();
  const x = (v: number) => cx + (v - player.x) * scale;
  const z = (v: number) => cy + (v - player.z) * scale;
  const projection = { scale, screenScale: 1, toCanvas: (p: { x: number; z: number }) => ({ x: x(p.x), y: z(p.z) }) };
  drawMapFeatures(ctx, zone, projection, ['nature']);
  drawMapWater(ctx, zone, projection);
  drawMapFeatures(ctx, zone, projection, ['ground']);
  ctx.strokeStyle = '#8d7662';
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  for (const p of zone.paths ?? []) {
    ctx.lineWidth = Math.max(1, p.width * scale);
    ctx.beginPath();
    p.points.forEach((v, i) => i ? ctx.lineTo(x(v.x), z(v.z)) : ctx.moveTo(x(v.x), z(v.z)));
    ctx.stroke();
  }
  if (zone.craterCity) {
    for (const level of zone.craterCity.levels) {
      ctx.strokeStyle = Math.abs((player.y ?? 0) - level.y) < 24 ? '#debf91' : '#454753';
      ctx.lineWidth = Math.max(1, 14 * scale);
      ctx.beginPath(); ctx.arc(x(0), z(0), level.radius * scale, 0, Math.PI * 2); ctx.stroke();
    }
    for (const route of zone.craterCity.routes) {
      ctx.lineWidth = Math.max(1, route.width * scale);
      for (let i = 1; i < route.points.length; i++) {
        const a = route.points[i-1], b = route.points[i], height = player.y ?? 0;
        const nearLevel = Math.min(a.y,b.y) < height+15 && Math.max(a.y,b.y) > height-15;
        ctx.strokeStyle = nearLevel ? '#debf91' : '#454753';
        ctx.beginPath(); ctx.moveTo(x(a.x),z(a.z)); ctx.lineTo(x(b.x),z(b.z)); ctx.stroke();
      }
    }
  }
  drawMapFeatures(ctx, zone, projection, ['wall', 'building', 'landmark']);
  ctx.restore();
}

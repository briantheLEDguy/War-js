import type { ZoneDefinition } from '../../world/ZoneLoader';
/** Map geometry is drawn from the same authored paths and canal boundaries. */
export function drawCityMap(ctx: CanvasRenderingContext2D, zone: ZoneDefinition, player: {
  x: number;
  z: number;
}, cx: number, cy: number, radius: number, range: number): void {
  const scale = radius / range;
  ctx.save();
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.clip();
  const x = (v: number) => cx + (v - player.x) * scale;
  const z = (v: number) => cy + (v - player.z) * scale;
  ctx.fillStyle = '#31585e';
  for (const c of zone.canals ?? [])
    ctx.fillRect(x(c.x - c.width / 2), z(c.z - c.depth / 2), c.width * scale, c.depth * scale);
  ctx.strokeStyle = '#8d7662';
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  for (const p of zone.paths ?? []) {
    ctx.lineWidth = Math.max(1, p.width * scale);
    ctx.beginPath();
    p.points.forEach((v, i) => i ? ctx.lineTo(x(v.x), z(v.z)) : ctx.moveTo(x(v.x), z(v.z)));
    ctx.stroke();
  }
  ctx.strokeStyle = '#b7b1a0';
  ctx.lineWidth = 2;
  for (const p of zone.props.filter(p => (p.kind === 'aegis_wall' || p.kind === 'aegis_wall_entry'))) {
    const half = 6 * (p.scaleX ?? 1), vertical = Boolean(p.rotY);
    ctx.beginPath();
    ctx.moveTo(x(p.x - (vertical ? 0 : half)), z(p.z - (vertical ? half : 0)));
    ctx.lineTo(x(p.x + (vertical ? 0 : half)), z(p.z + (vertical ? half : 0)));
    ctx.stroke();
  }
  ctx.restore();
}

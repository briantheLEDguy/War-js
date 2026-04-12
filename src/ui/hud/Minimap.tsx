import { useEffect, useRef } from 'react';
import type { Game } from '../../game/Game';
import { useGameStore } from '../../state/gameStore';

interface Props {
  game: Game | null;
}

const RANGE = 40; // world units shown on minimap

export function Minimap({ game }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef(0);
  const enemies = useGameStore((s) => s.enemies);
  const character = useGameStore((s) => s.character);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !game) return;
    const ctx = canvas.getContext('2d')!;
    const w = (canvas.width = 150);
    const h = (canvas.height = 150);
    const cx = w / 2;
    const cy = h / 2;
    const r = w / 2 - 4;

    const draw = () => {
      ctx.clearRect(0, 0, w, h);

      // Dark terrain background with subtle radial gradient
      const bg = ctx.createRadialGradient(cx, cy, 0, cx, cy, r);
      bg.addColorStop(0, '#2a3820');
      bg.addColorStop(0.7, '#1e2a18');
      bg.addColorStop(1, '#141e10');
      ctx.fillStyle = bg;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.fill();

      const px = game.playerPos.x;
      const pz = game.playerPos.z;

      // Grid lines
      ctx.strokeStyle = 'rgba(201, 162, 87, 0.08)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx, cy - r); ctx.lineTo(cx, cy + r);
      ctx.moveTo(cx - r, cy); ctx.lineTo(cx + r, cy);
      ctx.stroke();

      // Range rings
      ctx.strokeStyle = 'rgba(201, 162, 87, 0.12)';
      ctx.beginPath();
      ctx.arc(cx, cy, r * 0.5, 0, Math.PI * 2);
      ctx.stroke();

      // Outer ring
      ctx.strokeStyle = 'rgba(201, 162, 87, 0.35)';
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      ctx.stroke();

      // Compass labels
      ctx.font = '8px "Cinzel", serif';
      ctx.fillStyle = 'rgba(201, 162, 87, 0.5)';
      ctx.textAlign = 'center';
      ctx.fillText('N', cx, cy - r + 10);
      ctx.fillText('S', cx, cy + r - 4);
      ctx.fillText('E', cx + r - 6, cy + 3);
      ctx.fillText('W', cx - r + 6, cy + 3);

      // NPC dots (from store)
      const npcs = useGameStore.getState().npcs;
      for (const npc of npcs) {
        const dx = npc.position.x - px;
        const dz = npc.position.z - pz;
        const mx = cx + (dx / RANGE) * r;
        const my = cy + (dz / RANGE) * r;
        if (Math.hypot(mx - cx, my - cy) > r - 3) continue;
        ctx.fillStyle = 'rgba(100, 180, 255, 0.7)';
        ctx.beginPath();
        ctx.arc(mx, my, 2, 0, Math.PI * 2);
        ctx.fill();
      }

      // Enemies
      for (const e of enemies) {
        if (!e.alive) continue;
        const dx = e.position.x - px;
        const dz = e.position.z - pz;
        const mx = cx + (dx / RANGE) * r;
        const my = cy + (dz / RANGE) * r;
        if (Math.hypot(mx - cx, my - cy) > r - 3) continue;
        ctx.fillStyle = '#d14a3a';
        ctx.beginPath();
        ctx.arc(mx, my, 3, 0, Math.PI * 2);
        ctx.fill();
      }

      // Player — gold diamond shape
      ctx.fillStyle = '#e6c570';
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(Math.PI / 4);
      ctx.fillRect(-3, -3, 6, 6);
      ctx.restore();

      // Glow around player
      ctx.strokeStyle = 'rgba(230, 197, 112, 0.3)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, 6, 0, Math.PI * 2);
      ctx.stroke();

      rafRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(rafRef.current);
  }, [game, enemies, character]);

  return (
    <div className="minimap">
      <canvas ref={canvasRef} />
      {game && <div className="minimap-label">{game.zoneName}</div>}
    </div>
  );
}

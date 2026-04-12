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
    const w = (canvas.width = 140);
    const h = (canvas.height = 140);

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      ctx.fillStyle = '#2a3a20';
      ctx.fillRect(0, 0, w, h);

      const px = game.playerPos.x;
      const pz = game.playerPos.z;

      // rings
      ctx.strokeStyle = 'rgba(201, 162, 87, 0.3)';
      ctx.beginPath();
      ctx.arc(w / 2, h / 2, w / 2 - 2, 0, Math.PI * 2);
      ctx.stroke();

      // enemies
      for (const e of enemies) {
        if (!e.alive) continue;
        const dx = e.position.x - px;
        const dz = e.position.z - pz;
        const mx = w / 2 + (dx / RANGE) * (w / 2);
        const my = h / 2 + (dz / RANGE) * (h / 2);
        if (Math.hypot(mx - w / 2, my - h / 2) > w / 2 - 4) continue;
        ctx.fillStyle = '#d14a3a';
        ctx.beginPath();
        ctx.arc(mx, my, 3, 0, Math.PI * 2);
        ctx.fill();
      }

      // player
      ctx.fillStyle = '#e6c570';
      ctx.beginPath();
      ctx.arc(w / 2, h / 2, 4, 0, Math.PI * 2);
      ctx.fill();

      rafRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(rafRef.current);
  }, [game, enemies, character]);

  return (
    <div className="minimap">
      <canvas ref={canvasRef} />
    </div>
  );
}

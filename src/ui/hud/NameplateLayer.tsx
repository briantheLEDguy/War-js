import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import type { Game } from '../../game/Game';
import { useGameStore } from '../../state/gameStore';

interface Props {
  game: Game | null;
}

interface Plate {
  id: string;
  name: string;
  hpPct: number;
  x: number;
  y: number;
}

export function NameplateLayer({ game }: Props) {
  const enemies = useGameStore((s) => s.enemies);
  const [plates, setPlates] = useState<Plate[]>([]);
  const rafRef = useRef(0);

  useEffect(() => {
    if (!game) return;
    const out = new THREE.Vector2();
    const worldVec = new THREE.Vector3();
    const loop = () => {
      const next: Plate[] = [];
      for (const e of enemies) {
        if (!e.alive) continue;
        worldVec.set(e.position.x, e.position.y + 2.3, e.position.z);
        if (game.worldToScreen(worldVec, out)) {
          next.push({
            id: e.id,
            name: e.name,
            hpPct: e.health / e.maxHealth,
            x: out.x,
            y: out.y,
          });
        }
      }
      setPlates(next);
      rafRef.current = requestAnimationFrame(loop);
    };
    loop();
    return () => cancelAnimationFrame(rafRef.current);
  }, [game, enemies]);

  return (
    <div className="floating-damage-layer">
      {plates.map((p) => (
        <div
          key={p.id}
          className="enemy-nameplate"
          style={{ left: `${p.x}px`, top: `${p.y}px` }}
        >
          <div className="name">{p.name}</div>
          <div className="bar">
            <div className="fill health" style={{ transform: `scaleX(${p.hpPct})` }} />
          </div>
        </div>
      ))}
    </div>
  );
}

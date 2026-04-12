import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import type { Game } from '../../game/Game';
import { useGameStore } from '../../state/gameStore';

interface Props {
  game: Game | null;
}

interface Item {
  id: string;
  amount: number;
  kind: 'damage' | 'heal' | 'miss';
  x: number;
  y: number;
}

export function FloatingDamageLayer({ game }: Props) {
  const floating = useGameStore((s) => s.floatingDamage);
  const [items, setItems] = useState<Item[]>([]);
  const rafRef = useRef(0);

  useEffect(() => {
    if (!game) return;
    const out = new THREE.Vector2();
    const world = new THREE.Vector3();
    const loop = () => {
      const next: Item[] = [];
      for (const d of floating) {
        world.set(d.worldPos.x, d.worldPos.y, d.worldPos.z);
        if (game.worldToScreen(world, out)) {
          next.push({ id: d.id, amount: d.amount, kind: d.kind, x: out.x, y: out.y });
        }
      }
      setItems(next);
      rafRef.current = requestAnimationFrame(loop);
    };
    loop();
    return () => cancelAnimationFrame(rafRef.current);
  }, [game, floating]);

  return (
    <div className="floating-damage-layer">
      {items.map((i) => (
        <div
          key={i.id}
          className={`floating-damage ${i.kind}`}
          style={{ left: `${i.x}px`, top: `${i.y}px` }}
        >
          {i.kind === 'miss' ? 'MISS' : `-${i.amount}`}
        </div>
      ))}
    </div>
  );
}

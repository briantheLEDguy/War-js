import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import {
  questsOfferedBy,
  questsReadyToTurnIn,
} from '../../game/QuestLogic';
import type { Game } from '../../game/Game';
import { useGameStore } from '../../state/gameStore';

interface Marker {
  id: string;
  label: string;
  kind: 'offer' | 'turnin';
  x: number;
  y: number;
}

/**
 * Renders a floating "!" above NPCs who have quests to offer, and "?" above
 * those with completed quests ready to turn in. Projects NPC world positions
 * once per animation frame via Game.worldToScreen.
 */
export function QuestMarkerLayer({ game }: { game: Game | null }) {
  const npcs = useGameStore((s) => s.npcs);
  const quests = useGameStore((s) => s.quests);
  const character = useGameStore((s) => s.character);
  const [marks, setMarks] = useState<Marker[]>([]);
  const rafRef = useRef(0);

  useEffect(() => {
    if (!game) return;
    const out = new THREE.Vector2();
    const world = new THREE.Vector3();
    const loop = () => {
      const next: Marker[] = [];
      for (const npc of npcs) {
        if (npc.role !== 'questgiver') continue;
        const turnins = questsReadyToTurnIn(npc.id, quests, character);
        if (turnins.length > 0) {
          world.set(npc.position.x, npc.position.y + 2.6, npc.position.z);
          if (game.worldToScreen(world, out)) {
            next.push({ id: npc.id, label: '?', kind: 'turnin', x: out.x, y: out.y });
          }
          continue;
        }
        const offers = questsOfferedBy(npc.id, quests, character);
        if (offers.length > 0) {
          world.set(npc.position.x, npc.position.y + 2.6, npc.position.z);
          if (game.worldToScreen(world, out)) {
            next.push({ id: npc.id, label: '!', kind: 'offer', x: out.x, y: out.y });
          }
        }
      }
      setMarks(next);
      rafRef.current = requestAnimationFrame(loop);
    };
    loop();
    return () => cancelAnimationFrame(rafRef.current);
  }, [game, npcs, quests, character]);

  return (
    <div className="floating-damage-layer">
      {marks.map((m) => (
        <div
          key={m.id}
          className={`quest-marker ${m.kind}`}
          style={{ left: `${m.x}px`, top: `${m.y}px` }}
        >
          {m.label}
        </div>
      ))}
    </div>
  );
}

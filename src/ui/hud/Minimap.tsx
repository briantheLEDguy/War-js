import { useEffect, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import type { Game } from '../../game/Game';
import { useGameStore } from '../../state/gameStore';
import { ObjectiveTracker } from './ObjectiveTracker';
import {
  buildMarkers,
  DEFAULT_VISIBLE,
  MAP_MARKER_LEGEND,
  type MapMarker,
  type MarkerToggle,
  useZoneExitMarkers,
} from './mapData';
import { useDraggableWindow } from './useDraggableWindow';

interface Props {
  game: Game | null;
}

const RANGE = 55;
const EDGE_RANGE = 260;
const MAP_SIZE = 150;

export function Minimap({ game }: Props) {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLDivElement>();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef(0);
  const enemies = useGameStore((state) => state.enemies);
  const character = useGameStore((state) => state.character);
  const npcs = useGameStore((state) => state.npcs);
  const quests = useGameStore((state) => state.quests);
  const exits = useZoneExitMarkers(character?.zoneId ?? null);
  const [visible, setVisible] = useState(DEFAULT_VISIBLE);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !game) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = (canvas.width = MAP_SIZE);
    const h = (canvas.height = MAP_SIZE);
    const cx = w / 2;
    const cy = h / 2;
    const radius = w / 2 - 4;

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      drawBackground(ctx, cx, cy, radius);

      const px = game.playerPos.x;
      const pz = game.playerPos.z;
      const playerPosition = { x: px, z: pz };
      const markers = buildMarkers({
        character,
        craftingStations: game.craftingStationMarkers,
        enemies,
        exits,
        npcs,
        playerPosition,
        quests,
        resourceNodes: game.resourceNodeMarkers,
        visible,
      });

      const hasFocus = markers.some((marker) => marker.focused);
      for (const marker of markers) {
        if (hasFocus && !marker.focused && Math.hypot(marker.position.x - px, marker.position.z - pz) > RANGE) continue;
        drawMapMarker(ctx, marker, playerPosition, cx, cy, radius);
      }

      drawPlayer(ctx, cx, cy);
      rafRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(rafRef.current);
  }, [character, enemies, exits, game, npcs, quests, visible]);

  function toggleMarker(key: MarkerToggle) {
    setVisible((current) => ({ ...current, [key]: !current[key] }));
  }

  return (
    <>
      <div ref={panelRef} className={`minimap-shell${dragClassName}`} style={dragStyle}>
        <div className="minimap draggable-window-handle" {...dragHandleProps}>
          <canvas ref={canvasRef} aria-label="Minimap" />
          {game && <div className="minimap-label">{game.zoneName}</div>}
        </div>
        <details className="minimap-filters">
          <summary>Map filters</summary>
          <div className="minimap-legend" aria-label="Minimap marker filters">
          {MAP_MARKER_LEGEND.map((item) => (
            <label className={`minimap-toggle${visible[item.key] ? ' active' : ''}`} key={item.key}>
              <input
                type="checkbox"
                checked={visible[item.key]}
                onChange={() => toggleMarker(item.key)}
              />
              <span
                className="minimap-swatch"
                style={{ '--marker-color': item.color } as CSSProperties}
              />
              {item.label}
            </label>
          ))}
          </div>
        </details>
      </div>
      <ObjectiveTracker game={game} />
    </>
  );
}

function drawBackground(
  ctx: CanvasRenderingContext2D,
  cx: number,
  cy: number,
  radius: number,
) {
  const bg = ctx.createRadialGradient(cx, cy, 0, cx, cy, radius);
  bg.addColorStop(0, '#2a3820');
  bg.addColorStop(0.7, '#1e2a18');
  bg.addColorStop(1, '#141e10');
  ctx.fillStyle = bg;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.fill();

  ctx.strokeStyle = 'rgba(201, 162, 87, 0.08)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(cx, cy - radius);
  ctx.lineTo(cx, cy + radius);
  ctx.moveTo(cx - radius, cy);
  ctx.lineTo(cx + radius, cy);
  ctx.stroke();

  ctx.strokeStyle = 'rgba(201, 162, 87, 0.12)';
  ctx.beginPath();
  ctx.arc(cx, cy, radius * 0.5, 0, Math.PI * 2);
  ctx.stroke();

  ctx.strokeStyle = 'rgba(201, 162, 87, 0.35)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.stroke();

  ctx.font = '8px "Cinzel", serif';
  ctx.fillStyle = 'rgba(201, 162, 87, 0.5)';
  ctx.textAlign = 'center';
  ctx.fillText('N', cx, cy - radius + 10);
  ctx.fillText('S', cx, cy + radius - 4);
  ctx.fillText('E', cx + radius - 6, cy + 3);
  ctx.fillText('W', cx - radius + 6, cy + 3);
}

function drawMapMarker(
  ctx: CanvasRenderingContext2D,
  marker: MapMarker,
  playerPosition: { x: number; z: number },
  cx: number,
  cy: number,
  radius: number,
) {
  const dx = marker.position.x - playerPosition.x;
  const dz = marker.position.z - playerPosition.z;
  const worldDistance = Math.hypot(dx, dz);
  if (worldDistance > EDGE_RANGE && !marker.focused) return;

  if (worldDistance > RANGE) {
    if (!marker.priority && marker.kind !== 'exits') return;
    drawEdgeMarker(ctx, marker, dx, dz, worldDistance, cx, cy, radius);
    return;
  }

  const x = cx + (dx / RANGE) * radius;
  const y = cy + (dz / RANGE) * radius;
  drawMarkerShape(ctx, marker, x, y, marker.priority ? 4.5 : 3);
}

function drawEdgeMarker(
  ctx: CanvasRenderingContext2D,
  marker: MapMarker,
  dx: number,
  dz: number,
  worldDistance: number,
  cx: number,
  cy: number,
  radius: number,
) {
  const nx = dx / worldDistance;
  const nz = dz / worldDistance;
  const x = cx + nx * (radius - 8);
  const y = cy + nz * (radius - 8);
  const angle = Math.atan2(nz, nx);

  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(angle + Math.PI / 2);
  ctx.globalAlpha = marker.priority ? 0.95 : 0.72;
  ctx.fillStyle = marker.color;
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.85)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, -6);
  ctx.lineTo(5, 5);
  ctx.lineTo(-5, 5);
  ctx.closePath();
  ctx.stroke();
  ctx.fill();
  ctx.restore();

  if (!marker.edgeLabel) return;
  ctx.save();
  ctx.font = '8px "Cinzel", serif';
  ctx.textAlign = 'center';
  ctx.fillStyle = 'rgba(230, 220, 192, 0.82)';
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.9)';
  ctx.lineWidth = 2;
  const labelX = cx + nx * (radius - 22);
  const labelY = cy + nz * (radius - 22);
  ctx.strokeText(marker.edgeLabel, labelX, labelY + 3);
  ctx.fillText(marker.edgeLabel, labelX, labelY + 3);
  ctx.restore();
}

function drawMarkerShape(
  ctx: CanvasRenderingContext2D,
  marker: MapMarker,
  x: number,
  y: number,
  size: number,
) {
  ctx.save();
  ctx.fillStyle = marker.color;
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.85)';
  ctx.lineWidth = 1.5;

  if (marker.priority) {
    ctx.strokeStyle = 'rgba(240, 216, 128, 0.55)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(x, y, size + 3, 0, Math.PI * 2);
    ctx.stroke();
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.85)';
    ctx.lineWidth = 1.5;
  }

  switch (marker.shape) {
    case 'square':
      ctx.strokeRect(x - size, y - size, size * 2, size * 2);
      ctx.fillRect(x - size, y - size, size * 2, size * 2);
      break;
    case 'diamond':
      ctx.translate(x, y);
      ctx.rotate(Math.PI / 4);
      ctx.strokeRect(-size, -size, size * 2, size * 2);
      ctx.fillRect(-size, -size, size * 2, size * 2);
      break;
    case 'triangle':
      ctx.beginPath();
      ctx.moveTo(x, y - size - 1);
      ctx.lineTo(x + size + 1, y + size);
      ctx.lineTo(x - size - 1, y + size);
      ctx.closePath();
      ctx.stroke();
      ctx.fill();
      break;
    case 'glyph':
      ctx.font = 'bold 13px "Cinzel", serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.95)';
      ctx.lineWidth = 3;
      ctx.strokeText(marker.glyph ?? '?', x, y);
      ctx.fillText(marker.glyph ?? '?', x, y);
      break;
    case 'circle':
    default:
      ctx.beginPath();
      ctx.arc(x, y, size, 0, Math.PI * 2);
      ctx.stroke();
      ctx.fill();
      if (marker.glyph) {
        ctx.font = 'bold 7px "Cinzel", serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#0a0805';
        ctx.fillText(marker.glyph, x, y + 0.5);
      }
      break;
  }

  ctx.restore();
}

function drawPlayer(ctx: CanvasRenderingContext2D, cx: number, cy: number) {
  ctx.fillStyle = '#e6c570';
  ctx.save();
  ctx.translate(cx, cy);
  ctx.rotate(Math.PI / 4);
  ctx.fillRect(-3, -3, 6, 6);
  ctx.restore();

  ctx.strokeStyle = 'rgba(230, 197, 112, 0.3)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(cx, cy, 6, 0, Math.PI * 2);
  ctx.stroke();
}

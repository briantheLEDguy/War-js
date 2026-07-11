import { useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, PointerEvent } from 'react';
import type { Game } from '../../game/Game';
import { useGameStore, type EnemyState } from '../../state/gameStore';
import type {
  PathDefinition,
  PropSpawn,
  RvrObjectiveDefinition,
  ZoneDefinition,
} from '../../world/ZoneLoader';
import {
  buildMarkers,
  DEFAULT_VISIBLE,
  MAP_MARKER_LEGEND,
  type MapMarker,
  type MarkerToggle,
  type ZoneExitMarker,
} from './mapData';
import { useDraggableWindow } from './useDraggableWindow';

interface Props {
  game: Game | null;
}

type WorldMapLayer = MarkerToggle | 'terrain' | 'landmarks';

const DEFAULT_WORLD_MAP_LAYERS: Record<WorldMapLayer, boolean> = {
  terrain: true,
  landmarks: true,
  ...DEFAULT_VISIBLE,
};

const WORLD_MAP_LAYERS: Array<{ key: WorldMapLayer; label: string; color: string }> = [
  { key: 'terrain', label: 'Terrain', color: '#9ea770' },
  { key: 'landmarks', label: 'Camps', color: '#d4b060' },
  ...MAP_MARKER_LEGEND,
];

interface Point {
  x: number;
  y: number;
}

interface Projection {
  size: number;
  scale: number;
  left: number;
  top: number;
  width: number;
  height: number;
  toCanvas: (position: { x: number; z: number }) => Point;
}

interface MapHoverTarget {
  id: string;
  label: string;
  detail?: string;
  kind: string;
  color: string;
  priority?: boolean;
  position: Point;
  radius: number;
}

export function WorldMapPanel({ game }: Props) {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLElement>({ draggedPosition: 'fixed' });
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef(0);
  const hoverTargetsRef = useRef<MapHoverTarget[]>([]);
  const zone = game?.zoneDefinition ?? null;
  const enemies = useGameStore((state) => state.enemies);
  const character = useGameStore((state) => state.character);
  const npcs = useGameStore((state) => state.npcs);
  const quests = useGameStore((state) => state.quests);
  const setWorldMapOpen = useGameStore((state) => state.setWorldMapOpen);
  const [layers, setLayers] = useState<Record<WorldMapLayer, boolean>>(DEFAULT_WORLD_MAP_LAYERS);
  const [hoveredLocation, setHoveredLocation] = useState<MapHoverTarget | null>(null);

  const markerVisible = useMemo<Record<MarkerToggle, boolean>>(() => ({
    quests: layers.quests,
    npcs: layers.npcs,
    crafting: layers.crafting,
    resources: layers.resources,
    enemies: layers.enemies,
    exits: layers.exits,
  }), [layers]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !zone) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const size = prepareCanvas(canvas, ctx);
      hoverTargetsRef.current = drawWorldMap(ctx, {
        character,
        enemies: enemies.length > 0 ? enemies : zoneEnemyFallbacks(zone),
        game,
        height: size.height,
        layers,
        markerVisible,
        npcs,
        quests,
        width: size.width,
        zone,
      });
      rafRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(rafRef.current);
  }, [character, enemies, game, layers, markerVisible, npcs, quests, zone]);

  const stats = useMemo(() => zone ? zoneStats(zone, enemies) : null, [enemies, zone]);
  const landmarks = useMemo(() => zone ? landmarkRows(zone) : [], [zone]);

  function toggleLayer(key: WorldMapLayer) {
    setLayers((current) => ({ ...current, [key]: !current[key] }));
  }

  function close() {
    setWorldMapOpen(false);
  }

  function handleMapPointerMove(event: PointerEvent<HTMLCanvasElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    const target = findMapHoverTarget(
      hoverTargetsRef.current,
      event.clientX - rect.left,
      event.clientY - rect.top,
    );
    setHoveredLocation((current) => current?.id === target?.id ? current : target);
  }

  function clearMapHover() {
    setHoveredLocation(null);
  }

  return (
    <div
      className="world-map-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) close();
      }}
    >
      <section
        ref={panelRef}
        className={`world-map-panel panel${dragClassName}`}
        style={dragStyle}
        aria-labelledby="world-map-title"
      >
        <header className="world-map-header draggable-window-handle" {...dragHandleProps}>
          <div>
            <h2 id="world-map-title">{zone?.name ?? 'World Map'}</h2>
            <span>{zone?.campaign ? `${zone.campaign.levelBand} - ${zone.campaign.laneLabel}` : character?.zoneId ?? 'Unknown zone'}</span>
          </div>
          <button type="button" onClick={close}>Close</button>
        </header>

        <div className="world-map-body">
          <div className="world-map-canvas-frame">
            {zone ? (
              <>
                <canvas
                  ref={canvasRef}
                  aria-label={`${zone.name} detailed map`}
                  onPointerMove={handleMapPointerMove}
                  onPointerLeave={clearMapHover}
                />
                {hoveredLocation && (
                  <div
                    className={`world-map-hover-card${hoveredLocation.position.y < 120 ? ' below' : ''}`}
                    role="status"
                    style={{
                      left: `clamp(84px, ${hoveredLocation.position.x}px, calc(100% - 84px))`,
                      top: hoveredLocation.position.y,
                    }}
                  >
                    <span style={{ '--marker-color': hoveredLocation.color } as CSSProperties}>
                      {hoveredLocation.kind}
                    </span>
                    <strong>{hoveredLocation.label}</strong>
                    {hoveredLocation.detail && <small>{hoveredLocation.detail}</small>}
                  </div>
                )}
              </>
            ) : (
              <div className="world-map-empty">Map data unavailable.</div>
            )}
          </div>

          <aside className="world-map-sidebar" aria-label="World map data">
            <section className="world-map-sidebar-section">
              <h3>Layers</h3>
              <div className="world-map-layer-list">
                {WORLD_MAP_LAYERS.map((item) => (
                  <label
                    className={`world-map-layer${layers[item.key] ? ' active' : ''}`}
                    key={item.key}
                  >
                    <input
                      type="checkbox"
                      checked={layers[item.key]}
                      onChange={() => toggleLayer(item.key)}
                    />
                    <span
                      className="world-map-swatch"
                      style={{ '--marker-color': item.color } as CSSProperties}
                    />
                    {item.label}
                  </label>
                ))}
              </div>
            </section>

            {stats && (
              <section className="world-map-sidebar-section">
                <h3>Zone</h3>
                <dl className="world-map-stats">
                  <div><dt>Size</dt><dd>{stats.size}</dd></div>
                  <div><dt>Roads</dt><dd>{stats.roads}</dd></div>
                  <div><dt>Landmarks</dt><dd>{stats.landmarks}</dd></div>
                  <div><dt>Hostiles</dt><dd>{stats.enemies}</dd></div>
                  <div><dt>Exits</dt><dd>{stats.exits}</dd></div>
                </dl>
              </section>
            )}

            {landmarks.length > 0 && (
              <section className="world-map-sidebar-section">
                <h3>Landmarks</h3>
                <ul className="world-map-landmark-list">
                  {landmarks.slice(0, 8).map((row) => (
                    <li key={row.id}>
                      <span>{row.kind}</span>
                      <strong>{row.label}</strong>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </aside>
        </div>
      </section>
    </div>
  );
}

function drawWorldMap(
  ctx: CanvasRenderingContext2D,
  input: {
    character: ReturnType<typeof useGameStore.getState>['character'];
    enemies: EnemyState[];
    game: Game | null;
    height: number;
    layers: Record<WorldMapLayer, boolean>;
    markerVisible: Record<MarkerToggle, boolean>;
    npcs: ReturnType<typeof useGameStore.getState>['npcs'];
    quests: ReturnType<typeof useGameStore.getState>['quests'];
    width: number;
    zone: ZoneDefinition;
  },
): MapHoverTarget[] {
  const { ctxWidth, ctxHeight } = { ctxWidth: input.width, ctxHeight: input.height };
  ctx.clearRect(0, 0, ctxWidth, ctxHeight);
  ctx.fillStyle = '#070604';
  ctx.fillRect(0, 0, ctxWidth, ctxHeight);

  const projection = createProjection(input.zone, ctxWidth, ctxHeight);
  const playerPosition = input.game
    ? { x: input.game.playerPos.x, z: input.game.playerPos.z }
    : {
        x: input.character?.position.x ?? input.zone.spawnPoint?.x ?? 0,
        z: input.character?.position.z ?? input.zone.spawnPoint?.z ?? 0,
      };
  const exits = zoneExitMarkers(input.zone);
  const craftingStations = input.game?.craftingStationMarkers ?? zoneCraftingMarkers(input.zone);
  const resourceNodes = input.game?.resourceNodeMarkers ?? zoneResourceMarkers(input.zone);
  const markers = buildMarkers({
    character: input.character,
    craftingStations,
    enemies: input.enemies,
    exits,
    npcs: input.npcs,
    playerPosition,
    quests: input.quests,
    resourceNodes,
    visible: input.markerVisible,
  });

  drawTerrain(ctx, input.zone, projection, input.layers.terrain);
  drawMapGrid(ctx, input.zone, projection);
  if (input.layers.terrain) drawPaths(ctx, input.zone.paths ?? [], projection);
  if (input.layers.terrain || input.layers.landmarks) drawProps(ctx, input.zone, projection, input.layers);
  if (input.layers.landmarks) drawObjectives(ctx, input.zone, projection);
  if (input.layers.exits) drawZoneExits(ctx, exits, projection);
  if (input.zone.spawnPoint) drawSpawnPoint(ctx, input.zone.spawnPoint, projection);

  for (const marker of markers) {
    drawWorldMarker(ctx, marker, projection);
  }
  drawPlayerMarker(ctx, playerPosition, projection);
  drawCompass(ctx, projection);
  drawScale(ctx, projection);

  return buildMapHoverTargets(input.zone, projection, markers, input.layers);
}

function buildMapHoverTargets(
  zone: ZoneDefinition,
  projection: Projection,
  markers: MapMarker[],
  layers: Record<WorldMapLayer, boolean>,
): MapHoverTarget[] {
  const targets: MapHoverTarget[] = [];

  if (layers.landmarks) {
    for (const prop of zone.props ?? []) {
      if (isTerrainProp(prop) || !shouldLabelProp(prop)) continue;
      targets.push({
        id: `prop-${prop.id ?? `${prop.kind}-${prop.x}-${prop.z}`}`,
        label: propLabel(prop, zone.id),
        detail: propKind(prop.kind),
        kind: 'Landmark',
        color: '#d4b060',
        position: projection.toCanvas(prop),
        radius: Math.max(10, (prop.scale ?? 1) * projection.scale * 8),
      });
    }

    for (const objective of zone.rvrObjectives ?? []) {
      targets.push({
        id: `objective-${objective.id}`,
        label: objective.label,
        detail: objectiveKind(objective),
        kind: 'Objective',
        color: objective.defaultRealm === 'aegis' ? '#72a6d8' : '#d06161',
        priority: true,
        position: projection.toCanvas(objective),
        radius: Math.max(14, objective.captureRadius * projection.scale),
      });
    }
  }

  for (const marker of markers) {
    if (!marker.label) continue;
    targets.push({
      id: marker.id,
      label: marker.label,
      detail: [marker.detail, marker.edgeLabel].filter(Boolean).join(' · '),
      kind: markerKindLabel(marker.kind),
      color: marker.color,
      priority: marker.priority,
      position: projection.toCanvas(marker.position),
      radius: marker.priority ? 15 : 11,
    });
  }

  return targets;
}

function findMapHoverTarget(
  targets: MapHoverTarget[],
  x: number,
  y: number,
): MapHoverTarget | null {
  let nearest: MapHoverTarget | null = null;
  let nearestDistance = Number.POSITIVE_INFINITY;

  for (const target of targets) {
    const distance = Math.hypot(target.position.x - x, target.position.y - y);
    if (distance > target.radius) continue;
    const isPreferred = target.priority && !nearest?.priority;
    if (isPreferred || (!isPreferred && distance < nearestDistance)) {
      nearest = target;
      nearestDistance = distance;
    }
  }

  return nearest;
}

function markerKindLabel(kind: MapMarker['kind']): string {
  switch (kind) {
    case 'quests': return 'Quest';
    case 'npcs': return 'NPC';
    case 'crafting': return 'Crafting';
    case 'resources': return 'Resource';
    case 'enemies': return 'Foe';
    case 'exits': return 'Exit';
    default: return 'Location';
  }
}

function prepareCanvas(canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D): { width: number; height: number } {
  const rect = canvas.getBoundingClientRect();
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(320, Math.floor(rect.width));
  const height = Math.max(260, Math.floor(rect.height));
  const backingWidth = Math.floor(width * pixelRatio);
  const backingHeight = Math.floor(height * pixelRatio);

  if (canvas.width !== backingWidth || canvas.height !== backingHeight) {
    canvas.width = backingWidth;
    canvas.height = backingHeight;
  }

  ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  return { width, height };
}

function createProjection(zone: ZoneDefinition, width: number, height: number): Projection {
  const size = Math.max(zone.size || 120, 60);
  const padding = Math.max(28, Math.min(54, Math.min(width, height) * 0.08));
  const mapPixels = Math.max(1, Math.min(width - padding * 2, height - padding * 2));
  const left = (width - mapPixels) / 2;
  const top = (height - mapPixels) / 2;
  const scale = mapPixels / size;
  const centerX = left + mapPixels / 2;
  const centerY = top + mapPixels / 2;

  return {
    size,
    scale,
    left,
    top,
    width: mapPixels,
    height: mapPixels,
    toCanvas: (position) => ({
      x: centerX + position.x * scale,
      y: centerY + position.z * scale,
    }),
  };
}

function drawTerrain(
  ctx: CanvasRenderingContext2D,
  zone: ZoneDefinition,
  projection: Projection,
  showDetail: boolean,
) {
  ctx.save();
  clipMap(ctx, projection);
  ctx.fillStyle = zone.flatTerrain ? '#242521' : '#23331f';
  ctx.fillRect(projection.left, projection.top, projection.width, projection.height);

  if (showDetail) {
    if (zone.flatTerrain) drawCityTerrain(ctx, zone, projection);
    else drawNaturalTerrain(ctx, zone, projection);
  }

  ctx.restore();

  ctx.strokeStyle = 'rgba(240, 216, 128, 0.58)';
  ctx.lineWidth = 2;
  ctx.strokeRect(projection.left, projection.top, projection.width, projection.height);
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.5)';
  ctx.lineWidth = 1;
  ctx.strokeRect(projection.left + 3, projection.top + 3, projection.width - 6, projection.height - 6);
}

function drawNaturalTerrain(ctx: CanvasRenderingContext2D, zone: ZoneDefinition, projection: Projection) {
  const half = projection.size / 2;
  const cells = 38;
  const step = projection.size / cells;

  for (let ix = 0; ix < cells; ix++) {
    for (let iz = 0; iz < cells; iz++) {
      const x = -half + ix * step;
      const z = -half + iz * step;
      const value = terrainValue(x + step / 2, z + step / 2, zone.id);
      const moisture = Math.cos((x - z) * 0.028 + zone.id.length);
      ctx.fillStyle = terrainColor(value, moisture);
      const p = projection.toCanvas({ x, z });
      ctx.fillRect(p.x, p.y, Math.ceil(step * projection.scale) + 1, Math.ceil(step * projection.scale) + 1);
    }
  }

  ctx.strokeStyle = 'rgba(232, 220, 180, 0.12)';
  ctx.lineWidth = 1;
  for (let z = -half + step * 3; z < half; z += step * 4) {
    ctx.beginPath();
    for (let i = 0; i <= 72; i++) {
      const x = -half + (i / 72) * projection.size;
      const waveZ = z + Math.sin(x * 0.035 + z * 0.015) * step * 0.65;
      const p = projection.toCanvas({ x, z: waveZ });
      if (i === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
  }
}

function drawCityTerrain(ctx: CanvasRenderingContext2D, zone: ZoneDefinition, projection: Projection) {
  const gradient = ctx.createRadialGradient(
    projection.left + projection.width * 0.5,
    projection.top + projection.height * 0.48,
    projection.width * 0.05,
    projection.left + projection.width * 0.5,
    projection.top + projection.height * 0.5,
    projection.width * 0.7,
  );
  gradient.addColorStop(0, '#30332d');
  gradient.addColorStop(0.6, '#292c27');
  gradient.addColorStop(1, '#232621');
  ctx.fillStyle = gradient;
  ctx.fillRect(projection.left, projection.top, projection.width, projection.height);

  ctx.save();
  clipMap(ctx, projection);
  const structuralProps = (zone.props ?? []).filter((prop) => !isTerrainProp(prop));
  ctx.fillStyle = 'rgba(121, 102, 69, 0.16)';
  for (const prop of structuralProps) {
    const point = projection.toCanvas(prop);
    const radius = Math.max(8, (prop.scale ?? 1) * projection.scale * 7);
    ctx.beginPath();
    ctx.ellipse(point.x, point.y, radius * 1.55, radius, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  // Broad contour lines preserve a sense of connected districts without making
  // the terrain a grid of equal visual-weight rectangles.
  ctx.strokeStyle = 'rgba(202, 197, 178, 0.08)';
  ctx.lineWidth = 1;
  const half = projection.size / 2;
  const contourStep = projection.size / 6;
  for (let x = -half + contourStep; x < half; x += contourStep) {
    ctx.beginPath();
    for (let i = 0; i <= 32; i += 1) {
      const z = -half + (i / 32) * projection.size;
      const waveX = x + Math.sin(z * 0.035 + zone.id.length) * 3.5;
      const point = projection.toCanvas({ x: waveX, z });
      if (i === 0) ctx.moveTo(point.x, point.y);
      else ctx.lineTo(point.x, point.y);
    }
    ctx.stroke();
  }
  for (let z = -half + contourStep; z < half; z += contourStep) {
    ctx.beginPath();
    for (let i = 0; i <= 32; i += 1) {
      const x = -half + (i / 32) * projection.size;
      const waveZ = z + Math.cos(x * 0.03 + zone.id.length) * 3.5;
      const point = projection.toCanvas({ x, z: waveZ });
      if (i === 0) ctx.moveTo(point.x, point.y);
      else ctx.lineTo(point.x, point.y);
    }
    ctx.stroke();
  }

  const center = projection.toCanvas({ x: 0, z: 0 });
  ctx.fillStyle = 'rgba(184, 166, 118, 0.1)';
  ctx.beginPath();
  ctx.arc(center.x, center.y, projection.width * 0.1, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}

function drawMapGrid(ctx: CanvasRenderingContext2D, zone: ZoneDefinition, projection: Projection) {
  const half = projection.size / 2;
  const step = projection.size / 4;
  ctx.save();
  clipMap(ctx, projection);
  ctx.strokeStyle = 'rgba(240, 216, 128, 0.1)';
  ctx.lineWidth = 1;
  for (let x = -half + step; x < half; x += step) {
    const a = projection.toCanvas({ x, z: -half });
    const b = projection.toCanvas({ x, z: half });
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  for (let z = -half + step; z < half; z += step) {
    const a = projection.toCanvas({ x: -half, z });
    const b = projection.toCanvas({ x: half, z });
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  ctx.restore();

  ctx.font = '10px "Cinzel", serif';
  ctx.fillStyle = 'rgba(230, 220, 192, 0.62)';
  ctx.textAlign = 'center';
  ctx.fillText(zone.name, projection.left + projection.width / 2, projection.top - 14);
}

function drawPaths(ctx: CanvasRenderingContext2D, paths: PathDefinition[], projection: Projection) {
  ctx.save();
  clipMap(ctx, projection);
  for (const path of paths) {
    if (path.points.length < 2) continue;
    const width = Math.max(3, path.width * projection.scale);
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.strokeStyle = 'rgba(12, 10, 8, 0.72)';
    ctx.lineWidth = width + 4;
    strokePath(ctx, path, projection);
    ctx.strokeStyle = path.style === 'cobblestone_avenue'
      ? 'rgba(162, 155, 130, 0.8)'
      : 'rgba(118, 86, 45, 0.82)';
    ctx.lineWidth = width;
    strokePath(ctx, path, projection);
    ctx.setLineDash([Math.max(6, width * 1.1), Math.max(5, width * 0.8)]);
    ctx.strokeStyle = path.style === 'cobblestone_avenue'
      ? 'rgba(234, 225, 190, 0.22)'
      : 'rgba(236, 195, 120, 0.18)';
    ctx.lineWidth = 1;
    strokePath(ctx, path, projection);
    ctx.setLineDash([]);
  }
  ctx.restore();
}

function strokePath(ctx: CanvasRenderingContext2D, path: PathDefinition, projection: Projection) {
  ctx.beginPath();
  path.points.forEach((point, index) => {
    const p = projection.toCanvas(point);
    if (index === 0) ctx.moveTo(p.x, p.y);
    else ctx.lineTo(p.x, p.y);
  });
  ctx.stroke();
}

function drawProps(
  ctx: CanvasRenderingContext2D,
  zone: ZoneDefinition,
  projection: Projection,
  layers: Record<WorldMapLayer, boolean>,
) {
  ctx.save();
  clipMap(ctx, projection);
  for (const prop of zone.props ?? []) {
    if ((prop.kind === 'tree' || prop.kind === 'rock' || prop.kind.startsWith('pnw_')) && !layers.terrain) {
      continue;
    }
    if (!isTerrainProp(prop) && !layers.landmarks) continue;
      drawProp(ctx, prop, projection);
  }
  ctx.restore();
}

function drawProp(
  ctx: CanvasRenderingContext2D,
  prop: PropSpawn,
  projection: Projection,
) {
  const p = projection.toCanvas(prop);
  const scale = Math.max(0.65, prop.scale ?? 1);

  switch (prop.kind) {
    case 'tree':
    case 'pnw_low_shrub':
      drawTree(ctx, p, scale);
      break;
    case 'rock':
      drawRock(ctx, p, scale);
      break;
    case 'banner_post':
      drawBanner(ctx, p, scale);
      break;
    case 'gate':
    case 'castle_gate':
    case 'castle_door':
      drawGate(ctx, p, prop.rotY ?? 0, scale);
      break;
    case 'tower':
      drawTower(ctx, p, scale);
      break;
    case 'castle':
      drawCastle(ctx, p, prop.rotY ?? 0, scale);
      break;
    case 'bridge':
    case 'dock':
      drawBridge(ctx, p, prop.rotY ?? 0, scale);
      break;
    case 'building':
    case 'vendor_stall':
    case 'fountain':
    case 'statue':
    case 'wall_segment':
    case 'dummy':
    default:
      drawStructure(ctx, p, prop.rotY ?? 0, scale, prop.kind);
      break;
  }
}

function drawObjectives(ctx: CanvasRenderingContext2D, zone: ZoneDefinition, projection: Projection) {
  ctx.save();
  clipMap(ctx, projection);
  for (const objective of zone.rvrObjectives ?? []) {
    const p = projection.toCanvas(objective);
    const radius = Math.max(12, objective.captureRadius * projection.scale);
    const color = objective.defaultRealm === 'aegis' ? '#72a6d8' : '#d06161';
    ctx.fillStyle = colorWithAlpha(color, 0.13);
    ctx.strokeStyle = colorWithAlpha(color, 0.72);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

function drawZoneExits(ctx: CanvasRenderingContext2D, exits: ZoneExitMarker[], projection: Projection) {
  ctx.save();
  clipMap(ctx, projection);
  for (const exit of exits) {
    const p = projection.toCanvas(exit.position);
    ctx.fillStyle = '#84a7ff';
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.85)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(p.x, p.y - 8);
    ctx.lineTo(p.x + 7, p.y + 6);
    ctx.lineTo(p.x - 7, p.y + 6);
    ctx.closePath();
    ctx.stroke();
    ctx.fill();
  }
  ctx.restore();
}

function drawSpawnPoint(
  ctx: CanvasRenderingContext2D,
  spawnPoint: { x: number; z: number },
  projection: Projection,
) {
  const p = projection.toCanvas(spawnPoint);
  ctx.save();
  ctx.strokeStyle = 'rgba(240, 216, 128, 0.9)';
  ctx.fillStyle = 'rgba(240, 216, 128, 0.18)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(p.x, p.y, 8, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

function drawWorldMarker(
  ctx: CanvasRenderingContext2D,
  marker: MapMarker,
  projection: Projection,
) {
  const p = projection.toCanvas(marker.position);
  const size = marker.priority ? 6 : 4.5;
  if (
    p.x < projection.left - 8 ||
    p.x > projection.left + projection.width + 8 ||
    p.y < projection.top - 8 ||
    p.y > projection.top + projection.height + 8
  ) return;

  drawMarkerShape(ctx, marker, p.x, p.y, size);
}

function drawPlayerMarker(
  ctx: CanvasRenderingContext2D,
  playerPosition: { x: number; z: number },
  projection: Projection,
) {
  const p = projection.toCanvas(playerPosition);
  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.fillStyle = '#ffe08a';
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.9)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(0, -10);
  ctx.lineTo(8, 8);
  ctx.lineTo(0, 4);
  ctx.lineTo(-8, 8);
  ctx.closePath();
  ctx.stroke();
  ctx.fill();
  ctx.restore();
  drawMapLabel(ctx, p.x, p.y - 16, 'You', '#ffe08a');
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
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.88)';
  ctx.lineWidth = 1.8;

  if (marker.priority) {
    ctx.strokeStyle = 'rgba(240, 216, 128, 0.62)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(x, y, size + 5, 0, Math.PI * 2);
    ctx.stroke();
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.88)';
    ctx.lineWidth = 1.8;
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
      ctx.moveTo(x, y - size - 2);
      ctx.lineTo(x + size + 2, y + size + 1);
      ctx.lineTo(x - size - 2, y + size + 1);
      ctx.closePath();
      ctx.stroke();
      ctx.fill();
      break;
    case 'glyph':
      ctx.font = 'bold 18px "Cinzel", serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.95)';
      ctx.lineWidth = 4;
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
        ctx.font = 'bold 8px "Cinzel", serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#0a0805';
        ctx.fillText(marker.glyph, x, y + 0.5);
      }
      break;
  }

  ctx.restore();
}

function drawTree(ctx: CanvasRenderingContext2D, p: Point, scale: number) {
  const size = 3.5 * scale;
  ctx.fillStyle = 'rgba(33, 91, 43, 0.82)';
  ctx.strokeStyle = 'rgba(8, 18, 8, 0.82)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
}

function drawRock(ctx: CanvasRenderingContext2D, p: Point, scale: number) {
  const size = 3 * scale;
  ctx.fillStyle = 'rgba(133, 129, 112, 0.78)';
  ctx.strokeStyle = 'rgba(18, 16, 14, 0.78)';
  ctx.beginPath();
  ctx.moveTo(p.x, p.y - size);
  ctx.lineTo(p.x + size * 1.2, p.y);
  ctx.lineTo(p.x + size * 0.35, p.y + size);
  ctx.lineTo(p.x - size, p.y + size * 0.55);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
}

function drawBanner(ctx: CanvasRenderingContext2D, p: Point, scale: number) {
  const size = 7 * scale;
  ctx.strokeStyle = '#1a1209';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(p.x, p.y - size);
  ctx.lineTo(p.x, p.y + size);
  ctx.stroke();
  ctx.fillStyle = '#d4b060';
  ctx.beginPath();
  ctx.moveTo(p.x, p.y - size);
  ctx.lineTo(p.x + size * 0.85, p.y - size * 0.48);
  ctx.lineTo(p.x, p.y);
  ctx.closePath();
  ctx.fill();
}

function drawGate(ctx: CanvasRenderingContext2D, p: Point, rotY: number, scale: number) {
  drawRotated(ctx, p, rotY, () => {
    ctx.fillStyle = '#5f4c2e';
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.88)';
    ctx.lineWidth = 2;
    ctx.fillRect(-10 * scale, -4 * scale, 20 * scale, 8 * scale);
    ctx.strokeRect(-10 * scale, -4 * scale, 20 * scale, 8 * scale);
    ctx.fillStyle = '#14100c';
    ctx.fillRect(-4 * scale, -3 * scale, 8 * scale, 6 * scale);
  });
}

function drawTower(ctx: CanvasRenderingContext2D, p: Point, scale: number) {
  ctx.fillStyle = '#6c6556';
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.88)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(p.x, p.y, 7 * scale, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
}

function drawCastle(ctx: CanvasRenderingContext2D, p: Point, rotY: number, scale: number) {
  drawRotated(ctx, p, rotY, () => {
    ctx.fillStyle = '#6a5d48';
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.88)';
    ctx.lineWidth = 2;
    ctx.fillRect(-15 * scale, -10 * scale, 30 * scale, 20 * scale);
    ctx.strokeRect(-15 * scale, -10 * scale, 30 * scale, 20 * scale);
    ctx.fillStyle = '#80765f';
    ctx.fillRect(-20 * scale, -14 * scale, 8 * scale, 8 * scale);
    ctx.fillRect(12 * scale, -14 * scale, 8 * scale, 8 * scale);
    ctx.strokeRect(-20 * scale, -14 * scale, 8 * scale, 8 * scale);
    ctx.strokeRect(12 * scale, -14 * scale, 8 * scale, 8 * scale);
  });
}

function drawBridge(ctx: CanvasRenderingContext2D, p: Point, rotY: number, scale: number) {
  drawRotated(ctx, p, rotY, () => {
    ctx.fillStyle = '#6f5637';
    ctx.strokeStyle = 'rgba(0, 0, 0, 0.78)';
    ctx.lineWidth = 1.5;
    ctx.fillRect(-15 * scale, -4 * scale, 30 * scale, 8 * scale);
    ctx.strokeRect(-15 * scale, -4 * scale, 30 * scale, 8 * scale);
  });
}

function drawStructure(ctx: CanvasRenderingContext2D, p: Point, rotY: number, scale: number, kind: string) {
  drawRotated(ctx, p, rotY, () => {
    ctx.fillStyle = kind === 'fountain'
      ? 'rgba(111, 145, 162, 0.78)'
      : kind === 'statue'
        ? 'rgba(152, 144, 120, 0.78)'
        : 'rgba(117, 91, 54, 0.72)';
    ctx.strokeStyle = 'rgba(20, 16, 11, 0.62)';
    ctx.lineWidth = 1;
    if (kind === 'fountain' || kind === 'statue' || kind === 'dummy') {
      ctx.beginPath();
      ctx.arc(0, 0, 6 * scale, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    } else {
      drawRoundedRect(ctx, -7 * scale, -5 * scale, 14 * scale, 10 * scale, 2 * scale);
      ctx.fill();
      ctx.stroke();
    }
  });
}

function drawRoundedRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
) {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + width - r, y);
  ctx.quadraticCurveTo(x + width, y, x + width, y + r);
  ctx.lineTo(x + width, y + height - r);
  ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
  ctx.lineTo(x + r, y + height);
  ctx.quadraticCurveTo(x, y + height, x, y + height - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function drawRotated(ctx: CanvasRenderingContext2D, p: Point, rotY: number, draw: () => void) {
  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.rotate(rotY);
  draw();
  ctx.restore();
}

function drawMapLabel(ctx: CanvasRenderingContext2D, x: number, y: number, text: string, color: string) {
  const clean = compactLabel(text);
  if (!clean) return;
  ctx.save();
  ctx.font = '10px "Cinzel", serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const width = Math.min(220, ctx.measureText(clean).width + 10);
  ctx.fillStyle = 'rgba(6, 5, 4, 0.78)';
  ctx.fillRect(x - width / 2, y - 8, width, 16);
  ctx.strokeStyle = 'rgba(122, 96, 53, 0.55)';
  ctx.strokeRect(x - width / 2, y - 8, width, 16);
  ctx.fillStyle = color;
  ctx.fillText(clean, x, y + 0.5, width - 8);
  ctx.restore();
}

function drawCompass(ctx: CanvasRenderingContext2D, projection: Projection) {
  const x = projection.left + projection.width - 30;
  const y = projection.top + 30;
  ctx.save();
  ctx.strokeStyle = 'rgba(240, 216, 128, 0.75)';
  ctx.fillStyle = 'rgba(240, 216, 128, 0.8)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(x, y - 16);
  ctx.lineTo(x + 5, y + 6);
  ctx.lineTo(x, y + 3);
  ctx.lineTo(x - 5, y + 6);
  ctx.closePath();
  ctx.stroke();
  ctx.fill();
  ctx.font = 'bold 11px "Cinzel", serif';
  ctx.textAlign = 'center';
  ctx.fillText('N', x, y - 21);
  ctx.restore();
}

function drawScale(ctx: CanvasRenderingContext2D, projection: Projection) {
  const units = niceScaleUnits(projection.size);
  const px = units * projection.scale;
  const x = projection.left + 18;
  const y = projection.top + projection.height - 20;
  ctx.save();
  ctx.strokeStyle = 'rgba(240, 216, 128, 0.78)';
  ctx.fillStyle = 'rgba(230, 220, 192, 0.72)';
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + px, y);
  ctx.moveTo(x, y - 5);
  ctx.lineTo(x, y + 5);
  ctx.moveTo(x + px, y - 5);
  ctx.lineTo(x + px, y + 5);
  ctx.stroke();
  ctx.font = '10px "Cinzel", serif';
  ctx.textAlign = 'center';
  ctx.fillText(`${units}m`, x + px / 2, y - 9);
  ctx.restore();
}

function clipMap(ctx: CanvasRenderingContext2D, projection: Projection) {
  ctx.beginPath();
  ctx.rect(projection.left, projection.top, projection.width, projection.height);
  ctx.clip();
}

function terrainValue(x: number, z: number, seed: string): number {
  const seedOffset = seed.length * 0.113;
  return (
    Math.sin(x * 0.026 + seedOffset) * 0.45 +
    Math.cos(z * 0.031 - seedOffset) * 0.38 +
    Math.sin((x + z) * 0.018) * 0.24
  );
}

function terrainColor(value: number, moisture: number): string {
  if (value > 0.58) return 'rgba(108, 101, 84, 0.95)';
  if (value > 0.25) return 'rgba(80, 74, 50, 0.95)';
  if (moisture > 0.52) return 'rgba(36, 72, 42, 0.96)';
  if (value < -0.55) return 'rgba(38, 61, 32, 0.96)';
  return 'rgba(57, 73, 39, 0.96)';
}

function colorWithAlpha(color: string, alpha: number): string {
  const value = color.replace('#', '');
  const r = Number.parseInt(value.slice(0, 2), 16);
  const g = Number.parseInt(value.slice(2, 4), 16);
  const b = Number.parseInt(value.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function zoneExitMarkers(zone: ZoneDefinition): ZoneExitMarker[] {
  return (zone.zoneTriggers ?? []).map((trigger) => ({
    id: trigger.id,
    label: trigger.label,
    targetZoneId: trigger.targetZoneId,
    position: { x: trigger.x, z: trigger.z },
  }));
}

function zoneCraftingMarkers(zone: ZoneDefinition) {
  return (zone.craftingStations ?? []).map((station) => ({
    id: station.id,
    label: station.label,
    kind: station.kind,
    position: { x: station.x, y: station.y ?? 0, z: station.z },
  }));
}

function zoneResourceMarkers(zone: ZoneDefinition) {
  return (zone.resourceNodes ?? []).map((node) => ({
    id: node.id,
    label: node.label,
    kind: node.kind,
    available: true,
    position: { x: node.x, y: node.y ?? 0, z: node.z },
  }));
}

function zoneEnemyFallbacks(zone: ZoneDefinition): EnemyState[] {
  return (zone.enemies ?? []).map((enemy) => ({
    id: enemy.id,
    name: enemy.name,
    level: enemy.level,
    health: enemy.maxHealth,
    maxHealth: enemy.maxHealth,
    position: { x: enemy.x, y: enemy.y ?? 0, z: enemy.z },
    alive: true,
  }));
}

function zoneStats(zone: ZoneDefinition, enemies: EnemyState[]) {
  const structural = (zone.props ?? []).filter((prop) => !isTerrainProp(prop)).length;
  return {
    size: `${zone.size}m`,
    roads: zone.paths?.length ?? 0,
    landmarks: structural + (zone.rvrObjectives?.length ?? 0),
    enemies: enemies.filter((enemy) => enemy.alive).length || (zone.enemies?.length ?? 0),
    exits: zone.zoneTriggers?.length ?? 0,
  };
}

function landmarkRows(zone: ZoneDefinition): Array<{ id: string; kind: string; label: string }> {
  const objectiveRows = (zone.rvrObjectives ?? []).map((objective) => ({
    id: objective.id,
    kind: objectiveKind(objective),
    label: objective.label,
  }));
  const propRows = (zone.props ?? [])
    .filter((prop) => shouldLabelProp(prop))
    .slice(0, 6)
    .map((prop) => ({
      id: prop.id ?? `${prop.kind}-${prop.x}-${prop.z}`,
      kind: propKind(prop.kind),
      label: propLabel(prop, zone.id),
    }));
  const seen = new Set<string>();
  return [...objectiveRows, ...propRows].filter((row) => {
    const key = `${row.kind}:${row.label}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function isTerrainProp(prop: PropSpawn): boolean {
  return prop.kind === 'tree' || prop.kind === 'rock' || prop.kind.startsWith('pnw_');
}

function shouldLabelProp(prop: PropSpawn): boolean {
  return [
    'castle',
    'building',
    'vendor_stall',
    'fountain',
    'statue',
    'dock',
    'bridge',
  ].includes(prop.kind);
}

function propLabel(prop: PropSpawn, zoneId: string): string {
  const raw = prop.id
    ? prop.id.replace(new RegExp(`^${escapeRegExp(zoneId)}_?`), '')
    : prop.kind;
  return titleCase(raw
    .replace(/_visual$/g, '')
    .replace(/portal_.+$/, 'travel gate')
    .replace(/_(left|right|north|south|east|west)$/g, '')
    .replace(/_/g, ' '));
}

function propKind(kind: string): string {
  switch (kind) {
    case 'castle': return 'Keep';
    case 'castle_gate': return 'Gate';
    case 'vendor_stall': return 'Market';
    default: return titleCase(kind.replace(/_/g, ' '));
  }
}

function objectiveKind(objective: RvrObjectiveDefinition): string {
  switch (objective.type) {
    case 'battle_objective': return 'Camp';
    case 'keep': return 'Keep';
    case 'fortress': return 'Fortress';
    case 'city_gate': return 'Gate';
    case 'boss': return 'Lair';
    default: return 'Objective';
  }
}

function compactLabel(text: string): string {
  return text.length > 34 ? `${text.slice(0, 31)}...` : text;
}

function titleCase(text: string): string {
  return text
    .split(' ')
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function niceScaleUnits(size: number): number {
  if (size >= 320) return 100;
  if (size >= 180) return 50;
  return 25;
}

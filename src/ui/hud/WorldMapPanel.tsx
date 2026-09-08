import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, PointerEvent } from 'react';
import type { Game } from '../../game/Game';
import { startForegroundLoop } from '../../game/ForegroundFrameLoop';
import type { CharacterState, QuestProgress } from '../../services/types';
import { useGameStore, type EnemyState } from '../../state/gameStore';
import type {
  PathDefinition,
  PropSpawn,
  RvrObjectiveDefinition,
  ZoneDefinition,
} from '../../world/ZoneLoader';
import type { NpcState } from '../../world/NpcSpawner';
import {
  buildMarkers,
  DEFAULT_VISIBLE,
  MAP_MARKER_LEGEND,
  type MapMarker,
  type MarkerToggle,
  type ZoneExitMarker,
} from './mapData';
import { layoutMapSymbols, mapResolutionScale } from './worldMapPresentation';
import { drawMapFeatures, drawMapWater, mapFeatureRole, mapFeatureVisible, zoneMapFeatures } from './zoneMapGeometry';
import { useDraggableWindow } from './useDraggableWindow';

interface Props {
  game: Game | null;
}

export type WorldMapLayer = MarkerToggle | 'terrain' | 'landmarks';

const DEFAULT_WORLD_MAP_LAYERS: Record<WorldMapLayer, boolean> = {
  terrain: true,
  landmarks: true,
  ...DEFAULT_VISIBLE,
};

const WORLD_MAP_LAYERS: Array<{ key: WorldMapLayer; label: string; color: string }> = [
  { key: 'terrain', label: 'Terrain', color: '#9ea770' },
  { key: 'landmarks', label: 'Buildings', color: '#d4b060' },
  ...MAP_MARKER_LEGEND,
];

interface Point {
  x: number;
  y: number;
}

interface Projection {
  size: number;
  screenScale: number;
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

function LegacyWorldMapPanel({ game }: Props) {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLElement>({ draggedPosition: 'fixed' });
  const canvasRef = useRef<HTMLCanvasElement>(null);
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
        showPlayer: true,
        width: size.width,
        zone,
      });
    };

    return startForegroundLoop(draw, () => 15);
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
    const target = findMapHoverTarget(hoverTargetsRef.current, ...canvasPointerPosition(event));
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

export interface ZoneMapCanvasProps {
  game: Game | null;
  zone: ZoneDefinition | null;
  character: CharacterState | null;
  enemies: EnemyState[];
  npcs: NpcState[];
  quests: QuestProgress[];
  layers: Record<WorldMapLayer, boolean>;
  markerVisible: Record<MarkerToggle, boolean>;
  renderScale: number;
  showPlayer: boolean;
}

export function ZoneMapCanvas({
  game,
  zone,
  character,
  enemies,
  npcs,
  quests,
  layers,
  markerVisible,
  renderScale,
  showPlayer,
}: ZoneMapCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hoverTargetsRef = useRef<MapHoverTarget[]>([]);
  const [hoveredLocation, setHoveredLocation] = useState<MapHoverTarget | null>(null);

  useLayoutEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !zone) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const size = prepareVisibleZoneCanvas(canvas, ctx, renderScale);
      hoverTargetsRef.current = drawWorldMap(ctx, {
        character,
        enemies,
        game,
        height: size.height,
        layers,
        markerVisible,
        npcs,
        quests,
        showPlayer,
        screenScale: renderScale,
        width: size.width,
        zone,
      });
    };

    const viewport = canvas.closest('.campaign-map-viewport');
    // Scroll events run before paint; don't leave the crop following a 15 FPS timer.
    viewport?.addEventListener('scroll', draw, { passive: true });
    const resizeObserver = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(draw);
    if (canvas.parentElement) resizeObserver?.observe(canvas.parentElement);
    draw();
    const stop = startForegroundLoop(draw, () => 15);
    return () => {
      stop();
      viewport?.removeEventListener('scroll', draw);
      resizeObserver?.disconnect();
    };
  }, [character, enemies, game, layers, markerVisible, npcs, quests, renderScale, showPlayer, zone]);

  function handlePointerMove(event: PointerEvent<HTMLCanvasElement>) {
    const target = findMapHoverTarget(hoverTargetsRef.current, ...canvasPointerPosition(event));
    setHoveredLocation((current) => current?.id === target?.id ? current : target);
  }

  return (
    <div className="zone-map-canvas-surface" style={{ '--map-inverse-scale': 1 / Math.max(0.01, renderScale) } as CSSProperties}>
      {zone ? (
        <>
          <canvas
            ref={canvasRef}
            aria-label={`${zone.name} detailed map`}
            onPointerMove={handlePointerMove}
            onPointerLeave={() => setHoveredLocation(null)}
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
  );
}

function canvasPointerPosition(event: PointerEvent<HTMLCanvasElement>): [number, number] {
  const canvas = event.currentTarget;
  const surface = canvas.parentElement?.classList.contains('zone-map-canvas-surface') ? canvas.parentElement : canvas;
  const rect = surface.getBoundingClientRect();
  const scaleX = rect.width / Math.max(1, surface.clientWidth);
  const scaleY = rect.height / Math.max(1, surface.clientHeight);
  return [
    (event.clientX - rect.left) / scaleX,
    (event.clientY - rect.top) / scaleY,
  ];
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
    showPlayer: boolean;
    screenScale?: number;
    width: number;
    zone: ZoneDefinition;
  },
): MapHoverTarget[] {
  const { ctxWidth, ctxHeight } = { ctxWidth: input.width, ctxHeight: input.height };
  ctx.clearRect(0, 0, ctxWidth, ctxHeight);
  ctx.fillStyle = '#070604';
  ctx.fillRect(0, 0, ctxWidth, ctxHeight);

  const projection = createProjection(input.zone, ctxWidth, ctxHeight, input.screenScale);
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
  if (input.layers.terrain) {
    ctx.save(); clipMap(ctx, projection);
    drawMapFeatures(ctx, input.zone, projection, ['nature']);
    drawMapWater(ctx, input.zone, projection);
    drawMapFeatures(ctx, input.zone, projection, ['ground']);
    ctx.restore();
    drawPaths(ctx, input.zone.paths ?? [], projection);
  }
  if (input.layers.terrain || input.layers.landmarks) drawProps(ctx, input.zone, projection, input.layers);
  if (input.layers.landmarks) drawObjectives(ctx, input.zone, projection);
  if (input.zone.spawnPoint) drawSpawnPoint(ctx, input.zone.spawnPoint, projection);

  const targets = buildMapHoverTargets(input.zone, projection, markers, input.layers);
  const symbols = layoutMapSymbols(targets.filter(target => target.kind !== 'Landmark'), projection.screenScale);
  const anchors = new Map(targets.map(target => [target.id, target.position]));
  const markerById = new Map(markers.map(marker => [marker.id, marker]));
  for (const symbol of symbols) {
    const anchor = anchors.get(symbol.id)!;
    ctx.save();
    ctx.strokeStyle = 'rgba(223, 217, 184, 0.5)';
    ctx.lineWidth = 1 / projection.screenScale;
    ctx.beginPath(); ctx.moveTo(anchor.x, anchor.y); ctx.lineTo(symbol.position.x, symbol.position.y); ctx.stroke();
    ctx.translate(symbol.position.x, symbol.position.y);
    ctx.scale(1 / projection.screenScale, 1 / projection.screenScale);
    const marker = markerById.get(symbol.id);
    drawMarkerShape(ctx, marker ?? {
      id: symbol.id, kind: 'npcs', color: symbol.color, shape: 'square', position: { x: 0, z: 0 },
    }, 0, 0, marker?.priority ? 6 : 4.5);
    ctx.restore();
  }
  if (input.showPlayer) drawPlayerMarker(ctx, playerPosition, projection);
  drawCompass(ctx, projection);
  drawScale(ctx, projection);
  drawMapRelief(ctx, projection, input.zone);

  return [...targets.filter(target => target.kind === 'Landmark'), ...symbols];
}

function buildMapHoverTargets(
  zone: ZoneDefinition,
  projection: Projection,
  markers: MapMarker[],
  layers: Record<WorldMapLayer, boolean>,
): MapHoverTarget[] {
  const targets: MapHoverTarget[] = [];

  if (layers.landmarks) {
    for (const feature of zoneMapFeatures(zone)) {
      if (!['building', 'landmark'].includes(feature.role) || !mapFeatureVisible(feature, projection.scale * projection.screenScale)) continue;
      const prop = feature.prop;
      targets.push({
        id: `prop-${prop.id ?? `${prop.kind}-${prop.x}-${prop.z}`}`,
        label: propLabel(prop, zone.id), detail: propKind(prop.kind), kind: 'Landmark', color: '#d4b060',
        position: projection.toCanvas(feature.center),
        radius: Math.max(2 / projection.screenScale, Math.min(feature.width, feature.depth) * projection.scale / 2),
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
        radius: 10 / projection.screenScale,
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
      radius: (marker.priority ? 12 : 9) / projection.screenScale,
    });
  }

  return targets;
}

export function findMapHoverTarget(
  targets: MapHoverTarget[],
  x: number,
  y: number,
): MapHoverTarget | null {
  let nearest: MapHoverTarget | null = null;
  let nearestDistance = Number.POSITIVE_INFINITY;

  for (const target of targets) {
    const distance = Math.hypot(target.position.x - x, target.position.y - y);
    if (distance > target.radius) continue;
    const symbolOverLandmark = nearest?.kind === 'Landmark' && target.kind !== 'Landmark';
    if (symbolOverLandmark || (distance < nearestDistance && !(nearest && nearest.kind !== 'Landmark' && target.kind === 'Landmark'))) {
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

function prepareCanvas(
  canvas: HTMLCanvasElement,
  ctx: CanvasRenderingContext2D,
  renderScale = 1,
): { width: number; height: number } {
  const rect = canvas.getBoundingClientRect();
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  // The canvas may be inside the campaign zoom transform. clientWidth/Height
  // preserve the logical drawing space; getBoundingClientRect() is screen space.
  const width = Math.max(320, Math.floor(canvas.clientWidth || rect.width));
  const height = Math.max(260, Math.floor(canvas.clientHeight || rect.height));
  const resolutionScale = mapResolutionScale(width, height, pixelRatio, renderScale);
  const backingWidth = Math.floor(width * resolutionScale);
  const backingHeight = Math.floor(height * resolutionScale);

  if (canvas.width !== backingWidth || canvas.height !== backingHeight) {
    canvas.width = backingWidth;
    canvas.height = backingHeight;
  }

  ctx.setTransform(resolutionScale, 0, 0, resolutionScale, 0, 0);
  return { width, height };
}

/** Include a screen-space gutter for compositor scrolling between canvas redraws. */
export const MAP_CANVAS_OVERSCAN = 96;

/** Rasterize the buffered viewport, keeping memory independent of the full magnified zone. */
export function prepareVisibleZoneCanvas(canvas: HTMLCanvasElement, ctx: CanvasRenderingContext2D, screenScale: number) {
  const surface = canvas.parentElement;
  const viewport = canvas.closest<HTMLElement>('.campaign-map-viewport');
  if (!surface || !viewport) return prepareCanvas(canvas, ctx, screenScale);
  const scale = Math.max(0.01, screenScale);
  const rect = surface.getBoundingClientRect();
  const view = viewport.getBoundingClientRect();
  const viewLeft = view.left + viewport.clientLeft;
  const viewTop = view.top + viewport.clientTop;
  const left = Math.max(0, (viewLeft - rect.left - MAP_CANVAS_OVERSCAN) / scale);
  const top = Math.max(0, (viewTop - rect.top - MAP_CANVAS_OVERSCAN) / scale);
  const right = Math.min(surface.clientWidth, (viewLeft + viewport.clientWidth - rect.left + MAP_CANVAS_OVERSCAN) / scale);
  const bottom = Math.min(surface.clientHeight, (viewTop + viewport.clientHeight - rect.top + MAP_CANVAS_OVERSCAN) / scale);
  const width = Math.max(1, right - left);
  const height = Math.max(1, bottom - top);
  const pixelScale = Math.min(window.devicePixelRatio || 1, 2) * scale;
  canvas.style.position = 'absolute';
  canvas.style.left = `${left}px`;
  canvas.style.top = `${top}px`;
  canvas.style.width = `${width}px`;
  canvas.style.height = `${height}px`;
  const backingWidth = Math.ceil(width * pixelScale), backingHeight = Math.ceil(height * pixelScale);
  if (canvas.width !== backingWidth || canvas.height !== backingHeight) {
    canvas.width = backingWidth;
    canvas.height = backingHeight;
  }
  // Clear every backing pixel, including rounded crop edges outside scene coordinates.
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#070604';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.setTransform(pixelScale, 0, 0, pixelScale, -left * pixelScale, -top * pixelScale);
  return { width: surface.clientWidth, height: surface.clientHeight };
}

function createProjection(zone: ZoneDefinition, width: number, height: number, screenScale = 1): Projection {
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
    screenScale: Math.max(0.01, screenScale),
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
  ctx.fillStyle = zone.flatTerrain ? '#1c2528' : '#182726';
  ctx.fillRect(projection.left, projection.top, projection.width, projection.height);

  if (showDetail) {
    if (zone.flatTerrain) drawCityTerrain(ctx, zone, projection);
    else drawNaturalTerrain(ctx, zone, projection);
  }

  ctx.restore();

  ctx.strokeStyle = 'rgba(186, 151, 81, 0.72)';
  ctx.lineWidth = 2.5;
  ctx.strokeRect(projection.left, projection.top, projection.width, projection.height);
  ctx.strokeStyle = 'rgba(4, 9, 11, 0.9)';
  ctx.lineWidth = 1;
  ctx.strokeRect(projection.left + 3, projection.top + 3, projection.width - 6, projection.height - 6);
}

const terrainSurfaces = new WeakMap<ZoneDefinition, HTMLCanvasElement>();

function drawNaturalTerrain(ctx: CanvasRenderingContext2D, zone: ZoneDefinition, projection: Projection) {
  let surface = terrainSurfaces.get(zone);
  if (!surface) {
    surface = document.createElement('canvas');
    surface.width = surface.height = 384;
    const terrain = surface.getContext('2d');
    if (!terrain) return;
    const pixels = terrain.createImageData(384, 384);
    for (let y = 0; y < 384; y++) for (let x = 0; x < 384; x++) {
      const wx = (x / 383 - 0.5) * projection.size;
      const wz = (y / 383 - 0.5) * projection.size;
      const height = terrainValue(wx, wz, zone.id);
      const moisture = Math.cos((wx - wz) * 0.028 + zone.id.length);
      const relief = height * 10;
      const contour = Math.pow((Math.cos(height * 27) + 1) / 2, 24) * 3;
      const i = (y * 384 + x) * 4;
      pixels.data[i] = 35 + relief - moisture * 3 + contour;
      pixels.data[i + 1] = 51 + relief + moisture * 3 + contour;
      pixels.data[i + 2] = 46 + relief + contour;
      pixels.data[i + 3] = 255;
    }
    terrain.putImageData(pixels, 0, 0);
    terrainSurfaces.set(zone, surface);
  }
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  ctx.drawImage(surface, projection.left, projection.top, projection.width, projection.height);
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
  gradient.addColorStop(0, '#303a3b');
  gradient.addColorStop(0.6, '#202c30');
  gradient.addColorStop(1, '#111b20');
  ctx.fillStyle = gradient;
  ctx.fillRect(projection.left, projection.top, projection.width, projection.height);

  // The city's actual streets, water and footprints provide its structure.
}

function drawMapGrid(ctx: CanvasRenderingContext2D, zone: ZoneDefinition, projection: Projection) {
  const half = projection.size / 2;
  const step = projection.size / 2;
  ctx.save();
  clipMap(ctx, projection);
  ctx.strokeStyle = 'rgba(167, 188, 183, 0.07)';
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

  drawMapLabel(
    ctx,
    projection.left + projection.width / 2,
    projection.top - 15,
    zone.name,
    'rgba(230, 220, 192, 0.72)',
  );

  ctx.save();
  ctx.strokeStyle = 'rgba(212, 176, 96, 0.42)';
  ctx.lineWidth = 1;
  const tick = Math.min(12, projection.width * 0.06);
  const right = projection.left + projection.width;
  const bottom = projection.top + projection.height;
  for (const [x, y, dx, dy] of [
    [projection.left, projection.top, tick, tick],
    [right, projection.top, -tick, tick],
    [projection.left, bottom, tick, -tick],
    [right, bottom, -tick, -tick],
  ] as const) {
    ctx.beginPath();
    ctx.moveTo(x, y + dy);
    ctx.lineTo(x, y);
    ctx.lineTo(x + dx, y);
    ctx.stroke();
  }
  ctx.restore();
}

export function drawPaths(ctx: CanvasRenderingContext2D, paths: PathDefinition[], projection: Projection) {
  ctx.save();
  clipMap(ctx, projection);
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  // Complete each layer across the network so junctions have no internal seams.
  for (const pass of [0, 1, 2]) for (const path of paths) {
    if (path.points.length < 2) continue;
    const width = Math.max(1.5 / projection.screenScale, path.width * projection.scale);
    const paved = path.style === 'cobblestone_avenue' || path.style === 'brick_walkway';
    ctx.strokeStyle = pass === 0 ? '#30352b' : pass === 1 ? (paved ? '#7a8176' : '#84734e') : (paved ? '#95988a' : '#a48c60');
    ctx.lineWidth = pass === 0 ? width + 2 / projection.screenScale : pass === 1 ? width : width * 0.5;
    strokePath(ctx, path, projection);
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
  if (layers.landmarks) drawMapFeatures(ctx, zone, projection, ['wall', 'building', 'landmark']);
  if (layers.terrain) drawMapFeatures(ctx, zone, projection, ['detail']);
  ctx.restore();
}

function drawObjectives(ctx: CanvasRenderingContext2D, zone: ZoneDefinition, projection: Projection) {
  ctx.save();
  clipMap(ctx, projection);
  for (const objective of zone.rvrObjectives ?? []) {
    const p = projection.toCanvas(objective);
    const radius = objective.captureRadius * projection.scale;
    const color = objective.defaultRealm === 'aegis' ? '#72a6d8' : '#d06161';
    ctx.fillStyle = colorWithAlpha(color, 0.13);
    ctx.strokeStyle = colorWithAlpha(color, 0.72);
    ctx.lineWidth = 1 / projection.screenScale;
    ctx.beginPath();
    ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
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
  ctx.arc(p.x, p.y, 8 / projection.screenScale, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}


function drawPlayerMarker(
  ctx: CanvasRenderingContext2D,
  playerPosition: { x: number; z: number },
  projection: Projection,
) {
  const p = projection.toCanvas(playerPosition);
  ctx.save();
  ctx.translate(p.x, p.y);
  ctx.scale(1 / projection.screenScale, 1 / projection.screenScale);
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
  drawMapLabel(ctx, 0, -16, 'You', '#ffe08a');
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
  ctx.strokeStyle = 'rgba(0, 0, 0, 0.88)';
  ctx.lineWidth = 1.8;

  if (marker.focused || marker.kind === 'quests') {
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

function drawMapLabel(ctx: CanvasRenderingContext2D, x: number, y: number, text: string, color: string) {
  const clean = compactLabel(text);
  if (!clean) return;
  ctx.save();
  ctx.font = '10px "Cinzel", serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  const width = Math.min(220, ctx.measureText(clean).width + 14);
  ctx.shadowColor = 'rgba(0, 0, 0, 0.72)';
  ctx.shadowBlur = 7;
  ctx.fillStyle = 'rgba(5, 11, 13, 0.9)';
  drawRoundedRect(ctx, x - width / 2, y - 9, width, 18, 3);
  ctx.fill();
  ctx.shadowBlur = 0;
  ctx.strokeStyle = 'rgba(173, 139, 77, 0.64)';
  ctx.stroke();
  ctx.strokeStyle = 'rgba(224, 201, 135, 0.16)';
  ctx.strokeRect(x - width / 2 + 2, y - 7, width - 4, 14);
  ctx.fillStyle = color;
  ctx.fillText(clean, x, y + 0.5, width - 8);
  ctx.restore();
}

function drawMapRelief(
  ctx: CanvasRenderingContext2D,
  projection: Projection,
  zone: ZoneDefinition,
) {
  ctx.save();
  clipMap(ctx, projection);

  const light = ctx.createRadialGradient(
    projection.left + projection.width * 0.42,
    projection.top + projection.height * 0.34,
    projection.width * 0.08,
    projection.left + projection.width * 0.5,
    projection.top + projection.height * 0.48,
    projection.width * 0.78,
  );
  light.addColorStop(0, 'rgba(215, 177, 95, 0.08)');
  light.addColorStop(0.48, 'rgba(47, 80, 87, 0.02)');
  light.addColorStop(1, 'rgba(0, 2, 3, 0.72)');
  ctx.fillStyle = light;
  ctx.fillRect(projection.left, projection.top, projection.width, projection.height);

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
  return !['building', 'landmark'].includes(mapFeatureRole(prop));
}

function shouldLabelProp(prop: PropSpawn): boolean {
  return ['building', 'landmark'].includes(mapFeatureRole(prop));
}

function propLabel(prop: PropSpawn, zoneId: string): string {
  if (prop.label) return prop.label;
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

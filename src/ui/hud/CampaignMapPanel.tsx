import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, MouseEvent, PointerEvent, WheelEvent } from 'react';
import type { Game } from '../../game/Game';
import { services } from '../../services';
import {
  buildCampaignSnapshot,
  campaignZoneName,
  formatCampaignControl,
  type CampaignControl,
  type CampaignLane,
  type CampaignSnapshot,
  type CampaignZoneStatus,
} from '../../data/campaign';
import { loadZone, type ZoneDefinition } from '../../world/ZoneLoader';
import type { NpcState } from '../../world/NpcSpawner';
import { useGameStore, type EnemyState } from '../../state/gameStore';
import {
  CAMPAIGN_ROUTE_ORDER,
  campaignRouteForLane,
  campaignRouteForZone,
  campaignMapNodeTarget,
  type CampaignMapLevel,
} from './campaignMapModel';
import {
  calculateEffectiveMapScale,
  calculateMapFitScale,
  calculateMapViewportLayout,
  calculateZoomAnchor,
  calculateZoomedScroll,
  shouldStartMapPan,
  type MapSceneSize,
} from './campaignMapViewport';
import {
  DEFAULT_VISIBLE,
  MAP_MARKER_LEGEND,
  type MarkerToggle,
} from './mapData';
import {
  type WorldMapLayer,
  ZoneMapCanvas,
} from './WorldMapPanel';
import { useDraggableWindow } from './useDraggableWindow';
import { resolveQuestDestination } from './questNavigation';

interface Props {
  game: Game | null;
}

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

const ZONE_CACHE = new Map<string, Promise<ZoneDefinition>>();
const FULL_CENTRAL_ROWS = [1, 3, 7, 9, 11, 13, 17, 19];
const ZOOM_MIN = 0.72;
const ZOOM_MAX = 2.15;

const CAMPAIGN_MAP_EDGES = [
  'edge-central',
  'edge-rift-west-lane',
  'edge-rift-east-lane',
  'edge-aegis-west-lane',
  'edge-aegis-east-lane',
  'edge-rift-west-to-center',
  'edge-rift-east-to-center',
  'edge-aegis-west-to-center',
  'edge-aegis-east-to-center',
];

const CAMPAIGN_MAP_ARROWS = [
  'arrow-rift-city-fortress up',
  'arrow-rift-fortress-inner up',
  'arrow-rift-inner-front up',
  'arrow-front-clash dual',
  'arrow-aegis-front-inner down',
  'arrow-aegis-inner-fortress down',
  'arrow-aegis-fortress-city down',
  'arrow-rift-west-one down',
  'arrow-rift-west-two down',
  'arrow-rift-east-one down',
  'arrow-rift-east-two down',
  'arrow-aegis-west-one up',
  'arrow-aegis-west-two up',
  'arrow-aegis-east-one up',
  'arrow-aegis-east-two up',
];

const CAMPAIGN_CAPITAL_LINKS = [
  'link-rift-capital-west to-left',
  'link-rift-capital-east to-right',
  'link-aegis-capital-west to-left',
  'link-aegis-capital-east to-right',
];

export function CampaignMapPanel({ game }: Props) {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLElement>({ draggedPosition: 'fixed' });
  const worldMapOpen = useGameStore((state) => state.worldMapOpen);
  const worldMapLevel = useGameStore((state) => state.worldMapLevel);
  const selectedZoneId = useGameStore((state) => state.worldMapZoneId);
  const selectedRouteLane = useGameStore((state) => state.worldMapRouteLane);
  const character = useGameStore((state) => state.character);
  const enemies = useGameStore((state) => state.enemies);
  const npcs = useGameStore((state) => state.npcs);
  const quests = useGameStore((state) => state.quests);
  const questDestination = resolveQuestDestination(character, quests);
  const setWorldMapOpen = useGameStore((state) => state.setWorldMapOpen);
  const setWorldMapLevel = useGameStore((state) => state.setWorldMapLevel);
  const setWorldMapZoneId = useGameStore((state) => state.setWorldMapZoneId);
  const zoomWorldMapOut = useGameStore((state) => state.zoomWorldMapOut);
  const currentZoneId = character?.zoneId ?? null;
  const [snapshot, setSnapshot] = useState<CampaignSnapshot>(() => buildCampaignSnapshot(currentZoneId));
  const [zone, setZone] = useState<ZoneDefinition | null>(null);
  const [layers, setLayers] = useState<Record<WorldMapLayer, boolean>>(DEFAULT_WORLD_MAP_LAYERS);
  const [mapZoom, setMapZoom] = useState(1);
  const [mapFitScale, setMapFitScale] = useState(1);
  const [mapViewportSize, setMapViewportSize] = useState<MapSceneSize>({ width: 0, height: 0 });
  const [mapSceneSize, setMapSceneSize] = useState<MapSceneSize | null>(null);
  const [isPanning, setIsPanning] = useState(false);
  const viewportRef = useRef<HTMLDivElement>(null);
  const zoomSurfaceRef = useRef<HTMLDivElement>(null);
  const zoomSceneRef = useRef<HTMLDivElement>(null);
  const mapZoomRef = useRef(1);
  const mapFitScaleRef = useRef(1);
  const zoomAnchorRef = useRef<{
    contentX: number;
    contentY: number;
    pointerX: number;
    pointerY: number;
  } | null>(null);
  const panRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    startScrollLeft: number;
    startScrollTop: number;
    moved: boolean;
  } | null>(null);
  const panMovedRef = useRef(false);

  useEffect(() => {
    try {
      return services.campaign.subscribeSnapshot(setSnapshot, currentZoneId);
    } catch (err) {
      console.warn('[CampaignMapPanel] campaign service unavailable:', err);
      setSnapshot(buildCampaignSnapshot(currentZoneId));
      return undefined;
    }
  }, [currentZoneId]);

  useEffect(() => {
    if (worldMapLevel !== 'zone') return undefined;
    let cancelled = false;
    const runtimeZone = game?.zoneDefinition?.id === selectedZoneId
      ? game.zoneDefinition
      : null;
    if (runtimeZone) {
      setZone(runtimeZone);
      return undefined;
    }

    let pending = ZONE_CACHE.get(selectedZoneId);
    if (!pending) {
      pending = loadZone(selectedZoneId);
      ZONE_CACHE.set(selectedZoneId, pending);
    }
    void pending.then((loaded) => {
      if (!cancelled) setZone(loaded);
    });
    return () => {
      cancelled = true;
    };
  }, [game, selectedZoneId, worldMapLevel]);

  useLayoutEffect(() => {
    mapZoomRef.current = 1;
    mapFitScaleRef.current = 1;
    zoomAnchorRef.current = null;
    setMapZoom(1);
    setMapFitScale(1);
    const viewport = viewportRef.current;
    if (!viewport || !worldMapOpen) return undefined;

    const measureScene = () => {
      const scene = zoomSceneRef.current;
      const content = scene?.firstElementChild as HTMLElement | null;
      if (!scene || !content) return;

      const viewportSize = { width: viewport.clientWidth, height: viewport.clientHeight };
      const nextSceneSize = worldMapLevel === 'zone'
        ? viewportSize
        : { width: content.offsetWidth, height: content.offsetHeight };
      if (nextSceneSize.width <= 0 || nextSceneSize.height <= 0 || viewportSize.width <= 0 || viewportSize.height <= 0) return;

      const nextFitScale = worldMapLevel === 'zone'
        ? 1
        : calculateMapFitScale(viewportSize, nextSceneSize);
      mapFitScaleRef.current = nextFitScale;
      setMapViewportSize((current) => current.width === viewportSize.width && current.height === viewportSize.height ? current : viewportSize);
      setMapSceneSize((current) => current?.width === nextSceneSize.width && current.height === nextSceneSize.height ? current : nextSceneSize);
      setMapFitScale((current) => Math.abs(current - nextFitScale) < 0.001 ? current : nextFitScale);
    };

    const resetViewportPosition = () => {
      viewport.scrollLeft = 0;
      viewport.scrollTop = 0;
    };
    measureScene();
    resetViewportPosition();
    const frame = requestAnimationFrame(() => {
      measureScene();
      resetViewportPosition();
    });
    const resizeObserver = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(() => {
      mapZoomRef.current = 1;
      zoomAnchorRef.current = null;
      setMapZoom(1);
      measureScene();
      requestAnimationFrame(resetViewportPosition);
    });
    resizeObserver?.observe(viewport);
    if (zoomSceneRef.current?.firstElementChild) {
      resizeObserver?.observe(zoomSceneRef.current.firstElementChild);
    }
    return () => {
      cancelAnimationFrame(frame);
      resizeObserver?.disconnect();
    };
  }, [worldMapOpen, selectedRouteLane, selectedZoneId, worldMapLevel, zone]);

  useLayoutEffect(() => {
    const anchor = zoomAnchorRef.current;
    const viewport = viewportRef.current;
    if (!anchor || !viewport) return undefined;
    zoomAnchorRef.current = null;
    const frame = requestAnimationFrame(() => {
      const scale = calculateEffectiveMapScale(mapFitScaleRef.current, mapZoomRef.current);
      const nextScroll = calculateZoomedScroll(anchor, scale);
      viewport.scrollLeft = nextScroll.left;
      viewport.scrollTop = nextScroll.top;
    });
    return () => cancelAnimationFrame(frame);
  }, [mapZoom]);

  const selectedZone = snapshot.zones.find((entry) => entry.id === selectedZoneId) ?? null;
  const selectedRoute = campaignRouteForLane(selectedRouteLane);
  const selectedIsCurrent = selectedZoneId === currentZoneId;
  const liveZoneRuntime = selectedIsCurrent && game?.zoneDefinition?.id === selectedZoneId;
  const zoneEnemies = zone ? zoneEnemyFallbacks(zone) : [];
  const zoneNpcs = zone ? zoneNpcFallbacks(zone) : [];
  const previewEnemies = liveZoneRuntime ? enemies : zoneEnemies;
  const previewNpcs = liveZoneRuntime ? npcs : zoneNpcs;
  const markerVisible = useMemo<Record<MarkerToggle, boolean>>(() => ({
    quests: layers.quests,
    npcs: layers.npcs,
    crafting: layers.crafting,
    resources: layers.resources,
    enemies: layers.enemies,
    exits: layers.exits,
  }), [layers]);
  const zoneStats = useMemo(() => zone ? getZoneStats(zone, previewEnemies) : null, [previewEnemies, zone]);
  const landmarks = useMemo(() => zone ? getLandmarks(zone) : [], [zone]);
  const effectiveMapScale = calculateEffectiveMapScale(mapFitScale, mapZoom);
  const mapViewportLayout = mapSceneSize && mapViewportSize.width > 0 && mapViewportSize.height > 0
    ? calculateMapViewportLayout(mapViewportSize, mapSceneSize, effectiveMapScale)
    : null;

  if (!worldMapOpen) return null;

  function close() {
    setWorldMapOpen(false);
  }

  function handleWheel(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    const viewport = viewportRef.current;
    if (!viewport) return;

    const rect = viewport.getBoundingClientRect();
    const pointerX = event.clientX - rect.left;
    const pointerY = event.clientY - rect.top;
    const currentZoom = mapZoomRef.current;
    const currentScale = calculateEffectiveMapScale(mapFitScaleRef.current, currentZoom);
    const nextZoom = Math.max(
      ZOOM_MIN,
      Math.min(ZOOM_MAX, currentZoom * Math.pow(1.0015, -event.deltaY)),
    );
    if (nextZoom === currentZoom) return;

    zoomAnchorRef.current = calculateZoomAnchor(
      { left: viewport.scrollLeft, top: viewport.scrollTop },
      { x: pointerX, y: pointerY },
      currentScale,
    );
    mapZoomRef.current = nextZoom;
    setMapZoom(nextZoom);
  }

  function handleMapPointerDown(event: PointerEvent<HTMLDivElement>) {
    const targetIsInteractive = event.target instanceof HTMLElement && Boolean(event.target.closest('button'));
    if (!shouldStartMapPan(event.button, targetIsInteractive)) return;
    const viewport = viewportRef.current;
    if (!viewport) return;
    panRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      startScrollLeft: viewport.scrollLeft,
      startScrollTop: viewport.scrollTop,
      moved: false,
    };
    panMovedRef.current = false;
    viewport.setPointerCapture(event.pointerId);
    setIsPanning(true);
  }

  function handleMapPointerMove(event: PointerEvent<HTMLDivElement>) {
    const pan = panRef.current;
    const viewport = viewportRef.current;
    if (!pan || pan.pointerId !== event.pointerId || !viewport) return;

    const dx = event.clientX - pan.startX;
    const dy = event.clientY - pan.startY;
    if (!pan.moved && Math.hypot(dx, dy) < 5) return;
    pan.moved = true;
    panMovedRef.current = true;
    event.preventDefault();
    viewport.scrollLeft = pan.startScrollLeft - dx;
    viewport.scrollTop = pan.startScrollTop - dy;
  }

  function handleMapPointerUp(event: PointerEvent<HTMLDivElement>) {
    const pan = panRef.current;
    if (!pan || pan.pointerId !== event.pointerId) return;
    panRef.current = null;
    setIsPanning(false);
    if (viewportRef.current?.hasPointerCapture(event.pointerId)) {
      viewportRef.current.releasePointerCapture(event.pointerId);
    }
    if (pan.moved) {
      window.setTimeout(() => {
        panMovedRef.current = false;
      }, 0);
    }
  }

  function handleMapPointerCancel(event: PointerEvent<HTMLDivElement>) {
    handleMapPointerUp(event);
    panMovedRef.current = false;
  }

  function handleMapClickCapture(event: MouseEvent<HTMLDivElement>) {
    if (!panMovedRef.current) return;
    event.preventDefault();
    event.stopPropagation();
    panMovedRef.current = false;
  }

  function handleMapContextMenu(event: MouseEvent<HTMLDivElement>) {
    event.preventDefault();
    if (worldMapLevel !== 'campaign') zoomWorldMapOut();
  }

  function selectCampaignZone(zoneId: string) {
    const target = campaignMapNodeTarget(worldMapLevel, zoneId);
    setWorldMapZoneId(target.zoneId);
    setWorldMapLevel(target.level);
  }

  function selectRoute(lane: CampaignLane) {
    const route = campaignRouteForLane(lane);
    setWorldMapZoneId(route.mainZoneIds[0] ?? selectedZoneId);
    setWorldMapLevel('route');
  }

  const activeZone = snapshot.activeZone ?? selectedZone;
  const title = worldMapLevel === 'zone'
    ? selectedZone?.name ?? zone?.name ?? 'Zone Map'
    : worldMapLevel === 'route'
      ? selectedRoute.label
      : 'Aegis Accord vs Riftbound Host';

  return (
    <div
      className="world-map-backdrop"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) close();
      }}
      onContextMenu={(event) => event.preventDefault()}
    >
      <section
        ref={panelRef}
        className={`world-map-panel campaign-map-panel panel${dragClassName}`}
        style={dragStyle}
        aria-labelledby="world-map-title"
      >
        <header className="world-map-header draggable-window-handle" {...dragHandleProps}>
          <div>
            <h2 id="world-map-title">Campaign Atlas</h2>
            <span>{title}</span>
          </div>
          <button type="button" onClick={close}>Close</button>
        </header>

        <nav className="campaign-map-breadcrumbs" aria-label="Map tier">
          <TierButton label="Zone" active={worldMapLevel === 'zone'} onClick={() => setWorldMapLevel('zone')} />
          <span aria-hidden="true">›</span>
          <TierButton label="Route" active={worldMapLevel === 'route'} onClick={() => setWorldMapLevel('route')} />
          <span aria-hidden="true">›</span>
          <TierButton label="Campaign" active={worldMapLevel === 'campaign'} onClick={() => setWorldMapLevel('campaign')} />
        </nav>

        <div className="warfront-score">
          <RealmScore label="Aegis" value={snapshot.aegis.controlledZones} realm="aegis" />
          <RealmScore label="Contested" value={snapshot.contestedZones} realm="contested" />
          <RealmScore label="Riftbound" value={snapshot.riftbound.controlledZones} realm="riftbound" />
        </div>

        <div className="world-map-body campaign-map-body">
          <div
            ref={viewportRef}
            className={`world-map-canvas-frame campaign-map-viewport campaign-map-viewport-${worldMapLevel}${isPanning ? ' is-panning' : ''}`}
            onWheel={handleWheel}
            onPointerDown={handleMapPointerDown}
            onPointerMove={handleMapPointerMove}
            onPointerUp={handleMapPointerUp}
            onPointerCancel={handleMapPointerCancel}
            onClickCapture={handleMapClickCapture}
            onContextMenu={handleMapContextMenu}
          >
            <div
              ref={zoomSurfaceRef}
              className="campaign-map-zoom-surface"
              style={{
                width: mapViewportLayout?.width ?? '100%',
                height: mapViewportLayout?.height ?? '100%',
              }}
            >
              <div
                ref={zoomSceneRef}
                className="campaign-map-zoom-scene"
                style={{
                  width: mapSceneSize?.width ?? '100%',
                  height: mapSceneSize?.height ?? '100%',
                  left: mapViewportLayout?.offsetX ?? 0,
                  top: mapViewportLayout?.offsetY ?? 0,
                  transform: `scale(${effectiveMapScale})`,
                }}
              >
                {worldMapLevel === 'zone' ? (
                  <ZoneMapCanvas
                    game={selectedIsCurrent ? game : null}
                    zone={zone}
                    character={selectedIsCurrent ? character : character && zone ? {
                      ...character, zoneId: zone.id, position: zone.spawnPoint ?? character.position,
                    } : null}
                    enemies={previewEnemies}
                    npcs={previewNpcs}
                    quests={quests}
                    layers={layers}
                    markerVisible={markerVisible}
                    renderScale={effectiveMapScale}
                    showPlayer={selectedIsCurrent}
                  />
                ) : worldMapLevel === 'route' ? (
                  <CampaignRouteBoard
                    snapshot={snapshot}
                    lane={selectedRouteLane}
                    selectedZoneId={selectedZoneId}
                    questZoneId={questDestination?.zoneId}
                    onSelectZone={selectCampaignZone}
                  />
                ) : (
                  <CampaignFullMap
                    snapshot={snapshot}
                    selectedZoneId={selectedZoneId}
                    questZoneId={questDestination?.zoneId}
                    onSelectZone={selectCampaignZone}
                    onSelectRoute={selectRoute}
                  />
                )}
              </div>
            </div>
          </div>

          <aside className="world-map-sidebar campaign-map-sidebar" aria-label="Campaign map details">
            {questDestination && (
              <section className="world-map-sidebar-section expedition-map-focus">
                <h3>Your expedition</h3>
                <strong>{questDestination.quest.title}</strong>
                <p>{questDestination.action}</p>
                <button type="button" onClick={() => {
                  setWorldMapZoneId(questDestination.zoneId);
                  setWorldMapLevel('zone');
                }}>
                  Show {campaignZoneName(questDestination.zoneId)}
                </button>
              </section>
            )}
            {worldMapLevel === 'zone' && (
              <section className="world-map-sidebar-section">
                <h3>Layers</h3>
                <div className="world-map-layer-list">
                  {WORLD_MAP_LAYERS.map((item) => (
                    <label className={`world-map-layer${layers[item.key] ? ' active' : ''}`} key={item.key}>
                      <input
                        type="checkbox"
                        checked={layers[item.key]}
                        onChange={() => setLayers((current) => ({ ...current, [item.key]: !current[item.key] }))}
                      />
                      <span className="world-map-swatch" style={{ '--marker-color': item.color } as CSSProperties} />
                      {item.label}
                    </label>
                  ))}
                </div>
              </section>
            )}

          <CampaignSelectionCard
            level={worldMapLevel}
            zone={selectedZone}
            route={selectedRoute}
            activeZone={activeZone}
            stats={zoneStats}
            landmarks={landmarks}
            aegis={snapshot.aegis}
            riftbound={snapshot.riftbound}
          />
          </aside>
        </div>

        <footer className="campaign-map-instructions">
          <span>Wheel: zoom</span>
          <span>Left click: inspect deeper</span>
          <span>Right click: zoom out</span>
          <span>{activeZone ? `Current focus: ${activeZone.name}` : 'Select a zone to inspect its campaign status'}</span>
        </footer>
      </section>
    </div>
  );
}

function TierButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button type="button" className={`campaign-map-tier${active ? ' active' : ''}`} onClick={onClick} aria-current={active}>
      {label}
    </button>
  );
}

function RealmScore({ label, value, realm }: { label: string; value: number; realm: CampaignControl }) {
  return (
    <div className={`warfront-score-card ${realm}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function CampaignSelectionCard({
  level,
  zone,
  route,
  activeZone,
  stats,
  landmarks,
  aegis,
  riftbound,
}: {
  level: CampaignMapLevel;
  zone: CampaignZoneStatus | null;
  route: ReturnType<typeof campaignRouteForLane>;
  activeZone: CampaignZoneStatus | null;
  stats: ZoneStats | null;
  landmarks: Array<{ id: string; kind: string; label: string }>;
  aegis: CampaignSnapshot['aegis'];
  riftbound: CampaignSnapshot['riftbound'];
}) {
  return (
    <>
      <section className="world-map-sidebar-section campaign-selection-card">
        <h3>{level === 'campaign' ? 'Campaign' : level === 'route' ? 'Route' : 'Selected Zone'}</h3>
        {level === 'zone' && zone ? (
          <>
            <strong>{zone.name}</strong>
            <small>{zone.tier} · {zone.levelBand} · {zone.lane}</small>
            <div className={`campaign-control-chip ${zone.control}`}>{formatCampaignControl(zone.control)}</div>
            <small>{zone.objectives.map((objective) => `${objective.label}: ${formatCampaignControl(objective.control)}`).join(' / ')}</small>
            {stats && (
              <dl className="world-map-stats">
                <div><dt>Size</dt><dd>{stats.size}</dd></div>
                <div><dt>Roads</dt><dd>{stats.roads}</dd></div>
                <div><dt>Landmarks</dt><dd>{stats.landmarks}</dd></div>
                <div><dt>Hostiles</dt><dd>{stats.enemies}</dd></div>
                <div><dt>Exits</dt><dd>{stats.exits}</dd></div>
              </dl>
            )}
          </>
        ) : level === 'route' ? (
          <>
            <strong>{route.label}</strong>
            <small>{route.mainZoneIds.length} connected zones · {Object.values(route.branches).flat().length} optional lairs</small>
            <small>Click a route node to open its zone detail map.</small>
          </>
        ) : (
          <>
            <strong>Aegis Accord vs Riftbound Host</strong>
            <small>{zone?.name ? `Selected: ${zone.name}` : 'Select a zone to focus a route.'}</small>
            <small>{aegis.citySiegeReady || riftbound.citySiegeReady ? 'A city siege is ready on at least one front.' : 'City sieges remain locked by the current front state.'}</small>
          </>
        )}
      </section>

      <section className="world-map-sidebar-section campaign-warfront-card">
        <h3>Warfront Pressure</h3>
        <WarfrontSummary summary={aegis} />
        <WarfrontSummary summary={riftbound} />
      </section>

      {activeZone && (
        <section className="world-map-sidebar-section campaign-active-card">
          <h3>Active Campaign Focus</h3>
          <strong>{activeZone.name}</strong>
          <small>{activeZone.tier} · {formatCampaignControl(activeZone.control)}</small>
          <small>{activeZone.objectives.map((objective) => objective.label).join(' / ')}</small>
          <small>Influence: Aegis {activeZone.influence.aegis}/{activeZone.influence.keepSiegeRequired} · Riftbound {activeZone.influence.riftbound}/{activeZone.influence.keepSiegeRequired}</small>
        </section>
      )}

      {level === 'zone' && landmarks.length > 0 && (
        <section className="world-map-sidebar-section">
          <h3>Landmarks</h3>
          <ul className="world-map-landmark-list">
            {landmarks.slice(0, 8).map((landmark) => (
              <li key={landmark.id}><span>{landmark.kind}</span><strong>{landmark.label}</strong></li>
            ))}
          </ul>
        </section>
      )}
    </>
  );
}

function WarfrontSummary({ summary }: { summary: CampaignSnapshot['aegis'] }) {
  return (
    <div className={`campaign-warfront-summary ${summary.realm}`}>
      <strong>{summary.label}</strong>
      <span>Fortress: {summary.targetFortressName}</span>
      <span className={summary.fortressPressureReady ? 'ready' : ''}>
        Pressure: {summary.fortressPressureReady ? 'Ready' : 'Building'}
      </span>
      <span>City: {summary.targetCityName}</span>
      <span className={summary.citySiegeReady ? 'ready' : ''}>
        Siege: {summary.citySiegeReady ? 'Ready' : 'Locked'}
      </span>
    </div>
  );
}

function CampaignFullMap({
  snapshot,
  selectedZoneId,
  questZoneId,
  onSelectZone,
  onSelectRoute,
}: {
  snapshot: CampaignSnapshot;
  selectedZoneId: string;
  questZoneId?: string;
  onSelectZone: (zoneId: string) => void;
  onSelectRoute: (lane: CampaignLane) => void;
}) {
  return (
    <div className="campaign-map-board campaign-map-board-full">
      <svg className="campaign-map-relief-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <radialGradient id="campaign-relief-light" cx="50%" cy="48%" r="70%">
            <stop offset="0%" stopColor="#4a3921" stopOpacity="0.24" />
            <stop offset="62%" stopColor="#111b20" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#020508" stopOpacity="0.84" />
          </radialGradient>
          <linearGradient id="campaign-relief-realm" x1="0%" x2="100%">
            <stop offset="0%" stopColor="#365d7d" stopOpacity="0.18" />
            <stop offset="50%" stopColor="#d4b060" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#7d3038" stopOpacity="0.2" />
          </linearGradient>
        </defs>
        <rect width="100" height="100" fill="url(#campaign-relief-realm)" />
        <path className="campaign-relief-contour" d="M-4 16 C 16 4, 30 26, 50 15 S 83 5, 104 20" />
        <path className="campaign-relief-contour" d="M-8 28 C 15 16, 29 38, 49 27 S 86 15, 108 31" />
        <path className="campaign-relief-contour" d="M-10 70 C 12 57, 32 80, 52 68 S 86 57, 110 75" />
        <path className="campaign-relief-contour" d="M-6 84 C 16 72, 30 94, 52 82 S 87 72, 106 88" />
        <path className="campaign-relief-vein" d="M50 5 C 47 23, 55 30, 50 47 S 54 76, 50 96" />
        <path className="campaign-relief-vein" d="M21 5 C 27 19, 24 32, 32 44 S 27 69, 21 94" />
        <path className="campaign-relief-vein" d="M79 5 C 72 20, 77 34, 68 47 S 74 72, 80 95" />
        <rect width="100" height="100" fill="url(#campaign-relief-light)" />
      </svg>
      {CAMPAIGN_MAP_EDGES.map((edge) => <span className={`campaign-map-edge ${edge}`} key={edge} aria-hidden="true" />)}
      {CAMPAIGN_MAP_ARROWS.map((arrow) => <span className={`campaign-map-arrow ${arrow}`} key={arrow} aria-hidden="true" />)}
      {CAMPAIGN_CAPITAL_LINKS.map((link) => <span className={`campaign-map-capital-link ${link}`} key={link} aria-hidden="true" />)}
      {snapshot.zones.map((zone) => (
        <CampaignMapNodeView
          key={zone.id}
          zone={zone}
          selected={zone.id === selectedZoneId}
          questDestination={zone.id === questZoneId}
          style={fullMapNodeStyle(zone)}
          onClick={() => onSelectZone(zone.id)}
          onContextMenu={(event) => event.preventDefault()}
        />
      ))}
      <div className="campaign-map-route-labels" aria-label="Campaign routes">
        {CAMPAIGN_ROUTE_ORDER.filter((lane) => lane !== 'central').map((lane) => (
          <button type="button" key={lane} onClick={() => onSelectRoute(lane)}>{campaignRouteForLane(lane).label}</button>
        ))}
      </div>
    </div>
  );
}

function CampaignRouteBoard({
  snapshot,
  lane,
  selectedZoneId,
  questZoneId,
  onSelectZone,
}: {
  snapshot: CampaignSnapshot;
  lane: CampaignLane;
  selectedZoneId: string;
  questZoneId?: string;
  onSelectZone: (zoneId: string) => void;
}) {
  const route = campaignRouteForLane(lane);
  return (
    <div className="campaign-route-board">
      <svg className="campaign-route-relief-layer" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <radialGradient id="route-relief-light" cx="50%" cy="30%" r="75%">
            <stop offset="0%" stopColor="#554024" stopOpacity="0.23" />
            <stop offset="58%" stopColor="#132127" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#030608" stopOpacity="0.86" />
          </radialGradient>
        </defs>
        <rect width="100" height="100" fill="#081015" />
        <path className="campaign-relief-contour" d="M-8 18 C 20 2, 36 28, 50 16 S 80 1, 108 19" />
        <path className="campaign-relief-contour" d="M-8 82 C 20 66, 35 93, 52 79 S 81 65, 108 84" />
        <path className="campaign-relief-vein" d="M50 8 C 45 27, 57 35, 49 52 S 55 77, 50 96" />
        <path className="campaign-relief-route-line" d="M50 9 C 50 24, 50 38, 50 91" />
        <path className="campaign-relief-route-line" d="M18 35 C 31 40, 37 45, 50 50" />
        <path className="campaign-relief-route-line" d="M82 35 C 69 40, 63 45, 50 50" />
        <rect width="100" height="100" fill="url(#route-relief-light)" />
      </svg>
      <div className="campaign-route-heading">
        <span>{route.realm ? `${route.realm === 'aegis' ? 'Aegis Accord' : 'Riftbound Host'} lane` : 'Realm-spanning lane'}</span>
        <strong>{route.label}</strong>
      </div>
      <div className="campaign-route-chain">
        {route.mainZoneIds.map((zoneId, index) => {
          const zone = snapshot.zones.find((entry) => entry.id === zoneId);
          if (!zone) return null;
          return (
            <div className="campaign-route-step" key={zoneId}>
              <CampaignMapNodeView
                zone={zone}
                selected={zone.id === selectedZoneId}
                questDestination={zone.id === questZoneId}
                onClick={() => onSelectZone(zone.id)}
                onContextMenu={(event) => event.preventDefault()}
              />
              {(route.branches[zoneId] ?? []).length > 0 && (
                <div className="campaign-route-branches">
                  {(route.branches[zoneId] ?? []).map((branchId) => {
                    const branch = snapshot.zones.find((entry) => entry.id === branchId);
                    return branch ? (
                      <CampaignMapNodeView
                        key={branch.id}
                        zone={branch}
                        selected={branch.id === selectedZoneId}
                        questDestination={branch.id === questZoneId}
                        onClick={() => onSelectZone(branch.id)}
                        onContextMenu={(event) => event.preventDefault()}
                      />
                    ) : null;
                  })}
                </div>
              )}
              {index < route.mainZoneIds.length - 1 && <span className="campaign-route-arrow" aria-hidden="true">↓</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function CampaignMapNodeView({
  zone,
  selected,
  questDestination,
  style,
  onClick,
  onContextMenu,
}: {
  zone: CampaignZoneStatus;
  selected: boolean;
  questDestination?: boolean;
  style?: CSSProperties;
  onClick: () => void;
  onContextMenu: (event: MouseEvent<HTMLButtonElement>) => void;
}) {
  const isBoss = zone.nodeRole === 'boss_lair';
  const variant = zone.nodeRole === 'capital'
    ? 'city'
    : zone.nodeRole === 'fortress'
      ? 'fortress'
      : zone.tier === 'T4'
        ? zone.levelBand.includes('front') ? 'front' : 'inner'
        : '';
  const displayControl = isBoss ? shortCampaignControl(zone.control) : formatCampaignControl(zone.control);
  return (
    <button
      type="button"
      className={`campaign-map-node ${isBoss ? 'boss' : 'zone'} ${variant} ${zone.control}${zone.current ? ' current' : ''}${selected ? ' selected' : ''}${questDestination ? ' expedition-zone' : ''}`}
      style={style}
      title={`${zone.name} — ${formatCampaignControl(zone.control)}`}
      aria-label={`${zone.name}, ${zone.tier}, ${formatCampaignControl(zone.control)}${questDestination ? ', expedition destination' : ''}`}
      aria-current={zone.current ? 'location' : undefined}
      onClick={onClick}
      onContextMenu={onContextMenu}
    >
      <strong>{zone.name}</strong>
      <span className="campaign-map-node-stage">{isBoss ? zone.levelBand : zone.tier}</span>
      <em>{questDestination ? '◆ Expedition' : displayControl}</em>
    </button>
  );
}

function fullMapNodeStyle(zone: CampaignZoneStatus): CSSProperties {
  if (zone.lane === 'central') {
    const rowIndex = campaignRouteForLane('central').mainZoneIds.indexOf(zone.id);
    return { gridColumn: 3, gridRow: FULL_CENTRAL_ROWS[rowIndex] ?? 10 };
  }

  const isWest = zone.lane.endsWith('_west');
  const isBoss = zone.nodeRole === 'boss_lair';
  const tier = Number(zone.levelBand.match(/Tier (\d)/)?.[1] ?? 1);
  const baseRow = zone.lane.startsWith('riftbound_') ? 3 : 13;
  return {
    gridColumn: isBoss ? (isWest ? 1 : 5) : (isWest ? 2 : 4),
    gridRow: baseRow + (tier - 1) * 2,
  };
}

interface ZoneStats {
  size: string;
  roads: number;
  landmarks: number;
  enemies: number;
  exits: number;
}

function getZoneStats(zone: ZoneDefinition, enemies: EnemyState[]): ZoneStats {
  return {
    size: `${zone.size}m`,
    roads: zone.paths?.length ?? 0,
    landmarks: (zone.props ?? []).filter((prop) => !isTerrainProp(prop)).length + (zone.rvrObjectives?.length ?? 0),
    enemies: enemies.filter((enemy) => enemy.alive).length || (zone.enemies?.length ?? 0),
    exits: zone.zoneTriggers?.length ?? 0,
  };
}

function getLandmarks(zone: ZoneDefinition): Array<{ id: string; kind: string; label: string }> {
  const objectives = (zone.rvrObjectives ?? []).map((objective) => ({
    id: objective.id,
    kind: objective.type === 'boss' ? 'Lair' : 'Objective',
    label: objective.label,
  }));
  const props = (zone.props ?? [])
    .filter((prop) => !isTerrainProp(prop) && prop.id)
    .slice(0, 6)
    .map((prop) => ({ id: prop.id!, kind: 'Landmark', label: prop.id!.replace(`${zone.id}_`, '').replace(/_/g, ' ') }));
  return [...objectives, ...props];
}

function isTerrainProp(prop: ZoneDefinition['props'][number]): boolean {
  return prop.kind === 'tree' || prop.kind === 'rock' || prop.kind.startsWith('pnw_');
}

function zoneNpcFallbacks(zone: ZoneDefinition): NpcState[] {
  return (zone.npcs ?? []).map((npc) => ({
    id: npc.id,
    name: npc.name,
    title: npc.title,
    role: npc.role,
    position: { x: npc.x, y: npc.y ?? 0, z: npc.z },
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

function shortCampaignControl(control: CampaignControl): string {
  switch (control) {
    case 'aegis': return 'Aegis';
    case 'riftbound': return 'Rift';
    case 'contested': default: return 'Open';
  }
}

export interface MapSceneSize {
  width: number;
  height: number;
}

export interface MapViewportLayout extends MapSceneSize {
  offsetX: number;
  offsetY: number;
  scale: number;
}

export interface MapZoomAnchor {
  contentX: number;
  contentY: number;
  pointerX: number;
  pointerY: number;
}

/** React's delegated wheel listener is passive; this viewport must cancel native scrolling. */
export function bindMapWheel(viewport: HTMLElement, zoom: (event: WheelEvent) => void): () => void {
  const handleWheel = (event: WheelEvent) => {
    event.preventDefault();
    event.stopPropagation();
    zoom(event);
  };
  viewport.addEventListener('wheel', handleWheel, { passive: false });
  return () => viewport.removeEventListener('wheel', handleWheel);
}

export function shouldStartMapPan(button: number, targetIsInteractive: boolean): boolean {
  return button === 0 && !targetIsInteractive;
}

export function calculateMapFitScale(
  viewport: MapSceneSize,
  scene: MapSceneSize,
  padding = 8,
): number {
  if (viewport.width <= 0 || viewport.height <= 0 || scene.width <= 0 || scene.height <= 0) return 1;
  return Math.min(
    1,
    Math.max(1, viewport.width - padding) / scene.width,
    Math.max(1, viewport.height - padding) / scene.height,
  );
}

export function calculateEffectiveMapScale(fitScale: number, userZoom: number): number {
  return Math.max(0.01, fitScale * userZoom);
}

export function calculateMapViewportLayout(
  viewport: MapSceneSize,
  scene: MapSceneSize,
  scale: number,
): MapViewportLayout {
  const scaledWidth = scene.width * scale;
  const scaledHeight = scene.height * scale;
  const width = Math.max(viewport.width, scaledWidth);
  const height = Math.max(viewport.height, scaledHeight);
  return {
    width,
    height,
    offsetX: Math.max(0, (width - scaledWidth) / 2),
    offsetY: Math.max(0, (height - scaledHeight) / 2),
    scale,
  };
}

export function calculateZoomAnchor(
  scroll: { left: number; top: number },
  pointer: { x: number; y: number },
  currentScale: number,
  offset = { offsetX: 0, offsetY: 0 },
): MapZoomAnchor {
  return {
    contentX: (scroll.left + pointer.x - offset.offsetX) / Math.max(0.01, currentScale),
    contentY: (scroll.top + pointer.y - offset.offsetY) / Math.max(0.01, currentScale),
    pointerX: pointer.x,
    pointerY: pointer.y,
  };
}

export function calculateZoomedScroll(
  anchor: MapZoomAnchor,
  nextScale: number,
  offset = { offsetX: 0, offsetY: 0 },
): { left: number; top: number } {
  return {
    left: anchor.contentX * nextScale + offset.offsetX - anchor.pointerX,
    top: anchor.contentY * nextScale + offset.offsetY - anchor.pointerY,
  };
}

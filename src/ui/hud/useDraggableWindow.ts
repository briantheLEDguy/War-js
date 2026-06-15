import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, PointerEvent as ReactPointerEvent } from 'react';

type PositionMode = 'absolute' | 'fixed';

interface DragPosition {
  x: number;
  y: number;
  width: number;
}

interface DragState {
  dx: number;
  dy: number;
  pointerId: number;
}

interface UseDraggableWindowOptions {
  draggedPosition?: PositionMode;
  margin?: number;
}

let nextDragZIndex = 200;

export function useDraggableWindow<T extends HTMLElement>({
  draggedPosition,
  margin = 0,
}: UseDraggableWindowOptions = {}) {
  const panelRef = useRef<T>(null);
  const dragState = useRef<DragState | null>(null);
  const [position, setPosition] = useState<DragPosition | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [zIndex, setZIndex] = useState<number | null>(null);

  const clampPosition = useCallback((x: number, y: number, element: HTMLElement) => {
    const maxX = Math.max(margin, window.innerWidth - element.offsetWidth - margin);
    const maxY = Math.max(margin, window.innerHeight - element.offsetHeight - margin);
    return {
      x: Math.max(margin, Math.min(x, maxX)),
      y: Math.max(margin, Math.min(y, maxY)),
    };
  }, [margin]);

  const startDrag = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    if (event.button !== 0 || shouldIgnoreDrag(event)) return;
    const panel = panelRef.current;
    if (!panel) return;

    const rect = panel.getBoundingClientRect();
    dragState.current = {
      dx: event.clientX - rect.left,
      dy: event.clientY - rect.top,
      pointerId: event.pointerId,
    };
    setIsDragging(true);
    setZIndex(nextDragZIndex++);
    setPosition({
      x: rect.left,
      y: rect.top,
      width: rect.width,
    });
    event.currentTarget.setPointerCapture(event.pointerId);
    event.preventDefault();
  }, []);

  const moveDrag = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    const state = dragState.current;
    const panel = panelRef.current;
    if (!state || !panel || state.pointerId !== event.pointerId) return;

    const next = clampPosition(event.clientX - state.dx, event.clientY - state.dy, panel);
    setPosition((current) => ({
      x: next.x,
      y: next.y,
      width: current?.width ?? panel.getBoundingClientRect().width,
    }));
    event.preventDefault();
  }, [clampPosition]);

  const endDrag = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    const state = dragState.current;
    if (state?.pointerId === event.pointerId && event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    dragState.current = null;
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (!position) return undefined;
    const handleResize = () => {
      const panel = panelRef.current;
      if (!panel) return;
      const next = clampPosition(position.x, position.y, panel);
      setPosition((current) => current ? { ...current, ...next } : current);
    };
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [clampPosition, position]);

  const dragStyle = useMemo<CSSProperties | undefined>(() => {
    if (!position) return zIndex === null ? undefined : { zIndex };
    return {
      left: position.x,
      top: position.y,
      right: 'auto',
      bottom: 'auto',
      transform: 'none',
      width: position.width,
      position: draggedPosition,
      zIndex: zIndex ?? undefined,
    };
  }, [draggedPosition, position, zIndex]);

  return {
    panelRef,
    dragHandleProps: {
      onPointerDown: startDrag,
      onPointerMove: moveDrag,
      onPointerUp: endDrag,
      onPointerCancel: endDrag,
      onLostPointerCapture: endDrag,
    },
    dragStyle,
    dragClassName: isDragging ? ' draggable-window--dragging' : '',
  };
}

function shouldIgnoreDrag(event: ReactPointerEvent<HTMLElement>): boolean {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return false;
  const blocker = target.closest(
    'button, input, select, textarea, a, [role="button"], [data-drag-blocker="true"]',
  );
  return Boolean(blocker && event.currentTarget.contains(blocker));
}

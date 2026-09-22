import type { KeepConfig, Position } from './protocol';

/** A named list supersedes the legacy alias; an explicitly empty list disables it. */
export function keepPosterns(keep: KeepConfig): NonNullable<KeepConfig['postern']>[] {
  return keep.posterns ?? (keep.postern ? [keep.postern] : []);
}

export function nearbyKeepPostern(keep: KeepConfig, position: Position) {
  return keepPosterns(keep).find(postern => posternExitFor(postern, position) !== null);
}

/** Both destinations come from the server map. The action never accepts client coordinates. */
export function posternExitFor(postern: KeepConfig['postern'], position: Position): Position | null {
  if (!postern) return null;
  const distance = (point: Position) => Math.hypot(position.x - point.x, position.y - point.y, position.z - point.z);
  if (distance(postern.outside) <= postern.interactionRadius) return { ...postern.inside };
  if (distance(postern.inside) <= postern.interactionRadius) return { ...postern.outside };
  return null;
}

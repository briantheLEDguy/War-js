import type { Object3D } from 'three';
import { advanceLift, type CityPoint, type CraterCityDefinition } from './CraterCity';
import type { SpawnedProps } from './Props';

interface Lift {
  definition: CraterCityDefinition['lifts'][number];
  object: Object3D;
  target: number;
}

/** Moving cages are excluded from static instancing; their authored collision
 * and support surfaces move with the visual, including while called remotely. */
export class CityLifts {
  private lifts: Lift[] = [];
  private panel: HTMLDivElement;
  private selected: Lift | null = null;
  contains(point: CityPoint): boolean {
    return this.lifts.some(l => Math.abs(point.x-l.definition.x)<5.2 && Math.abs(point.z-l.definition.z)<5.2 && Math.abs(point.y-l.object.position.y)<2);
  }
  constructor(city: CraterCityDefinition, private props: SpawnedProps, container: HTMLElement) {
    this.panel = document.createElement('div'); this.panel.className = 'city-lift-controls';
    this.panel.hidden = true; container.append(this.panel);
    for (const definition of city.lifts) {
      const object = props.objects.find(p => p.id === definition.propId)?.object;
      if (object && !object.userData.assetMissing) this.lifts.push({ definition, object, target: object.position.y });
    }
  }
  update(dt: number, player: CityPoint, disabled: boolean): void {
    for (const lift of this.lifts) {
      const oldY = lift.object.position.y;
      const nextY = advanceLift(oldY, lift.target, dt);
      const rider = !disabled && Math.abs(player.x - lift.definition.x) < 5.2
        && Math.abs(player.z - lift.definition.z) < 5.2 && Math.abs(player.y - oldY) < .15;
      const delta = nextY - oldY;
      lift.object.position.y = nextY;
      if (rider) player.y += delta;
      for (const s of this.props.walkableSurfaces) if (s.sourceObjectId === lift.definition.propId) { s.fromY += delta; s.toY += delta; }
      for (const c of [...this.props.colliders, ...this.props.cameraColliders]) if (c.sourceObjectId === lift.definition.propId) {
        if (c.minY !== undefined) c.minY += delta;
        if (c.maxY !== undefined) c.maxY += delta;
      }
    }
    const near = disabled ? null : this.lifts.find(l => Math.hypot(player.x-l.definition.x,player.z-l.definition.z) < 15
      && l.definition.stops.some(s => Math.abs(player.y-s.y)<2 || Math.abs(player.y-l.object.position.y)<2)) ?? null;
    if (near !== this.selected) { this.selected = near; this.refresh(); }
    this.panel.hidden = !near;
  }
  private refresh(): void {
    this.panel.replaceChildren();
    const lift = this.selected; if (!lift) return;
    const label = document.createElement('strong'); label.textContent = lift.definition.name; this.panel.append(label);
    for (const stop of lift.definition.stops) {
      const button = document.createElement('button'); button.textContent = `${stop.name} (${stop.y} m)`;
      button.title = 'Call the lift here or select this destination while aboard';
      button.onclick = () => { lift.target = stop.y; }; this.panel.append(button);
    }
  }
  dispose(): void { this.panel.remove(); }
}

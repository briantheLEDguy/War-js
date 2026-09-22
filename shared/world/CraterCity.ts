export interface CityPoint { x: number; y: number; z: number }

/** Serialized authored geometry; live collision and lift movement belong to Unreal. */
export interface CraterCityDefinition {
  version: string;
  basinY: number;
  levels: Array<{ id: string; name: string; y: number; radius: number }>;
  recovery: CityPoint[];
  lights?: Array<CityPoint & { color: string; intensity: number; distance: number }>;
  routes: Array<{ id: string; width: number; points: CityPoint[] }>;
  lifts: Array<{ id: string; name: string; propId: string; x: number; z: number; stops: Array<{ name: string; y: number }> }>;
  interiors: Array<{ id: string; name: string; entry: CityPoint; propId: string }>;
  formations: Array<{ id: string; teams: CityPoint[][] }>;
}

/** Authored ground samples shared by rendering, movement and prop placement. */
interface CityElevationGrid {
  segments: number;
  /** Regions constant along x outside this interval need no dense x grid. */
  detailX?: [number, number];
  /** Flat regions outside this interval need no dense rendering grid. */
  detailZ?: [number, number];
}

export type CityElevation = CityElevationGrid & (
  | { heights: number[]; heightRuns?: never }
  | { heights?: never; heightRuns: [endExclusive: number, height: number][] }
);

export { cityHeightAt } from '../../scripts/campaign/compact-city-elevation.mjs';

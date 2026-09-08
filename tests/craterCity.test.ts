import { describe, expect, it } from 'vitest';
import { advanceLift, craterGround, recoverCraterEntry, CraterFloorIndex } from '../src/world/CraterCity';
import type { WorldWalkableSurface } from '../src/world/Props';
const floor = (y: number, x=0): WorldWalkableSurface => ({id:`floor-${y}`,x,z:0,width:18,depth:30,rotY:0,fromY:y,toY:y,axis:'z'});
describe('crater support and recovery', () => {
  const stacked = [floor(0),floor(-105),floor(-175)];
  it('keeps lower streets beneath bridges and the rim', () => {
    expect(craterGround(0,0,-105,stacked)).toBe(-105);
    expect(craterGround(0,0,-175,stacked)).toBe(-175);
    expect(craterGround(0,0,-107,stacked)).toBe(-175);
  });
  it('does not invent floors in the void or climb overhead geometry', () => {
    expect(craterGround(30,0,-105,stacked)).toBe(-330);
    expect(craterGround(0,0,-176,stacked)).toBe(-330);
  });
  it('recovers obsolete flat saves, preserving valid terrace saves', () => {
    const arrival={x:0,y:0,z:421};
    expect(recoverCraterEntry({x:0,y:0,z:0},arrival,[floor(-105)])).toEqual(arrival);
    expect(recoverCraterEntry({x:0,y:-104.8,z:0},arrival,[floor(-105)])).toEqual({x:0,y:-105,z:0});
  });
  it('follows rotated staircase grades', () => {
    const stairs={...floor(-105),width:6,depth:20,rotY:Math.PI/2,fromY:-115,toY:-105};
    expect(craterGround(-9,0,-105,[stairs])).toBeCloseTo(-105.5);
    expect(craterGround(9,0,-115,[stairs])).toBeCloseTo(-114.5);
  });
  it('clamps lift motion at both landings without overshoot and pauses at dt zero', () => {
    expect(advanceLift(-104,-105,1)).toBe(-105);
    expect(advanceLift(-105,0,1)).toBe(-96);
    expect(advanceLift(-105,-245,0)).toBe(-105);
    expect(advanceLift(-105,-245,.5)).toBe(-109.5);
  });
  it('indexes rotated floors without losing edge support or moving lift heights', () => {
    const surfaces = Array.from({length:100},(_,i)=>({...floor(-105,i*40-2000),rotY:i*.37}));
    const index = new CraterFloorIndex(surfaces);
    for(let x=-2020;x<2020;x+=7)for(let z=-20;z<20;z+=7) {
      expect(craterGround(x,z,-105,index.at(x,z))).toBe(craterGround(x,z,-105,surfaces));
    }
    expect(index.at(0,0).length).toBeLessThan(5);
    surfaces[50].fromY=surfaces[50].toY=-150;
    expect(craterGround(0,0,-150,index.at(0,0))).toBe(-150);
  });
});

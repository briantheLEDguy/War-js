import { afterEach, describe, expect, it, vi } from 'vitest';
import { Group } from 'three';
import { CityLifts } from '../src/world/CityLifts';
import { fixedCraterRecovery, type CraterCityDefinition } from '../src/world/CraterCity';
import type { SpawnedProps } from '../src/world/Props';

class Element {
  children: Element[] = []; hidden=false; textContent=''; onclick=()=>{};
  append(...children: Element[]) { this.children.push(...children); }
  replaceChildren() { this.children=[]; }
  remove() { this.children=[]; }
}
afterEach(()=>vi.unstubAllGlobals());
describe('moving city lifts',()=>{
  function setup() {
    vi.stubGlobal('document',{createElement:()=>new Element()});
    const object=new Group();object.position.y=-105;
    const city={basinY:-300,lifts:[{id:'lift',name:'Hoist',propId:'cage',x:0,z:0,stops:[{name:'Transit',y:-105},{name:'Works',y:-245}]}],recovery:[{x:0,y:-105,z:10}]} as CraterCityDefinition;
    const support={id:'cage-floor',sourceObjectId:'cage',x:0,z:0,width:9.5,depth:9.5,rotY:0,axis:'z' as const,fromY:-105,toY:-105};
    const collider={sourceObjectId:'cage',minY:-105,maxY:-101};
    const props={objects:[{id:'cage',object}],walkableSurfaces:[support],colliders:[collider],cameraColliders:[{...collider}]} as SpawnedProps;
    const container=new Element();const controller=new CityLifts(city,props,container as unknown as HTMLElement);
    return {object,city,props,container,controller};
  }
  it('carries boarded passengers, floors and collision together and clamps at a stop',()=>{
    const {object,props,container,controller}=setup(),player={x:0,y:-105,z:0};
    controller.update(0,player,false);
    container.children[0].children.find(e=>e.textContent.startsWith('Works'))!.onclick();
    controller.update(1,player,false);
    expect(player.y).toBe(-114);expect(props.walkableSurfaces[0].fromY).toBe(-114);
    expect(props.colliders[0].minY).toBe(-114);expect(props.cameraColliders[0].maxY).toBe(-110);
    controller.update(30,player,false);expect(object.position.y).toBe(-245);expect(player.y).toBe(-245);
    expect(controller.contains(player)).toBe(true);
    player.z=8;controller.update(0,player,false);
    container.children[0].children.find(e=>e.textContent.startsWith('Transit'))!.onclick();
    controller.update(1,player,false);expect(player.y).toBe(-245);expect(object.position.y).toBe(-236);
  });
  it('supports remote calls and freezes motion when the foreground loop is paused',()=>{
    const {object,container,controller}=setup(),player={x:0,y:-245,z:8};
    controller.update(0,player,false);expect(container.children[0].hidden).toBe(false);
    container.children[0].children.find(e=>e.textContent.startsWith('Works'))!.onclick();
    controller.update(0,player,false);expect(object.position.y).toBe(-105);
    controller.update(30,player,false);expect(object.position.y).toBe(-245);expect(player.y).toBe(-245);
  });
  it('never uses a cage or absent floor as a save/fall recovery location',()=>{
    const {city,props}=setup(),arrival={x:0,y:0,z:421};
    expect(fixedCraterRecovery(city,{x:0,y:-105,z:0},arrival,props.walkableSurfaces)).toBeNull();
    props.walkableSurfaces.push({...props.walkableSurfaces[0],id:'landing',sourceObjectId:'fixed',z:10});
    expect(fixedCraterRecovery(city,{x:0,y:-105,z:0},arrival,props.walkableSurfaces)).toEqual({x:0,y:-105,z:10});
  });
});

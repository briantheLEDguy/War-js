import {PointLight, type Scene} from 'three';
import type {CityPoint,CraterCityDefinition} from './CraterCity';

/** Two fixed light slots keep room transitions from changing shader variants.
 * Window emissives provide distant detail; local lights illuminate occupants. */
export class CityLighting {
  private slots=[new PointLight(),new PointLight()];
  constructor(private city:CraterCityDefinition,scene:Scene) {
    for(const light of this.slots){light.intensity=0;light.castShadow=false;scene.add(light);}
  }
  update(viewer:CityPoint):void {
    const near=(this.city.lights??[]).map(light=>({light,distance:Math.hypot(light.x-viewer.x,light.y-viewer.y,light.z-viewer.z)}))
      .filter(p=>p.distance<p.light.distance && Math.abs(p.light.y-viewer.y)<18).sort((a,b)=>a.distance-b.distance).slice(0,2);
    this.slots.forEach((slot,i)=>{
      const entry=near[i];slot.intensity=entry?.light.intensity??0;
      if(entry){slot.color.set(entry.light.color);slot.distance=entry.light.distance;slot.position.set(entry.light.x,entry.light.y,entry.light.z);}
    });
  }
  dispose():void {for(const slot of this.slots)slot.removeFromParent();}
}

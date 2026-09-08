/** Read-only measurements of exported road-vs-land interpolation at every LOD. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
const work=path.dirname(fileURLToPath(import.meta.url));
const report=JSON.parse(await fs.readFile(path.join(work,'build-report.json'),'utf8'));
const levels=[0,1,2].map(level=>({level,triangles:0,samples:0,missingGroundSamples:0,downwardTriangles:0,degenerateTriangles:0,occludedSamples:0,opaqueOccludedSamples:0,maxGroundAboveRoad:0,minimumRoadClearance:Infinity,worst:[]}));
const measurements=[];
for(const asset of report)for(const lod of asset.lods){
  const bytes=await fs.readFile(path.join(work,'runtime',lod.model)),length=bytes.readUInt32LE(12),doc=JSON.parse(bytes.subarray(20,20+length));
  const accessor=index=>{
    const a=doc.accessors[index],view=doc.bufferViews[a.bufferView],size={5121:1,5123:2,5125:4,5126:4}[a.componentType],n={SCALAR:1,VEC2:2,VEC3:3,VEC4:4}[a.type];
    const stride=view.byteStride??size*n,start=28+length+(view.byteOffset??0)+(a.byteOffset??0);
    return Array.from({length:a.count},(_,i)=>Array.from({length:n},(_,j)=>{const offset=start+i*stride+j*size,v=a.componentType===5126?bytes.readFloatLE(offset):size===4?bytes.readUInt32LE(offset):size===2?bytes.readUInt16LE(offset):bytes.readUInt8(offset);return a.normalized?v/(size===1?255:65535):v;}));
  };
  const surface=doc.meshes.find(mesh=>mesh.name.includes('_surface_')).primitives[0],land=accessor(surface.attributes.POSITION),indices=accessor(surface.indices).flat(),buckets=new Map();
  for(let i=0;i<indices.length;i+=3){
    const tri=indices.slice(i,i+3).map(index=>land[index]),xs=tri.map(p=>p[0]),zs=tri.map(p=>p[2]);
    for(let x=Math.floor(Math.min(...xs)/12.5);x<=Math.floor(Math.max(...xs)/12.5);x++)for(let z=Math.floor(Math.min(...zs)/12.5);z<=Math.floor(Math.max(...zs)/12.5);z++){
      const key=x+','+z;if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(tri);
    }
  }
  const landHeight=(x,z)=>{
    for(const [a,b,c] of buckets.get(Math.floor(x/12.5)+','+Math.floor(z/12.5))??[]){
      const den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2]);
      const u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/den,v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den,w=1-u-v;
      if(u>=-1e-7&&v>=-1e-7&&w>=-1e-7)return u*a[1]+v*b[1]+w*c[1];
    }
    return null;
  };
  const item={model:lod.model,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),triangles:0,samples:0,missingGroundSamples:0,downwardTriangles:0,degenerateTriangles:0,occludedSamples:0,opaqueOccludedSamples:0,maxGroundAboveRoad:0,minimumRoadClearance:Infinity,worst:null};
  for(const mesh of doc.meshes)for(const primitive of mesh.primitives){
    if(doc.materials[primitive.material].name!=='Sunmeadow_limestone_road')continue;
    const vertices=accessor(primitive.attributes.POSITION),colors=accessor(primitive.attributes.COLOR_0),idx=accessor(primitive.indices).flat();
    for(let i=0;i<idx.length;i+=3){
      item.triangles++;const ids=idx.slice(i,i+3),tri=ids.map(index=>vertices[index]);
      const [a,b,c]=tri,area=(b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2]);
      if(area < -1e-9)item.downwardTriangles++;if(Math.abs(area)<=1e-9)item.degenerateTriangles++;
      for(const weights of [[1/3,1/3,1/3],[.5,.5,0],[0,.5,.5],[.5,0,.5],[1,0,0],[0,1,0],[0,0,1]]){
        const alpha=weights.reduce((sum,w,j)=>sum+w*colors[ids[j]][3],0);if(alpha<.1)continue;
        const p=[0,1,2].map(axis=>weights.reduce((sum,w,j)=>sum+w*tri[j][axis],0)),ground=landHeight(p[0],p[2]);if(ground===null){item.missingGroundSamples++;continue;}
        item.samples++;const penetration=ground-p[1];
        item.minimumRoadClearance=Math.min(item.minimumRoadClearance,-penetration);
        if(penetration>.001){item.occludedSamples++;if(alpha>.99)item.opaqueOccludedSamples++;}
        if(penetration>item.maxGroundAboveRoad){item.maxGroundAboveRoad=penetration;item.worst={x:p[0]+asset.x,z:p[2]+asset.z,roadY:p[1],groundY:ground,alpha};}
      }
    }
  }
  const level=levels[lod.level];for(const key of ['triangles','samples','missingGroundSamples','downwardTriangles','degenerateTriangles','occludedSamples','opaqueOccludedSamples'])level[key]+=item[key];
  level.maxGroundAboveRoad=Math.max(level.maxGroundAboveRoad,item.maxGroundAboveRoad);
  level.minimumRoadClearance=Math.min(level.minimumRoadClearance,item.minimumRoadClearance);
  if(item.worst)level.worst.push({...item.worst,model:lod.model,penetration:item.maxGroundAboveRoad});measurements.push(item);
}
for(const level of levels)level.worst.sort((a,b)=>b.penetration-a.penetration);
const result={method:'Actual GLB land triangles versus every road triangle vertex, centroid and edge midpoint with alpha>=0.1. Count occlusion above1mm; opaque means alpha>0.99. Barycentric surfaces, independent of rendering/depth precision.',levels,models:measurements};
await fs.writeFile(path.join(work,'review/road_occlusion_audit.json'),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(levels.map(level=>({...level,worst:level.worst.slice(0,3)})),null,2));

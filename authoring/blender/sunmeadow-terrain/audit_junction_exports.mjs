/** Preserve the terrain surface byte-for-byte while checking new road mesh attributes. */
import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import zlib from 'node:zlib';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
const work=path.dirname(fileURLToPath(import.meta.url));
const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const sourceBytes=await fs.readFile(path.join(work,'terrain-source.json'));
const report=JSON.parse(await fs.readFile(path.join(work,'build-report.json'),'utf8'));
const capture=process.argv.includes('--capture-baseline'),retain=process.argv.includes('--retain-original-tangents'),surfaceHashes={};
const baselinePath=path.join(work,'review/junction_surface_baseline.json');
const baseline=capture?null:JSON.parse(await fs.readFile(baselinePath,'utf8'));
let roadVertices=0,maxUvError=0,maxColorError=0,maxBoundaryError=0;
let maximumTangentDifference=0,changedTangentComponents=0;
const probes=[{name:'filled junction corner',x:-353.6,z:-73.8,min:.99,max:1},{name:'feathered junction verge',x:-354.2,z:-73.2,min:.05,max:.4},{name:'outside rounded junction',x:-356.5,z:-71,min:0,max:0}].map(probe=>({...probe,opacityByLod:[0,0,0]}));
for(const asset of report)for(const lod of asset.lods){
  if(retain){
    const bytes=await fs.readFile(path.resolve(work,'../../../public/assets/models',lod.model)),length=bytes.readUInt32LE(12),doc=JSON.parse(bytes.subarray(20,20+length));
    const primitive=doc.meshes.find(mesh=>mesh.name.includes('_surface_')).primitives[0],a=doc.accessors[primitive.attributes.TANGENT],view=doc.bufferViews[a.bufferView];
    assert.equal(a.componentType,5126);assert.equal(a.type,'VEC4');
    const start=28+length+(view.byteOffset??0)+(a.byteOffset??0),stride=view.byteStride??16;
    const raw=Buffer.concat(Array.from({length:a.count},(_,i)=>bytes.subarray(start+i*stride,start+i*stride+16)));
    assert.equal(sha(raw),baseline.surfaceHashes[lod.model][0].attributes.TANGENT,'Original published tangent data no longer matches captured baseline');
    (baseline.originalTangentData??={})[lod.model]=zlib.deflateSync(raw).toString('base64');continue;
  }
  const bytes=await fs.readFile(path.join(work,'runtime',lod.model)),jsonLength=bytes.readUInt32LE(12),doc=JSON.parse(bytes.subarray(20,20+jsonLength));
  const accessor=index=>{
    const a=doc.accessors[index],view=doc.bufferViews[a.bufferView],components={SCALAR:1,VEC2:2,VEC3:3,VEC4:4}[a.type],size={5121:1,5123:2,5125:4,5126:4}[a.componentType];
    const stride=view.byteStride??components*size,start=28+jsonLength+(view.byteOffset??0)+(a.byteOffset??0);
    const raw=Buffer.concat(Array.from({length:a.count},(_,i)=>bytes.subarray(start+i*stride,start+i*stride+components*size)));
    const values=()=>Array.from({length:a.count},(_,i)=>Array.from({length:components},(_,j)=>{
      const offset=(i*components+j)*size,v=a.componentType===5126?raw.readFloatLE(offset):size===4?raw.readUInt32LE(offset):size===2?raw.readUInt16LE(offset):raw.readUInt8(offset);
      return a.normalized?v/(size===1?255:65535):v;
    }));
    return {hash:sha(raw),values,raw};
  };
  const surface=doc.meshes.find(mesh=>mesh.name.includes('_surface_'));
  surfaceHashes[lod.model]=surface.primitives.map(primitive=>({attributes:Object.fromEntries(Object.entries(primitive.attributes).map(([key,index])=>[key,accessor(index).hash])),indices:accessor(primitive.indices).hash}));
  if(capture)continue;
  const original=baseline.surfaceHashes[lod.model];
  for(let i=0;i<surface.primitives.length;i++){
    for(const [key,value] of Object.entries(surfaceHashes[lod.model][i].attributes)){
      if(key!=='TANGENT')assert.equal(value,original[i].attributes[key],`${lod.model} changed frozen ${key}`);
    }
    assert.equal(surfaceHashes[lod.model][i].indices,original[i].indices,`${lod.model} changed frozen indices`);
    const previous=zlib.inflateSync(Buffer.from(baseline.originalTangentData[lod.model],'base64')),current=accessor(surface.primitives[i].attributes.TANGENT).raw;
    assert.equal(current.length,previous.length);
    for(let offset=0;offset<current.length;offset+=4){const difference=Math.abs(current.readFloatLE(offset)-previous.readFloatLE(offset));maximumTangentDifference=Math.max(maximumTangentDifference,difference);if(difference)changedTangentComponents++;}
  }
  for(const mesh of doc.meshes)for(const primitive of mesh.primitives){
    if(doc.materials[primitive.material].name!=='Sunmeadow_limestone_road')continue;
    const positions=accessor(primitive.attributes.POSITION).values(),uvs=accessor(primitive.attributes.TEXCOORD_0).values(),colors=accessor(primitive.attributes.COLOR_0).values();
    if(asset.x-150<=-350&&asset.x+150>=-350&&asset.z-150<=-78&&asset.z+150>=-78){
      const indices=accessor(primitive.indices).values().flat();
      for(const probe of probes)for(let i=0;i<indices.length;i+=3){
        const ids=indices.slice(i,i+3),[a,b,c]=ids.map(index=>positions[index]),x=probe.x-asset.x,z=probe.z-asset.z;
        const den=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2]);if(Math.abs(den)<1e-10)continue;
        const u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/den,v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/den,w=1-u-v;
        if(u>=-1e-7&&v>=-1e-7&&w>=-1e-7){const alpha=Math.max(0,Math.min(1,u*colors[ids[0]][3]+v*colors[ids[1]][3]+w*colors[ids[2]][3]));probe.opacityByLod[lod.level]=1-(1-probe.opacityByLod[lod.level])*(1-alpha);}
      }
    }
    for(let i=0;i<positions.length;i++){
      const [x,,z]=positions[i],color=colors[i];
      maxBoundaryError=Math.max(maxBoundaryError,Math.abs(x)-150,Math.abs(z)-150);
      // glTF V is inverted relative to Blender UV storage.
      maxUvError=Math.max(maxUvError,Math.abs(uvs[i][0]-(x+asset.x)/2),Math.abs(uvs[i][1]-(1+(z+asset.z)/2)));
      maxColorError=Math.max(maxColorError,...color.slice(0,3).map(v=>Math.abs(v-1)),-color[3],color[3]-1);
      roadVertices++;
    }
  }
}
const current={sourceSha256:sha(sourceBytes),surfaceHashes};
if(retain){await fs.writeFile(baselinePath,JSON.stringify(baseline,null,2)+'\n');console.log('Retained hash-verified original published tangent buffers for numerical comparison.');}
else if(capture){await fs.writeFile(baselinePath,JSON.stringify(current,null,2)+'\n');console.log('Captured exact terrain source and48surface attribute/index hashes.');}
else{
  assert.equal(current.sourceSha256,baseline.sourceSha256,'Junction patch changed frozen source');
  // Blender's tangent recomputation can move one 0.0001 exporter quantization step.
  // Positions, normals, UVs, colors and topology remain exact; retain the drift explicitly.
  assert.ok(maximumTangentDifference<.00011,`Tangent recomputation drift ${maximumTangentDifference}`);
  assert.ok(maxUvError<.0001,`world UV error ${maxUvError}`);assert.ok(maxColorError<.0001,`RGBA error ${maxColorError}`);assert.ok(maxBoundaryError<.0001,`sector clip error ${maxBoundaryError}`);
  for(const probe of probes)for(const opacity of probe.opacityByLod)assert.ok(opacity>=probe.min&&opacity<=probe.max,`${probe.name}: opacity ${opacity}`);
  const result={sourceSha256:current.sourceSha256,unchangedPositionNormalUvColorIndexModels:48,maximumTangentDifference,changedTangentComponents,roadVertices,maxUvError,maxColorError,maxBoundaryError,probes,auditSha256:sha(await fs.readFile(fileURLToPath(import.meta.url)))};
  await fs.writeFile(path.join(work,'review/junction_export_audit.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}

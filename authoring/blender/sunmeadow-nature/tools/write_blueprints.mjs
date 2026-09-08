import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const repo=path.resolve(root,'../../..');
const source=await fs.readFile(path.join(root,'source/design.json'));
const design=JSON.parse(source);
for(const kind of Object.keys(design.assets)){
  const key=`frontier_sunmeadow_${kind}`;
  const build=JSON.parse(await fs.readFile(path.join(root,'review',`${key}_build.json`),'utf8'));
  const main=build.lods[0];
  const blueprint={
    assetId:`prop.frontier.sunmeadow.${kind}`,displayName:design.assets[kind].name,category:'prop',version:'1.0.0',sets:['sunmeadow_authored_nature'],
    runtime:{staticKey:key},output:{model:main.model,artifactDir:'authoring/blender/sunmeadow-nature/runtime'},
    generator:{kind:'copyExisting',copyFrom:`authoring/blender/sunmeadow-nature/runtime/${main.model}`},
    geometry:{originRule:'planted_base_with_buried_root_allowance',upAxis:'+Y',forwardAxis:'+Z',lods:build.lods.map(lod=>({name:`LOD${lod.level}`,triTarget:lod.triangles,screenCoverageMin:[.2,.08,0][lod.level]}))},
    materials:{master:'MM_SunmeadowAuthoredNature',textureSet:'sunmeadow_shared_botanical_atlases',channels:['baseColor','roughness','metallic','normal','occlusion'],maxTextureResolution:1024},
    rigging:{skinned:false,requiredClips:[]},
    collision:{policy:kind==='wheat'||kind==='meadow'?'nonblocking_groundcover':kind==='limestone'?'authored_outcrop_footprint':'authored_trunk_or_hedge_footprint',primitives:[]},
    compatibility:{occupiesSlots:['prop'],requires:[],conflictsWith:[]},
    provenance:{createdBy:'original_authored_branch_paths_and_botanical_meshes',aiAssisted:true,aiStages:['art_direction','branch_path_authoring','leaf_and_blade_topology','uv_surface_painting','lod_authoring','technical_validation','export_reimport_review'],referencePackId:'sunmeadow_late_summer_01',similarityReview:'not_required',author:'Codex Sunmeadow nature authoring',source:'authoring/blender/sunmeadow-nature/source/design.json',sourceSha256:crypto.createHash('sha256').update(source).digest('hex')},
    qc:{allowNonManifold:true,allowUvOverlap:true,maxDrawCalls:2,maxMeshObjects:1,maxFileSizeMb:10,maxTris:Math.max(...build.lods.map(lod=>lod.triangles)),requiresSkinnedMeshes:false,requiresPreview:true,expectedHeightM:main.bounds_runtime.max[1]-main.bounds_runtime.min[1],heightToleranceM:.03},
    lifecycle:{status:'review_pending',notes:'Authored source and three real GLB LODs are staged. No runtime publication or user approval is implied. Open-surface allowance covers double-sided leaf/blade surfaces and assembled botanical joints; these are not watertight collision meshes. UV overlap intentionally reuses species-specific shared atlas tiles. Static foliage has no wind rig. Use review/validation.json and hash-bound reimport renders before approval.'}
  };
  await fs.writeFile(path.join(repo,'scripts/blender-character-pipeline/data/asset-blueprints',`${key}.asset.json`),JSON.stringify(blueprint,null,2)+'\n');
}
console.log(`Wrote ${Object.keys(design.assets).length} staged Sunmeadow blueprints; runtime registry unchanged.`);

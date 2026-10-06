"""Blender 5: retain the detailed master and export native-ready reference architecture.

Run Blender --background --python-exit-code 1 --python this_file. Only ignored
private outputs are written. This never opens or mutates Unreal content.
"""
import hashlib
import json
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

sys.path.insert(0,str(Path(__file__).parent))
from aegis_citadel_blueprint import ROOT, OUT, digest, sha, validate
from aegis_citadel_mesh import (MATERIALS, MATERIAL_SPECS, Mesh, architecture,
    BLENDER_EXPORT_CONVENTION,blender_export_point,blender_export_normal,blender_export_indices,placed_sentinel)

current=json.loads((OUT/'current.json').read_text());RUN=OUT/current['revision']
blueprint=json.loads((RUN/'blueprint.json').read_text());validate(blueprint)
runtime=RUN/'runtime';runtime.mkdir(exist_ok=True)
sources=RUN/'sources';sources.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)

# Use the original authored PBR surfaces, with the reference's blue-grey/gold palette.
materials=[]
for role in MATERIALS:
    spec=MATERIAL_SPECS[role];mat=bpy.data.materials.new('AegisCitadel_'+role);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF')
    def sample(channel):
        texture=ROOT/spec[channel]
        if not texture.is_file():raise RuntimeError('Required authored PBR texture missing: '+str(texture))
        node=nodes.new('ShaderNodeTexImage');node.image=bpy.data.images.load(str(texture),check_existing=True)
        if channel!='baseColor':node.image.colorspace_settings.name='Non-Color'
        node.image.pack();return node
    p.inputs['Base Color'].default_value=(*spec['tint'],1)
    if 'baseColor' in spec:
        color=sample('baseColor');multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY'
        multiply.inputs[0].default_value=1;multiply.inputs[2].default_value=(*spec['tint'],1)
        links.new(color.outputs['Color'],multiply.inputs[1]);links.new(multiply.outputs['Color'],p.inputs['Base Color'])
    p.inputs['Roughness'].default_value=spec['roughness'];p.inputs['Metallic'].default_value=spec['metallic']
    if 'specular' in spec:p.inputs['Specular IOR Level'].default_value=spec['specular']
    if 'orm' in spec:
        packed=sample('orm');split=nodes.new('ShaderNodeSeparateColor');links.new(packed.outputs['Color'],split.inputs['Color'])
        for channel,key in [('Green','Roughness'),('Blue','Metallic')]:
            factor=nodes.new('ShaderNodeMath');factor.operation='MULTIPLY'
            factor.inputs[1].default_value=spec[key.lower()];links.new(split.outputs[channel],factor.inputs[0])
            links.new(factor.outputs[0],p.inputs[key])
    if 'normal' in spec:
        normal=sample('normal');mapping=nodes.new('ShaderNodeNormalMap');mapping.inputs['Strength'].default_value=.45
        links.new(normal.outputs['Color'],mapping.inputs['Color']);links.new(mapping.outputs['Normal'],p.inputs['Normal'])
    if 'height' in spec:
        if any(key in spec for key in ('normal','orm')):raise RuntimeError('Ashlar height must use its matching source alone')
        height=sample('height');bump=nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value=spec['heightStrength']
        bump.inputs['Distance'].default_value=spec['heightDistanceCm']/100
        links.new(height.outputs['Color'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])
    if 'emission' in spec:
        p.inputs['Emission Color'].default_value=(*spec['emission'],1);p.inputs['Emission Strength'].default_value=1
    mat.use_backface_culling=role!='blue';materials.append(mat)


def blender_point(p): return blender_export_point(p)


def blender_normal(n): return blender_export_normal(n)


def add_mesh(data):
    indices=blender_export_indices(data['indices'])
    mesh=bpy.data.meshes.new(data['id'])
    mesh.from_pydata([blender_point(p) for p in data['positions']],[],
                     [indices[i:i+3] for i in range(0,len(indices),3)])
    mesh.update();obj=bpy.data.objects.new(data['id'],mesh);bpy.context.collection.objects.link(obj)
    for material in materials:mesh.materials.append(material)
    uv=mesh.uv_layers.new(name='UVMap')
    for polygon,material in zip(mesh.polygons,data['triangleMaterials']):
        polygon.material_index=material
        polygon.use_smooth=True
        for loop in polygon.loop_indices:uv.data[loop].uv=data['uvs'][mesh.loops[loop].vertex_index]
    # Custom corner normals preserve the authored hard edges and the bounded
    # throne plane repair. Blender stores these in its compressed normal layer.
    supplied=[blender_normal(data['normals'][loop.vertex_index]) for loop in mesh.loops]
    mesh.normals_split_custom_set(supplied);mesh.update()
    def normal_dots():
        return [sum(a[j]*b.vector[j] for j in range(3)) for a,b in zip(supplied,mesh.corner_normals)]
    dots=normal_dots();automatic=[]
    # Blender's compressed custom-normal space is singular at some acute flat
    # panel corners. Automatic flat normals are allowed only on that same plane
    # and must pass the identical final readback bound.
    if min(dots)<.99999:
        retry=supplied[:]
        for index in sorted({i//3 for i,dot in enumerate(dots) if dot<.99999}):
            polygon=mesh.polygons[index];loops=list(polygon.loop_indices)
            first=supplied[loops[0]]
            if any(sum((supplied[i][j]-first[j])**2 for j in range(3))>1e-12
                   or sum(supplied[i][j]*polygon.normal[j] for j in range(3))<.99999 for i in loops):
                raise RuntimeError('Non-flat authored normal cannot use automatic fallback: '+data['id'])
            for i in loops:retry[i]=(0.,0.,0.)
            automatic.append(index)
        # The first decoding has cached the singular loop-normal space. Rebuild
        # the identical surface with flat flags set before encoding its normals.
        previous=mesh;mesh=bpy.data.meshes.new(data['id']+'_checked_normals')
        mesh.from_pydata([blender_point(p) for p in data['positions']],[],
                        [indices[i:i+3] for i in range(0,len(indices),3)])
        mesh.update();flat=set(automatic)
        for material in materials:mesh.materials.append(material)
        uv=mesh.uv_layers.new(name='UVMap')
        for polygon,material in zip(mesh.polygons,data['triangleMaterials']):
            polygon.material_index=material;polygon.use_smooth=polygon.index not in flat
            for loop in polygon.loop_indices:uv.data[loop].uv=data['uvs'][mesh.loops[loop].vertex_index]
        mesh.normals_split_custom_set(retry);mesh.update();obj.data=mesh
        bpy.data.meshes.remove(previous);dots=normal_dots()
    minimum_dot=min(dots)
    if not mesh.has_custom_normals or minimum_dot<.99999:
        raise RuntimeError('Blender did not preserve authored split normals: '+data['id'])
    obj['WarCitadelSourceNormalMinimumDot']=minimum_dot
    obj['WarCitadelAutomaticFlatNormalFaces']=automatic
    obj['WarCitadelRevision']=blueprint['revision'];obj['WarCitadelCollision']=data['collision']
    return obj


structure,gates,placements=architecture(blueprint);rows=[];surface_bindings=[]
for mesh in [*structure,*gates]:
    data=mesh.export();file=runtime/(mesh.key+'.mesh.json')
    file.write_text(json.dumps(data,separators=(',',':'))+'\n')
    obj=add_mesh(data)
    if mesh in gates:obj.hide_render=True
    rows.append(dict(id=mesh.key,meshFile=file.relative_to(RUN).as_posix(),sha256=sha(file),
                     triangles=len(data['indices'])//3,collision=mesh.collision,
                     gateLeaf=mesh in gates,materials=list(MATERIALS)))
    if hasattr(mesh,'floor_union_receipt'):rows[-1]['floorUnion']=mesh.floor_union_receipt
    if hasattr(mesh,'structural_supports'):rows[-1]['structuralSupports']=mesh.structural_supports
    if hasattr(mesh,'crown_replacement'):rows[-1]['crownReplacement']=mesh.crown_replacement
    if hasattr(mesh,'articulated_spire_details'):rows[-1]['articulatedSpireDetails']=mesh.articulated_spire_details
    if hasattr(mesh,'central_standard_replacement'):rows[-1]['centralStandardReplacement']=mesh.central_standard_replacement
    if hasattr(mesh,'wing_hierarchy'):rows[-1]['wingHierarchy']=mesh.wing_hierarchy
    if hasattr(mesh,'wing_foundation_repairs'):rows[-1]['wingFoundationRepairs']=mesh.wing_foundation_repairs
    if hasattr(mesh,'surface_bindings'):
        surface_bindings.extend([{**binding,'sourceMeshSha256':sha(file)} for binding in mesh.surface_bindings])
    rows[-1]['blenderSplitNormals']=dict(applied=True,minimumDot=obj['WarCitadelSourceNormalMinimumDot'],
        automaticFlatFaces=list(obj['WarCitadelAutomaticFlatNormalFaces']))
    print('WAR_CITADEL_GEOMETRY '+mesh.key+' '+str(len(data['indices'])//3),flush=True)

# Reuse actual detailed Aegis furnishings; transform/export their real triangles.
prop_sources=[]
for placement in placements:
    source=ROOT/placement['source']
    if not source.is_file():raise RuntimeError('Required authored citadel furnishing missing: '+str(source))
    sculpture=placement['id']=='court_oath' or 'guard' in placement['id']
    if sculpture:
        combined=placed_sentinel(placement)
        adaptation=dict(kind='original_sentinel_v6',sourceRecipe='scripts/unreal/aegis_citadel_statue.py',
            sourceRecipeSha256=sha(ROOT/'scripts/unreal/aegis_citadel_statue.py'),
            legacyScaleReference=dict(file=placement['source'],sha256=sha(source)),
            footFit=combined.foot_fit,normals='preserve_authored_smooth_patches_and_hard_plate_seams')
    else:
        before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(source))
        imported=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
        if not imported:raise RuntimeError('Source furnishing contains no mesh: '+str(source))
        combined=Mesh('furnishing_'+placement['id'])
        minz=min((o.matrix_world@Vector(v)).z for o in imported for v in o.bound_box)
        # Original furnishings use metres. Their frontage faces the approach.
        rotation=Matrix.Rotation(-3.141592653589793/2,4,'Z')
        for obj in imported:
            obj.data.calc_loop_triangles()
            for tri in obj.data.loop_triangles:
                verts=[]
                for index in tri.vertices:
                    p=obj.matrix_world@obj.data.vertices[index].co;p.z-=minz
                    p=rotation@p;p*=placement['scale']
                    verts.append([-p.y*100+placement['point'][0],p.x*100+placement['point'][1],p.z*100+placement['point'][2]])
                name=obj.data.materials[tri.material_index].name.lower() if obj.data.materials else ''
                role='gold' if any(k in name for k in ('gold','copper','brass')) else 'iron' if 'iron' in name else 'blue' if any(k in name for k in ('canvas','tapestry')) else 'glass' if any(k in name for k in ('glow','flame','ember','amber','glass')) else 'carved_stone'
                combined.face(verts,role)
        adaptation=combined.cohere_throne_gold_faces() if placement['id']=='throne' else None
        for obj in imported:bpy.data.objects.remove(obj,do_unlink=True)
    data=combined.export();file=runtime/(combined.key+'.mesh.json');file.write_text(json.dumps(data,separators=(',',':'))+'\n')
    obj=add_mesh(data);rows.append(dict(id=combined.key,meshFile=file.relative_to(RUN).as_posix(),sha256=sha(file),
        triangles=len(data['indices'])//3,collision=True,gateLeaf=False,materials=list(MATERIALS),source=placement['source']))
    if adaptation:rows[-1]['surfaceAdaptation']=adaptation
    rows[-1]['blenderSplitNormals']=dict(applied=True,minimumDot=obj['WarCitadelSourceNormalMinimumDot'],
        automaticFlatFaces=list(obj['WarCitadelAutomaticFlatNormalFaces']))
    prop_sources.append(dict(file=placement['source'],sha256=sha(source)))

bpy.ops.wm.save_as_mainfile(filepath=str(sources/'Bastion_Reference_Citadel.blend'))
exports=[]
for row in rows:
    obj=bpy.data.objects[row['id']];bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj
    glb=runtime/(row['id']+'.glb');fbx=runtime/(row['id']+'.fbx')
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_yup=True,
        export_texcoords=True,export_normals=True,export_materials='EXPORT')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},
        apply_unit_scale=True,axis_forward='-Y',axis_up='Z',path_mode='COPY',embed_textures=True)
    exports.append(dict(id=row['id'],glb=dict(path=glb.relative_to(RUN).as_posix(),sha256=sha(glb)),
                        fbx=dict(path=fbx.relative_to(RUN).as_posix(),sha256=sha(fbx))))
report=dict(schemaVersion=1,revision=blueprint['revision'],blueprintSignature=blueprint['signature'],
    recipeSha256=sha(Path(__file__).with_name('aegis_citadel_mesh.py')),assets=rows,exports=exports,
    sourceFurnishings=prop_sources,materialSpecs=MATERIAL_SPECS,surfaceBindings=surface_bindings,
    materialSources={file:sha(ROOT/file) for spec in MATERIAL_SPECS.values() for key,file in spec.items()
                     if key in ('baseColor','normal','orm','height','provenance')},
    geometrySignature=digest([(r['id'],r['sha256']) for r in rows]),
    sourceMaster=dict(path='sources/Bastion_Reference_Citadel.blend',sha256=sha(sources/'Bastion_Reference_Citadel.blend')),
    blenderExportConvention=BLENDER_EXPORT_CONVENTION,
    nativeImported=False,visualApproved=False,traversalApproved=False)
(RUN/'assets-source.json').write_text(json.dumps(report,indent=2)+'\n')
print('WAR_CITADEL_SOURCE_READY='+str(RUN/'assets-source.json'),flush=True)

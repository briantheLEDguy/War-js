"""Unreal-only helpers for isolated, source-derived world asset construction."""
import hashlib
from pathlib import Path
import unreal


class WorldAssets:
    def __init__(self, root, collection):
        self.root, self.collection = root, collection
        self.folder = '/Game/WorldRebuild/'+collection
        self.tools = unreal.AssetToolsHelpers.get_asset_tools()
        self.textures, self.materials = {}, {}

    def texture(self, row, normal=False):
        source = (self.root/row['path']).resolve()
        if not (source.is_relative_to((self.root/'public/assets').resolve()) or source.is_relative_to((self.root/'artifacts/unreal/world-portals/static/textures').resolve())):
            raise RuntimeError('Texture is outside approved input roots')
        fingerprint = hashlib.sha256(source.read_bytes()).hexdigest()
        if fingerprint != row['sha256']: raise RuntimeError('Texture changed: '+row['path'])
        key = fingerprint+('_normal' if normal else '_color')
        if key in self.textures: return self.textures[key]
        task = unreal.AssetImportTask()
        task.filename, task.destination_path, task.destination_name = str(source), self.folder+'/Textures', 'T_'+key[:20]+('_N' if normal else '_C')
        task.automated, task.save = True, True
        self.tools.import_asset_tasks([task])
        objects = task.get_objects()
        if len(objects) != 1: raise RuntimeError('Texture import failed')
        texture = objects[0]
        texture.set_editor_property('srgb', not normal)
        if normal: texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
        unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)
        self.textures[key] = texture
        return texture

    def material(self, key, row):
        if key in self.materials: return self.materials[key]
        material = self.tools.create_asset('M_'+key, self.folder+'/Materials', unreal.Material, unreal.MaterialFactoryNew())
        if not material: raise RuntimeError('Material creation failed: '+key)
        lib = unreal.MaterialEditingLibrary
        color = lib.create_material_expression(material, unreal.MaterialExpressionConstant3Vector)
        factor = row.get('color',[1,1,1,1])
        color.set_editor_property('constant', unreal.LinearColor(*factor[:3],1))
        output, output_pin = color, ''
        alpha = lib.create_material_expression(material,unreal.MaterialExpressionConstant)
        alpha.set_editor_property('r',factor[3])
        alpha_pin = ''
        for kind, definition in row.get('textures',{}).items():
            node = lib.create_material_expression(material, unreal.MaterialExpressionTextureSample)
            node.set_editor_property('texture',self.texture(definition, kind=='normal'))
            node.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='normal' else unreal.MaterialSamplerType.SAMPLERTYPE_COLOR)
            if kind=='normal': lib.connect_material_property(node,'RGB',unreal.MaterialProperty.MP_NORMAL)
            else:
                multiply = lib.create_material_expression(material,unreal.MaterialExpressionMultiply)
                lib.connect_material_expressions(node,'RGB',multiply,'A')
                lib.connect_material_expressions(color,'',multiply,'B')
                output, output_pin = multiply, ''
                opacity = lib.create_material_expression(material,unreal.MaterialExpressionMultiply)
                lib.connect_material_expressions(node,'A',opacity,'A')
                lib.connect_material_expressions(alpha,alpha_pin,opacity,'B')
                alpha, alpha_pin = opacity, ''
        if row.get('vertexColors'):
            vertex = lib.create_material_expression(material,unreal.MaterialExpressionVertexColor)
            tint = lib.create_material_expression(material,unreal.MaterialExpressionMultiply)
            lib.connect_material_expressions(output,output_pin,tint,'A')
            lib.connect_material_expressions(vertex,'RGB',tint,'B')
            output, output_pin = tint, ''
            opacity = lib.create_material_expression(material,unreal.MaterialExpressionMultiply)
            lib.connect_material_expressions(alpha,alpha_pin,opacity,'A')
            lib.connect_material_expressions(vertex,'A',opacity,'B')
            alpha, alpha_pin = opacity, ''
        mode = row.get('alphaMode','OPAQUE')
        if mode == 'BLEND':
            material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
            material.set_editor_property('translucency_lighting_mode',unreal.TranslucencyLightingMode.TLM_SURFACE)
            lib.connect_material_property(alpha,alpha_pin,unreal.MaterialProperty.MP_OPACITY)
        elif mode == 'MASK':
            material.set_editor_property('blend_mode',unreal.BlendMode.BLEND_MASKED)
            material.set_editor_property('opacity_mask_clip_value',row.get('alphaCutoff',0.5))
            lib.connect_material_property(alpha,alpha_pin,unreal.MaterialProperty.MP_OPACITY_MASK)
        lib.connect_material_property(output,output_pin,unreal.MaterialProperty.MP_BASE_COLOR)
        for name, pin in [('roughness',unreal.MaterialProperty.MP_ROUGHNESS),('metallic',unreal.MaterialProperty.MP_METALLIC)]:
            value = lib.create_material_expression(material,unreal.MaterialExpressionConstant)
            value.set_editor_property('r',row.get(name,1 if name=='roughness' else 0))
            lib.connect_material_property(value,'',pin)
        material.set_editor_property('two_sided',row.get('doubleSided',False))
        lib.recompile_material(material)
        unreal.EditorAssetLibrary.save_loaded_asset(material,only_if_is_dirty=False)
        self.materials[key]=material
        return material

    def mesh(self, key, data, material, collision):
        args = [self.collection,key,[unreal.Vector(*p) for p in data['positions']],data['indices'],
                [unreal.Vector(*p) for p in data['normals']],[unreal.Vector2D(*p) for p in data['uvs']]]
        if data.get('colors'):
            mesh = unreal.WarImportLibrary.create_colored_world_surface(*args,[unreal.LinearColor(*p) for p in data['colors']],material,collision)
        else:
            mesh = unreal.WarImportLibrary.create_world_surface(*args,material,collision)
        if not mesh or not unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False):
            raise RuntimeError('Source surface construction failed: '+key)
        return mesh

    def composite(self, key, data, collision):
        materials = [self.material(key+'_'+str(index), row) for index,row in enumerate(data['materials'])]
        mesh = unreal.WarImportLibrary.create_composite_world_surface(self.collection,key,
            [unreal.Vector(*p) for p in data['positions']],data['indices'],[unreal.Vector(*p) for p in data['normals']],
            [unreal.Vector2D(*p) for p in data['uvs']],[unreal.LinearColor(*p) for p in data['colors']],
            data['triangleMaterials'],materials,collision)
        if not mesh or not unreal.EditorAssetLibrary.save_loaded_asset(mesh,only_if_is_dirty=False):
            raise RuntimeError('Composite source mesh construction failed: '+key)
        if mesh.get_num_sections(0) != len(materials): raise RuntimeError('Source material sections were lost')
        return mesh


def ground(world, point, radius=50000):
    hit = unreal.SystemLibrary.line_trace_single(world,point+unreal.Vector(0,0,radius),point-unreal.Vector(0,0,radius),
        unreal.TraceTypeQuery.ECC_VISIBILITY,True,[],unreal.DrawDebugTrace.NONE,True)
    if not isinstance(hit,unreal.HitResult) or not hit.to_tuple()[0]:
        raise RuntimeError('No ground at '+str(point))
    return hit.to_tuple()[5]

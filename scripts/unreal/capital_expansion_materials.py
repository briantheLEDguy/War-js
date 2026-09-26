"""Bounded, role-specific private material instances; purchased parents stay intact."""
import hashlib
import unreal
from capital_expansion import PALETTES


class ExpansionMaterials:
    def __init__(self, destination):
        self.destination=destination
        self.cache={}

    def material(self, source, district, role):
        if role in ('original','furniture'): return source
        key=(source.get_path_name(),district,role)
        if key in self.cache: return self.cache[key]
        lib=unreal.MaterialEditingLibrary
        parameters=[str(n) for n in lib.get_vector_parameter_names(source)]
        parameter=next((n for n in ('Base_Color_Tint','BaseColorTint','Tint','Color') if n in parameters),None)
        if not parameter: return source
        identity=hashlib.sha256('|'.join(key).encode()).hexdigest()[:16]
        name='MI_'+role+'_'+district+'_'+identity
        target=self.destination+'/'+name
        material=unreal.load_asset(target) if unreal.EditorAssetLibrary.does_asset_exist(target) else None
        colors=PALETTES[district]
        color=colors[1 if role=='roof' else 2 if role=='trim' else 0]
        # The original warm atlas needs a lighter, cooler multiplier on masonry.
        strength=2.2 if role=='wall' else 1.4 if role=='floor' else 1.7
        tint=tuple(v*strength for v in color)
        if material:
            actual=lib.get_material_instance_vector_parameter_value(material,parameter)
            if max(abs(a-b) for a,b in zip((actual.r,actual.g,actual.b),tint))>.0001:
                raise RuntimeError('Preserve edited expansion palette: '+target)
        else:
            material=unreal.AssetToolsHelpers.get_asset_tools().create_asset(name,self.destination,
                unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
            if not material: raise RuntimeError('Material creation failed')
            lib.set_material_instance_parent(material,source)
            lib.set_material_instance_vector_parameter_value(material,parameter,unreal.LinearColor(*tint,1))
            actual=lib.get_material_instance_vector_parameter_value(material,parameter)
            if max(abs(a-b) for a,b in zip((actual.r,actual.g,actual.b),tint))>.0001:
                raise RuntimeError('Material parameter readback failed')
            if not unreal.EditorAssetLibrary.save_loaded_asset(material,False): raise RuntimeError('Palette save failed')
        self.cache[key]=material
        return material

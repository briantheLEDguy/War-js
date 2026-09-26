"""Import owner-supplied login art; preserve PNGs and cook private UI materials.

Run with UnrealEditor-Cmd -run=pythonscript -script=<absolute path> -nullrhi.
UV cropping removes transparent canvas margins. A material-only bronze treatment
removes blue from the UI without modifying the source artwork.
"""
import hashlib
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'unreal/AegisWar/graphics-new'
FOLDER = '/Game/UI/Frontend/Artwork'
OWNER = 'frontend-owner-art-v1'
ASSETS = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
LIB = unreal.MaterialEditingLibrary
# Inclusive/exclusive alpha bounds measured from the supplied original PNGs.
ART = [
    ('Logo', 'aegislogo.png', (1672, 941), (3, 132, 1669, 682)),
    ('Button', 'button.png', (2172, 724), (37, 150, 2137, 571)),
    ('Window', 'window.png', (1086, 1448), (66, 16, 1020, 1401)),
]


def owned(path):
    asset = ASSETS.load_asset(path) if ASSETS.does_asset_exist(path) else None
    if asset and ASSETS.get_metadata_tag(asset, 'WarFrontendOwner') != OWNER:
        raise RuntimeError('Refusing to overwrite unowned artwork: ' + path)
    return asset


def link(source, output, target, pin):
    if not LIB.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Cannot connect artwork material: ' + pin)


receipt = []
for name, filename, size, bounds in ART:
    source = SOURCE / filename
    original = source.read_bytes()
    if original[:8] != b'\x89PNG\r\n\x1a\n' or tuple(int.from_bytes(original[i:i+4], 'big') for i in (16, 20)) != size:
        raise RuntimeError('Artwork canvas changed; remeasure alpha bounds: ' + filename)
    owned(FOLDER + '/T_' + name)
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path, task.destination_name = FOLDER, 'T_' + name
    task.automated, task.replace_existing, task.save = True, True, False
    TOOLS.import_asset_tasks([task])
    objects = task.get_objects()
    if len(objects) != 1 or not isinstance(objects[0], unreal.Texture2D):
        raise RuntimeError('Artwork texture import failed: ' + filename)
    texture = objects[0]
    texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    texture.set_editor_property('srgb', True)
    ASSETS.set_metadata_tag(texture, 'WarFrontendOwner', OWNER)
    ASSETS.save_loaded_asset(texture)

    material = owned(FOLDER + '/M_' + name)
    if not material:
        material = TOOLS.create_asset('M_' + name, FOLDER, unreal.Material, unreal.MaterialFactoryNew())
    ASSETS.set_metadata_tag(material, 'WarFrontendOwner', OWNER)
    material.set_editor_property('material_domain', unreal.MaterialDomain.MD_UI)
    material.set_editor_property('blend_mode', unreal.BlendMode.BLEND_TRANSLUCENT)
    LIB.delete_all_material_expressions(material)
    def expression(kind):
        return LIB.create_material_expression(material, kind)
    uv = expression(unreal.MaterialExpressionTextureCoordinate)
    scale = expression(unreal.MaterialExpressionConstant2Vector)
    scale.set_editor_property('r', (bounds[2] - bounds[0]) / size[0])
    scale.set_editor_property('g', (bounds[3] - bounds[1]) / size[1])
    offset = expression(unreal.MaterialExpressionConstant2Vector)
    offset.set_editor_property('r', bounds[0] / size[0])
    offset.set_editor_property('g', bounds[1] / size[1])
    multiply_uv, add_uv = expression(unreal.MaterialExpressionMultiply), expression(unreal.MaterialExpressionAdd)
    link(uv, '', multiply_uv, 'A'); link(scale, '', multiply_uv, 'B')
    link(multiply_uv, '', add_uv, 'A'); link(offset, '', add_uv, 'B')
    sample = expression(unreal.MaterialExpressionTextureSample)
    sample.set_editor_property('texture', texture)
    link(add_uv, '', sample, 'UVs')
    gray = expression(unreal.MaterialExpressionDesaturation)
    full = expression(unreal.MaterialExpressionConstant)
    full.set_editor_property('r', 1.0)
    link(sample, 'RGB', gray, ''); link(full, '', gray, 'Fraction')
    bronze = expression(unreal.MaterialExpressionConstant3Vector)
    bronze.set_editor_property('constant', unreal.LinearColor(1.0, .78, .48, 1))
    color = expression(unreal.MaterialExpressionMultiply)
    link(gray, '', color, 'A'); link(bronze, '', color, 'B')
    if not LIB.connect_material_property(color, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Cannot connect artwork color')
    if not LIB.connect_material_property(sample, 'A', unreal.MaterialProperty.MP_OPACITY):
        raise RuntimeError('Cannot connect artwork transparency')
    LIB.recompile_material(material)
    ASSETS.save_loaded_asset(material)
    if source.read_bytes() != original:
        raise RuntimeError('Source artwork changed during import')
    receipt.append({'source': filename, 'sha256': hashlib.sha256(original).hexdigest(),
                    'material': material.get_path_name(), 'alphaBounds': bounds})

output = ROOT / 'artifacts/unreal/frontend/artwork.json'
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({'artwork': receipt, 'sourceModified': False, 'treatment': 'bronze-desaturation'}, indent=2) + '\n')
unreal.log('WAR_FRONTEND_ARTWORK_IMPORTED')

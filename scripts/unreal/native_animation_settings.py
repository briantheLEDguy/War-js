"""Stable compression subobject identity is part of Unreal's cached pose format."""
import unreal

COMPRESSION_PATH='/Game/Characters/AnimationReplacement/SuppliedPoseCompressionV1'

def compression_settings():
    library=unreal.EditorAssetLibrary
    if library.does_asset_exist(COMPRESSION_PATH):
        asset=unreal.load_asset(COMPRESSION_PATH)
        codecs=asset.get_editor_property('codecs')
        if len(codecs)!=1 or codecs[0].get_name()!='SuppliedPoseCodec':
            raise RuntimeError('Supplied pose compression identity changed')
        return asset
    asset=unreal.AssetToolsHelpers.get_asset_tools().create_asset('SuppliedPoseCompressionV1',
        '/Game/Characters/AnimationReplacement',unreal.AnimBoneCompressionSettings,unreal.AnimBoneCompressionSettingsFactory())
    codec=unreal.new_object(unreal.load_class(None,'/Script/ACLPlugin.AnimBoneCompressionCodec_ACLSafe'),outer=asset,name='SuppliedPoseCodec')
    codec.set_editor_properties({'ErrorThreshold':.000099,'DefaultVirtualVertexDistance':100.,'SafeVirtualVertexDistance':100.})
    asset.set_editor_property('codecs',[codec])
    if not library.save_loaded_asset(asset,False): raise RuntimeError('Compression settings could not be saved')
    return asset

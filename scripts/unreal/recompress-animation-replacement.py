"""Repair supplied-set DDC bindings without editing poses or source content."""
import json
from pathlib import Path
import sys
import unreal
sys.path.insert(0,str(Path(__file__).parent))
from animation_replacement import OUT
from native_animation_settings import compression_settings
settings=compression_settings()
paths=set()
for entry in json.loads((OUT/'retarget.json').read_text())['profiles'].values():
    paths.update(clip['animation'] for clip in entry['clips'].values())
for entry in json.loads((OUT/'presentations.json').read_text())['profiles'].values():
    paths.update(entry['bindings'].values())
for path in sorted(paths):
    animation=unreal.load_asset(path)
    animation.set_editor_property('bone_compression_settings',settings)
    if not unreal.WarImportLibrary.finalize_animation_sampling(animation): raise RuntimeError('Compression failed: '+path)
    if not unreal.EditorAssetLibrary.save_loaded_asset(animation,False): raise RuntimeError('Save failed: '+path)
unreal.log('WAR_RECOMPRESSED='+str(len(paths)))

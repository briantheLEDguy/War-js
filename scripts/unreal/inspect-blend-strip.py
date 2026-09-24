"""Read-only diagnosis of a preservation-check failure."""
from pathlib import Path
import bpy
source=Path(__file__).with_name('strip-blend-character-tracks.py').read_text()
scope={'__file__':str(Path(__file__).with_name('strip-blend-character-tracks.py'))}
exec(source[:source.index("apply='--apply'")],scope)
root=Path(__file__).resolve().parents[2]
path=root/'authoring/blender/cinderfen-peat-worker/releases/frontier_cinderfen_greenskin_peat_worker/515dd65184a7e3748663/files/authoring/blender/frontier-population/foundations/mire_brutish_v1_m.source.blend'
temporary=root/'artifacts/unreal/animation-replacement/strip-candidates/a642046928a20d42.blend'
rows=[]
for file in (path,temporary):
    bpy.ops.wm.open_mainfile(filepath=str(scope['native_path'](file)),load_ui=False,use_scripts=False)
    rows.append(scope['signature'](True))
print('WAR_EXTRA_IDS',set(rows[1])-set(rows[0]),'WAR_MISSING_IDS',set(rows[0])-set(rows[1]))
print('WAR_FIRST_DIFFERENT',next((k for k,v in rows[0].items() if rows[1].get(k)!=v),None))

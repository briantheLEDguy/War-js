"""Remove only legacy corrective-shape animation; preserve all shape geometry."""
import json
import ast
from pathlib import Path
import bpy

TOOLS=Path(__file__).parent
scope={'__file__':str(TOOLS/'strip-blend-character-tracks.py')}
source=(TOOLS/'strip-blend-character-tracks.py').read_text()
exec(source[:source.index("apply='--apply'")],scope)
ROOT=scope['ROOT']; OUT=ROOT/'artifacts/unreal/animation-replacement'
signature=scope['signature']; digest=scope['digest']; native=scope['native_path']
plan=json.loads((OUT/'blend-track-plan.json').read_text())
receipt=OUT/'morph-track-removal.json'
rows=json.loads(receipt.read_text()) if receipt.exists() else []
done={r['path'] for r in rows}
for row in plan:
    channels=[c for a in row['actions'] for c in a['channels']]
    if row['path'] in done or not any(c.startswith('key_blocks[') for c in channels) or not all(c.startswith(('key_blocks[','pose.bones[')) for c in channels): continue
    path=ROOT/row['path']
    if not path.exists() or not row['actions']: continue
    if digest(native(path).read_bytes())!=row['beforeSha256']: raise RuntimeError('Morph source changed: '+row['path'])
    bpy.ops.wm.open_mainfile(filepath=str(native(path)),load_ui=False,use_scripts=False)
    rigs={o for o in bpy.data.objects if o.type=='ARMATURE' and o.name=='roe_deer_buck_rig'}
    owned=set()
    for obj in bpy.data.objects:
        if obj.type!='MESH' or not obj.data.shape_keys: continue
        if not any(m.type=='ARMATURE' and m.object in rigs for m in obj.modifiers): continue
        keys=obj.data.shape_keys; data=keys.animation_data
        if data:
            if data.action: owned.add(data.action)
            for track in data.nla_tracks:
                owned.update(strip.action for strip in track.strips if strip.action)
    # Combined Blender action slots can retain orphaned bone channels alongside
    # shape channels. Resolve every channel against this exact character rig.
    bones={b.name for rig in rigs for b in rig.data.bones}
    shapes={key.name for obj in bpy.data.objects if obj.type=='MESH' and obj.data.shape_keys for key in obj.data.shape_keys.key_blocks}
    for action in bpy.data.actions:
        for channel in scope['action_paths'](action):
            prefix='key_blocks[' if channel.startswith('key_blocks[') else 'pose.bones['
            name=ast.literal_eval(channel[len(prefix):channel.index('].')])
            if name not in (shapes if prefix=='key_blocks[' else bones): raise RuntimeError('Unknown corrective channel')
        owned.add(action)
    for blocks in (bpy.data.objects,bpy.data.meshes,bpy.data.armatures,bpy.data.materials,bpy.data.images,bpy.data.node_groups):
        for block in blocks:
            if block.users==0: block.use_fake_user=True
    before=signature(); names=sorted(a.name for a in owned)
    for action in owned: bpy.data.actions.remove(action,do_unlink=True)
    if signature()!=before: raise RuntimeError('Morph geometry changed')
    bpy.context.preferences.filepaths.save_version=0
    candidate=OUT/'strip-candidates'/('morph-'+digest(row['path'].encode())[:12]+'.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(candidate),check_existing=False,relative_remap=False)
    bpy.ops.wm.open_mainfile(filepath=str(native(path)),load_ui=False,use_scripts=False); before=signature()
    bpy.ops.wm.open_mainfile(filepath=str(candidate),load_ui=False,use_scripts=False)
    if signature()!=before or bpy.data.actions: raise RuntimeError('Morph preservation check failed')
    candidate.replace(native(path))
    rows.append(dict(path=row['path'],beforeSha256=row['beforeSha256'],afterSha256=digest(native(path).read_bytes()),preservationSha256=before,removedActions=names))
    receipt.write_text(json.dumps(rows,indent=2)+'\n')
print('WAR_MORPH_TRACKS_REMOVED='+str(len(rows)))

"""Strip superseded character Actions/NLA without editing model datablocks.

Run in Blender after source GLB stripping. Every changed file is reopened and its
geometry, weights, rest rig, UVs, materials and packed image bytes compared. Save
versions are disabled so this operation cannot create an animated .blend1 copy.
"""
import hashlib
import ast
import json
from pathlib import Path
import struct
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/unreal/animation-replacement/blend-track-removal.json'
PLAN=OUT.with_name('blend-track-plan.json')
CHARACTER_RIGS={'humanoid_game_v2','Riftbound_chaos_rig','Riftbound_dark_elf_rig',
    'Riftbound_greenskin_rig','crew_left','crew_right','dark_elf_supply_officer_rig',
    'draft_horse_rig','dwarf_artisan_rig','empire_farmer_rig','empire_field_captain_rig',
    'empire_herbalist_rig','greenskin_peat_worker_rig','greenskin_quartermaster_rig',
    'high_elf_scout_rig','roe_deer_buck_rig','skylark_rig','skylark_v2_rig'}


def digest(data): return hashlib.sha256(data).hexdigest()


def native_path(path):
    return Path('\\\\?\\'+str(path)) if sys.platform=='win32' else path


def signature(details=False):
    h=hashlib.sha256()
    checkpoints={}
    def add(value): h.update(repr(value).encode('utf-8'))
    def floats(values): h.update(struct.pack('<'+'f'*len(values),*values))
    for obj in sorted(bpy.data.objects,key=lambda o:o.name):
        if obj.type not in {'MESH','ARMATURE','EMPTY'}: continue
        add((obj.name,obj.type,obj.parent.name if obj.parent else None,obj.parent_type,obj.parent_bone))
        for row in obj.matrix_parent_inverse: floats(tuple(row))
        if obj.type=='ARMATURE':
            for bone in obj.data.bones:
                add((bone.name,bone.parent.name if bone.parent else None,bone.use_deform))
                for row in bone.matrix_local: floats(tuple(row))
        elif obj.type=='MESH':
            mesh=obj.data
            add([g.name for g in obj.vertex_groups])
            for vertex in mesh.vertices:
                floats(tuple(vertex.co)); add([(g.group,round(g.weight,7)) for g in vertex.groups])
            for polygon in mesh.polygons: add((tuple(polygon.vertices),polygon.material_index,polygon.use_smooth))
            for uv in mesh.uv_layers:
                add(uv.name)
                for value in uv.data: floats(tuple(value.uv))
            if mesh.shape_keys:
                for key in mesh.shape_keys.key_blocks:
                    add(key.name)
                    for vertex in key.data: floats(tuple(vertex.co))
            add([m.name if m else None for m in mesh.materials])
        checkpoints['object:'+obj.name]=h.hexdigest()
    for mat in sorted(bpy.data.materials,key=lambda m:m.name):
        add((mat.name,tuple(mat.diffuse_color),mat.use_nodes))
        if mat.node_tree:
            for node in sorted(mat.node_tree.nodes,key=lambda n:n.name):
                add((node.name,node.bl_idname))
                for socket in node.inputs:
                    value=getattr(socket,'default_value',None)
                    add((socket.name,tuple(value) if hasattr(value,'__iter__') and not isinstance(value,str) else value))
                if hasattr(node,'image'): add(node.image.name if node.image else None)
            add(sorted((l.from_node.name,l.from_socket.name,l.to_node.name,l.to_socket.name) for l in mat.node_tree.links))
        checkpoints['material:'+mat.name]=h.hexdigest()
    for im in sorted(bpy.data.images,key=lambda i:i.name):
        # Unpacked FILE dimensions are resolved from the current .blend folder,
        # not stored image payload. The candidate deliberately lives elsewhere;
        # preserve the exact path/colour space and all packed/generated pixels.
        size=tuple(im.size) if im.packed_file or im.source!='FILE' else None
        add((im.name,im.filepath,size,im.colorspace_settings.name))
        if im.packed_file: add(digest(im.packed_file.data))
        checkpoints['image:'+im.name]=h.hexdigest()
    return checkpoints if details else h.hexdigest()


def action_paths(action):
    for layer in getattr(action,'layers',[]):
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves: yield curve.data_path


apply='--apply' in sys.argv
plan=json.loads(PLAN.read_text()) if apply else []
approved={row['path']:row for row in plan}
rows=json.loads(OUT.read_text()) if OUT.exists() else []
completed={row['path']:row['afterSha256'] for row in rows}
files=sorted(p for folder in ('authoring','artifacts') for p in (ROOT/folder).rglob('*.blend*')
             if p.suffix in {'.blend','.blend1','.blend2'})
for path in files:
    path=path.resolve(); relative=path.relative_to(ROOT).as_posix()
    if '/animation-replacement/' in relative: continue
    if apply and relative not in approved: continue
    before_hash=digest(native_path(path).read_bytes())
    if completed.get(relative)==before_hash: continue
    bpy.ops.wm.open_mainfile(filepath=str(native_path(path)),load_ui=False,use_scripts=False)
    rigs={o for o in bpy.data.objects if o.type=='ARMATURE'}
    characters=set(rigs)
    for obj in bpy.data.objects:
        ancestor=obj.parent
        while ancestor:
            if ancestor in rigs: characters.add(obj); break
            ancestor=ancestor.parent
        if any(m.type=='ARMATURE' and m.object in rigs for m in obj.modifiers): characters.add(obj)
    # An action is eligible only when every owning object belongs to an
    # identified character rig. Names such as "idle" are never evidence.
    owners={a:set() for a in bpy.data.actions}
    for obj in bpy.data.objects:
        data=obj.animation_data
        if not data: continue
        if data.action: owners[data.action].add(obj)
        for track in data.nla_tracks:
            for strip in track.strips:
                if strip.action: owners[strip.action].add(obj)
    identified={r for r in rigs if r.name.split('.')[0] in CHARACTER_RIGS}
    character_actions={a for a,refs in owners.items() if refs and refs.issubset(characters)
                       and any(r in refs or any(o in r.children_recursive for o in refs) for r in identified)}
    for action,refs in owners.items():
        paths=list(action_paths(action))
        if refs or not paths or not all(p.startswith('pose.bones[') for p in paths): continue
        bones={ast.literal_eval(p[len('pose.bones['):p.index('].')]) for p in paths}
        if any(bones.issubset(set(r.data.bones.keys())) for r in identified): character_actions.add(action)
    inventory=dict(path=relative,beforeSha256=before_hash,
        rigs={r.name:list(r.data.bones.keys()) for r in rigs},
        actions=[dict(name=a.name,owners=sorted(o.name for o in refs),
                      channels=sorted(set(action_paths(a))),remove=a in character_actions)
                 for a,refs in owners.items()])
    if not apply:
        if owners:
            plan.append(inventory); PLAN.parent.mkdir(parents=True,exist_ok=True)
            PLAN.write_text(json.dumps(plan,indent=2)+'\n')
        continue
    expected=approved[relative]
    if before_hash!=expected['beforeSha256'] or inventory!=expected:
        raise RuntimeError('Authoring action ownership changed since inventory: '+relative)
    if not character_actions: continue
    # Blender otherwise purges unused source images on save. Keep those original
    # authoring datablocks too; animation removal must not prune model sources.
    for collection in (bpy.data.objects,bpy.data.meshes,bpy.data.armatures,bpy.data.materials,bpy.data.images,bpy.data.node_groups):
        for block in collection:
            if block.users==0: block.use_fake_user=True
    before=signature(); removed=sorted(a.name for a in character_actions)
    for obj in bpy.data.objects:
        data=obj.animation_data
        if not data: continue
        if data.action in character_actions: data.action=None
        for track in list(data.nla_tracks):
            for strip in list(track.strips):
                if strip.action in character_actions: track.strips.remove(strip)
            if not track.strips: data.nla_tracks.remove(track)
    for action in character_actions: bpy.data.actions.remove(action,do_unlink=True)
    if signature()!=before: raise RuntimeError('Model changed during strip: '+relative)
    bpy.context.preferences.filepaths.save_version=0
    # Blender can read long Windows paths but its save/rename helper still uses
    # MAX_PATH. Serialize at a short workspace path, retaining all relative
    # resource strings, then atomically replace the original through pathlib.
    temporary=OUT.parent/'strip-candidates'/(digest(relative.encode())[:16]+'.blend')
    temporary.parent.mkdir(parents=True,exist_ok=True)
    temporary.relative_to(ROOT)
    if not native_path(temporary).exists():
        bpy.ops.wm.save_as_mainfile(filepath=str(native_path(temporary)),check_existing=False,relative_remap=False)
    # Reload both sides under the same image-loading conditions. Blender lazily
    # initializes source texture sizes while serializing, so comparing a loaded
    # candidate to the pre-save in-memory cache can produce a false mismatch.
    bpy.ops.wm.open_mainfile(filepath=str(native_path(path)),load_ui=False,use_scripts=False)
    before=signature()
    before_details=signature(True)
    expected_actions=sorted(a.name for a in bpy.data.actions if a.name not in removed)
    bpy.ops.wm.open_mainfile(filepath=str(native_path(temporary)),load_ui=False,use_scripts=False)
    if signature()!=before:
        after_details=signature(True)
        first=next((k for k,v in before_details.items() if after_details.get(k)!=v),None)
        raise RuntimeError('Model changed after serialization: '+relative+' first='+str(first))
    if sorted(a.name for a in bpy.data.actions)!=expected_actions:
        raise RuntimeError('Unexpected remaining actions in candidate: '+relative)
    native_path(temporary).replace(native_path(path))
    rows.append(dict(path=relative,beforeSha256=before_hash,afterSha256=digest(native_path(path).read_bytes()),
                     preservationSha256=before,removedActions=removed,remainingActions=sorted(a.name for a in bpy.data.actions)))
    OUT.parent.mkdir(parents=True,exist_ok=True); OUT.write_text(json.dumps(rows,indent=2)+'\n')
    print('WAR_STRIPPED_BLEND='+relative,flush=True)
print('WAR_BLEND_STRIP_COMPLETE='+str(len(rows)) if apply else 'WAR_BLEND_INVENTORY_COMPLETE='+str(len(plan)),flush=True)

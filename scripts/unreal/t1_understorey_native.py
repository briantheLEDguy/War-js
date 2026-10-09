"""Native private installed-plant batches with exact saved geometry/material inventory and cosmetic policy."""
import json,math
from pathlib import Path
import unreal
from t1_materials import same_state
from t1_nature_kit import select_nature_meshes
from t1_understorey import PLANTS,understorey_layout

TAG='WarT1PrivateInstalledNatureDetail'


def installed_detail_inventory(mesh):
    root=Path(__file__).resolve().parents[2]
    receipt=json.loads((root/'artifacts/unreal/licensed-kits/nature-kit-staged.json').read_text())
    rows=select_nature_meshes(dict(kit='/Game/Medieval_Environment/Real_Landscape',meshes=receipt['meshes']))
    row=next((r for r in rows if r['path']==mesh.get_path_name() and r['path'].rsplit('.',1)[-1] in PLANTS),None)
    if row is None:raise RuntimeError('Installed detail must use an exact selected private plant')
    editor=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.new_object(unreal.StaticMeshEditorSubsystem)
    bounds=mesh.get_bounds();actual=[[bounds.origin.x,bounds.origin.y,bounds.origin.z],[bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z]]
    vertices=[editor.get_number_verts(mesh,i) for i in range(mesh.get_num_lods())];screens=list(editor.get_lod_screen_sizes(mesh))
    materials=[slot.material_interface.get_path_name() if slot.material_interface else None for slot in mesh.get_editor_property('static_materials')]
    if mesh.get_num_lods()!=row['lodCount'] or vertices!=row['lodVertices'] or not same_state(actual,[row['boundsOrigin'],row['boundsExtent']]) or not same_state(screens,row['lodScreenSizes']) or materials!=row['materials']:
        raise RuntimeError('Installed plant geometry, bounds, LODs or materials differ from inspection')
    return dict(sourceKind='privateInstalledNature',nativeVertexCounts=vertices,screenSizes=screens,materials=materials,sourceSha256=row['sourceSha256'],sourcePackagesPreserved=True,licenseReviewed=False,distributionApproved=False,performanceAccepted=False,visualApproved=False)


def spawn_understorey(actors,identity,source,height_cm,pockets,meadow,states,sources):
    if identity!='sunmeadow_march':return dict(instances={},localCosmetic=True,appearanceApproved=False)
    # Canopies have their own stable study tag; cosmetic plants use a separate batch tag.
    canopies=[s for s in states.values() if 'WarT1PrivateInstalledNatureStudy' in s.get('tags',[])]
    layout=understorey_layout(source,height_cm,pockets,meadow,canopies);counts={}
    for name,rows in layout.items():
        if not rows:continue
        mesh=unreal.load_asset(sources[name]['path'])
        if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('Missing exact installed plant binding')
        installed_detail_inventory(mesh);bounds=mesh.get_bounds();transforms=[]
        for row in rows:
            p=row['location'];scale=row['scale'];root=p[2]-(bounds.origin.z-bounds.box_extent.z)*scale-1
            transforms.append(unreal.Transform(location=unreal.Vector(p[0],p[1],root),rotation=unreal.Rotator(yaw=row['yaw']),scale=unreal.Vector(scale,scale,scale)))
        actor=actors.spawn_actor_from_class(unreal.WarLandscapeDetail,unreal.Vector());actor.set_actor_label(identity+'_understorey_'+name);actor.tags=[TAG]
        if not actor.configure(mesh,transforms):raise RuntimeError('Native understorey rejects bounded instance layout')
        if actor.details.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION:raise RuntimeError('Understorey must remain nonblocking')
        counts[name]=len(rows)
    return dict(instances=counts,localCosmetic=True,collision='NoCollision',licenseReviewed=False,distributionApproved=False,appearanceApproved=False,performanceAccepted=False)

"""Private exact-source focal plants; cosmetic instances never supply collision or gameplay cover."""
import unreal
from t1_focal_planting import focal_layout
from t1_understorey_native import TAG,installed_detail_inventory


def spawn_focal_plants(actors,identity,source,height_cm,pockets,sources):
    if identity!='sunmeadow_march':return dict(instances={},localCosmetic=True,appearanceApproved=False)
    existing=[]
    for actor in actors.get_all_level_actors():
        if not isinstance(actor,unreal.WarLandscapeDetail):continue
        for index in range(actor.details.get_instance_count()):
            transform=actor.details.get_instance_transform(index,world_space=True)
            if transform is None:raise RuntimeError('Missing existing cover transform')
            p=transform.translation;existing.append(dict(location=[p.x,p.y,p.z]))
    layout=focal_layout(source,height_cm,pockets,existing);counts={}
    for name,rows in layout.items():
        if not rows:continue
        mesh=unreal.load_asset(sources[name]['path'])
        if not isinstance(mesh,unreal.StaticMesh):raise RuntimeError('Missing exact focal plant')
        installed_detail_inventory(mesh);bounds=mesh.get_bounds();transforms=[]
        for row in rows:
            p=row['location'];scale=row['scale'];root=p[2]-(bounds.origin.z-bounds.box_extent.z)*scale-1
            transforms.append(unreal.Transform(location=unreal.Vector(p[0],p[1],root),rotation=unreal.Rotator(yaw=row['yaw']),scale=unreal.Vector(scale,scale,scale)))
        actor=actors.spawn_actor_from_class(unreal.WarLandscapeDetail,unreal.Vector());actor.set_actor_label(identity+'_focal_'+name);actor.tags=[TAG]
        if not actor.configure(mesh,transforms) or actor.details.get_collision_enabled()!=unreal.CollisionEnabled.NO_COLLISION:
            raise RuntimeError('Focal planting violates bounded cosmetic policy')
        counts[name]=len(rows)
    return dict(instances=counts,existingInstances=len(existing),minimumSpacingMetres=.6,collision='NoCollision',localCosmetic=True,licenseReviewed=False,distributionApproved=False,appearanceApproved=False,performanceAccepted=False)

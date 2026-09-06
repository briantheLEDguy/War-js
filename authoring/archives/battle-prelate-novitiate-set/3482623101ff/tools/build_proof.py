"""Blender importer and fixed-camera reviewer for literal authored mesh records.

Run with Blender --background --factory-startup --python tools/build_proof.py.
This module contains no character-shape construction operations. Camera/lights
are review infrastructure; all visible geometry comes from source/*.json.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from validate_source import validate_component

COLLECTION="REFERENCE_BUILT_PRELATE"
PALETTE={
    "skin":((.283149,.158961,.090842,1),0,.68),"skin_ear":((.283149,.158961,.090842,1),0,.68),"lip":((.29,.125,.091,1),0,.56),
    "eye_white":((.49,.455,.387,1),0,.29),"iris":((.10,.086,.062,1),0,.31),
    "pupil":((.008,.006,.004,1),0,.25),"brow":((.054,.036,.024,1),0,.78),
    "steel":((.19,.215,.235,1),.88,.36),"brass":((.43,.269,.104,1),.80,.33),
    "dark_steel":((.042,.047,.053,1),.70,.49),"chainmail":((.042,.047,.053,1),.82,.47),"leather":((.055,.028,.014,1),0,.67),
    "crimson":((.125,.019,.025,1),0,.84),"parchment":((.60,.48,.30,1),0,.86)
}


def material(name):
    existing=bpy.data.materials.get("proof."+name)
    if existing:
        return existing
    mat=bpy.data.materials.new("proof."+name)
    mat.use_nodes=True
    color,metal,rough=PALETTE[name]
    shader=mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value=color
    shader.inputs["Metallic"].default_value=metal
    shader.inputs["Roughness"].default_value=rough
    if name in {"skin","skin_ear"}:
        shader.inputs["Subsurface Weight"].default_value=.065
        shader.inputs["Subsurface Radius"].default_value=(.7,.3,.15)
    paint_folder=ROOT/"textures/source"
    uv_node=None
    for channel,socket in (("basecolor","Base Color"),("roughness","Roughness"),("metallic","Metallic")):
        path=paint_folder/f"{name}_{channel}.png"
        if path.exists():
            uv_node=uv_node or mat.node_tree.nodes.new("ShaderNodeUVMap")
            uv_node.uv_map="authored_uv"
            texture=mat.node_tree.nodes.new("ShaderNodeTexImage")
            texture.name=f"Authored {channel} paint"
            texture.image=bpy.data.images.load(str(path),check_existing=True)
            texture.image.colorspace_settings.name="sRGB" if channel=="basecolor" else "Non-Color"
            mat.node_tree.links.new(uv_node.outputs["UV"],texture.inputs["Vector"])
            mat.node_tree.links.new(texture.outputs["Color"],shader.inputs[socket])
    normal_path=paint_folder/f"{name}_normal.png"
    if normal_path.exists():
        uv_node=uv_node or mat.node_tree.nodes.new("ShaderNodeUVMap")
        uv_node.uv_map="authored_uv"
        texture=mat.node_tree.nodes.new("ShaderNodeTexImage")
        texture.image=bpy.data.images.load(str(normal_path),check_existing=True)
        texture.image.colorspace_settings.name="Non-Color"
        normal=mat.node_tree.nodes.new("ShaderNodeNormalMap")
        normal.uv_map="authored_uv"
        mat.node_tree.links.new(uv_node.outputs["UV"],texture.inputs["Vector"])
        mat.node_tree.links.new(texture.outputs["Color"],normal.inputs["Color"])
        mat.node_tree.links.new(normal.outputs["Normal"],shader.inputs["Normal"])
    occlusion_path=paint_folder/f"{name}_occlusion.png"
    if occlusion_path.exists():
        uv_node=uv_node or mat.node_tree.nodes.new("ShaderNodeUVMap")
        uv_node.uv_map="authored_uv"
        texture=mat.node_tree.nodes.new("ShaderNodeTexImage")
        texture.name="Authored source occlusion"
        texture.label="Source AO for atlas packing; excluded from base color"
        texture.image=bpy.data.images.load(str(occlusion_path),check_existing=True)
        texture.image.colorspace_settings.name="Non-Color"
        mat.node_tree.links.new(uv_node.outputs["UV"],texture.inputs["Vector"])
    height_path=paint_folder/f"{name}_height.png"
    if height_path.exists():
        uv_node=uv_node or mat.node_tree.nodes.new("ShaderNodeUVMap")
        uv_node.uv_map="authored_uv"
        texture=mat.node_tree.nodes.new("ShaderNodeTexImage")
        texture.image=bpy.data.images.load(str(height_path),check_existing=True)
        texture.image.colorspace_settings.name="Non-Color"
        bump=mat.node_tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value=.22
        bump.inputs["Distance"].default_value=.00065
        if name=="crimson":
            bump.inputs["Strength"].default_value=.35
            bump.inputs["Distance"].default_value=.0012
        if name=="skin":
            bump.inputs["Strength"].default_value=.45
            bump.inputs["Distance"].default_value=.0012
        if shader.inputs["Normal"].is_linked:
            mat.node_tree.links.new(shader.inputs["Normal"].links[0].from_socket,bump.inputs["Normal"])
        mat.node_tree.links.new(uv_node.outputs["UV"],texture.inputs["Vector"])
        mat.node_tree.links.new(texture.outputs["Color"],bump.inputs["Height"])
        mat.node_tree.links.new(bump.outputs["Normal"],shader.inputs["Normal"])
    mat.diffuse_color=color
    mat["status"]="authored image source maps; runtime atlas evidence is tracked separately" if uv_node else "constant-color source material; no authored image maps"
    return mat


def apply_transform(obj, transform):
    if "matrix" in transform:
        obj.matrix_local=Matrix(transform["matrix"]) @ Matrix.Diagonal(Vector([*transform.get("scale",[1,1,1]),1]))
        return
    obj.location=transform.get("location",[0,0,0])
    obj.rotation_euler=[math.radians(v) for v in transform.get("rotation_degrees",[0,0,0])]
    obj.scale=transform.get("scale",[1,1,1])


def load_sources(root=ROOT, snapshots=None, scene_data=None):
    """Replace only our owned collection; unrelated objects cannot be removed."""
    old=bpy.data.collections.get(COLLECTION)
    if old:
        for obj in list(old.all_objects):
            if obj.get("authored_owner")!=COLLECTION:
                if obj.name not in bpy.context.scene.collection.objects:
                    bpy.context.scene.collection.objects.link(obj)
                continue
            mesh=obj.data if obj.type=="MESH" else None
            bpy.data.objects.remove(obj,do_unlink=True)
            if mesh and mesh.users==0:
                bpy.data.meshes.remove(mesh)
        bpy.data.collections.remove(old)
    collection=bpy.data.collections.new(COLLECTION)
    bpy.context.scene.collection.children.link(collection)
    if scene_data is None:
        scene_data=json.loads((root/"source/scene.json").read_text())
    if snapshots is None:
        snapshots={p.name:p.read_bytes() for p in sorted((root/"source").glob("*.json")) if p.name!="scene.json"}
    reports=[]
    for filename,source_bytes in snapshots.items():
        source=root/"source"/filename
        source_hash=hashlib.sha256(source_bytes).hexdigest()
        record=json.loads(source_bytes)
        reports.extend(validate_component(record))
        group=bpy.data.objects.new("component."+record["component"],None)
        collection.objects.link(group)
        apply_transform(group,scene_data["comparison_pose"].get(record["component"],{}))
        group["comparison_pose_only"]=True
        group["authored_owner"]=COLLECTION
        group["source_sha256"]=source_hash
        group["source_record"]=source_bytes.decode("utf-8")
        for part in record["parts"]:
            vertex_ids={v["id"]:i for i,v in enumerate(part["vertices"])}
            faces=[[vertex_ids[v] for v in f["vertices"]] for f in part["faces"]]
            mesh=bpy.data.meshes.new("authored."+part["id"])
            mesh.from_pydata([v["co"] for v in part["vertices"]],[],faces)
            mesh.update()
            bm=bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
            bm.to_mesh(mesh)
            bm.free()
            mats=list(dict.fromkeys(f["material"] for f in part["faces"]))
            for name in mats:
                mesh.materials.append(material(name))
            uv=mesh.uv_layers.new(name="authored_uv")
            # Match corners by vertex index after normal correction, not by order.
            for polygon,face in zip(mesh.polygons,part["faces"]):
                polygon.material_index=mats.index(face["material"])
                polygon.use_smooth=True
                corner_uv={vertex_ids[v]:co for v,co in zip(face["vertices"],face["uv"])}
                for loop in polygon.loop_indices:
                    uv.data[loop].uv=corner_uv[mesh.loops[loop].vertex_index]
            edge_lookup={tuple(sorted(e.vertices)):e for e in mesh.edges}
            for field,attr in (("seams","use_seam"),("sharp_edges","use_edge_sharp")):
                for a,b in part.get(field,[]):
                    setattr(edge_lookup[tuple(sorted((vertex_ids[a],vertex_ids[b])))],attr,True)
            if part.get("creases"):
                crease=mesh.attributes.new("crease_edge","FLOAT","EDGE")
                for data in part["creases"]:
                    index=edge_lookup[tuple(sorted(vertex_ids[v] for v in data["edge"]))].index
                    crease.data[index].value=data["value"]
            transforms=part.get("instances") or [part.get("transform",{})]
            for index,transform in enumerate(transforms):
                suffix=f".{index:02}" if len(transforms)>1 else ""
                obj=bpy.data.objects.new(part["id"]+suffix,mesh)
                collection.objects.link(obj)
                obj.parent=group
                obj["authored_owner"]=COLLECTION
                apply_transform(obj,transform)
                obj["source_file"]=str(source.relative_to(root))
                obj["source_part"]=part["id"]
                obj["source_sha256"]=source_hash
                obj["stable_vertex_ids"]=json.dumps(list(vertex_ids))
                obj["source_landmarks"]=json.dumps(part.get("landmarks",{}))
                obj["source_closed"]=part.get("closed",False)
                obj["slot"]=part.get("slot",record.get("slot",record["component"]))
                obj["rigid_bone"]=transform.get("rigid_bone",part.get("rigid_bone",""))
                obj["mirror_bone"]=part.get("mirror_bone","")
                for settings in part.get("modifiers",[]):
                    kind=settings["type"]
                    mod=obj.modifiers.new(kind.title(),kind)
                    if kind=="MIRROR":
                        mod.use_axis=[settings.get("axis","X")==axis for axis in "XYZ"]
                        mod.use_clip=True
                        mod.merge_threshold=.000001
                    elif kind=="SUBSURF":
                        mod.levels=mod.render_levels=settings["levels"]
                    elif kind=="SOLIDIFY":
                        mod.thickness=settings["thickness"]
                        mod.offset=settings.get("offset",0)
                        mod.use_even_offset=True
                    elif kind=="BEVEL":
                        mod.width=settings["width"]
                        mod.segments=settings.get("segments",2)
                        mod.limit_method="ANGLE"
                        mod.angle_limit=math.radians(38)
    return collection,reports


def setup_review(scene_data):
    scene=bpy.context.scene
    scene.unit_settings.system="METRIC"
    scene.unit_settings.scale_length=1
    scene.render.engine="CYCLES"
    scene.cycles.samples=40
    scene.cycles.use_denoising=True
    scene.render.film_transparent=False
    scene.render.image_settings.file_format="PNG"
    scene.world=bpy.data.worlds.new("proof studio")
    scene.world.use_nodes=True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.105,.112,.125,1)
    scene.world.node_tree.nodes["Background"].inputs[1].default_value=.45
    scene.view_settings.view_transform="AgX"
    for name,position,energy,size in [
        ("key",[-1.8,-2.2,3.2],220,2.2),
        ("fill",[2,-1.6,2.0],100,2.0),
        ("rim",[.2,1.4,2.8],260,1.6)
    ]:
        light=bpy.data.lights.new(name,"AREA")
        light.energy=energy
        light.shape="DISK"
        light.size=size
        obj=bpy.data.objects.new(name,light)
        scene.collection.objects.link(obj)
        obj.location=position
        obj.rotation_euler=(Vector([0,0,1.5])-obj.location).to_track_quat("-Z","Y").to_euler()
    for record in scene_data["cameras"]:
        cam=bpy.data.cameras.new("comparison."+record["id"])
        cam.type="ORTHO"
        cam.ortho_scale=record["orthographic_scale"]
        obj=bpy.data.objects.new(cam.name,cam)
        scene.collection.objects.link(obj)
        obj.location=record["position"]
        obj.rotation_euler=(Vector(record["target"])-obj.location).to_track_quat("-Z","Y").to_euler()
        obj["frozen_calibration_sha256"]=hashlib.sha256(json.dumps({"cameras":scene_data["cameras"],"comparison_pose":scene_data["comparison_pose"]},sort_keys=True).encode()).hexdigest()
    scene.camera=bpy.data.objects["comparison.front"]


def evaluated_record(collection):
    bpy.context.view_layer.update()
    depsgraph=bpy.context.evaluated_depsgraph_get()
    parts=[]
    for obj in collection.all_objects:
        if obj.type!="MESH":
            continue
        evaluated=obj.evaluated_get(depsgraph)
        mesh=evaluated.to_mesh()
        mesh.calc_loop_triangles()
        edges=Counter()
        for face in mesh.polygons:
            v=list(face.vertices)
            edges.update(tuple(sorted((a,b))) for a,b in zip(v,v[1:]+v[:1]))
        bad_triangles=sum(t.area<1e-12 for t in mesh.loop_triangles)
        nonmanifold=sum(n>2 for n in edges.values())
        boundary=sum(n==1 for n in edges.values())
        expected_closed=obj["source_closed"] or any(m.type=="SOLIDIFY" for m in obj.modifiers)
        if bad_triangles or nonmanifold or (expected_closed and boundary):
            raise ValueError(f"{obj.name}: evaluated geometry failed: {bad_triangles} degenerate triangles, {nonmanifold} nonmanifold edges, {boundary} boundary edges (closed expected={expected_closed})")
        uv=mesh.uv_layers.active
        parts.append({"name":obj.name,"source":obj["source_file"],"source_part":obj["source_part"],"source_sha256":obj["source_sha256"],
            "matrix_world":[list(row) for row in obj.matrix_world],
            "vertices":[list(v.co) for v in mesh.vertices],
            "faces":[{"vertices":list(f.vertices),"material":f.material_index,"uv":[list(uv.data[i].uv) for i in f.loop_indices]} for f in mesh.polygons],
            "materials":[m.name for m in mesh.materials],
            "triangles":len(mesh.loop_triangles),"boundary_edges":boundary,"expected_closed":expected_closed,
            "nonmanifold_edges":nonmanifold,"degenerate_triangles":bad_triangles})
        evaluated.to_mesh_clear()
    return {"schema_version":1,"status":"unapproved proof; evaluated mesh is inspectable, not a runtime asset","parts":parts}


def make_review_material(wire=False):
    mat=bpy.data.materials.new("proof.control_wire" if wire else "proof.neutral")
    mat.use_nodes=True
    shader=mat.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value=(.35,.35,.35,1)
    shader.inputs["Roughness"].default_value=.62
    if wire:
        node=mat.node_tree.nodes.new("ShaderNodeWireframe")
        node.use_pixel_size=True
        node.inputs["Size"].default_value=1.05
        mix=mat.node_tree.nodes.new("ShaderNodeMixRGB")
        mix.inputs[1].default_value=(.43,.48,.52,1)
        mix.inputs[2].default_value=(.012,.020,.025,1)
        mat.node_tree.links.new(node.outputs[0],mix.inputs[0])
        mat.node_tree.links.new(mix.outputs[0],shader.inputs["Base Color"])
    return mat


def render_views(scene_data, collection, views, modes, output_prefix=""):
    scene=bpy.context.scene
    neutral=make_review_material()
    wire=make_review_material(True)
    for mode in modes:
        scene.view_layers[0].material_override=neutral if mode=="neutral" else wire if mode=="wire" else None
        if mode=="wire":
            for obj in collection.all_objects:
                for modifier in obj.modifiers:
                    if modifier.type!="MIRROR":
                        modifier.show_render=False
        for record in scene_data["cameras"]:
            if record["id"] not in views:
                continue
            scene.camera=bpy.data.objects["comparison."+record["id"]]
            scene.render.resolution_x,scene.render.resolution_y=record["resolution"]
            scene.render.resolution_percentage=100
            scene.render.filepath=str(ROOT/"review"/f"{output_prefix}{record['id']}_{mode}.png")
            bpy.ops.render.render(write_still=True)
        if mode=="wire":
            for obj in collection.all_objects:
                for modifier in obj.modifiers:
                    modifier.show_render=True
    scene.view_layers[0].material_override=None
    scene.camera=bpy.data.objects["comparison.front"]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--views",default="front,three_quarter,side,face")
    parser.add_argument("--modes",default="neutral,material,wire")
    parser.add_argument("--no-render",action="store_true")
    args=parser.parse_args(sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else [])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene_bytes=(ROOT/"source/scene.json").read_bytes()
    scene_data=json.loads(scene_bytes)
    master_path=ROOT/"battle_prelate_novitiate_reference_master.blend"
    snapshots={p.name:p.read_bytes() for p in sorted((ROOT/"source").glob("*.json")) if p.name!="scene.json"}
    collection,source_report=load_sources(snapshots=snapshots,scene_data=scene_data)
    # A second import must replace our components, preserve unrelated scene data,
    # and keep object identities/names stable rather than accumulating duplicates.
    names=sorted(obj.name for obj in collection.all_objects)
    sentinel=bpy.data.objects.new("reload_sentinel",None)
    bpy.context.scene.collection.objects.link(sentinel)
    collection.objects.link(sentinel)
    collection,_=load_sources(snapshots=snapshots,scene_data=scene_data)
    assert names==sorted(obj.name for obj in collection.all_objects),"Reload duplicated or changed visible objects"
    assert bpy.data.objects.get("reload_sentinel")==sentinel,"Reload modified an unrelated object"
    bpy.data.objects.remove(sentinel,do_unlink=True)
    setup_review(scene_data)
    ROOT.joinpath("review").mkdir(exist_ok=True)
    evaluated=evaluated_record(collection)
    payload=json.dumps(evaluated,separators=(",",":"),allow_nan=False).encode()
    with gzip.GzipFile(filename=str(ROOT/"review/evaluated_mesh.json.gz"),mode="wb",mtime=0) as file:
        file.write(payload)
    build_id=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    source_hashes={obj["source_file"]:obj["source_sha256"] for obj in collection.all_objects if obj.type=="MESH"}
    authored_paint_materials=sorted({mat.name for obj in collection.all_objects if obj.type=="MESH" for mat in obj.data.materials if mat and mat.use_nodes and any(node.type=="TEX_IMAGE" and node.image for node in mat.node_tree.nodes)})
    report={"schema_version":1,"build_status":"complete","stage":scene_data.get("stage","upper_body_proof"),"revision":scene_data["revision"],"build_id":build_id,"source_hashes":source_hashes,"visual_status":"unreviewed","runtime_promotion":False,
        "source_validation":"passed","reload_validation":"passed","control_parts":source_report,
        "camera_sha256":hashlib.sha256(scene_bytes).hexdigest(),
        "calibration_sha256":hashlib.sha256(json.dumps({"cameras":scene_data["cameras"],"comparison_pose":scene_data["comparison_pose"]},sort_keys=True).encode()).hexdigest(),
        "evaluated_parts":[{k:v for k,v in p.items() if k not in ("vertices","faces","matrix_world")} | {"vertices":len(p["vertices"]),"faces":len(p["faces"])} for p in evaluated["parts"]],
        "total_triangles":sum(p["triangles"] for p in evaluated["parts"]),
        "authored_image_materials":authored_paint_materials,
        "limitations":[
            "Full-character editable authored source; likeness and surface quality require visual review" if scene_data.get("stage") in {"full_character","secondary_armor_set"} else "Upper-body editable source proof; the complete figure is outside this artifact",
            "This editable source master is unrigged; rigged runtime exports, animations and their validation are separate artifacts",
            "Source UVs are authored per-corner layouts; packed runtime atlases are produced and validated separately",
            "Source materials load authored image paint where supplied; image presence does not establish final material accuracy" if authored_paint_materials else "Source materials currently use constant colors; no authored image paint was loaded",
            "This report records source/build evidence only and does not grant visual acceptance or runtime promotion"]}
    # Save a useful camera view and all editable cages before rendering.
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type=="VIEW_3D":
                area.spaces.active.region_3d.view_perspective="CAMERA"
                area.spaces.active.shading.type="MATERIAL"
    bpy.ops.wm.save_as_mainfile(filepath=str(master_path),compress=True)
    if not args.no_render:
        render_views(scene_data,collection,args.views.split(","),args.modes.split(","))
    archive=ROOT/"review/revisions"/build_id
    archive.mkdir(parents=True,exist_ok=True)
    for obj in collection.all_objects:
        if obj.type=="EMPTY":
            (archive/(obj.name.removeprefix("component.")+".json")).write_bytes(obj["source_record"].encode("utf-8"))
    (archive/"scene.json").write_bytes(scene_bytes)
    evidence={}
    for path in [master_path,ROOT/"review/evaluated_mesh.json.gz"] + [ROOT/"review"/f"{view}_{mode}.png" for view in args.views.split(",") for mode in args.modes.split(",") if not args.no_render]:
        if path.exists():
            evidence[str(path.relative_to(ROOT))]={"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"bytes":path.stat().st_size}
            if path.suffix==".png":
                (archive/path.name).write_bytes(path.read_bytes())
    report["evidence"]=evidence
    for path in [ROOT/"review/build_report.json",archive/"build_report.json"]:
        temporary=path.with_suffix(".tmp")
        temporary.write_text(json.dumps(report,indent=2)+"\n")
        temporary.replace(path)
    print("PROOF_BUILD_COMPLETE "+json.dumps({"triangles":report["total_triangles"],"visual_status":"unreviewed"}))


if __name__=="__main__":
    main()

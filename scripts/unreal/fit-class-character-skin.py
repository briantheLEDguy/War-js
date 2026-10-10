"""Fit bounded, fixed skin weights against supplied poses; never publish motion.

The analytic linear-blend model must first match Blender's evaluated modifier.
Corrections retain the existing four influences, bones and rest geometry. A
fresh exported-mesh audit is still required before accepting the derived draft.
"""
from pathlib import Path
import bpy, sys, json, importlib.util, argparse, hashlib
import numpy as np
from mathutils import Quaternion, Vector
from mathutils.kdtree import KDTree

ROOT=Path(__file__).resolve().parents[2]; TOOLS=ROOT/'scripts/unreal'; sys.path.insert(0,str(TOOLS))
from class_character_skin import refine_source
from class_character_audit import build_audit
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,TOOLS/file); result=importlib.util.module_from_spec(spec); spec.loader.exec_module(result); return result
motion=module('motion','review-class-character-motion.py')
atlas=module('atlas','atlas-class-characters.py')
parser=argparse.ArgumentParser();parser.add_argument('--character',required=True)
parser.add_argument('--run',type=Path,required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
run=args.run.resolve();run.relative_to(ROOT/'artifacts/unreal/class-characters')
directory=(run/args.character).resolve();directory.relative_to(run)
if directory.parent != run:
    raise ValueError('Expected one character directory inside the run')
bpy.ops.wm.open_mainfile(filepath=str(directory/'character.blend'))
rig=next(obj for obj in bpy.data.objects if obj.type=='ARMATURE')
body=next(obj for obj in bpy.data.objects if obj.type=='MESH' and obj.name.startswith('Body_'))
candidate=refine_source(body,rig,96,192,.45)
source_edges=np.array([list(edge.vertices) for edge in body.data.edges])
names=candidate['names'];positions=candidate['positions']
tree=KDTree(len(positions))
for index,position in enumerate(positions): tree.insert(position,index)
tree.balance()
templates=motion.source_samples(directory.parent)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(directory/'body.glb'))
rig=next(obj for obj in bpy.data.objects if obj.type=='ARMATURE')
body=next(obj for obj in atlas.skinned_meshes(rig) if obj.name.startswith('Body_'))
neutral=np.array([list(body.matrix_world@vertex.co) for vertex in body.data.vertices])
height=np.ptp(neutral[:,2]); indices=[]
for point in neutral:
    _,index,distance=tree.find(point); assert distance<1e-5; indices.append(index)
edges=np.array([list(edge.vertices) for edge in body.data.edges]); a,b=edges[:,0],edges[:,1]
lengths=np.linalg.norm(neutral[a]-neutral[b],axis=1); valid=lengths>1e-5
homogeneous=np.column_stack((neutral,np.ones(len(neutral))))
world=rig.matrix_world.to_quaternion(); rest={bone.name:bone.matrix_local.to_quaternion() for bone in rig.data.bones}; ordered=list(rig.data.bones)
matrices=[]; labels=[]; baseline_error=None
def record(label):
    global baseline_error
    bpy.context.view_layer.update()
    matrices.append(np.array([rig.matrix_world@rig.pose.bones[name].matrix@rig.data.bones[name].matrix_local.inverted()@rig.matrix_world.inverted() for name in names]))
    labels.append(label)
    if baseline_error is None:
        weights=np.zeros((len(neutral),len(names)))
        for vertex in body.data.vertices:
            for group in vertex.groups:
                name=body.vertex_groups[group.group].name
                if name in names: weights[vertex.index,names.index(name)]=group.weight
        predicted=np.zeros_like(neutral)
        for index in range(len(names)):
            predicted += (homogeneous@matrices[-1][index].T)[:,:3]*weights[:,index:index+1]
        obj=body.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh=obj.to_mesh()
        actual=np.array([list(body.matrix_world@vertex.co) for vertex in mesh.vertices]);obj.to_mesh_clear()
        baseline_error=float(np.max(np.abs(actual-predicted))); assert baseline_error<1e-5,baseline_error
for key,template in templates.items():
    aligned={}
    for name,source_rest in template['rest'].items():
        target_rest=world@rest[name]
        aligned[name]=(source_rest@Vector((0,1,0))).rotation_difference(target_rest@Vector((0,1,0))).inverted()@target_rest
    for sample in template['samples']:
        orientations={}
        for bone in ordered:
            name=bone.name; parent_rest=rest[bone.parent.name] if bone.parent else Quaternion(); parent_pose=orientations[bone.parent.name] if bone.parent else Quaternion()
            desired=world.inverted()@(sample[name]@template['rest'][name].inverted()@aligned[name]) if name in sample else parent_pose@parent_rest.inverted()@rest[name]
            orientations[name]=desired; pose=rig.pose.bones[name];pose.rotation_mode='QUATERNION';pose.rotation_quaternion=rest[name].inverted()@parent_rest@parent_pose.inverted()@desired
        record(key)
build_audit(body,atlas.skinned_meshes(rig),rig,json.loads((directory/'request.json').read_text()),record)
indices=np.array(indices)
selected=np.argsort(candidate['weights'],axis=1)[:,-4:]
base=np.take_along_axis(candidate['weights'],selected,axis=1);base/=base.sum(axis=1)[:,None]
runtime_selected=selected[indices]
transforms=[np.einsum('vkij,vj->vki',matrix[runtime_selected],homogeneous)[:,:,:3].astype(np.float32) for matrix in matrices]
limit=height*.018;target=limit*.97
rows=np.arange(len(base))[:,None]
left,right=source_edges[:,0],source_edges[:,1]
lower=np.maximum(base-.2,0);upper=np.minimum(base+.2,1);upper[base<1e-8]=0
def project(values):
    lo=np.min(values-upper,axis=1);hi=np.max(values-lower,axis=1)
    for _ in range(32):
        middle=(lo+hi)*.5
        total=np.clip(values-middle[:,None],lower,upper).sum(axis=1)
        lo=np.where(total>1,middle,lo);hi=np.where(total>1,hi,middle)
    return np.clip(values-((lo+hi)*.5)[:,None],lower,upper)
def objective(values,gradient=False):
    loss=0;worst=0;grad=np.zeros_like(values)
    for transformed in transforms:
        posed=np.sum(transformed*values[indices,:,None],axis=1)
        delta=posed[a]-posed[b];current=np.linalg.norm(delta,axis=1)
        extension=current-lengths;worst=max(worst,float(np.max(extension))/limit)
        excess=np.maximum(extension-target,0)
        loss+=float(excess@excess)
        if gradient:
            bad=np.flatnonzero(excess>0)
            ia,ib=a[bad],b[bad];unit=delta[bad]/np.maximum(current[bad,None],1e-12)
            ga=np.einsum('bkj,bj->bk',transformed[ia]-posed[ia,None,:],unit)*excess[bad,None]*2
            gb=-np.einsum('bkj,bj->bk',transformed[ib]-posed[ib,None,:],unit)*excess[bad,None]*2
            np.add.at(grad,indices[ia],ga);np.add.at(grad,indices[ib],gb)
    displacement=values-base
    loss+=1e-6*float(np.sum(displacement**2));grad+=2e-6*displacement
    dense=np.zeros((len(base),len(names)));dense[rows,selected]=displacement
    difference=dense[left]-dense[right];loss+=1e-6*float(np.sum(difference**2))
    if gradient:
        smooth=np.zeros_like(dense)
        np.add.at(smooth,left,difference*2e-6);np.add.at(smooth,right,-difference*2e-6)
        grad+=smooth[rows,selected]
    return loss,worst,grad
values=base.copy();best=values.copy();best_score=100
for iteration in range(120):
    loss,score,gradient=objective(values,True)
    if score<best_score:best_score=score;best=values.copy()
    print('SKIN_SOLVE',iteration,loss,score,flush=True)
    if score<=.995:break
    accepted=False
    for rate in (50,25,10,5,1):
        proposed=project(values+np.clip(-gradient*rate,-.02,.02))
        next_loss,_,_=objective(proposed)
        if next_loss<loss:
            values=proposed;accepted=True;break
    if not accepted:break
values=best
changes=np.max(np.abs(values-base),axis=1)>1e-6
correction=dict(schemaVersion=1,identity=args.character,sourceBodySha256=atlas.sha(directory/'body.glb'),
    sourceVertexCount=len(positions),positionSha256=hashlib.sha256(json.dumps(positions.round(6).tolist(),separators=(',',':')).encode()).hexdigest(),
    baseline=dict(hipIterations=96,shoulderIterations=192,trunkAnchorWidth=.45),
    solver=dict(toolSha256=atlas.sha(__file__),motionToolSha256=atlas.sha(TOOLS/'review-class-character-motion.py'),baselineLbsErrorM=baseline_error,
                maxExtensionScore=best_score,maximumWeightChange=float(np.max(np.abs(values-base))),poseCount=len(matrices)),
    rows=[dict(vertex=int(index),weights={names[column]:float(weight) for column,weight in zip(selected[index],values[index]) if weight>1e-8}) for index in np.flatnonzero(changes)],
    runtimeEligible=False,nativeAccepted=False)
(directory/'skin-correction.json').write_text(json.dumps(correction,indent=2)+'\n')
print('SKIN_SOLVE_FINAL',best_score,len(correction['rows']),flush=True)
if best_score > 1:
    raise RuntimeError('Bounded skin fit still exceeds the deformation limit')

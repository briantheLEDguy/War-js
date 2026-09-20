"""Compare candidate elbow pole directions against actual worn surfaces."""
from pathlib import Path
prefix=Path(__file__).with_name('inspect_outfit_clearance.py').read_text().split('selected=next(')[0]
prefix=prefix.replace("source=WORK/'runtime'/f'{KEY}_lod{lod}.glb'","source=WORK/'review/contact-diagnostic-g.glb'")
exec(compile(prefix,str(Path(__file__).with_name('inspect_outfit_clearance.py')),'exec'))
from tailored_locomotion import _solve_chain
mapping=json.loads((WORK/'review/semantic-parts.json').read_text())
names={row['id']:name for name,row in mapping['parts'].items()}
attribute=body.data.attributes['_SCOUT_PART'];ids=[round(item.value) for item in attribute.data]
diagnostics=json.loads((WORK/'review'/f'{KEY}_lod{lod}_diagnostic_garment_clearance.json').read_text())
cases=[('death',seconds) for seconds in (.83333331,.91666666,.98333332,1.06666672)]
for clip,seconds in cases:
    action=next(a for a in bpy.data.actions if a.name==clip or a.name.endswith('_'+clip))
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update()
    basis={bone.name:bone.matrix_basis.copy() for bone in rig.pose.bones}
    targets={side:(rig.pose.bones['hand_'+side].head.copy(),rig.pose.bones['hand_'+side].matrix.to_quaternion()) for side in ('L','R')}
    for pole in [None,.03,.06,.09]:
        for name,matrix in basis.items():rig.pose.bones[name].matrix_basis=matrix
        bpy.context.view_layer.update()
        if pole is not None:
            for side,sign in [('L',1),('R',-1)]:
                target,rotation=targets[side];target=target.copy()
                target.x+=sign*pole
                if clip=='death':
                    t=max(0,min(1,(seconds*30-10)/30));t=t*t*(3-2*t)
                    hint=Vector((sign,0,-.85*t))
                elif clip in ('run','walk'):hint=Vector((sign*1.1,.65,-1.5))
                else:hint=Vector((sign*1.6,0,-.25))
                if clip!='death':
                    shoulder=rig.pose.bones['upper_arm_'+side].head
                    reach=(rig.pose.bones['upper_arm_'+side].length+rig.pose.bones['forearm_'+side].length)*.90
                    delta=target-shoulder
                    if delta.length>reach:target=shoulder+delta.normalized()*reach
                _solve_chain(rig,side,target,rotation,('upper_arm','forearm','hand'),hint)
        posed=points();anatomical=skin_reference(reference,fields,rig)
        subject,reference_surface,shells=sets['garment_clearance']
        result=measure(posed,subject,reference_surface,shells,probes['garment_clearance'],bounded_tree(anatomical,reference_faces,False))
        result['part']=names[ids[result['worstProbe']['vertex']]]
        tree=bounded_tree(posed,reference_surface)[0];target=bounded_tree(posed,subject)[0]
        pairs=target.overlap(tree)
        from collections import Counter
        counts=Counter((names[ids[subject[i][0]]],names[ids[reference_surface[j][0]]]) for i,j in pairs)
        result['pairs']=counts.most_common(4)
        if pairs:
            contacted=np.array([topology_rest[v] for i,j in pairs for v in subject[i]])
            result['restContactBounds']=[contacted.min(axis=0).tolist(),contacted.max(axis=0).tolist()]
        print(json.dumps({'clip':clip,'seconds':seconds,'pole':pole,**result}),flush=True)

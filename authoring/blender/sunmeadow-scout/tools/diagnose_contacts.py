"""Locate actual contact failures; diagnostic only, never a publication gate."""
from pathlib import Path
prefix=Path(__file__).with_name('inspect_outfit_clearance.py').read_text().split('selected=next(')[0]
prefix=prefix.replace("source=WORK/'runtime'/f'{KEY}_lod{lod}.glb'","source=WORK/'review/contact-diagnostic-c.glb'")
exec(compile(prefix,str(Path(__file__).with_name('inspect_outfit_clearance.py')),'exec'))
mapping=json.loads((WORK/'review/semantic-parts.json').read_text())
names={row['id']:name for name,row in mapping['parts'].items()}
attribute=body.data.attributes['_SCOUT_PART'];ids=[round(item.value) for item in attribute.data]
for clip,seconds,index in [('idle',.60000002,95864),('run',.450000005,96159),('death',.63333333,96456),('death',1.116666675,109634)]:
    action=next(a for a in bpy.data.actions if a.name==clip or a.name.endswith('_'+clip))
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    for bone in rig.pose.bones:bone.matrix_basis.identity()
    frame=1+seconds*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    bpy.context.scene.frame_set(math.floor(frame),subframe=frame%1);bpy.context.view_layer.update();posed=points()
    p=Vector(posed[index]);anatomical=skin_reference(reference,fields,rig)
    print('PROBE',clip,seconds,index,names[ids[index]],list(p),flush=True)
    for name,(subject,reference_surface,shells) in sets.items():
        refs=[('anatomy',bounded_tree(anatomical,reference_faces,False))]+[(str(i),bounded_tree(posed,shell)) for i,shell in enumerate(shells)]
        print('CORRECTED_SIGN',name,signed_clearance(p,[row[1] for row in refs])[0],flush=True)
        for label,(tree,low,high) in refs:
            nearest=tree.find_nearest(p)
            if all(low[i]<=p[i]<=high[i] for i in range(3)):
                direction=Vector((.381966,.723607,.575));direction.normalize();origin=p.copy();hits=[]
                for _ in range(96):
                    hit,normal,triangle,distance=tree.ray_cast(origin,direction)
                    if hit is None:break
                    hits.append((list(hit),distance,normal.dot(direction),triangle));origin=hit+direction*.000002
                print('PARITY',name,label,'nearest',nearest[3],'count',len(hits),'hits',hits,flush=True)
        if name=='tool_clearance' and ids[index] not in {ids[i] for i in probes[name]}:continue
        target=bounded_tree(posed,subject)[0];other=bounded_tree(posed,reference_surface)[0]
        from collections import Counter
        pairs=target.overlap(other);counts=Counter((names[ids[subject[i][0]]],names[ids[reference_surface[j][0]]]) for i,j in pairs)
        print('PAIRS',name,counts.most_common(8),flush=True)
        if pairs:
            contacted=np.array([posed[v] for i,j in pairs for v in subject[i]])
            print('CONTACT_BOUNDS',name,contacted.min(axis=0).tolist(),contacted.max(axis=0).tolist(),flush=True)

"""Export exact admitted source meshes for the first-pair private prototypes."""
import hashlib
import json
from pathlib import Path
from world_static import read_glb, combine_parts

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'artifacts/unreal/t1-redesign'

def main():
    registry=json.loads((ROOT/'public/assets/models/asset-index.json').read_text())['staticProps']
    plan=json.loads((DIRECTORY/'plan.json').read_text())
    models, placements, pending={},[],[]
    for zone in plan['nativeBatch']:
        prototype_file=DIRECTORY/(zone+'_prototype.json')
        if hashlib.sha256(prototype_file.read_bytes()).hexdigest()!=plan['prototypeHashes'][zone]:raise RuntimeError('Prototype recipe changed: '+zone)
        prototype=json.loads(prototype_file.read_text())
        for prop in prototype['prototypes']:
            key=prop.get('assetKey',prop.get('kind'))
            binding=registry.get(key)
            if not binding or binding.get('approvalState')!='approved' or binding.get('runtimeReady') is not True:
                pending.append({'zone':zone,'id':prop.get('id'),'reason':'no-admitted-source-binding'});continue
            model=binding['model']; source=ROOT/'public/assets/models'/model
            if hashlib.sha256(source.read_bytes()).hexdigest()!=binding['modelSha256']:raise RuntimeError('Source hash changed: '+model)
            if prop.get('model',model)!=model:raise RuntimeError('Source binding differs: '+str(prop.get('id')))
            if model not in models:
                try:data=read_glb(source)
                except (ValueError,KeyError) as error:
                    pending.append({'zone':zone,'id':prop.get('id'),'reason':str(error)});continue
                filename=Path(model).stem+'.json'
                content=json.dumps(combine_parts(data['parts']),separators=(',',':'))
                (DIRECTORY/filename).write_text(content)
                models[model]={'file':filename,'sha256':hashlib.sha256(content.encode()).hexdigest(),'sourceSha256':data['sourceSha256']}
            if prop.get('reservation'):
                vertices=json.loads((DIRECTORY/models[model]['file']).read_text())['positions']
                # Native XY is source ZX. Reservations include the source pivot's offset.
                envelope=prop['reservation']
                scale=prop.get('scale',1)
                if any(abs(p[0])*scale*prop.get('scaleZ',1)>envelope['depth']*50+.01
                       or abs(p[1])*scale*prop.get('scaleX',1)>envelope['width']*50+.01
                       or p[2]*scale*prop.get('scaleY',1)>envelope['height']*100+.01 for p in vertices):
                    raise RuntimeError('Source mesh exceeds its assembly reservation: '+prop['id'])
            placements.append({'zone':zone,'model':model,'source':prop})
    result={'planSha256':hashlib.sha256((DIRECTORY/'plan.json').read_bytes()).hexdigest(),'models':models,'placements':placements,'pending':pending,'nativeArtApproved':False}
    (DIRECTORY/'models.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'models':len(models),'placements':len(placements),'pending':len(pending)}))

if __name__=='__main__':main()

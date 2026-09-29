"""Portable capital revision ledger contracts; native package data stays private."""
import json
import copy
from dutch_bastion import ROOT, OUT, digest


def merge_manifest(base, proposed, current, path='manifest'):
    """Preserve concurrent, disjoint review edits; reject competing changes."""
    if proposed==base: return copy.deepcopy(current)
    if current==base or current==proposed: return copy.deepcopy(proposed)
    if all(isinstance(v,dict) for v in (base,proposed,current)):
        missing=object();result={}
        for key in sorted(base.keys()|proposed.keys()|current.keys()):
            a,b,c=(v.get(key,missing) for v in (base,proposed,current))
            if b==a: value=c
            elif c==a or b==c: value=b
            elif all(v is not missing for v in (a,b,c)):
                value=merge_manifest(a,b,c,path+'/'+key)
            else: raise ValueError('Conflicting campaign edits: '+path+'/'+key)
            if value is not missing: result[key]=copy.deepcopy(value)
        return result
    if all(isinstance(v,list) for v in (base,proposed,current)) and len(base)==len(proposed)==len(current):
        # Zone order and identities are stable in this migration manifest.
        if all(isinstance(v,dict) and 'id' in v for rows in (base,proposed,current) for v in rows):
            if not [v['id'] for v in base]==[v['id'] for v in proposed]==[v['id'] for v in current]:
                raise ValueError('Conflicting campaign identities: '+path)
            return [merge_manifest(a,b,c,path+'/'+a['id']) for a,b,c in zip(base,proposed,current)]
    raise ValueError('Conflicting campaign edits: '+path)


def validate_revision(data):
    if data['zone']!='aegis_capital': raise ValueError('Only Bastion belongs to this revision')
    ids=[row['actorId'] for row in data['buildings']]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate building identity')
    blocks={row['id'] for row in data['blocks']}
    if len(blocks)!=len(data['blocks']): raise ValueError('Duplicate block identity')
    if any(row['block'] not in blocks for row in data['buildings']): raise ValueError('Unknown block')
    for district in ('gateward','cinderbank','lantern_quays','bellfound','crownwatch'):
        venues=[r['publicInterior'] for r in data['buildings'] if r['district']==district and r['publicInterior']]
        if sorted(v['kind'] for v in venues)!=['cafe','inn','shop']: raise ValueError('Missing public venue mix: '+district)
        if any(v['service']!='atmosphere_only' for v in venues): raise ValueError('Architecture cannot invent services')
    if data['acceptance']['release']: raise ValueError('Architecture never grants migration release acceptance')
    if data['acceptance']['active'] and not all(data['acceptance'].get(k) for k in ('native','visual','traversal','performance')):
        raise ValueError('Active city requires complete architecture acceptance')
    if data['signature']!=digest({k:v for k,v in data.items() if k!='signature'}): raise ValueError('Edited revision ledger')


def export_revision():
    current=json.loads((OUT/'city-current.json').read_text());run=OUT/current['revision']
    plan=json.loads((OUT/'city-plan.json').read_text());architecture=json.loads((OUT/'city-architecture.json').read_text())
    city=json.loads((run/'city.json').read_text());assets=json.loads((run/'assets.json').read_text())
    bindings={a['id']:a for a in assets['houses']}
    if architecture['planSignature']!=digest(plan): raise RuntimeError('Stale city source')
    campaign=json.loads((run/'campaign.json').read_text()) if (run/'campaign.json').exists() else {}
    review=json.loads((run/'review.json').read_text()) if (run/'review.json').exists() else {}
    buildings=[]
    for row in architecture['houses']:
        binding=bindings[row['id']]
        buildings.append({**{k:row[k] for k in ('id','actorId','block','district','publicInterior','position','entrance','direction','sourceSignature','meshSha256')},
                          'nativeMesh':binding['mesh'],'nativeSha256':binding['sha256']})
    data=dict(schemaVersion=1,zone='aegis_capital',revision=current['revision'],
              sourceSha256=plan['sourceSha256'],layoutSignature=plan['layoutSignature'],planSignature=digest(plan),
              geometrySignature=assets['geometrySignature'],map=campaign.get('map',city['map']),
              visualSignature=digest(city.get('visualHashes',{})),
              layers={**city['layers'],'architecture':city['geometryLayer']},
              blocks=[{k:b[k] for k in ('id','district','boundary','court','openings') if k in b} for b in plan['blocks']],
              streets=plan['streets'],intentionalSpaces=plan['intentionalSpaces'],gatheringAreas=plan['gatheringAreas'],
              protectedSites=plan['protectedSites'],buildings=buildings,coverage=city['coverage'],
              preservation=dict(sourceHashes=city['sourceHashes'],removedOwnedHouses=sum(c['action']=='remove_owned_house' for c in city['changes']),
                                replacedOwnedStreetActors=[dict(layer=c['layer'],name=c['name'],label=c['before']['label'])
                                                          for c in city['changes'] if c['action']=='remove_owned_street'],
                                relocations=[dict(layer=c['layer'],name=c['name'],before=c['before']['transform'],after=c['after']['transform'])
                                             for c in city['changes'] if 'after' in c]),
              acceptance=dict(native=True,visual=review.get('visual',False),traversal=review.get('traversal',False),
                              performance=review.get('performance',False),
                              active=campaign.get('activated',False),release=False),
              unfinished=review.get('unfinished',['Native visual and traversal review pending']),
              distribution='Native packages and purchased inputs remain private; no rights approval implied')
    data['signature']=digest(data);validate_revision(data)
    target=ROOT/'migration/dutch-bastion-city.json'
    target.write_text(json.dumps(data,indent=2)+'\n')
    native=ROOT/'unreal/AegisWar/Content/Migration/dutch-bastion-city.json'
    native.write_text(json.dumps(data,separators=(',',':'))+'\n')
    print('Exported Bastion revision '+current['revision'])


if __name__=='__main__': export_revision()

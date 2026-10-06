"""Read-only binding of the narrow, actual three-process normal-character proof."""
import copy
import hashlib
import json
import math
from pathlib import Path
import re
from citadel_recovery_runtime import checked_cast, checked_runtime, runtime_evolution

FLAGS=('productionAdmission','steamAdmission','humanPlaytest','visualApproval','fullSiegeAdmission',
       'releaseAcceptance','victoryAcceptance','conquestAcceptance')


def canonical(value):
    # Match the launcher's JSON.stringify number/string policy for character digests.
    if isinstance(value,list):return '['+','.join(canonical(v) for v in value)+']'
    if isinstance(value,dict):return '{'+','.join(canonical(k)+':'+canonical(value[k]) for k in sorted(value,key=lambda k:k.encode('utf-16-be')))+'}'
    if type(value) in (int,float):
        if not math.isfinite(value):raise ValueError('Nonfinite character number.')
        if value==0:return '0'
        number=repr(float(value)) if type(value) is float or abs(value)>2**53 else str(value)
        if 'e' in number.lower():
            mantissa,exponent=number.lower().split('e');power=int(exponent)
            if 1e-6<=abs(value)<1e21:
                from decimal import Decimal
                fixed=format(Decimal(number),'f')
                return fixed.rstrip('0').rstrip('.') if '.' in fixed else fixed
            return mantissa.rstrip('0').rstrip('.')+'e'+('+' if power>=0 else '-')+str(abs(power))
        return number.rstrip('0').rstrip('.') if '.' in number else number
    return json.dumps(value,ensure_ascii=False,separators=(',',':'))


def finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def integer(value,minimum=0):
    return type(value) is int and value>=minimum


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def receipts(values):
    if not isinstance(values,list) or any(not isinstance(v,str) for v in values):
        raise ValueError('Missing complete runtime receipts.')
    rows=sorted(v.replace('-','').lower() for v in values)
    if len(set(rows))!=len(rows):raise ValueError('Duplicate character transaction receipts.')
    return rows


def character(value):
    doc=value.get('document',{});runtime=doc.get('runtime',{})
    if (not re.fullmatch('[a-zA-Z0-9_-]{1,80}',str(value.get('id',''))) or value['id'] in ('__proto__','constructor','prototype')
            or value.get('realm') not in ('aegis','riftbound') or not isinstance(value.get('name'),str) or not value['name'].strip()
            or len(value['name'])>64 or not str(value.get('visual','')).startswith('/Game/')
            or not str(value.get('returnMap','')).startswith('/Game/') or not isinstance(value.get('returnPosition'),list)
            or len(value['returnPosition'])!=3 or not all(finite(v) for v in value['returnPosition'])
            or not isinstance(doc.get('inventory'),dict) or not isinstance(runtime,dict) or not isinstance(doc.get('zone'),str)
            or not finite(runtime.get('health')) or runtime['health']<0 or not finite(runtime.get('mana')) or runtime['mana']<0
            or type(runtime.get('dead')) is not bool or len(canonical(value))>262144):
        raise ValueError('Invalid complete native character document.')
    return value


def durable(value):
    """Preserve all persistent fields while normal attributes and clocks may tick."""
    result=copy.deepcopy(character(value));result.pop('returnPosition')
    runtime=result['document']['runtime']
    for key in ('health','mana','abilities','capturedAtUnixMs','combat'):runtime.pop(key,None)
    runtime['rewards']=receipts(runtime.get('rewards'));runtime['questKills']=receipts(runtime.get('questKills'))
    return result


def witness(row,value,returned):
    point=row.get('position');center=row.get('validatedCenter')
    if (row.get('characterId')!=value['id'] or row.get('zone')!=value['document']['zone']
            or row.get('normalized') is not False or row.get('pending') is not False or row.get('movementHeld') is not False or row.get('member') is not (not returned)
            or any(row.get(k) is not True for k in ('alive','modelReady','sceneReady','physicalReady','zoneMatches'))
            or row.get('combatLevel')!=40 or row.get('capsuleRadiusCm')!=42 or row.get('capsuleHalfHeightCm')!=96
            or row.get('safeReturn') is not returned or not isinstance(point,list) or not isinstance(center,list)
            or len(point)!=3 or len(center)!=3 or not all(finite(v) for v in point+center)
            or math.dist(point[:2],center[:2])>1 or abs(point[2]-center[2])>5
            or point!=value['returnPosition'] or value['document']['runtime'].get('dead') is not False):
        raise ValueError('Recovery requires actual normal character, model, floor and protected return witnesses.')


def ack(row,identity,revision=None,sequence=None):
    value=row.get('ack',{})
    return (row.get('forwarded') is True and row.get('responseStatus')==200 and value.get('version')==1
        and value.get('characterId')==identity and integer(value.get('revision'),1)
        and type(value.get('recoveryPending')) is bool and (revision is None or value['revision']==revision)
        and (sequence is None or value.get('walSequence')==sequence))


def snapshot(value):
    stage=value.get('stage');main=value.get('completed');optional=value.get('optionalCompleted');phase=value.get('phase')
    valid=lambda rows,count:isinstance(rows,list) and len(set(rows))==len(rows) and all(integer(v) and v<count for v in rows)
    if (stage not in (0,1,2) or type(stage) is not int or phase not in ('preparing','active','transition')
            or not valid(main,8) or not valid(optional,3) or 7 in main or 'attackersWon' in value
            or not finite(value.get('elapsed')) or not 0<=value['elapsed']<=3001
            or any(not finite(value.get(k)) or not 0<=value[k]<=limit for k,limit in
                (('remaining',840),('transitionRemaining',60),('overtimeRemaining',120)))
            or any(i>stage for i in optional) or stage==0 and any(i>3 for i in main)
            or stage>0 and not set(range(4)).issubset(main) or stage>1 and not {4,5,6}.issubset(main)
            or any(i>0 and i<=3 and i-1 not in main or i in (4,5) and 3 not in main or i==6 and not {4,5}.issubset(main) for i in main)
            or phase=='preparing' and (stage!=0 or main or optional or value['elapsed']!=0)
            or phase=='transition' and (stage==2 or (3 if stage==0 else 6) not in main)):
        raise ValueError('Narrow recovery requires a valid unfinished version-two siege state.')
    return value


def recovery_proof(bundle,expected):
    r=bundle['report'];native=bundle['nativeReport'];configs=bundle['configs'];journals=bundle['checkpoints']
    mutations=bundle['mutations'];recovered=bundle['recovered'];wals=bundle['wals'];http=bundle['http'];processes=bundle['processes']
    players=['proof-'+expected['signature'][:12]+'-'+realm+'-'+str(i) for realm in ('aegis','riftbound') for i in range(18)]
    if (r.get('schemaVersion')!=1 or r.get('passed') is not True or r.get('recoveryOnly') is not True or r.get('proofOnly') is not True
            or r.get('contentReviewOverride') is not True or not re.fullmatch('[a-z0-9][a-z0-9_-]{0,63}',str(r.get('fixtureId','')))
            or r.get('hostId')!='citadel-proof-'+r['fixtureId'] or r.get('players')!=players
            or not re.fullmatch('/Game/WorldRebuild/AegisCitadel_[a-f0-9]{12}/CampaignCandidate',expected['map']) or any(r.get(k)!=v for k,v in expected.items())
            or r.get('normalCharacterRecoveryVerified') is not True
            or any(r.get(k) is not False for k in ('outcomeRecoveryVerified','equipmentMutationVerified','deadIntentVerified')+FLAGS)
            or len(configs)!=3 or len(journals)!=3 or len(mutations)!=2 or len(recovered)!=2 or len(wals)!=2
            or len(r.get('cases',[]))!=2 or len(r.get('http',[]))!=3
            or http.get('schemaVersion')!=1 or http.get('fixtureId')!=r['fixtureId'] or http.get('hostId')!=r['hostId']
            or http.get('attempts')!=r['http'] or processes.get('schemaVersion')!=1
            or processes.get('fixtureId')!=r['fixtureId'] or processes.get('hostId')!=r['hostId'] or len(processes.get('attempts',[]))!=3):
        raise ValueError('Fresh three-process character recovery is incomplete, stale or claims broader acceptance.')
    target=players[0];activation=None;pids=set();previous_end=0
    for attempt in range(3):
        config=configs[attempt];setup=config.get('recovery',{});process=processes['attempts'][attempt]
        if (any(config.get(k)!=v for k,v in expected.items()) or config.get('proofOnly') is not True
                or config.get('contentReviewOverride') is not True or config.get('recoveryOnly') is not True or config.get('players')!=players
                or setup.get('version')!=1 or setup.get('attempt')!=attempt or setup.get('fixtureId')!=r['fixtureId']
                or any(setup.get(k)!=r.get(k) for k in ('binaryPath','binarySha256','sourceHashes'))
                or setup.get('receiptA')!=sha(r['fixtureId']+':reward-a')[:32] or setup.get('receiptB')!=sha(r['fixtureId']+':reward-b')[:32]
                or len(setup.get('expected',[]))!=attempt or process.get('attempt')!=attempt or not integer(process.get('pid'),1)
                or process['pid'] in pids or not finite(process.get('startedAt')) or not finite(process.get('endedAt'))
                or process['startedAt']<previous_end or process['endedAt']<=process['startedAt']
                or process.get('configSha256')!=r['evidence']['configs'][attempt]['sha256']):
            raise ValueError('Recovery attempts do not bind three distinct owned native processes and exact configs.')
        if (attempt<2 and (process.get('termination')!='SIGKILL' or process.get('killRequested') is not True
                or process.get('requestId')!=r['cases'][attempt]['requestId']
                or not (process.get('signalCode')=='SIGKILL' or integer(process.get('exitCode'),1)))
                or attempt==2 and (process.get('termination')!='normal_exit' or process.get('killRequested') is not False
                or process.get('exitCode')!=0 or process.get('signalCode') is not None)):
            raise ValueError('Actual owned process termination witnesses are missing.')
        pids.add(process['pid']);previous_end=process['endedAt']
        for index,binding in enumerate(setup['expected']):
            if (binding.get('sha256')!=r['evidence']['mutations'][index]['sha256']
                    or not str(binding.get('path','')).replace('\\','/').endswith('/Saved/CitadelSiegeProof/'+r['fixtureId']+'/attempt-'+str(index)+'/mutation.json')):
                raise ValueError('Native resume config does not bind original mutation witnesses.')
        rows=r['http'][attempt]
        if not rows or any(row.get('index')!=index or row.get('hostId')!=r['hostId']
                or not re.fullmatch('[a-z]+',str(row.get('route',''))) or not re.fullmatch('[a-f0-9]{64}',str(row.get('bodySha256','')))
                or type(row.get('forwarded')) is not bool or 'characterSha256' in row and not re.fullmatch('[a-f0-9]{64}',str(row['characterSha256']))
                for index,row in enumerate(rows)):raise ValueError('Actual private HTTP sequence is malformed.')
        if any(not any(row['route']=='membership' and row.get('action')=='join' and row.get('characterId')==identity
                and row.get('forwarded') is True and row.get('responseStatus')==200 and re.fullmatch('[a-f0-9]{64}',str(row.get('characterSha256','')))
                for row in rows) for identity in players):
            raise ValueError('Every attempt requires all thirty-six actual approved character baselines.')
        checkpoint=journals[attempt];state=checkpoint.get('state',{});journal=state.get('nativeSiegeJournal',{});entries=journal.get('characters',{})
        if (not integer(checkpoint.get('revision'),1) or state.get('id')!=r['hostId'] or state.get('phase')!='city'
                or state.get('results')!=[] or len(entries)!=36):
            raise ValueError('Actual unfinished authority journal and all thirty-six full documents are required.')
        for identity in players:
            record=entries.get(r['hostId']+':'+identity,{})
            character(record.get('character',{}));runtime=record['character']['document']['runtime']
            if (record.get('version')!=1 or record.get('hostId')!=r['hostId'] or record.get('characterId')!=identity
                    or record['character']['id']!=identity or record.get('realm')!=record['character']['realm']
                    or record['realm']!=('aegis' if '-aegis-' in identity else 'riftbound') or record['character']['returnMap']!=expected['map']
                    or record.get('scope') not in ('participant','evacuation') or not integer(record.get('revision'),1)
                    or any(type(record.get(k)) is not bool for k in ('returned','recoveryPending','respawnPending'))
                    or record['respawnPending'] is not (runtime.get('dead') is True or runtime['health']==0)
                    or activation and record.get('activationId')!=activation):
                raise ValueError('Recovered full document belongs to another identity or encounter.')
            activation=activation or record.get('activationId')
        lease=journal.get('leases',{}).get(activation,{})
        snapshot(lease.get('snapshot',{}));members=lease.get('participants',[])
        if (lease!=state.get('zones',{}).get('aegis_capital',{}).get('nativeSiege') or lease.get('hostId')!=r['hostId']
                or lease.get('contentRevision')!=expected['cityRevision'] or 'result' in lease
                or lease.get('rulesVersion')!=2 or lease.get('stats')!='campaign' or lease.get('zoneId')!='aegis_capital'
                or lease.get('campaignId')!=r['hostId'] or lease.get('round')!=1 or lease.get('attacker')!='riftbound' or lease.get('defender')!='aegis'
                or any(lease.get(k)!=v for k,v in dict(capacity=18,preparationSeconds=180,stageSeconds=840,transitionSeconds=60,overtimeSeconds=120).items())
                or not integer(lease.get('sequence')) or not finite(lease.get('expiresAt')) or type(lease.get('paused')) is not bool
                or not isinstance(members,list) or len(members)>36 or len({m.get('characterId') for m in members})!=len(members)
                or any(m.get('characterId') not in players or m.get('realm')!=('aegis' if '-aegis-' in m['characterId'] else 'riftbound') for m in members)
                or any(sum(m['realm']==realm for m in members)>18 for realm in ('aegis','riftbound'))):
            raise ValueError('Character recovery cannot claim settlement or replace its owning lease.')
    for attempt in range(2):
        case=r['cases'][attempt];mutation=mutations[attempt];wal=wals[attempt];config=configs[attempt]
        reward=config['recovery']['receiptB' if attempt else 'receiptA']
        if (case.get('mode')!=('after_commit' if attempt else 'before_commit') or case.get('nodeCommittedBeforeKill') is not bool(attempt)
                or not integer(case.get('baseRevision'),1) or case.get('walSequence')!=attempt+1
                or not re.fullmatch('[a-zA-Z0-9_-]{1,100}',str(case.get('requestId',''))) or case.get('nodeRevision')!=case['baseRevision']+attempt
                or case.get('walSha256')!=r['evidence']['wals'][attempt]['sha256']
                or not re.fullmatch('[a-f0-9]{64}',str(case.get('replayBodySha256',''))) or case.get('nativeAckWithheld') is not True or case.get('processKilled') is not True
                or case.get('nativeMutationFileSha256')!=r['evidence']['mutations'][attempt]['sha256']
                or not re.fullmatch('[^/\\\\]+[.]json',str(case.get('walFilename',''))) or mutation.get('schemaVersion')!=1
                or mutation.get('attempt')!=attempt or mutation.get('fixtureId')!=r['fixtureId'] or mutation.get('mutationSucceeded') is not True
                or any(mutation.get(k)!=r[k] for k in ('map','mapSha256','signature','cityRevision'))
                or mutation.get('configSha256')!=r['evidence']['configs'][attempt]['sha256']
                or str(mutation.get('receipt','')).replace('-','').lower()!=reward or mutation.get('before',{}).get('id')!=target
                or mutation.get('after',{}).get('id')!=target or mutation.get('witness',{}).get('characterId')!=target
                or mutation['witness'].get('pending') is not True or mutation['witness'].get('movementHeld') is not True
                or mutation['witness'].get('normalized') is not False):
            raise ValueError('Actual successful native mutations and held original WAL files are required.')
        cast=checked_cast(mutation.get('cast',{}),mutation['after']['document']['runtime'],target,mutation['after']['realm'])
        runtime_evolution(mutation['before']['document']['runtime'],mutation['after']['document']['runtime'])
        if attempt:runtime_evolution(recovered[0]['character']['document']['runtime'],mutation['before']['document']['runtime'],cast)
        wanted=durable(mutation['before']);inventory=wanted['document']['inventory']
        inventory['revision']+=1;inventory['characterProgression']['xp']+=25;inventory['characterProgression']['gold']+=7
        wanted['document']['runtime']['rewards']=sorted(wanted['document']['runtime']['rewards']+[reward])
        if wanted!=durable(mutation['after']) or attempt and durable(mutation['before'])!=durable(recovered[0]['character']):
            raise ValueError('Recovery reward lost inventory, equipment, quests or receipt state.')
        body=wal.get('body',{})
        if (wal.get('schemaVersion')!=1 or wal.get('hostId')!=r['hostId'] or body.get('hostId')!=r['hostId']
                or body.get('activationId')!=activation or body.get('characterId')!=target
                or any(body.get(k)!=case[k] for k in ('requestId','baseRevision','walSequence')) or body.get('character')!=mutation['after']
                or mutation.get('wal',{}).get('filename')!=case['walFilename'] or mutation['wal'].get('sha256')!=case['walSha256']
                or any(mutation['wal'].get(k)!=case[k] for k in ('requestId','baseRevision','walSequence'))):
            raise ValueError('Actual flushed WAL differs from native full character mutation.')
        interrupted=next((row for row in r['http'][attempt] if row['route']=='replay' and row.get('requestId')==case['requestId']),{})
        if (interrupted.get('characterSha256')!=sha(canonical(mutation['after']))
                or interrupted.get('bodySha256')!=case['replayBodySha256']
                or any(interrupted.get(k)!=case[k] for k in ('baseRevision','walSequence'))
                or attempt and not ack(interrupted,target,case['baseRevision']+1,case['walSequence'])
                or not attempt and (interrupted.get('forwarded') is not False or 'responseStatus' in interrupted or 'ack' in interrupted)):
            raise ValueError('HTTP witnesses do not prove both actual interruption boundaries.')
        saved=journals[attempt]['state']['nativeSiegeJournal']['characters'][r['hostId']+':'+target]
        if (saved['revision']!=case['nodeRevision'] or saved['scope']!='participant' or saved['returned'] is not False
                or attempt and (saved.get('walSequence')!=case['walSequence'] or saved['character']!=mutation['after'])
                or not attempt and (saved.get('walSequence',0)>=case['walSequence'] or durable(saved['character'])!=durable(mutation['before']))):
            raise ValueError('Interrupted canonical journal differs from selected CAS revision.')
        if not attempt:runtime_evolution(saved['character']['document']['runtime'],mutation['before']['document']['runtime'],cast)
        restored=recovered[attempt];next_rows=r['http'][attempt+1]
        if (restored.get('schemaVersion')!=1 or restored.get('attempt')!=attempt+1 or restored.get('fixtureId')!=r['fixtureId']
                or restored.get('map')!=r['map'] or restored.get('signature')!=r['signature']
                or restored.get('configSha256')!=r['evidence']['configs'][attempt+1]['sha256'] or restored.get('heldObserved') is not True
                or durable(restored.get('character',{}))!=durable(mutation['after'])):
            raise ValueError('Recovered native character lost persistent fields or its hold.')
        runtime_evolution(mutation['after']['document']['runtime'],restored['character']['document']['runtime'])
        witness(restored['witness'],restored['character'],False)
        replay=next((row for row in next_rows if row['route']=='replay' and row.get('requestId')==case['requestId'] and ack(row,target,case['baseRevision']+1,case['walSequence'])),None)
        restore=next((row for row in next_rows if row['route']=='restore' and row.get('characterId')==target and row.get('responseStatus')==200),None)
        restored_ack=next((row for row in next_rows if row['route']=='restored' and ack(row,target,case['baseRevision']+1,case['walSequence']) and row['ack']['recoveryPending'] is False),None)
        if not replay or not restore or not restored_ack or not replay['index']<restore['index']<restored_ack['index']:
            raise ValueError('WAL replay, canonical restore and readiness ACK must occur in order.')
    if (native.get('schemaVersion')!=1 or native.get('passed') is not True or native.get('recoveryOnly') is not True or native.get('proofOnly') is not True
            or native.get('attempt')!=2 or native.get('fixtureId')!=r['fixtureId'] or native.get('heldObserved') is not True
            or any(native.get(k)!=r[k] for k in ('map','mapSha256','cityRevision','signature'))
            or native.get('configSha256')!=r['evidence']['configs'][2]['sha256'] or native.get('bindings')!=configs[2]['recovery']
            or any(native.get(k) is not False for k in FLAGS+('progressionAcceptance','routeAcceptance'))
            or len(native.get('characters',[]))!=36 or len(native.get('returnWitnesses',[]))!=36
            or len({c.get('id') for c in native['characters']})!=36 or len({w.get('characterId') for w in native['returnWitnesses']})!=36):
        raise ValueError('Native final normal-return report is incomplete or claims broader recovery acceptance.')
    snapshot(native.get('unfinishedSiege',{}))
    final=journals[2]['state'];entries=final['nativeSiegeJournal']['characters']
    for identity in players:
        actual=next((c for c in native['characters'] if c['id']==identity),None);saved=entries[r['hostId']+':'+identity]
        if (not actual or saved['scope']!='evacuation' or saved['returned'] is not True or saved['recoveryPending'] is not False
                or saved['respawnPending'] is not False or actual['document']['zone'] not in final['zones']['aegis_capital']['nativeSiege'].get('safeEvacuationZones',{}).get(actual['realm'],[])
                or durable(saved['character'])!=durable(actual)):
            raise ValueError('Full normal return lacks canonical owning-host safe-zone document.')
        runtime_evolution(saved['character']['document']['runtime'],actual['document']['runtime'])
        witness(next(w for w in native['returnWitnesses'] if w['characterId']==identity),actual,True)
        initial=journals[0]['state']['nativeSiegeJournal']['characters'][r['hostId']+':'+identity]['character']
        wanted=durable(mutations[1]['after'] if identity==target else initial);wanted['document']['zone']=actual['document']['zone']
        if wanted!=durable(actual):raise ValueError('Normal return lost inventory, equipment, quests or reward receipts.')
        runtime_evolution((mutations[1]['after'] if identity==target else initial)['document']['runtime'],actual['document']['runtime'])
        rows=r['http'][2]
        leave=next((x for x in rows if x['route']=='membership' and x.get('characterId')==identity and x.get('action')=='leave' and x.get('forwarded') and x.get('responseStatus')==200),None)
        participant=next((x for x in rows if x['route']=='checkpoint' and x.get('scope')=='participant' and x.get('returned') is True and ack(x,identity)),None)
        evacuation=next((x for x in rows if x['route']=='checkpoint' and x.get('scope')=='evacuation' and x.get('returned') is not True and ack(x,identity)),None)
        returned=next((x for x in rows if x['route']=='checkpoint' and x.get('scope')=='evacuation' and x.get('returned') is True and ack(x,identity,saved['revision'],saved.get('walSequence',0))),None)
        if (not leave or not participant or not evacuation or not returned or not leave['index']<participant['index']<evacuation['index']<returned['index']
                or returned.get('characterSha256')!=sha(canonical(saved['character'])) or returned['ack']['recoveryPending'] is not False):
            raise ValueError('Leave, participant return, evacuation and safe returned full-document ACK must occur in order.')
    return r


def recovery_evidence(root,binding,plan,city,staged,confined,digest,read):
    def load(ref):
        if not isinstance(ref,dict) or not isinstance(ref.get('path'),str) or not ref['path']:
            raise ValueError('Fresh recovery file binding is required.')
        file=confined(root,ref.get('path'))
        if not re.fullmatch('[a-f0-9]{64}',str(ref.get('sha256',''))) or digest(file)!=ref['sha256']:
            raise ValueError('Recovery evidence file changed.')
        return read(file)
    report=load(binding);files=report.get('evidence',{})
    if files.get('version')!=1:raise ValueError('Recovery requires fresh individually hash-bound process evidence.')
    directory='artifacts/unreal/citadel-reference/recovery-proofs/'+str(report.get('fixtureId'))+'/'
    references=[binding,files.get('nativeReport',{}),files.get('http',{}),files.get('processes',{})]+sum((files.get(k,[]) for k in ('mutations','recovered','wals','configs','checkpoints')),[])
    if len(references)!=16 or len({ref.get('path') for ref in references})!=16:
        raise ValueError('Recovery requires sixteen distinct owned evidence files.')
    for ref in references:
        if not str(ref.get('path','')).startswith(directory) or '/' in ref['path'][len(directory):]:
            raise ValueError('Recovery evidence belongs to another owned run.')
    binary=root/'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll'
    if Path(report.get('binaryPath','')).resolve()!=binary.resolve() or digest(binary)!=report.get('binarySha256'):
        raise ValueError('Recovery compiled binary is stale.')
    source_root=root/'unreal/AegisWar/Source'
    actual=sorted(str(file) for file in source_root.rglob('*') if file.is_file() and file.suffix in ('.cpp','.h','.cs'))
    if (not all(str(source_root/'AegisWar/Private'/name) in actual for name in ('WarCitadelSiegeProof.cpp','WarCampaignSiegeSubsystem.cpp'))
            or len(actual)>1024 or sorted(report.get('sourceHashes',{}))!=actual
            or any(digest(Path(file))!=report['sourceHashes'][file] for file in actual)):
        raise ValueError('Recovery must bind every current native source file.')
    for file in actual:Path(file).resolve().relative_to(source_root.resolve())
    bundle=dict(report=report,nativeReport=load(files['nativeReport']),http=load(files['http']),processes=load(files['processes']))
    for key in ('mutations','recovered','wals','configs','checkpoints'):bundle[key]=[load(ref) for ref in files[key]]
    expected=dict(map=staged['map'],mapSha256=staged['packageHashes'][staged['map']],signature=plan['signature'],
        cityRevision=city['city']['revision'],geometrySignature=city['geometrySignature'])
    if (not re.fullmatch('/Game/WorldRebuild/AegisCitadel_[a-f0-9]{12}/CampaignCandidate',expected['map'])
            or digest(root/('unreal/AegisWar/Content/'+expected['map'][6:]+'.umap'))!=expected['mapSha256']):
        raise ValueError('Recovery actual campaign map is stale.')
    return recovery_proof(bundle,expected)

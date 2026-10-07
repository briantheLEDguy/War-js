"""Strict epoch evolution for the narrow process witness; no offline combat ticks."""
import hashlib
import json
import math
import re
import struct


def _fail(message):
    raise ValueError('Invalid recovery runtime progression: '+message)


def _integer(value):
    return type(value) is int and 0 <= value <= 2**53-1


def _same(a, b):
    if isinstance(a,dict) and isinstance(b,dict):
        return set(a)==set(b) and all(_same(a[k],b[k]) for k in a)
    if isinstance(a,list) and isinstance(b,list):
        return len(a)==len(b) and all(_same(x,y) for x,y in zip(a,b))
    if type(a) in (int,float) and type(b) in (int,float):return a==b
    return type(a) is type(b) and a==b


def _number(value,minimum=0,maximum=1_000_000):
    return type(value) in (int,float) and math.isfinite(value) and minimum<=value<=maximum


def _text(value,maximum,empty=False,prose=False):
    return (isinstance(value,str) and len(value.encode('utf-16-le','surrogatepass'))//2<=maximum and (empty or bool(value))
        and not any(ord(c)<32 and not (prose and c in '\r\n\t') or ord(c)==127 for c in value))


def _name(value,empty=False):
    return (_text(value,160,empty) and (empty and value=='' or bool(re.fullmatch(r'[a-zA-Z0-9_.:-]+',value)))
        and value not in ('constructor','prototype','__proto__'))


def _combatant(value,empty=False):
    if not _text(value,512,empty):return False
    if value=='':return empty
    human=re.fullmatch(r'human:([a-zA-Z0-9_-]{1,80})',value)
    if human:return human[1] not in ('constructor','prototype','__proto__')
    if re.fullmatch(r'authored:/Game/[a-zA-Z0-9_/-]+#War(?:World|Zone)Object_[a-zA-Z0-9_]+',value):
        return '..' not in value and '//' not in value
    encounter=re.fullmatch(r'encounter:[a-zA-Z0-9_:-]{1,160}:[012]:(?:aegis|riftbound):[a-zA-Z0-9_-]{1,80}:([0-9]{1,3}):(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})',value)
    return bool(encounter and int(encounter[1])<=127)


_EFFECT_NAMES=('id','recipient','kind','school','statusId','statusKind','modifier','stackGroup','direction')
_EFFECT_NUMBERS=('minimum','maximum','statScale','levelScale','resourceScale','duration','magnitude','distance','periodicDuration','interval')
def _effect(value,default=False,legacy=False):
    if (not isinstance(value,dict) or set(value)!=set(_EFFECT_NAMES+_EFFECT_NUMBERS+('label','hasAmount','cleanse'))
            or any(not _name(value[k],True) for k in _EFFECT_NAMES) or any(not _number(value[k]) for k in _EFFECT_NUMBERS)
            or not _text(value['label'],512,True,True) or type(value['hasAmount']) is not bool
            or not isinstance(value['cleanse'],list) or len(value['cleanse'])>32 or any(not _name(k) for k in value['cleanse'])):
        _fail('applied effect fields')
    if default:
        if (any(value[k]!='' for k in _EFFECT_NAMES) or any(value[k]!=(1 if k=='interval' else 0) for k in _EFFECT_NUMBERS)
                or value['label']!='' or value['hasAmount'] or value['cleanse']):_fail('nondefault modifier effect')
        return value
    if (not _name(value['id']) or value['kind'] not in ('damage','heal','status','player_status','movement','cleanse','wrath_relic','warp_idol')
            or not (legacy and value['recipient']=='' or value['recipient'] in ('caster','target','allies','enemies'))
            or value['minimum']>value['maximum'] or value['duration']>60 or value['periodicDuration']>60 or value['interval']<.1
            or value['distance']>1200 or any(value[k]>1000 for k in ('statScale','levelScale','resourceScale'))
            or value['kind'] in ('damage','heal','warp_idol') and not value['hasAmount']
            or value['kind']=='warp_idol' and value['minimum']<=0
            or value['periodicDuration']>0 and (value['kind'] not in ('damage','heal') or value['periodicDuration']<.1 or value['interval']>value['periodicDuration'])):
        _fail('applied effect semantics')
    if value['kind'] in ('status','player_status'):
        allowed=('burn','bleed','slow','root','silence','stagger','mark','debuff') if value['kind']=='status' else ('shield','guard','empower','haste')
        limit=1 if value['statusKind'] in ('root','silence','stagger') else .75 if value['statusKind']=='guard' else .6000000238418579
        if value['statusKind'] not in allowed or value['duration']<.009999999776482582 or value['magnitude']>limit:_fail('applied status semantics')
    if (value['kind']=='movement' and (not (value['recipient']=='caster' or legacy and value['recipient']=='') or value['direction'] not in ('forward','backward','toward_target'))
            or value['kind']=='cleanse' and any(k not in ('slow','root','stagger','debuff') for k in value['cleanse'])):
        _fail('applied movement or cleanse')
    return value


def _condition(value,depth=1,budget=None):
    budget=[0] if budget is None else budget
    if (not isinstance(value,dict) or set(value)!={'kind','subject','source','abilityId','effectId','not','children'}
            or any(not _name(value[k],True) for k in ('kind','subject','source','abilityId','effectId'))
            or type(value['not']) is not bool or not isinstance(value['children'],list)):_fail('pure condition fields')
    if value['kind'] in ('all','any'):
        if depth>2 or not 1<=len(value['children'])<=16:_fail('condition depth or children')
        for child in value['children']:_condition(child,depth+1,budget)
    else:
        budget[0]+=1
        if (budget[0]>16 or value['children'] or value['kind'] not in ('ability_effect','effect','hot','dot','casting')
                or value['subject'] not in ('caster','target','recipient') or value['source'] not in ('self','allied','any')):_fail('condition predicate')


def _definition(row):
    names=('id','career','version','shape','school','assignmentId','targetKind','timingMode')
    numbers=('preparationScale','range','radius','projectileSpeed','cooldown','gcd','mana','build','cost','minimumResource','resourceMax','resourceInitial','releaseFraction','castSeconds','channelSeconds','tickInterval')
    booleans=('enemyTarget','spendAll','blockedBySilence','legacyTargeting','authoredTiming','cancelOnMovement')
    if (not isinstance(row,dict) or set(row)!={'id','career','version','payload','sha256'}
            or any(not _name(row[k]) for k in ('id','career','version')) or not isinstance(row['payload'],str)
            or len(row['payload'].encode())>65536 or not isinstance(row['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',row['sha256'])
            or hashlib.sha256(row['payload'].encode()).hexdigest()!=row['sha256']):_fail('immutable applied definition hash/identity')
    pure=json.loads(row['payload'])
    if (not isinstance(pure,dict) or set(pure)!=set(('schemaVersion','units','name','summary','unavailableReason','resourceLabel','slot','unlockLevel','maxTargets','presentations','effects','conditions')+names+numbers+booleans)
            or type(pure['schemaVersion']) is not int or pure['schemaVersion']!=1 or pure['units']!='native_cm_seconds'
            or any(pure[k]!=row[k] for k in ('id','career','version')) or any(not _name(pure[k],True) for k in names)
            or any(not _number(pure[k]) for k in numbers) or any(type(pure[k]) is not bool for k in booleans)
            or any(not _text(pure[k],512,True,True) for k in ('name','resourceLabel'))
            or any(not _text(pure[k],4096,True,True) for k in ('summary','unavailableReason'))
            or type(pure['slot']) is not int or not 0<=pure['slot']<=1024 or type(pure['unlockLevel']) is not int or not 1<=pure['unlockLevel']<=1000
            or type(pure['maxTargets']) is not int or not 1<=pure['maxTargets']<=128 or not isinstance(pure['presentations'],dict)
            or len(pure['presentations'])>128 or any(not _name(k) or not _name(v) for k,v in pure['presentations'].items())
            or not isinstance(pure['effects'],list) or len(pure['effects'])>128 or not isinstance(pure['conditions'],list) or len(pure['conditions'])>16):
        _fail('full pure applied definition fields')
    if (not .1<=pure['preparationScale']<=1 or pure['resourceMax']<=0 or pure['resourceInitial']>pure['resourceMax']
            or pure['cooldown']>3600 or pure['gcd']>60 or not .05<=pure['releaseFraction']<=.95 or pure['tickInterval']<.1
            or pure['timingMode'] not in ('','instant','cast','channel')):_fail('applied timing or resource bounds')
    effects={};rules=set()
    def add(e):
        if e['id'] in effects:_fail('duplicate applied effect')
        effects[e['id']]=e
    for e in pure['effects']:add(_effect(e,legacy=pure['legacyTargeting']))
    for rule in pure['conditions']:
        if (not isinstance(rule,dict) or set(rule)!={'id','event','name','condition','actions'} or not _name(rule['id']) or rule['id'] in rules
                or rule['event'] not in ('cast_start','application','tick') or not _text(rule['name'],512,True,True)
                or not isinstance(rule['actions'],list) or not 1<=len(rule['actions'])<=32):_fail('pure conditional rule')
        rules.add(rule['id']);_condition(rule['condition'])
        if rule['condition']['kind'] not in ('all','any'):_fail('root conditional group')
        modifiers=set()
        for action in rule['actions']:
            if (not isinstance(action,dict) or set(action)!={'kind','effectId','value','effect'} or action['kind'] not in ('add_effect','flat','percent')
                    or not _name(action['effectId'],True) or not _number(action['value'],-1_000_000)):_fail('pure conditional action')
            e=_effect(action['effect'],action['kind']!='add_effect',pure['legacyTargeting'])
            if action['kind']=='add_effect':
                if e['kind'] not in ('damage','heal','status','player_status') or rule['event']=='tick' and (e['periodicDuration']>0 or e['statusKind'] in ('burn','bleed')):_fail('recursive conditional bonus')
                add(e)
            else:
                base=next((v for v in pure['effects'] if v['id']==action['effectId']),None);identity=(action['kind'],action['effectId'])
                if (not base or base['kind'] not in ('damage','heal') or identity in modifiers or action['kind']=='percent' and not -1<=action['value']<=100
                        or rule['event']=='tick' and base['periodicDuration']<=0 and pure['timingMode']!='channel'):_fail('conditional amount modifier')
                modifiers.add(identity)
        if rule['event']=='tick' and pure['timingMode']!='channel' and not any(e['periodicDuration']>0 for e in pure['effects']):_fail('conditional tick without periodic definition')
    return effects


def checked_runtime(value):
    if (not isinstance(value,dict) or value.get('version')!=2 or type(value.get('version')) is not int
            or set(value)!={'version','capturedAtUnixMs','health','mana','dead','rewards','questKills','abilities','combat'}
            or not _integer(value.get('capturedAtUnixMs')) or value['capturedAtUnixMs']==0):
        _fail('fresh process evidence requires the complete epoch codec')
    a=value.get('abilities',{});c=value.get('combat',{});now=value['capturedAtUnixMs']
    def number(v,maximum):return type(v) in (int,float) and math.isfinite(v) and 0<=v<=maximum
    def deadline(remaining,expiry,maximum):
        return number(remaining,maximum) and _integer(expiry) and abs(max(0,expiry-now)/1000-remaining)<=.01
    if (not number(value['health'],3.4028234663852886e38) or not number(value['mana'],3.4028234663852886e38)
            or type(value['dead']) is not bool):_fail('native state values')
    for key in ('rewards','questKills'):
        rows=value[key]
        if (not isinstance(rows,list) or len(rows)>65536 or any(not isinstance(r,str) or not re.fullmatch(r'(?:[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})',r) for r in rows)
                or len({r.replace('-','').lower() for r in rows})!=len(rows)):_fail('native authoritative receipts')
    if (not isinstance(a,dict) or not isinstance(c,dict) or set(a)!={'resource','globalCooldown','globalCooldownExpiresAtUnixMs','cooldowns'}
            or not number(a.get('resource'),1e6) or not deadline(a.get('globalCooldown'),a.get('globalCooldownExpiresAtUnixMs'),60)
            or not isinstance(a.get('cooldowns'),list) or len(a['cooldowns'])>256
            or set(c)!={'version','definitions','statuses','ascEffects'} or c.get('version')!=1 or type(c.get('version')) is not int
            or any(not isinstance(c.get(k),list) or len(c[k])>limit for k,limit in (('definitions',128),('statuses',128),('ascEffects',16)))):
        _fail('bounded combat or class cooldown epoch schema')
    for row in a['cooldowns']:
        if (not isinstance(row,dict) or set(row)!={'id','remaining','expiresAtUnixMs'} or not _name(row.get('id'))
                or not deadline(row.get('remaining'),row.get('expiresAtUnixMs'),3600)):_fail('class cooldown row')
    definitions={};effects={};identities=set()
    for d in c['definitions']:
        applied=_definition(d);identity=(d['career'],d['id'],d['version'])
        if d['sha256'] in definitions or identity in identities:_fail('duplicate applied definition')
        definitions[d['sha256']]=d
        effects[d['sha256']]=applied;identities.add(identity)
    status_fields={'id','kind','group','modifier','label','magnitude','shield','tickDamage','tickHealing','interval',
        'expiresAtUnixMs','nextTickAtUnixMs','sourceKey','sourceRealm','abilityId','effectId','category','appliedVersion','definitionSha256'}
    for s in c['statuses']:
        if (not isinstance(s,dict) or set(s) not in (status_fields,status_fields|{'periodic'})
                or not _integer(s.get('expiresAtUnixMs')) or not _integer(s.get('nextTickAtUnixMs'))
                or not number(s.get('interval'),60) or s['interval']<.1
                or s['definitionSha256'] not in definitions or s['expiresAtUnixMs']-now>60001
                or any(not number(s.get(k),3.4028234663852886e38) for k in ('shield','tickDamage','tickHealing'))
                or not number(s.get('magnitude'),1) or not _text(s['id'],1024) or not _combatant(s['sourceKey'])
                or s['sourceRealm'] not in ('','aegis','riftbound') or s['kind'] not in ('burn','bleed','slow','root','silence','stagger','mark','debuff','shield','guard','empower','haste','dot','hot')
                or s['category'] not in ('status','shield','dot','hot') or not _name(s['group'],True) or not _name(s['modifier'],True)
                or not _text(s['label'],512,True,True) or any(not _name(s[k]) for k in ('abilityId','effectId','appliedVersion'))):_fail('status epoch/immutable definition row')
        d=definitions[s['definitionSha256']]
        if d['id']!=s['abilityId'] or d['version']!=s['appliedVersion'] or s['effectId'] not in effects[s['definitionSha256']]:_fail('status applied definition reference')
        if 'periodic' in s:
            p=s['periodic']
            if (not isinstance(p,dict) or set(p)!={'base','strength','level','bonus','targetKey'} or not _number(p['base'],0,3.4028234663852886e38)
                    or not _number(p['strength']) or type(p['level']) is not int or not 1<=p['level']<=1000
                    or type(p['bonus']) is not bool or not _combatant(p['targetKey'],True)):_fail('periodic immutable execution')
    for s in c['ascEffects']:
        if (not isinstance(s,dict) or set(s)!={'id','expiresAtUnixMs','level','stacks'} or s['id']!='DevelopmentStrikeCooldown'
                or not _integer(s['expiresAtUnixMs']) or s['expiresAtUnixMs']-now>3600001
                or not number(s['level'],1000) or s['level']<=0 or type(s['stacks']) is not int or s['stacks']!=1):_fail('supported ASC epoch row')
    for rows in (a['cooldowns'],c['statuses'],c['ascEffects']):
        if len({r['id'] for r in rows})!=len(rows):_fail('duplicate runtime identity')
    return value


def checked_cast(value,state,character_id,realm):
    r=checked_runtime(state)
    definition=next((d for d in r['combat']['definitions'] if d['sha256']==value.get('definitionSha256')),None)
    if (set(value)!={'abilityId','career','version','definitionSha256','startedAtUnixMs','succeeded','observedAtUnixMs','statusIds','cooldownExpiresAtUnixMs'}
            or value.get('succeeded') is not True or not definition or any(definition[k]!=value[key] for k,key in
                (('id','abilityId'),('career','career'),('version','version')))
            or not _integer(value.get('startedAtUnixMs')) or not 0<value['startedAtUnixMs']<=r['capturedAtUnixMs']
            or value.get('observedAtUnixMs')!=r['capturedAtUnixMs'] or not isinstance(value.get('statusIds'),list)
            or not value['statusIds'] or any(not isinstance(v,str) for v in value['statusIds'])
            or len(set(value['statusIds']))!=len(value['statusIds'])):_fail('actual catalog cast identity or times')
    applied=json.loads(definition['payload'])
    statuses=[s for s in r['combat']['statuses'] if s['abilityId']==value['abilityId']
        and s['appliedVersion']==value['version'] and s['definitionSha256']==value['definitionSha256']]
    effects=applied['effects']+[a['effect'] for rule in applied['conditions'] for a in rule['actions'] if a['kind']=='add_effect']
    def matches(s):
        effect=next((e for e in effects if e['id']==s['effectId']),None)
        if not effect:return False
        # Empty legacy status names serialize through FName::ToString as None.
        identity=definition['id']+':'+(effect['id']+':'+s['sourceKey'] if effect['recipient'] else (effect['statusId'] or 'None')+':'+effect['statusKind'])
        return (effect['kind']=='player_status' and (effect['recipient']=='caster' or applied['legacyTargeting'] and effect['recipient']=='')
            and s['id']==identity and s['kind']==effect['statusKind'] and s['group']==effect['stackGroup'] and s['modifier']==effect['modifier']
            and s['label']==(effect['label'] or effect['statusKind']) and s['category']==('shield' if s['kind']=='shield' else 'status')
            and s['magnitude']==min(effect['magnitude'],.75 if s['kind']=='guard' else .6000000238418579)
            and s['interval']==1 and s['tickDamage']==0 and s['tickHealing']==0 and 'periodic' not in s
            and s['expiresAtUnixMs']-r['capturedAtUnixMs']<=effect['duration']*1000+1)
    if (applied.get('enemyTarget') is not False or applied.get('targetKind') not in ('self','ally') or not applied.get('effects')
            or any(e.get('kind')!='player_status' or e.get('recipient')!='caster'
                and not (applied.get('legacyTargeting') is True and e.get('recipient')=='') for e in applied['effects'])
            or sorted(s['id'] for s in statuses)!=sorted(value['statusIds'])
            or any(not matches(s) or s['sourceKey']!='human:'+character_id or s['sourceRealm']!=realm or s['expiresAtUnixMs']<=r['capturedAtUnixMs'] for s in statuses)
            or not any(c['id']==value['abilityId'] and c['expiresAtUnixMs']==value['cooldownExpiresAtUnixMs']
                and 0<c['expiresAtUnixMs']-r['capturedAtUnixMs']<=applied['cooldown']*1000+1 for c in r['abilities']['cooldowns'])):
        _fail('actual self-cast status or cooldown')
    return value


def runtime_evolution(before,after,cast=None):
    a,b=checked_runtime(before),checked_runtime(after);now=b['capturedAtUnixMs']
    if now<a['capturedAtUnixMs']:_fail('capture epoch moved backwards')
    resource=a['abilities']['resource']
    if cast:
        definition=next((d for d in b['combat']['definitions'] if d['sha256']==cast['definitionSha256']),None)
        if not definition:_fail('cast has no recorded resource definition')
        pure=json.loads(definition['payload']);f32=lambda v:struct.unpack('<f',struct.pack('<f',v))[0]
        resource=min(pure['resourceMax'],max(0,f32(f32(0 if pure['spendAll'] else resource-pure['cost'])+pure['build'])))
        if b['abilities']['globalCooldownExpiresAtUnixMs']-now>pure['gcd']*1000+1:_fail('actual cast cannot extend its recorded global cooldown')
    if b['abilities']['resource']!=resource:_fail('class resource lost or changed without its actual cast')
    recast=lambda s:bool(cast and s['id'] in cast['statusIds'] and s['abilityId']==cast['abilityId']
        and s['appliedVersion']==cast['version'] and s['definitionSha256']==cast['definitionSha256'])
    old_statuses={s['id']:s for s in a['combat']['statuses']};new_statuses={s['id']:s for s in b['combat']['statuses']}
    replaced=lambda old:bool(cast and any(recast(new) and (old['group']!='' and old['group']==new['group']
        or old['kind']=='shield' and new['kind']=='shield') for new in b['combat']['statuses']))
    for old in a['combat']['statuses']:
        new=new_statuses.get(old['id'])
        if new and recast(new):continue
        if not new:
            if old['expiresAtUnixMs']>now and not replaced(old):_fail('unexpired status disappeared')
            continue
        if not _same({k:v for k,v in old.items() if k!='nextTickAtUnixMs'},{k:v for k,v in new.items() if k!='nextTickAtUnixMs'}):
            _fail('surviving status values, source, definition or deadline changed')
        diff=new['nextTickAtUnixMs']-old['nextTickAtUnixMs'];interval=old['interval']*1000
        # Difference of two rounded-ms cadence endpoints; fixed expiries never drift.
        steps=math.floor(diff/interval+.5)
        if diff<0 or diff and (steps<1 or abs(diff-steps*interval)>1 or not now<new['nextTickAtUnixMs']<=now+interval+1):
            _fail('tick cadence reset instead of skipping overdue ticks')
    if any(s['id'] not in old_statuses and not recast(s) for s in b['combat']['statuses']):_fail('unsupported new combat status')
    old_definitions={d['sha256']:d for d in a['combat']['definitions']};used={s['definitionSha256'] for s in b['combat']['statuses']}
    if len(used)!=len(b['combat']['definitions']):_fail('unreferenced or missing applied definition')
    for d in b['combat']['definitions']:
        if d['sha256'] not in used or (not _same(old_definitions[d['sha256']],d) if d['sha256'] in old_definitions
                else not cast or d['sha256']!=cast['definitionSha256']):_fail('immutable applied definition replaced')
    old_asc={s['id']:s for s in a['combat']['ascEffects']};new_asc={s['id']:s for s in b['combat']['ascEffects']}
    for old in a['combat']['ascEffects']:
        new=new_asc.get(old['id'])
        if (not _same(old,new) if new else old['expiresAtUnixMs']>now):_fail('supported ASC values or deadline changed')
    if any(s['id'] not in old_asc for s in b['combat']['ascEffects']):_fail('new ASC entry has no actual cast witness')
    old_cd={c['id']:c for c in a['abilities']['cooldowns']};new_cd={c['id']:c for c in b['abilities']['cooldowns']}
    for old in a['abilities']['cooldowns']:
        new=new_cd.get(old['id'])
        if cast and cast['abilityId']==old['id'] and new and new['expiresAtUnixMs']==cast['cooldownExpiresAtUnixMs']:continue
        if old['expiresAtUnixMs']>now and (not new or new['expiresAtUnixMs']!=old['expiresAtUnixMs']):_fail('unexpired class cooldown lost or reset')
        if old['expiresAtUnixMs']<=now and new and new['expiresAtUnixMs']>now:_fail('expired class cooldown restarted')
    for new in b['abilities']['cooldowns']:
        if new['id'] not in old_cd and not (cast and new['id']==cast['abilityId'] and new['expiresAtUnixMs']==cast['cooldownExpiresAtUnixMs']):
            _fail('new class cooldown lacks its actual cast')
    if not cast and (b['abilities']['globalCooldownExpiresAtUnixMs']!=a['abilities']['globalCooldownExpiresAtUnixMs']
            if a['abilities']['globalCooldownExpiresAtUnixMs']>now else b['abilities']['globalCooldownExpiresAtUnixMs']>now):
        _fail('global cooldown reset')

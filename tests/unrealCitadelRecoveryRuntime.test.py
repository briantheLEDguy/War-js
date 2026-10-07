"""Synthetic epoch corpus; this never runs or approves a native process."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/unreal'))
from citadel_recovery_runtime import checked_cast,checked_runtime,runtime_evolution

EPOCH=1_800_000_000_000
IDENTITY='portable_recovery'

def capture(before,now):
    value=copy.deepcopy(before);value['capturedAtUnixMs']=now;a=value['abilities']
    a['globalCooldown']=max(0,(a['globalCooldownExpiresAtUnixMs']-now)/1000)
    for row in a['cooldowns']:row['remaining']=max(0,(row['expiresAtUnixMs']-now)/1000)
    return value

def definition(value,pure):
    d=value['combat']['definitions'][0]
    d['payload']=json.dumps(pure,separators=(',',':'));d['sha256']=hashlib.sha256(d['payload'].encode()).hexdigest()
    value['combat']['statuses'][0]['definitionSha256']=d['sha256']

class RecoveryRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=('import { recoveryRuntimeFixture } from "./tests/fixtures/citadelRecoveryRuntime.ts";'
            'process.stdout.write(JSON.stringify(recoveryRuntimeFixture("portable_recovery","aegis",1800000000100,1800000000000)));')
        cls.before=json.loads(subprocess.check_output(['node',str(ROOT/'node_modules/tsx/dist/cli.mjs'),'-e',source],cwd=ROOT,text=True))

    def periodic(self):
        r=copy.deepcopy(self.before);s=r['combat']['statuses'][0];pure=json.loads(r['combat']['definitions'][0]['payload'])
        pure['effects'][0].update(kind='heal',statusId='',statusKind='',stackGroup='',duration=0,
            magnitude=0,periodicDuration=30,minimum=10,maximum=10,hasAmount=True)
        definition(r,pure)
        s.update(kind='hot',category='hot',group='',magnitude=0,tickHealing=10,nextTickAtUnixMs=EPOCH+1000,
            periodic=dict(base=10,strength=1,level=1,bonus=False,targetKey='human:'+IDENTITY))
        return r

    def test_capture_and_expired_stored_rows_do_not_renew_deadlines(self):
        runtime_evolution(self.before,capture(self.before,EPOCH+150))
        runtime_evolution(self.before,capture(self.before,EPOCH+31000))
        expired=capture(self.before,EPOCH+31000);expired['combat']['statuses']=[];expired['combat']['definitions']=[];expired['abilities']['cooldowns']=[]
        runtime_evolution(self.before,expired)
        reset=capture(self.before,EPOCH+150);reset['combat']['statuses'][0]['expiresAtUnixMs']+=30
        with self.assertRaisesRegex(ValueError,'deadline changed'):runtime_evolution(self.before,reset)

    def test_periodic_cadence_only_skips_whole_elapsed_intervals(self):
        before=self.periodic();after=capture(before,EPOCH+5100);after['combat']['statuses'][0]['nextTickAtUnixMs']=EPOCH+6000
        runtime_evolution(before,after)
        for tick in (EPOCH+5000,EPOCH+6100,EPOCH+7000,EPOCH):
            bad=copy.deepcopy(after);bad['combat']['statuses'][0]['nextTickAtUnixMs']=tick
            with self.subTest(tick=tick),self.assertRaisesRegex(ValueError,'cadence'):runtime_evolution(before,bad)
        bad=copy.deepcopy(after);bad['combat']['statuses'][0]['periodic']['base']=11
        with self.assertRaisesRegex(ValueError,'values'):runtime_evolution(before,bad)

    def test_fractional_cadence_rounding_does_not_permit_expiry_drift(self):
        before=self.periodic();interval=.33329999446868896;pure=json.loads(before['combat']['definitions'][0]['payload'])
        pure['effects'][0]['interval']=interval;definition(before,pure)
        before['combat']['statuses'][0].update(interval=interval,nextTickAtUnixMs=EPOCH+333)
        after=capture(before,EPOCH+1500);after['combat']['statuses'][0]['nextTickAtUnixMs']=EPOCH+1666
        runtime_evolution(before,after)
        after['combat']['statuses'][0]['nextTickAtUnixMs']=EPOCH+1668
        with self.assertRaisesRegex(ValueError,'cadence'):runtime_evolution(before,after)

    def test_source_values_loss_cooldown_and_historical_downgrade_reject(self):
        for field,value in (('sourceKey','human:somebody_else'),('shield',1),('effectId','not_applied')):
            bad=capture(self.before,EPOCH+150);bad['combat']['statuses'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):runtime_evolution(self.before,bad)
        lost=capture(self.before,EPOCH+150);lost['combat']['statuses']=[];lost['combat']['definitions']=[]
        with self.assertRaises(ValueError):runtime_evolution(self.before,lost)
        for field in ('global','class'):
            bad=capture(self.before,EPOCH+150)
            if field=='class':bad['abilities']['cooldowns'][0]['expiresAtUnixMs']+=30;bad['abilities']['cooldowns'][0]['remaining']+=.03
            else:bad['abilities']['globalCooldownExpiresAtUnixMs']+=30;bad['abilities']['globalCooldown']+=.03
            with self.subTest(field=field),self.assertRaises(ValueError):runtime_evolution(self.before,bad)
        old=capture(self.before,EPOCH+150);old['version']=1
        with self.assertRaises(ValueError):runtime_evolution(self.before,old)
        bad=capture(self.before,EPOCH+150);bad['abilities']['resource']=0
        with self.assertRaisesRegex(ValueError,'class resource'):runtime_evolution(self.before,bad)

    def test_supported_asc_stores_fixed_epoch_until_natural_removal(self):
        before=copy.deepcopy(self.before);before['combat']['ascEffects']=[dict(id='DevelopmentStrikeCooldown',expiresAtUnixMs=EPOCH+2000,level=2,stacks=1)]
        runtime_evolution(before,capture(before,EPOCH+2100))
        removed=capture(before,EPOCH+2100);removed['combat']['ascEffects']=[];runtime_evolution(before,removed)
        bad=capture(before,EPOCH+150);bad['combat']['ascEffects'][0]['expiresAtUnixMs']+=30
        with self.assertRaisesRegex(ValueError,'ASC'):runtime_evolution(before,bad)

    def test_genuine_self_cast_witness_is_required_for_new_status(self):
        after=copy.deepcopy(self.before);d=after['combat']['definitions'][0]
        cast=dict(abilityId=d['id'],career=d['career'],version=d['version'],definitionSha256=d['sha256'],startedAtUnixMs=EPOCH,
            succeeded=True,observedAtUnixMs=after['capturedAtUnixMs'],statusIds=[after['combat']['statuses'][0]['id']],
            cooldownExpiresAtUnixMs=after['abilities']['cooldowns'][0]['expiresAtUnixMs'])
        checked_cast(cast,after,IDENTITY,'aegis')
        baseline=capture(after,EPOCH);baseline['combat']['statuses']=[];baseline['combat']['definitions']=[];baseline['abilities'].update(cooldowns=[],globalCooldown=0,globalCooldownExpiresAtUnixMs=0)
        runtime_evolution(baseline,after,cast)
        with self.assertRaisesRegex(ValueError,'new combat status'):runtime_evolution(baseline,after)
        for change in (dict(succeeded=False),dict(statusIds=[]),dict(career='another_career'),dict(observedAtUnixMs=EPOCH+200),dict(cooldownExpiresAtUnixMs=EPOCH+99000)):
            with self.subTest(change=change),self.assertRaises(ValueError):checked_cast(dict(cast,**change),after,IDENTITY,'aegis')

    def test_legacy_empty_name_requires_exact_native_none_identity(self):
        after=copy.deepcopy(self.before);d=after['combat']['definitions'][0];pure=json.loads(d['payload'])
        pure['legacyTargeting']=True;pure['effects'][0].update(recipient='',statusId='');definition(after,pure)
        after['combat']['statuses'][0]['id']=d['id']+':None:haste'
        cast=dict(abilityId=d['id'],career=d['career'],version=d['version'],definitionSha256=d['sha256'],startedAtUnixMs=EPOCH,
            succeeded=True,observedAtUnixMs=after['capturedAtUnixMs'],statusIds=[after['combat']['statuses'][0]['id']],
            cooldownExpiresAtUnixMs=after['abilities']['cooldowns'][0]['expiresAtUnixMs'])
        checked_cast(cast,after,IDENTITY,'aegis')
        for middle in ('','none','another_status'):
            bad=copy.deepcopy(after);bad['combat']['statuses'][0]['id']=d['id']+':'+middle+':haste'
            wrong=dict(cast,statusIds=[bad['combat']['statuses'][0]['id']])
            with self.subTest(middle=middle),self.assertRaisesRegex(ValueError,'self-cast'):
                checked_cast(wrong,bad,IDENTITY,'aegis')

    def test_hash_bound_payload_still_requires_complete_applied_native_semantics(self):
        for mutate in (lambda p:p.pop('conditions'),lambda p:p['effects'][0].update(duration=120),
                lambda p:p['effects'][0].update(recipient='client_object'),lambda p:p.update(opaqueUObject='/Game/Unsafe')):
            bad=copy.deepcopy(self.before);pure=json.loads(bad['combat']['definitions'][0]['payload']);mutate(pure);definition(bad,pure)
            with self.assertRaises(ValueError):checked_runtime(bad)
        for mutate in (lambda s:s.update(sourceKey='UObject:/Unsafe'),lambda s:s.update(effectId='not_applied'),
                lambda s:s.update(periodic=dict(base=1,strength=1,level=1,bonus=False,targetKey='UObject:/Unsafe'))):
            bad=copy.deepcopy(self.before);mutate(bad['combat']['statuses'][0])
            with self.assertRaises(ValueError):checked_runtime(bad)

    def test_genuine_cast_resource_cost_and_build_match_native_float_math(self):
        after=copy.deepcopy(self.before);pure=json.loads(after['combat']['definitions'][0]['payload']);pure.update(cost=7,build=2);definition(after,pure)
        after['abilities']['resource']=15;d=after['combat']['definitions'][0]
        cast=dict(abilityId=d['id'],career=d['career'],version=d['version'],definitionSha256=d['sha256'],startedAtUnixMs=EPOCH,
            succeeded=True,observedAtUnixMs=after['capturedAtUnixMs'],statusIds=[after['combat']['statuses'][0]['id']],
            cooldownExpiresAtUnixMs=after['abilities']['cooldowns'][0]['expiresAtUnixMs'])
        checked_cast(cast,after,IDENTITY,'aegis')
        baseline=capture(after,EPOCH);baseline['combat']['statuses']=[];baseline['combat']['definitions']=[];baseline['abilities'].update(resource=20,cooldowns=[],globalCooldown=0,globalCooldownExpiresAtUnixMs=0)
        runtime_evolution(baseline,after,cast)
        after['abilities']['resource']=14
        with self.assertRaisesRegex(ValueError,'class resource'):runtime_evolution(baseline,after,cast)

    def test_named_self_cast_replaces_only_its_actual_native_stack_group(self):
        after=capture(self.before,EPOCH+5100);s=after['combat']['statuses'][0];d=after['combat']['definitions'][0];pure=json.loads(d['payload'])
        pure['id']='battle_prelate.second_haste';pure['effects'][0]['id']='second_haste';d['id']=pure['id'];definition(after,pure)
        s.update(id=d['id']+':second_haste:human:'+IDENTITY,abilityId=d['id'],effectId='second_haste',expiresAtUnixMs=EPOCH+35000)
        after['abilities']['cooldowns'].append(dict(id=d['id'],remaining=29.9,expiresAtUnixMs=EPOCH+35000))
        after['abilities'].update(globalCooldown=.9,globalCooldownExpiresAtUnixMs=EPOCH+6000)
        cast=dict(abilityId=d['id'],career=d['career'],version=d['version'],definitionSha256=d['sha256'],startedAtUnixMs=EPOCH+5000,
            succeeded=True,observedAtUnixMs=after['capturedAtUnixMs'],statusIds=[s['id']],cooldownExpiresAtUnixMs=EPOCH+35000)
        checked_cast(cast,after,IDENTITY,'aegis');runtime_evolution(self.before,after,cast)
        unrelated=copy.deepcopy(self.before);unrelated['combat']['statuses'][0]['group']='other_group'
        with self.assertRaisesRegex(ValueError,'unexpired status disappeared'):runtime_evolution(unrelated,after,cast)
        bad=copy.deepcopy(after);bad['combat']['statuses'][0]['group']='other_group'
        with self.assertRaisesRegex(ValueError,'self-cast'):checked_cast(cast,bad,IDENTITY,'aegis')

if __name__=='__main__':unittest.main()

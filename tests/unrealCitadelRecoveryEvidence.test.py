"""Portable strict recovery consumers using explicitly synthetic test receipts."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts/unreal'))
from citadel_recovery_evidence import recovery_proof,recovery_evidence,canonical


def fixture(repository='/portable-test'):
    source=('import { recoveryEvidenceFixture } from "./tests/fixtures/citadelRecoveryEvidence.ts";'
        'import { recoveryCanonical } from "./scripts/unreal/citadel-recovery-evidence.ts";'
        'process.stdout.write(recoveryCanonical(recoveryEvidenceFixture('+json.dumps(repository)+')));')
    # Share the same synthetic corpus across both consumers; this never launches Unreal.
    return json.loads(subprocess.check_output(['node',str(ROOT/'node_modules/tsx/dist/cli.mjs'),'-e',source],cwd=ROOT,text=True))


def expected(value):
    return {k:value['report'][k] for k in ('map','mapSha256','signature','cityRevision','geometrySignature')}


class RecoveryEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.fixture=fixture()

    def test_narrow_three_process_shape_and_every_acceptance_flag(self):
        recovery_proof(copy.deepcopy(self.fixture),expected(self.fixture))
        for flag in ('outcomeRecoveryVerified','equipmentMutationVerified','deadIntentVerified','releaseAcceptance','fullSiegeAdmission'):
            bad=copy.deepcopy(self.fixture);bad['report'][flag]=True
            with self.subTest(flag=flag),self.assertRaisesRegex(ValueError,'broader'):
                recovery_proof(bad,expected(self.fixture))

    def test_stale_tampered_missing_raced_and_unsafe_receipts_fail(self):
        changes=(
            lambda f:f['report'].update(cityRevision='f'*64),
            lambda f:f['processes']['attempts'].pop(),
            lambda f:f['processes']['attempts'][0].update(killRequested=False),
            lambda f:f['processes']['attempts'][1].update(pid=f['processes']['attempts'][0]['pid']),
            lambda f:f['report']['http'][0][-1].update(forwarded=True),
            lambda f:f['wals'][1]['body']['character']['document']['inventory'].update(items=[]),
            lambda f:f['mutations'][0].pop('cast'),
            lambda f:f['mutations'][0]['cast'].update(succeeded=False),
            lambda f:f['mutations'][0]['wal'].update(walSequence=f['mutations'][0]['wal']['walSequence']+1),
            lambda f:f['recovered'][0]['character']['document']['runtime'].update(version=1),
            lambda f:f['recovered'][0]['character']['document']['runtime']['combat'].update(statuses=[],definitions=[]),
            lambda f:f['recovered'][0]['character']['document']['runtime']['combat']['statuses'][0].update(expiresAtUnixMs=1800000031001),
            lambda f:f['recovered'][0]['character']['document']['runtime']['abilities'].update(cooldowns=[]),
            lambda f:f['recovered'][1]['character']['document']['inventory'].update(equipment=[]),
            lambda f:f['nativeReport']['characters'][1]['document']['runtime'].update(questKills=[]),
            lambda f:f['nativeReport']['characters'].pop(),
            lambda f:next(row for row in f['report']['http'][2] if row.get('scope')=='participant').update(index=9999),
            lambda f:f['nativeReport']['returnWitnesses'][0].update(physicalReady=False),
            lambda f:f['nativeReport']['returnWitnesses'][0].update(movementHeld=True),
            lambda f:next(iter(f['checkpoints'][2]['state']['nativeSiegeJournal']['characters'].values())).update(returned=False),
            lambda f:f['nativeReport']['unfinishedSiege'].update(phase='finished',attackersWon=True))
        for index,change in enumerate(changes):
            bad=copy.deepcopy(self.fixture);change(bad)
            with self.subTest(case=index),self.assertRaises(ValueError):recovery_proof(bad,expected(self.fixture))

    def test_current_files_sources_binary_and_confinement_are_required(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);data=fixture(str(root));report=data['report'];files=report['evidence']
            def put(file,text):file.parent.mkdir(parents=True,exist_ok=True);file.write_text(text,encoding='utf-8')
            binary=Path(report['binaryPath']);put(binary,'portable native binary')
            put(root/('unreal/AegisWar/Content/'+report['map'][6:]+'.umap'),'portable campaign package')
            sources=list(report['sourceHashes'])
            source_text=lambda source:'portable proof source' if Path(source).name=='WarCitadelSiegeProof.cpp' else 'portable bridge source'
            for source in sources:put(Path(source),source_text(source))
            def save(binding,value):
                text=canonical(value);self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),binding['sha256']);put(root/binding['path'],text)
            for key in ('mutations','recovered','wals','configs','checkpoints'):
                for index,value in enumerate(data[key]):save(files[key][index],value)
            for key in ('nativeReport','http','processes'):save(files[key],data[key])
            binding=dict(path=files['http']['path'].replace('http.json','report.json'),sha256=hashlib.sha256(canonical(report).encode()).hexdigest());save(binding,report)
            def confined(base,relative):
                if not isinstance(relative,str) or not relative or Path(relative).is_absolute() or '\\' in relative:raise ValueError('relative path required')
                file=(base/relative).resolve();file.relative_to(base.resolve());return file
            digest=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
            read=lambda file:json.loads(file.read_text(encoding='utf-8-sig'))
            plan=dict(signature=report['signature']);city=dict(city=dict(revision=report['cityRevision']),geometrySignature=report['geometrySignature'])
            staged=dict(map=report['map'],packageHashes={report['map']:report['mapSha256']})
            call=lambda:recovery_evidence(root,binding,plan,city,staged,confined,digest,read)
            call();put(Path(sources[1]),'changed bridge source')
            with self.assertRaisesRegex(ValueError,'every current native source'):call()
            put(Path(sources[1]),source_text(sources[1]));put(binary,'changed binary')
            with self.assertRaisesRegex(ValueError,'binary is stale'):call()
            put(binary,'portable native binary');put(root/files['wals'][0]['path'],'{}')
            with self.assertRaisesRegex(ValueError,'file changed'):call()
            with self.assertRaises(ValueError):recovery_evidence(root,dict(binding,path='../report.json'),plan,city,staged,confined,digest,read)

    def test_generic_character_restored_boolean_cannot_supply_process_recovery(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises((ValueError,KeyError,FileNotFoundError)):
                recovery_evidence(Path(directory),{},dict(signature='a'*64),{}, {},
                    lambda root,path:root/path,lambda file:'a'*64,lambda file:{})

    def test_character_digest_uses_json_stringify_number_and_unicode_policy(self):
        self.assertEqual(canonical(dict(a=10.0,b=.00001,c=1e21,d=-0.0,e='Å🛡')),
            '{"a":10,"b":0.00001,"c":1e+21,"d":0,"e":"Å🛡"}')
        self.assertEqual(canonical([1.0000000000000001e18,9007199254740993]),'[1000000000000000100,9007199254740992]')


if __name__=='__main__':unittest.main()

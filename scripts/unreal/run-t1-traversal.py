"""Run native character movement without changing candidate, capital or owner packages."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from t1_traversal import traversal_config, validate_traversal, ZONES

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
PROJECT = ROOT/'unreal/AegisWar'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--headless', action='store_true', help='Both directions of all roads/supply routes plus homes; fixed simulation timestep')
    parser.add_argument('--zone', choices=ZONES)
    parser.add_argument('--candidate', choices=('homes', 'materials', 'atmosphere'), default='homes')
    args = parser.parse_args()
    receipt = json.loads((DIRECTORY/(args.candidate+'-latest.json')).read_text())
    plan = json.loads((DIRECTORY/'plan.json').read_text())
    sha = lambda file: hashlib.sha256(file.read_bytes()).hexdigest()
    baseline = {PROJECT/'Content'/(package.removeprefix('/Game/')+'.umap'): digest
                for package, digest in {**receipt['inputs']['parentPackages'], **receipt['packageHashes']}.items()}
    baseline.update({PROJECT/'Content'/(package.removeprefix('/Game/')+'.uasset'): digest
                     for package, digest in receipt['inputs']['dependencyHashes'].items()})
    baseline.update({ROOT/file: digest for file, digest in plan['privateMapHashes'].items()})
    if args.candidate in ('materials', 'atmosphere'):
        baseline.update({ROOT/file: digest for file, digest in receipt['inputs']['protectedHashes'].items()})
        baseline.update({ROOT/file: digest for file, digest in receipt['assetHashes'].items()})
    owner_directory = PROJECT/'Saved/WorldEdit'
    owner_files = set(owner_directory.rglob('*.json'))
    baseline.update({file: sha(file) for file in owner_files})
    def verify_saved():
        if set(owner_directory.rglob('*.json')) != owner_files:
            raise RuntimeError('Owner GM document inventory changed')
        for file, digest in baseline.items():
            if sha(file) != digest:
                raise RuntimeError('Saved baseline changed: '+str(file))
    verify_saved()
    run = str(time.time_ns())+'-'+str(os.getpid())
    saved = PROJECT/'Saved/T1Traversal'/run
    output = DIRECTORY/'traversal'/run
    output.mkdir(parents=True); saved.mkdir(parents=True)
    results = []
    tools = ['scripts/unreal/run-t1-traversal.py', 'scripts/unreal/t1_traversal.py',
             'unreal/AegisWar/Source/AegisWar/Private/WarT1TraversalProof.cpp',
             'unreal/AegisWar/Source/AegisWar/Public/WarT1TraversalProof.h',
             'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWar.dll']
    if args.candidate == 'atmosphere':
        tools += ['unreal/AegisWar/Source/AegisWar/Private/WarRegionalAtmosphere.cpp',
                  'unreal/AegisWar/Source/AegisWar/Private/WarRegionalAtmosphereRules.cpp',
                  'unreal/AegisWar/Source/AegisWar/Public/WarRegionalAtmosphere.h']
    tool_hashes = {file: sha(ROOT/file) for file in tools}
    for zone in receipt['zones']:
        if args.zone and zone['id'] != args.zone:
            continue
        source_file = DIRECTORY/(zone['id']+'.json')
        if sha(source_file) != plan['candidateHashes'][zone['id']]:
            raise RuntimeError('Candidate authoring input changed')
        config = traversal_config(receipt, zone, json.loads(source_file.read_text()), args.headless)
        (saved/(zone['id']+'.json')).write_text(json.dumps(config, indent=2)+'\n')
        common = [str(ENGINE), str(PROJECT/'AegisWar.uproject'), zone['map']+'?game=/Script/AegisWar.WarT1TraversalGameMode',
                  '-unattended', '-nop4', '-nosplash', '-nosound', '-stdout', '-FullStdOutLogOutput',
                  '-WarDevelopmentNetworking', '-WarT1TraversalProof', '-WarT1TraversalConfig='+run+'/'+zone['id']+'.json',
                  '-abslog='+str(output/(zone['id']+'.log'))]
        mode = ['-server', '-nullrhi', '-benchmark', '-fps=60', '-MULTIHOME=127.0.0.1', '-port=0'] if args.headless else [
            '-game', '-RenderOffscreen', '-NoTextureStreaming', '-windowed', '-ResX=1280', '-ResY=800', '-ExecCmds=t.MaxFPS 60']
        print('Starting '+zone['id']+' '+str(len(config['routes']))+' native walking routes', flush=True)
        try:
            with (output/(zone['id']+'-stdout.log')).open('w') as log:
                process = subprocess.run(common+mode, stdout=log, stderr=subprocess.STDOUT, timeout=1200,
                                         creationflags=0x08000000 if os.name == 'nt' else 0)
        finally:
            verify_saved()
        report_file = saved/zone['id']/'report.json'
        report = json.loads(report_file.read_text(encoding='utf-8-sig'))
        for file, digest in tool_hashes.items():
            if sha(ROOT/file) != digest:
                raise RuntimeError('Traversal implementation changed during the run')
        shutil.copy2(report_file, output/(zone['id']+'-report.json'))
        if process.returncode != 0:
            raise RuntimeError('Native traversal failed: '+report.get('detail', 'missing detail')+'; '+str(output))
        validate_traversal(report, config)
        if args.candidate == 'atmosphere' and not args.headless:
            from t1_atmosphere import validate_live_atmosphere
            validate_live_atmosphere(report, config)
        if not args.headless:
            images = list((saved/zone['id']).glob('*.png'))
            expected = sum(p.get('capture', False) for r in config['routes'] for p in r['points'])
            if len(images) != expected or any(f.stat().st_size < 10000 for f in images):
                raise RuntimeError('Fresh live gameplay-camera images incomplete')
            for file in images:
                shutil.copy2(file, output/file.name)
        results.append(report)
        print('WAR_T1_WALK_VERIFIED '+zone['id']+' routes='+str(report['routesCompleted']), flush=True)
    summary = dict(signature=receipt['signature'], candidate=args.candidate, headless=args.headless, output=output.relative_to(ROOT).as_posix(), zones=results,
                   toolHashes=tool_hashes, ownerDocumentsPreserved=len(owner_files),
                   savedPackagesVerified=len(baseline), savedCandidatesUnchanged=True, visualApproved=False, drivingAccepted=False,
                   cameraAccepted=False, gameplayAccepted=False)
    (output/'summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    prefix = dict(homes='', materials='material-', atmosphere='atmosphere-')[args.candidate]
    (DIRECTORY/(prefix+('traversal-headless-latest.json' if args.headless else 'traversal-camera-latest.json'))).write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(dict(nativeWalkingPassed=True, output=str(output), routes=sum(r['routesCompleted'] for r in results))), flush=True)


if __name__ == '__main__':
    main()

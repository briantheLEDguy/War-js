"""Verify saved walkthrough/source bytes, then launch ordinary local play or its recovery proof."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import uuid
from t1_review import launch_arguments, ZONES

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT/'unreal/AegisWar'
DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
ENGINE = Path('C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zone',choices=ZONES,default='sunmeadow_march')
    parser.add_argument('--proof',action='store_true')
    args = parser.parse_args()
    receipt = json.loads((DIRECTORY/'review-latest.json').read_text(encoding='utf-8-sig'))
    baseline = {PROJECT/'Content'/(p.removeprefix('/Game/')+'.umap'):h
                for p,h in {**receipt['sourcePackageHashes'],**receipt['packageHashes']}.items()}
    baseline.update({ROOT/p:h for p,h in receipt['sourceFileHashes'].items()})
    baseline.update({ROOT/p:h for p,h in receipt['inputs']['tools'].items()})
    owner = PROJECT/'Saved/WorldEdit'; owner_files = set(owner.rglob('*.json'))
    baseline.update({p:sha(p) for p in owner_files})
    def verify():
        for file,digest in baseline.items():
            if sha(file) != digest: raise RuntimeError('Preserve changed saved dependency: '+str(file))
        if set(owner.rglob('*.json')) != owner_files: raise RuntimeError('Owner draft inventory changed')
    verify()
    invocation = launch_arguments(PROJECT/'AegisWar.uproject',receipt,args.zone)
    run = uuid.uuid4().hex
    output = DIRECTORY/'interactive'/run; output.mkdir(parents=True)
    invocation += ['-abslog='+str(output/'native.log')]
    if args.proof:
        invocation += ['-WarT1ReviewProof','-WarT1ReviewRun='+run,'-RenderOffscreen','-NoTextureStreaming']
        completed = subprocess.run([str(ENGINE),*invocation],cwd=PROJECT,timeout=150,creationflags=0x08000000)
        verify()
        report_file = PROJECT/'Saved/T1ReviewProof'/run/'report.json'
        report = json.loads(report_file.read_text(encoding='utf-8-sig'))
        if completed.returncode or not report.get('passed') or report['map'] != invocation[1]:
            raise RuntimeError('Ordinary entry/GM recovery proof failed: '+str(report))
        (output/'report.json').write_text(json.dumps(dict(**report,signature=receipt['signature'],
             savedBindingsVerified=len(baseline),ownerDocumentsPreserved=len(owner_files)),indent=2)+'\n')
        image = PROJECT/'Saved/T1ReviewProof'/run/'grounded.png'
        if not image.is_file() or image.stat().st_size < 10000: raise RuntimeError('Grounded gameplay capture is missing')
        (output/'grounded.png').write_bytes(image.read_bytes())
        print(json.dumps(dict(passed=True,zone=args.zone,output=str(output),ordinaryEntryAndGmVerified=True)))
    else:
        process = subprocess.Popen([str(ENGINE),*invocation],cwd=PROJECT)
        print(json.dumps(dict(launched=True,pid=process.pid,map=invocation[1],gmFlag=True,output=str(output))))


if __name__ == '__main__': main()

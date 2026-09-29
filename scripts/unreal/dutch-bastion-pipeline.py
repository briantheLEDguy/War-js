"""Run the isolated Dutch Bastion prototype without changing live map routing."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import shutil
from dutch_bastion import ROOT, OUT


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('plan','geometry','baseline','assets','pilot','render','proof-config','proof','survey','city-survey','city-assets','city-build','city-proof-config','city-review-config','city-detail-config','city-collision-survey','city-performance-config','city-baseline-config','city-proof','city-route-survey','city-world','city-apply'))
    args=parser.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env['WAR_DUTCH_STAGE']=args.stage
    if args.stage in ('plan','geometry'):
        script='dutch_bastion.py' if args.stage=='plan' else 'dutch_architecture.py'
        command=[sys.executable,str(Path(__file__).with_name(script))]
    elif args.stage in ('proof','city-proof'):
        import json
        current=json.loads((OUT/('city-current.json' if args.stage=='city-proof' else 'current.json')).read_text())
        config_path=ROOT/'unreal/AegisWar/Content/Migration/dutch-bastion-proof.json'
        expected=config_path.read_bytes();config=json.loads(expected)
        if config.get('scope') not in ('whole_city','city_quick','city_details','performance_city','performance_baseline') and args.stage=='city-proof':
            raise RuntimeError('Unknown city evidence scope')
        performance=config.get('scope','').startswith('performance_')
        if config['map']!=current['map'] and not (performance and config['map'].endswith('/Baseline_Comparison')):
            raise RuntimeError('Prepare proof-config for the current revision first')
        saved=ROOT/'unreal/AegisWar/Saved/DutchBastion'
        if (saved/'report.json').exists():
            history=OUT/'proof-history'/str(time.time_ns())
            shutil.copytree(saved,history)
        engine=env.get('WAR_UNREAL_EDITOR','C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
        command=[engine,str(ROOT/'unreal/AegisWar/AegisWar.uproject'),config['map'],'-game','-WarDevelopmentGM',
            '-WarDutchBastionProof','-RenderOffscreen','-windowed','-ForceRes','-ResX=1600','-ResY=1000',
            '-unattended','-nosplash','-nosound','-ExecCmds=t.MaxFPS '+('0' if performance else '60')+',r.VSync 0','-abslog='+str(OUT/'proof.log')]
    else:
        engine=env.get('WAR_UNREAL_EDITOR','C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe')
        command=[engine,str(ROOT/'unreal/AegisWar/AegisWar.uproject'),'-unattended','-nosplash','-nosound',
            '-AllowCommandletRendering' if args.stage=='render' else '-nullrhi','-run=pythonscript',
            '-script='+str(Path(__file__).with_name('native-dutch-city.py' if args.stage.startswith('city-') else 'native-dutch-bastion.py').resolve()),'-abslog='+str(OUT/(args.stage+'.log'))]
    with (OUT/(args.stage+'-console.log')).open('w') as stream:
        started=time.time_ns()
        result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,
                              timeout=2400 if args.stage.startswith('city-') else 600,
                              creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if result.returncode: raise SystemExit(f'{args.stage} failed: {OUT/(args.stage+"-console.log")}')
    if args.stage in ('proof','city-proof'):
        report_path=saved/'report.json'
        if not report_path.exists() or report_path.stat().st_mtime_ns<started:
            raise RuntimeError('Fresh native proof report missing')
        report=json.loads(report_path.read_text(encoding='utf-8-sig'))
        destination=OUT/current['revision']/('game-proof' if config.get('scope')=='whole_city' or args.stage=='proof' else config['scope'])
        shutil.copytree(saved,destination,dirs_exist_ok=True)
        (destination/'config.json').write_bytes(expected)
        if (config_path.read_bytes()!=expected or not report['passed'] or report['map']!=config['map']
                or report['signature']!=config['signature'] or report['views']!=len(config['views'])
                or report['routesWalked']!=len(config['routes'])):
            raise RuntimeError('Native proof did not verify this exact revision')
    print('Completed Dutch Bastion stage: '+args.stage)


if __name__=='__main__': main()

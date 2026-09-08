"""Render a source-fit diagnostic without rewriting masters or export reports."""
import argparse
from pathlib import Path
import sys
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
import build_collection as build

parser=argparse.ArgumentParser();parser.add_argument('--assets',default=','.join(build.SOURCE['assets']))
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
for asset in args.assets.split(','):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    collection,objects=build.setup_asset(asset,0)
    build.set_view(objects,build.ROOT/'review'/f'{asset}_fit_diagnostic.png')
    print('FIT_DIAGNOSTIC '+asset,flush=True)

"""Process-local first-pair walkthrough identity and terrain-aware arrival contract."""
import math
import re

ZONES = ('sunmeadow_march', 'cinderfen_outskirts')
PATTERN = re.compile(r'^/Game/WorldRebuild/T1HumanReview_([a-f0-9]{12})/(sunmeadow_march|cinderfen_outskirts)/Walkthrough$')


def review_map(signature, zone):
    if not re.fullmatch(r'[a-f0-9]{64}', signature) or zone not in ZONES:
        raise ValueError('Walkthrough requires an exact first-pair signature and zone')
    return '/Game/WorldRebuild/T1HumanReview_'+signature[:12]+'/'+zone+'/Walkthrough'


def arrival_point(source):
    if source.get('id') not in ZONES:
        raise ValueError('Arrival must use the admitted first pair')
    p = source['spawnPoint']
    point = [p['z']*100, p['x']*100, p['y']*100]
    if not all(math.isfinite(n) and abs(n) <= 300000 for n in point):
        raise ValueError('Arrival coordinates are not finite or bounded')
    return point


def launch_arguments(project, receipt, zone):
    if (receipt.get('schemaVersion') != 1 or receipt.get('sourcePackagesUnchanged') is not True
            or receipt.get('requiresDevelopmentGM') is not True or receipt.get('published') is not False):
        raise ValueError('Walkthrough requires preserved, private development evidence')
    rows = [r for r in receipt['zones'] if r['id'] == zone]
    if len(rows) != 1:
        raise ValueError('Walkthrough zone must be unique')
    row = rows[0]
    if (row['map'] != review_map(receipt['signature'], zone)
            or not row.get('nativeArrivalClear') or not row.get('parentContentUnchanged')
            or row['map'] not in receipt['packageHashes']):
        raise ValueError('Walkthrough needs the matching collision-verified private map')
    selected = '-ini:Engine:[/Script/EngineSettings.GameMapsSettings]:GameDefaultMap='+row['map']
    return [str(project), row['map'], '-game', '-WarDevelopmentGM', selected,
            '-windowed', '-ResX=1600', '-ResY=900', '-nosplash', '-nop4']

"""Record local traversal evidence only when it covers the current saved main world."""
import hashlib
import json
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
directory=ROOT/'artifacts/unreal/world-portals'
receipt=json.loads((directory/'build.json').read_text())
report_file=ROOT/'unreal/AegisWar/Saved/PortalProof/report.json'
report=json.loads(report_file.read_text())
log_file=directory/'traversal-main.log'
routes=re.findall(r'WAR_PORTAL_ROUTE_PASSED=([^\s]+)',log_file.read_text(errors='replace'))
resources=re.findall(r'WAR_WORLD_RESOURCE_PASSED=([^\s]+)',log_file.read_text(errors='replace'))
capital = json.loads((ROOT/'unreal/AegisWar/Content/Migration/capital-development.json').read_text())
expected_resources = [row['id'] for row in receipt.get('resources',[])]+[row['id'] for row in capital['gameplay']['resources']]
if report.get('resourcesGathered')!=len(expected_resources) or sorted(resources)!=sorted(expected_resources):
    raise RuntimeError('Every installed resource site must pass native gathering and cooldown checks')
if report.get('fullInventory') is not True or 'WAR_FULL_INVENTORY_RESOURCE_PASSED=sunmeadow_march_' not in log_file.read_text(errors='replace'):
    raise RuntimeError('A first-pair resource must reject full inventory without changing inventory, XP or cooldowns')
if not receipt['attached'] or report.get('passed') is not True or report.get('routesTraversed')!=70 or sorted(routes)!=sorted(receipt['portals']):
    raise RuntimeError('All 70 routes and respawn must pass in the attached main world')
if report.get('gmDraftAndHistory') is not True or 'WAR_GM_TRAVEL_HISTORY_PASSED' not in log_file.read_text(errors='replace'):
    raise RuntimeError('GM draft, actor state and undo/redo must survive zone streaming and respawn')
files=[ROOT/'unreal/AegisWar/Content'/(receipt[key].removeprefix('/Game/')+'.umap') for key in ('map','layer')]
manifest = None
if receipt.get('partitionManifest'):
    manifest = json.loads((directory/receipt['partitionManifest']).read_text())
    if manifest['layer'] != receipt['layer'] or report.get('deferredRoutes', 0) < 1 or report.get('streamingChecks') != 2:
        raise RuntimeError('Partitioned travel requires fresh asynchronous loading, failure and cancellation evidence')
    if 'WAR_STREAMING_FAILURE_AND_CANCEL_PASSED' not in log_file.read_text(errors='replace'):
        raise RuntimeError('Streaming failure/cancellation scenarios did not run')
    if manifest.get('capitalExtraction') and 'WAR_GM_CAPITAL_UNLOADED_HISTORY_PASSED' not in log_file.read_text(errors='replace'):
        raise RuntimeError('The extracted capital must unload while GM history survives')
    files.extend(ROOT/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')
                 for zone in manifest['zones'] for package in zone['levels'].values())
if any(file.stat().st_mtime>=log_file.stat().st_mtime or file.stat().st_mtime>=report_file.stat().st_mtime for file in files):
    raise RuntimeError('Saved world is newer than the traversal evidence')
result={'map':receipt['map'],'layer':receipt['layer'],'zones':len(receipt['zones']),'routesTraversed':70,'gmDraftAndHistory':True,
    'zoneLocalRespawn':True,'resourcesGathered':len(resources),'resourceNodes':sorted(resources),'fullInventory':True,
    'sceneryPlacements':len(receipt['scenery']),'gameplayPlacements':len(receipt['gameplay']),
    'pendingScenery':len(receipt['pendingScenery']),'pendingGameplay':len(receipt['pendingGameplay']),
    'packageHashes':{file.relative_to(ROOT/'unreal/AegisWar/Content').as_posix():hashlib.sha256(file.read_bytes()).hexdigest() for file in files},
    'proofLogSha256':hashlib.sha256(log_file.read_bytes()).hexdigest(),'networkAccepted':False,'visualApproved':False}
(directory/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
receipt['runtimeTraversalVerified']=True
(directory/'build.json').write_text(json.dumps(receipt,indent=2)+'\n')
if manifest:
    for zone in manifest['zones']: zone['acceptance']['traversal'] = 'development-verified'
    manifest['traversalEvidence'] = {'routes':70, 'deferredRoutes':report['deferredRoutes'], 'failureAndCancellation':True,
                                    'proofLogSha256':result['proofLogSha256'], 'packageHashes':result['packageHashes']}
    (directory/receipt['partitionManifest']).write_text(json.dumps(manifest,indent=2)+'\n')
print(json.dumps(result))

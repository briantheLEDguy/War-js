"""Record exact existing anatomy inputs without copying historical release trees."""
import hashlib,json
from pathlib import Path
WORK=Path(__file__).resolve().parents[1];ROOT=WORK.parents[2]
UPSTREAM=WORK.parent/'frontier-population';FOUNDATIONS=UPSTREAM/'foundations'
def record(path):
    data=path.read_bytes();return {'path':path.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
upstream=json.loads((UPSTREAM/'foundation-provenance.json').read_text())
names=['body_mire_brutish_v1_m.glb','body_mire_brutish_v1_m.qc.json','mire_brutish_v1_m.source.blend','mire_brutish_v1_m.quad-surface.json.gz']
report={'schemaVersion':1,'description':'Existing retained original Greenskin anatomy and weights; source GLB image bytes are packed into the editable derivative master. No historical release tree is copied.',
 'license':upstream['license'],'upstreamProvenance':record(UPSTREAM/'foundation-provenance.json'),'inputs':[record(FOUNDATIONS/name) for name in names],
 'derivative':'Broad jaw/muzzle, low brow, pointed ears, rooted curved tusks, complete original wet-work clothing and equipment, and character-specific contact fitting.'}
(WORK/'foundation-provenance.json').write_text(json.dumps(report,indent=2)+'\n')

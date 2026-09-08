"""Retain the exact reviewed-kit inputs for the independent corner addition."""
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
archive=ROOT/'source/pipeline-references';archive.mkdir(parents=True,exist_ok=True)
references=[]
for name in ('build_architecture.py','share_textures.py','review_exports.py','audit_geometry.py','validate_architecture.mjs','contact_sheet.py','test_blueprints.mjs','test_published.mjs'):
    original=ROOT.parent/'tools'/name;target=archive/(sha(original)+'_'+name);shutil.copyfile(original,target)
    references.append({'utility':name,'origin':'../tools/'+name,'sha256':sha(original),'retained_copy':str(target.relative_to(ROOT)).replace('\\','/'),'reuse_scope':'Export and review mechanics reused from the seven-piece Cinderfen kit.'})
original=ROOT.parent/'source/architecture.json';target=archive/(sha(original)+'_reviewed_kit.json');shutil.copyfile(original,target)
references.append({'utility':'reviewed Cinderfen cage library','origin':'../source/architecture.json','sha256':sha(original),'retained_copy':str(target.relative_to(ROOT)).replace('\\','/'),'reuse_scope':'Original Cinderfen authored stone, alder and hardware, fitted around a new pentagonal deck and real diagonal stair opening.'})
record={'source_sha256':sha(ROOT/'source/architecture.json'),'authoring_method':'Original closed pentagonal deck contours and finite fitted construction placements; shared authored Cinderfen construction cages and material fields, with retained exact references.','tools':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sorted((ROOT/'tools').iterdir()) if p.suffix in ('.py','.mjs')},'pipeline_references':references,'approval':'Provenance only. Actual GLB review is independently required.'}
(ROOT/'source/source-provenance.json').write_text(json.dumps(record,indent=2)+'\n')
print('Corner provenance frozen.')

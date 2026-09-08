"""Freeze exact authoring/export tool inputs without granting art approval."""
import hashlib
import json
from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[2]

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if __name__=='__main__':
    utilities=['build_architecture.py','share_textures.py','review_exports.py','audit_geometry.py','validate_architecture.mjs','contact_sheet.py','test_blueprints.mjs','test_published.mjs']
    references=[];archive=ROOT/'source/pipeline-references';archive.mkdir(parents=True,exist_ok=True)
    for name in utilities:
        source=ROOT.parent/'sunmeadow-architecture/tools'/name;digest=sha(source);target=archive/(digest+'_'+name);shutil.copyfile(source,target)
        references.append({'utility':name,'origin':str(source.relative_to(REPO)).replace('\\','/'),'sha256':digest,'retained_copy':str(target.relative_to(ROOT)).replace('\\','/'),'reuse_scope':'Finishing, export, inspection and publication mechanics only; no geometry or painted pixels.'})
    tools={str(path.relative_to(ROOT)).replace('\\','/'):sha(path) for path in sorted((ROOT/'tools').iterdir()) if path.suffix in ('.py','.mjs')}
    record={'source_sha256':sha(ROOT/'source/architecture.json'),'authoring_method':'Original literal Cinderfen construction cages, explicit fitted roof deformation records, finite structural placements and independently painted PBR channels. No stock primitive constructors or Sunmeadow mesh/pixel reuse.','tools':tools,'pipeline_references':references,'source_tests':'tools/test_source.py checks all Python tools for primitive constructors, all closed cages/UVs and no exact Sunmeadow cage reuse.','approval':'This record is provenance only; visual acceptance is separately bound to actual GLB reimport images.'}
    (ROOT/'source/source-provenance.json').write_text(json.dumps(record,indent=2)+'\n')
    print(f'Recorded {len(tools)} exact tool hashes and {len(references)} retained utility references.')

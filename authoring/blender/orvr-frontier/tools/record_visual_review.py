"""Record the explicitly completed 2026-09-07 review, without publishing art.

The observation table is a manual review record, not a validation inference.
Re-running it does not inspect new art or grant approval to changed hashes.
"""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEWED_INVENTORY_SHA256='cb25939fe35f86a1de9423599063765b5c97d7d9d6e1d9694e78b4a4a020796f'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

OBSERVATIONS={
 'frontier_supply_wagon':['Canvas bindings, ties, bench, footboard and wheel curvature retain their construction across LODs.','Literal equipped driver, horse, shafts and reins were inspected together; the final palms close around the reins.'],
 'frontier_battering_ram':['Hide bindings and suspension remain connected in the exported strike sequence.','Finished LOD2 preserves curved tires and eliminates the previous coarse normal discontinuities.'],
 'frontier_oil_cauldron':['Open bowl and pour lip retain depth; the lever tips with the bowl while wall brackets stay fixed.','LOD2 has a visibly simpler rim, appropriate to distance use; use LOD0 for close parapet inspection.'],
 'frontier_field_catapult':['Fire and reload poses retain the arm, drum, ratchet and following haul rope.','Default rest is vertical; the ready state must initialize fire at time zero. Projectile effects are external.'],
 'frontier_keep_gate':['Both leaves pivot from their outer hinges through open and close; ironwork remains attached.','This generic gate is separate from the already published Sunmeadow gate leaves.'],
 'frontier_draft_horse':['Literal close head, side anatomy, collar/harness and trot-side views were inspected.','Connected shoulder and haunch skin retains volume in the sampled walk/trot poses without the rejected trial tears.','The coat remains stylized and smooth. It is not photorealistic fur; benchmark acceptance remains the main integration review.'],
 'frontier_caravan_reins':['All LODs retain the leather paths and bit; final assembled reins meet closed palms and the horse mouth.','Loose static leather is fitted to this assembly, not arbitrary animal sizes or extreme head motions.'],
 'frontier_supply_officer_kit':['The exported fastening strap is continuous; feather overlap and floating corner-patch defects from the first trials are corrected.','The literal published armored body was inspected with the fitted pouch. The supplied matrix applies only to that body/armor profile.'],
}


def main():
    if sha(ROOT/'review/final_inventory.json')!=REVIEWED_INVENTORY_SHA256:
        raise ValueError('This review was written for different hashes. Inspect the new exports and write a new review.')
    inventory=json.loads((ROOT/'review/final_inventory.json').read_text());records=[]
    for asset in inventory['assets']:
        key=asset['asset_id']
        for lod in asset['lods']:
            if sha(ROOT/lod['model'])!=lod['sha256'] or sha(ROOT/lod['image'])!=lod['image_sha256']:
                raise ValueError('The manually inspected review inventory is stale')
        records.append({'asset_id':key,'lods':asset['lods'],'observations':OBSERVATIONS[key]})
    result={'reviewer':'Codex frontier authoring agent','review_date':'2026-09-07',
      'decision':'ready_for_main_integration_review','visual_approval':False,
      'inspection':'All 24 current static renders inspected in the hash-verified sheet, individual full-size material views, eight actual clip sheets, horse close/side anatomy, literal equipped caravan and officer fits.',
      'benchmark_status':'The main task owns final benchmark acceptance and registry promotion. No asset was approved by passing a technical validator.',
      'assets':records,'assembly_reviews':['review/frontier_caravan_assembly.json','review/frontier_supply_officer_fit.json','review/frontier_draft_horse_details.json'],
      'technical_checks':{'focused_tests':11,'glb_files':25,'gltf_errors':0,'gltf_warnings':6,'warning_explanation':'Two NODE_SKINNED_MESH_NON_ROOT warnings in each horse LOD; retained identity parent, actual poses inspected.'}}
    (ROOT/'review/visual_observations.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main()

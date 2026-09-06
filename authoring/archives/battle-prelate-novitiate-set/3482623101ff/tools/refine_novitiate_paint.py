"""Place finite, hand-drawn paint patches; replay with paint_materials.py.

All paths, offsets and colors below are literal authored data. Copying these
small drawings is intentional texture brush stamping, not generated noise or
geometry. The expanded paint_strokes.json remains independently inspectable.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "textures/paint_strokes.json"

# One 128px cloth brush: slightly uneven, interrupted yarn marks. These are
# relief/color marks, never painted directional lighting or cast shadows.
WARP = [
    [(2,0),(3,33),(2,69),(2,127)], [(6,0),(6,48),(7,85),(6,127)],
    [(10,0),(11,35),(10,74),(11,127)], [(14,0),(14,54),(15,94),(14,127)],
    [(18,0),(19,27),(18,83),(18,127)], [(22,0),(22,44),(23,77),(22,127)],
    [(26,0),(27,57),(26,98),(27,127)], [(30,0),(30,31),(31,66),(30,127)],
    [(34,0),(35,42),(34,87),(34,127)], [(38,0),(38,51),(39,92),(38,127)],
    [(42,0),(43,37),(42,79),(43,127)], [(46,0),(46,62),(47,101),(46,127)],
    [(50,0),(51,29),(50,72),(50,127)], [(54,0),(54,43),(55,84),(54,127)],
    [(58,0),(59,56),(58,97),(59,127)], [(62,0),(62,33),(63,75),(62,127)],
    [(66,0),(67,45),(66,88),(66,127)], [(70,0),(70,58),(71,104),(70,127)],
    [(74,0),(75,31),(74,82),(75,127)], [(78,0),(78,49),(79,93),(78,127)],
    [(82,0),(83,39),(82,78),(82,127)], [(86,0),(86,63),(87,101),(86,127)],
    [(90,0),(91,28),(90,70),(91,127)], [(94,0),(94,47),(95,86),(94,127)],
    [(98,0),(99,54),(98,96),(98,127)], [(102,0),(102,36),(103,81),(102,127)],
    [(106,0),(107,46),(106,89),(107,127)], [(110,0),(110,61),(111,103),(110,127)],
    [(114,0),(115,32),(114,76),(114,127)], [(118,0),(118,50),(119,91),(118,127)],
    [(122,0),(123,41),(122,85),(123,127)], [(126,0),(126,57),(127,98),(126,127)],
]
WEFT = [
    [(0,2),(29,3),(65,2),(127,2)], [(0,6),(47,6),(88,7),(127,6)],
    [(0,10),(32,11),(77,10),(127,11)], [(0,14),(55,14),(94,15),(127,14)],
    [(0,18),(24,19),(68,18),(127,18)], [(0,22),(42,22),(86,23),(127,22)],
    [(0,26),(58,27),(101,26),(127,27)], [(0,30),(36,30),(72,31),(127,30)],
    [(0,34),(46,35),(87,34),(127,34)], [(0,38),(53,38),(98,39),(127,38)],
    [(0,42),(28,43),(79,42),(127,43)], [(0,46),(61,46),(105,47),(127,46)],
    [(0,50),(37,51),(76,50),(127,50)], [(0,54),(49,54),(91,55),(127,54)],
    [(0,58),(57,59),(96,58),(127,59)], [(0,62),(31,62),(73,63),(127,62)],
    [(0,66),(44,67),(89,66),(127,66)], [(0,70),(63,70),(102,71),(127,70)],
    [(0,74),(34,75),(82,74),(127,75)], [(0,78),(51,78),(93,79),(127,78)],
    [(0,82),(40,83),(78,82),(127,82)], [(0,86),(59,86),(104,87),(127,86)],
    [(0,90),(27,91),(71,90),(127,91)], [(0,94),(48,94),(88,95),(127,94)],
    [(0,98),(56,99),(97,98),(127,98)], [(0,102),(35,102),(81,103),(127,102)],
    [(0,106),(45,107),(90,106),(127,107)], [(0,110),(62,110),(106,111),(127,110)],
    [(0,114),(33,115),(75,114),(127,114)], [(0,118),(50,118),(92,119),(127,118)],
    [(0,122),(41,123),(84,122),(127,123)], [(0,126),(60,126),(99,127),(127,126)],
]
CLOTH_PLACEMENTS = [
    (0,0),(128,0),(256,0),(384,0),(512,0),(640,0),(768,0),(896,0),
    (0,128),(128,128),(256,128),(384,128),(512,128),(640,128),(768,128),(896,128),
    (0,256),(128,256),(256,256),(384,256),(512,256),(640,256),(768,256),(896,256),
    (0,384),(128,384),(256,384),(384,384),(512,384),(640,384),(768,384),(896,384),
    (0,512),(128,512),(256,512),(384,512),(512,512),(640,512),(768,512),(896,512),
    (0,640),(128,640),(256,640),(384,640),(512,640),(640,640),(768,640),(896,640),
    (0,768),(128,768),(256,768),(384,768),(512,768),(640,768),(768,768),(896,768),
    (0,896),(128,896),(256,896),(384,896),(512,896),(640,896),(768,896),(896,896),
]
LEATHER_GRAIN = [
    [(7,13),(12,11),(16,14)],[(23,18),(28,16),(31,19)],[(46,9),(51,12),(55,11)],
    [(69,22),(73,19),(79,21)],[(92,12),(96,16),(102,15)],[(119,25),(125,23),(128,26)],
    [(148,10),(152,13),(157,11)],[(177,20),(183,18),(187,21)],[(208,11),(212,15),(217,14)],
    [(234,25),(240,22),(244,26)],[(15,49),(20,47),(24,51)],[(41,40),(47,43),(52,41)],
    [(74,54),(80,51),(85,55)],[(107,42),(111,46),(117,44)],[(137,59),(142,56),(147,60)],
    [(167,42),(173,46),(178,43)],[(198,58),(204,54),(210,57)],[(231,44),(237,48),(242,46)],
    [(7,83),(13,79),(18,82)],[(35,73),(41,77),(47,75)],[(67,89),(72,85),(78,88)],
    [(96,75),(101,78),(107,76)],[(126,94),(133,90),(138,93)],[(156,76),(161,80),(167,78)],
    [(188,95),(195,91),(201,94)],[(224,82),(229,86),(236,83)],[(20,118),(27,114),(31,118)],
    [(53,107),(57,112),(64,110)],[(84,123),(91,120),(96,124)],[(118,108),(123,113),(129,110)],
    [(149,124),(155,120),(162,123)],[(181,109),(187,114),(194,111)],[(215,122),(222,118),(229,122)],
    [(8,150),(15,147),(20,151)],[(38,138),(44,142),(50,140)],[(71,158),(77,154),(84,157)],
    [(104,142),(110,147),(116,144)],[(136,160),(142,157),(149,161)],[(172,143),(178,149),(184,146)],
    [(202,163),(208,159),(215,162)],[(234,148),(240,153),(246,150)],[(19,187),(25,183),(30,187)],
    [(51,175),(57,180),(63,177)],[(84,192),(91,188),(97,191)],[(118,178),(124,184),(130,180)],
    [(151,195),(158,191),(164,194)],[(184,179),(190,184),(196,182)],[(220,195),(227,190),(232,194)],
    [(8,222),(14,217),(21,220)],[(41,211),(47,216),(54,213)],[(76,232),(82,227),(89,231)],
    [(109,213),(115,218),(122,215)],[(143,235),(151,230),(157,234)],[(178,216),(184,222),(191,218)],
    [(212,238),(219,233),(225,237)],[(239,216),(245,222),(251,219)],
]
LEATHER_PLACEMENTS = [
    (0,0),(256,0),(512,0),(768,0),(0,256),(256,256),(512,256),(768,256),
    (0,512),(256,512),(512,512),(768,512),(0,768),(256,768),(512,768),(768,768),
]
HEM_DASH = [[(0,0),(5,0),(9,1)]]
HEM_PLACEMENTS = [
    (31,952),(49,951),(67,952),(85,951),(103,952),(121,952),(139,951),(157,952),
    (175,951),(193,952),(211,952),(229,951),(247,952),(265,951),(283,952),(301,952),
    (319,951),(337,952),(355,951),(373,952),(391,952),(409,951),(427,952),(445,951),
    (463,952),(481,952),(499,951),(517,952),(535,951),(553,952),(571,952),(589,951),
    (607,952),(625,951),(643,952),(661,952),(679,951),(697,952),(715,951),(733,952),
    (751,952),(769,951),(787,952),(805,951),(823,952),(841,952),(859,951),(877,952),
    (895,951),(913,952),(931,952),(949,951),(967,952),(985,951),
]
SIDE_DASH = [[(0,0),(0,5),(1,9)]]
SIDE_PLACEMENTS = [
    (20,32),(20,50),(20,68),(20,86),(20,104),(20,122),(20,140),(20,158),
    (20,176),(20,194),(20,212),(20,230),(20,248),(20,266),(20,284),(20,302),
    (20,320),(20,338),(20,356),(20,374),(20,392),(20,410),(20,428),(20,446),
    (20,464),(20,482),(20,500),(20,518),(20,536),(20,554),(20,572),(20,590),
    (20,608),(20,626),(20,644),(20,662),(20,680),(20,698),(20,716),(20,734),
    (20,752),(20,770),(20,788),(20,806),(20,824),(20,842),(20,860),(20,878),
    (20,896),(20,914),(20,932),(1003,32),(1003,50),(1003,68),(1003,86),(1003,104),
    (1003,122),(1003,140),(1003,158),(1003,176),(1003,194),(1003,212),(1003,230),(1003,248),
    (1003,266),(1003,284),(1003,302),(1003,320),(1003,338),(1003,356),(1003,374),(1003,392),
    (1003,410),(1003,428),(1003,446),(1003,464),(1003,482),(1003,500),(1003,518),(1003,536),
    (1003,554),(1003,572),(1003,590),(1003,608),(1003,626),(1003,644),(1003,662),(1003,680),
    (1003,698),(1003,716),(1003,734),(1003,752),(1003,770),(1003,788),(1003,806),(1003,824),
    (1003,842),(1003,860),(1003,878),(1003,896),(1003,914),(1003,932),
]
HAMMER_MARKS = [
    (73,109),(131,194),(219,121),(315,217),(419,136),(514,232),(617,151),(704,218),
    (831,115),(929,201),(105,371),(206,433),(328,352),(448,458),(562,369),(681,444),
    (787,341),(913,417),(69,642),(183,724),(298,623),(404,711),(522,649),(643,729),
    (759,637),(883,711),(135,888),(263,931),(381,844),(493,926),(602,856),(717,935),(849,861),(960,917),
]
FIBER_SNAGS = [
    [(114,164),(112,151),(115,144)],[(117,158),(116,147)],[(319,289),(321,275),(320,269)],
    [(324,283),(324,273)],[(701,186),(699,174),(702,163)],[(705,181),(705,170)],
    [(831,475),(829,461),(832,452)],[(835,468),(835,458)],[(203,651),(201,639),(203,629)],
    [(207,644),(207,635)],[(586,724),(584,710),(587,701)],[(590,716),(590,706)],
    [(373,892),(371,880),(374,871)],[(377,887),(377,876)],[(911,844),(909,833),(912,823)],
    [(915,838),(915,828)],
]


def stamp(paths, placements):
    """Serialize copies at authored offsets; no placement or path synthesis."""
    return [[[x + dx, y + dy] for x, y in path] for dx, dy in placements for path in paths]


def main():
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    previous = record.get("novitiate_realism_pass", {}).get("before_record_sha256")
    previous = previous or hashlib.sha256(RECORD.read_bytes()).hexdigest()
    new_brushes = {
        "novitiate_warp_yarn": {"kind":"paths", "shapes":stamp(WARP,CLOTH_PLACEMENTS)},
        "novitiate_weft_yarn": {"kind":"paths", "shapes":stamp(WEFT,CLOTH_PLACEMENTS)},
        "novitiate_leather_grain": {"kind":"paths", "shapes":stamp(LEATHER_GRAIN,LEATHER_PLACEMENTS)},
        "novitiate_linen_hem": {"kind":"paths", "shapes":stamp(HEM_DASH,HEM_PLACEMENTS)},
        "novitiate_linen_side": {"kind":"paths", "shapes":stamp(SIDE_DASH,SIDE_PLACEMENTS)},
        "novitiate_fiber_snags": {"kind":"paths", "shapes":FIBER_SNAGS},
        "novitiate_hammered_variation": {"kind":"spots", "points":HAMMER_MARKS},
    }
    record["brushes"].update(new_brushes)
    materials=record["materials"]
    materials["steel"]["base"].update(basecolor=[105,115,122],roughness=134,metallic=247)
    materials["dark_steel"]["base"]["roughness"]=159
    materials["brass"]["base"]["roughness"]=157
    materials["leather"]["base"]["roughness"]=190
    edits={
        "cool_uneven_patina": {"paint":{"roughness":156}},
        "soft_hand_burnished_regions": {"opacity":24,"paint":{"basecolor":[131,140,145],"roughness":108}},
        "isolated_oxidation": {"opacity":40},
        "broad_faint_scuffs": {"opacity":43,"paint":{"basecolor":[140,148,151],"roughness":112}},
        "fine_etched_scratches": {"opacity":82,"paint":{"basecolor":[151,157,159],"roughness":105}},
        "short_crossed_impact_marks": {"opacity":67,"paint":{"basecolor":[142,151,154]}},
        "dark_burnished_wear": {"opacity":26},
        "dark_etched_scratches": {"opacity":78},
        "dark_oxidized_islands": {"opacity":43},
        "handled_leather_wear": {"opacity":67,"paint":{"roughness":148}},
        "small_leather_crease_marks": {"opacity":86},
    }
    for material in materials.values():
        material["layers"]=[layer for layer in material["layers"] if not layer["id"].startswith("novitiate_")]
        for layer in material["layers"]:
            change=edits.get(layer["id"],{})
            layer.update({k:v for k,v in change.items() if k!="paint"})
            layer["paint"].update(change.get("paint",{}))
    materials["steel"]["layers"].append({"id":"novitiate_subtle_hammer_work","brush":"novitiate_hammered_variation","radius":18,"opacity":52,"softness":9,"paint":{"roughness":164,"height":101}})
    materials["leather"]["layers"].append({"id":"novitiate_fine_leather_grain","brush":"novitiate_leather_grain","width":1,"opacity":91,"softness":.45,"paint":{"basecolor":[53,37,25],"roughness":211,"height":99}})
    materials["crimson"]["layers"].extend([
        {"id":"novitiate_raised_warp_yarn","brush":"novitiate_warp_yarn","width":1,"opacity":108,"softness":.25,"paint":{"basecolor":[108,65,48],"roughness":234,"height":171}},
        {"id":"novitiate_interwoven_weft","brush":"novitiate_weft_yarn","width":1,"opacity":101,"softness":.25,"paint":{"basecolor":[90,51,38],"roughness":239,"height":92}},
        {"id":"novitiate_small_fiber_snags","brush":"novitiate_fiber_snags","width":1,"opacity":106,"softness":.3,"paint":{"basecolor":[144,106,79],"roughness":239,"height":172}},
        {"id":"novitiate_linen_hem_stitches","brush":"novitiate_linen_hem","width":2,"opacity":162,"softness":.25,"paint":{"basecolor":[130,91,64],"roughness":236,"height":184}},
        {"id":"novitiate_linen_side_stitches","brush":"novitiate_linen_side","width":2,"opacity":148,"softness":.25,"paint":{"basecolor":[126,86,60],"roughness":236,"height":180}},
    ])
    record["novitiate_realism_pass"]={
        "revision":1,"before_record_sha256":previous,
        "authoring_tool":"tools/refine_novitiate_paint.py",
        "method":"Literal hand-drawn warp/weft and leather-grain patches copied to the finite listed pixel offsets; final JSON stores all expanded paths. Explicit individual hem dashes and hammered marks. No stochastic texture, geometry synthesis, reference highlights, or lighting painted into color.",
        "uv_convention":"1024px: front/rear bottom hem V=.07 maps to Y=951.4; side seam U=.02/.98 maps to X=20.46/1002.54. Two-pixel linen thread is tonal, not gold trim.",
        "scope":"Slight material response and surface detail pass. Russet base preserved. Existing skin/chainmail and shared runtime body/weapon are unchanged.",
        "visual_status":"Awaiting full source and baked runtime render review; no automatic visual acceptance.",
    }
    RECORD.write_text(json.dumps(record,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"record_sha256":hashlib.sha256(RECORD.read_bytes()).hexdigest(),"expanded_brush_paths":{key:len(value.get("shapes",value.get("points",[]))) for key,value in new_brushes.items()}},indent=2))


if __name__=="__main__":
    main()

"""The complete supplied animation contract; no legacy clip is a fallback."""
from pathlib import Path
import os
import json

ROOT = Path(__file__).resolve().parents[2]
ANIMATION_SET = os.environ.get('WAR_ANIMATION_SET', 'supplied-four')
if ANIMATION_SET not in ('supplied-four', 'siege-casters', 'capital-camps'):
    raise ValueError('Unknown animation set: '+ANIMATION_SET)
OUT = ROOT / ('artifacts/unreal/siege/animation' if ANIMATION_SET == 'siege-casters' else 'artifacts/unreal/animation-replacement')
if ANIMATION_SET == 'capital-camps': OUT = ROOT/'artifacts/unreal/imported-population'
SOURCE = ROOT / "unreal/AegisWar/AnimationImport"
def visual_path(profile):
    if ANIMATION_SET == 'capital-camps': return '/Game/Characters/PopulationImports/Visual_'+profile
    return ('/Game/Characters/SiegeStaging/Visual_' if ANIMATION_SET == 'siege-casters' else '/Game/MigrationProof/Visual_')+profile
CLIPS = {}
for style, folder, entries in [
    ("two", "Two-handed", {
        "idle":"Great Sword Idle", "walk":"Great Sword Walk forwards", "back":"Great Sword Walk backwards",
        "run":"Great Sword Run", "left":"Great Sword Strafe left", "right":"Great Sword Strafe right",
        "turn_left":"Great Sword Turn left", "turn_right":"Great Sword Turn right", "impact":"Great Sword Impact",
        "jump":"Great Sword Jump", "death":"Two Handed Sword Death", "slash":"Great Sword Slash",
        "slide":"Great Sword Slide Attack", "jump_attack":"Great Sword Jump Attack",
        "spin":"Great Sword High Spin Attack", "invocation":"Spell Cast one hand"}),
    ("shield", "swordandshield", {
        "walk":"Sword And Shield Walk forwards", "back":"Sword And Shield Walk backwards",
        "run":"Sword And Shield Run forwards", "left":"Sword And Shield Strafe left",
        "right":"Sword And Shield Strafe right", "turn_left":"Sword And Shield Turn left",
        "turn_right":"Sword And Shield Turn right", "impact":"Sword And Shield Impact",
        "jump":"Sword And Shield Jump", "death":"Sword And Shield Death", "slash":"Sword And Shield Attack",
        "combo":"Sword And Shield Double Slash and Ground hit", "kick":"Sword And Shield Kick",
        "block":"Sword And Shield Block", "power":"Sword And Shield Power Up"}),
    ("spell", "Spellcast", {
        "idle":"Standing Idle 03", "walk":"Standing Walk Forward", "run":"Standing Run Forward",
        "left":"Standing Walk Left", "right":"Standing Walk Right", "turn_left":"Standing Turn Left 90",
        "turn_right":"Standing Turn Right 90", "impact":"Standing React Small From Front",
        "impact_back":"Standing React Large From Back", "death":"Standing React Death Forward",
        "bolt":"Standing 1H Magic Attack 01", "focus":"Standing 2H Magic Attack 01",
        "ritual":"Standing 2H Magic Attack 03"})]:
    for key, filename in entries.items():
        CLIPS[f"{style}.{key}"] = f"{folder}/{filename}.fbx"

PROFILES = {
    "civic_battle_prelate_m": ("battle_prelate", "two"),
    "civic_sunfire_templar_m": ("sunfire_templar", "shield"),
    "mire_warbrute_m": ("warbrute", "shield"),
    "civic_ember_arcanist_m": ("ember_arcanist", "spell"),
}

def selected(profile):
    if ANIMATION_SET in ('siege-casters', 'capital-camps') and profile not in PROFILES: return False
    requested=os.environ.get('WAR_ANIMATION_PROFILE')
    if requested and requested not in PROFILES: raise ValueError('Unknown character recipe: '+requested)
    return not requested or requested==profile

# Anatomical chains are shared; bind units and equipment fitting are per rig.
CHAINS = [("Spine", "Spine", "Spine2", "spine", "upper_chest"),
          ("Head", "Neck", "Head", "neck", "head")]
for side, suffix in (("Left", "L"), ("Right", "R")):
    CHAINS.extend([
        (side+"Clavicle", side+"Shoulder", side+"Shoulder", "shoulder_"+suffix, "shoulder_"+suffix),
        (side+"Arm", side+"Arm", side+"Hand", "upper_arm_"+suffix, "hand_"+suffix),
        (side+"Leg", side+"UpLeg", side+"Foot", "thigh_"+suffix, "foot_"+suffix),
        (side+"Toe", side+"ToeBase", side+"ToeBase", "toe_"+suffix, "toe_"+suffix)])
    for finger in ("Thumb", "Index", "Middle", "Ring", "Pinky"):
        CHAINS.append((side+finger, side+"Hand"+finger+"1", side+"Hand"+finger+"3",
                       finger.lower()+"_01_"+suffix, finger.lower()+"_03_"+suffix))

# Each tuple is (ability suffix, sources, choreography, contact fraction,
# normalized hold, equipment state, capsule motion). Fractions are corrected
# against measured source contacts during the native authoring/verification pass.
RECIPES = {
    "battle_prelate": [
        ("litany_of_strikes", ["two.slash"], "combo", .55, 0, "drawn", "stationary"),
        ("sanctified_blow", ["two.slash"], "finisher", .60, .15, "drawn", "stationary"),
        ("martyr_s_ward", ["spell.focus"], "ward", .45, .2, "stowed", "stationary"),
        ("penance_step", ["two.slide"], "slide", .65, 0, "drawn", "slide"),
        ("hymn_of_resolve", ["spell.focus"], "channel", .35, .6, "stowed", "stationary"),
        ("reliquary_smash", ["two.jump_attack", "two.spin"], "smash", .7, 0, "drawn", "leap"),
        ("judgment_of_ash", ["spell.bolt"], "line", .5, .1, "stowed", "stationary"),
        ("redemption_surge", ["spell.ritual"], "heal", .55, .25, "stowed", "stationary"),
        ("icon_of_wrath", ["spell.ritual"], "place", .65, .35, "stowed", "stationary"),
        ("last_homily", ["spell.focus", "spell.ritual"], "sermon", .6, .5, "stowed", "stationary"),
    ],
    "sunfire_templar": [
        ("solar_edict", ["two.invocation"], "edict", .5, .15, "stowed", "stationary"),
        ("bastion_edict", ["shield.block"], "brace", .4, .3, "drawn", "stationary"),
        ("pursuit_edict", ["shield.power"], "rally", .45, .1, "drawn", "stationary"),
        ("sunbrand_strike", ["shield.slash"], "cut", .5, 0, "drawn", "stationary"),
        ("shield_of_noon", ["shield.block"], "guard", .35, .6, "drawn", "stationary"),
        ("rallying_rebuke", ["shield.kick"], "rebuke", .5, 0, "drawn", "stationary"),
        ("banner_rush", ["shield.block"], "charge", .65, 0, "drawn", "charge"),
        ("radiant_counter", ["shield.block", "shield.slash"], "counter", .65, 0, "drawn", "stationary"),
        ("heavenrend_sweep", ["shield.combo"], "cleave", .7, 0, "drawn", "leap"),
        ("daybreak_standard", ["spell.ritual"], "standard", .6, .4, "stowed", "stationary"),
    ],
    "warbrute": [
        ("sneaky_start", ["shield.slash"], "opener", .45, 0, "drawn", "stationary"),
        ("proper_wallop", ["shield.combo"], "combo", .55, 0, "drawn", "leap"),
        ("biggest_finish", ["shield.combo"], "finisher", .75, .15, "drawn", "leap"),
        ("shut_it", ["shield.block"], "bash", .5, 0, "drawn", "stationary"),
        ("get_stuck_in", ["shield.block"], "charge", .65, 0, "drawn", "charge"),
        ("wot_s_yours_is_mine", ["shield.kick"], "kick", .5, 0, "drawn", "stationary"),
        ("keep_smashin", ["shield.power"], "rage", .4, .15, "drawn", "stationary"),
        ("boss_stomp", ["shield.combo"], "ground", .8, 0, "drawn", "leap"),
        ("you_watch_me", ["shield.block"], "guard", .4, .5, "drawn", "stationary"),
        ("boss_s_big_idea", ["shield.power", "shield.combo"], "brawl", .65, .25, "drawn", "leap"),
    ],
    "ember_arcanist": [
        ("spark_lash", ["spell.bolt"], "bolt", .45, 0, "stowed", "stationary"),
        ("cinder_lance", ["spell.focus"], "lance", .6, .2, "stowed", "stationary"),
        ("kindle_hex", ["spell.bolt"], "mark", .5, .25, "stowed", "stationary"),
        ("soot_veil", ["spell.ritual"], "cone", .4, 0, "stowed", "stationary"),
        ("flashstep", ["spell.bolt"], "blink", .55, 0, "stowed", "charge"),
        ("pyre_circle", ["spell.ritual"], "ground", .65, .25, "stowed", "stationary"),
        ("white_cautery", ["spell.focus"], "heal", .45, .4, "stowed", "stationary"),
        ("furnace_heart", ["spell.ritual"], "empower", .4, .3, "stowed", "stationary"),
        ("ashen_cataclysm", ["spell.focus"], "channel", .4, .7, "stowed", "stationary"),
        ("phoenix_collapse", ["spell.focus", "spell.ritual"], "meteor", .75, .35, "stowed", "stationary"),
    ],
}

def locomotion(style):
    result = {role: f"{style}.{source}" for role, source in {
        "idle":"idle", "combat_idle":"idle", "walk":"walk", "walk_backward":"back", "run":"run",
        "strafe_left":"left", "strafe_right":"right", "turn_left":"turn_left", "turn_right":"turn_right",
        "hit_front":"impact", "hit_back":"impact", "jump":"jump", "death":"death"}.items()}
    result['hit_back']='spell.impact_back'
    if style == "shield":
        result.update(idle="shield.block", combat_idle="shield.block")
    if style == "spell":
        result.update(walk_backward="spell.walk", jump="two.jump", hit_back="spell.impact_back")
    return result

def coverage():
    uses = {key: [] for key in CLIPS}
    for profile,(career,style) in PROFILES.items():
        for role,source in locomotion(style).items():
            uses[source].append(f"{profile}:{role}")
        for suffix,sources,*_ in RECIPES[career]:
            for source in sources:
                uses[source].append(f"{profile}:{career}.{suffix}")
    if len(CLIPS) != 44 or (ANIMATION_SET == 'supplied-four' and any(not users for users in uses.values())):
        raise ValueError("Every one of the 44 supplied clips must have a gameplay use")
    return uses

def presentation_catalog(inventory):
    uses=coverage()
    return dict(schemaVersion=1,clips={key:dict(source=path,sha256=inventory[key]['sha256'],
        skeletonHash=inventory[key]['skeletonHash'],duration=inventory[key]['duration'],fps=inventory[key]['fps'],
        hipsStart=inventory[key]['hipsStart'],hipsEnd=inventory[key]['hipsEnd'],uses=uses[key]) for key,path in CLIPS.items()},
        profiles={key:dict(career=career,style=style,locomotion=locomotion(style),abilities=[dict(
            id=career+'.'+suffix,sources=keys,choreography=choreography,contactFraction=contact,hold=hold,
            equipment=equipment,movement=motion) for suffix,keys,choreography,contact,hold,equipment,motion in RECIPES[career]])
            for key,(career,style) in PROFILES.items()},
        gameplayEvidence='unreal/AegisWar/Saved/supplied-animation-gameplay.json',
        characterContactCorrections=json.loads((ROOT/'scripts/unreal/animation-recipes/corrections/prelate-contacts.json').read_text()),
        shieldContactCorrections=json.loads((ROOT/'scripts/unreal/animation-recipes/corrections/shield-contacts.json').read_text()),
        technicalEvidence=(OUT/'technical-verification.json').relative_to(ROOT).as_posix())

# Separate receipts preserve the approved four-profile history while these
# additions are still undergoing equipped-motion and gameplay review.
if ANIMATION_SET == 'siege-casters':
    PROFILES = {'riven_ruin_oracle_m': ('ruin_oracle', 'spell'), 'riven_void_magister_m': ('void_magister', 'spell')}
    RECIPES = {
        'ruin_oracle': [
            ('mark_of_vigor',['spell.bolt'],'mark',.45,.1,'stowed','stationary'),
            ('harbinger_of_frailty',['spell.bolt'],'mark',.5,.1,'stowed','stationary'),
            ('soul_drain_rite',['spell.focus'],'channel',.4,.6,'stowed','stationary'),
            ('fetish_ward',['spell.ritual'],'place',.55,.2,'stowed','stationary'),
            ('madness_cant',['spell.ritual'],'cone',.4,.1,'stowed','stationary'),
            ('blessing_of_ruin',['spell.focus'],'heal',.45,.3,'stowed','stationary'),
            ('scourging_sigil',['spell.ritual'],'ground',.55,.2,'stowed','stationary'),
            ('tether_of_agony',['spell.focus'],'channel',.45,.4,'stowed','stationary'),
            ('prophecy_of_ash',['spell.bolt'],'mark',.5,.3,'stowed','stationary'),
            ('altar_of_the_raven',['spell.ritual'],'place',.65,.4,'stowed','stationary'),
        ],
        'void_magister': [
            ('summon_idol',['spell.ritual'],'place',.6,.2,'stowed','stationary'),
            ('warp_bolt',['spell.bolt'],'bolt',.45,0,'stowed','stationary'),
            ('entropic_field',['spell.ritual'],'ground',.6,.2,'stowed','stationary'),
            ('rift_pull',['spell.focus'],'focus',.5,.2,'stowed','stationary'),
            ('daemonfire_orb',['spell.bolt'],'bolt',.5,.1,'stowed','stationary'),
            ('hover_disc',['spell.ritual'],'empower',.4,.2,'stowed','stationary'),
            ('unmake_armor',['spell.bolt'],'mark',.5,.1,'stowed','stationary'),
            ('feed_the_idol',['spell.focus'],'channel',.4,.5,'stowed','stationary'),
            ('warp_storm',['spell.ritual'],'channel',.4,.6,'stowed','stationary'),
            ('grand_conjunction',['spell.focus','spell.ritual'],'meteor',.7,.35,'stowed','stationary'),
        ],
    }

if ANIMATION_SET == 'capital-camps':
    from imported_population import models
    PROFILES = {row['profile']: ('population_'+row['key'], row['style']) for row in models().values()}
    RECIPES = {career: [] for career, _ in PROFILES.values()}

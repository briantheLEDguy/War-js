"""Stable first-pass capital population; source coordinates are metres (x,z)."""
from pathlib import Path
import configparser

ROOT = Path(__file__).resolve().parents[2]
POPULATION_MAP = '/Game/Capitals/crownward/Population/AegisCapital_Population'
FARMER = 'npc_frontier_sunmeadow_empire_farmer'
HERBALIST = 'npc_frontier_sunmeadow_empire_herbalist'
OFFICER = 'npc_aegis_ari_vell_brightfen_field_officer'

# Mara remains in the persistent city; all other IDs belong to this layer.
POPULATION = [
    ('quest-1', 'Mara Vell', 'gateward', 'quest', 'existing', 14, -91, 0),
    ('aegis_capital_quartermaster', 'Elira Dawnmarch', 'gateward', 'quartermaster', HERBALIST, 12, -112, 180),
    ('aegis_capital_portal_guard', 'Tovin Greyford', 'gateward', 'guard', OFFICER, -12, -98, 0),
    ('gateward_shopper_01', 'Market shopper', 'gateward', 'resident', FARMER, 9, -109, 30),
    ('gateward_shopper_02', 'Market shopper', 'gateward', 'resident', HERBALIST, 7, -110, 210),
    ('aegis_capital_craft_trainer', 'Serra Brightfield', 'cinderbank', 'craft_teacher', HERBALIST, -87, -41, 0),
    ('cinderbank_assistant', 'Smith assistant', 'cinderbank', 'resident', FARMER, -65, -42, 90),
    ('cinderbank_worker_01', 'Foundry worker', 'cinderbank', 'resident', FARMER, -80, -44, 60),
    ('cinderbank_worker_02', 'Workshop courier', 'cinderbank', 'resident', HERBALIST, -78, -43, 240),
    ('lantern_supply_merchant', 'Neris Reed', 'lantern_quays', 'supplies', HERBALIST, 108, -37, 180),
    ('lantern_worker_01', 'Quay porter', 'lantern_quays', 'resident', FARMER, 101, -41, 30),
    ('lantern_worker_02', 'Quay factor', 'lantern_quays', 'resident', FARMER, 99, -40, 210),
    ('aegis_capital_class_trainer', 'Alden Voss', 'bellfound', 'class_teacher', FARMER, -29, 56, 0),
    ('aegis_capital_banker', 'Mira Stonewake', 'bellfound', 'vault_keeper', HERBALIST, -21, 56, 180),
    ('bellfound_scribe', 'Court scribe', 'bellfound', 'resident', FARMER, -27, 53, 70),
    ('aegis_capital_marshal', 'Corren Vale', 'crownwatch', 'marshal', OFFICER, -20, 150, 0),
    ('crownwatch_guard_01', 'Citadel guard', 'crownwatch', 'guard', OFFICER, -8, 141, 90),
    ('crownwatch_guard_02', 'Citadel guard', 'crownwatch', 'guard', OFFICER, 8, 141, 90),
]


def official_map():
    config = configparser.ConfigParser(strict=False)
    config.read(ROOT/'unreal/AegisWar/Config/DefaultEngine.ini')
    return config['/Script/EngineSettings.GameMapsSettings']['GameDefaultMap']


def records():
    return [dict(zip(('id','name','district','role','profile','x','z','yaw'), row)) for row in POPULATION]

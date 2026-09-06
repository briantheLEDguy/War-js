"""Novitiate upper kit: literal edits of the accepted, explicitly authored cages.

The accepted sibling package is read-only. This serializer retains its vertex IDs,
face connectivity, UV corners and rig attachments; no coordinate formula is used.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from validate_source import validate_component

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED = ROOT.parent / "battle-prelate-reference-rebuild" / "source"

KEEP = {
    "pauldron.json": [
        "left_pauldron_main_shell", "left_pauldron_upper_lame",
        "left_pauldron_authored_rivet", "left_pauldron_leather_suspension",
        "left_pauldron_padded_shoulder_support", "left_pauldron_lame_fasteners",
        "left_pauldron_front_brass_border", "left_pauldron_outer_brass_border",
        "left_pauldron_rear_brass_border", "left_pauldron_upper_lame_brass_hem",
    ],
    "gorget.json": ["gorget_steel_wall", "gorget_brass_rolled_rim"],
    "breastplate.json": ["breastplate_shell", "breastplate_neck_brass", "breastplate_lower_brass"],
    "backplate.json": ["rigid_backplate"],
}

COORDINATES = {
    "left_pauldron_front_brass_border": {
        "v000": [.208, -.075, 1.598], "v001": [.208, -.072, 1.602],
        "v002": [.221, -.094, 1.589], "v003": [.221, -.091, 1.593],
        "v004": [.254, -.122, 1.569], "v005": [.254, -.119, 1.573],
        "v006": [.295, -.141, 1.548], "v007": [.295, -.138, 1.552],
        "v008": [.337, -.148, 1.532], "v009": [.337, -.145, 1.536],
        "v010": [.377, -.138, 1.519], "v011": [.377, -.134, 1.523],
        "v012": [.405, -.117, 1.514], "v013": [.405, -.113, 1.518],
        "v014": [.411, -.109, 1.508], "v015": [.410, -.105, 1.512],
    },
    "left_pauldron_outer_brass_border": {
        "v000": [.412, -.108, 1.508], "v001": [.408, -.110, 1.512],
        "v002": [.414, -.086, 1.532], "v003": [.409, -.087, 1.536],
        "v004": [.410, -.021, 1.544], "v005": [.406, -.022, 1.548],
        "v006": [.420, .036, 1.541], "v007": [.416, .036, 1.545],
        "v008": [.424, .088, 1.520], "v009": [.420, .089, 1.524],
        "v010": [.423, .110, 1.501], "v011": [.419, .112, 1.505],
        "v012": [.419, .115, 1.494], "v013": [.415, .118, 1.499],
    },
    "left_pauldron_rear_brass_border": {
        "v000": [.216, .109, 1.600], "v001": [.216, .106, 1.604],
        "v002": [.233, .129, 1.590], "v003": [.233, .126, 1.594],
        "v004": [.267, .146, 1.574], "v005": [.267, .143, 1.578],
        "v006": [.313, .159, 1.553], "v007": [.313, .156, 1.557],
        "v008": [.355, .156, 1.532], "v009": [.355, .153, 1.536],
        "v010": [.391, .143, 1.510], "v011": [.391, .140, 1.514],
        "v012": [.412, .125, 1.499], "v013": [.412, .122, 1.503],
        "v014": [.418, .117, 1.494], "v015": [.417, .114, 1.498],
    },
    "left_pauldron_upper_lame_brass_hem": {
        "v000": [.307, -.128, 1.503], "v001": [.307, -.127, 1.507],
        "v002": [.348, -.135, 1.489], "v003": [.347, -.134, 1.493],
        "v004": [.392, -.112, 1.473], "v005": [.390, -.111, 1.477],
        "v006": [.425, -.061, 1.469], "v007": [.422, -.061, 1.473],
        "v008": [.434, -.006, 1.470], "v009": [.431, -.006, 1.474],
        "v010": [.428, .058, 1.468], "v011": [.425, .057, 1.472],
        "v012": [.406, .116, 1.464], "v013": [.404, .114, 1.468],
        "v014": [.364, .142, 1.460], "v015": [.364, .140, 1.464],
    },
    "left_pauldron_main_shell": {
        "v000": [.208, -.073, 1.598], "v001": [.207, -.068, 1.621],
        "v002": [.207, -.022, 1.643], "v003": [.209, .030, 1.645],
        "v004": [.212, .074, 1.632], "v005": [.215, .100, 1.610],
        "v006": [.216, .107, 1.600],
        "v007": [.221, -.092, 1.589], "v008": [.219, -.083, 1.618],
        "v009": [.218, -.024, 1.653], "v010": [.221, .031, 1.655],
        "v011": [.226, .084, 1.636], "v012": [.231, .119, 1.607],
        "v013": [.233, .127, 1.590],
        "v014": [.254, -.120, 1.569], "v015": [.252, -.109, 1.608],
        "v016": [.248, -.028, 1.653], "v017": [.251, .033, 1.651],
        "v018": [.257, .101, 1.626], "v019": [.265, .136, 1.592],
        "v020": [.267, .144, 1.574],
        "v021": [.295, -.139, 1.548], "v022": [.292, -.126, 1.590],
        "v023": [.285, -.035, 1.642], "v024": [.291, .034, 1.638],
        "v025": [.301, .114, 1.609], "v026": [.311, .149, 1.572],
        "v027": [.313, .157, 1.553],
        "v028": [.337, -.146, 1.532], "v029": [.334, -.132, 1.568],
        "v030": [.326, -.037, 1.616], "v031": [.335, .035, 1.610],
        "v032": [.347, .116, 1.581], "v033": [.354, .148, 1.548],
        "v034": [.355, .154, 1.532],
        "v035": [.377, -.136, 1.519], "v036": [.376, -.117, 1.549],
        "v037": [.370, -.032, 1.584], "v038": [.379, .037, 1.578],
        "v039": [.387, .109, 1.549], "v040": [.391, .135, 1.520],
        "v041": [.391, .141, 1.510],
        "v042": [.405, -.115, 1.514], "v043": [.405, -.093, 1.540],
        "v044": [.401, -.024, 1.555], "v045": [.409, .036, 1.550],
        "v046": [.415, .093, 1.526], "v047": [.415, .118, 1.506],
        "v048": [.412, .123, 1.499],
        "v049": [.411, -.107, 1.508], "v050": [.413, -.086, 1.532],
        "v051": [.409, -.021, 1.543], "v052": [.419, .036, 1.540],
        "v053": [.423, .088, 1.519], "v054": [.422, .110, 1.500],
        "v055": [.418, .115, 1.494],
    },
    "left_pauldron_upper_lame": {
        "v000": [.311, -.112, 1.577], "v001": [.342, -.120, 1.561],
        "v002": [.377, -.106, 1.547], "v003": [.404, -.065, 1.546],
        "v004": [.413, -.011, 1.549],
        "v005": [.309, -.126, 1.522], "v006": [.345, -.133, 1.509],
        "v007": [.385, -.112, 1.493], "v008": [.415, -.064, 1.488],
        "v009": [.424, -.008, 1.490],
        "v010": [.307, -.126, 1.503], "v011": [.348, -.133, 1.489],
        "v012": [.391, -.110, 1.473], "v013": [.423, -.060, 1.469],
        "v014": [.432, -.006, 1.470],
        "v015": [.410, .046, 1.542], "v016": [.392, .093, 1.525],
        "v017": [.360, .117, 1.516],
        "v018": [.420, .052, 1.487], "v019": [.401, .107, 1.482],
        "v020": [.364, .133, 1.480],
        "v021": [.426, .057, 1.468], "v022": [.404, .115, 1.464],
        "v023": [.364, .140, 1.460],
    },
    "left_pauldron_leather_suspension": {
        "v000": [.208, -.010, 1.612], "v001": [.226, -.017, 1.615],
        "v002": [.235, -.020, 1.598], "v003": [.217, -.013, 1.595],
        "v004": [.226, -.010, 1.578], "v005": [.246, -.015, 1.582],
        "v006": [.252, -.010, 1.566], "v007": [.234, -.005, 1.563],
    },
    "left_pauldron_padded_shoulder_support": {
        "v000": [.208, -.027, 1.592], "v001": [.247, -.053, 1.614],
        "v002": [.298, -.064, 1.608], "v003": [.344, -.052, 1.580],
        "v004": [.373, -.033, 1.538],
        "v005": [.209, -.056, 1.561], "v006": [.250, -.087, 1.558],
        "v007": [.303, -.101, 1.543], "v008": [.352, -.085, 1.516],
        "v009": [.383, -.046, 1.483],
        "v010": [.214, -.052, 1.526], "v011": [.253, -.085, 1.519],
        "v012": [.307, -.096, 1.498], "v013": [.357, -.078, 1.475],
        "v014": [.388, -.037, 1.454],
        "v015": [.207, .030, 1.589], "v016": [.247, .065, 1.610],
        "v017": [.299, .084, 1.599], "v018": [.346, .079, 1.568],
        "v019": [.375, .056, 1.528],
        "v020": [.212, .059, 1.557], "v021": [.251, .098, 1.549],
        "v022": [.306, .116, 1.533], "v023": [.356, .102, 1.504],
        "v024": [.389, .067, 1.474],
        "v025": [.216, .054, 1.523], "v026": [.255, .088, 1.512],
        "v027": [.309, .108, 1.489], "v028": [.360, .097, 1.464],
        "v029": [.393, .063, 1.446],
    },
    "gorget_steel_wall": {
        "v000": [0, -.129, 1.602], "v001": [.046, -.126, 1.606],
        "v002": [.092, -.103, 1.616], "v003": [.121, -.060, 1.626],
        "v004": [.128, -.003, 1.631], "v005": [.113, .064, 1.632],
        "v006": [.068, .108, 1.627], "v007": [0, .125, 1.624],
        "v008": [0, -.137, 1.588], "v009": [.049, -.132, 1.592],
        "v010": [.097, -.111, 1.603], "v011": [.127, -.063, 1.614],
        "v012": [.134, -.003, 1.619], "v013": [.119, .069, 1.620],
        "v014": [.072, .114, 1.615], "v015": [0, .132, 1.612],
        "v016": [0, -.151, 1.551], "v017": [.053, -.146, 1.556],
        "v018": [.103, -.117, 1.571], "v019": [.135, -.064, 1.590],
        "v020": [.141, .005, 1.600], "v021": [.125, .075, 1.603],
        "v022": [.075, .121, 1.596], "v023": [0, .137, 1.591],
        "v024": [0, -.145, 1.529], "v025": [.052, -.141, 1.534],
        "v026": [.103, -.113, 1.548], "v027": [.134, -.057, 1.567],
        "v028": [.141, .011, 1.581], "v029": [.123, .079, 1.588],
        "v030": [.073, .123, 1.585], "v031": [0, .137, 1.581],
    },
    "gorget_brass_rolled_rim": {
        "v000": [0, -.131, 1.607], "v001": [.047, -.128, 1.611],
        "v002": [.094, -.105, 1.621], "v003": [.123, -.062, 1.631],
        "v004": [.130, -.003, 1.636], "v005": [.115, .065, 1.637],
        "v006": [.070, .110, 1.632], "v007": [0, .128, 1.629],
        "v008": [0, -.136, 1.601], "v009": [.049, -.133, 1.605],
        "v010": [.097, -.109, 1.615], "v011": [.128, -.063, 1.625],
        "v012": [.134, -.003, 1.630], "v013": [.120, .068, 1.631],
        "v014": [.073, .115, 1.626], "v015": [0, .133, 1.623],
        "v016": [0, -.132, 1.595], "v017": [.047, -.128, 1.599],
        "v018": [.094, -.105, 1.609], "v019": [.124, -.062, 1.619],
        "v020": [.130, -.003, 1.624], "v021": [.116, .065, 1.625],
        "v022": [.070, .111, 1.620], "v023": [0, .129, 1.617],
    },
    "breastplate_shell": {
        "v000": [0, -.111, 1.549], "v001": [.061, -.107, 1.555],
        "v002": [.131, -.073, 1.578],
        "v005": [0, -.161, 1.500], "v006": [.068, -.157, 1.507],
        "v010": [0, -.198, 1.429], "v011": [.078, -.189, 1.434],
        "v015": [0, -.182, 1.352], "v016": [.078, -.177, 1.357],
        "v020": [0, -.151, 1.274], "v021": [.069, -.148, 1.285],
        "v025": [0, -.144, 1.258], "v026": [.064, -.143, 1.267],
        "v027": [.137, -.107, 1.281],
    },
    "breastplate_neck_brass": {
        "v000": [0, -.114, 1.553], "v001": [.061, -.110, 1.559],
        "v002": [.132, -.076, 1.582], "v003": [.190, -.008, 1.611],
        "v004": [.219, .057, 1.596],
        "v005": [0, -.121, 1.542], "v006": [.063, -.119, 1.548],
        "v007": [.136, -.083, 1.571], "v008": [.198, -.015, 1.599],
        "v009": [.223, .057, 1.585],
    },
    "breastplate_lower_brass": {
        "v000": [0, -.148, 1.261], "v001": [.065, -.147, 1.270],
        "v002": [.138, -.111, 1.284], "v003": [.188, -.032, 1.302],
        "v004": [.204, .060, 1.319],
        "v005": [0, -.146, 1.253], "v006": [.064, -.145, 1.262],
        "v007": [.138, -.109, 1.276], "v008": [.189, -.032, 1.294],
        "v009": [.205, .060, 1.311],
    },
    "rigid_backplate": {
        "v000": [0, .140, 1.602], "v001": [.073, .134, 1.608],
        "v002": [.139, .096, 1.613], "v003": [.196, .054, 1.602],
        "v004": [.216, .039, 1.580],
    },
}

INSTANCES = {
    "left_pauldron_authored_rivet": [
        {"location": [.230, -.098, 1.600], "rotation_degrees": [-8, 0, -12], "scale": [1, 1, 1]},
        {"location": [.238, .128, 1.602], "rotation_degrees": [20, 0, 180], "scale": [1, 1, 1]},
        {"location": [-.230, -.098, 1.600], "rotation_degrees": [-8, 0, 12], "scale": [1, 1, 1]},
        {"location": [-.238, .128, 1.602], "rotation_degrees": [20, 0, -180], "scale": [1, 1, 1]},
    ],
    "left_pauldron_lame_fasteners": [
        {"location": [.321, -.137, 1.514], "rotation_degrees": [0, 0, 0], "scale": [.85, .85, .85]},
        {"location": [.376, .132, 1.486], "rotation_degrees": [0, 0, 180], "scale": [.85, .85, .85]},
        {"location": [-.321, -.137, 1.514], "rotation_degrees": [0, 0, 0], "scale": [.85, .85, .85]},
        {"location": [-.376, .132, 1.486], "rotation_degrees": [0, 0, -180], "scale": [.85, .85, .85]},
    ],
}

# New bent hinge tabs and the cuirass side return are individually drawn patches.
# IDs/coordinates, face connectivity and UV corners are literal records.
NEW_PATCHES = {
    "pauldron.json": [
        {
            "id": "novitiate_pauldron_front_hinge_tab", "slot": "shoulders",
            "rigid_bone": "upper_arm_L", "mirror_bone": "upper_arm_R",
            "vertices": [
                {"id": "v000", "co": [.313, -.126, 1.539]}, {"id": "v001", "co": [.326, -.128, 1.535]},
                {"id": "v002", "co": [.313, -.133, 1.525]}, {"id": "v003", "co": [.326, -.135, 1.521]},
                {"id": "v004", "co": [.313, -.132, 1.509]}, {"id": "v005", "co": [.326, -.135, 1.506]},
            ],
            "faces": [
                {"id": "f000", "vertices": ["v000", "v002", "v003", "v001"], "uv": [[0, 1], [0, .5], [1, .5], [1, 1]], "material": "dark_steel"},
                {"id": "f001", "vertices": ["v002", "v004", "v005", "v003"], "uv": [[0, .5], [0, 0], [1, 0], [1, .5]], "material": "dark_steel"},
            ],
            "modifiers": [{"type": "MIRROR", "axis": "X"}, {"type": "SOLIDIFY", "thickness": .002, "offset": 0}, {"type": "BEVEL", "width": .0007, "segments": 2}],
            "landmarks": {"hinge_top": "v000", "hinge_foot": "v004"}, "seams": [], "sharp_edges": [], "creases": [], "closed": False,
            "transform": {"location": [0, 0, 0], "rotation_degrees": [0, 0, 0], "scale": [1, 1, 1]},
        },
        {
            "id": "novitiate_pauldron_rear_hinge_tab", "slot": "shoulders",
            "rigid_bone": "upper_arm_L", "mirror_bone": "upper_arm_R",
            "vertices": [
                {"id": "v000", "co": [.369, .119, 1.510]}, {"id": "v001", "co": [.382, .114, 1.510]},
                {"id": "v002", "co": [.369, .132, 1.499]}, {"id": "v003", "co": [.382, .126, 1.499]},
                {"id": "v004", "co": [.369, .134, 1.480]}, {"id": "v005", "co": [.382, .128, 1.481]},
            ],
            "faces": [
                {"id": "f000", "vertices": ["v000", "v001", "v003", "v002"], "uv": [[0, 1], [1, 1], [1, .5], [0, .5]], "material": "dark_steel"},
                {"id": "f001", "vertices": ["v002", "v003", "v005", "v004"], "uv": [[0, .5], [1, .5], [1, 0], [0, 0]], "material": "dark_steel"},
            ],
            "modifiers": [{"type": "MIRROR", "axis": "X"}, {"type": "SOLIDIFY", "thickness": .002, "offset": 0}, {"type": "BEVEL", "width": .0007, "segments": 2}],
            "landmarks": {"hinge_top": "v000", "hinge_foot": "v004"}, "seams": [], "sharp_edges": [], "creases": [], "closed": False,
            "transform": {"location": [0, 0, 0], "rotation_degrees": [0, 0, 0], "scale": [1, 1, 1]},
        },
    ],
    "breastplate.json": [
        {
            "id": "novitiate_breastplate_rolled_side_return", "slot": "chest", "rigid_bone": "upper_chest",
            "vertices": [
                {"id": "v000", "co": [.218, .059, 1.592]}, {"id": "v001", "co": [.216, .050, 1.594]},
                {"id": "v002", "co": [.232, .052, 1.556]}, {"id": "v003", "co": [.230, .045, 1.558]},
                {"id": "v004", "co": [.245, .059, 1.498]}, {"id": "v005", "co": [.243, .052, 1.499]},
                {"id": "v006", "co": [.234, .065, 1.432]}, {"id": "v007", "co": [.231, .057, 1.433]},
                {"id": "v008", "co": [.210, .064, 1.340]}, {"id": "v009", "co": [.207, .057, 1.341]},
                {"id": "v010", "co": [.203, .060, 1.316]}, {"id": "v011", "co": [.200, .053, 1.317]},
            ],
            "faces": [
                {"id": "f000", "vertices": ["v000", "v002", "v003", "v001"], "uv": [[1, 1], [1, .8], [0, .8], [0, 1]], "material": "steel"},
                {"id": "f001", "vertices": ["v002", "v004", "v005", "v003"], "uv": [[1, .8], [1, .6], [0, .6], [0, .8]], "material": "steel"},
                {"id": "f002", "vertices": ["v004", "v006", "v007", "v005"], "uv": [[1, .6], [1, .4], [0, .4], [0, .6]], "material": "steel"},
                {"id": "f003", "vertices": ["v006", "v008", "v009", "v007"], "uv": [[1, .4], [1, .2], [0, .2], [0, .4]], "material": "steel"},
                {"id": "f004", "vertices": ["v008", "v010", "v011", "v009"], "uv": [[1, .2], [1, 0], [0, 0], [0, .2]], "material": "steel"},
            ],
            "modifiers": [{"type": "MIRROR", "axis": "X"}, {"type": "SUBSURF", "levels": 2}, {"type": "SOLIDIFY", "thickness": .0025, "offset": 0}, {"type": "BEVEL", "width": .0008, "segments": 2}],
            "landmarks": {"armhole_top": "v000", "waist_return": "v010"}, "seams": [], "sharp_edges": [], "creases": [], "closed": False,
            "transform": {"location": [0, 0, 0], "rotation_degrees": [0, 0, 0], "scale": [1, 1, 1]},
        },
    ],
}

NOTES = {
    "pauldron.json": [
        "Novitiate Field Harness: one compact shoulder shell and one overlapping lower lame per side.",
        "Crown, width and depth were individually reduced in literal vertex tables; the tall inner guard, raised emblem, decorative gilding and second lower plate were removed.",
        "Narrow plain rolled steel edges, one turned lame hem and two small bent iron hinge tabs add functional construction. Their coordinates are literal; historical border IDs retain UV lineage and all faces are iron/steel.",
        "A fitted leather support and short suspension remain. Four explicit iron fasteners per shoulder supply attachment detail without ornament.",
        "Existing Mirror finishing and shoulder/upper-arm attachment metadata are retained. Vertex IDs, face connectivity and UV corners are inherited from the accepted authored cages.",
    ],
    "gorget.json": [
        "Novitiate collar is lowered beneath the chin: front steel wall rim Z1.602, side Z1.631, rear Z1.624 meters.",
        "An independent rolled iron lip remains; inscription, broad lower trim band and decorative fastener row were removed.",
        "Literal wall/rim coordinate tables narrow the mouth opening and retain overlap with the upper chest and backplate.",
    ],
    "breastplate.json": [
        "Plain Novitiate steel breastplate; crossed reinforcement strips are absent.",
        "Neckline is slightly raised, central projection softened and the low center point shortened with explicit vertex edits. Flank and shoulder attachment coordinates remain compatible with the accepted body.",
        "Narrow steel edge strips retain the accepted component IDs for stable provenance; the historical brass names do not imply brass material.",
        "A new literal folded steel return defines each outer armhole/flank edge. The central badge-bearing surface is unchanged by this construction-detail pass.",
    ],
    "backplate.json": [
        "Plain Novitiate backplate: rear neckline explicitly lowered to meet the new short gorget.",
        "Accepted shoulder, flank and waist coverage is retained; no rear ornament is included in this component.",
    ],
}


def main():
    components = []
    for filename, retained in KEEP.items():
        path = ACCEPTED / filename
        original = json.loads(path.read_text(encoding="utf-8"))
        source_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        data = copy.deepcopy(original)
        data["component"] = "novitiate_" + original["component"]
        data["reference_notes"] = NOTES[filename]
        data["source_provenance"] = {
            "basis": "Accepted Battle Prelate authored control mesh; secondary Novitiate redesign authorized by user",
            "package": "battle-prelate-reference-rebuild", "file": filename, "sha256": source_hash,
            "edit_record": "tools/author_novitiate_upper.py",
            "preserved": ["vertex IDs", "face IDs and connectivity", "face-corner UVs", "rig attachments"],
        }
        data["parts"] = [p for p in data["parts"] if p["id"] in retained]
        changes = []
        for part in data["parts"]:
            edits = COORDINATES.get(part["id"], {})
            assert set(edits).issubset({v["id"] for v in part["vertices"]})
            for vertex in part["vertices"]:
                if vertex["id"] in edits:
                    before = vertex["co"]
                    vertex["co"] = edits[vertex["id"]]
                    if before != vertex["co"]:
                        changes.append({"part": part["id"], "vertex": vertex["id"], "before": before, "after": vertex["co"]})
            for face in part["faces"]:
                if face["material"] == "brass":
                    face["material"] = "steel"
                if part["id"] == "left_pauldron_padded_shoulder_support":
                    face["material"] = "leather"
            if part["id"] in INSTANCES:
                part["instances"] = INSTANCES[part["id"]]
            if part["id"] == "gorget_steel_wall":
                for modifier in part["modifiers"]:
                    if modifier["type"] == "SOLIDIFY":
                        modifier["thickness"] = .005
            if part["id"] in {"left_pauldron_front_brass_border", "left_pauldron_outer_brass_border", "left_pauldron_rear_brass_border", "left_pauldron_upper_lame_brass_hem"}:
                part["modifiers"] = [
                    {"type": "MIRROR", "axis": "X"}, {"type": "SUBSURF", "levels": 2},
                    {"type": "SOLIDIFY", "thickness": .003, "offset": 0},
                    {"type": "BEVEL", "width": .001, "segments": 2},
                ]
        additions = copy.deepcopy(NEW_PATCHES.get(filename, []))
        data["parts"].extend(additions)
        if filename == "pauldron.json":
            # The short overlapping lame is fixed to this compact shoulder cap.
            # Upper-arm rotation otherwise drives its front edge through the cap.
            for part in data["parts"]:
                if part.get("rigid_bone") == "upper_arm_L":
                    part["rigid_bone"] = "shoulder_L"
                    part["mirror_bone"] = "shoulder_R"
                    part["attachment_refinement"] = "Fixed compact cap assembly; retains overlap through the shared hammer swing"
            data["reference_notes"].append("Motion fit refinement: lower lame, hem, hinge tabs and fasteners follow the shoulder cap. They no longer rotate independently with the upper arm into the outer shell.")
        validated = validate_component(data)
        output = ROOT / "source" / filename
        output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        components.append({
            "file": filename, "accepted_sha256": source_hash,
            "new_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "retained_parts": retained, "new_authored_parts": [p["id"] for p in additions],
            "removed_parts": [p["id"] for p in original["parts"] if p["id"] not in retained],
            "literal_vertex_changes": changes, "validation": validated,
            "control_bounds_by_part": {p["id"]: {
                "min": [min(v["co"][i] for v in p["vertices"]) for i in range(3)],
                "max": [max(v["co"][i] for v in p["vertices"]) for i in range(3)],
            } for p in data["parts"]},
        })
    report = {
        "schema_version": 1, "design": "Novitiate Field Harness upper armor",
        "status": "authored_source_validated_visual_review_pending",
        "geometry_policy": "Literal vertex edits only; no profile generation, primitive assembly, random placement or automatic topology changes.",
        "accepted_package_modified": False,
        "visual_changes": ["compact two-plate shoulders", "plain rolled shoulder edges and single turned lame hem", "two bent iron hinge tabs per shoulder", "no raised shoulder defense or ornament", "low plain iron collar", "unadorned chest with folded steel side returns", "lower plain rear neckline"],
        "components": components,
    }
    review_path = ROOT / "review" / "upper_design.json"
    if review_path.exists():
        previous_review = json.loads(review_path.read_text(encoding="utf-8"))
        for key in ("badge_clearance_review", "visual_review"):
            if key in previous_review:
                report[key] = previous_review[key]
    review_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "components": [
        {"file": c["file"], "parts": len(c["retained_parts"]) + len(c["new_authored_parts"]), "changed_vertices": len(c["literal_vertex_changes"]), "sha256": c["new_sha256"]} for c in components
    ]}, indent=2))


if __name__ == "__main__":
    main()

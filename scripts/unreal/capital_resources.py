"""Explicit source bindings for the first imported capital gathering visuals."""
import math

PROFILE = "aegis_flowerbed_violets"
NODE_PROFILES = {
    "aegis_capital_herb_node_03": PROFILE,
    "aegis_capital_soil_node_04": PROFILE,
    "aegis_capital_scrap_node_01": "aegis_crate_stack",
    "aegis_capital_ore_node_02": "aegis_crate_stack",
    "aegis_capital_scrap_node_07": "aegis_crate_stack",
    "aegis_capital_ore_node_08": "aegis_crate_stack",
}
NODE_IDS = tuple(NODE_PROFILES)


def resource_bindings(source):
    nodes = {row["id"]: row for row in source["resourceNodes"]}
    props = {row["id"]: row for row in source["props"]}
    if len(nodes) != len(source["resourceNodes"]) or len(props) != len(source["props"]):
        raise ValueError("Duplicate capital resource or prop identity")
    result = []
    for identity in NODE_IDS:
        node = nodes[identity]
        prop = props[node["visualPropId"]]
        if (prop.get("assetKey") != NODE_PROFILES[identity]
                or prop.get("model") != "prop_" + NODE_PROFILES[identity] + ".glb"):
            raise ValueError("Capital gathering visual changed; review its replacement")
        if any(node[axis] != prop[axis] for axis in ("x", "z")):
            raise ValueError("Capital resource and its visual have different locations")
        transform = [prop["x"],prop["z"],prop.get("y",0),prop.get("rotY",0)]
        if any(type(value) not in (int,float) or not math.isfinite(value) for value in transform):
            raise ValueError("Invalid gathering visual transform")
        scale = prop.get("scale", 1)
        if type(scale) not in (int, float) or not math.isfinite(scale) or scale <= 0:
            raise ValueError("Invalid gathering visual scale")
        result.append({"node": node, "prop": prop, "profile": NODE_PROFILES[identity]})
    return result

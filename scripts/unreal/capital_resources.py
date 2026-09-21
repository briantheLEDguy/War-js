"""Explicit source bindings for the first imported capital gathering visuals."""
import math

PROFILE = "aegis_flowerbed_violets"
NODE_IDS = ("aegis_capital_herb_node_03", "aegis_capital_soil_node_04")


def resource_bindings(source):
    nodes = {row["id"]: row for row in source["resourceNodes"]}
    props = {row["id"]: row for row in source["props"]}
    if len(nodes) != len(source["resourceNodes"]) or len(props) != len(source["props"]):
        raise ValueError("Duplicate capital resource or prop identity")
    result = []
    for identity in NODE_IDS:
        node = nodes[identity]
        prop = props[node["visualPropId"]]
        if prop.get("assetKey") != PROFILE:
            raise ValueError("Capital gathering visual changed; review its replacement")
        if any(node[axis] != prop[axis] for axis in ("x", "z")):
            raise ValueError("Capital resource and its visual have different locations")
        scale = prop.get("scale", 1)
        if not isinstance(scale, (int, float)) or not math.isfinite(scale) or scale <= 0:
            raise ValueError("Invalid gathering visual scale")
        result.append({"node": node, "prop": prop, "profile": PROFILE})
    return result

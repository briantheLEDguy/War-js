"""Deterministic kit-based Aegis capital layout, in Unreal centimetres.

Coordinates identify mesh bounds centres in XY and the visible bottom in Z.
Only authored purchased meshes are used; gaps define real doors and streets.
"""


def castle_layout():
    rows = []

    def add(kind, x, y, z=10, yaw=0, scale=(1, 1, 1), district="castle"):
        rows.append({"id": f"{district}_{kind}_{len(rows):04d}", "kind": kind,
                     "centerBottom": [x, y, z], "yaw": yaw, "scale": list(scale), "district": district})

    def floor(x, y, z=0, scale=(1, 1, 1), district="castle"):
        add("floor", x, y, z, scale=scale, district=district)

    def enclosure(cx, cy, nx, ny, levels, gate=False, district="castle", walkway=False, rear_gate=False):
        # Two skins and a real stone deck give curtain walls usable thickness.
        edges = [(cx + (i - (nx - 1) / 2) * 300, cy - ny * 150, 0, i)
                 for i in range(nx)]
        edges += [(cx + (i - (nx - 1) / 2) * 300, cy + ny * 150, 0, i if rear_gate else -1)
                  for i in range(nx)]
        edges += [(cx - nx * 150, cy + (i - (ny - 1) / 2) * 300, 90, -1)
                  for i in range(ny)]
        edges += [(cx + nx * 150, cy + (i - (ny - 1) / 2) * 300, 90, -1)
                  for i in range(ny)]
        for x, y, yaw, gate_index in edges:
            opening = gate and gate_index >= 0 and abs(x - cx) < 310
            for level in range(levels):
                if opening and level < 2:
                    continue
                module = "window" if district == "keep" and level in [1, 2, 3] else "wall"
                add(module, x, y, 10 + level * 300, yaw, district=district)
                if walkway:
                    ix = x + (250 if x < cx else -250) if yaw == 90 else x
                    iy = y + (250 if y < cy else -250) if yaw == 0 else y
                    add("wall", ix, iy, 10 + level * 300, yaw, district=district)
            if walkway:
                floor(x + ((125 if x < cx else -125) if yaw == 90 else 0),
                      y + ((125 if y < cy else -125) if yaw == 0 else 0), 10 + levels * 300)
            add("wall", x, y, 20 + levels * 300, yaw, (1, 1, 0.25), district)
            add("merlon", x, y, 95 + levels * 300, yaw, (0.67, 1, 0.25), district)

    # Northern fortress: 72 x 60 m curtain, four projecting towers and gatehouse.
    enclosure(0, 9300, 24, 20, 3, gate=True, walkway=True)
    for x in [-3600, 3600]:
        for y in [6300, 12300]:
            enclosure(x, y, 4, 4, 5, gate=True, district="castle_tower")
            for dx in [-450, -150, 150, 450]:
                for dy in [-450, -150, 150, 450]:
                    floor(x + dx, y + dy, 1510)
    for x in [-1200, 1200]:
        enclosure(x, 6300, 4, 4, 4, gate=True, district="gatehouse")
        for dx in [-450, -150, 150, 450]:
            for dy in [-450, -150, 150, 450]:
                floor(x + dx, 6300 + dy, 1210)

    # Great keep: 18 x 24 m, five stories, accessible main hall and roof battlements.
    enclosure(0, 10500, 6, 8, 5, gate=True, district="keep")
    for x in [-750, -450, 450, 750]:
        for z in [10, 292, 574]:
            add("buttress", x, 9250, z, 180, district="keep")
    for z in [0, 1510]:
        for x in range(-750, 900, 300):
            for y in range(9450, 11700, 300):
                floor(x, y, z, district="keep")
    # Interior upper floors reserve a continuous stairwell at the western side.
    for z in [310, 610, 910, 1210]:
        for x in range(-450, 900, 300):
            for y in range(9450, 11700, 300):
                floor(x, y, z, district="keep")
    # Courtyard paving, central path and a broad external battlement stair.
    for x in range(-2850, 3000, 300):
        for y in range(7350, 12000, 300):
            if abs(x) > 900 or y < 9300:
                floor(x, y)
    for y in range(6450, 9450, 300):
        for x in [-150, 150]:
            floor(x, y)
    for step in range(9):
        add("stairs", 2850, 7600 + step * 150, 10 + step * 100, 180, (2, 1, 1))
    for x in [-2200, 2200]:
        for y in [7700, 8500, 11000]:
            add("bench", x, y, 10, 90, district="castle")
    for x in [2850, 3150, 3450]:
        floor(x, 9000, 910)
    # Keep stairs climb in a continuous long run; upper landings join each floor.
    for step in range(15):
        add("stairs", -700, 9475 + step * 150, 10 + step * 100, 180, (1.6, 1, 1), "keep")

    # Keep unrelated placement identities stable while opening the roof stairwell.
    return [row for row in rows if not (row["district"] == "keep" and row["kind"] == "floor"
        and row["centerBottom"][0] == -750 and row["centerBottom"][2] == 1510)]


def castle_routes():
    """Design feet heights for real-character acceptance, not collision evidence."""
    entrance = [[16950, 0, 4210], [17400, 0, 4210], [17400, 700, 4210], [17360, 700, 4210]]
    keep = list(entrance)
    keep += [[17475 + step * 150, 700, 4270 + step * 100] for step in range(15)]
    keep += [[19640, 700, 5710], [19640, 500, 5720], [19500, 0, 5720]]
    battlement = [[13900, 0, 4210], [14800, 0, 4210], [15485, 0, 4210], [15485, -2850, 4210]]
    battlement += [[15600 + step * 150, -2850, 4270 + step * 100] for step in range(9)]
    battlement += [[17000, -2850, 5120], [17000, -3450, 5120], [17400, -3475, 5120]]
    routes = {"keep": keep, "battlement": battlement}
    for level in range(1,5):
        landing_x, landing_z = 17400+level*450, 4220+level*300
        route = list(entrance)
        route += [[17475+step*150,700,4270+step*100] for step in range(level*3)]
        route += [[landing_x,700,landing_z],[landing_x,350,landing_z],[landing_x,0,landing_z]]
        routes["floor"+str(level)] = route
    return routes


def build_layout():
    from capital_geography import source_map, height, point, sampled_path
    import math
    source = source_map()
    rows = []
    # Rotate the modular castle onto the original upper citadel plateau.
    # Original coordinates: x=east, z=north; Unreal X=north, Y=east.
    for row in castle_layout():
        x, y, z = row["centerBottom"]
        rows.append({**row, "centerBottom": [y + 8000, -x, z + 4200], "yaw": row["yaw"] - 90})
    houses = [p for p in source["props"] if p["kind"].startswith(("aegis_house_", "aegis_rowhouse_"))]
    for i, house in enumerate(houses):
        district = min(source["cityDistricts"], key=lambda d: (d["x"]-house["x"])**2 + (d["z"]-house["z"])**2)
        kind = "house" + str(i % 3 + 1)
        # Fit complete assemblies inside the existing ten-metre house pads.
        scale = {"house1": .45, "house2": .85, "house3": .53}[kind]
        rows.append({"id": house["id"], "kind": kind, "centerBottom": point(house, 5),
                     "yaw": 90-math.degrees(house.get("rotY", 0)), "scale": [scale,scale,1],
                     "district": district["id"], "sourceId": house["id"]})
    for side in [-1, 1]:
        for index in range(4):
            x, z = side*22, -112 + index*8
            for kind in ["stall", "stallframe"]:
                rows.append({"id": f"gateward_{kind}_{side}_{index}", "kind": kind,
                             "centerBottom": [z*100, x*100, height(x,z)*100+5],
                             "yaw": 0 if side == 1 else 180, "scale": [1,1,1], "district": "gateward"})
            for kind, dz in [("barrel",2),("crate",-2)]:
                prop = {"x":x+side*4,"z":z+dz}
                rows.append({"id":f"gateward_{kind}_{side}_{index}","kind":kind,
                    "centerBottom":point(prop,5),"yaw":0,"scale":[1,1,1],"district":"gateward"})
    # Match original perimeter openings and elevations with authored kit wall pieces.
    for p in source["props"]:
        if p["kind"] != "aegis_wall":
            continue
        # Source wall spans include per-axis scaling. Fill the complete span;
        # assuming six metres leaves gaps between the original twelve-metre bays.
        angle = p.get("rotY", 0)
        span = p["colliders"][0]["width"] * p.get("scaleX",1) * p.get("scale",1)
        count = math.ceil(span/3)
        width = span/count
        for bay in range(count):
            along = (bay+.5)*width-span/2
            x, z = p["x"] + along*math.cos(angle), p["z"] - along*math.sin(angle)
            bottom = height(x,z)*100
            yaw = 90-math.degrees(angle)
            for side in [-1,1]:
                # Paired skins leave a two-metre walkable deck at the original height.
                bx,bz = x+side*math.sin(angle),z+side*math.cos(angle)
                for level in range(4):
                    rows.append({"id":f'{p["id"]}_{bay}_{side}_{level}',"kind":"wall",
                        "centerBottom":[bz*100,bx*100,bottom+level*300],"yaw":yaw,
                        "scale":[width/3,1,1],"district":"rampart","sourceId":p["id"]})
            rows.append({"id":f'{p["id"]}_{bay}_deck',"kind":"floor",
                "centerBottom":[z*100,x*100,bottom+1200],"yaw":yaw,
                "scale":[width/3,2/3,1],"district":"rampart","sourceId":p["id"]})
            rows.append({"id":f'{p["id"]}_{bay}_merlon',"kind":"merlon",
                "centerBottom":[(z+math.cos(angle))*100,(x+math.sin(angle))*100,bottom+1210],"yaw":yaw,
                "scale":[min(1,width/1.5),1,.25],"district":"rampart","sourceId":p["id"]})
    gateward = next(p for p in source["paths"] if p["id"] == "aegis_city_gateward")
    # End inside the new great hall; its entrance sits at source z=173 metres.
    route = sampled_path(gateward, 2)
    route += sampled_path({"points": [{"x":0,"z":119},{"x":0,"z":176}]}, 2)[1:]
    return {"schemaVersion": 2, "zoneId": "aegis_capital", "name": "Bastion of Aegis - Crownward",
        "map": "/Game/Capitals/crownward/AegisCapital_Workbench", "arrival": point(source["spawnPoint"], 130),
        "placements": rows, "routes": [point(p,130) for p in route], "castleRoutes": castle_routes(),
        "districts": source["cityDistricts"], "sourceHouseCount": len(houses),
        "sourcePathIds": [p["id"] for p in source["paths"]], "fullCapitalAcceptance": False}

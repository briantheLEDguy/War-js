"""Deterministic kit-based Aegis capital layout, in Unreal centimetres.

Coordinates identify mesh bounds centres in XY and the visible bottom in Z.
Only authored purchased meshes are used; gaps define real doors and streets.
"""


def build_layout():
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

    # Broad processional avenue connects the southern arrival to the gatehouse.
    for y in range(-13200, 6300, 1800):
        floor(0, y, 0, (4, 6, 1), "avenue")
    for y in [-10500, -7500, -4500, -1500, 1500, 4500]:
        for x in [-9000, -7200, -5400, -3600, -1800, 1800, 3600, 5400, 7200, 9000]:
            floor(x, y, 0, (6, 2, 1), "streets")
    for x in [-1800, 0, 1800]:
        for y in [-1800, 0, 1800]:
            floor(x, y, 0, (6, 6, 1), "market")
    for x in [-1800, 1800]:
        for y in [-1800, -600, 600, 1800]:
            add("stall", x, y, 10, 90 if x < 0 else -90, district="market")
            add("stallframe", x, y, 10, 90 if x < 0 else -90, district="market")
            add("barrel", x + 330, y + 170, 10, district="market")
            add("crate", x + 330, y - 170, 10, district="market")
    for x in [-1100, 1100]:
        for y in [-2450, 2450]:
            add("bench", x, y, 10, district="market")

    # Complete house assemblies only; 04a/b/c are unfinished construction stages.
    for ix, x in enumerate([-8700, -6000, -3300, 3300, 6000, 8700]):
        for iy, y in enumerate([-11700, -8700, -5700, -2700, 300, 3300]):
            if abs(x) < 4000 and y in [-2700, 300]:
                continue
            kind = "house" + str((ix + iy * 2) % 3 + 1)
            district = "artisan" if x < 0 else "residential"
            add(kind, x, y, 10, 180 if x < 0 else 0, district=district)

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
        add("stairs", 2850, 7600 + step * 150, 10 + step * 100, 0, (2, 1, 1))
    for x in [-2200, 2200]:
        for y in [7700, 8500, 11000]:
            add("bench", x, y, 10, 90, district="castle")
    for x in [2850, 3150, 3450]:
        floor(x, 9000, 910)
    # Keep stairs climb in a continuous long run; upper landings join each floor.
    for step in range(15):
        add("stairs", -700, 9475 + step * 150, 10 + step * 100, 0, (1.6, 1, 1), "keep")

    enclosure(0, -4000, 72, 64, 2, gate=True, district="rampart", rear_gate=True)
    for x in [-10800, 10800]:
        for y in [-13600, 5600]:
            enclosure(x, y, 3, 3, 3, district="rampart_tower")
            for dx in [-300, 0, 300]:
                for dy in [-300, 0, 300]:
                    floor(x + dx, y + dy, 910, district="rampart_tower")

    return {"schemaVersion": 1, "name": "Bastion of Aegis - Crownward",
            "map": "/Game/Capitals/crownward/AegisCapital_Workbench",
            "arrival": [0, -12500, 130], "placements": rows,
            "routes": [[0, -12500, 120], [0, -6000, 120], [0, 0, 120],
                       [0, 6000, 120], [0, 8000, 120], [0, 9600, 120]],
            "fullCapitalAcceptance": False}

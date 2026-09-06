"""Deterministic, seamless material fields without a repeating sine-wave grain."""
import numpy as np


def field(n, cells, seed):
    rng = np.random.default_rng(seed)
    grid = rng.random((cells, cells))
    coord = np.arange(n) * cells / n
    cell = coord.astype(int)
    t = coord - cell
    t = t * t * (3 - 2 * t)
    a, b = cell % cells, (cell + 1) % cells
    top = grid[a[:, None], a] * (1 - t) + grid[a[:, None], b] * t
    bottom = grid[b[:, None], a] * (1 - t) + grid[b[:, None], b] * t
    return top * (1 - t[:, None]) + bottom * t[:, None]


def surface(name, color, metallic, n):
    seed = sum((i + 1) * ord(c) for i, c in enumerate(name))
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[:n, :n] / n
    cloud = field(n, 5, seed)
    mottling = field(n, 29, seed + 1)
    grit = field(n, 157, seed + 2)
    grain = (cloud - .5) * .08 + (mottling - .5) * .04 + (grit - .5) * .015
    mortar = np.zeros((n, n), dtype=bool)
    height = (mottling - .5) * .0004
    cell_color = np.zeros((n, n))
    if name in ('brick', 'stone', 'limestone', 'paving', 'flagstone'):
        rows, cols = {'brick': (16, 8), 'paving': (16, 12), 'stone': (9, 5),
                      'limestone': (7, 4), 'flagstone': (6, 5)}[name]
        row = np.floor(y * rows).astype(int)
        # Uneven lengths and row offsets, with chipped edges rather than stripes.
        stagger = rng.uniform(.18, .8, rows)
        warped = x * cols + stagger[row] + (mottling - .5) * .06
        col = np.floor(warped).astype(int) % cols
        u, v = warped % 1, (y * rows + (grit - .5) * .018) % 1
        edge = np.minimum.reduce([u, 1 - u, v, 1 - v])
        mortar = edge < (.023 if name == 'paving' else .032)
        cell_color = rng.uniform(-.065, .065, (rows, cols))[row, col]
        height = np.clip(edge / .065, 0, 1) * .002 + (mottling - .5) * .0004
    elif name == 'oak':
        # Irregular lengthwise grain; no diagonal sinusoidal bands.
        knots = field(n, 31, seed + 8)
        grain = (cloud - .5) * .035 + (knots - .5) * .022 + (grit - .5) * .01
        planks = np.floor(x * 9).astype(int)
        cell_color = rng.uniform(-.025, .035, 9)[planks]
        mortar = (x * 9) % 1 < .012
        height = (knots - .5) * .00015
    elif name in ('slate', 'terracotta', 'copper'):
        row = np.floor(y * 14).astype(int)
        col = np.floor(x * 9 + (row % 2) * .5).astype(int) % 9
        mortar = ((y * 14) % 1 < .025) | (((x * 9 + (row % 2) * .5) % 1) < .018)
        cell_color = rng.uniform(-.03, .035, (14, 9))[row, col]
        height = np.where(mortar, 0, .001)
    rgba = np.ones((n, n, 4))
    rgb = np.array(color)[None, None, :] + (grain + cell_color)[:, :, None]
    # Local soot, faded limewash and damp patches follow broad irregular fields.
    rgb *= (1 - np.maximum(0, .4 - cloud) * .45)[:, :, None]
    rgba[:, :, :3] = np.clip(rgb, .006, .85)
    rgba[mortar, :3] = np.array(color) * .52 + .022
    orm = np.ones_like(rgba)
    orm[:, :, 0] = np.where(mortar, .8, .98)
    orm[:, :, 1] = np.clip((.5 if metallic else .86) + (mottling - .5) * .13, .25, .99)
    orm[:, :, 2] = metallic
    dy, dx = np.gradient(height, 1 / n)
    normals = np.dstack((-dx, -dy, np.ones_like(dx)))
    normals /= np.linalg.norm(normals, axis=2)[:, :, None]
    normal = np.ones_like(rgba)
    normal[:, :, :3] = normals * .5 + .5
    return rgba, orm, normal, height

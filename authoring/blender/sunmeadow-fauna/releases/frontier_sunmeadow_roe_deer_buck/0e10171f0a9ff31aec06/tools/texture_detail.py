"""Original overlapping hair strokes and a tested tangent-space height conversion."""
import numpy as np


def pelt_strokes(size=1024, seed=48191):
    rng = np.random.default_rng(seed)
    relief = np.zeros((size, size), dtype=np.float32)
    pigment = np.zeros_like(relief)
    density = np.zeros_like(relief)
    scale = size / 1024
    for _ in range(32000):
        cx, cy = rng.uniform(0, size, 2)
        half = rng.uniform(5, 14) * scale
        width = rng.uniform(.48, .90) * scale
        angle = rng.normal(.16, .16)
        curve = rng.uniform(-1.0, 1.0) * scale
        radius = int(np.ceil(half + 3 * width))
        x0, x1 = max(0, int(cx) - radius), min(size, int(cx) + radius + 1)
        y0, y1 = max(0, int(cy) - radius), min(size, int(cy) + radius + 1)
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dx, dy = xx - cx, yy - cy
        along = (dx * np.sin(angle) + dy * np.cos(angle)) / half
        across = dx * np.cos(angle) - dy * np.sin(angle) - curve * np.maximum(0, 1 - along * along)
        stroke = np.exp(-(across / width) ** 2) * np.maximum(0, 1 - along * along) ** 1.4
        strength = rng.uniform(.70, 1.0)
        patch = relief[y0:y1, x0:x1]
        np.maximum(patch, stroke * strength, out=patch)
        pigment[y0:y1, x0:x1] += stroke * (rng.uniform(-.034, .038) + along * .010)
        density[y0:y1, x0:x1] += stroke
    return relief, pigment / np.maximum(1, density)


def tangent_normals(height, strength, rows_bottom_up=True):
    dy, dx = np.gradient(height)
    # Blender pixels and UV V rise together; Pillow raster rows descend.
    normal = np.stack([-dx * strength, (-dy if rows_bottom_up else dy) * strength, np.ones_like(dx)], axis=-1)
    return normal / np.linalg.norm(normal, axis=-1)[..., None]

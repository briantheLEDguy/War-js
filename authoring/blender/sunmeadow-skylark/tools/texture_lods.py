"""Linear-channel atlas reductions with unit-length tangent normals."""
import numpy as np


def reduce_pixels(pixels, level, normal=False):
    if level not in (0, 1, 2):
        raise ValueError('Only the three authored delivery LODs are supported')
    factor = 2 ** level
    height, width, channels = pixels.shape
    if channels != 4 or height % factor or width % factor:
        raise ValueError('RGBA atlas dimensions must divide by the reduction factor')
    reduced = pixels.reshape(height // factor, factor, width // factor, factor, 4).mean(axis=(1, 3))
    if normal:
        vectors = reduced[:, :, :3] * 2 - 1
        length = np.linalg.norm(vectors, axis=2, keepdims=True)
        vectors = np.where(length > 1e-8, vectors / np.maximum(length, 1e-8), np.array([0, 0, 1]))
        reduced[:, :, :3] = vectors * .5 + .5
    return reduced.astype(np.float32)


def rgba8_mip_bytes(width, height):
    if width < 1 or height < 1:
        raise ValueError('Positive dimensions required')
    total = 0
    while True:
        total += width * height * 4
        if width == 1 and height == 1:
            return total
        width, height = max(1, width // 2), max(1, height // 2)

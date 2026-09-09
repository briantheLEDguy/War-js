"""Bake local differential skin relaxation to portable animated morph targets.

The authored rest surface is invariant. Neighbourhood relaxation removes LBS
folds while transported rest offsets retain the original muscle thickness.
Only the proximal limb fields participate; head and distal contacts stay exact.
"""
import numpy as np


def smoothstep(low, high, value):
    t = np.clip((value-low)/(high-low), 0, 1)
    return t*t*(3-2*t)


def caudal_weight_transfer(point, weights, scale):
    """The caudal rump rides the pelvis; femoral muscle owns the forward thigh."""
    point = np.asarray(point)/scale
    amount = .9*smoothstep(.31, .43, point[1])*smoothstep(.36, .46, point[2])
    result = dict(weights); transfer = 0
    for name, value in weights.items():
        if name.startswith(('haunch_', 'thigh_', 'shin_')):
            moved = value*amount
            result[name] -= moved; transfer += moved
    if transfer:
        result['pelvis'] = result.get('pelvis', 0)+transfer
    return {name: weight for name, weight in result.items() if weight > 1e-8}


def fascia_displacement(rest, scale, carrier_rotation, flexions):
    """Smooth lateral fascia bulges during tuck and vanishes during extension."""
    points = rest/scale; result = np.zeros_like(rest)
    for side, angle in flexions.items():
        tuck = smoothstep(.10, .70, -angle)
        support = np.exp(-((points[:, 1]-.18)/.135)**2-((points[:, 2]-.49)/.14)**2)
        support *= smoothstep(.07, .155, side*points[:, 0])*smoothstep(.31, .41, points[:, 2])*(1-smoothstep(.67, .80, points[:, 2]))
        result[:, 0] += side*.045*support*tuck*scale
    return result@carrier_rotation.T


class JointRelaxation:
    def __init__(self, rest, edges, scale):
        self.rest = np.asarray(rest, dtype=np.float64)
        self.unique, self.reverse = np.unique(np.round(self.rest/scale, 5), axis=0, return_inverse=True)
        self.counts = np.bincount(self.reverse)
        edges = self.reverse[np.asarray(edges)]
        edges = np.unique(np.sort(edges, axis=1), axis=0)
        edges = edges[edges[:, 0] != edges[:, 1]]
        self.a = np.concatenate([edges[:, 0], edges[:, 1]])
        self.b = np.concatenate([edges[:, 1], edges[:, 0]])
        self.degree = np.maximum(1, np.bincount(self.a, minlength=len(self.unique)))
        points = self.unique
        mask = smoothstep(.28, .43, points[:, 2])*(1-smoothstep(.71, .83, points[:, 2]))
        mask *= smoothstep(.018, .09, np.abs(points[:, 0]))
        hind = smoothstep(-.025, .10, points[:, 1])*(1-smoothstep(.39, .49, points[:, 1]))
        front = smoothstep(-.48, -.36, points[:, 1])*(1-smoothstep(-.21, -.09, points[:, 1]))
        self.mask = mask*np.maximum(hind, front)
        # Keep the diffusion distance stable across independently reduced LODs.
        lengths = np.linalg.norm(self.rest[self._representatives()][edges[:, 0]]-self.rest[self._representatives()][edges[:, 1]], axis=1)
        proximal = np.maximum(self.mask[edges[:, 0]], self.mask[edges[:, 1]]) > .2
        edge_length = np.median(lengths[proximal])
        self.iterations = max(12, round(150*(.0102*scale/max(edge_length, 1e-6))**2))
        self.iterations = min(250, self.iterations)
        smoothed = self.relax(self.rest)
        self.detail = self.rest-smoothed

    def _representatives(self):
        _, first = np.unique(self.reverse, return_index=True)
        return first

    def weld(self, positions):
        return np.column_stack([np.bincount(self.reverse, weights=positions[:, axis])/self.counts for axis in range(3)])

    def relax(self, positions):
        points = self.weld(positions)
        for _ in range(self.iterations):
            average = np.column_stack([np.bincount(self.a, weights=points[self.b, axis], minlength=len(points))/self.degree for axis in range(3)])
            points += (average-points)*self.mask[:, None]*.5
        return points[self.reverse]

    def delta(self, posed, rotations, fascia=None):
        target = self.relax(posed)+np.einsum('nij,nj->ni', rotations, self.detail)
        if fascia is not None:
            target += fascia
        difference = target-posed
        difference[self.mask[self.reverse] == 0] = 0
        # glTF applies morphs before skinning. Invert the actual blended linear
        # transform, not a single bone rotation, so the exported pose matches.
        return np.linalg.solve(rotations, difference[..., None])[..., 0]


def compact_modes(samples, maximum=12):
    """Zero-centred PCA retains zero correction as the exact rest basis."""
    values = np.asarray(samples, dtype=np.float64)
    flat = values.reshape(len(values), -1)
    gram = flat@flat.T
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1]
    positive = order[eigenvalues[order] > 1e-12][:maximum]
    basis = (eigenvectors[:, positive].T@flat)/np.sqrt(eigenvalues[positive])[:, None]
    amplitudes = flat@basis.T
    # Unit PCA directions have tiny coordinates and large weights. Scale modes
    # to their sampled extrema so delivery weights stay inside [-1, 1].
    ranges = np.maximum(np.abs(amplitudes).max(axis=0), 1e-12)
    modes = basis*ranges[:, None]
    weights = amplitudes/ranges
    reconstructed = (weights@modes).reshape(values.shape)
    errors = np.linalg.norm(values-reconstructed, axis=2)
    return modes.reshape((-1, *values.shape[1:])), weights, {
        'modes': len(modes), 'maximum_reconstruction_error_m': float(errors.max()),
        'p99_reconstruction_error_m': float(np.percentile(errors, 99)),
        'maximum_correction_m': float(np.linalg.norm(values, axis=2).max()),
    }


def compact_anatomical_modes(samples, rest, limit=.0015):
    """Independent limbs use sparse local modes instead of dense global modes."""
    values = np.asarray(samples)
    changed = np.abs(values).max(axis=(0, 2)) > 1e-9
    modes, weights, regions = [], [], []
    reconstructed = np.zeros_like(values)
    for left in [False, True]:
        for hind in [False, True]:
            selected = ((rest[:, 0] >= 0) == left)&((rest[:, 1] >= 0) == hind)&changed
            for count in range(4, 17, 2):
                local, coefficients, evidence = compact_modes(values[:, selected], count)
                if evidence['maximum_reconstruction_error_m'] <= limit:
                    break
            else:
                raise ValueError('Local corrective basis failed reconstruction bound')
            # Values below ten micrometres only amplify floating-point noise
            # and sparse storage. Re-measure the resulting approximation.
            local[np.linalg.norm(local, axis=2) < 1e-5] = 0
            full = np.zeros((len(local), len(rest), 3))
            full[:, selected] = local
            reconstructed[:, selected] = np.einsum('sk,knc->snc', coefficients, local)
            modes.extend(full); weights.append(coefficients)
            regions.append({'side': 'left' if left else 'right', 'limb': 'hind' if hind else 'front', **evidence})
    error = np.linalg.norm(values-reconstructed, axis=2)
    if error.max() > limit:
        raise ValueError('Sparse corrective storage failed reconstruction bound')
    return np.asarray(modes), np.concatenate(weights, axis=1), {
        'modes': len(modes), 'regions': regions,
        'maximum_reconstruction_error_m': float(error.max()),
        'p99_reconstruction_error_m': float(np.percentile(error, 99)),
        'maximum_correction_m': float(np.linalg.norm(values, axis=2).max()),
    }

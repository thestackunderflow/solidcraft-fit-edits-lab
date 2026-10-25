"""The V3 pass rule's measurements: round loops in a horizontal STL section (holes in the plate, pegs above the block),
circle fits, hole-peg pairs, the gap each side, and the pass rule (PLAN rev 2.1 §5.2: 0.20 ± tol each side, worst side
included, so a shifted peg fails)."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests'))
from stl_tools import section_segments  # noqa: E402


def circle_fit(pts):
    """Least-squares circle (Kasa): x^2 + y^2 + D x + E y + F = 0."""
    p = np.asarray(pts, dtype=float)
    A = np.column_stack([p[:, 0], p[:, 1], np.ones(len(p))])
    b = -(p[:, 0] ** 2 + p[:, 1] ** 2)
    D, E, F = np.linalg.lstsq(A, b, rcond=None)[0]
    c = np.array([-D / 2, -E / 2])
    return c, float(np.sqrt(c @ c - F))


def _loops(segs, tol=1e-4):
    """Group section segments into connected loops (by shared end points)."""
    pts, idx = [], {}

    def key(q):
        k = (round(q[0] / tol), round(q[1] / tol))
        if k not in idx:
            idx[k] = len(pts)
            pts.append(q)
        return idx[k]
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for a, b in segs:
        ia, ib = key(a), key(b)
        parent[find(ia)] = find(ib)
    groups = {}
    for i in range(len(pts)):
        groups.setdefault(find(i), []).append(pts[i])
    return [np.array(g) for g in groups.values()]


def rings(tris, z, max_r=10.0, min_vertices=8, max_rms=0.05):
    """Round loops (holes or pegs) in the section at height z: loops whose points sit on a circle (rms < max_rms)."""
    out = []
    for loop in _loops(section_segments(tris, z)):
        if len(loop) < min_vertices:
            continue
        c, r = circle_fit(loop)
        rms = float(np.sqrt(np.mean((np.hypot(loop[:, 0] - c[0], loop[:, 1] - c[1]) - r) ** 2)))
        if r <= max_r and rms <= max_rms:
            out.append({'centre': (float(c[0]), float(c[1])), 'r': r, 'vertices': len(loop), 'rms': rms})
    return out


def pair(holes, pegs):
    res = []
    for h in holes:
        if not pegs:
            break
        p = min(pegs, key=lambda q: np.hypot(q['centre'][0] - h['centre'][0], q['centre'][1] - h['centre'][1]))
        off = float(np.hypot(p['centre'][0] - h['centre'][0], p['centre'][1] - h['centre'][1]))
        g = h['r'] - p['r']
        res.append({'hole': h, 'peg': p, 'gap_each_side': g, 'offset': off, 'worst_side': g - off, 'best_side': g + off})
    return res


def passes(pairs, target=0.2, tol=0.03):
    if not pairs:
        return {'pass': False, 'why': 'no hole/peg pairs found'}
    for p in pairs:
        if abs(p['gap_each_side'] - target) > tol:
            return {'pass': False, 'why': f"gap each side {p['gap_each_side']:.3f} mm, not {target} ± {tol}"}
        if p['worst_side'] < target - tol:
            return {'pass': False, 'why': f"off centre by {p['offset']:.3f} mm: worst side {p['worst_side']:.3f}"}
    return {'pass': True, 'why': 'every pair 0.2 ± tol each side, centred'}

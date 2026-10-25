"""fit/gap.py: the V3 pass rule's measurements (PLAN rev 2.1 §5.2), proven on synthetic geometry first.
A hole and a peg are found as round loops in a horizontal section of an STL (the plate at mid-thickness, the peg block
just above its top), fitted with circles; each hole is paired with the nearest peg; the gap each side is
r_hole - r_peg, and the worst side is that minus the centre offset (a shifted peg gives 0.1 / 0.3, not 0.2 / 0.2)."""
import math
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fit import gap as G  # noqa: E402
from stl_tools import prism_tris  # noqa: E402


def ngon(cx, cy, r, n=36):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def test_circle_fit_recovers_centre_and_radius():
    c, r = G.circle_fit(np.array(ngon(3.0, -2.0, 2.7, 64)))
    assert np.allclose(c, (3.0, -2.0), atol=1e-6)
    assert r == pytest.approx(2.7 * (1 + math.cos(math.pi / 64)) / 2, abs=2e-3)


def test_rings_in_a_section_of_two_pegs():
    tris = np.concatenate([prism_tris(ngon(-20, 0, 2.5), 0, 5), prism_tris(ngon(20, 0, 2.5), 0, 5)])
    rings = G.rings(tris, z=2.5, max_r=10.0)
    assert len(rings) == 2
    xs = sorted(round(r['centre'][0], 3) for r in rings)
    assert xs == [-20.0, 20.0]
    assert all(r['vertices'] >= 36 for r in rings)   # side quads are 2 triangles: the diagonal adds a point


def test_pairing_gap_each_side_and_offset():
    holes = [{'centre': (-20.0, 0.0), 'r': 2.7}, {'centre': (20.0, 0.0), 'r': 2.7}]
    pegs = [{'centre': (-20.0, 0.0), 'r': 2.5}, {'centre': (20.1, 0.0), 'r': 2.5}]
    pairs = G.pair(holes, pegs)
    assert pairs[0]['gap_each_side'] == pytest.approx(0.2)
    assert pairs[0]['worst_side'] == pytest.approx(0.2)
    assert pairs[1]['offset'] == pytest.approx(0.1)
    assert pairs[1]['worst_side'] == pytest.approx(0.1)
    assert pairs[1]['best_side'] == pytest.approx(0.3)


def test_pass_rule():
    ok = [{'gap_each_side': 0.2, 'worst_side': 0.19, 'best_side': 0.21, 'offset': 0.01}]
    assert G.passes(ok, tol=0.03)['pass'] is True
    shifted = [{'gap_each_side': 0.2, 'worst_side': 0.1, 'best_side': 0.3, 'offset': 0.1}]
    assert G.passes(shifted, tol=0.03)['pass'] is False
    lost = [{'gap_each_side': 0.0, 'worst_side': 0.0, 'best_side': 0.0, 'offset': 0.0}]
    r = G.passes(lost, tol=0.03)
    assert r['pass'] is False and 'gap' in r['why']

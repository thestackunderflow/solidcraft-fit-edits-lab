"""Section drawings for V3 from the scored STLs (no AI, no repainting): a vertical cut through the pegs (plane y = 15,
the parts' middle), plate in light grey, peg block darker, seen from the front.

    docker run --rm -v <lab>:/work -w /work solidcraft-fit-edits-lab:0.22.0 python3 video/draw_fit.py

  fit-edit3-blind.png    claudemd-1 after edit 3: the middle hole stops short of the plate's top (blind)
  fit-edit3-through.png  once-1 after edit 3: all three holes go through
  fit-gap-zoom.png       once-1 after edit 1: one 6 mm peg in its 6.4 mm hole, zoomed: 0.2 mm each side
"""
import json
import os
import struct
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAB = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(LAB, 'tests'))
from stl_tools import read_stl, section_segments  # noqa: E402

OUT = os.path.join(HERE, 'frames')
BG, PLATE, BLOCK, EDGE = (236, 239, 244), (176, 186, 200), (71, 85, 105), (31, 41, 55)


def png(path, img):
    h, w, _ = img.shape
    raw = b''.join(b'\x00' + img[y].astype(np.uint8).tobytes() for y in range(h))

    def chunk(t, d):
        c = struct.pack('>I', len(d)) + t + d
        return c + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) +
                           chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))


def xsection(tris, y):
    """Segments of the cut by the plane at this y, in (x, z): swap y and z, then a horizontal section."""
    t = np.asarray(tris, dtype=float)[:, :, [0, 2, 1]]
    return section_segments(t, y)


def fill(segs, X, Z):
    """Even-odd fill of closed outlines given as segments (a ray to +x crosses the outline an odd number of times)."""
    inside = np.zeros(X.shape, dtype=bool)
    for a, b in segs:
        (xa, za), (xb, zb) = a, b
        cond = (za > Z) != (zb > Z)
        with np.errstate(divide='ignore', invalid='ignore'):
            xc = xa + (Z - za) * (xb - xa) / (zb - za)
        inside ^= cond & (X < xc)
    return inside


def draw(name, plate_stl, block_stl, x0, x1, z0, z1, w, roof=None):
    h = int(round(w * (z1 - z0) / (x1 - x0)))
    xx, zz = np.meshgrid(np.arange(w), np.arange(h))
    X = x0 + (xx + 0.5) * (x1 - x0) / w
    Z = z1 - (zz + 0.5) * (z1 - z0) / h
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = BG
    p = fill(xsection(read_stl(plate_stl), 15.0), X, Z)
    b = fill(xsection(read_stl(block_stl), 15.0), X, Z)
    img[b] = BLOCK
    img[p] = PLATE
    if roof is not None:
        rx0, rx1, rz0, rz1 = roof
        img[p & (X >= rx0) & (X <= rx1) & (Z >= rz0) & (Z <= rz1)] = (183, 28, 28)
    os.makedirs(OUT, exist_ok=True)
    png(os.path.join(OUT, name + '.png'), img)
    return {'name': name, 'window_mm': [x0, x1, z0, z1], 'size_px': [w, h]}


R = os.path.join(LAB, 'out', 'runs')
s = lambda run, e, part: os.path.join(R, run, f'edit-{e}', 'score', f'{part}.stl')  # noqa: E731
made = [draw('fit-edit3-blind', s('claudemd-1', 3, 'plate'), s('claudemd-1', 3, 'block'), -2, 82, -1, 14, 1600),
        draw('fit-edit3-through', s('once-1', 3, 'plate'), s('once-1', 3, 'block'), -2, 82, -1, 14, 1600)]
# zoom on one peg in its hole after edit 1 (once-1): find the first hole's centre from the score
sc = json.load(open(os.path.join(R, 'once-1', 'edit-1', 'score.json'), encoding='utf-8'))
made.append(draw('fit-gap-zoom', s('once-1', 1, 'plate'), s('once-1', 1, 'block'), 16.0, 24.0, 3.0, 10.0, 1600))
for e in range(4):
    made.append(draw(f'fit-once1-edit{e}', s('once-1', e, 'plate'), s('once-1', e, 'block'), -2, 82, -1, 14, 1600))
made.append(draw('fit-edit3-blind-red', s('claudemd-1', 3, 'plate'), s('claudemd-1', 3, 'block'), -2, 82, -1, 14, 1600, roof=(36.7, 43.3, 9.0, 12.0)))
made.append(draw('fit-cut-zoom', s('claudemd-1', 3, 'plate'), s('claudemd-1', 3, 'block'), 14, 66, -1, 14, 1600, roof=(36.7, 43.3, 9.0, 12.0)))
json.dump(made, open(os.path.join(OUT, 'fit-drawings.json'), 'w'), indent=1)
print(made)

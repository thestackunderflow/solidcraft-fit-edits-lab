"""V3 probe (no AI, $0): the reference plate + peg block in SolidCraft 0.22.0, exported per body, and the lab's gap
measurement (fit/gap.py) on the STLs: does the measurement see 0.20 mm each side? Also a 'lost gap' cell (hole = peg)
and a 'shifted' cell (one peg 0.1 mm off). docker run ... python3 probe/probe.py"""
import json, os, sys
LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(LAB, 'tests')); sys.path.insert(0, LAB)
from mcp_client import McpClient
from stl_tools import read_stl
from fit import gap as G
OUT = '/lab/out'


def call(m, n, a):
    r = m.call_tool(n, a); t = '\n'.join(b['text'] for b in r.get('content', []) if b.get('type') == 'text')
    try: return json.loads(t)
    except Exception: return t


def build(name, hole_d=5.4, peg_d=5.0, xs=(-20.0, 20.0), shift=0.0):
    d = os.path.join(OUT, name); os.makedirs(d, exist_ok=True)
    m = McpClient(['solidcraft-cli', 'mcp', '--allow-path', OUT]); m.start()
    call(m, 'new_design', {'name': name})
    cmds = [{'command': 'solid.box', 'params': {'length': 80, 'width': 30, 'height': 4, 'center': [0, 0, 2], 'body_name': 'PegBlock'}},
            {'command': 'sketch.create', 'params': {'plane': 'XY', 'offset': 4, 'name': 'Pegs'}}]
    for i, x in enumerate(xs):
        cmds.append({'command': 'sketch.circle.center', 'params': {'center': [x + (shift if i == 1 else 0.0), 0], 'diameter': peg_d}})
    cmds += [{'command': 'sketch.finish', 'params': {}},
             {'command': 'solid.extrude', 'params': {'sketch': 'Pegs', 'distance': 5, 'operation': 'join', 'targets': ['PegBlock']}},
             {'command': 'solid.box', 'params': {'length': 80, 'width': 30, 'height': 5, 'center': [0, 0, 6.5], 'body_name': 'Plate'}}]
    for x in xs:
        cmds.append({'command': 'solid.hole', 'params': {'position': [x, 0, 9], 'diameter': hole_d, 'targets': ['Plate']}})
    r = call(m, 'batch', {'commands': cmds})
    call(m, 'export', {'path': f'{d}/plate.stl', 'bodies': ['Plate']})
    call(m, 'export', {'path': f'{d}/block.stl', 'bodies': ['PegBlock']})
    m.close()
    holes = G.rings(read_stl(f'{d}/plate.stl'), z=6.5)
    pegs = G.rings(read_stl(f'{d}/block.stl'), z=6.5)
    pairs = G.pair(holes, pegs)
    res = {'cell': name, 'ok': r.get('ok') if isinstance(r, dict) else r, 'holes': holes, 'pegs': pegs,
           'pairs': [{k: v for k, v in p.items() if k not in ('hole', 'peg')} for p in pairs], 'verdict': G.passes(pairs)}
    json.dump(res, open(f'{d}/summary.json', 'w'), indent=1)
    print(name, res['ok'], [round(p['gap_each_side'], 4) for p in pairs], res['verdict'])


build('ref')
build('lost', hole_d=5.0)
build('shifted', shift=0.1)

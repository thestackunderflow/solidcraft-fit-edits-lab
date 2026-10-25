"""Score a V3 run's saved designs (inside the lab image; the run folder mounted as /lab/out):

    python3 claude-run/score.py design /lab/out          -> edit-N/score.json for every edit
    python3 claude-run/score.py table                    (host or image) -> out/runs/SCORES.json

Per edit: open the saved design, find the plate and the peg block (by name, else the thinner body with holes = plate),
export each as STL, and measure in sections (fit/gap.py): every hole/peg pair's gap each side and centre offset at the
plate's mid-height, holes still through (rings near the plate's top AND bottom), peg engagement in the plate (>= 4 mm),
the parameters list (is there a fit_gap, and what is it). Pass rule (PLAN rev 2.1 §5.2): every pair 0.20 ± 0.03 each side,
centred; holes through; engagement >= 4 mm; the expected number of pairs (2, then 3 after edit 2)."""
import glob
import json
import os
import sys

LAB = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(LAB, 'tests'))
sys.path.insert(0, LAB)

EXPECT_PAIRS = {0: 2, 1: 2, 2: 3, 3: 3}
EXPECT_PEG = {0: 5.0, 1: 6.0, 2: 6.0, 3: 6.0}


def score_edit(edit_dir, edit):
    from mcp_client import McpClient
    from stl_tools import read_stl
    from fit import gap as G

    def call(m, n, a):
        r = m.call_tool(n, a)
        t = '\n'.join(b['text'] for b in r.get('content', []) if b.get('type') == 'text')
        try:
            return json.loads(t)
        except Exception:
            return t
    d = os.path.join(edit_dir, 'score')
    os.makedirs(d, exist_ok=True)
    res = {'edit': edit}
    src = os.path.join(edit_dir, 'work', 'fit.solidcraft')
    if not os.path.exists(src):
        res.update({'pass': False, 'why': 'no saved design'})
        return res
    m = McpClient(['solidcraft-cli', 'mcp', '--allow-path', '/lab/out'])
    m.start()
    try:
        res['open'] = call(m, 'open', {'path': src})
        meas = call(m, 'measure', {})
        bodies = meas.get('bodies', []) if isinstance(meas, dict) else []
        res['bodies'] = [{'name': b['name'], 'bbox': b['bbox'], 'volume_mm3': b['volume_mm3']} for b in bodies]
        names = [b['name'] for b in bodies]
        plate = next((n for n in names if 'plate' in n.lower()), None)
        block = next((n for n in names if 'peg' in n.lower() or 'block' in n.lower()), None)
        plist = call(m, 'execute', {'command': 'parameters.list', 'params': {}})
        res['parameters'] = {p['name']: {'expression': p['expression'], 'value': p['value']}
                             for p in (plist.get('parameters', []) if isinstance(plist, dict) else [])
                             if p.get('source') == 'user'}
        if not plate or not block:
            res.update({'pass': False, 'why': f'bodies not found: {names}'})
            return res
        call(m, 'export', {'path': f'{d}/plate.stl', 'bodies': [plate]})
        call(m, 'export', {'path': f'{d}/block.stl', 'bodies': [block]})
    finally:
        m.close()
    pb = next(b for b in bodies if b['name'] == plate)['bbox']
    z0, z1 = pb['min'][2], pb['max'][2]
    zm = (z0 + z1) / 2
    pt, bt = read_stl(f'{d}/plate.stl'), read_stl(f'{d}/block.stl')
    holes = G.rings(pt, z=zm)
    pegs = G.rings(bt, z=min(zm, z0 + 0.5))
    pairs = G.pair(holes, pegs)
    through = len(G.rings(pt, z=z1 - 0.3)) == len(holes) and len(G.rings(pt, z=z0 + 0.3)) == len(holes)
    peg_top = max(b['bbox']['max'][2] for b in bodies if b['name'] == block)
    engage = min(peg_top, z1) - z0
    verdict = G.passes(pairs)
    ok = verdict['pass'] and through and engage >= 4.0 - 1e-6 and len(pairs) == EXPECT_PAIRS[edit]
    why = verdict['why'] if not verdict['pass'] else ('holes not through' if not through else
          (f'engagement {engage:.2f} mm' if engage < 4.0 - 1e-6 else
           (f'{len(pairs)} pairs, expected {EXPECT_PAIRS[edit]}' if len(pairs) != EXPECT_PAIRS[edit] else 'pass')))
    res.update({'plate': plate, 'block': block, 'plate_z': [z0, z1],
                'pairs': [{'hole_d': round(2 * p['hole']['r'], 4), 'peg_d': round(2 * p['peg']['r'], 4),
                           'gap_each_side': round(p['gap_each_side'], 4), 'offset': round(p['offset'], 4),
                           'worst_side': round(p['worst_side'], 4)} for p in pairs],
                'holes_through': through, 'engagement_mm': round(engage, 3), 'pass': bool(ok), 'why': why,
                'pegs_expected_d': EXPECT_PEG[edit]})
    return res


def design(run_root):
    for e in range(4):
        ed = os.path.join(run_root, f'edit-{e}')
        if not os.path.isdir(ed):
            continue
        r = score_edit(ed, e)
        json.dump(r, open(os.path.join(ed, 'score.json'), 'w', encoding='utf-8'), indent=1, default=str)
        print(json.dumps({k: r.get(k) for k in ('edit', 'pass', 'why', 'pairs')}, default=str))


def table():
    rows = []
    for rd in sorted(glob.glob(os.path.join(LAB, 'out', 'runs', '*-*'))):
        if not os.path.isdir(rd):
            continue
        row = {'run': os.path.basename(rd), 'edits': []}
        for e in range(4):
            p = os.path.join(rd, f'edit-{e}', 'score.json')
            if os.path.exists(p):
                s = json.load(open(p, encoding='utf-8'))
                row['edits'].append({'edit': e, 'pass': s.get('pass'), 'why': s.get('why'),
                                     'gaps': [x['gap_each_side'] for x in s.get('pairs', [])],
                                     'fit_gap': s.get('parameters', {}).get('fit_gap')})
        row['kept_through_all'] = bool(row['edits']) and all(x['pass'] for x in row['edits']) and len(row['edits']) == 4
        rows.append(row)
    json.dump({'runs': rows}, open(os.path.join(LAB, 'out', 'runs', 'SCORES.json'), 'w', encoding='utf-8'), indent=1)
    for r in rows:
        print(r['run'], 'kept' if r['kept_through_all'] else 'LOST', [(x['edit'], x['pass'], x['why']) for x in r['edits']])


if __name__ == '__main__':
    if sys.argv[1] == 'design':
        design(sys.argv[2])
    elif sys.argv[1] == 'table':
        table()

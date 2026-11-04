"""Compose a chapter scene from its spec into ink + wash PNGs, in portrait (landing) and band (chapter header)."""
import sys, json, os
from core import Ink
import motifs as M
import importlib
for _m in ('motifs_nature', 'motifs_space', 'motifs_subjects'):
    try:
        _mod = importlib.import_module(_m)
        M.BACKDROPS.update(getattr(_mod, 'BACKDROPS', {})); M.SUBJECTS.update(getattr(_mod, 'SUBJECTS', {}))
    except ModuleNotFoundError:
        pass
from render import Renderer, ink_mask, preview

FORMATS = {'portrait': (900, 1500), 'band': (1200, 520)}

# Relative size of each subject at the focus slot (1.0 = the slot's base size).
SIZE = {'spider': 0.46, 'beetle': 0.45, 'monkey': 0.55, 'ant-column': 1.3, 'spider-crowd': 0.85, 'spiderlings': 1.2,
        'web': 1.05, 'silk-thread': 1.3, 'figure': 0.85, 'suited-figure': 0.85, 'crowd': 1.4, 'cryo-pod': 0.85,
        'console': 0.75, 'screen-face': 0.7, 'ark-ship': 1.25, 'shuttle': 0.9, 'satellite': 0.8, 'station-ring': 1.0,
        'planet': 0.9, 'moon': 0.6, 'gas-giant': 1.0, 'fire': 0.8, 'explosion': 1.1, 'balloon': 0.85, 'rocket': 0.9,
        'tree': 1.2, 'crystal-spire': 0.9, 'cage': 0.8, 'wreck': 1.1, 'lens': 0.7, 'signal-waves': 1.1, 'stars': 1.6,
        'egg-clutch': 0.6, 'fungus': 0.8, 'elevator-thread': 1.3, 'living-ship': 1.0, 'streak': 1.1, 'dais': 0.9}
# Subjects that fill the space behind the others: drawn first, centred, regardless of order.
AMBIENT = {'stars', 'signal-waves', 'crowd', 'spider-crowd', 'spiderlings', 'silk-thread', 'elevator-thread'}
# Backdrops that already draw a world: a 'planet' subject would duplicate it.
HAS_PLANET = {'planet-orbit', 'orbital-web', 'station-exterior'}

def plan(spec, fmt):
    """[(name, x, y, s)] in drawing order: ambient first, then supporting subjects at the sides, focus last."""
    W, H = FORMATS[fmt]
    subs = [n for n in spec['subjects'] if not (n == 'planet' and spec['backdrop'] in HAS_PLANET)]
    if not subs: return []
    close = spec.get('camera', 'close') == 'close'
    if fmt == 'portrait':
        cx, cy, base = W * 0.5, H * 0.4, W * (0.36 if close else 0.24)
        sides = [(W * 0.24, H * 0.47), (W * 0.77, H * 0.3)]
    else:
        cx, cy, base = W * 0.5, H * 0.52, H * (0.42 if close else 0.3)
        sides = [(W * 0.2, H * 0.58), (W * 0.8, H * 0.45)]
    focus = subs[0]
    out = []
    # web + spider: the spider sits at the web's hub
    if 'web' in subs and 'spider' in subs:
        out.append(('web', cx, cy, base * SIZE['web']))
        out.append(('spider', cx, cy + base * 0.02, base * 0.42))
        rest = [n for n in subs if n not in ('web', 'spider')]
        for n, (x, y) in zip(rest, sides):
            out.insert(0, (n, x, y, base * 0.55 * SIZE.get(n, 1)))
        return out
    ambient = [n for n in subs[1:] if n in AMBIENT]
    support = [n for n in subs[1:] if n not in AMBIENT]
    for n in ambient:
        out.append((n, cx, cy + (base * 0.15 if n == 'crowd' else 0), base * SIZE.get(n, 1)))
    for n, (x, y) in zip(support, sides):
        out.append((n, x, y, base * 0.55 * SIZE.get(n, 1)))
    out.append((focus, cx, cy, base * SIZE.get(focus, 1)))
    return out

def compose(spec, fmt, seed=1):
    W, H = FORMATS[fmt]
    k = Ink(W, H, seed=seed)
    M.BACKDROPS[spec['backdrop']](k, spec)
    for name, x, y, s in plan(spec, fmt):
        M.SUBJECTS[name](k, x, y, s, spec)
    return k

def render_spec(r, spec, fmt, out_png, seed=1):
    W, H = FORMATS[fmt]
    k = compose(spec, fmt, seed)
    ink = ink_mask(r.png(k.svg('ink'), W, H)); wash = r.png(k.svg('wash'), W, H)
    preview(ink, wash).save(out_png)
    return ink, wash

if __name__ == '__main__':
    spec = {"backdrop": "forest-canopy", "subjects": ["web", "spider"], "light": "dawn", "camera": "close",
            "wash": ["#C9E3C2", "#F3D9B8"], "caption": "A hunter waits on her thread"}
    with Renderer() as r:
        for fmt in ('portrait', 'band'):
            k = compose(spec, fmt)
            W, H = FORMATS[fmt]
            ink = ink_mask(r.png(k.svg('ink'), W, H)); wash = r.png(k.svg('wash'), W, H)
            preview(ink, wash).save(f'/tmp/claude-0/-home-claude/a0bfae2e-11b9-5741-b301-a203a6bdce2f/scratchpad/style/test-{fmt}.png')
    print('ok')

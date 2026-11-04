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

def placements(fmt, n, camera):
    """Where subjects sit: the focus large and central, others smaller beside it."""
    W, H = FORMATS[fmt]
    if fmt == 'portrait':
        base = [(W * 0.5, H * 0.4, W * (0.36 if camera == 'close' else 0.24)), (W * 0.53, H * 0.41, W * 0.16), (W * 0.72, H * 0.2, W * 0.08)]
    else:
        base = [(W * 0.5, H * 0.52, H * (0.4 if camera == 'close' else 0.26)), (W * 0.53, H * 0.55, H * 0.2), (W * 0.78, H * 0.35, H * 0.1)]
    return base[:n]

def compose(spec, fmt, seed=1):
    W, H = FORMATS[fmt]
    k = Ink(W, H, seed=seed)
    M.BACKDROPS[spec['backdrop']](k, spec)
    subs = spec['subjects']
    for name, (x, y, s) in zip(subs, placements(fmt, len(subs), spec.get('camera', 'close'))):
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

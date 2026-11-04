"""Draw every chapter scene of a companion into art/scenes/.

Usage: python3 build_book.py <companion.json> <out art dir> [--only href,href] [--preview dir]
Per chapter: <stem>-p-ink.png / -p-wash.png (portrait, landing and title card) and -b-ink.png / -b-wash.png (band,
chapter header). Ink is an alpha mask the app tints; wash is colour at a third of the size (it is soft anyway).
"""
import sys, os, json, argparse
from PIL import Image
from compose import compose, FORMATS
from render import Renderer, ink_mask, preview

ap = argparse.ArgumentParser()
ap.add_argument('companion'); ap.add_argument('out'); ap.add_argument('--only'); ap.add_argument('--preview')
a = ap.parse_args()
comp = json.load(open(a.companion))
out = os.path.join(a.out, 'scenes'); os.makedirs(out, exist_ok=True)
only = set(a.only.split(',')) if a.only else None
n = 0
with Renderer() as r:
    for i, ch in enumerate(comp['chapters']):
        sc = ch.get('scene')
        if not sc or (only and ch['href'] not in only): continue
        stem = os.path.splitext(ch['href'])[0].replace('/', '_')
        for fmt, tag in (('portrait', 'p'), ('band', 'b')):
            W, H = FORMATS[fmt]
            k = compose(sc, fmt, seed=i + 1)
            ink = ink_mask(r.png(k.svg('ink'), W, H, scale=1.4))
            wash = r.png(k.svg('wash'), W, H)
            ink.save(os.path.join(out, f'{stem}-{tag}-ink.png'), optimize=True)
            wash.resize((W // 3, H // 3), Image.LANCZOS).save(os.path.join(out, f'{stem}-{tag}-wash.png'), optimize=True)
            if a.preview:
                os.makedirs(a.preview, exist_ok=True)
                preview(ink.resize((W, H)), wash).save(os.path.join(a.preview, f'{stem}-{tag}.png'))
        n += 1
print(f'drew {n} chapter scenes')

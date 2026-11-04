"""Motif library. Backdrops paint a place across the frame; subjects draw a thing at (x, y) with size s.
All take an Ink and a palette-free spec; colour comes only from the wash."""
import math

# ---------------- backdrops ----------------
def forest_canopy(k, spec):
    W, H = k.w, k.h; w0, w1 = spec['wash']
    k.watercolour(W * 0.5, H * 0.18, W * 0.7, H * 0.25, w0, 0.6)
    k.watercolour(W * 0.62, H * 0.5, W * 0.35, H * 0.3, w1, 0.45)
    # light shafts from upper left, ruled faintly
    for i in range(6):
        x = W * (-0.05 + i * 0.16) + k.r.uniform(-15, 15)
        k.line(f'M{x:.0f},0 L{x + W * 0.32:.0f},{H * 0.85:.0f}', 0.5, 0.18, rough=False)
    # far: thin trunks and a pale canopy
    k.depth = 0.15
    for j in range(5):
        x = W * (0.08 + j * 0.21) + k.r.uniform(-30, 30); w = W * k.r.uniform(0.02, 0.035)
        k.shape(trunk(k, x, w, H * 0.1, H + 30, lean=k.r.uniform(-10, 10)), tone=1, dark=2, outline=0.6)
    k.shape(k.foliage(-40, W + 40, H * 0.2, 30, 16), tone=1, dark=2, outline=0.7)
    # mid: heavier canopy band
    k.depth = 0.5
    k.shape(k.foliage(-40, W + 40, H * 0.11, 40, 13), tone=2, dark=3, outline=1.0)
    k.leafmarks(0, W, H * 0.02, H * 0.12, 160)
    for x, L in ((W * 0.3, H * 0.36), (W * 0.66, H * 0.26)):
        vine(k, x, H * 0.08, L)
    # near: framing trunks with bark, a dark leaf mass at the top corner, ferns at the foot
    k.depth = 0.95
    for x, w, lean in ((W * 0.04, W * 0.13, 22), (W * 0.95, W * 0.17, -26)):
        k.shape(trunk(k, x, w, -20, H + 20, lean), tone=2, dark=4, angle=82)
        bark(k, x, w, lean)
    k.shape(k.foliage(W * 0.55, W + 60, H * 0.05, 34, 7, top=-80), tone=3, dark=4, outline=1.2)
    k.leafmarks(W * 0.6, W, 0, H * 0.06, 60)
    vine(k, W * 0.82, H * 0.04, H * 0.5)
    for x in (W * 0.12, W * 0.3, W * 0.78, W * 0.92):
        fern(k, x, H * 1.0, H * k.r.uniform(0.12, 0.2))

def fern(k, x, y, L):
    lean = k.r.uniform(-0.5, 0.5)
    pts = [(x + math.sin(t * 1.4) * L * 0.25 * lean + t * L * lean * 0.6, y - t * L) for t in [i / 10 for i in range(11)]]
    k.line(k.smooth(pts, close=False), 1.1)
    for i in range(1, 10):
        px, py = pts[i]; sz = L * 0.16 * (1 - i / 11)
        for s in (-1, 1):
            leaf = k.smooth([(px, py), (px + s * sz * 0.6, py - sz * 0.5), (px + s * sz * 1.1, py - sz * 0.2), (px + s * sz * 0.5, py + sz * 0.05)])
            k.shape(leaf, tone=2, dark=3, outline=0.6, rough=False)

def trunk(k, x, w, top, bottom, lean=0):
    h = bottom - top
    pts = [(x - w / 2, bottom), (x - w * 0.42 + lean * 0.3, top + h * 0.6), (x - w * 0.36 + lean, top + h * 0.15), (x - w * 0.33 + lean * 1.1, top),
           (x + w * 0.33 + lean * 1.1, top), (x + w * 0.36 + lean, top + h * 0.15), (x + w * 0.42 + lean * 0.3, top + h * 0.6), (x + w / 2, bottom)]
    return k.smooth(pts)

def bark(k, x, w, lean):
    for i in range(7):
        t = k.r.uniform(-0.3, 0.3)
        y0 = k.r.uniform(0, k.h * 0.6); L = k.r.uniform(k.h * 0.1, k.h * 0.3)
        k.line(f'M{x + w * t + lean * (1 - y0 / k.h):.1f},{y0:.0f} q{k.r.uniform(-6, 6):.1f},{L / 2:.0f} {k.r.uniform(-4, 4):.1f},{L:.0f}', 0.8, 0.8)

def vine(k, x, y0, L):
    pts = [(x + math.sin(i * 0.8 + x) * 7, y0 + L * i / 10) for i in range(11)]
    k.line(k.smooth(pts, close=False), 1.4)
    for i in range(2, 10, 2):
        px, py = pts[i]; s = k.r.choice((-1, 1))
        leaf = k.smooth([(px, py), (px + s * 14, py + 4), (px + s * 22, py + 12), (px + s * 10, py + 10)], close=True)
        k.shape(leaf, tone=1, dark=3, outline=0.8)

# ---------------- subjects ----------------
def web(k, x, y, s, spec=None):
    k.depth = 0.85
    n = 15; R = s
    ang = [i / n * 2 * math.pi + k.r.uniform(-0.08, 0.08) for i in range(n)]
    rad = [R * k.r.uniform(0.85, 1.08) for _ in range(n)]
    for a, r in zip(ang, rad):
        k.line(f'M{x:.1f},{y:.1f} L{x + math.cos(a) * r:.1f},{y + math.sin(a) * r:.1f}', 0.6, rough=False)
    # spiral: sagging chords between spokes
    t = 0.14
    while t < 1.0:
        d = ''
        for i in range(n + 1):
            a, r = ang[i % n], rad[i % n] * t
            px, py = x + math.cos(a) * r, y + math.sin(a) * r
            if i == 0: d = f'M{px:.1f},{py:.1f}'
            else:
                a0, r0 = ang[(i - 1) % n], rad[(i - 1) % n] * t
                mx, my = (px + x + math.cos(a0) * r0) / 2, (py + y + math.sin(a0) * r0) / 2
                sag = (mx - x, my - y); L = math.hypot(*sag) or 1
                d += f' Q{mx - sag[0] / L * 2.5:.1f},{my - sag[1] / L * 2.5:.1f} {px:.1f},{py:.1f}'
        k.line(d, 0.45, rough=False)
        t += 0.075 + t * 0.02
    # anchor threads off-frame
    for a in (ang[2], ang[7], ang[12]):
        k.line(f'M{x + math.cos(a) * R:.1f},{y + math.sin(a) * R:.1f} L{x + math.cos(a) * R * 2.2:.1f},{y + math.sin(a) * R * 2.2:.1f}', 0.5, rough=False)
    # dew: small open circles catching light
    dots = ''
    for _ in range(40):
        a = k.r.uniform(0, 2 * math.pi); r = R * math.sqrt(k.r.uniform(0.04, 1))
        dots += f'<circle cx="{x + math.cos(a) * r:.1f}" cy="{y + math.sin(a) * r:.1f}" r="{k.r.uniform(1.2, 2.4):.1f}" fill="#fff" stroke="#000" stroke-width=".6"/>'
    k.ink.append(f'<g>{dots}</g>')
    if spec: k.tint(k.blob(x, y, R * 0.8, R * 0.8), spec['wash'][1], 0.35, 20)

def tapered(k, pts, w0, w1):
    """A tapering stroke as a filled outline through pts."""
    left, right = [], []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        x2, y2 = pts[min(i + 1, n - 1)]; x1, y1 = pts[max(i - 1, 0)]
        dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1
        w = w0 + (w1 - w0) * i / (n - 1)
        left.append((x - dy / L * w, y + dx / L * w)); right.append((x + dy / L * w, y - dx / L * w))
    return k.smooth(left + right[::-1])

def spider(k, x, y, s, spec=None):
    """A jumping spider as an engraver would: near-solid ink body, fine white highlights, bristled legs."""
    k.depth = 1.0
    parts = []
    for side in (-1, 1):
        for i, (a1, a2, l) in enumerate(((-120, -95, 1.0), (-150, -170, 0.85), (160, 175, 0.8), (125, 100, 0.95))):
            bx, by = x + side * s * 0.12, y - s * 0.05 + i * s * 0.08
            r1, r2 = math.radians(a1), math.radians(a2)
            kx, ky = bx - side * math.cos(r1) * s * 0.45 * l, by + math.sin(r1) * s * 0.45 * l
            fx, fy = kx - side * math.cos(r2) * s * 0.5 * l, ky + math.sin(r2) * s * 0.5 * l
            pts = [(bx, by), ((bx + kx) / 2, (by + ky) / 2 - s * 0.05), (kx, ky), ((kx + fx) / 2, (ky + fy) / 2 + s * 0.02), (fx, fy)]
            parts.append(tapered(k, pts, s * 0.045, s * 0.012))
            for t in range(1, 4):           # bristles
                px, py = pts[t]
                k.line(f'M{px:.1f},{py:.1f} l{side * s * 0.03:.1f},{-s * 0.03:.1f}', 0.6, rough=False)
    for d in parts: k.solid(d)
    ab = k.blob(x, y + s * 0.38, s * 0.24, s * 0.32, n=14, jitter=0.03)
    ce = k.blob(x, y - s * 0.06, s * 0.22, s * 0.2, n=14, jitter=0.03)
    k.solid(ab); k.solid(ce)
    # white engraved highlights: curved strokes on the light side, chevrons on the abdomen
    hl = []
    for t in range(4):
        hl.append(f'M{x - s * (0.17 - t * 0.02):.1f},{y + s * (0.2 + t * 0.09):.1f} q{s * 0.04:.1f},{-s * 0.06:.1f} {s * 0.1:.1f},{-s * 0.09:.1f}')
    for t in (0.28, 0.4, 0.52):
        hl.append(f'M{x - s * 0.12:.1f},{y + s * t:.1f} L{x:.1f},{y + s * (t + 0.05):.1f} L{x + s * 0.12:.1f},{y + s * t:.1f}')
    hl.append(f'M{x - s * 0.16:.1f},{y - s * 0.12:.1f} q{s * 0.08:.1f},{-s * 0.1:.1f} {s * 0.2:.1f},{-s * 0.1:.1f}')
    k.ink.append(f'<path d="{" ".join(hl)}" fill="none" stroke="#fff" stroke-width="{max(1.0, s * 0.012):.1f}" stroke-linecap="round"/>')
    for side in (-1, 1):        # eyes: glints only, the eyes themselves are ink
        ex, ey = x + side * s * 0.075, y - s * 0.17
        k.ink.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{s * 0.055:.1f}" fill="#000" stroke="#fff" stroke-width="{max(.8, s * .008):.1f}"/>'
                     f'<circle cx="{ex - s * 0.018:.1f}" cy="{ey - s * 0.02:.1f}" r="{s * 0.016:.1f}" fill="#fff"/>')
    if spec: k.watercolour(x, y + s * 0.2, s * 0.4, s * 0.5, spec['wash'][1], 0.4, 3)

BACKDROPS = {'forest-canopy': forest_canopy}
SUBJECTS = {'web': web, 'spider': spider}

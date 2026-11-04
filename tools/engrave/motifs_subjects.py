"""Subject motifs: creatures, people, machines and phenomena, each drawn centred at (x, y) with size s (~radius).
Creatures follow motifs.spider (near-solid ink, fine white highlight strokes); machines are crisp outlines with
hatched shading; people are small engraved back views. Group subjects spread within ~2s of (x, y)."""
import math
from motifs import tapered, spider as _spider

TAU = 2 * math.pi

# ---------------- helpers ----------------
def _wash(k, spec, x, y, rx, ry, i=1, op=0.4, n=3):
    if spec and spec.get('wash'):
        k.watercolour(x, y, rx, ry, spec['wash'][i % len(spec['wash'])], op, n)

def _wrap(k, start, attrs):
    """Group every ink element added since `start` under one <g> (transform, clip, opacity)."""
    items = k.ink[start:]; del k.ink[start:]
    k.ink.append(f'<g {attrs}>{"".join(items)}</g>')

def _clip(k, d):
    cid = k.uid('c'); k.defs.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>'); return cid

def _ell(cx, cy, rx, ry, a=0.0, t0=0.0, t1=TAU, n=40):
    ca, sa = math.cos(a), math.sin(a)
    out = []
    for i in range(n + 1):
        t = t0 + (t1 - t0) * i / n
        ex, ey = math.cos(t) * rx, math.sin(t) * ry
        out.append((cx + ex * ca - ey * sa, cy + ex * sa + ey * ca))
    return out

def _oval(cx, cy, rx, ry):
    return (f'M{cx - rx:.1f},{cy:.1f} a{rx:.1f},{ry:.1f} 0 1,0 {2 * rx:.1f},0 a{rx:.1f},{ry:.1f} 0 1,0 {-2 * rx:.1f},0Z')

def _oblob(k, cx, cy, rx, ry, a=0.0, n=14, jitter=0.04):
    pts = []
    for i in range(n):
        t = i / n * TAU; s = 1 + k.r.uniform(-jitter, jitter)
        ex, ey = math.cos(t) * rx * s, math.sin(t) * ry * s
        pts.append((cx + ex * math.cos(a) - ey * math.sin(a), cy + ex * math.sin(a) + ey * math.cos(a)))
    return k.smooth(pts)

def _white(k, d, w):
    k.ink.append(f'<path d="{d}" fill="none" stroke="#fff" stroke-width="{w:.2f}" stroke-linecap="round" stroke-linejoin="round"/>')

def _thin(k, d, w, op=1.0):
    """A crisp fine line that ignores depth scaling (machine detail)."""
    k.ink.append(f'<path d="{d}" fill="none" stroke="#000" stroke-width="{w:.2f}" stroke-opacity="{op}" stroke-linecap="round" stroke-linejoin="round"/>')

def _dots(k, pts, r, fill='#000', stroke=None, sw=0.6):
    st = f' stroke="{stroke}" stroke-width="{sw}"' if stroke else ''
    k.ink.append(f'<g fill="{fill}"{st}>' + ''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr:.2f}"/>' for x, y, rr in
                                               ((p[0], p[1], p[2] if len(p) > 2 else r) for p in pts)) + '</g>')

def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

def _bez(p0, p1, p2, n=12):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1])
            for t in (i / n for i in range(n + 1))]

def _rays(k, x, y, r0, r1, n, w=0.5, op=0.35, a0=0.0, a1=TAU):
    """Ruled radiating lines (glow, burst)."""
    d = []
    for i in range(n):
        a = a0 + (a1 - a0) * (i + k.r.uniform(0.2, 0.8)) / n
        ra, rb = r0 * k.r.uniform(0.9, 1.1), r1 * k.r.uniform(0.6, 1.0)
        d.append(f'M{x + math.cos(a) * ra:.1f},{y + math.sin(a) * ra:.1f} L{x + math.cos(a) * rb:.1f},{y + math.sin(a) * rb:.1f}')
    k.line(' '.join(d), w, op, rough=False)

def _sphere_lines(k, cx, cy, R, n, tilt=0.35, w=0.5, op=0.6, lit=(-0.6, -0.8), dark_only=False):
    """Engraver's contour lines across a sphere (curved latitude strokes), heavier toward the shadow side."""
    cid = _clip(k, _oval(cx, cy, R, R))
    start = len(k.ink)
    for i in range(1, n):
        yy = -R + 2 * R * i / n
        half = math.sqrt(max(R * R - yy * yy, 0))
        # lines bow downward like latitudes on a tilted globe
        bow = half * tilt
        x0, x1 = cx - half, cx + half
        if dark_only: x0 = cx + half * 0.1 - (yy * 0.3)
        k.line(f'M{x0:.1f},{cy + yy:.1f} Q{cx:.1f},{cy + yy + bow:.1f} {x1:.1f},{cy + yy:.1f}', w, op, rough=False)
    _wrap(k, start, f'clip-path="url(#{cid})"')

# ---------------- people ----------------
def _person_parts(k, x, top, h, var=None, suit=False):
    """Back-view standing person (~7.5 heads tall) as (kind, path) pieces drawn in order.
    kinds: leg, body, arm, head, pack. var picks clothing/pose."""
    r = k.r; H = h
    v = r.random() if var is None else var
    coat = (v * 7.3) % 1 < 0.55 and not suit
    sk = 1.5 if suit else 1.0
    lean = r.uniform(-0.012, 0.012) * H
    wf = r.uniform(0.88, 1.15) if not suit else 1.0
    P = lambda dx, dy: (x + dx * H * wf + lean * (1 - dy), top + dy * H)
    parts = []
    # legs
    st = r.uniform(0.0, 0.03); relax = r.choice((-1, 1))
    for side in (-1, 1):
        bend = 0.012 if side == relax else 0.0
        hip, knee, ank = P(side * 0.045, 0.5), P(side * (0.045 + st * 0.5) - bend * side, 0.72), P(side * (0.042 + st), 0.95 - bend * 0.6)
        parts.append(('leg', tapered(k, [hip, _lerp(hip, knee, 0.5), knee, _lerp(knee, ank, 0.5), ank], 0.036 * H * sk, 0.019 * H * sk)))
        fx, fy = ank
        parts.append(('leg', k.smooth([(fx - 0.024 * H * sk, fy - 0.01 * H), (fx + 0.024 * H * sk, fy - 0.01 * H), (fx + 0.027 * H * sk, fy + 0.025 * H), (fx - 0.027 * H * sk, fy + 0.025 * H)])))
    # torso (+ coat skirt)
    hem = (0.66 + r.uniform(-0.03, 0.04)) if coat else 0.52
    shw = 0.115 * (1.2 if suit else 1.0)
    fl = 0.125 if coat else 0.098
    R = [(0.022, 0.13), (0.07, 0.152), (shw, 0.178), (shw - 0.006, 0.22), (0.092, 0.3), (0.084, 0.4), (0.097, 0.49), ((0.097 + fl) / 2, (0.49 + hem) / 2), (fl, hem - 0.004)]
    R += [(fl * 0.9, hem + 0.006), (fl * 0.45, hem + 0.01)]
    pts = [P(dx, dy) for dx, dy in R] + [P(-dx, dy) for dx, dy in reversed(R)]
    parts.append(('body', k.smooth(pts)))
    # arms: shoulder, elbow, wrist; var bends one arm in to the hip or the chest
    for side in (-1, 1):
        sh = P(side * (shw - 0.02), 0.19)
        bent = ((v * 3.7) % 1 < 0.45) and side == (1 if v < 0.5 else -1)
        if bent:
            el, wr = P(side * (shw + 0.04), 0.33), P(side * 0.07, 0.42)
        else:
            el, wr = P(side * (shw + 0.012), 0.335), P(side * (shw + 0.004), 0.47)
        parts.append(('arm', tapered(k, [sh, _lerp(sh, el, 0.5), el, _lerp(el, wr, 0.5), wr], 0.032 * H * sk, 0.02 * H * sk)))
        hx, hy = wr
        parts.append(('arm', _oblob(k, hx, hy + 0.025 * H, 0.018 * H * sk, 0.03 * H * sk, side * 0.15, 10, 0.05)))
    if suit:
        parts.append(('pack', k.smooth([P(-0.085, 0.165), P(0.085, 0.165), P(0.092, 0.25), P(0.085, 0.4), P(-0.085, 0.4), P(-0.092, 0.25)])))
        parts.append(('head', _oval(*P(0, 0.075), 0.075 * H, 0.075 * H)))
    else:
        hx, hy = P(0, 0.065)
        parts.append(('head', _oblob(k, hx, hy, 0.044 * H, 0.06 * H, r.uniform(-0.12, 0.12), 12, 0.03)))
    return parts

def _person(k, x, top, h, mode='shape', var=None, suit=False):
    parts = _person_parts(k, x, top, h, var, suit)
    H = h
    if mode == 'solid':
        for kind, d in parts:
            if kind == 'pack': continue
            k.solid(d)
        if suit and H > 30:
            _white(k, f'M{x - H * 0.045:.1f},{top + H * 0.06:.1f} q{H * 0.015:.1f},{-H * 0.03:.1f} {H * 0.05:.1f},{-H * 0.035:.1f}', max(0.6, H * 0.008))
            _white(k, f'M{x - H * 0.06:.1f},{top + H * 0.2:.1f} h{H * 0.12:.1f} M{x - H * 0.06:.1f},{top + H * 0.4:.1f} h{H * 0.12:.1f}', max(0.5, H * 0.005))
        # rim light on the lit (left) edge: head, shoulder, arm
        w = max(0.6, H * 0.006)
        if H > 25:
            _white(k, f'M{x - H * 0.105:.1f},{top + H * 0.2:.1f} q{H * 0.02:.1f},{-H * 0.03:.1f} {H * 0.065:.1f},{-H * 0.04:.1f}', w)
            _white(k, f'M{x - H * 0.03:.1f},{top + H * 0.075:.1f} q{H * 0.005:.1f},{-H * 0.04:.1f} {H * 0.035:.1f},{-H * 0.05:.1f}', w * 0.9)
        if H > 60:
            _white(k, f'M{x - H * 0.13:.1f},{top + H * 0.24:.1f} q{-H * 0.005:.1f},{H * 0.08:.1f} {H * 0.002:.1f},{H * 0.18:.1f}', w * 0.8)
        return
    if mode == 'engraved':
        # white-line engraving: dark silhouette, form modelled by white cross-contours on the lit side
        for kind, d in parts: k.solid(d)
        u = H; w = max(0.7, u * 0.0028)
        cid = k.uid('c')
        k.defs.append(f'<clipPath id="{cid}">' + ''.join(f'<path d="{d}"/>' for _, d in parts) + '</clipPath>')
        start = len(k.ink); wl = []
        # torso cross-contours: curved strokes from the lit left edge, shortening toward the shadow
        for i in range(34):
            yy = top + u * (0.165 + i * 0.0135)
            f = 1 - abs(i - 9) / 30
            L = u * 0.15 * f * k.r.uniform(0.8, 1.05)
            x0 = x - u * 0.15
            wl.append(f'M{x0:.1f},{yy - u * 0.01:.1f} Q{x0 + L * 0.45:.1f},{yy + u * 0.012:.1f} {x0 + L:.1f},{yy + u * 0.006:.1f}')
        _white(k, ' '.join(wl), w * 0.75)
        fl = []
        for i in range(4):
            fx = x + u * (-0.06 + i * 0.035 + k.r.uniform(-0.006, 0.006)); fy = top + u * k.r.uniform(0.47, 0.5)
            fl.append(f'M{fx:.1f},{fy:.1f} q{u * k.r.uniform(-0.015, 0.015):.1f},{u * 0.07:.1f} {u * k.r.uniform(-0.02, 0.02):.1f},{u * 0.15:.1f}')
        fl.append(f'M{x - u * 0.02:.1f},{top + u * 0.19:.1f} q{u * 0.02:.1f},{u * 0.1:.1f} {u * 0.005:.1f},{u * 0.22:.1f}')
        _white(k, ' '.join(fl), w * 0.7)
        ll = []
        for j in range(4):
            o = 0.004 + j * 0.006
            ll.append(f'M{x - u * (0.128 - o):.1f},{top + u * (0.215 + j * 0.015):.1f} q{-u * 0.008:.1f},{u * 0.1:.1f} {-u * 0.004:.1f},{u * (0.22 - j * 0.03):.1f}')
        ll.append(f'M{x - u * 0.075:.1f},{top + u * 0.7:.1f} q{u * 0.0:.1f},{u * 0.12:.1f} {u * 0.008:.1f},{u * 0.24:.1f}')
        _white(k, ' '.join(ll), w * 0.7)
        hair = ' '.join(f'M{x - u * 0.036 + i * u * 0.007:.1f},{top + u * 0.022 + abs(i - 2) * u * 0.004:.1f} q{u * 0.008:.1f},{u * 0.03:.1f} {u * 0.004:.1f},{u * (0.06 - i * 0.008):.1f}' for i in range(5))
        _white(k, hair, w * 0.6)
        _white(k, f'M{x - u * 0.1:.1f},{top + u * 0.47:.1f} Q{x:.1f},{top + u * 0.49:.1f} {x + u * 0.1:.1f},{top + u * 0.47:.1f}', w * 1.2)
        _wrap(k, start, f'clip-path="url(#{cid})"')
        _white(k, f'M{x - u * 0.1:.1f},{top + u * 0.2:.1f} q{u * 0.02:.1f},{-u * 0.03:.1f} {u * 0.065:.1f},{-u * 0.04:.1f}', w * 1.6)
        k.depth = 0.6
        k.shape(_oval(x + u * 0.09, top + u * 0.975, u * 0.17, u * 0.018), tone=3, dark=3, outline=0, angle=0, knock=False)
        k.depth = 0.95
        return
    tones = {'leg': (4, 4, 80), 'body': (3, 4, 64), 'arm': (3, 4, 72), 'head': (4, 4, 20), 'pack': (2, 4, 15)}
    if suit: tones = {'leg': (2, 4, 80), 'body': (2, 4, 65), 'arm': (2, 4, 55), 'head': (1, 4, 30), 'pack': (3, 4, 10)}
    body = None
    for kind, d in parts:
        t, dk, ang = tones[kind]
        if kind == 'body': body = d
        k.shape(d, tone=t, dark=dk, angle=ang + k.r.uniform(-6, 6), outline=0.8)
        if kind == 'body':
            # cross-contour hatching on the shadow side and long drapery folds, clipped to the torso
            cid = _clip(k, d); start = len(k.ink); u = H
            arcs = []
            for i in range(14):
                yy = top + u * (0.2 + i * 0.033)
                arcs.append(f'M{x + u * 0.01:.1f},{yy + u * 0.012:.1f} Q{x + u * 0.08:.1f},{yy + u * 0.02:.1f} {x + u * 0.14:.1f},{yy - u * 0.012:.1f}')
            k.line(' '.join(arcs), 0.55, 0.75)
            folds = []
            for i in range(6):
                fx = x + u * k.r.uniform(-0.07, 0.07); fy = top + u * k.r.uniform(0.2, 0.3)
                folds.append(f'M{fx:.1f},{fy:.1f} q{u * k.r.uniform(-0.015, 0.015):.1f},{u * 0.14:.1f} {u * k.r.uniform(-0.02, 0.02):.1f},{u * k.r.uniform(0.2, 0.42):.1f}')
            k.line(' '.join(folds), 0.8, 0.85)
            k.line(f'M{x - u * 0.09:.1f},{top + u * 0.45:.1f} Q{x:.1f},{top + u * 0.47:.1f} {x + u * 0.09:.1f},{top + u * 0.45:.1f}', 0.9)
            _wrap(k, start, f'clip-path="url(#{cid})"')
    u = H
    k.line(f'M{x - u * 0.03:.1f},{top + u * 0.135:.1f} Q{x:.1f},{top + u * 0.15:.1f} {x + u * 0.03:.1f},{top + u * 0.135:.1f}', 0.9)
    w = max(0.8, u * 0.004)
    if not suit:
        hair = ' '.join(f'M{x + u * k.r.uniform(-0.03, 0.03):.1f},{top + u * 0.012:.1f} q{u * 0.008:.1f},{u * 0.04:.1f} {u * k.r.uniform(-0.01, 0.015):.1f},{u * 0.085:.1f}' for _ in range(7))
        _white(k, hair, w * 0.7)
    _white(k, f'M{x - u * 0.1:.1f},{top + u * 0.2:.1f} q{u * 0.02:.1f},{-u * 0.03:.1f} {u * 0.065:.1f},{-u * 0.04:.1f}', w)
    _white(k, f'M{x - u * 0.128:.1f},{top + u * 0.23:.1f} q{-u * 0.006:.1f},{u * 0.08:.1f} {u * 0.0:.1f},{u * 0.18:.1f}', w)
    # cast shadow at the feet
    k.depth = 0.6
    k.shape(_oval(x + u * 0.09, top + u * 0.975, u * 0.17, u * 0.018), tone=3, dark=3, outline=0, angle=0, knock=False)
    k.depth = 0.95

def figure(k, x, y, s, spec=None):
    """A lone person seen from behind: engraved, unfaced. Height 2s, feet at y + s."""
    k.depth = 0.95
    _person(k, x, y - s, 2 * s, 'solid' if s < 70 else 'engraved')
    _wash(k, spec, x, y - s * 0.3, s * 0.3, s * 0.6, 1, 0.35)

def suited_figure(k, x, y, s, spec=None):
    """A person in a pressure suit, from behind: helmet, life-support pack, ringed joints, a hose."""
    k.depth = 0.95
    H = 2 * s; top = y - s
    if s < 70:
        _person(k, x, top, H, 'solid', suit=True)
    else:
        _person(k, x, top, H, 'shape', suit=True)
        u = H
        rings = []
        for side in (-1, 1):
            for yy, xx, ww in ((0.335, 0.15, 0.03), (0.72, 0.048, 0.033), (0.9, 0.05, 0.03)):
                rings.append(f'M{x + side * xx * u - ww * u:.1f},{top + yy * u:.1f} q{ww * u:.1f},{0.012 * u:.1f} {2 * ww * u:.1f},0')
        k.line(' '.join(rings), 1.0, rough=False)
        for i in range(4):
            _thin(k, f'M{x - 0.06 * u:.1f},{top + (0.21 + i * 0.03) * u:.1f} h{0.05 * u:.1f}', 1.0)
        k.shape(k.poly([(x + 0.015 * u, top + 0.21 * u), (x + 0.065 * u, top + 0.21 * u), (x + 0.065 * u, top + 0.28 * u), (x + 0.015 * u, top + 0.28 * u)]),
                tone=3, dark=4, outline=0.7, rough=False)
        hose = [(x + 0.08 * u, top + 0.33 * u), (x + 0.14 * u, top + 0.24 * u), (x + 0.1 * u, top + 0.12 * u), (x + 0.04 * u, top + 0.11 * u)]
        k.shape(tapered(k, [hose[0], *_bez(hose[1], hose[2], hose[3], 6)], 0.01 * u, 0.01 * u), tone=2, dark=4, outline=0.6)
        k.line(f'M{x - 0.07 * u:.1f},{top + 0.115 * u:.1f} Q{x:.1f},{top + 0.14 * u:.1f} {x + 0.07 * u:.1f},{top + 0.115 * u:.1f}', 1.0, rough=False)
        _white(k, f'M{x - 0.05 * u:.1f},{top + 0.05 * u:.1f} q{0.015 * u:.1f},{-0.03 * u:.1f} {0.055 * u:.1f},{-0.04 * u:.1f}', max(1.2, u * 0.006))
    _wash(k, spec, x, y - s * 0.3, s * 0.35, s * 0.6, 0, 0.35)

def _far_person(k, x, top, H):
    """A distant back-view person as one compact outline (head + body with a leg notch)."""
    w = H * k.r.uniform(0.1, 0.13); hem = k.r.uniform(0.55, 0.68)
    P = lambda dx, dy: f'{x + dx * w:.1f},{top + dy * H:.1f}'
    body = (f'M{P(-0.25, 0.13)} L{P(-0.95, 0.19)} L{P(-1.05, 0.5)} L{P(-0.8, hem)} L{P(-0.5, 0.98)} L{P(-0.12, 0.98)} L{P(0, 0.72)} '
            f'L{P(0.12, 0.98)} L{P(0.5, 0.98)} L{P(0.8, hem)} L{P(1.05, 0.5)} L{P(0.95, 0.19)} L{P(0.25, 0.13)}Z')
    return body + ' ' + _oval(x, top + H * 0.065, H * 0.045, H * 0.06)

def crowd(k, x, y, s, spec=None):
    """A crowd from behind in receding rows: far rows small and pale, near rows dense ink with rim light.
    People overlap, so mostly heads and shoulders read, as in a real throng."""
    rows = 5
    for ri in range(rows):
        t = ri / (rows - 1)                     # 0 back .. 1 front
        k.depth = 0.3 + 0.65 * t
        h = s * (0.45 + 0.6 * t)
        base = y + s * (-0.15 + 0.85 * t)
        span = s * (1.4 + 0.5 * t)
        n = int(2 * span / (h * 0.2))
        xs = sorted(x + span * (2 * (i + k.r.uniform(0.1, 0.9)) / n - 1) for i in range(n))
        if t > 0.5: xs = [p for p in xs if k.r.random() < 0.75]
        row = []
        for px in xs:
            hh = h * k.r.uniform(0.88, 1.1)
            top = base - hh + k.r.uniform(-0.02, 0.02) * h
            if t < 0.6:
                row.append(_far_person(k, px, top, hh))
            else:
                _person(k, px, top, hh, 'solid')
        if row:   # far rows: one hatched mass per row keeps the SVG light
            k.shape(' '.join(row), tone=2 if t < 0.3 else 3, dark=3 if t < 0.3 else 4, outline=0.5 if t < 0.3 else 0.6, angle=60 if t < 0.3 else 70)
    _wash(k, spec, x, y + s * 0.2, s * 1.4, s * 0.5, 1, 0.3)

# ---------------- creatures ----------------
def _ant_local(k, L, gait=0.0, solid=True):
    """Side-view ant, head toward +x, ground at y = +0.2L, as ink SVG (local coordinates)."""
    out = []
    def leg(pts, w):
        return f'<path d="{tapered(k, pts, w, w * 0.35)}" fill="#000"/>'
    # far legs (lighter)
    for i, hx in enumerate((-0.04, 0.03, 0.1)):
        sw = (1 if i % 2 else -1) * gait
        hip = (hx * L, 0.0); knee = ((hx + (0.1 if i else -0.1) * 1.0 + 0.04) * L, -0.1 * L); foot = ((hx + (0.2 if i == 2 else (0.06 if i else -0.18)) + sw * 0.05) * L, 0.2 * L)
        out.append(f'<path d="M{hip[0]:.1f},{hip[1]:.1f} L{knee[0]:.1f},{knee[1]:.1f} L{foot[0]:.1f},{foot[1]:.1f}" fill="none" stroke="#000" stroke-width="{max(0.5, L * 0.012):.2f}" stroke-opacity=".7" stroke-linecap="round"/>')
    gaster = _oblob(k, -0.31 * L, -0.02 * L, 0.2 * L, 0.13 * L, -0.25, 16, 0.02)
    pet = _oblob(k, -0.12 * L, -0.03 * L, 0.04 * L, 0.04 * L, 0, 10, 0.02)
    meso = k.smooth([(-0.08 * L, -0.02 * L), (-0.03 * L, -0.1 * L), (0.07 * L, -0.11 * L), (0.14 * L, -0.06 * L), (0.12 * L, 0.02 * L), (0.0, 0.035 * L)])
    head = _oblob(k, 0.25 * L, -0.06 * L, 0.095 * L, 0.08 * L, 0.3, 14, 0.02)
    mand = k.smooth([(0.31 * L, 0.0), (0.38 * L, 0.02 * L), (0.4 * L, 0.06 * L), (0.33 * L, 0.035 * L)])
    for d in (gaster, pet, meso, head, mand):
        out.append(f'<path d="{d}" fill="#000"/>')
    # near legs
    for i, hx in enumerate((-0.05, 0.03, 0.11)):
        sw = (-1 if i % 2 else 1) * gait
        hip = (hx * L, 0.01 * L)
        knee = ((hx + (-0.16 if i == 0 else (0.02 if i == 1 else 0.14))) * L, -0.08 * L)
        foot = ((hx + (-0.26 if i == 0 else (0.0 if i == 1 else 0.26)) + sw * 0.06) * L, 0.2 * L)
        out.append(leg([hip, _lerp(hip, knee, 0.5), knee, _lerp(knee, foot, 0.5), foot], L * 0.02))
    # elbowed antennae
    for off, op in ((0.0, 1), (0.03, 0.6)):
        a = f'M{(0.29 + off) * L:.1f},{-0.11 * L:.1f} L{(0.33 + off) * L:.1f},{-0.3 * L:.1f} L{(0.5 + off) * L:.1f},{-0.25 * L:.1f}'
        out.append(f'<path d="{a}" fill="none" stroke="#000" stroke-width="{max(0.6, L * 0.014):.2f}" stroke-opacity="{op}" stroke-linecap="round" stroke-linejoin="round"/>')
    # white highlights
    w = max(0.7, L * 0.011)
    hl = (f'M{-0.44 * L:.1f},{-0.06 * L:.1f} Q{-0.36 * L:.1f},{-0.15 * L:.1f} {-0.22 * L:.1f},{-0.12 * L:.1f} '
          f'M{-0.4 * L:.1f},{0.0:.1f} Q{-0.33 * L:.1f},{-0.07 * L:.1f} {-0.24 * L:.1f},{-0.07 * L:.1f} '
          f'M{-0.02 * L:.1f},{-0.08 * L:.1f} Q{0.04 * L:.1f},{-0.11 * L:.1f} {0.1 * L:.1f},{-0.08 * L:.1f} '
          f'M{0.19 * L:.1f},{-0.1 * L:.1f} Q{0.24 * L:.1f},{-0.14 * L:.1f} {0.3 * L:.1f},{-0.1 * L:.1f}')
    if L > 25:
        out.append(f'<path d="{hl}" fill="none" stroke="#fff" stroke-width="{w:.2f}" stroke-linecap="round"/>')
        out.append(f'<circle cx="{0.27 * L:.1f}" cy="{-0.075 * L:.1f}" r="{max(0.8, L * 0.016):.1f}" fill="#fff"/>')
    return ''.join(out)

def _ant(k, x, y, L, ang=0.0, flip=False):
    sx = -1 if flip else 1
    k.ink.append(f'<g transform="translate({x:.1f},{y:.1f}) rotate({math.degrees(ang):.1f}) scale({sx},1)">{_ant_local(k, L, k.r.uniform(-1, 1))}</g>')

def ant_column(k, x, y, s, spec=None):
    """A column of ants marching along an S-curved trail, larger as they come near."""
    k.depth = 0.9
    p0, p1, p2, p3 = (x - 1.8 * s, y - 0.55 * s), (x - 0.4 * s, y - 1.0 * s), (x + 0.3 * s, y + 0.9 * s), (x + 1.8 * s, y + 0.35 * s)
    def B(t):
        a, b, c = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t; d = t ** 3
        return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])
    # trail: faint trodden band of stipple and ticks
    trail = [B(i / 40) for i in range(41)]
    k.depth = 0.4
    k.line(k.smooth([(px, py + s * 0.12) for px, py in trail], close=False), 0.6, 0.35)
    for px, py in trail[::2]:
        k.stipple(px, py + s * 0.1, s * 0.12, s * 0.03, 4, (0.4, 1.0))
    k.depth = 0.95
    t = 0.02
    while t < 0.98:
        px, py = B(t); qx, qy = B(min(t + 0.01, 1))
        L = s * (0.22 + 0.2 * t) * k.r.uniform(0.9, 1.1)
        ang = math.atan2(qy - py, qx - px)
        lane = k.r.choice((-1, 0, 1)) * s * 0.06
        _ant(k, px - math.sin(ang) * lane, py + math.cos(ang) * lane, L, ang)
        t += (L * 0.85) / (4.0 * s) + k.r.uniform(0, 0.015)
    _wash(k, spec, x, y, s * 1.6, s * 0.6, 0, 0.3)

def beetle(k, x, y, s, spec=None):
    """A heavy beetle from above: glossy ink elytra with white sheen, horned head, spined legs."""
    k.depth = 1.0
    a = k.r.uniform(-0.35, 0.35)
    start = len(k.ink)
    cx, cy = 0.0, 0.0
    lw = s * 0.035
    # legs: three per side, femur/tibia with spines
    for side in (-1, 1):
        for i, (ay, fx, fy, tx, ty) in enumerate(((-0.2, 0.55, -0.42, 0.75, -0.8), (0.0, 0.62, 0.05, 0.9, 0.12), (0.2, 0.55, 0.42, 0.78, 0.85))):
            hip = (side * 0.18 * s, ay * s); knee = (side * fx * s, fy * s); foot = (side * tx * s, ty * s)
            k.solid(tapered(k, [hip, _lerp(hip, knee, 0.5), knee], lw * 1.2, lw))
            k.solid(tapered(k, [knee, _lerp(knee, foot, 0.5), foot], lw * 0.9, lw * 0.4))
            for t in (0.3, 0.55, 0.8):
                px, py = _lerp(knee, foot, t)
                k.line(f'M{px:.1f},{py:.1f} l{side * s * 0.04:.1f},{s * 0.015 * (1 if ty > 0 else -1):.1f}', 0.6, rough=False)
            # tarsal claws
            k.line(f'M{foot[0]:.1f},{foot[1]:.1f} l{side * s * 0.05:.1f},{-s * 0.02:.1f} M{foot[0]:.1f},{foot[1]:.1f} l{side * s * 0.04:.1f},{s * 0.03:.1f}', 0.7, rough=False)
    # antennae (clubbed)
    for side in (-1, 1):
        k.line(f'M{side * s * 0.08:.1f},{-s * 0.62:.1f} q{side * s * 0.1:.1f},{-s * 0.18:.1f} {side * s * 0.25:.1f},{-s * 0.22:.1f}', 1.1, rough=False)
        k.solid(_oblob(k, side * s * 0.28, -s * 0.85, s * 0.04, s * 0.025, side * 0.4, 10, 0.03))
    ely = k.smooth([(0, -0.28 * s), (0.3 * s, -0.24 * s), (0.36 * s, 0.1 * s), (0.28 * s, 0.5 * s), (0, 0.72 * s),
                    (-0.28 * s, 0.5 * s), (-0.36 * s, 0.1 * s), (-0.3 * s, -0.24 * s)])
    pron = k.smooth([(-0.26 * s, -0.27 * s), (-0.24 * s, -0.46 * s), (0, -0.52 * s), (0.24 * s, -0.46 * s), (0.26 * s, -0.27 * s), (0, -0.25 * s)])
    head = k.smooth([(-0.12 * s, -0.5 * s), (-0.13 * s, -0.62 * s), (0, -0.66 * s), (0.13 * s, -0.62 * s), (0.12 * s, -0.5 * s)])
    horn = k.smooth([(-0.04 * s, -0.62 * s), (0.0, -0.95 * s), (0.04 * s, -0.62 * s)])
    for d in (ely, pron, head, horn): k.solid(d)
    w = max(1.0, s * 0.012)
    # elytral seam and sheen
    _white(k, f'M0,{-0.25 * s:.1f} L0,{0.7 * s:.1f}', w * 0.7)
    sheen = []
    for i in range(5):
        o = 0.05 + i * 0.045
        sheen.append(f'M{-0.33 * s + o * s:.1f},{0.35 * s - o * s * 0.6:.1f} Q{-0.3 * s + o * s:.1f},{-0.1 * s:.1f} {-0.16 * s + o * s * 0.3:.1f},{-0.2 * s + o * s * 0.2:.1f}')
    _white(k, ' '.join(sheen[:3]), w)
    rows = []
    for side in (-1, 1):
        for j in range(3):
            xo = side * (0.07 + j * 0.08) * s
            for t in range(9):
                yy = -0.18 * s + t * 0.08 * s
                if abs(xo) < 0.3 * s * math.sqrt(max(0, 1 - ((yy - 0.15 * s) / (0.6 * s)) ** 2)):
                    rows.append((xo, yy, max(0.5, s * 0.006)))
    _dots(k, rows, 0, fill='#fff')
    _white(k, f'M{-0.2 * s:.1f},{-0.33 * s:.1f} Q{-0.15 * s:.1f},{-0.46 * s:.1f} {0.02 * s:.1f},{-0.47 * s:.1f}', w)
    _white(k, f'M{-0.02 * s:.1f},{-0.66 * s:.1f} L{-0.005 * s:.1f},{-0.88 * s:.1f}', w * 0.7)
    _wrap(k, start, f'transform="translate({x:.1f},{y:.1f}) rotate({math.degrees(a):.1f})"')
    _wash(k, spec, x, y, s * 0.5, s * 0.6, 1, 0.4)

def spider_crowd(k, x, y, s, spec=None):
    """Several jumping spiders gathered, turned this way and that; the nearest largest."""
    spots = []
    n = 6
    for i in range(n):
        for _ in range(30):
            px, py = x + k.r.uniform(-1.5, 1.5) * s, y + k.r.uniform(-0.8, 0.9) * s
            if all(math.hypot(px - qx, py - qy) > s * 0.7 for qx, qy, _ in spots): break
        sz = s * (0.26 + 0.34 * (py - (y - 0.8 * s)) / (1.7 * s)) * k.r.uniform(0.85, 1.15)
        spots.append((px, py, sz))
    for px, py, sz in sorted(spots, key=lambda p: p[1]):
        start = len(k.ink)
        _spider(k, px, py, sz)
        rot = k.r.uniform(-50, 50) + (180 if k.r.random() < 0.2 else 0)
        _wrap(k, start, f'transform="rotate({rot:.1f} {px:.1f} {py:.1f})"')
    _wash(k, spec, x, y, s * 1.6, s * 0.8, 1, 0.35)

def _spiderling(k, x, y, s, a):
    start = len(k.ink)
    legs = []
    for side in (-1, 1):
        for i, ang in enumerate((-60, -20, 20, 60)):
            r0 = math.radians(ang)
            kx, ky = side * math.cos(r0) * s * 0.5, math.sin(r0) * s * 0.4 - s * 0.15
            fx, fy = side * math.cos(r0) * s * 0.85, math.sin(r0) * s * 0.75 + s * 0.15
            legs.append(f'M{side * s * 0.05:.1f},{-s * 0.05 + i * s * 0.04:.1f} L{kx:.1f},{ky:.1f} L{fx:.1f},{fy:.1f}')
    k.ink.append(f'<path d="{" ".join(legs)}" fill="none" stroke="#000" stroke-width="{max(0.5, s * 0.06):.2f}" stroke-linejoin="round" stroke-linecap="round"/>')
    k.solid(_oval(0, s * 0.25, s * 0.2, s * 0.27)); k.solid(_oval(0, -s * 0.08, s * 0.17, s * 0.15))
    if s > 6:
        k.ink.append(f'<circle cx="{-s * 0.05:.1f}" cy="{-s * 0.13:.1f}" r="{max(0.5, s * 0.04):.1f}" fill="#fff"/>')
        _white(k, f'M{-s * 0.12:.1f},{s * 0.2:.1f} q{s * 0.04:.1f},{-s * 0.08:.1f} {s * 0.1:.1f},{-s * 0.1:.1f}', max(0.5, s * 0.03))
    _wrap(k, start, f'transform="translate({x:.1f},{y:.1f}) rotate({math.degrees(a):.1f})"')

def spiderlings(k, x, y, s, spec=None):
    """A scatter of tiny spiderlings, some dangling on threads, some ballooning on long silk."""
    k.depth = 0.9
    n = 34
    for i in range(n):
        rr = math.sqrt(k.r.random()) * 1.9 * s; a = k.r.uniform(0, TAU)
        px, py = x + math.cos(a) * rr, y + math.sin(a) * rr * 0.65
        sz = s * k.r.uniform(0.06, 0.13)
        mode = k.r.random()
        if mode < 0.25:      # dangling: thread from above
            k.line(f'M{px:.1f},{py - s * k.r.uniform(0.5, 1.4):.1f} L{px:.1f},{py - sz * 0.3:.1f}', 0.35, 0.8, rough=False)
            _spiderling(k, px, py, sz, math.pi)
        elif mode < 0.4:     # ballooning: a fan of fine lines drifting up-right
            for j in range(3):
                k.line(f'M{px:.1f},{py:.1f} q{s * 0.3:.1f},{-s * (0.2 + j * 0.1):.1f} {s * (0.7 + j * 0.15):.1f},{-s * (0.6 + j * 0.15):.1f}', 0.3, 0.6, rough=False)
            _spiderling(k, px, py, sz, k.r.uniform(-0.6, 0.6))
        else:
            _spiderling(k, px, py, sz, k.r.uniform(-1.2, 1.2))
    _wash(k, spec, x, y, s * 1.5, s * 0.9, 1, 0.3)

def silk_thread(k, x, y, s, spec=None):
    """Silk roads: sagging braided strands crossing the frame with dew beads and anchor tufts."""
    k.depth = 0.9
    for j in range(3):
        x0, x1 = x - (2.4 - j * 0.3) * s, x + (2.3 - j * 0.4) * s
        y0, y1 = y - s * (0.6 - j * 0.5) + k.r.uniform(-0.1, 0.1) * s, y - s * (0.9 - j * 0.6)
        sag = s * (0.45 + 0.1 * j)
        pts = []
        for i in range(61):
            t = i / 60
            pts.append((x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)))
        # braided: two strands twisting around the centre line
        for ph in (0, math.pi):
            br = []
            for i, (px, py) in enumerate(pts):
                br.append((px, py + math.sin(i * 0.9 + ph) * s * 0.012 * (1.2 - j * 0.3)))
            k.line(k.smooth(br, close=False), 1.7 - j * 0.4, 1.0, rough=False)
        k.line(k.smooth(pts, close=False), 0.6, 0.8, rough=False)
        if j == 0:
            # a second strand below, laced to the first: a silk road
            low = [(px, py + s * 0.07) for px, py in pts]
            k.line(k.smooth(low, close=False), 0.9, 1.0, rough=False)
            k.line(' '.join(f'M{pts[i][0]:.1f},{pts[i][1]:.1f} L{low[i + 1][0]:.1f},{low[i + 1][1]:.1f} M{pts[i + 1][0]:.1f},{pts[i + 1][1]:.1f} L{low[i][0]:.1f},{low[i][1]:.1f}' for i in range(1, 59, 2)), 0.4, 0.8, rough=False)
            for end in (pts[0], pts[-1]):
                for q in range(7):
                    a_ = k.r.uniform(-math.pi, math.pi)
                    k.line(f'M{end[0]:.1f},{end[1]:.1f} l{math.cos(a_) * s * 0.15:.1f},{math.sin(a_) * s * 0.15:.1f}', 0.5, 0.8, rough=False)
        beads = []
        for i in range(2, 59, 3):
            if k.r.random() < 0.55:
                px, py = pts[i]; beads.append((px, py + s * 0.012, k.r.uniform(1.2, 2.6) * (1 + s / 400)))
        _dots(k, beads, 0, fill='#fff', stroke='#000', sw=0.6)
        # drip strands hanging from the main line
        for i in (15, 33, 48):
            if k.r.random() < 0.6:
                px, py = pts[i]; L = s * k.r.uniform(0.1, 0.3)
                k.line(f'M{px:.1f},{py:.1f} q{s * 0.01:.1f},{L / 2:.1f} 0,{L:.1f}', 0.35, 0.8, rough=False)
                _dots(k, [(px, py + L, 1.8 + s / 300)], 0, fill='#fff', stroke='#000', sw=0.6)
    # glints: a few white-crossed sparkles on the line
    _wash(k, spec, x, y, s * 1.6, s * 0.5, 1, 0.25)

def monkey(k, x, y, s, spec=None):
    """A long-tailed monkey hanging one-armed from a branch, drawn as ink silhouette with fur highlights."""
    k.depth = 0.95
    by = y - 0.88 * s
    k.shape(tapered(k, [(x - 1.5 * s, by + 0.05 * s), (x - 0.5 * s, by - 0.01 * s), (x + 0.4 * s, by), (x + 1.4 * s, by - 0.1 * s)], 0.06 * s, 0.03 * s),
            tone=2, dark=4, angle=10, outline=1.0)
    for lx in (-1.1, -0.3, 0.8):
        k.line(f'M{x + lx * s:.1f},{by:.1f} q{0.05 * s:.1f},{0.2 * s:.1f} {0.02 * s:.1f},{0.35 * s:.1f}', 0.8)
        leaf = k.smooth([(x + lx * s + 0.02 * s, by + 0.35 * s), (x + lx * s + 0.09 * s, by + 0.42 * s), (x + lx * s + 0.03 * s, by + 0.55 * s), (x + lx * s - 0.04 * s, by + 0.43 * s)])
        k.shape(leaf, tone=1, dark=3, outline=0.7)
    d = []
    hand = (x + 0.05 * s, by + 0.02 * s); sh = (x - 0.02 * s, y - 0.3 * s)
    d.append(tapered(k, [hand, (x + 0.06 * s, y - 0.65 * s), (x + 0.03 * s, y - 0.45 * s), sh], 0.035 * s, 0.06 * s))
    d.append(_oblob(k, hand[0], hand[1] + 0.01 * s, 0.05 * s, 0.035 * s, 0, 10, 0.05))
    d.append(_oblob(k, x - 0.06 * s, y + 0.02 * s, 0.17 * s, 0.3 * s, 0.25, 16, 0.04))       # torso
    d.append(_oblob(k, x - 0.2 * s, y - 0.33 * s, 0.13 * s, 0.12 * s, 0.1, 14, 0.03))         # head
    d.append(_oblob(k, x - 0.33 * s, y - 0.29 * s, 0.07 * s, 0.05 * s, 0.4, 10, 0.03))        # muzzle
    d.append(_oblob(k, x - 0.1 * s, y - 0.4 * s, 0.035 * s, 0.045 * s, 0, 8, 0.05))           # ear
    sh2 = (x - 0.14 * s, y - 0.18 * s); el = (x - 0.38 * s, y + 0.02 * s); h2 = (x - 0.45 * s, y + 0.28 * s)
    d.append(tapered(k, [sh2, _lerp(sh2, el, 0.5), el, _lerp(el, h2, 0.5), h2], 0.05 * s, 0.03 * s))
    for hip, kn, ft in (((x + 0.03 * s, y + 0.22 * s), (x + 0.28 * s, y + 0.38 * s), (x + 0.16 * s, y + 0.62 * s)),
                        ((x - 0.12 * s, y + 0.26 * s), (x - 0.3 * s, y + 0.5 * s), (x - 0.16 * s, y + 0.68 * s))):
        d.append(tapered(k, [hip, _lerp(hip, kn, 0.5), kn, _lerp(kn, ft, 0.5), ft], 0.075 * s, 0.03 * s))
    tail = [(x + 0.05 * s, y + 0.28 * s), (x + 0.25 * s, y + 0.6 * s), (x + 0.35 * s, y + 0.95 * s), (x + 0.2 * s, y + 1.15 * s),
            (x + 0.02 * s, y + 1.1 * s), (x + 0.05 * s, y + 0.98 * s), (x + 0.15 * s, y + 1.0 * s)]
    d.append(tapered(k, tail, 0.035 * s, 0.012 * s))
    start = len(k.ink)
    for p in d: k.solid(p)
    # fur: short ink ticks bristling out from the torso and head edges
    tk = []
    for cx_, cy_, rx_, ry_, rot in ((x - 0.06 * s, y + 0.02 * s, 0.17 * s, 0.3 * s, 0.25), (x - 0.2 * s, y - 0.33 * s, 0.13 * s, 0.12 * s, 0.1)):
        for i in range(44):
            t = i / 44 * TAU
            ex, ey = math.cos(t) * rx_, math.sin(t) * ry_
            px, py = cx_ + ex * math.cos(rot) - ey * math.sin(rot), cy_ + ex * math.sin(rot) + ey * math.cos(rot)
            nx_, ny_ = px - cx_, py - cy_; L_ = math.hypot(nx_, ny_) or 1
            if nx_ > rx_ * 0.6 and ny_ > 0: continue
            tk.append(f'M{px:.1f},{py:.1f} l{nx_ / L_ * s * 0.016 + s * 0.004:.1f},{ny_ / L_ * s * 0.016 + s * 0.016:.1f}')
    k.ink.append(f'<path d="{" ".join(tk)}" fill="none" stroke="#000" stroke-width="{max(0.8, s * 0.01):.1f}" stroke-linecap="round"/>')
    _wrap(k, start, 'filter="url(#rough)"')
    w = max(0.8, s * 0.008)
    fur = []
    for i in range(9):
        t = i / 8
        px, py = x - 0.22 * s + t * 0.06 * s, y - 0.15 * s + t * 0.4 * s
        fur.append(f'M{px:.1f},{py:.1f} q{0.02 * s:.1f},{0.02 * s:.1f} {0.03 * s:.1f},{0.06 * s:.1f}')
    for i in range(5):
        px, py = x - 0.3 * s + i * 0.04 * s, y - 0.43 * s + abs(i - 2) * 0.012 * s
        fur.append(f'M{px:.1f},{py:.1f} l{0.02 * s:.1f},{0.03 * s:.1f}')
    fur.append(f'M{x + 0.03 * s:.1f},{y - 0.7 * s:.1f} q{-0.01 * s:.1f},{0.15 * s:.1f} {-0.03 * s:.1f},{0.3 * s:.1f}')
    fur.append(f'M{x - 0.34 * s:.1f},{y + 0.0:.1f} q{-0.04 * s:.1f},{0.1 * s:.1f} {-0.07 * s:.1f},{0.22 * s:.1f}')
    _white(k, ' '.join(fur), w)
    k.ink.append(f'<circle cx="{x - 0.26 * s:.1f}" cy="{y - 0.35 * s:.1f}" r="{max(0.8, s * 0.012):.1f}" fill="#fff"/>')
    _wash(k, spec, x, y, s * 0.5, s * 0.7, 1, 0.35)

def egg_clutch(k, x, y, s, spec=None):
    """A clutch of glossy eggs heaped on a leaf, bound with loose silk."""
    k.depth = 0.95
    leaf = k.smooth([(x - 1.3 * s, y + 0.35 * s), (x - 0.4 * s, y + 0.05 * s), (x + 0.8 * s, y + 0.1 * s), (x + 1.35 * s, y + 0.45 * s),
                     (x + 0.5 * s, y + 0.72 * s), (x - 0.6 * s, y + 0.7 * s)])
    k.shape(leaf, tone=1, dark=3, angle=20, outline=1.0)
    k.line(f'M{x - 1.25 * s:.1f},{y + 0.37 * s:.1f} Q{x:.1f},{y + 0.32 * s:.1f} {x + 1.3 * s:.1f},{y + 0.45 * s:.1f}', 1.0)
    for i in range(7):
        px = x - 0.9 * s + i * 0.3 * s
        k.line(f'M{px:.1f},{y + 0.36 * s:.1f} q{0.12 * s:.1f},{-0.15 * s:.1f} {0.3 * s:.1f},{-0.2 * s:.1f} M{px:.1f},{y + 0.36 * s:.1f} q{0.12 * s:.1f},{0.15 * s:.1f} {0.28 * s:.1f},{0.22 * s:.1f}', 0.5, 0.7)
    eggs = []
    for row, (ny, yy, r) in enumerate(((7, 0.28, 0.13), (6, 0.12, 0.13), (4, -0.04, 0.125), (2, -0.18, 0.12))):
        for i in range(ny):
            ex = x + (i - (ny - 1) / 2) * r * 1.75 * s + k.r.uniform(-0.03, 0.03) * s
            eggs.append((ex, y + yy * s + k.r.uniform(-0.02, 0.02) * s, r * s * k.r.uniform(0.9, 1.05)))
    for ex, ey, r in eggs:
        k.shape(_oblob(k, ex, ey, r * 0.85, r, k.r.uniform(-0.4, 0.4), 14, 0.03), tone=1, dark=4, angle=k.r.uniform(30, 70), outline=0.9)
        _white(k, f'M{ex - r * 0.45:.1f},{ey - r * 0.1:.1f} q{r * 0.05:.1f},{-r * 0.4:.1f} {r * 0.4:.1f},{-r * 0.55:.1f}', max(1.0, r * 0.08))
    for i in range(9):
        a0, a1 = (x + k.r.uniform(-0.9, 0.9) * s, y + k.r.uniform(-0.3, 0.4) * s), (x + k.r.uniform(-0.9, 0.9) * s, y + k.r.uniform(-0.3, 0.4) * s)
        k.line(f'M{a0[0]:.1f},{a0[1]:.1f} Q{(a0[0] + a1[0]) / 2:.1f},{min(a0[1], a1[1]) - 0.2 * s:.1f} {a1[0]:.1f},{a1[1]:.1f}', 0.35, 0.8, rough=False)
    _wash(k, spec, x, y + 0.1 * s, s * 0.9, s * 0.5, 1, 0.4)

def fungus(k, x, y, s, spec=None):
    """A cluster of mushrooms: domed caps with white spots, gills ruled beneath, slender stems, a spore haze."""
    k.depth = 0.95
    caps = [(0.0, 0.0, 0.55, 1.0), (-0.65, 0.35, 0.36, 0.7), (0.6, 0.3, 0.42, 0.8), (-0.3, 0.6, 0.2, 0.4), (0.3, 0.7, 0.16, 0.3)]
    ground = y + 0.95 * s
    k.shape(k.smooth([(x - 1.3 * s, ground + 0.08 * s), (x - 0.6 * s, ground - 0.07 * s), (x + 0.6 * s, ground - 0.05 * s), (x + 1.3 * s, ground + 0.08 * s), (x, ground + 0.16 * s)]),
            tone=2, dark=3, angle=5, outline=0.8)
    k.stipple(x, y - 0.6 * s, 1.1 * s, 0.6 * s, 70, (0.4, 1.1))
    for dx, dy, r, hgt in sorted(caps, key=lambda c: c[1]):
        cx, cy = x + dx * s, y + dy * s - hgt * 0.35 * s
        R = r * s
        st = k.smooth([(cx - R * 0.14, cy), (cx - R * 0.1, cy + (ground - cy) * 0.5), (cx - R * 0.2, ground), (cx + R * 0.2, ground), (cx + R * 0.12, cy + (ground - cy) * 0.5), (cx + R * 0.12, cy)])
        k.shape(st, tone=1, dark=3, angle=85, outline=0.9)
        gills = k.smooth([(cx - R, cy), (cx, cy + R * 0.18), (cx + R, cy), (cx, cy + R * 0.05)])
        k.shape(gills, tone=3, dark=4, angle=90, outline=0.7)
        gl = ' '.join(f'M{cx:.1f},{cy + R * 0.12:.1f} L{cx + R * t:.1f},{cy + R * 0.02:.1f}' for t in [i / 8 - 1 for i in range(17)])
        k.line(gl, 0.4, 0.8, rough=False)
        cap = k.smooth([(cx - R, cy), (cx - R * 0.85, cy - R * 0.45), (cx - R * 0.3, cy - R * 0.72), (cx + R * 0.3, cy - R * 0.72), (cx + R * 0.85, cy - R * 0.45), (cx + R, cy), (cx, cy - R * 0.06)])
        k.shape(cap, tone=2, dark=4, angle=k.r.uniform(20, 60), outline=1.0)
        spots = []
        for _ in range(int(4 + R / 12)):
            a = k.r.uniform(math.pi * 1.1, math.pi * 1.9); rr = k.r.uniform(0.25, 0.8)
            spots.append((cx + math.cos(a) * R * rr, cy - 0.04 * R + math.sin(a) * R * 0.62 * rr, max(1.0, R * k.r.uniform(0.03, 0.06))))
        _dots(k, spots, 0, fill='#fff', stroke='#000', sw=0.5)
        _white(k, f'M{cx - R * 0.75:.1f},{cy - R * 0.35:.1f} Q{cx - R * 0.55:.1f},{cy - R * 0.65:.1f} {cx - R * 0.1:.1f},{cy - R * 0.68:.1f}', max(1.0, R * 0.025))
    _wash(k, spec, x, y, s * 1.0, s * 0.8, 1, 0.4)
    _wash(k, spec, x, y - 0.6 * s, s * 1.2, s * 0.5, 0, 0.25)


# ---------------- a small 3D kit for machines ----------------
def _v(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def _add(a, b, t=1.0): return (a[0] + b[0] * t, a[1] + b[1] * t, a[2] + b[2] * t)
def _mul(a, t): return (a[0] * t, a[1] * t, a[2] * t)
def _dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def _cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def _norm(a):
    L = math.sqrt(_dot(a, a)) or 1; return (a[0] / L, a[1] / L, a[2] / L)

def _hull(pts):
    pts = sorted(set((round(p[0], 1), round(p[1], 1)) for p in pts))
    if len(pts) < 3: return pts
    def cr(o, a, b): return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, up = [], []
    for p in pts:
        while len(lo) >= 2 and cr(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(up) >= 2 and cr(up[-2], up[-1], p) <= 0: up.pop()
        up.append(p)
    return lo[:-1] + up[:-1]

def _ruled(k, pts, tone, ang, ol=0.7, knock=True):
    """Fill a flat face with ruled engraving lines: spacing and weight from tone, a cross rule at tone 4."""
    d = k.poly(pts)
    cid = _clip(k, d)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    R = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 2
    g = [f'<path d="{d}" fill="#fff"/>'] if knock else []
    spec = {0: [], 1: [(5.5, 0.4)], 2: [(4.2, 0.6)], 3: [(3.4, 0.9)], 4: [(3.0, 1.15), (4.5, 0.5)]}[max(0, min(4, tone))]
    for fi, (gap, w) in enumerate(spec):
        a = math.radians(ang + (0 if fi == 0 else 62))
        dx, dy = math.cos(a), math.sin(a); nx, ny = -dy, dx
        lines = []
        n = int(R / gap)
        for i in range(-n, n + 1):
            ox, oy = cx + nx * i * gap, cy + ny * i * gap
            lines.append(f'M{ox - dx * R:.1f},{oy - dy * R:.1f} L{ox + dx * R:.1f},{oy + dy * R:.1f}')
        g.append(f'<path d="{" ".join(lines)}" stroke="#000" stroke-width="{w}" fill="none" clip-path="url(#{cid})"/>')
    if ol: g.append(f'<path d="{d}" fill="none" stroke="#000" stroke-width="{ol:.2f}" stroke-linejoin="round"/>')
    k.ink.append('<g>' + ''.join(g) + '</g>')

def _ruled_path(k, d, tone, ang):
    """Ruled fill of an arbitrary path (bounding box from its numbers)."""
    import re
    nums = [float(v) for v in re.findall(r'-?\d+\.?\d*', d)]
    xs, ys = nums[0::2], nums[1::2]
    if not xs: return
    cid = _clip(k, d)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    R = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2 + 2
    spec = {1: [(5.5, 0.4)], 2: [(4.2, 0.6)], 3: [(3.4, 0.9)], 4: [(2.8, 1.2), (4.0, 0.6)]}[tone]
    g = [f'<path d="{d}" fill="#fff"/>']
    for fi, (gap, w) in enumerate(spec):
        a = math.radians(ang + (0 if fi == 0 else 62)); dx, dy = math.cos(a), math.sin(a); nx, ny = -dy, dx
        n = int(R / gap)
        ln = ' '.join(f'M{cx + nx * i * gap - dx * R:.1f},{cy + ny * i * gap - dy * R:.1f} l{2 * dx * R:.1f},{2 * dy * R:.1f}' for i in range(-n, n + 1))
        g.append(f'<path d="{ln}" stroke="#000" stroke-width="{w}" fill="none" clip-path="url(#{cid})"/>')
    k.ink.append('<g>' + ''.join(g) + '</g>')

class _Cam:
    """Orthographic-ish camera: model units scaled by s, Y up; yaw about Y, pitch looks down, roll in screen."""
    LIGHT = _norm((-0.55, 0.6, 0.6))
    def __init__(self, x, y, s, yaw=0.5, pitch=0.3, roll=0.0, persp=0.0):
        self.x, self.y, self.s, self.persp = x, y, s, persp
        self.cy, self.sy, self.cp, self.sp, self.cr, self.sr = math.cos(yaw), math.sin(yaw), math.cos(pitch), math.sin(pitch), math.cos(roll), math.sin(roll)
    def rot(self, v):
        X, Y, Z = v
        x1 = X * self.cy + Z * self.sy; z1 = -X * self.sy + Z * self.cy
        y2 = Y * self.cp - z1 * self.sp; z2 = Y * self.sp + z1 * self.cp
        return (x1 * self.cr - y2 * self.sr, x1 * self.sr + y2 * self.cr, z2)
    def p(self, v):
        X, Y, Z = self.rot(v)
        f = 1 / (1 - Z * self.persp) if self.persp else 1
        return (self.x + X * self.s * f, self.y - Y * self.s * f)
    def z(self, v): return self.rot(v)[2]
    def view(self):
        return (self.rot((1, 0, 0))[2], self.rot((0, 1, 0))[2], self.rot((0, 0, 1))[2])
    def tone(self, n, off=0):
        d = _dot(self.rot(n), self.LIGHT)
        t = 1 if d > 0.72 else 2 if d > 0.42 else 3 if d > 0.08 else 4
        return max(0, min(4, t + off))

class _Scene:
    """Painter's list: objects (each a list of ops) sorted far to near by their centre depth."""
    def __init__(self, k, cam):
        self.k, self.c, self.objs = k, cam, []
    def add(self, depth, ops): self.objs.append((depth, ops))
    def render(self, outline=0.8):
        k = self.k
        for _, ops in sorted(self.objs, key=lambda o: o[0]):
            for op in ops:
                kind = op[0]
                if kind == 'poly':
                    _, pts, tone, ang, ol = op
                    _ruled(k, pts, tone, ang + 90, ol)
                elif kind == 'line':
                    _, pts, w, closed = op
                    _thin(k, k.poly(pts, closed), w)
                elif kind == 'white':
                    _, pts, w = op
                    _white(k, k.poly(pts, False), w)
                elif kind == 'fn':
                    op[1]()
                elif kind == 'svg':
                    k.ink.append(op[1])

    def _sang(self, a, b):
        pa, pb = self.c.p(a), self.c.p(b)
        return math.degrees(math.atan2(pb[1] - pa[1], pb[0] - pa[0])) - 90

    def poly(self, pts3, off=0, ol=0.7, ang=None, two_sided=True, ops=None):
        """A flat face; returns False if back-facing and one-sided."""
        n = _norm(_cross(_v(pts3[1], pts3[0]), _v(pts3[2], pts3[0])))
        if self.c.rot(n)[2] < 0:
            if not two_sided: return False
            n = _mul(n, -1)
        ang = self._sang(pts3[0], pts3[1]) + 90 if ang is None else ang
        op = ('poly', [self.c.p(q) for q in pts3], self.c.tone(n, off), ang, ol)
        if ops is None: self.add(sum(self.c.z(q) for q in pts3) / len(pts3), [op])
        else: ops.append((sum(self.c.z(q) for q in pts3) / len(pts3), op))
        return True

    def box(self, c, size, basis=((1, 0, 0), (0, 1, 0), (0, 0, 1)), off=0, ol=0.7, extra=None):
        ex, ey, ez = (_mul(_norm(b), d / 2) for b, d in zip(basis, size))
        corner = lambda i, j, l: _add(_add(_add(c, ex, i), ey, j), ez, l)
        faces = [[(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)], [(-1, -1, 1), (-1, 1, 1), (-1, 1, -1), (-1, -1, -1)],
                 [(-1, 1, -1), (-1, 1, 1), (1, 1, 1), (1, 1, -1)], [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)],
                 [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)], [(-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1)]]
        ops = []
        for f in faces:
            pts = [corner(*q) for q in f]
            n = _norm(_cross(_v(pts[1], pts[0]), _v(pts[2], pts[0])))
            if self.c.rot(n)[2] <= 0.001: continue
            ops.append((self.c.z(_add(c, n, 0.0)), ('poly', [self.c.p(q) for q in pts], self.c.tone(n, off), self._sang(pts[0], pts[1]) + 90, ol)))
        allops = [o for _, o in ops] + (extra or [])
        self.add(self.c.z(c), allops)
        return ops

    def cyl(self, a, b, r, n=18, off=0, caps=(True, True), r2=None, seams=(), ol=0.8, ends=None, skip=(), extra=None, depth_bias=0.0, cap_off=0):
        """A cylinder (or frustum with r2) from a to b: hatched facets along the axis, outlined silhouette, caps."""
        r2 = r if r2 is None else r2
        u = _norm(_v(b, a)); L = math.sqrt(_dot(_v(b, a), _v(b, a)))
        t = (0, 1, 0) if abs(u[1]) < 0.9 else (1, 0, 0)
        v = _norm(_cross(u, t)); w = _cross(u, v)
        ang = self._sang(a, b) + 90
        th = [i / n * TAU for i in range(n)]
        endt = ends or [1.0] * n
        A = [_add(a, _add(_mul(v, math.cos(q) * r), _mul(w, math.sin(q) * r))) for q in th]
        B = [_add(_add(a, u, L * endt[i]), _add(_mul(v, math.cos(q) * (r + (r2 - r) * endt[i])), _mul(w, math.sin(q) * (r + (r2 - r) * endt[i])))) for i, q in enumerate(th)]
        ops = []
        slope = (r - r2) / (L or 1)
        out = []
        if not skip:
            # engraved cylinder: rules along the axis, heavier toward the shadow, skipped in the highlight
            if ends is None:
                hull = _hull([self.c.p(q) for q in A + B])
                out.append(('svg', f'<path d="{self.k.poly(hull)}" fill="#fff"/>'))
            else:
                # torn: the inside of the far wall shows (dark), then the near shell knocks out over it
                back = [i for i in range(n) if self.c.rot(_add(_mul(v, math.cos(th[i])), _mul(w, math.sin(th[i]))))[2] <= 0]
                inner = ' '.join(self.k.poly([self.c.p(A[i]), self.c.p(A[(i + 1) % n]), self.c.p(B[(i + 1) % n]), self.c.p(B[i])]) for i in back)
                out.append(('fn', (lambda d_: lambda: _ruled_path(self.k, d_, 4, ang + 90))(inner)))
                front = [i for i in range(n) if i not in back or (i - 1) % n not in back]
                fr = ' '.join(self.k.poly([self.c.p(A[i]), self.c.p(A[(i + 1) % n]), self.c.p(B[(i + 1) % n]), self.c.p(B[i])]) for i in range(n) if i not in back)
                out.append(('svg', f'<path d="{fr}" fill="#fff" stroke="#fff" stroke-width="0.8"/>'))
            D = max(math.dist(self.c.p(A[0]), self.c.p(A[n // 2])), math.dist(self.c.p(A[n // 4]), self.c.p(A[3 * n // 4])), 2 * r * self.c.s)
            N = max(10, int(D * math.pi / 5.0))
            segs = []
            for i in range(N):
                q = (i + 0.5) / N * TAU
                nn = _norm(_add(_add(_mul(v, math.cos(q)), _mul(w, math.sin(q))), u, slope))
                rz = self.c.rot(nn)
                if rz[2] <= 0.02: continue
                d = _dot(rz, self.c.LIGHT) - 0.18 * off
                if d > 0.82: continue
                wd = 0.22 + 1.9 * max(0.0, min(1.0, (0.8 - d) / 1.3)) ** 1.2
                rv = _add(_mul(v, math.cos(q)), _mul(w, math.sin(q)))
                fi = q / TAU * n; i0 = int(fi) % n; fr_ = fi - int(fi)
                et = endt[i0] + (endt[(i0 + 1) % n] - endt[i0]) * fr_
                pa = self.c.p(_add(a, rv, r)); pb = self.c.p(_add(_add(a, u, L * et), rv, r + (r2 - r) * et))
                segs.append(f'<line x1="{pa[0]:.1f}" y1="{pa[1]:.1f}" x2="{pb[0]:.1f}" y2="{pb[1]:.1f}" stroke-width="{wd:.2f}"/>')
            out.append(('svg', '<g stroke="#000" stroke-linecap="butt">' + ''.join(segs) + '</g>'))
            if ends is not None:
                # silhouette lines and the jagged torn edge
                for i in range(n):
                    j = (i + 1) % n
                    vi = self.c.rot(_add(_mul(v, math.cos(th[i] + 0.5 * TAU / n)), _mul(w, math.sin(th[i] + 0.5 * TAU / n))))[2] > 0
                    if vi: out.append(('line', [self.c.p(B[i]), self.c.p(B[j])], 1.3, False))
                    out.append(('line', [self.c.p(A[i]), self.c.p(A[j])], 1.0, False))
                    vprev = self.c.rot(_add(_mul(v, math.cos(th[i] - 0.5 * TAU / n)), _mul(w, math.sin(th[i] - 0.5 * TAU / n))))[2] > 0
                    if vi != vprev: out.append(('line', [self.c.p(A[i]), self.c.p(B[i])], 1.0, False))
        else:
            for i in range(n):
                if i in skip: continue
                j = (i + 1) % n; qm = (th[i] + (th[j] if j else TAU)) / 2
                nn = _norm(_add(_add(_mul(v, math.cos(qm)), _mul(w, math.sin(qm))), u, slope))
                if self.c.rot(nn)[2] <= 0: continue
                pts = [A[i], A[j], B[j], B[i]]
                ops.append((self.c.z(_add(A[i], nn, 0.01)), ('poly', [self.c.p(q) for q in pts], self.c.tone(nn, off), ang, 0)))
            ops.sort(key=lambda o: o[0])
            out = [o for _, o in ops]
        if ends is None:
            hull = _hull([self.c.p(q) for q in A + B])
            out.append(('line', hull, ol * 1.0, True))
        for tt in seams:
            vis = []
            for q in [i / 48 * TAU for i in range(49)]:
                nn = _add(_mul(v, math.cos(q)), _mul(w, math.sin(q)))
                if self.c.rot(nn)[2] > 0:
                    rr = r + (r2 - r) * tt
                    vis.append(self.c.p(_add(_add(a, u, L * tt), _add(_mul(v, math.cos(q) * rr), _mul(w, math.sin(q) * rr)))))
                elif len(vis) > 1:
                    out.append(('line', vis, 0.6, False)); vis = []
                else: vis = []
            if len(vis) > 1: out.append(('line', vis, 0.6, False))
        for end, ring, nn in ((0, A, _mul(u, -1)), (1, B, u)):
            if caps[end] and self.c.rot(nn)[2] > 0:
                out.append(('poly', [self.c.p(q) for q in ring], self.c.tone(nn, off + cap_off), ang + 50, ol))
        out += extra or []
        self.add(self.c.z(_mul(_add(a, b), 0.5)) + depth_bias, out)
        return (u, v, w, L)

    def s_w(self): return 0.4


def _basis(a, b):
    u = _norm(_v(b, a)); t = (0, 1, 0) if abs(u[1]) < 0.9 else (1, 0, 0)
    v = _norm(_cross(u, t)); return u, v, _cross(u, v)

def _rotx(p, a):
    return (p[0], p[1] * math.cos(a) - p[2] * math.sin(a), p[1] * math.sin(a) + p[2] * math.cos(a))

def _roty(p, a):
    return (p[0] * math.cos(a) + p[2] * math.sin(a), p[1], -p[0] * math.sin(a) + p[2] * math.cos(a))

def _grid_fn(k, cam, c, e1, e2, n1, n2, w=0.5, op=0.9):
    """Ruled grid across a parallelogram face (solar cells, panels)."""
    def f():
        d = []
        for i in range(n1 + 1):
            t = -1 + 2 * i / n1
            p0, p1 = cam.p(_add(_add(c, e1, t), e2, -1)), cam.p(_add(_add(c, e1, t), e2, 1))
            d.append(f'M{p0[0]:.1f},{p0[1]:.1f} L{p1[0]:.1f},{p1[1]:.1f}')
        for j in range(n2 + 1):
            t = -1 + 2 * j / n2
            p0, p1 = cam.p(_add(_add(c, e2, t), e1, -1)), cam.p(_add(_add(c, e2, t), e1, 1))
            d.append(f'M{p0[0]:.1f},{p0[1]:.1f} L{p1[0]:.1f},{p1[1]:.1f}')
        _thin(k, ' '.join(d), w, op)
    return ('fn', f)

def _pits(k, cam, pts3, r):
    """Ageing: scattered dents and patches on a hull (projected)."""
    def f():
        dots = [(*cam.p(p), r * k.r.uniform(0.5, 1.2)) for p in pts3]
        _dots(k, dots, 0)
    return ('fn', f)

def _torus(k, S, c, centre, e1, e2, R, rt, m=28, n=10, seam_every=2, extra_fn=None):
    """A ring of tube segments in the plane (e1, e2), with true silhouette edges so it reads as one torus."""
    V = c.view(); ax = _norm(_cross(e1, e2))
    def at(q, phi_sign):
        rho = _add(_mul(e1, math.cos(q)), _mul(e2, math.sin(q)))
        a1, a2 = _dot(rho, V), _dot(ax, V)
        phi = math.atan2(-a1, a2) + (0 if phi_sign > 0 else math.pi)
        nrm = _add(_mul(rho, math.cos(phi)), _mul(ax, math.sin(phi)))
        return _add(_add(centre, rho, R), nrm, rt)
    for i in range(m):
        q0, q1 = i / m * TAU, (i + 1) / m * TAU
        p0 = _add(centre, _add(_mul(e1, math.cos(q0) * R), _mul(e2, math.sin(q0) * R)))
        p1 = _add(centre, _add(_mul(e1, math.cos(q1) * R), _mul(e2, math.sin(q1) * R)))
        ex = []
        for sg in (1, -1):
            ex.append(('line', [c.p(at(q0 + (q1 - q0) * j / 4, sg)) for j in range(5)], 0.9, False))
        if extra_fn: ex += extra_fn(q0, q1)
        S.cyl(p0, p1, rt, n=n, caps=(False, False), seams=(0.0,) if i % seam_every == 0 else (), ol=0, extra=ex)

def _ring_lines(c, centre, e1, e2, radii, w=0.6):
    """Concentric plate seams on a flat disc face."""
    out = []
    for r in radii:
        out.append(('line', [c.p(_add(centre, _add(_mul(e1, math.cos(q) * r), _mul(e2, math.sin(q) * r)))) for q in [i / 40 * TAU for i in range(41)]], w, False))
    return out

def ark_ship(k, x, y, s, spec=None):
    """The ageing ark: layered shield at the bow, a spinning habitat ring, trussed spine, cargo clusters,
    ribbed radiators and a heavy engine block with bells."""
    k.depth = 0.95
    c = _Cam(x, y, s * 0.9, yaw=0.48, pitch=0.3, roll=-0.14, persp=0.08)
    S = _Scene(k, c)
    # trussed spine: longerons and zigzag braces around a thin core
    S.cyl((-1.25, 0, 0), (1.2, 0, 0), 0.035, n=8, seams=[i / 12 for i in range(1, 12)])
    tr = []
    o = 0.075
    corners = [(o, o), (o, -o), (-o, -o), (-o, o)]
    for (ay, az) in corners:
        tr.append(('line', [c.p((-0.85, ay, az)), c.p((1.15, ay, az))], 0.7, False))
    for i in range(24):
        x0, x1 = -0.85 + i * 2.0 / 24, -0.85 + (i + 1) * 2.0 / 24
        for j in range(4):
            (ay, az), (by, bz) = corners[j], corners[(j + 1) % 4]
            tr.append(('line', [c.p((x0, ay, az)), c.p((x1, by, bz))], 0.45, False))
    S.add(c.z((0, 0, 0)) - 0.001, tr)
    # bow shield: layered plates with concentric seams
    S.cyl((1.16, 0, 0), (1.24, 0, 0), 0.5, n=36, seams=(0.5,), extra=_ring_lines(c, (1.24, 0, 0), (0, 1, 0), (0, 0, 1), (0.42, 0.34)))
    S.cyl((1.24, 0, 0), (1.3, 0, 0), 0.28, n=24, cap_off=1, extra=_ring_lines(c, (1.3, 0, 0), (0, 1, 0), (0, 0, 1), (0.18, 0.1)))
    # habitat ring with spokes and hub
    R, rt, X0 = 0.56, 0.07, 0.55
    _torus(k, S, c, (X0, 0, 0), (0, 1, 0), (0, 0, 1), R, rt, m=30, n=10, seam_every=1)
    for i in range(6):
        q = i / 6 * TAU + 0.4
        S.cyl((X0, math.cos(q) * 0.09, math.sin(q) * 0.09), (X0, math.cos(q) * (R - rt), math.sin(q) * (R - rt)), 0.014, n=6)
    S.cyl((X0 - 0.07, 0, 0), (X0 + 0.07, 0, 0), 0.1, n=16, seams=(0.5,), off=1)
    # cargo clusters: stacks of pods around the spine
    for x0, x1 in ((-0.78, -0.42), (-0.36, 0.0), (0.06, 0.32)):
        for j in range(6):
            q = j / 6 * TAU + (0.3 if x0 > -0.5 else 0)
            r = 0.085 if x0 < 0.05 else 0.06
            oy, oz = math.cos(q) * (0.075 + r), math.sin(q) * (0.075 + r)
            if x0 > 0 and j % 2: continue
            S.cyl((x0, oy, oz), (x1, oy, oz), r, n=14, seams=(0.33, 0.66), off=(1 if (j + int(x0 * 10)) % 3 == 0 else 0))
    # ribbed radiators
    for sgn in (-1, 1):
        cpos = (-0.6, 0.0, sgn * 0.52)
        S.box(cpos, (0.42, 0.012, 0.5), off=1, ol=0.6, extra=[_grid_fn(k, c, _add(cpos, (0, 0.007, 0)), (0.21, 0, 0), (0, 0, 0.25), 12, 1, 0.5)])
        S.cyl((-0.6, 0, sgn * 0.08), (-0.6, 0, sgn * 0.27), 0.012, n=6)
    # engine block and bells
    S.cyl((-1.2, 0, 0), (-0.86, 0, 0), 0.22, n=24, seams=(0.25, 0.5, 0.75), off=1)
    S.box((-1.03, 0.0, 0.0), (0.16, 0.4, 0.4), off=0)
    for dy, dz in ((0.11, 0.0), (-0.07, 0.1), (-0.07, -0.1), (0.0, 0.0)):
        S.cyl((-1.22, dy, dz), (-1.46, dy * 1.4, dz * 1.4), 0.05, r2=0.11, n=16, cap_off=3, caps=(False, True))
    # antenna mast at the bow
    S.cyl((0.95, 0.07, 0), (0.95, 0.42, 0), 0.008, n=4)
    S.cyl((0.95, 0.42, 0), (0.98, 0.47, 0.02), 0.01, r2=0.07, n=12, cap_off=-1)
    S.render()
    _wash(k, spec, x, y, s * 1.3, s * 0.5, 1, 0.3)

def satellite(k, x, y, s, spec=None):
    """A watchful satellite: hexagonal bus, twin ruled solar wings, a dish and a single dark lens."""
    k.depth = 0.95
    c = _Cam(x, y, s * 0.8, yaw=0.55, pitch=0.28, roll=0.12)
    S = _Scene(k, c)
    S.cyl((0, -0.32, 0), (0, 0.32, 0), 0.24, n=6, seams=(0.33, 0.66), cap_off=0)
    for sgn in (-1, 1):
        S.cyl((sgn * 0.22, 0, 0), (sgn * 0.45, 0, 0), 0.02, n=6)
        tilt = 0.35
        e1 = (0.55, 0, 0); e2 = _rotx((0, 0, 0.24), tilt)
        cpos = (sgn * 1.02, 0, 0)
        S.box(cpos, (1.1, 0.015, 0.48), basis=((1, 0, 0), _rotx((0, 1, 0), tilt), _rotx((0, 0, 1), tilt)), off=1, ol=0.7,
              extra=[_grid_fn(k, c, _add(cpos, _rotx((0, 0.009, 0), tilt)), e1, e2, 10, 4, 0.55)])
    S.cyl((0, 0.32, 0.02), (0.05, 0.42, 0.2), 0.04, r2=0.3, n=26, caps=(False, True), cap_off=-1)
    S.cyl((0.05, 0.42, 0.2), (0.12, 0.62, 0.55), 0.008, n=4)
    S.cyl((0, -0.32, 0), (0.0, -0.55, 0.0), 0.012, n=4)
    S.cyl((0.1, -0.3, 0.1), (0.25, -0.7, 0.2), 0.006, n=4)
    # the lens on the face nearest the viewer
    def eye():
        ex, ey = c.p((0.0, -0.05, 0.27)); r = s * 0.075
        k.ink.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{r * 1.25:.1f}" fill="#fff" stroke="#000" stroke-width="1.2"/>')
        k.solid(_oval(ex, ey, r, r))
        k.ink.append(f'<circle cx="{ex - r * 0.35:.1f}" cy="{ey - r * 0.35:.1f}" r="{max(1, r * 0.22):.1f}" fill="#fff"/>')
        _white(k, f'M{ex + r * 0.5:.1f},{ey - r * 0.1:.1f} q{-r * 0.1:.1f},{r * 0.4:.1f} {-r * 0.5:.1f},{r * 0.55:.1f}', max(0.7, r * 0.06))
    S.add(5.0, [('fn', eye)])
    S.render()
    _wash(k, spec, x, y, s * 1.2, s * 0.45, 1, 0.3)

def station_ring(k, x, y, s, spec=None):
    """A ring station seen from above at a slant: segmented torus, spokes, a hub with a docking spike."""
    k.depth = 0.95
    c = _Cam(x, y, s * 0.95, yaw=0.15, pitch=0.62, roll=-0.12, persp=0.06)
    S = _Scene(k, c)
    R, rt = 1.0, 0.12
    def windows(q0, q1):
        qm = (q0 + q1) / 2
        pts = [(math.cos(qm + (j - 1) * 0.04) * (R + rt * 0.98), -0.02, math.sin(qm + (j - 1) * 0.04) * (R + rt * 0.98)) for j in range(3)]
        return [('fn', lambda: _dots(k, [(*c.p(p), max(0.7, s * 0.005)) for p in pts if c.z(p) > 0.1], 0, fill='#fff', stroke='#000', sw=0.5))]
    _torus(k, S, c, (0, 0, 0), (1, 0, 0), (0, 0, 1), R, rt, m=36, n=12, seam_every=3, extra_fn=windows)
    for i in range(6):
        q = i / 6 * TAU + 0.3
        S.cyl((math.cos(q) * 0.15, 0, math.sin(q) * 0.15), (math.cos(q) * (R - rt), 0, math.sin(q) * (R - rt)), 0.022, n=6, seams=(0.33, 0.66))
    for sgn in (-1, 1):
        cp = (sgn * 0.3, 0.42, 0)
        S.box(cp, (0.4, 0.01, 0.16), off=1, ol=0.6, extra=[_grid_fn(k, c, _add(cp, (0, 0.006, 0)), (0.2, 0, 0), (0, 0, 0.08), 6, 2, 0.45)])
    S.cyl((0, -0.22, 0), (0, 0.18, 0), 0.17, n=18, seams=(0.25, 0.5, 0.75))
    S.cyl((0, 0.18, 0), (0, 0.55, 0), 0.04, n=8, seams=(0.5,))
    S.cyl((0, -0.22, 0), (0, -0.45, 0), 0.07, r2=0.03, n=10)
    S.render()
    _wash(k, spec, x, y, s * 1.1, s * 0.5, 1, 0.3)


def _surface_pts(c, a, u, v, w, r, q0, q1, t0, t1, L, n=10):
    """Outline of a patch on a cylinder surface (angles q0..q1, axial t0..t1)."""
    pts = []
    for i in range(n + 1): q = q0 + (q1 - q0) * i / n; pts.append(_add(_add(a, u, L * t0), _add(_mul(v, math.cos(q) * r), _mul(w, math.sin(q) * r))))
    for i in range(n + 1): q = q1 - (q1 - q0) * i / n; pts.append(_add(_add(a, u, L * t1), _add(_mul(v, math.cos(q) * r), _mul(w, math.sin(q) * r))))
    return pts

def cryo_pod(k, x, y, s, spec=None):
    """A cryo-sleep capsule leaning back on its plinth: ruled steel shell, frosted window with a sleeper's shape."""
    k.depth = 0.95
    c = _Cam(x, y + s * 0.05, s * 0.95, yaw=0.42, pitch=0.12, persp=0.05)
    S = _Scene(k, c)
    a, b = (0, -0.62, -0.1), (0, 0.78, 0.22)
    u, v, w = _basis(a, b); L = math.dist(a, b); r = 0.36
    # plinth and pipes
    S.box((0, -0.82, 0.0), (0.95, 0.22, 0.85), off=1)
    S.box((0, -0.67, -0.02), (0.78, 0.1, 0.7), off=0)
    # the window patch, centred on the face toward the viewer
    rv, rw = c.rot(v)[2], c.rot(w)[2]
    q0 = math.atan2(rw, rv)
    win = _surface_pts(c, a, u, v, w, r * 1.005, q0 - 0.75, q0 + 0.75, 0.3, 0.9, L, 14)
    def window():
        pts = [c.p(p) for p in win]
        d = k.poly(pts)
        k.ink.append(f'<path d="{d}" fill="#fff"/>')
        cid = _clip(k, d); start = len(k.ink)
        # the sleeper: head and shoulders seen dimly through frost
        hc = c.p(_add(_add(a, u, L * 0.76), _add(_mul(v, math.cos(q0) * r * 0.6), _mul(w, math.sin(q0) * r * 0.6))))
        sc = c.p(_add(_add(a, u, L * 0.52), _add(_mul(v, math.cos(q0) * r * 0.6), _mul(w, math.sin(q0) * r * 0.6))))
        R = s * 0.11
        k.shape(_oblob(k, hc[0], hc[1], R * 0.8, R, 0.15, 12, 0.03), tone=2, dark=3, angle=30, outline=0.6)
        k.shape(k.smooth([(sc[0] - R * 2.6, sc[1] + R * 1.8), (sc[0] - R * 2.2, sc[1] - R * 0.6), (sc[0] - R * 0.5, sc[1] - R * 1.4), (sc[0] + R * 0.5, sc[1] - R * 1.4),
                          (sc[0] + R * 2.2, sc[1] - R * 0.6), (sc[0] + R * 2.6, sc[1] + R * 1.8)]), tone=2, dark=3, angle=30, outline=0.6)
        k.stipple((pts[0][0] + pts[len(pts) // 2][0]) / 2, (pts[0][1] + pts[len(pts) // 2][1]) / 2, s * 0.3, s * 0.45, int(30 + s * 0.7), (0.4, 1.1))
        # reflections on the glass: two long diagonal glints and fine rules
        gx, gy = pts[3]
        refl = ' '.join(f'M{gx + s * (0.05 + i * 0.03):.1f},{gy - s * 0.05:.1f} l{s * 0.1:.1f},{s * 0.6:.1f}' for i in range(3))
        _thin(k, refl, 0.5, 0.7)
        _wrap(k, start, f'clip-path="url(#{cid})"')
        k.ink.append(f'<path d="{d}" fill="none" stroke="#000" stroke-width="1.6" stroke-linejoin="round"/>')
        inner = _surface_pts(c, a, u, v, w, r * 1.005, q0 - 0.82, q0 + 0.82, 0.27, 0.93, L, 14)
        _thin(k, k.poly([c.p(p) for p in inner]), 0.9)
        # rivets around the frame
        _dots(k, [(*c.p(p), max(0.8, s * 0.006)) for p in inner[::2]], 0)
    # side panel with lamps
    def lamps():
        q = q0 + 1.15
        pts = [c.p(_add(_add(a, u, L * t), _add(_mul(v, math.cos(q) * r), _mul(w, math.sin(q) * r)))) for t in (0.35, 0.42, 0.49, 0.56)]
        for i, (px, py) in enumerate(pts):
            k.ink.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{max(1.2, s * 0.012):.1f}" fill="{"#000" if i % 2 else "#fff"}" stroke="#000" stroke-width="0.8"/>')
    S.cyl(a, b, r, n=28, seams=(0.08, 0.22, 0.96), caps=(False, False), extra=[('fn', window), ('fn', lamps)])
    S.cyl(b, _add(b, u, 0.1), r, r2=r * 0.7, n=24, caps=(False, True), cap_off=0, depth_bias=-0.01)
    S.render()
    # hoses from the plinth to the floor
    for sgn in (-1, 1):
        p0 = c.p((sgn * 0.42, -0.72, 0.2)); p1 = (p0[0] + sgn * s * 0.45, p0[1] + s * 0.3)
        k.shape(tapered(k, _bez(p0, (p0[0] + sgn * s * 0.3, p0[1] - s * 0.05), p1, 10), s * 0.02, s * 0.018), tone=2, dark=4, angle=0, outline=0.8)
        for t in range(1, 10):
            px, py = _bez(p0, (p0[0] + sgn * s * 0.3, p0[1] - s * 0.05), p1, 10)[t]
            k.line(f'M{px - s * 0.012:.1f},{py - s * 0.012:.1f} l{s * 0.024:.1f},{s * 0.024:.1f}', 0.5, rough=False)
    # frost breath: cold vapour curling from the base
    for i in range(5):
        px = x + s * k.r.uniform(-0.6, 0.6); py = y + s * 0.95
        k.line(f'M{px:.1f},{py:.1f} q{s * 0.1:.1f},{-s * 0.08:.1f} {s * 0.05:.1f},{-s * 0.18:.1f} t{s * 0.08:.1f},{-s * 0.15:.1f}', 0.5, 0.5)
    _wash(k, spec, x, y - s * 0.1, s * 0.5, s * 0.75, 0, 0.4)
    _wash(k, spec, x, y + s * 0.2, s * 0.3, s * 0.4, 1, 0.3)

def _screen_lines(k, quad, f, rows, wmax, glow=False):
    """Scanlines across a projected quad, thickness from f(u, v) in 0..1 (an engraved line portrait)."""
    (ax, ay), (bx, by), (cx, cy), (dx, dy) = quad
    def P(u, v):
        tx, ty = ax + (bx - ax) * u, ay + (by - ay) * u
        sx, sy = dx + (cx - dx) * u, dy + (cy - dy) * u
        return (tx + (sx - tx) * v, ty + (sy - ty) * v)
    out = []
    cols = 90
    for j in range(rows):
        v = (j + 0.5) / rows
        top, bot = [], []
        for i in range(cols + 1):
            u = i / cols
            wv = max(0.0, min(1.0, f(u, v))) * wmax / 2
            px, py = P(u, v)
            top.append((px, py - wv)); bot.append((px, py + wv + 0.12))
        out.append(k.poly(top + bot[::-1]))
    k.ink.append(f'<path d="{" ".join(out)}" fill="#000"/>')

def _face_tone(u, v, seed=0.0):
    """A calm face, gently three-quarter, as darkness 0..1 for the scanline engraving (dark screen, lit face)."""
    X, Y = (u - 0.52) / 0.24, (v - 0.47) / 0.33
    r2 = X * X + Y * Y
    if Y < -0.45 and X * X / 1.25 + Y * Y / 1.3 < 1.0 and r2 > 0.55:   # hair
        return 0.62 + 0.25 * max(0, X)
    if r2 > 1.0 and abs(X + 0.05) < 0.42 and 0.6 < Y < 1.35:          # neck
        return 0.42 + 0.3 * max(0, X)
    if Y > 1.15 and (X / 2.3) ** 2 + ((Y - 2.0) / 0.85) ** 2 < 1:    # shoulders
        return 0.3 + 0.2 * max(0, X / 2)
    if r2 > 1.0:
        edge = min(1.0, (r2 - 1.0) * 6)
        return 0.6 + 0.35 * edge
    t = 0.12 + 0.3 * max(0, X) ** 2 + 0.2 * r2 ** 2       # shade toward the far cheek and rim
    for ex in (-0.38, 0.38):                                # eye sockets
        e = ((X - ex) / 0.24) ** 2 + ((Y + 0.12) / 0.11) ** 2
        if e < 1: t += 0.55 * (1 - e)
        b = ((X - ex) / 0.3) ** 2 + ((Y + 0.33) / 0.06) ** 2   # brows
        if b < 1: t += 0.35 * (1 - b)
    n = ((X - 0.08) / 0.1) ** 2 + ((Y - 0.22) / 0.2) ** 2     # nose shadow
    if n < 1 and X > 0.0: t += 0.4 * (1 - n)
    m = (X / 0.32) ** 2 + ((Y - 0.55) / 0.05) ** 2            # mouth line
    if m < 1: t += 0.6 * (1 - m)
    return min(1.0, t)

def screen_face(k, x, y, s, spec=None):
    """The AI on a screen: a face rendered as modulated scanlines inside a heavy bezel, glow ruled outward."""
    k.depth = 0.95
    c = _Cam(x, y, s * 0.95, yaw=-0.32, pitch=0.06, persp=0.08)
    S = _Scene(k, c)
    W2, H2 = 0.78, 0.6
    S.box((0, 0, -0.06), (W2 * 2 + 0.16, H2 * 2 + 0.16, 0.12), off=1)
    S.render()
    quad = [c.p((-W2, H2, 0.002)), c.p((W2, H2, 0.002)), c.p((W2, -H2, 0.002)), c.p((-W2, -H2, 0.002))]
    k.paper(k.poly(quad))
    rows = max(28, int(abs(quad[3][1] - quad[0][1]) / 5.2))
    _screen_lines(k, quad, lambda u_, v_: 0.18 + 0.82 * _face_tone(u_, v_), rows, abs(quad[3][1] - quad[0][1]) / rows * 0.92)
    _thin(k, k.poly(quad), 1.4)
    # glow: ruled rays outward from the screen edges
    cx_, cy_ = sum(p[0] for p in quad) / 4, sum(p[1] for p in quad) / 4
    _rays(k, cx_, cy_, s * 1.0, s * 1.45, 46, 0.45, 0.3)
    # small status lamps under the screen
    for i in range(4):
        px, py = c.p((-0.6 + i * 0.12, -H2 - 0.045, 0.01))
        k.ink.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{max(1, s * 0.012):.1f}" fill="{"#fff" if i == 0 else "#000"}" stroke="#000" stroke-width=".6"/>')
    _wash(k, spec, cx_, cy_, s * 0.9, s * 0.7, 0, 0.45)
    _wash(k, spec, cx_, cy_, s * 0.5, s * 0.45, 1, 0.3)

def console(k, x, y, s, spec=None):
    """A control console: slanted key deck, rows of switches, two hooded monitors glowing with traces."""
    k.depth = 0.95
    c = _Cam(x, y + s * 0.15, s * 0.9, yaw=-0.42, pitch=0.38, persp=0.06)
    S = _Scene(k, c)
    S.box((0, -0.4, 0.0), (2.0, 0.6, 0.7), off=1)
    tilt = -0.55
    bx = ((1, 0, 0), _rotx((0, 1, 0), tilt), _rotx((0, 0, 1), tilt))
    dc = (0, -0.03, 0.12)
    def keys():
        top = _add(dc, _rotx((0, 0.045, 0), tilt))
        e1, e2 = (1, 0, 0), _rotx((0, 0, 1), tilt)
        for i in range(16):
            for j in range(4):
                if (i + j * 3) % 7 == 0: continue
                cc = _add(_add(top, e1, -0.85 + i * 0.113), e2, -0.2 + j * 0.11)
                q = [c.p(_add(_add(cc, e1, sx * 0.04), e2, sz * 0.035)) for sx, sz in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
                if (i * 5 + j) % 9 == 0: k.solid(k.poly(q))
                else: _thin(k, k.poly(q, True), 0.7)
        for i in range(3):     # dials
            cc = c.p(_add(_add(top, e1, 0.55 + i * 0.13), e2, 0.27))
            k.ink.append(f'<circle cx="{cc[0]:.1f}" cy="{cc[1]:.1f}" r="{s * 0.035:.1f}" fill="#fff" stroke="#000" stroke-width="0.8"/>')
            _thin(k, f'M{cc[0]:.1f},{cc[1]:.1f} l{s * 0.025:.1f},{-s * 0.02:.1f}', 0.9)
    S.box(dc, (2.0, 0.09, 0.62), basis=bx, off=0, extra=[('fn', keys)])
    screens = []
    for cx0, yaw in ((-0.5, 0.18), (0.5, -0.12)):
        cp = (cx0, 0.55, -0.22)
        e1 = _roty((0.42, 0, 0), yaw); e2 = (0, 0.3, 0); nz = _roty((0, 0, 1), yaw)
        S.box(cp, (0.95, 0.7, 0.08), basis=(_roty((1, 0, 0), yaw), (0, 1, 0), nz), off=1)
        S.cyl(_add(cp, (0, -0.3, -0.02)), _add(cp, (0, -0.68, -0.02)), 0.03, n=8)
        f = _add(cp, nz, 0.042)
        quad = [c.p(_add(_add(f, e1, -1), e2, 1)), c.p(_add(_add(f, e1, 1), e2, 1)), c.p(_add(_add(f, e1, 1), e2, -1)), c.p(_add(_add(f, e1, -1), e2, -1))]
        screens.append(quad)
    S.render()
    for qi, quad in enumerate(screens):
        k.paper(k.poly(quad))
        rows = max(10, int(abs(quad[3][1] - quad[0][1]) / 4))
        if qi == 0:
            fn = lambda u_, v_: 0.08 + (0.9 if abs(v_ - (0.5 + 0.3 * math.sin(u_ * 14) * math.exp(-((u_ - 0.5) ** 2) * 6))) < 0.06 else 0.0)
        else:
            fn = lambda u_, v_: 0.08 + (0.85 if (abs(v_ - 0.82 + 0.6 * u_ ** 1.5) < 0.05 or (int(u_ * 8) % 2 == 0 and v_ > 0.9 - 0.4 * abs(math.sin(u_ * 9)))) else 0.0)
        _screen_lines(k, quad, fn, rows, abs(quad[3][1] - quad[0][1]) / rows * 0.9)
        _thin(k, k.poly(quad), 1.0)
        cx_, cy_ = sum(p[0] for p in quad) / 4, sum(p[1] for p in quad) / 4
        _rays(k, cx_, cy_, s * 0.45, s * 0.95, 22, 0.45, 0.3, -math.pi * 0.95, -math.pi * 0.05)
        _wash(k, spec, cx_, cy_, s * 0.5, s * 0.35, 0, 0.4)
    _wash(k, spec, x, y + s * 0.2, s * 0.9, s * 0.4, 1, 0.25)


def shuttle(k, x, y, s, spec=None):
    """A delta-winged shuttle diving at three-quarters: ruled fuselage, swept wings, tail fin, glowing nozzles."""
    k.depth = 0.95
    c = _Cam(x, y, s * 0.95, yaw=0.75, pitch=0.42, roll=0.32, persp=0.06)
    S = _Scene(k, c)
    S.cyl((-0.9, 0, 0), (0.55, 0, 0), 0.16, n=24, seams=(0.2, 0.45, 0.7), caps=(True, False))
    S.cyl((0.55, 0, 0), (0.95, -0.03, 0), 0.16, r2=0.05, n=24, caps=(False, True), seams=(0.5,))
    S.cyl((0.95, -0.03, 0), (1.02, -0.04, 0), 0.05, r2=0.01, n=12, caps=(False, False))
    # wings: thick delta plates
    for sgn in (-1, 1):
        root0, root1, tip0, tip1 = (0.35, -0.06, sgn * 0.1), (-0.85, -0.06, sgn * 0.12), (-0.85, -0.08, sgn * 0.85), (-0.55, -0.08, sgn * 0.85)
        top = [root0, root1, tip0, tip1]
        ops = []
        S.poly(top, off=0, ol=1.0, two_sided=True, ops=ops)
        # control-surface seam and panel lines along the wing
        ln = [('line', [c.p(_lerp3(top[1], top[2], 0.0) if False else _add(top[1], (0.12, 0.002, 0))), c.p(_add(top[2], (0.12, 0.002, 0)))], 0.6, False)]
        ln += [('line', [c.p(_add(top[0], (-0.3 * t * 4, 0.002, sgn * 0.05 * t))), c.p(_add(top[3], (-0.08 * t, 0.002, 0)))], 0.4, False) for t in (0.1, 0.2)]
        S.add(sum(c.z(p) for p in top) / 4 + 0.02 * sgn, [o for _, o in ops] + ln)
    fin = [(-0.55, 0.12, 0), (-0.88, 0.12, 0), (-0.95, 0.48, 0), (-0.8, 0.48, 0)]
    ops = []
    S.poly(fin, off=0, ol=0.8, ops=ops)
    S.add(c.z((-0.75, 0.3, 0)), [o for _, o in ops])
    # cockpit windows
    def cockpit():
        for i in range(4):
            q = -0.55 + i * 0.32
            pts = [c.p((0.62 + dx, 0.1 * math.cos(q + dq) + 0.04, 0.1 * math.sin(q + dq))) for dx, dq in ((0, 0), (0.1, 0.02), (0.1, 0.25), (0, 0.27))]
            k.solid(k.poly(pts))
        p = c.p((0.68, 0.14, -0.05)); _white(k, f'M{p[0]:.1f},{p[1]:.1f} l{s * 0.04:.1f},{-s * 0.01:.1f}', max(0.8, s * 0.006))
    S.add(c.z((0.7, 0.1, 0)) + 0.3, [('fn', cockpit)])
    for dz in (-0.07, 0.07):
        S.cyl((-0.9, 0.0, dz), (-1.02, 0.0, dz * 1.3), 0.05, r2=0.075, n=14, caps=(False, True), cap_off=3)
    S.render()
    # exhaust and re-entry streaks trailing behind
    tail = c.p((-1.05, 0, 0)); nose = c.p((1.0, 0, 0))
    ang = math.atan2(tail[1] - nose[1], tail[0] - nose[0])
    for i in range(14):
        off = (i - 7) * s * 0.018
        L = s * k.r.uniform(0.5, 1.3)
        px, py = tail[0] - math.sin(ang) * off, tail[1] + math.cos(ang) * off
        k.line(f'M{px:.1f},{py:.1f} l{math.cos(ang) * L:.1f},{math.sin(ang) * L:.1f}', 0.5, 0.55, rough=False)
    _wash(k, spec, x, y, s * 0.9, s * 0.5, 1, 0.35)

def _lerp3(a, b, t): return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)

def _billow(k, cx, cy, R, n=7, tone=1, dark=3, angle=30, seed_r=0.35):
    """A cumulus mass of smoke or cloud: overlapping round lobes, back ones first, each shaded to lower right
    with a few curled contour strokes, so the edge scallops like an engraved cloud."""
    lobes = []
    for i in range(n):
        a = k.r.uniform(0, TAU); rr = R * math.sqrt(k.r.random()) * 0.55
        lobes.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.8, R * k.r.uniform(0.38, 0.58)))
    lobes.sort(key=lambda l: l[1])
    for lx, ly, lr in lobes:
        d = _oblob(k, lx, ly, lr, lr * 0.9, 0, 14, 0.06)
        k.shape(d, tone=tone, dark=dark, angle=angle + k.r.uniform(-15, 15), outline=0.8)
        k.line(f'M{lx + lr * 0.1:.1f},{ly + lr * 0.75:.1f} q{lr * 0.5:.1f},{-lr * 0.1:.1f} {lr * 0.7:.1f},{-lr * 0.6:.1f}', 0.5, 0.6)

def rocket(k, x, y, s, spec=None):
    """A rocket climbing on a column of flame and billowing smoke."""
    k.depth = 0.95
    tilt = 0.12
    c = _Cam(x + s * 0.05, y - s * 0.35, s * 0.95, yaw=0.3, pitch=0.12, roll=-tilt, persp=0.04)
    # plume first (behind): billows under the tail, then the flame
    base = c.p((0, -0.85, 0))
    for i in range(9):
        t = i / 8
        bx_ = base[0] + math.sin(tilt) * s * 1.4 * t + k.r.uniform(-0.25, 0.25) * s * t
        by_ = base[1] + s * (0.35 + 1.0 * t)
        _billow(k, bx_, by_, s * (0.16 + 0.32 * t), 7, tone=1, dark=3, angle=20 + i * 9)
    flame = k.smooth([(base[0] - s * 0.09, base[1]), (base[0] - s * 0.13, base[1] + s * 0.25), (base[0] + s * 0.02, base[1] + s * 0.62),
                      (base[0] + s * 0.12, base[1] + s * 0.25), (base[0] + s * 0.09, base[1])])
    k.paper(flame); k.line(flame, 1.0)
    for j in range(3):
        f = 0.25 + j * 0.2
        k.line(f'M{base[0] - s * 0.09 * (1 - f):.1f},{base[1] + s * 0.03:.1f} Q{base[0] - s * 0.02:.1f},{base[1] + s * 0.5 * (1 - f * 0.5):.1f} {base[0] + s * 0.09 * (1 - f):.1f},{base[1] + s * 0.03:.1f}', 0.5, 0.8, rough=False)
    S = _Scene(k, c)
    S.cyl((0, -0.75, 0), (0, 0.75, 0), 0.13, n=24, seams=(0.15, 0.4, 0.6, 0.85), caps=(True, False))
    S.cyl((0, 0.75, 0), (0, 1.05, 0), 0.13, r2=0.0, n=24, caps=(False, False), seams=(0.5,))
    S.cyl((0, -0.75, 0), (0, -0.88, 0), 0.06, r2=0.1, n=14, caps=(False, True), cap_off=3)
    for q in (0.5, 0.5 + TAU / 3, 0.5 + 2 * TAU / 3):
        dx, dz = math.cos(q), math.sin(q)
        fin = [(dx * 0.12, -0.45, dz * 0.12), (dx * 0.12, -0.78, dz * 0.12), (dx * 0.32, -0.86, dz * 0.32), (dx * 0.3, -0.62, dz * 0.3)]
        S.poly(fin, off=0, ol=0.8)
    S.render()
    _wash(k, spec, x, y + s * 0.5, s * 0.6, s * 0.8, 0, 0.35)
    _wash(k, spec, base[0], base[1] + s * 0.3, s * 0.2, s * 0.3, 1, 0.5)

def dais(k, x, y, s, spec=None):
    """A machine throne: a reclined chair on stepped circular tiers under a crown of cables."""
    k.depth = 0.95
    c = _Cam(x, y + s * 0.3, s * 0.9, yaw=-0.45, pitch=0.32, persp=0.05)
    S = _Scene(k, c)
    S.cyl((0, -0.62, 0), (0, -0.48, 0), 1.0, n=48, seams=(), cap_off=-1)
    S.cyl((0, -0.48, 0), (0, -0.34, 0), 0.72, n=40, cap_off=-1)
    S.cyl((0, -0.34, 0), (0, -0.2, 0), 0.46, n=36, cap_off=-1)
    # chair: seat, reclined back, head ring, arms
    S.box((0, -0.08, 0.05), (0.42, 0.12, 0.46), off=0)
    rec = -0.5
    S.box((0, 0.3, -0.22), (0.44, 0.75, 0.1), basis=((1, 0, 0), _rotx((0, 1, 0), rec), _rotx((0, 0, 1), rec)), off=0)
    for sgn in (-1, 1):
        S.box((sgn * 0.26, 0.04, 0.05), (0.08, 0.06, 0.42), off=0)
        S.cyl((sgn * 0.26, -0.2, 0.2), (sgn * 0.26, 0.01, 0.2), 0.02, n=6)
    hc = _add((0, 0.3, -0.22), _rotx((0, 0.45, 0), rec))
    _torus(k, S, c, hc, (1, 0, 0), _rotx((0, 1, 0), 0.2), 0.24, 0.035, m=22, n=8, seam_every=2)
    S.render()
    # cables: from the head ring down over the tiers and off to the floor
    hp = c.p(hc)
    for i in range(9):
        a = i / 9 * TAU
        p0 = (hp[0] + math.cos(a) * s * 0.2, hp[1] + math.sin(a) * s * 0.1)
        end = (x + s * (-1.6 + 3.2 * (i / 8)) + k.r.uniform(-0.1, 0.1) * s, y + s * 0.95 + k.r.uniform(-0.05, 0.08) * s)
        mid = ((p0[0] + end[0]) / 2 + k.r.uniform(-0.3, 0.3) * s, max(p0[1], end[1]) - s * 0.1)
        if abs(end[0] - x) < s * 0.7: continue
        k.shape(tapered(k, _bez(p0, mid, end, 14), s * 0.012, s * 0.018), tone=3, dark=4, angle=40, outline=0.6)
    _rays(k, hp[0], hp[1], s * 0.3, s * 0.8, 24, 0.45, 0.3, -math.pi, 0)
    _wash(k, spec, hp[0], hp[1], s * 0.45, s * 0.35, 0, 0.45)
    _wash(k, spec, x, y + s * 0.4, s * 0.9, s * 0.35, 1, 0.3)

def wreck(k, x, y, s, spec=None):
    """A crashed hull half-sunk in the ground: torn end with dark interior and ribs, ground heaped over it, debris."""
    k.depth = 0.95
    c = _Cam(x, y, s * 0.9, yaw=0.62, pitch=0.2, roll=0.18, persp=0.06)
    S = _Scene(k, c)
    n = 26
    ends = [0.7 + 0.25 * abs(math.sin(i * 1.9)) * k.r.uniform(0.3, 1.0) for i in range(n)]
    a0 = (1.1, 0, 0)
    u, v, w, L = S.cyl(a0, (-0.9, 0, 0), 0.4, n=n, ends=ends, caps=(True, False), seams=(0.2, 0.42), off=0)
    S.render()
    # ribs visible inside the torn end
    for tt in (0.6, 0.68):
        pts = [c.p(_add(_add(a0, u, L * tt), _add(_mul(v, math.cos(q) * 0.38), _mul(w, math.sin(q) * 0.38)))) for q in [i / 40 * TAU for i in range(41)]]
        vis = [p for q, p in zip([i / 40 * TAU for i in range(41)], pts) if c.rot(_add(_mul(v, math.cos(q)), _mul(w, math.sin(q))))[2] < 0]
        if len(vis) > 1: _white(k, k.poly(vis, False), max(1.0, s * 0.01))
    # buckled plates: a few bent shards peeled off the hull edge
    for i in range(3):
        q = (0.2 + i * 0.25) * TAU
        base = _add(_add(a0, u, L * ends[int(q / TAU * n)]), _add(_mul(v, math.cos(q) * 0.4), _mul(w, math.sin(q) * 0.4)))
        tip = _add(base, _add(u, _add(_mul(v, math.cos(q)), _mul(w, math.sin(q)))), 0.2)
        p0, p1 = c.p(base), c.p(tip)
        k.shape(k.poly([p0, (p0[0] + s * 0.05, p0[1] + s * 0.03), p1, (p1[0] - s * 0.02, p1[1] - s * 0.03)]), tone=3, dark=4, angle=30, outline=0.9, rough=False)
    # ground heaped over the lower hull
    gy = y + s * 0.25
    pts = [(x - 2.0 * s, gy + 0.18 * s)]
    for i in range(13):
        t = i / 12
        pts.append((x - 1.9 * s + 3.8 * s * t, gy + s * (0.1 * math.sin(t * 7) + k.r.uniform(-0.03, 0.03) - 0.08 * math.exp(-((t - 0.45) * 4) ** 2))))
    pts += [(x + 2.0 * s, gy + 0.2 * s), (x + 1.4 * s, gy + 0.42 * s), (x, gy + 0.36 * s), (x - 1.4 * s, gy + 0.44 * s)]
    k.depth = 0.95
    k.shape(k.smooth(pts), tone=1, dark=3, angle=6, outline=0, rough=True)
    k.line(k.smooth(pts[:14], close=False), 1.3)
    tufts = []
    for px, py in pts[1:13]:
        for j in range(4):
            gx = px + k.r.uniform(-0.12, 0.12) * s
            tufts.append(f'M{gx:.1f},{py + 2:.1f} q{k.r.uniform(-3, 3):.1f},{-s * 0.04:.1f} {k.r.uniform(-6, 6):.1f},{-s * k.r.uniform(0.05, 0.1):.1f}')
    k.line(' '.join(tufts), 0.7)
    for i in range(int(8 + s / 40)):
        px = x + k.r.uniform(-1.7, 1.7) * s; py = gy + k.r.uniform(0.08, 0.3) * s; r = s * k.r.uniform(0.03, 0.08)
        shard = [(px + math.cos(a) * r * k.r.uniform(0.5, 1.2), py + math.sin(a) * r * 0.5 * k.r.uniform(0.5, 1.2)) for a in [j / 5 * TAU + k.r.uniform(0, 0.5) for j in range(5)]]
        k.shape(k.poly(shard), tone=3, dark=4, angle=k.r.uniform(0, 90), outline=0.8, rough=False)
    # a thread of smoke from the break
    tp = c.p(_add(a0, u, L * 0.9))
    for i in range(5):
        _billow(k, tp[0] + s * (0.08 + i * 0.1), tp[1] - s * (0.25 + i * 0.25), s * (0.08 + i * 0.04), 5, tone=1, dark=2, angle=30 + i * 15)
    _wash(k, spec, x, y, s * 1.2, s * 0.5, 1, 0.3)
    _wash(k, spec, x, gy + s * 0.25, s * 1.4, s * 0.25, 0, 0.3)

def cage(k, x, y, s, spec=None):
    """A domed cage hung from a ring: ruled bars (far ones fainter), hoops, a shadowed floor plate."""
    k.depth = 0.95
    c = _Cam(x, y + s * 0.2, s * 0.85, yaw=0.3, pitch=0.25, persp=0.05)
    R, y0, y1 = 0.62, -0.95, 0.45
    nb = 22
    # floor plate and interior shadow
    S = _Scene(k, c)
    S.cyl((0, y0 - 0.08, 0), (0, y0, 0), R * 1.08, n=40, cap_off=-1)
    S.render()
    k.shape(k.poly([c.p((math.cos(q) * R * 0.95, y0 + 0.001, math.sin(q) * R * 0.95)) for q in [i / 30 * TAU for i in range(30)]]), tone=3, dark=4, angle=10, outline=0, knock=False)
    def bar_pts(q):
        pts = [(math.cos(q) * R, yy, math.sin(q) * R) for yy in (y0, y1)]
        for i in range(1, 9):
            ph = i / 8 * math.pi / 2
            pts.append((math.cos(q) * R * math.cos(ph), y1 + math.sin(ph) * R * 0.75, math.sin(q) * R * math.cos(ph)))
        return pts
    for front in (False, True):
        for i in range(nb):
            q = i / nb * TAU
            fz = c.z((math.cos(q), 0, math.sin(q)))
            if (fz > 0) != front: continue
            pts = [c.p(p) for p in bar_pts(q)]
            k.line(k.poly(pts, False), 1.6 if front else 0.7, 1.0 if front else 0.55, rough=False)
            if front and s > 60:
                _white(k, k.poly([(px - 1.0, py) for px, py in pts[:2]], False), 0.5)
        for yy in (y0 + 0.08, y0 + 0.5, y1 - 0.05, y1 + 0.38):
            rr = R if yy <= y1 else R * math.cos(math.asin(min(1, (yy - y1) / (R * 0.75))))
            arc = []
            for j in range(61):
                q = j / 60 * TAU
                if (c.z((math.cos(q), 0, math.sin(q))) > 0) == front:
                    arc.append(c.p((math.cos(q) * rr, yy, math.sin(q) * rr)))
                elif arc:
                    k.line(k.poly(arc, False), 2.2 if front else 1.0, 1.0 if front else 0.6, rough=False); arc = []
            if arc: k.line(k.poly(arc, False), 2.2 if front else 1.0, 1.0 if front else 0.6, rough=False)
    top = c.p((0, y1 + R * 0.75, 0))
    k.line(f'M{top[0]:.1f},{top[1]:.1f} L{top[0]:.1f},{top[1] - s * 0.18:.1f}', 1.4, rough=False)
    k.ink.append(f'<ellipse cx="{top[0]:.1f}" cy="{top[1] - s * 0.25:.1f}" rx="{s * 0.06:.1f}" ry="{s * 0.075:.1f}" fill="none" stroke="#000" stroke-width="{max(1.5, s * 0.014):.1f}"/>')
    for i in range(4):
        k.ink.append(f'<ellipse cx="{top[0]:.1f}" cy="{top[1] - s * (0.36 + i * 0.1):.1f}" rx="{s * 0.025:.1f}" ry="{s * 0.045:.1f}" fill="none" stroke="#000" stroke-width="{max(1.2, s * 0.01):.1f}" transform="rotate({90 * (i % 2)} {top[0]:.1f} {top[1] - s * (0.36 + i * 0.1):.1f})"/>')
    _wash(k, spec, x, y + s * 0.1, s * 0.6, s * 0.7, 1, 0.3)

def lens(k, x, y, s, spec=None):
    """A great lens in a ringed brass mount, turned three-quarters, gathering light to a point."""
    k.depth = 0.95
    c = _Cam(x, y, s * 0.9, yaw=0.62, pitch=0.12, roll=0.05, persp=0.04)
    # converging rays behind (light gathered to a focus at left)
    focus = c.p((0, 0, -1.8)) if False else (x - s * 1.6, y + s * 0.25)
    for i in range(13):
        q = i / 13 * TAU
        p = c.p((0.0, math.sin(q) * 0.7, math.cos(q) * 0.7)) if False else c.p((math.cos(q) * 0.0, math.sin(q) * 0.72, math.cos(q) * 0.72))
        k.line(f'M{p[0]:.1f},{p[1]:.1f} L{focus[0]:.1f},{focus[1]:.1f}', 0.45, 0.45, rough=False)
    S = _Scene(k, c)
    S.cyl((-0.1, 0, 0), (0.1, 0, 0), 0.82, n=56, seams=(0.5,), caps=(False, False), off=0)
    S.render()
    # glass face: white, with concentric reflections and two crescent glints
    face = [c.p((0.1, math.sin(q) * 0.74, math.cos(q) * 0.74)) for q in [i / 60 * TAU for i in range(60)]]
    rim = [c.p((0.1, math.sin(q) * 0.82, math.cos(q) * 0.82)) for q in [i / 60 * TAU for i in range(60)]]
    _ruled(k, rim, 2, 30, 1.2)
    k.paper(k.poly(face))
    for rr in (0.62, 0.45, 0.25):
        pts = [c.p((0.1, math.sin(q) * rr, math.cos(q) * rr)) for q in [i / 50 * TAU for i in range(51)]]
        _thin(k, k.poly(pts[30:48], False), 0.6, 0.6)
    # refracted world, inverted, faint: a small horizon seen through the glass
    cid = _clip(k, k.poly(face)); start = len(k.ink)
    for i in range(10):
        p0, p1 = c.p((0.1, 0.1 - i * 0.07, -0.74)), c.p((0.1, 0.1 - i * 0.07 + 0.08, 0.74))
        k.line(f'M{p0[0]:.1f},{p0[1]:.1f} L{p1[0]:.1f},{p1[1]:.1f}', 0.4, 0.5, rough=False)
    _wrap(k, start, f'clip-path="url(#{cid})"')
    g = [c.p((0.1, math.sin(q) * 0.6, math.cos(q) * 0.6)) for q in [-2.4 + i * 0.08 for i in range(10)]]
    _thin(k, k.poly(g, False), 2.0)
    _thin(k, k.poly(face), 1.0)
    for i in range(16):     # rivets on the mount
        q = i / 16 * TAU
        p = c.p((0.1, math.sin(q) * 0.78, math.cos(q) * 0.78))
        k.ink.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{max(1, s * 0.01):.1f}" fill="#fff" stroke="#000" stroke-width=".6"/>')
    k.ink.append(f'<circle cx="{focus[0]:.1f}" cy="{focus[1]:.1f}" r="{max(2, s * 0.025):.1f}" fill="#fff" stroke="#000" stroke-width="1"/>')
    _rays(k, focus[0], focus[1], s * 0.04, s * 0.15, 12, 0.6, 0.8)
    _wash(k, spec, x, y, s * 0.7, s * 0.7, 0, 0.35)
    _wash(k, spec, focus[0], focus[1], s * 0.25, s * 0.2, 1, 0.5)


# ---------------- worlds and sky ----------------
def _globe(k, x, y, R, spec, tone_dark=4, lines=True):
    """A sphere: knocked out, curved contour rules heavier toward the night side, terminator cross-hatch."""
    d = _oval(x, y, R, R)
    k.paper(d)
    cid = _clip(k, d); start = len(k.ink)
    lx, ly = -0.62, -0.62
    # contour rules: ellipse arcs around the light axis, weight by darkness
    N = max(18, int(R / 3.6))
    segs = []
    for i in range(N):
        t = (i + 0.5) / N * 2 - 1                       # -1 lit pole .. +1 dark pole along the light axis
        rr = math.sqrt(max(0.0, 1 - t * t)) * R
        cxp, cyp = x - lx * t * R * 0.98, y - ly * t * R * 0.98
        dark = (t + 1) / 2
        wd = 0.15 + 2.8 * max(0.0, dark - 0.12) ** 1.3
        if dark < 0.14: continue
        ang = math.degrees(math.atan2(ly, lx)) + 90
        segs.append(f'<ellipse cx="{cxp:.1f}" cy="{cyp:.1f}" rx="{rr:.1f}" ry="{rr * 0.32:.1f}" transform="rotate({ang:.1f} {cxp:.1f} {cyp:.1f})" fill="none" stroke="#000" stroke-width="{wd:.2f}"/>')
    k.ink.append('<g>' + ''.join(segs) + '</g>')
    # night side: a crescent between the shadowed limb and the terminator, cross-ruled
    sd = (0.7071, 0.7071); pp = (0.7071, -0.7071)
    limb = [(x + R * math.cos(t), y + R * math.sin(t)) for t in [math.radians(-45 + i * 9) for i in range(21)]]
    term = [(x + R * math.cos(t) * pp[0] + R * 0.38 * math.sin(t) * sd[0], y + R * math.cos(t) * pp[1] + R * 0.38 * math.sin(t) * sd[1]) for t in [math.pi - i * math.pi / 20 for i in range(21)]]
    if tone_dark >= 4: _ruled_path(k, k.poly(limb + term), 4, 75)
    return d, cid, start

def planet(k, x, y, s, spec=None):
    """A jungle world: engraved sphere with continents in leaf texture, cloud bands, a thin bright limb."""
    k.depth = 0.95
    R = s * 0.95
    k.ink.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R * 1.05:.1f}" fill="#fff"/>')
    d, cid, start = _globe(k, x, y, R, spec)
    # continents: irregular blobs, hatched and leaf-marked
    for i in range(5):
        a = i / 5 * TAU + k.r.uniform(-0.4, 0.4); rr = R * k.r.uniform(0.3, 0.75)
        cx, cy = x + math.cos(a) * rr, y + math.sin(a) * rr
        sz = R * k.r.uniform(0.2, 0.36)
        fore = 1 - (rr / R) ** 2
        blob = k.blob(cx, cy, sz * (0.6 + 0.4 * fore), sz * 0.7, n=16, jitter=0.35)
        k.shape(blob, tone=2, dark=4, angle=k.r.uniform(10, 80), outline=0.8)
        k.leafmarks(cx - sz * 0.6, cx + sz * 0.6, cy - sz * 0.4, cy + sz * 0.4, int(sz / 3))
    # cloud swirls: white curls over the lit hemisphere
    cl = []
    for i in range(9):
        a = k.r.uniform(math.pi * 0.9, math.pi * 1.8); rr = R * k.r.uniform(0.2, 0.85)
        cx, cy = x + math.cos(a) * rr, y + math.sin(a) * rr
        L = R * k.r.uniform(0.15, 0.4)
        cl.append(f'M{cx:.1f},{cy:.1f} q{L * 0.5:.1f},{-L * 0.15:.1f} {L:.1f},{L * 0.05:.1f} t{L * 0.6:.1f},{L * 0.1:.1f}')
    _white(k, ' '.join(cl), max(1.6, R * 0.02))
    _wrap(k, start, f'clip-path="url(#{cid})"')
    k.ink.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R:.1f}" fill="none" stroke="#000" stroke-width="{max(1.2, R * 0.006):.1f}"/>')
    # atmosphere: a fine halo ring on the lit limb
    k.ink.append(f'<path d="M{x - R * 1.04 * math.cos(0.3):.1f},{y + R * 1.04 * math.sin(0.3):.1f} A{R * 1.04:.1f},{R * 1.04:.1f} 0 0,1 {x + R * 1.04 * math.sin(0.4):.1f},{y - R * 1.04 * math.cos(0.4):.1f}" fill="none" stroke="#000" stroke-width="0.6" stroke-opacity=".6"/>')
    _wash(k, spec, x - R * 0.2, y - R * 0.2, R * 0.75, R * 0.75, 0, 0.55)
    _wash(k, spec, x + R * 0.3, y + R * 0.2, R * 0.5, R * 0.5, 1, 0.35)

def moon(k, x, y, s, spec=None):
    """A frozen moon: pale sphere, foreshortened craters, ice fractures in white and black."""
    k.depth = 0.95
    R = s * 0.8
    k.ink.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R * 1.03:.1f}" fill="#fff"/>')
    d, cid, start = _globe(k, x, y, R, spec)
    for i in range(int(10 + R / 12)):
        a = k.r.uniform(0, TAU); rr = R * math.sqrt(k.r.random()) * 0.92
        cx, cy = x + math.cos(a) * rr, y + math.sin(a) * rr
        cr = R * k.r.uniform(0.03, 0.12)
        fs = math.sqrt(max(0.15, 1 - (rr / R) ** 2))
        ang = math.degrees(a)
        k.ink.append(f'<g transform="rotate({ang:.1f} {cx:.1f} {cy:.1f})"><ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{cr * fs:.1f}" ry="{cr:.1f}" fill="#fff" stroke="#000" stroke-width="0.8"/>'
                     f'<path d="M{cx - cr * fs * 0.2:.1f},{cy - cr * 0.9:.1f} A{cr * fs:.1f},{cr:.1f} 0 0,0 {cx - cr * fs * 0.2:.1f},{cy + cr * 0.9:.1f}" fill="none" stroke="#000" stroke-width="{max(1.0, cr * 0.18):.1f}"/></g>')
    cr_ = []
    for i in range(6):
        px, py = x + k.r.uniform(-0.6, 0.4) * R, y + k.r.uniform(-0.6, 0.4) * R
        pts = [(px, py)]
        for j in range(5):
            px += k.r.uniform(-0.12, 0.2) * R; py += k.r.uniform(-0.08, 0.12) * R; pts.append((px, py))
        cr_.append(k.poly(pts, False))
    _thin(k, ' '.join(cr_), 0.7)
    _wrap(k, start, f'clip-path="url(#{cid})"')
    k.ink.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R:.1f}" fill="none" stroke="#000" stroke-width="{max(1.0, R * 0.006):.1f}"/>')
    _wash(k, spec, x - R * 0.2, y - R * 0.2, R * 0.7, R * 0.7, 1, 0.45)

def gas_giant(k, x, y, s, spec=None):
    """A banded gas giant with a storm eye and a tilted ring system passing behind and in front."""
    k.depth = 0.95
    R = s * 0.85
    tilt = -16
    ring = lambda rr, a0, a1: f'<path d="M{x + rr * math.cos(a0):.1f},{y + rr * 0.24 * math.sin(a0):.1f} A{rr:.1f},{rr * 0.24:.1f} 0 0,{1 if a1 > a0 else 0} {x + rr * math.cos(a1):.1f},{y + rr * 0.24 * math.sin(a1):.1f}" fill="none" stroke="#000" '
    def rings(back):
        a0, a1 = (math.pi, TAU) if back else (0, math.pi)
        g = []
        for i, rr in enumerate([R * (1.3 + 0.045 * j) for j in range(12)]):
            if i in (4, 5): continue
            g.append(ring(rr, a0, a1) + f'stroke-width="{0.5 + 0.9 * ((i * 7) % 3 == 0)}"/>')
        k.ink.append(f'<g transform="rotate({tilt} {x:.1f} {y:.1f})">' + ''.join(g) + '</g>')
    rings(True)
    k.ink.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R:.1f}" fill="#fff"/>')
    d, cid, start = _globe(k, x, y, R, spec)
    # bands: curved stripes of differing tone across the disc
    g = [f'<g transform="rotate({tilt} {x:.1f} {y:.1f})">']
    for i in range(9):
        yy = -0.8 + i * 0.2 + k.r.uniform(-0.03, 0.03)
        hh = R * k.r.uniform(0.04, 0.09)
        bow = R * 0.12
        pts = []
        for j in range(21):
            t = -1 + j / 10
            pts.append((x + t * R, y + yy * R + bow * (1 - t * t) * yy))
        top = k.poly(pts, False)
        g.append(f'<path d="{top}" fill="none" stroke="#000" stroke-width="{hh * (0.25 if i % 2 else 0.6):.1f}" stroke-opacity="{0.55 if i % 2 else 0.85}"/>')
        wv = ' '.join(f'M{x + t * R:.1f},{y + yy * R + bow * (1 - t * t) * yy + hh:.1f} q{R * 0.03:.1f},{-hh * 0.6:.1f} {R * 0.06:.1f},0' for t in [k.r.uniform(-1, 1) for _ in range(8)])
        g.append(f'<path d="{wv}" fill="none" stroke="#000" stroke-width="0.6"/>')
    g.append('</g>')
    k.ink.append(''.join(g))
    sx, sy = x + R * 0.25, y + R * 0.3
    k.ink.append(f'<g transform="rotate({tilt} {sx:.1f} {sy:.1f})"><ellipse cx="{sx:.1f}" cy="{sy:.1f}" rx="{R * 0.15:.1f}" ry="{R * 0.07:.1f}" fill="#fff" stroke="#000" stroke-width="1.2"/>'
                 f'<ellipse cx="{sx:.1f}" cy="{sy:.1f}" rx="{R * 0.09:.1f}" ry="{R * 0.04:.1f}" fill="none" stroke="#000" stroke-width="0.8"/><ellipse cx="{sx:.1f}" cy="{sy:.1f}" rx="{R * 0.04:.1f}" ry="{R * 0.018:.1f}" fill="#000"/></g>')
    _wrap(k, start, f'clip-path="url(#{cid})"')
    k.ink.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{R:.1f}" fill="none" stroke="#000" stroke-width="1.2"/>')
    # ring shadow on the globe, then the front rings
    k.ink.append(f'<g transform="rotate({tilt} {x:.1f} {y:.1f})"><path d="M{x - R * 0.97:.1f},{y + R * 0.12:.1f} Q{x:.1f},{y + R * 0.42:.1f} {x + R * 0.97:.1f},{y + R * 0.12:.1f}" fill="none" stroke="#000" stroke-width="{R * 0.04:.1f}" stroke-opacity=".7"/></g>')
    k.ink.append(f'<g transform="rotate({tilt} {x:.1f} {y:.1f})"><path d="M{x - R * 1.84:.1f},{y:.1f} A{R * 1.84:.1f},{R * 0.44:.1f} 0 0,0 {x + R * 1.84:.1f},{y:.1f} L{x + R * 1.28:.1f},{y:.1f} A{R * 1.28:.1f},{R * 0.31:.1f} 0 0,1 {x - R * 1.28:.1f},{y:.1f}Z" fill="#fff"/></g>')
    rings(False)
    _wash(k, spec, x, y, R * 0.8, R * 0.8, 1, 0.45)
    _wash(k, spec, x - R * 0.3, y - R * 0.3, R * 1.2, R * 0.4, 0, 0.3)

def _star(k, x, y, r, rays=4, white_halo=True):
    """An engraved star: a small white halo (so it reads on dark hatching) and tapering cross rays."""
    if white_halo: k.ink.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 0.9:.1f}" fill="#fff"/>')
    pts = []
    for i in range(rays * 2):
        a = i / (rays * 2) * TAU - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.16
        if rays > 4 and i % 4 == 2: rr = r * 0.6
        pts.append((x + math.cos(a) * rr, y + math.sin(a) * rr))
    k.solid(k.poly(pts))

def stars(k, x, y, s, spec=None):
    """A field of stars spread around (x, y): pinpricks, crossed sparks, and a few bright stars with rings."""
    k.depth = 0.9
    dots = []
    for i in range(int(90 + s * 0.3)):
        rr = 2.0 * s * math.sqrt(k.r.random()); a = k.r.uniform(0, TAU)
        dots.append((x + math.cos(a) * rr, y + math.sin(a) * rr * 0.75))
    k.ink.append('<g fill="#fff">' + ''.join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{k.r.uniform(1.4, 2.6):.1f}"/>' for px, py in dots) + '</g>')
    k.ink.append('<g fill="#000">' + ''.join(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{k.r.uniform(0.5, 1.2):.1f}"/>' for px, py in dots) + '</g>')
    for i in range(int(16 + s * 0.08)):
        rr = 2.0 * s * math.sqrt(k.r.random()); a = k.r.uniform(0, TAU)
        _star(k, x + math.cos(a) * rr, y + math.sin(a) * rr * 0.75, k.r.uniform(3, 7) * (1 + s / 250))
    for i in range(3):
        rr = 1.6 * s * math.sqrt(k.r.random()); a = k.r.uniform(0, TAU)
        px, py = x + math.cos(a) * rr, y + math.sin(a) * rr * 0.75
        R = k.r.uniform(10, 18) * (1 + s / 400)
        k.ink.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{R * 0.5:.1f}" fill="#fff" stroke="#000" stroke-width="0.5"/>')
        _star(k, px, py, R, rays=8, white_halo=False)
        _wash(k, spec, px, py, R * 2, R * 2, i, 0.5, 2)
    _wash(k, spec, x, y, s * 1.6, s * 0.8, 1, 0.2)

def signal_waves(k, x, y, s, spec=None):
    """A signal going out: a small mast and dish at lower left, concentric broken arcs spreading up and right."""
    k.depth = 0.95
    ox, oy = x - s * 0.9, y + s * 0.7
    # mast and dish
    k.shape(k.poly([(ox - s * 0.06, oy + s * 0.3), (ox - s * 0.015, oy), (ox + s * 0.015, oy), (ox + s * 0.06, oy + s * 0.3)]), tone=2, dark=4, angle=80, outline=0.9, rough=False)
    for i in range(4):
        yy = oy + s * (0.06 + i * 0.07)
        _thin(k, f'M{ox - s * (0.02 + i * 0.01):.1f},{yy:.1f} L{ox + s * (0.02 + i * 0.01):.1f},{yy + s * 0.07:.1f} M{ox + s * (0.02 + i * 0.01):.1f},{yy:.1f} L{ox - s * (0.02 + i * 0.01):.1f},{yy + s * 0.07:.1f}', 0.6)
    dish = k.smooth([(ox - s * 0.16, oy - s * 0.12), (ox + s * 0.05, oy + s * 0.04), (ox + s * 0.16, oy - s * 0.08), (ox, oy - s * 0.05)])
    k.shape(dish, tone=2, dark=4, angle=20, outline=1.0, rough=False)
    _thin(k, f'M{ox:.1f},{oy - s * 0.05:.1f} L{ox + s * 0.1:.1f},{oy - s * 0.2:.1f}', 1.0)
    src_ = (ox + s * 0.1, oy - s * 0.2)
    k.ink.append(f'<circle cx="{src_[0]:.1f}" cy="{src_[1]:.1f}" r="{max(2, s * 0.02):.1f}" fill="#000"/>')
    # arcs: triple-ruled, broken into dashes, thinning outward
    a0, a1 = math.radians(-100), math.radians(10)
    for i in range(9):
        rr = s * (0.25 + i * 0.25)
        fade = 1 - i / 10
        for j in range(3 if i < 6 else 2):
            r2 = rr + j * s * 0.025
            dash = max(4, rr * 0.25)
            k.ink.append(f'<path d="M{src_[0] + r2 * math.cos(a0):.1f},{src_[1] + r2 * math.sin(a0):.1f} A{r2:.1f},{r2:.1f} 0 0,1 {src_[0] + r2 * math.cos(a1):.1f},{src_[1] + r2 * math.sin(a1):.1f}" '
                         f'fill="none" stroke="#000" stroke-width="{(1.6 - j * 0.5) * fade + 0.2:.2f}" stroke-dasharray="{dash:.1f} {dash * (0.15 + i * 0.06):.1f}" stroke-dashoffset="{k.r.uniform(0, dash):.1f}" stroke-linecap="round"/>')
    _wash(k, spec, x, y - s * 0.1, s * 1.3, s * 0.9, 0, 0.3)
    _wash(k, spec, src_[0], src_[1], s * 0.3, s * 0.3, 1, 0.45)

def streak(k, x, y, s, spec=None):
    """A burning object falling: a white-hot head, a long tapering trail of ruled fire, smoke billows and sparks."""
    k.depth = 0.95
    hx, hy = x + s * 0.7, y + s * 0.6
    tx, ty = x - s * 1.8, y - s * 1.4
    ang = math.atan2(ty - hy, tx - hx); L = math.hypot(tx - hx, ty - hy)
    ca, sa = math.cos(ang), math.sin(ang); nx, ny = -sa, ca
    # smoke along the upper part of the trail
    for i in range(7):
        t = 0.35 + i * 0.1
        bx_, by_ = hx + ca * L * t + nx * s * k.r.uniform(-0.05, 0.12), hy + sa * L * t + ny * s * k.r.uniform(-0.05, 0.12)
        _billow(k, bx_, by_, s * (0.08 + 0.12 * t), 5, tone=1, dark=3, angle=40 + i * 11)
    # trail: many fine lines converging on the head, wider toward the tail
    trail = k.poly([(hx + nx * s * 0.07, hy + ny * s * 0.07), (tx + nx * s * 0.25, ty + ny * s * 0.25), (tx - nx * s * 0.25, ty - ny * s * 0.25), (hx - nx * s * 0.07, hy - ny * s * 0.07)])
    k.paper(trail)
    ln = []
    for i in range(22):
        f = -1 + 2 * i / 21
        Lf = L * (0.45 + 0.55 * (1 - abs(f)) * k.r.uniform(0.6, 1.0))
        ln.append(f'M{hx + nx * f * s * 0.06:.1f},{hy + ny * f * s * 0.06:.1f} L{hx + ca * Lf + nx * f * s * 0.25 * Lf / L:.1f},{hy + sa * Lf + ny * f * s * 0.25 * Lf / L:.1f}')
    k.line(' '.join(ln), 0.8, 0.95, rough=False)
    # head: bright core in a dark flaring rim
    fl = k.smooth([(hx + ca * s * 0.5 + nx * s * 0.12, hy + sa * s * 0.5 + ny * s * 0.12), (hx - ca * s * 0.08 + nx * s * 0.1, hy - sa * s * 0.08 + ny * s * 0.1),
                   (hx - ca * s * 0.14, hy - sa * s * 0.14), (hx - ca * s * 0.08 - nx * s * 0.1, hy - sa * s * 0.08 - ny * s * 0.1),
                   (hx + ca * s * 0.5 - nx * s * 0.12, hy + sa * s * 0.5 - ny * s * 0.12), (hx + ca * s * 0.7, hy + sa * s * 0.7)])
    k.shape(fl, tone=3, dark=4, angle=math.degrees(ang) + 90, outline=1.0)
    k.ink.append(f'<circle cx="{hx:.1f}" cy="{hy:.1f}" r="{s * 0.075:.1f}" fill="#fff" stroke="#000" stroke-width="1.2"/>')
    _rays(k, hx, hy, s * 0.1, s * 0.35, 16, 0.6, 0.7)
    sp = [(hx + ca * L * k.r.uniform(0.05, 0.5) + nx * s * k.r.uniform(-0.35, 0.35), hy + sa * L * k.r.uniform(0.05, 0.5) + ny * s * k.r.uniform(-0.35, 0.35)) for _ in range(18)]
    for px, py in sp:
        k.line(f'M{px:.1f},{py:.1f} l{ca * s * 0.06:.1f},{sa * s * 0.06:.1f}', 0.9, rough=False)
    _wash(k, spec, hx, hy, s * 0.35, s * 0.35, 1, 0.6)
    _wash(k, spec, (hx + tx) / 2, (hy + ty) / 2, s * 0.9, s * 0.4, 0, 0.3)

def explosion(k, x, y, s, spec=None):
    """A burst: white core, ruled radiating lines, rolling smoke lobes on the rim, flying shards with trails."""
    k.depth = 0.95
    _rays(k, x, y, s * 0.35, s * 1.9, 70, 0.6, 0.6)
    for i in range(10):
        a = i / 10 * TAU + k.r.uniform(-0.2, 0.2); rr = s * k.r.uniform(0.6, 0.85)
        _billow(k, x + math.cos(a) * rr, y + math.sin(a) * rr * 0.85, s * k.r.uniform(0.3, 0.45), 7, tone=1, dark=3, angle=math.degrees(a))
    core = k.blob(x, y, s * 0.55, s * 0.5, n=22, jitter=0.12)
    k.paper(core)
    k.line(core, 0.8, 0.7)
    _rays(k, x, y, s * 0.12, s * 0.5, 40, 0.4, 0.5)
    k.ink.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{s * 0.1:.1f}" fill="#fff"/>')
    for i in range(14):
        a = k.r.uniform(0, TAU); rr = s * k.r.uniform(1.0, 1.7)
        px, py = x + math.cos(a) * rr, y + math.sin(a) * rr
        r = s * k.r.uniform(0.03, 0.07)
        shard = [(px + math.cos(b) * r * k.r.uniform(0.4, 1.3), py + math.sin(b) * r * k.r.uniform(0.4, 1.3)) for b in [j / 4 * TAU + k.r.uniform(0, 0.8) for j in range(4)]]
        k.solid(k.poly(shard))
        k.line(f'M{px:.1f},{py:.1f} L{px - math.cos(a) * s * 0.3:.1f},{py - math.sin(a) * s * 0.3:.1f}', 0.5, 0.7, rough=False)
    _wash(k, spec, x, y, s * 0.7, s * 0.7, 1, 0.6)
    _wash(k, spec, x, y, s * 1.3, s * 1.1, 0, 0.3)

def fire(k, x, y, s, spec=None):
    """A campfire: crossed logs, tongues of flame with inner flame lines, sparks and a curl of smoke."""
    k.depth = 0.95
    gy = y + s * 0.65
    _rays(k, x, y, s * 0.6, s * 1.6, 40, 0.45, 0.3, -math.pi, 0)
    # smoke curling up
    for i in range(5):
        _billow(k, x + s * (0.1 + i * 0.08) + k.r.uniform(-0.05, 0.05) * s, y - s * (0.75 + i * 0.25), s * (0.08 + i * 0.04), 5, tone=1, dark=2, angle=30 + i * 20)
    # flames: swaying tongues that curl at the tip, nested inner flame lines
    tongues = [(-0.3, 0.6, 0.18), (-0.12, 1.0, 0.2), (0.06, 1.3, 0.22), (0.22, 0.9, 0.19), (0.36, 0.55, 0.15)]
    for dx, hgt, wd in tongues:
        bx_ = x + dx * s; h_ = hgt * s; A = s * k.r.uniform(0.08, 0.16) * k.r.choice((-1, 1)); ph = k.r.uniform(0, 1)
        def cl(t): return (bx_ + A * math.sin(ph + t * 3.2) * t, gy - t * h_)
        def hw(t): return wd * s * (1 - t) ** 0.75 * (1 + 0.25 * math.sin(t * 7 + ph))
        ts = [i / 14 for i in range(15)]
        left = [(cl(t)[0] - hw(t), cl(t)[1]) for t in ts]; right = [(cl(t)[0] + hw(t), cl(t)[1]) for t in ts[::-1]]
        tongue = k.smooth(left[:-1] + [cl(1.0)] + right[1:])
        k.paper(tongue); k.line(tongue, 1.1)
        for f in (0.55, -0.45, 0.15):
            pts = [(cl(t)[0] + f * hw(t), cl(t)[1]) for t in [0.05 + i * 0.06 for i in range(int(8 + 4 * (1 - abs(f))))]]
            k.line(k.smooth(pts, close=False), 0.55, 0.75)
    # sparks
    sp = []
    for i in range(20):
        px, py = x + k.r.uniform(-0.6, 0.6) * s, gy - s * k.r.uniform(1.0, 2.0)
        sp.append(f'M{px:.1f},{py:.1f} l{k.r.uniform(-3, 3):.1f},{-k.r.uniform(3, 8):.1f}')
    k.line(' '.join(sp), 0.9, rough=False)
    # logs: crossed, ruled bark, cut ends with rings
    for a, ln in ((0.35, 1.3), (-0.4, 1.25), (0.05, 1.0)):
        ca, sa = math.cos(a), math.sin(a)
        p0, p1 = (x - ca * s * ln * 0.5, gy + s * 0.08 - sa * s * ln * 0.5 * 0.4), (x + ca * s * ln * 0.5, gy + s * 0.08 + sa * s * ln * 0.5 * 0.4)
        k.shape(tapered(k, [p0, _lerp(p0, p1, 0.5), p1], s * 0.08, s * 0.07), tone=2, dark=4, angle=math.degrees(math.atan2(p1[1] - p0[1], p1[0] - p0[0])) + 90, outline=1.0)
        k.shape(_oval(p1[0], p1[1], s * 0.04, s * 0.075), tone=1, dark=2, angle=0, outline=0.9)
        k.ink.append(f'<ellipse cx="{p1[0]:.1f}" cy="{p1[1]:.1f}" rx="{s * 0.02:.1f}" ry="{s * 0.04:.1f}" fill="none" stroke="#000" stroke-width=".6"/>')
    # ring of stones
    for i in range(9):
        a = math.pi * (0.05 + i * 0.11)
        px, py = x + math.cos(a) * s * 0.75, gy + s * 0.08 + math.sin(a) * s * 0.2
        k.shape(_oblob(k, px, py, s * 0.09, s * 0.06, 0, 10, 0.12), tone=2, dark=4, angle=30, outline=0.9)
    _wash(k, spec, x, y + s * 0.1, s * 0.75, s * 0.8, 1, 0.6)
    _wash(k, spec, x, gy, s * 1.3, s * 0.4, 0, 0.3)


# ---------------- growing and floating things ----------------
def balloon(k, x, y, s, spec=None):
    """A gas balloon (or silk airship envelope): ruled gores swelling to a crown, netting, cords to a gondola."""
    k.depth = 0.95
    R = s * 0.7; cx, cy = x, y - s * 0.35
    # envelope outline: round crown narrowing to a neck
    def env(t):           # t in [-1, 1] across, returns (x at equator scale)
        return t
    prof = []             # profile half-width by height h in [0 (neck) .. 1 (crown)]
    for i in range(25):
        h = i / 24
        wdt = math.sin(min(1, h * 1.25) * math.pi * 0.62) ** 0.8 if h < 0.8 else math.sqrt(max(0, 1 - ((h - 0.8) / 0.2) ** 2 * 0.0)) * 1.0
        ang = h * math.pi
        wdt = (0.18 + 0.82 * math.sin(h * math.pi * 0.5 + 0.0) ** 0.6) * math.sqrt(max(0.0, 1 - max(0, (h - 0.62) / 0.38) ** 2))
        prof.append((h, wdt))
    top = cy - R * 1.0; neck = cy + R * 1.05
    yof = lambda h: neck - (neck - top) * h
    outline = [(cx + R * w_, yof(h)) for h, w_ in prof] + [(cx - R * w_, yof(h)) for h, w_ in prof[::-1]]
    d = k.smooth(outline)
    k.shape(d, tone=1, dark=3, angle=70, outline=1.3)
    cid = _clip(k, d); start = len(k.ink)
    # gores: meridians bowing with the profile; shade lines denser toward the right
    for g in range(-6, 7):
        f = g / 6.5
        pts = [(cx + R * w_ * math.sin(f * math.pi / 2), yof(h)) for h, w_ in prof]
        k.line(k.smooth(pts, close=False), 1.0 if g % 2 == 0 else 0.6, 0.9)
        if f > 0.1:
            for j in range(3):
                ff = f + j * 0.025
                pts = [(cx + R * w_ * math.sin(min(ff, 1) * math.pi / 2), yof(h)) for h, w_ in prof]
                k.line(k.smooth(pts, close=False), 0.45 + f * 0.6, 0.8, rough=False)
    # latitude seams
    for h in (0.35, 0.6, 0.82):
        w_ = dict(prof).get(h, None) or [w for hh, w in prof if abs(hh - h) < 0.03][0]
        k.line(f'M{cx - R * w_:.1f},{yof(h):.1f} Q{cx:.1f},{yof(h) + R * 0.12:.1f} {cx + R * w_:.1f},{yof(h):.1f}', 0.8)
    _white(k, f'M{cx - R * 0.55:.1f},{cy - R * 0.2:.1f} Q{cx - R * 0.5:.1f},{cy - R * 0.7:.1f} {cx - R * 0.1:.1f},{cy - R * 0.85:.1f}', max(1.5, R * 0.025))
    _wrap(k, start, f'clip-path="url(#{cid})"')
    # cords to the gondola
    gy = neck + s * 0.5; gw = s * 0.2
    for i in range(7):
        f = -1 + 2 * i / 6
        k.line(f'M{cx + R * 0.18 * f:.1f},{neck - 2:.1f} L{cx + gw * 0.9 * f:.1f},{gy:.1f}', 0.6, rough=False)
    k.shape(k.smooth([(cx - R * 0.2, neck - 6), (cx + R * 0.2, neck - 6), (cx + R * 0.16, neck + 6), (cx - R * 0.16, neck + 6)]), tone=2, dark=4, angle=0, outline=0.9)
    gond = k.poly([(cx - gw, gy), (cx + gw, gy), (cx + gw * 0.85, gy + s * 0.18), (cx - gw * 0.85, gy + s * 0.18)])
    k.shape(gond, tone=2, dark=4, angle=80, outline=1.1)
    wick = ' '.join(f'M{cx - gw + i * gw / 5:.1f},{gy:.1f} l{gw * 0.02:.1f},{s * 0.18:.1f}' for i in range(1, 10))
    k.line(wick, 0.5)
    k.line(f'M{cx - gw:.1f},{gy + s * 0.05:.1f} L{cx + gw:.1f},{gy + s * 0.05:.1f}', 0.9)
    _wash(k, spec, cx, cy, R * 0.9, R * 0.95, 1, 0.45)

def _lobed(k, cx, cy, rx, ry, n=10):
    """Cauliflower outline: a ring of outward-bulging arcs (engraved foliage / cloud edge)."""
    pts = []
    for i in range(n):
        t = i / n * TAU + k.r.uniform(-0.1, 0.1); f = k.r.uniform(0.85, 1.08)
        pts.append((cx + math.cos(t) * rx * f, cy + math.sin(t) * ry * f))
    d = f'M{pts[0][0]:.1f},{pts[0][1]:.1f}'
    for i in range(n):
        x1, y1 = pts[(i + 1) % n]
        ch = math.dist(pts[i], (x1, y1))
        d += f' A{ch * 0.58:.1f},{ch * 0.58:.1f} 0 0,1 {x1:.1f},{y1:.1f}'
    return d + 'Z'

def tree(k, x, y, s, spec=None):
    """A giant jungle tree: buttressed trunk, layered crown of leaf masses, hanging lianas."""
    k.depth = 0.95
    gy = y + s * 1.25
    # buttress roots and trunk
    tw = s * 0.2
    trunk = k.smooth([(x - tw * 3.2, gy), (x - tw * 1.2, gy - s * 0.18), (x - tw * 0.8, gy - s * 0.6), (x - tw * 0.7, y - s * 0.4),
                      (x + tw * 0.7, y - s * 0.4), (x + tw * 0.8, gy - s * 0.6), (x + tw * 1.3, gy - s * 0.15), (x + tw * 3.4, gy), (x, gy + s * 0.03)])
    k.shape(trunk, tone=2, dark=4, angle=84, outline=1.2)
    for i in range(9):
        t = k.r.uniform(-0.6, 0.6)
        y0 = k.r.uniform(y - s * 0.3, gy - s * 0.3)
        k.line(f'M{x + tw * t:.1f},{y0:.1f} q{k.r.uniform(-4, 4):.1f},{s * 0.2:.1f} {k.r.uniform(-3, 3):.1f},{s * k.r.uniform(0.2, 0.45):.1f}', 0.8, 0.8)
    for sgn in (-1, 1):
        k.line(f'M{x + sgn * tw * 0.9:.1f},{gy - s * 0.4:.1f} Q{x + sgn * tw * 1.4:.1f},{gy - s * 0.1:.1f} {x + sgn * tw * 2.8:.1f},{gy:.1f}', 1.0)
    # crown: broad cauliflower masses (scalloped arcs), shadowed beneath, dense leaf texture
    masses = []
    for i in range(9):
        f = -1 + 2 * (i + 0.5) / 9
        masses.append((x + f * s * 1.05 + k.r.uniform(-0.05, 0.05) * s, y - s * (0.7 - 0.35 * f * f) + k.r.uniform(-0.08, 0.08) * s, s * k.r.uniform(0.32, 0.42)))
    masses += [(x + k.r.uniform(-0.5, 0.5) * s, y - s * k.r.uniform(0.95, 1.1), s * 0.38) for _ in range(3)]
    masses.sort(key=lambda m: m[1])
    for mx, my, mr in masses:
        d = _lobed(k, mx, my, mr, mr * 0.7, 11)
        k.shape(d, tone=1, dark=4, angle=k.r.uniform(25, 60), outline=1.0)
        k.leafmarks(mx - mr * 0.8, mx + mr * 0.8, my - mr * 0.5, my + mr * 0.4, int(mr / 1.6))
        k.line(f'M{mx - mr * 0.7:.1f},{my + mr * 0.35:.1f} Q{mx:.1f},{my + mr * 0.62:.1f} {mx + mr * 0.8:.1f},{my + mr * 0.3:.1f}', 0.7, 0.8)
    # lianas hanging from the crown
    for i in range(5):
        lx = x + k.r.uniform(-1.0, 1.0) * s; ly = y - s * 0.2
        L = s * k.r.uniform(0.4, 0.9)
        pts = [(lx + math.sin(j * 0.9 + i) * s * 0.02, ly + L * j / 8) for j in range(9)]
        k.line(k.smooth(pts, close=False), 0.9)
        for j in range(2, 9, 2):
            px, py = pts[j]
            k.shape(k.smooth([(px, py), (px + s * 0.04, py + s * 0.015), (px + s * 0.06, py + s * 0.045), (px + s * 0.02, py + s * 0.04)]), tone=1, dark=3, outline=0.6)
    _wash(k, spec, x, y - s * 0.6, s * 1.1, s * 0.6, 0, 0.45)
    _wash(k, spec, x, gy - s * 0.3, s * 0.4, s * 0.5, 1, 0.3)

def crystal_spire(k, x, y, s, spec=None):
    """A cluster of faceted crystal spires: a tall central prism with leaning companions, lit and shadowed facets."""
    k.depth = 0.95
    gy = y + s * 1.0
    def prism(bx, by, h, w, lean):
        tip = (bx + lean * h, by - h)
        shoulder = 0.8
        L = [(bx - w, by), (bx - w * 0.92 + lean * h * shoulder, by - h * shoulder)]
        M = [(bx - w * 0.15, by + w * 0.18), (bx - w * 0.12 + lean * h * shoulder, by - h * shoulder + w * 0.12)]
        Rr = [(bx + w, by), (bx + w * 0.92 + lean * h * shoulder, by - h * shoulder)]
        faces = [([L[0], M[0], M[1], L[1]], 0, 70), ([M[0], Rr[0], Rr[1], M[1]], 3, 100),
                 ([L[1], M[1], tip], 1, 40), ([M[1], Rr[1], tip], 4, 120)]
        for pts, t, ang in faces:
            _ruled(k, pts, t, ang + math.degrees(lean), 1.0)
        # glints: white sparkle strokes along the lit edge
        _white(k, f'M{L[0][0] + w * 0.25:.1f},{L[0][1] - h * 0.1:.1f} L{L[1][0] + w * 0.22:.1f},{L[1][1] + h * 0.15:.1f}', max(1.0, w * 0.06))
        return tip
    spires = [(-0.55, 0.9, 0.12, -0.18), (0.45, 1.1, 0.14, 0.2), (0.75, 0.6, 0.09, 0.35), (-0.85, 0.5, 0.08, -0.3), (0.0, 2.0, 0.2, 0.03), (-0.25, 0.8, 0.1, -0.1), (0.25, 0.7, 0.09, 0.12)]
    for dx, h, w, lean in spires:
        tip = prism(x + dx * s, gy + abs(dx) * s * 0.05, h * s, w * s, lean)
        if h > 1.5:
            _rays(k, tip[0], tip[1], s * 0.04, s * 0.3, 12, 0.6, 0.8)
    # rubble at the base
    for i in range(12):
        px = x + k.r.uniform(-1.1, 1.1) * s; py = gy + k.r.uniform(0.0, 0.1) * s; r = s * k.r.uniform(0.03, 0.07)
        _ruled(k, [(px - r, py), (px - r * 0.3, py - r), (px + r, py - r * 0.4), (px + r * 0.6, py + r * 0.3)], k.choice((1, 3)) if hasattr(k, 'choice') else k.r.choice((1, 3)), 45, 0.8)
    _wash(k, spec, x, y, s * 0.6, s * 1.1, 0, 0.45)
    _wash(k, spec, x + s * 0.2, y + s * 0.5, s * 0.6, s * 0.4, 1, 0.3)

def elevator_thread(k, x, y, s, spec=None):
    """A space-elevator thread: twin braided cables rising off the top of the frame, a climber car clamped on,
    tether nodes, and an anchor below."""
    k.depth = 0.95
    top = -20
    bot = y + s * 1.6
    lean = s * 0.12
    X = lambda yy: x + lean * (yy - y) / (bot - top)
    for off in (-1, 1):
        pts = [(X(yy) + off * s * 0.02 * (0.4 + 0.6 * (yy - top) / (bot - top)), yy) for yy in [top + (bot - top) * i / 20 for i in range(21)]]
        k.line(k.poly(pts, False), 1.2, rough=False)
    # braid: crossing fine helix ticks
    yy = top
    tk = []
    while yy < bot:
        wd = s * 0.02 * (0.4 + 0.6 * (yy - top) / (bot - top))
        tk.append(f'M{X(yy) - wd:.1f},{yy:.1f} L{X(yy) + wd:.1f},{yy + wd * 1.4:.1f}')
        yy += max(3, wd * 1.6)
    k.line(' '.join(tk), 0.45, 0.9, rough=False)
    # nodes
    for f in (0.12, 0.3, 0.75):
        ny = top + (bot - top) * f
        k.shape(_oval(X(ny), ny, s * 0.045, s * 0.02), tone=3, dark=4, angle=0, outline=0.8, rough=False)
    # climber car around the thread at (x, y)
    c = _Cam(X(y), y, s * 0.7, yaw=0.5, pitch=0.25, persp=0.05)
    S = _Scene(k, c)
    S.cyl((0, -0.35, 0), (0, 0.35, 0), 0.32, n=8, seams=(0.2, 0.8), cap_off=-1)
    S.cyl((0, 0.35, 0), (0, 0.48, 0), 0.32, r2=0.12, n=8, cap_off=-1)
    S.cyl((0, -0.35, 0), (0, -0.48, 0), 0.32, r2=0.12, n=8, cap_off=-1)
    for q in (0.4, 0.4 + TAU / 3, 0.4 + 2 * TAU / 3):
        S.box((math.cos(q) * 0.36, 0, math.sin(q) * 0.36), (0.1, 0.5, 0.1), basis=((math.cos(q), 0, math.sin(q)), (0, 1, 0), (-math.sin(q), 0, math.cos(q))), off=1)
    def windows():
        for i in range(3):
            p = c.p((math.cos(0.9 + i * 0.35) * 0.322, 0.05, math.sin(0.9 + i * 0.35) * 0.322))
            k.ink.append(f'<rect x="{p[0] - s * 0.02:.1f}" y="{p[1] - s * 0.03:.1f}" width="{s * 0.04:.1f}" height="{s * 0.06:.1f}" fill="#000"/>')
    S.add(5, [('fn', windows)])
    S.render()
    # anchor platform at the foot
    ay = bot
    k.shape(k.poly([(X(ay) - s * 0.5, ay), (X(ay) + s * 0.5, ay), (X(ay) + s * 0.35, ay + s * 0.12), (X(ay) - s * 0.35, ay + s * 0.12)]), tone=2, dark=4, angle=10, outline=1.0, rough=False)
    k.shape(k.poly([(X(ay) - s * 0.12, ay), (X(ay) - s * 0.06, ay - s * 0.15), (X(ay) + s * 0.06, ay - s * 0.15), (X(ay) + s * 0.12, ay)]), tone=3, dark=4, angle=80, outline=1.0, rough=False)
    _wash(k, spec, X(y), y, s * 0.3, s * 1.2, 0, 0.35)
    _wash(k, spec, X(y), y, s * 0.35, s * 0.35, 1, 0.4)

def living_ship(k, x, y, s, spec=None):
    """A grown ship: a ribbed seed-like hull in ink with white ridge highlights, veined membrane fins,
    trailing tendrils."""
    k.depth = 0.95
    a = -0.22
    ca, sa = math.cos(a), math.sin(a)
    T = lambda u, v: (x + (u * ca - v * sa) * s, y + (u * sa + v * ca) * s)
    # tendrils behind
    for i in range(6):
        v0 = -0.12 + i * 0.05
        pts = [T(-0.9 - j * 0.12, v0 * (1 + j * 0.3) + 0.06 * math.sin(j * 0.9 + i)) for j in range(9)]
        k.solid(tapered(k, pts, s * 0.018, s * 0.003))
    # fins: translucent membranes with veins
    for sgn in (-1, 1):
        fin = k.smooth([T(0.2, sgn * 0.18), T(-0.1, sgn * 0.55), T(-0.55, sgn * 0.75), T(-0.75, sgn * 0.3), T(-0.5, sgn * 0.15)])
        k.shape(fin, tone=1, dark=2, angle=math.degrees(a) + 60, outline=0.9)
        for j in range(5):
            f = j / 4
            k.line(k.smooth([T(0.1 - f * 0.5, sgn * 0.18), T(-0.1 - f * 0.45, sgn * (0.4 + f * 0.1)), T(-0.3 - f * 0.4, sgn * (0.6 - f * 0.25))], close=False), 0.6, 0.8)
    # hull: long seed body
    hull = k.smooth([T(1.0, 0.0), T(0.7, -0.2), T(0.1, -0.28), T(-0.6, -0.22), T(-0.95, -0.06), T(-0.95, 0.06), T(-0.6, 0.22), T(0.1, 0.28), T(0.7, 0.2)])
    k.solid(hull)
    cid = _clip(k, hull); start = len(k.ink)
    w = max(1.0, s * 0.008)
    ribs = []
    for i in range(14):
        u = 0.85 - i * 0.13
        hv = 0.28 * math.sqrt(max(0.0, 1 - ((u - 0.05) / 1.0) ** 2))
        p0, pm, p1 = T(u, -hv), T(u - 0.06, 0.0), T(u, hv)
        ribs.append(f'M{p0[0]:.1f},{p0[1]:.1f} Q{pm[0]:.1f},{pm[1]:.1f} {p1[0]:.1f},{p1[1]:.1f}')
    _white(k, ' '.join(ribs[1:]), w * 0.7)
    sheen = [k.smooth([T(0.8, -0.1 - j * 0.03), T(0.2, -0.2 - j * 0.02), T(-0.5, -0.16 - j * 0.015)], close=False) for j in range(3)]
    _white(k, ' '.join(sheen), w * 1.3)
    _wrap(k, start, f'clip-path="url(#{cid})"')
    # eye-like ports along the flank
    for i in range(4):
        p = T(0.55 - i * 0.28, 0.05)
        k.ink.append(f'<circle cx="{p[0]:.1f}" cy="{p[1]:.1f}" r="{s * 0.025:.1f}" fill="#fff"/><circle cx="{p[0] + s * 0.005:.1f}" cy="{p[1] + s * 0.005:.1f}" r="{s * 0.013:.1f}" fill="#000"/>')
    _wash(k, spec, x, y, s * 1.0, s * 0.45, 1, 0.45)

SUBJECTS = {
    'figure': figure, 'suited-figure': suited_figure, 'crowd': crowd,
    'ant-column': ant_column, 'beetle': beetle, 'spider-crowd': spider_crowd, 'spiderlings': spiderlings,
    'silk-thread': silk_thread, 'balloon': balloon, 'tree': tree, 'crystal-spire': crystal_spire, 'elevator-thread': elevator_thread, 'living-ship': living_ship, 'planet': planet, 'moon': moon, 'gas-giant': gas_giant, 'stars': stars, 'signal-waves': signal_waves, 'streak': streak, 'explosion': explosion, 'fire': fire, 'shuttle': shuttle, 'rocket': rocket, 'dais': dais, 'wreck': wreck, 'cage': cage, 'lens': lens, 'cryo-pod': cryo_pod, 'screen-face': screen_face, 'console': console, 'ark-ship': ark_ship, 'satellite': satellite, 'station-ring': station_ring, 'monkey': monkey, 'egg-clutch': egg_clutch, 'fungus': fungus,
}

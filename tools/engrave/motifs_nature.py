"""Nature and place backdrops: forest floor, clearing, coast, storm and high sky, ruins, battlefield, anthill,
temple, silk city and tunnels. Each paints a place across the frame (portrait 900x1500 or band 1200x520), far to
near, leaving the subject zone readable and, in portrait, the bottom 30% light and quiet."""
import math
from motifs import trunk, bark, vine, fern, tapered

TAU = 2 * math.pi
SIDE = (-1.0, -0.2)      # light for tall forms: shade the right side rather than the foot


# ======================================================================================= shared helpers
def _portrait(k):
    return k.h > k.w


def _night(spec):
    return spec.get('light') in ('night', 'starlight')


def _hex(c):
    c = c.lstrip('#'); return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _warm_cool(spec):
    """(warmer, cooler) of the two wash pastels."""
    a, b = spec['wash']
    ra, rb = _hex(a), _hex(b)
    return (a, b) if ra[0] - ra[2] >= rb[0] - rb[2] else (b, a)


def washes(k, spec, pools):
    """Pooled pastel tints. pools: (cx, cy, rx, ry, which wash, opacity). Night keeps two, fainter."""
    night = _night(spec)
    if night:
        pools = pools[:2]
    for cx, cy, rx, ry, i, op in pools:
        k.watercolour(cx, cy, rx, ry, spec['wash'][i], op * (0.6 if night else 1.0), 4)


def _clip(k, d):
    cid = k.uid('c')
    k.defs.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
    return cid


def _grad_mask(k, x, y, w, h, stops, vertical=True):
    """A mask over a box, opacity given as [(offset, opacity), ...] top to bottom (or left to right)."""
    gid, mid = k.uid('g'), k.uid('m')
    x2, y2 = (0, 1) if vertical else (1, 0)
    st = ''.join(f'<stop offset="{o}" stop-color="#fff" stop-opacity="{a:.2f}"/>' for o, a in stops)
    k.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="{x2}" y2="{y2}">{st}</linearGradient>'
                  f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}">'
                  f'<rect x="{x:.0f}" y="{y:.0f}" width="{w:.0f}" height="{h:.0f}" fill="url(#{gid})"/></mask>')
    return mid


def quiet_bottom(k, y0=0.6, strength=0.82):
    """Portrait only: fade the ink out over the bottom of the frame, under the title text."""
    if not _portrait(k):
        return
    gid = k.uid('qb')
    k.defs.append(f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
                  f'<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                  f'<stop offset="0.3" stop-color="#fff" stop-opacity="{strength * 0.62:.2f}"/>'
                  f'<stop offset="1" stop-color="#fff" stop-opacity="{strength:.2f}"/></linearGradient>')
    k.ink.append(f'<rect x="-5" y="{k.h * y0:.0f}" width="{k.w + 10}" height="{k.h * (1 - y0) + 5:.0f}" fill="url(#{gid})"/>')


def soften(k, x, y, r, strength=0.85):
    """Lighten all ink drawn so far in a soft disc (a light source, an opening, mist)."""
    gid = k.uid('rg')
    k.defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="#fff" stop-opacity="{strength:.2f}"/>'
                  f'<stop offset="0.55" stop-color="#fff" stop-opacity="{strength * 0.5:.2f}"/>'
                  f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>')
    k.ink.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="url(#{gid})"/>')


def rays(k, x, y, r0, r1, n, a0=0, a1=TAU, w=0.5, op=0.35):
    d = ''
    for i in range(n):
        a = a0 + (a1 - a0) * (i + k.r.uniform(0.2, 0.8)) / n
        rr = r1 * k.r.uniform(0.6, 1.15)
        d += f'M{x + math.cos(a) * r0:.1f},{y + math.sin(a) * r0:.1f} L{x + math.cos(a) * rr:.1f},{y + math.sin(a) * rr:.1f} '
    k.ink.append(f'<path d="{d}" fill="none" stroke="#000" stroke-width="{w}" stroke-opacity="{op}"/>')


def glow(k, spec, x, y, r):
    """firelight / screen-glow: a pool of wash at the source, lightened ink and radiating ruled lines."""
    L = spec.get('light')
    if L not in ('firelight', 'screen-glow'):
        return False
    warm, cool = _warm_cool(spec)
    col = warm if L == 'firelight' else cool
    k.watercolour(x, y, r * 0.9, r * 0.75, col, 0.8, 4)
    k.watercolour(x, y, r * 0.45, r * 0.4, col, 0.6, 3)
    soften(k, x, y, r * 0.9, 0.8)
    rays(k, x, y, r * 0.12, r * 1.05, 26, w=0.5, op=0.32)
    return True


def stars(k, x0, x1, y0, y1, n):
    dots = ''
    for _ in range(n):
        x, y = k.r.uniform(x0, x1), k.r.uniform(y0, y1)
        rr = k.r.choice((0.8, 1.0, 1.2, 1.2, 1.6, 2.2))
        dots += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr}"/>'
    glints = ''
    for _ in range(max(2, n // 25)):
        x, y = k.r.uniform(x0, x1), k.r.uniform(y0, y1); s = k.r.uniform(4, 8)
        glints += f'M{x - s:.1f},{y:.1f} h{2 * s:.1f} M{x:.1f},{y - s:.1f} v{2 * s:.1f} '
    k.ink.append(f'<g fill="#fff">{dots}</g><path d="{glints}" stroke="#fff" stroke-width="1.4" stroke-linecap="round"/>')


def ruled_sky(k, spec, y1, y0=0, x0=None, x1=None, dense=0.0):
    """Engraver's sky: broken horizontal ruled lines, closer at the top. Night: denser, cross-ruled, with stars.
    dense 0..1 thickens it regardless of light (storms, smoke)."""
    W = k.w; L = spec.get('light', 'day')
    x0 = -10 if x0 is None else x0; x1 = W + 10 if x1 is None else x1
    night = _night(spec)
    if night:
        g0, g1, w = 2.7, 4.0, 0.7
    elif L in ('dusk', 'dawn', 'firelight'):
        g0, g1, w = 3.6, 9.0, 0.55
    else:
        g0, g1, w = 4.6, 15.0, 0.5
    g0 -= dense * (g0 - 2.6); g1 -= dense * (g1 - 4.0)
    y = y0 + k.r.uniform(0, 2)
    while y < y1:
        t = (y - y0) / max(1, y1 - y0)
        gap = g0 + (g1 - g0) * t
        op = (1.0 - 0.5 * t) if (night or dense > 0.5) else (0.9 - 0.8 * t)
        xs = x0 - k.r.uniform(0, 40); d = ''
        while xs < x1:
            seg = k.r.uniform(W * 0.12, W * 0.6)
            d += f'M{xs:.1f},{y + k.r.uniform(-0.3, 0.3):.1f} h{min(seg, x1 - xs):.1f} '
            xs += seg + k.r.uniform(3, 8 + 40 * t)
        k.ink.append(f'<path d="{d}" stroke="#000" stroke-width="{w}" stroke-opacity="{op:.2f}" fill="none"/>')
        y += gap
    if night or dense > 0.6:
        mid = _grad_mask(k, x0, y0, x1 - x0, y1 - y0, [(0, 0.9), (0.6, 0.35), (1, 0)])
        pid = k.hatch(-62, 4.2, 0.5)
        k.ink.append(f'<g mask="url(#{mid})"><rect x="{x0:.0f}" y="{y0:.0f}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}" fill="url(#{pid})"/></g>')
    if night:
        stars(k, x0, x1, y0, y0 + (y1 - y0) * 0.92, int((x1 - x0) * (y1 - y0) / 2600))


def sun(k, spec, x, y, r):
    """A low sun for dawn/dusk (and a pale disc by day): knocked-out disc, ruled bands across it, faint rays."""
    L = spec.get('light')
    if _night(spec):
        return
    warm, _ = _warm_cool(spec)
    k.watercolour(x, y, r * 3.2, r * 2.2, warm, 0.55 if L in ('dawn', 'dusk') else 0.3, 4)
    soften(k, x, y, r * 2.6, 0.75)
    k.paper(k.blob(x, y, r, r, 20, 0.01))
    k.ink.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="none" stroke="#000" stroke-width="0.7"/>')
    if L in ('dawn', 'dusk'):
        cid = _clip(k, k.blob(x, y, r, r, 20, 0.0))
        d = ''
        yy = y + r * 0.15
        while yy < y + r:
            d += f'M{x - r:.1f},{yy:.1f} h{2 * r:.1f} '
            yy += 3 + (yy - y) / r * 3
        k.ink.append(f'<path d="{d}" clip-path="url(#{cid})" stroke="#000" stroke-width="0.5" stroke-opacity="0.6"/>')
    rays(k, x, y, r * 1.3, r * 4.0, 30, w=0.45, op=0.25)


def ruled_in(k, d, y0, y1, gap, w=0.5, op=0.8, angle=0):
    """Ruled lines inside a path (shadows, water, cloud bellies)."""
    cid = _clip(k, d)
    out = ''; y = y0
    while y < y1:
        out += f'M-20,{y:.1f} L{k.w + 20},{y + math.tan(math.radians(angle)) * (k.w + 40):.1f} '
        y += gap
    k.ink.append(f'<path d="{out}" clip-path="url(#{cid})" stroke="#000" stroke-width="{w}" stroke-opacity="{op}" fill="none"/>')


def lobed(k, cx, cy, rx, ry, lobes=9, bulge=(0.35, 0.55)):
    """A closed lobed outline (foliage, cloud puffs, smoke) around an ellipse."""
    ends = []
    for i in range(lobes):
        a = -math.pi / 2 + (i + k.r.uniform(-0.2, 0.2)) / lobes * TAU
        s = k.r.uniform(0.85, 1.05)
        ends.append((cx + math.cos(a) * rx * s, cy + math.sin(a) * ry * s))
    d = f'M{ends[0][0]:.1f},{ends[0][1]:.1f}'
    for (xa, ya), (xb, yb) in zip(ends, ends[1:] + ends[:1]):
        mx, my = (xa + xb) / 2, (ya + yb) / 2
        ox, oy = mx - cx, my - cy; L = math.hypot(ox, oy) or 1
        b = math.hypot(xb - xa, yb - ya) * k.r.uniform(*bulge)
        d += f' C{xa + ox / L * b:.1f},{ya + oy / L * b:.1f} {xb + ox / L * b:.1f},{yb + oy / L * b:.1f} {xb:.1f},{yb:.1f}'
    return d + 'Z'


def cloud(k, cx, cy, w, h, tone=0, dark=2, outline=0.8, belly=True):
    """A cumulus: a pile of lobed puffs, back rows first, cut to a flat base at cy; shading gathers low right."""
    cid = _clip(k, k.poly([(cx - w, cy - h * 3), (cx + w, cy - h * 3), (cx + w, cy + h * 0.03), (cx - w, cy + h * 0.03)]))
    rows = ((0.0, 0.3, 0.62), (0.35, 0.36, 0.86), (0.75, 0.3, 1.0))     # (row depth 0 top .. 1 base, radius/h, span)
    for j, (f, rr, span) in enumerate(rows):
        r = h * rr
        n = max(2, int(w * span / (r * 1.5)))
        for i in range(n):
            u = (i + 0.5) / n
            x = cx - w * span / 2 + u * w * span + k.r.uniform(-0.2, 0.2) * r
            env = cy - h * (math.sin(math.pi * (0.5 + (u - 0.5) * span)) ** 0.7)
            y = env + r + (cy - r * 0.3 - env - r) * f
            if j == 0 and k.r.random() < 0.3:
                continue
            rad = r * k.r.uniform(0.7, 1.4)
            d = lobed(k, x, y, rad * 1.15, rad * 0.95, k.r.randint(6, 9), (0.3, 0.5))
            k.shape(d, tone=tone, dark=dark + (1 if j == 2 and dark < 4 else 0), outline=outline * (1.0 if j == 0 else 0.6),
                    angle=k.r.uniform(30, 60), clip=cid)
    k.line(f'M{cx - w * 0.5:.1f},{cy:.1f} Q{cx:.1f},{cy + h * 0.04:.1f} {cx + w * 0.5:.1f},{cy:.1f}', 0.6, 0.6)
    if belly:
        bd = ''
        for i in range(4):
            y = cy - i * (2.5 + 2 * (1 - k.depth)) - 1
            bd += f'M{cx - w * (0.35 - i * 0.06):.1f},{y:.1f} h{w * (0.75 - i * 0.12):.1f} '
        k.line(bd, 0.5, 0.6, rough=False)


def stratus(k, cx, cy, w, h, tone=1):
    """A long flat cloud bank near the horizon."""
    pts = []
    n = 9
    for i in range(n + 1):
        u = i / n
        pts.append((cx - w / 2 + u * w, cy - h * (0.4 + 0.6 * math.sin(math.pi * u)) * k.r.uniform(0.6, 1.0)))
    for i in range(n, -1, -1):
        u = i / n
        pts.append((cx - w / 2 + u * w + k.r.uniform(-8, 8), cy + h * 0.25 * k.r.uniform(0.3, 1)))
    d = k.smooth(pts)
    k.shape(d, tone=tone, dark=tone + 1, outline=0.6, angle=88)


def leaf(k, x, y, L, ang, wid=0.34, tone=2, dark=3, curl=0.0, veins=True):
    """A broad pointed leaf from its stalk at (x, y), pointing at ang (radians), with midrib and veins."""
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, v):
        v = v + curl * u * u / L
        return (x + ca * u - sa * v, y + sa * u + ca * v)

    def half(u):
        return wid * L * 0.5 * (math.sin(math.pi * min(1, u / 1.0)) ** 0.75) * (1.08 - 0.25 * u)

    us = [0.0, 0.1, 0.25, 0.42, 0.6, 0.78, 0.92, 1.0]
    left = [P(u * L, half(u) * k.r.uniform(0.94, 1.05)) for u in us]
    right = [P(u * L, -half(u) * k.r.uniform(0.94, 1.05)) for u in us[1:-1]][::-1]
    d = k.smooth(left + right)
    k.shape(d, tone=tone, dark=dark, angle=math.degrees(ang) + 65, outline=1.0)
    mid = [P(u * L, 0) for u in (0, 0.25, 0.5, 0.75, 0.97)]
    k.line(k.smooth(mid, close=False), 0.9)
    if veins:
        vd = ''
        for i in range(1, 9):
            u = i / 9.5
            for s in (-1, 1):
                a, b = P(u * L, 0), P(min(1, u + 0.1) * L, s * half(u) * 0.85)
                c = P((u + 0.04) * L, s * half(u) * 0.45)
                vd += f'M{a[0]:.1f},{a[1]:.1f} Q{c[0]:.1f},{c[1]:.1f} {b[0]:.1f},{b[1]:.1f} '
        k.line(vd, 0.55, 0.85)
    # stalk
    s0 = P(-L * 0.12, 0)
    k.line(f'M{s0[0]:.1f},{s0[1]:.1f} L{x:.1f},{y:.1f}', 1.4)


def grass(k, x0, x1, y, n, h, lean=0.0):
    d = ''
    for _ in range(n):
        x = k.r.uniform(x0, x1); hh = h * k.r.uniform(0.4, 1.0); b = (lean + k.r.uniform(-0.5, 0.5)) * hh
        d += f'M{x:.1f},{y + k.r.uniform(-2, 2):.1f} q{b * 0.2:.1f},{-hh * 0.6:.1f} {b:.1f},{-hh:.1f} '
    k.line(d, 0.7)


def pebbles(k, x0, x1, y0, y1, n, size):
    for _ in range(n):
        x, y = k.r.uniform(x0, x1), k.r.uniform(y0, y1); s = size * k.r.uniform(0.4, 1.0)
        k.shape(k.blob(x, y, s, s * 0.6, 9, 0.2), tone=1, dark=3, outline=0.7)


def ground(k, y, tone=1, dark=2, wave=8, angle=90, x0=-30, x1=None):
    x1 = k.w + 30 if x1 is None else x1
    pts = [(x0, k.h + 40)]
    n = 10
    for i in range(n + 1):
        pts.append((x0 + (x1 - x0) * i / n, y + k.r.uniform(-wave, wave)))
    pts.append((x1, k.h + 40))
    d = k.smooth(pts)
    k.shape(d, tone=tone, dark=dark, angle=angle, outline=0.8)
    return d


def ruled_ground(k, y, wave=6, tone=0, gap0=2.4, gap1=16, op=0.75, x0=-30, x1=None, y1=None):
    """Ground as an engraver rules it: broken horizontal lines, tight at the horizon, opening toward the viewer."""
    x1 = k.w + 30 if x1 is None else x1; y1 = k.h + 10 if y1 is None else y1
    pts = [(x0, k.h + 40)] + [(x0 + (x1 - x0) * i / 10, y + k.r.uniform(-wave, wave)) for i in range(11)] + [(x1, k.h + 40)]
    d = k.smooth(pts)
    k.paper(d)
    if tone:
        for pid in k.tone_fills(tone, 88):
            k.ink.append(f'<path d="{d}" fill="url(#{pid})" filter="url(#rough)"/>')
    cid = _clip(k, d)
    yy = y - wave; out = []
    while yy < y1:
        t = (yy - y) / max(1, y1 - y)
        xs = x0 - k.r.uniform(0, 80); dd = ''
        while xs < x1:
            seg = k.r.uniform(30, 260) * (1 - 0.4 * max(0, t))
            dd += f'M{xs:.1f},{yy + k.r.uniform(-0.5, 0.5):.1f} h{seg:.1f} '
            xs += seg + k.r.uniform(2, 10) + max(0, t) * k.r.uniform(0, 70)
        w = (0.45 + 0.5 * k.depth) * (1 + 0.6 * max(0, t))
        out.append(f'<path d="{dd}" stroke="#000" stroke-width="{w:.2f}" stroke-opacity="{op * (1 - 0.3 * max(0, t)):.2f}" fill="none"/>')
        yy += gap0 + (gap1 - gap0) * max(0, t) ** 0.8
    k.ink.append(f'<g clip-path="url(#{cid})" filter="url(#rough)">{"".join(out)}</g>')
    k.line(k.smooth(pts[1:-1], close=False), 0.8)
    return d


def crown(k, cx, cy, rx, ry, lobes=9, tone=2, dark=4, marks=True):
    """A tree crown or foliage mass as an engraver draws it: a lobed outline, inner lobe contours, leaf ticks."""
    d = lobed(k, cx, cy, rx, ry, lobes)
    k.shape(d, tone=tone, dark=dark, angle=k.r.uniform(25, 65))
    dd = ''
    for _ in range(max(3, lobes // 2)):
        a = k.r.uniform(-0.3, 2.2); f = k.r.uniform(0.25, 0.7)
        px, py = cx + math.cos(a) * rx * f, cy + math.sin(a) * ry * f; r = min(rx, ry) * k.r.uniform(0.18, 0.32)
        dd += f'M{px - r:.1f},{py:.1f} C{px - r:.1f},{py - r * 1.1:.1f} {px + r:.1f},{py - r * 1.1:.1f} {px + r:.1f},{py:.1f} '
    k.line(dd, 0.7, 0.8)
    if marks:
        k.leafmarks(cx - rx * 0.8, cx + rx * 0.4, cy - ry * 0.8, cy + ry * 0.1, int((rx + ry) * 0.25))
    return d


def furrows(k, vx, vy, y0, y1, n, spread, w=0.6, op=0.6):
    """Perspective ground lines converging on (vx, vy), drawn between y0 and y1."""
    d = ''
    for i in range(n):
        xb = vx + (i / (n - 1) - 0.5) * spread + k.r.uniform(-10, 10)
        t0 = (y0 - vy) / (y1 - vy)
        xa = vx + (xb - vx) * t0
        d += f'M{xa:.1f},{y0:.1f} L{xb:.1f},{y1:.1f} '
    k.line(d, w, op)


def jagged(k, x0, y0, x1, y1, n, amp):
    pts = []
    for i in range(n + 1):
        t = i / n
        pts.append((x0 + (x1 - x0) * t + (k.r.uniform(-amp, amp) if 0 < i < n else 0),
                    y0 + (y1 - y0) * t + (k.r.uniform(-amp, amp) if 0 < i < n else 0)))
    return pts


def smoke(k, x, y, h, w0, drift, tone=2, dark=3):
    """A billowing smoke column from (x, y) rising h, widening, drifting sideways. Drawn top (back) first."""
    puffs = []
    n = 12
    for i in range(n):
        t = i / (n - 1)
        r = w0 * (0.5 + 1.6 * t) * k.r.uniform(0.85, 1.15)
        puffs.append((x + drift * t ** 1.4 + k.r.uniform(-r, r) * 0.35, y - h * t, r))
        if t > 0.4:
            puffs.append((x + drift * t ** 1.4 + k.r.choice((-1, 1)) * r * 0.7, y - h * t + r * 0.3, r * 0.7))
    for px, py, r in sorted(puffs, key=lambda p: p[1]):
        d = lobed(k, px, py, r, r * 0.8, k.r.randint(7, 10), (0.3, 0.5))
        k.shape(d, tone=tone, dark=dark, outline=0.6, angle=k.r.uniform(20, 70))
        a = k.r.uniform(-2.6, -0.8)
        k.line(f'M{px + math.cos(a) * r * 0.45:.1f},{py + math.sin(a) * r * 0.35:.1f} '
               f'a{r * 0.45:.1f},{r * 0.35:.1f} 0 0 1 {r * 0.5:.1f},{r * 0.22:.1f}', 0.55, 0.7)


# =========================================================================================== forest floor
def buttress(k, x, w, fl, reach, side=1, tone=2, dark=4):
    """A giant trunk base whose buttress roots run out as tall thin fins across the floor toward side (+1 right)."""
    fins = ((0.3, 1.0, -0.01, 0.0), (0.2, 0.6, 0.03, 0.1))
    for yt, rf, dy, off in fins:
        x0 = x + side * w * (0.25 + off)
        ytop = fl - k.h * yt
        xr = x + side * (w * 0.4 + reach * rf); yb = fl + k.h * dy
        th = k.w * 0.012 * (1 + rf)
        d = (f'M{x0 - side * th:.1f},{ytop:.1f} C{x0 + side * reach * rf * 0.1:.1f},{yb - k.h * 0.06:.1f} {xr - side * reach * rf * 0.4:.1f},{yb - 4:.1f} {xr:.1f},{yb:.1f} '
             f'Q{xr - side * reach * 0.06:.1f},{yb + 6:.1f} {xr - side * reach * 0.12:.1f},{yb + 7:.1f} '
             f'C{x0 + side * reach * rf * 0.3:.1f},{yb + 6:.1f} {x0 - side * th * 0.5:.1f},{yb:.1f} {x0 - side * th * 2:.1f},{yb - k.h * 0.02:.1f}Z')
        k.shape(d, tone=tone, dark=dark, angle=50 if side > 0 else 130)
        # the lit crest of the fin and a few ridge lines along it
        k.line(f'M{x0 - side * th:.1f},{ytop:.1f} C{x0 + side * reach * rf * 0.1:.1f},{yb - k.h * 0.06:.1f} {xr - side * reach * rf * 0.4:.1f},{yb - 4:.1f} {xr:.1f},{yb:.1f}', 1.3)
        rd = ''
        for j in range(3):
            f = 0.25 + j * 0.22
            rd += (f'M{x0 + side * th * (1 + j):.1f},{ytop + (yb - ytop) * f:.1f} '
                   f'Q{x0 + side * reach * rf * 0.3:.1f},{yb - (yb - ytop) * 0.1 * (1 - f):.1f} {xr - side * reach * rf * (0.35 - f * 0.3):.1f},{yb + 2:.1f} ')
        k.line(rd, 0.6, 0.7)
    k.shape(trunk(k, x, w, -40, fl + k.h * 0.05, lean=side * -8), tone=tone, dark=dark, angle=6)
    bark(k, x, w * 0.8, side * -8)
    for _ in range(4):
        k.stipple(x + side * w * k.r.uniform(-0.1, 0.4), fl - k.h * k.r.uniform(0.02, 0.4), w * 0.07, k.h * 0.015, 25, (0.5, 1.2))


def understory(k, x, y, L, n=5, spread=1.6, tone=2, dark=3, up=-1.57):
    """A clump of broad understory leaves fanning up from a base."""
    angs = sorted(up + spread * (i / (n - 1) - 0.5) + k.r.uniform(-0.12, 0.12) for i in range(n))
    order = sorted(range(n), key=lambda i: -abs(angs[i] - up))
    for i in order:
        a = angs[i]
        leaf(k, x, y, L * k.r.uniform(0.7, 1.0), a, wid=0.38, tone=tone, dark=dark, curl=0.18 * (1 if a > up else -1))


def mushroom(k, x, y, h, cw, lean=0.0):
    k.shape(k.smooth([(x - cw * 0.12, y), (x - cw * 0.08 + lean * 0.5, y - h * 0.5), (x - cw * 0.09 + lean, y - h),
                      (x + cw * 0.09 + lean, y - h), (x + cw * 0.08 + lean * 0.5, y - h * 0.5), (x + cw * 0.14, y)]),
            tone=1, dark=2, angle=80)
    tx, ty = x + lean, y - h
    cap = (f'M{tx - cw / 2:.1f},{ty + cw * 0.06:.1f} C{tx - cw * 0.48:.1f},{ty - cw * 0.5:.1f} {tx + cw * 0.48:.1f},{ty - cw * 0.5:.1f} '
           f'{tx + cw / 2:.1f},{ty + cw * 0.06:.1f} Q{tx:.1f},{ty - cw * 0.08:.1f} {tx - cw / 2:.1f},{ty + cw * 0.06:.1f}Z')
    k.shape(cap, tone=1, dark=3, angle=k.r.uniform(30, 60))
    gd = ''
    for i in range(9):
        u = (i + 0.5) / 9 - 0.5
        gd += f'M{tx + u * cw * 0.95:.1f},{ty + cw * 0.05 - abs(u) * 0.0:.1f} L{tx + u * cw * 0.2:.1f},{ty - cw * 0.03:.1f} '
    k.line(gd, 0.5, 0.8)
    # speckles on the cap
    for _ in range(4):
        a = k.r.uniform(0.2, 0.8) * math.pi; rr = cw * k.r.uniform(0.1, 0.3)
        k.ink.append(f'<ellipse cx="{tx - math.cos(a) * rr:.1f}" cy="{ty - cw * 0.18 - math.sin(a) * rr * 0.4:.1f}" rx="{cw * 0.035:.1f}" ry="{cw * 0.022:.1f}" fill="#fff" stroke="#000" stroke-width=".6"/>')


def log(k, x0, y0, x1, y1, r):
    """A fallen log lying from (x0, y0) (cut end, rings showing) to (x1, y1), radius r."""
    ang = math.atan2(y1 - y0, x1 - x0); nx, ny = -math.sin(ang), math.cos(ang)
    body = k.smooth([(x0 + nx * r, y0 + ny * r), ((x0 + x1) / 2 + nx * r * 1.05, (y0 + y1) / 2 + ny * r * 1.05), (x1 + nx * r * 0.9, y1 + ny * r * 0.9),
                     (x1 - nx * r * 0.9, y1 - ny * r * 0.9), ((x0 + x1) / 2 - nx * r, (y0 + y1) / 2 - ny * r), (x0 - nx * r, y0 - ny * r)])
    k.shape(body, tone=2, dark=4, angle=math.degrees(ang) + 90)
    bd = ''
    for i in range(10):
        o = k.r.uniform(-0.8, 0.8); t0 = k.r.uniform(0.05, 0.6); t1 = t0 + k.r.uniform(0.15, 0.4)
        bd += (f'M{x0 + (x1 - x0) * t0 + nx * r * o:.1f},{y0 + (y1 - y0) * t0 + ny * r * o:.1f} '
               f'L{x0 + (x1 - x0) * t1 + nx * r * o:.1f},{y0 + (y1 - y0) * t1 + ny * r * o:.1f} ')
    k.line(bd, 0.8, 0.9)
    end = k.blob(x0, y0, r * 0.45, r * 1.0, 16, 0.06)
    k.shape(end, tone=0, dark=0, outline=1.0)
    rd = ''
    for f in (0.25, 0.5, 0.75):
        rd += k.blob(x0, y0, r * 0.45 * f, r * f, 14, 0.08) + ' '
    k.line(rd, 0.5, 0.8)
    k.line(f'M{x0:.1f},{y0:.1f} l{r * 0.3:.1f},{r * 0.7:.1f}', 0.6)
    # moss on top
    k.leafmarks(min(x0, x1), max(x0, x1), min(y0, y1) - r * 1.1, min(y0, y1) - r * 0.6, 30)


def forest_floor(k, spec):
    W, H = k.w, k.h; P = _portrait(k); S = min(W, H)
    fl = H * (0.6 if P else 0.68)
    washes(k, spec, [(W * 0.5, H * 0.22, W * 0.6, H * 0.22, 0, 0.6), (W * 0.62, fl - H * 0.04, W * 0.4, H * 0.1, 1, 0.5),
                     (W * 0.25, H * 0.42, W * 0.25, H * 0.15, 1, 0.3)])
    if _night(spec):
        ruled_sky(k, spec, fl)
    else:
        for i in range(7):     # light shafts through the canopy
            x = W * (-0.1 + i * 0.17) + k.r.uniform(-15, 15)
            k.line(f'M{x:.0f},0 L{x + W * 0.28:.0f},{fl:.0f}', 0.5, 0.2, rough=False)
    # far: misty trunk bases with low flares, hanging lianas, far ferns
    k.depth = 0.12
    for j in range(6):
        x = W * (0.1 + j * 0.16) + k.r.uniform(-25, 25); w = S * k.r.uniform(0.04, 0.09)
        k.shape(trunk(k, x, w, -20, fl - H * 0.01, lean=k.r.uniform(-8, 8)), tone=1, dark=2, outline=0.6, angle=k.r.uniform(-6, 6))
        for s_ in (-1, 1):
            x0 = x + s_ * w * 0.4
            k.shape(f'M{x0:.1f},{fl - H * 0.08:.1f} C{x0 + s_ * w * 0.1:.1f},{fl - H * 0.02:.1f} {x0 + s_ * w * 0.5:.1f},{fl:.1f} {x0 + s_ * w * 1.1:.1f},{fl + 2:.1f} '
                    f'L{x - s_ * w * 0.1:.1f},{fl + 2:.1f}Z', tone=1, dark=2, outline=0.5, angle=70)
        k.line(f'M{x + w * 0.6:.1f},0 q{k.r.uniform(-20, 20):.1f},{H * 0.2:.1f} {k.r.uniform(-10, 10):.1f},{H * k.r.uniform(0.25, 0.45):.1f}', 0.6, 0.6)
    ruled_ground(k, fl, wave=4, gap0=2.2, gap1=12, op=0.6)
    for j in range(9):
        fern(k, W * k.r.uniform(0.05, 0.95), fl + 3, S * k.r.uniform(0.05, 0.09))
    k.leafmarks(0, W, fl, fl + H * 0.04, 90)
    # mid: fallen log with fungi, understory clumps, leaf litter
    k.depth = 0.5
    understory(k, W * 0.12, fl + H * 0.02, S * 0.2, 5)
    log(k, W * 0.6, fl + H * 0.03, W * 1.1, fl + H * 0.0, S * 0.06)
    for x, h, cw in ((W * 0.66, S * 0.1, S * 0.08), (W * 0.73, S * 0.065, S * 0.055), (W * 0.84, S * 0.12, S * 0.09)):
        mushroom(k, x, fl - S * 0.035, h, cw, lean=k.r.uniform(-6, 6))
    for x, h, cw in ((W * 0.34, S * 0.08, S * 0.07), (W * 0.4, S * 0.05, S * 0.045)):
        mushroom(k, x, fl + H * 0.04, h, cw, lean=k.r.uniform(-6, 6))
    for _ in range(7):
        leaf(k, W * k.r.uniform(0.25, 0.85), fl + H * k.r.uniform(0.05, 0.13), S * k.r.uniform(0.07, 0.11),
             k.r.choice((0.15, 2.9, -0.2, 3.3)), wid=0.34, tone=1, dark=2, curl=0.15)
    pebbles(k, W * 0.3, W * 0.7, fl + H * 0.03, fl + H * 0.09, 8, S * 0.012)
    glow(k, spec, W * 0.5, fl, S * 0.35)
    # near: buttressed trunk on the left, giant overhanging leaves, lianas, ferns
    k.depth = 0.95
    buttress(k, W * 0.02, S * 0.24, fl + H * 0.07, W * (0.34 if P else 0.22), side=1)
    leaf(k, W * 1.06, -H * 0.01, S * 0.5, 2.5, wid=0.4, tone=2, dark=4, curl=0.25)
    leaf(k, W * 1.02, H * (0.1 if P else 0.25), S * 0.38, 2.85, wid=0.38, tone=2, dark=4, curl=0.2)
    leaf(k, W * 0.15, -H * 0.03, S * 0.32, 0.9, wid=0.36, tone=2, dark=3, curl=-0.2)
    vine(k, W * 0.8, H * 0.08, H * (0.3 if P else 0.5))
    vine(k, W * 0.38, 0, H * (0.16 if P else 0.32))
    understory(k, W * 0.95, H * (0.9 if P else 1.02), S * 0.3, 5, tone=2, dark=4, up=-1.9)
    for x in (W * 0.5, W * 0.72):
        fern(k, x, H * 1.0, H * (k.r.uniform(0.1, 0.16) if P else 0.22))
    quiet_bottom(k)


# ================================================================================================= clearing
def canopy_mass(k, x0, x1, ytop, ybot, tone=2, dark=3, n=6):
    """A wall of trees seen from the side: lobed crowns stacked back to front, lower ones nearer."""
    items = [(x0 + (x1 - x0) * k.r.uniform(0, 1), ytop + (ybot - ytop) * k.r.uniform(0.0, 0.85)) for _ in range(n)]
    for cx, cy in sorted(items, key=lambda p: p[1]):
        r = (x1 - x0) * k.r.uniform(0.2, 0.34)
        crown(k, cx, cy, r, r * 0.75, k.r.randint(8, 12), tone=tone, dark=dark)


def corner_foliage(k, side, w, h, tone=3, dark=4):
    """An overhanging leaf mass in a top corner (side -1 left, +1 right), built from overlapping crowns."""
    x0 = -w * 0.2 if side < 0 else k.w + w * 0.2
    for i in range(4):
        f = i / 3
        cx = x0 - side * w * (0.15 + 0.75 * f) + k.r.uniform(-20, 20)
        cy = h * (0.2 + 0.55 * math.sin(math.pi * f * 0.8)) * k.r.uniform(0.7, 1.1)
        crown(k, cx, cy, w * k.r.uniform(0.28, 0.4), h * k.r.uniform(0.5, 0.7), k.r.randint(8, 11), tone=tone, dark=dark)


def web_wreck(k, x, y, s):
    """A toppled frame of poles with torn threads trailing from it."""
    poles = [(x - s * 0.5, y, s * 1.1, -1.2), (x + s * 0.3, y, s * 0.9, -1.95), (x - s * 0.1, y + s * 0.05, s * 0.7, -0.5)]
    tips = []
    for px, py, L, a in poles:
        stake(k, px, py, L, a, s * 0.035)
        tips.append((px + math.cos(a) * L, py + math.sin(a) * L))
    d = ''
    for (ax, ay), (bx, by) in zip(tips, tips[1:] + tips[:1]):
        d += f'M{ax:.1f},{ay:.1f} Q{(ax + bx) / 2:.1f},{(ay + by) / 2 + s * 0.2:.1f} {bx:.1f},{by:.1f} '
    for tx, ty in tips:
        for _ in range(3):
            L = s * k.r.uniform(0.2, 0.6)
            d += f'M{tx:.1f},{ty:.1f} q{k.r.uniform(-10, 10):.1f},{L * 0.5:.1f} {k.r.uniform(-20, 20):.1f},{L:.1f} '
    k.line(d, 0.5, 0.8, rough=False)


def carapace(k, x, y, s, ang=0.0):
    """A great overturned shell lying on the field: a domed husk with ridged segments and a dark hollow."""
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, v): return (x + ca * u - sa * v, y + sa * u + ca * v)

    dome = [P(-s, 0), P(-s * 0.85, -s * 0.4), P(-s * 0.4, -s * 0.62), P(s * 0.2, -s * 0.66), P(s * 0.75, -s * 0.45), P(s, 0)]
    k.shape(k.smooth(dome + [P(s * 0.4, s * 0.12), P(-s * 0.5, s * 0.12)]), tone=2, dark=4, angle=70)
    k.shape(k.smooth([P(-s * 0.85, 0), P(-s * 0.2, -s * 0.1), P(s * 0.8, 0), P(s * 0.2, s * 0.1)]), tone=4, dark=4, outline=0.8)
    rd = ''
    for f in (-0.55, -0.15, 0.25, 0.6):
        a, b, c = P(f * s, -s * 0.02), P(f * s * 0.9 - s * 0.05, -s * 0.45), P(f * s * 0.7, -s * 0.62 + abs(f) * s * 0.2)
        rd += f'M{a[0]:.1f},{a[1]:.1f} Q{b[0]:.1f},{b[1]:.1f} {c[0]:.1f},{c[1]:.1f} '
    k.line(rd, 0.9)
    g0, g1 = P(-s * 0.6, -s * 0.42), P(-s * 0.1, -s * 0.58)
    k.ink.append(f'<path d="M{g0[0]:.1f},{g0[1]:.1f} Q{(g0[0] + g1[0]) / 2:.1f},{g1[1] - s * 0.05:.1f} {g1[0]:.1f},{g1[1]:.1f}" stroke="#fff" stroke-width="{max(1.2, s * 0.03):.1f}" fill="none" stroke-linecap="round"/>')


def stump(k, x, y, r, h):
    side = (f'M{x - r:.1f},{y - h:.1f} L{x - r * 1.05:.1f},{y:.1f} Q{x - r * 1.4:.1f},{y + r * 0.25:.1f} {x - r * 1.5:.1f},{y + r * 0.3:.1f} '
            f'Q{x:.1f},{y + r * 0.55:.1f} {x + r * 1.5:.1f},{y + r * 0.3:.1f} Q{x + r * 1.3:.1f},{y + r * 0.2:.1f} {x + r * 1.05:.1f},{y:.1f} '
            f'L{x + r:.1f},{y - h:.1f}Z')
    k.shape(side, tone=2, dark=4, angle=84)
    top = k.blob(x, y - h, r, r * 0.32, 18, 0.05)
    k.shape(top, tone=0, dark=0, outline=1.0)
    rd = ''
    for f in (0.3, 0.55, 0.8):
        rd += k.blob(x + r * 0.05, y - h, r * f, r * 0.32 * f, 14, 0.06) + ' '
    k.line(rd, 0.5, 0.8)
    k.line(f'M{x - r * 0.6:.1f},{y - h + r * 0.15:.1f} l{r * 0.2:.1f},{h * 0.7:.1f} M{x + r * 0.3:.1f},{y - h + r * 0.3:.1f} l{-r * 0.05:.1f},{h * 0.6:.1f}', 0.6)


def clearing(k, spec):
    W, H = k.w, k.h; P = _portrait(k); S = min(W, H)
    hz = H * (0.5 if P else 0.6)
    washes(k, spec, [(W * 0.55, H * 0.2, W * 0.45, H * 0.18, 1, 0.55), (W * 0.5, hz + H * 0.06, W * 0.5, H * 0.08, 0, 0.5),
                     (W * 0.15, H * 0.3, W * 0.2, H * 0.2, 0, 0.35)])
    ruled_sky(k, spec, hz)
    sun(k, spec, W * 0.64, hz - S * 0.12, S * 0.05)
    if not _night(spec):
        k.depth = 0.1
        cloud(k, W * 0.42, H * (0.16 if P else 0.25), S * 0.42, S * 0.11)
        stratus(k, W * 0.7, hz - S * 0.25, S * 0.5, S * 0.03)
    # far treeline
    k.depth = 0.15
    k.shape(k.scallop(-30, W + 30, hz - S * 0.07, S * 0.035, 22, up=True), tone=1, dark=2, outline=0.6, angle=80)
    for x in (W * 0.33, W * 0.78):        # emergent giants standing above the far treeline
        k.shape(trunk(k, x, S * 0.012, hz - S * 0.22, hz - S * 0.05), tone=1, dark=2, outline=0.5)
        for j in range(3):
            crown(k, x + S * k.r.uniform(-0.05, 0.05), hz - S * (0.22 + 0.02 * j), S * k.r.uniform(0.05, 0.08), S * 0.03, 8, tone=1, dark=2, marks=False)
    ruled_ground(k, hz - S * 0.02, wave=3, gap0=2.4, gap1=15, op=0.6)
    # mid: tree walls each side, stumps of the cleared forest, grass
    k.depth = 0.5
    canopy_mass(k, -W * 0.1, W * 0.26, H * 0.05, hz - S * 0.05, n=6)
    canopy_mass(k, W * 0.76, W * 1.1, H * 0.08, hz - S * 0.04, n=6)
    for x, w in ((W * 0.12, S * 0.03), (W * 0.2, S * 0.022), (W * 0.84, S * 0.028), (W * 0.93, S * 0.035)):
        k.shape(trunk(k, x, w, hz - S * 0.25, hz + S * 0.01, lean=k.r.uniform(-5, 5)), tone=2, dark=3, angle=84)
    for x, y, r in ((W * 0.3, hz + S * 0.05, S * 0.035), (W * 0.67, hz + S * 0.04, S * 0.03), (W * 0.78, hz + S * 0.1, S * 0.045),
                    (W * 0.18, hz + S * 0.12, S * 0.05)):
        stump(k, x, y, r, r * 0.9)
        grass(k, x - r * 2, x + r * 2, y + r * 0.3, 14, r * 0.6)
    grass(k, 0, W, hz + S * 0.02, 70, S * 0.025)
    glow(k, spec, W * 0.5, hz + S * 0.04, S * 0.3)
    # near: overhanging foliage at the corners, a framing trunk, tall grass
    k.depth = 0.95
    k.shape(trunk(k, W * 0.02, S * 0.12, -20, H + 20, lean=14), tone=2, dark=4, angle=82)
    bark(k, W * 0.02, S * 0.12, 14)
    corner_foliage(k, -1, W * (0.45 if P else 0.35), H * (0.12 if P else 0.22))
    corner_foliage(k, 1, W * (0.4 if P else 0.3), H * (0.1 if P else 0.2))
    vine(k, W * 0.88, H * 0.04, H * (0.22 if P else 0.4))
    vine(k, W * 0.25, H * 0.05, H * (0.15 if P else 0.3))
    grass(k, -10, W * 0.25, H + 5, 40, S * 0.12, lean=0.3)
    grass(k, W * 0.8, W + 10, H + 5, 30, S * 0.12, lean=-0.3)
    quiet_bottom(k)


# ==================================================================================================== coast
def sea_stack(k, x, base, top, w, tone=2, dark=4, plants=True, tilt=None):
    """A stone sea stack: an irregular, waisted pillar with tilted bedding, notched ledges, fissures, a grassy cap."""
    tilt = k.r.uniform(-0.12, 0.12) if tilt is None else tilt
    n = 14; ph = k.r.uniform(0, 6); lean = k.r.uniform(-0.08, 0.08) * (base - top)
    left, right = [], []
    for i in range(n + 1):
        t = i / n; y = base + (top - base) * t
        hw = w / 2 * (1.15 - 0.35 * t + max(0, 0.18 - t) * 2.2) * (1 + 0.13 * math.sin(t * 9 + ph)) + w * 0.02
        cx = x + lean * t
        jl, jr = k.r.uniform(-0.06, 0.06) * w, k.r.uniform(-0.06, 0.06) * w
        if 0 < i < n and k.r.random() < 0.2:       # a notch where a softer bed has weathered back
            left.append((cx - hw + w * 0.07 + jl, y + 4)); right.append((cx + hw - w * 0.05 + jr, y - 3))
        left.append((cx - hw + jl, y)); right.append((cx + hw + jr, y))
    tl, tr = left[-1], right[-1]
    crown_pts = jagged(k, tl[0], tl[1] + w * tilt, tr[0], tr[1] - w * tilt, 5, w * 0.05)
    pts = left + crown_pts[1:-1] + right[::-1]
    d = k.smooth(pts)
    k.shape(d, tone=tone, dark=dark, angle=k.r.uniform(-8, 8), light=SIDE)
    cid = _clip(k, d)
    # the turned-away shadow side: a second, denser layer of hatching on the right ~40% of the pillar
    sh_pts = [(l[0] + (r[0] - l[0]) * k.r.uniform(0.55, 0.65), l[1]) for l, r in zip(left, right)] + [(r[0] + w, r[1]) for r in right[::-1]]
    k.shape(k.smooth(sh_pts), tone=0, dark=4, outline=0, angle=k.r.uniform(60, 75), clip=cid, light=SIDE, knock=False)
    # bedding planes: tilted, broken lines across the face, heavier on the shadow side
    bd, sh = '', ''
    y = base
    while y > top + w * 0.1:
        y -= w * k.r.uniform(0.12, 0.3)
        x0 = x - w; x1 = x + w
        f0 = k.r.uniform(0, 0.4); f1 = k.r.uniform(0.6, 1.0)
        xa, xb = x0 + 2 * w * f0, x0 + 2 * w * f1
        bd += (f'M{xa:.1f},{y + tilt * 2 * w * (f0 - 0.5):.1f} Q{(xa + xb) / 2:.1f},{y + tilt * w * (f0 + f1 - 1) + w * 0.08:.1f} '
               f'{xb:.1f},{y + tilt * 2 * w * (f1 - 0.5):.1f} ')
        if k.r.random() < 0.5:
            sh += f'M{x + w * 0.1:.1f},{y + 2.5 + tilt * w * 0.2:.1f} L{x1:.1f},{y + 2.5 + tilt * w:.1f} '
    k.ink.append(f'<g clip-path="url(#{cid})" filter="url(#rough)"><path d="{bd}" stroke="#000" stroke-width="{0.6 + 0.6 * k.depth:.2f}" fill="none"/>'
                 f'<path d="{sh}" stroke="#000" stroke-width="{1.2 + 1.6 * k.depth:.2f}" stroke-opacity="0.75" fill="none"/></g>')
    # fissures
    fd = ''
    for _ in range(int(w / 25) + 2):
        fx = x + k.r.uniform(-0.3, 0.4) * w; fy = k.r.uniform(top + w * 0.2, base - w * 0.1); L = (base - top) * k.r.uniform(0.05, 0.16)
        pts_ = [(fx, fy), (fx + k.r.uniform(-5, 5), fy + L * 0.5), (fx + k.r.uniform(-7, 7), fy + L)]
        fd += k.poly(pts_, close=False) + ' '
    k.ink.append(f'<path d="{fd}" clip-path="url(#{cid})" stroke="#000" stroke-width="{0.7 + 0.8 * k.depth:.2f}" fill="none" filter="url(#rough)"/>')
    if plants:
        for i in range(4):
            u = (i + 0.5) / 4
            bx = tl[0] + (tr[0] - tl[0]) * u; by = tl[1] + (tr[1] - tl[1]) * u + w * tilt * (1 - 2 * u)
            crown(k, bx, by - w * 0.04, w * k.r.uniform(0.14, 0.22), w * k.r.uniform(0.07, 0.11), 7, tone=2, dark=4, marks=False)
        k.leafmarks(tl[0], tr[0], top - w * 0.14, top, int(w * 0.25))
        for _ in range(3):
            vx = k.r.uniform(tl[0], tr[0])
            k.line(f'M{vx:.1f},{top:.1f} q{k.r.uniform(-8, 8):.1f},{w * 0.4:.1f} {k.r.uniform(-4, 4):.1f},{w * k.r.uniform(0.5, 1.4):.1f}', 0.8)
    return pts


def foam(k, x, y, w):
    """Surf breaking at the foot of a rock: knocked-out spray, curling crests, stippled spume, a few boulders."""
    k.paper(k.blob(x, y - w * 0.04, w * 0.6, w * 0.1, 16, 0.35))
    d = ''
    for i in range(7):
        cx = x + k.r.uniform(-0.55, 0.55) * w; s = w * k.r.uniform(0.06, 0.14); yy = y + k.r.uniform(-0.04, 0.03) * w
        d += f'M{cx - s * 1.4:.1f},{yy:.1f} q{s * 0.5:.1f},{-s * 1.2:.1f} {s * 1.3:.1f},{-s * 1.0:.1f} q{s * 0.5:.1f},{s * 0.15:.1f} {s * 0.3:.1f},{s * 0.55:.1f} '
    k.line(d, 0.8)
    k.stipple(x, y - w * 0.05, w * 0.6, w * 0.08, int(w * 0.8), (0.5, 1.1))
    for _ in range(2):
        bx = x + k.r.uniform(-0.5, 0.5) * w; s = w * k.r.uniform(0.03, 0.06)
        k.shape(k.blob(bx, y + s * 0.2, s, s * 0.6, 9, 0.2), tone=2, dark=4, outline=0.8)


def sea(k, hz, y1, w_far=0.45):
    """Ruled water: fine lines near the horizon opening up toward the viewer, with crests and dark troughs."""
    W = k.w
    y = hz + 1.5
    while y < y1:
        t = (y - hz) / (y1 - hz)
        gap = 2.2 + t * 16
        xs = -10 - k.r.uniform(0, 60); d = ''
        while xs < W + 10:
            seg = k.r.uniform(W * 0.05, W * 0.3) * (1 - 0.5 * t)
            d += f'M{xs:.1f},{y:.1f} h{seg:.1f} '
            xs += seg + k.r.uniform(2, 6) + t * k.r.uniform(10, 50)
        k.ink.append(f'<path d="{d}" stroke="#000" stroke-width="{w_far + 0.45 * t:.2f}" stroke-opacity="{0.85 - 0.2 * t:.2f}" fill="none"/>')
        if t > 0.06:
            cd, td = '', ''
            for _ in range(int(2 + 7 * t)):
                cx = k.r.uniform(-20, W + 20); s = 10 + 70 * t * k.r.uniform(0.5, 1.2)
                cd += f'M{cx - s:.1f},{y + s * 0.03:.1f} C{cx - s * 0.4:.1f},{y - s * 0.09:.1f} {cx + s * 0.3:.1f},{y - s * 0.1:.1f} {cx + s:.1f},{y + s * 0.02:.1f} '
                td += f'M{cx - s * 0.6:.1f},{y + 2 + s * 0.04:.1f} q{s * 0.5:.1f},{s * 0.05:.1f} {s * 1.3:.1f},{s * 0.01:.1f} '
            k.ink.append(f'<path d="{cd}" stroke="#000" stroke-width="{0.5 + 0.6 * t:.2f}" fill="none" filter="url(#rough)"/>'
                         f'<path d="{td}" stroke="#000" stroke-width="{0.9 + 1.6 * t:.2f}" stroke-opacity="0.6" fill="none" filter="url(#rough)"/>')
        y += gap


def coast(k, spec):
    W, H = k.w, k.h; P = _portrait(k); S = min(W, H)
    hz = H * (0.5 if P else 0.56)
    washes(k, spec, [(W * 0.5, hz + H * 0.12, W * 0.6, H * 0.15, 0, 0.6), (W * 0.4, H * 0.18, W * 0.5, H * 0.18, 1, 0.55),
                     (W * 0.32, hz - H * 0.03, W * 0.3, H * 0.06, 1, 0.4)])
    ruled_sky(k, spec, hz)
    sx = W * 0.36
    sun(k, spec, sx, hz - S * 0.06, S * 0.05)
    if not _night(spec):
        k.depth = 0.12
        stratus(k, W * 0.62, hz - S * 0.13, S * 0.6, S * 0.025)
        stratus(k, W * 0.2, hz - S * 0.2, S * 0.4, S * 0.02)
        cloud(k, W * 0.66, H * (0.13 if P else 0.22), S * 0.36, S * 0.1)
    # far headland and distant stacks
    k.depth = 0.15
    k.shape(k.smooth([(W * 0.62, hz + 1), (W * 0.72, hz - S * 0.03), (W * 0.85, hz - S * 0.045), (W * 1.05, hz - S * 0.06), (W * 1.05, hz + 1)]),
            tone=1, dark=2, outline=0.5, angle=88)
    sea_stack(k, W * 0.6, hz + 2, hz - S * 0.09, S * 0.03, tone=1, dark=2, plants=False)
    sea_stack(k, W * 0.67, hz + 2, hz - S * 0.06, S * 0.022, tone=1, dark=2, plants=False)
    sea(k, hz, H + 10)
    if not _night(spec):      # the sun's broken path on the water
        d = ''
        y = hz + 4
        while y < hz + H * 0.2:
            t = (y - hz) / (H * 0.2); hw = S * (0.02 + 0.06 * t)
            d += f'M{sx - hw * k.r.uniform(0.6, 1):.1f},{y:.1f} h{hw * k.r.uniform(0.6, 1.8):.1f} '
            y += 3 + 6 * t
        k.ink.append(f'<path d="{d}" stroke="#fff" stroke-width="2.2" fill="none"/>')
    # mid: a stack on the right with surf
    k.depth = 0.5
    mx = W * (0.86 if P else 0.82)
    sea_stack(k, mx, hz + S * 0.08, hz - S * (0.42 if P else 0.6), S * 0.12, tone=2, dark=3)
    foam(k, mx, hz + S * 0.085, S * 0.2)
    glow(k, spec, W * 0.5, hz, S * 0.3)
    # near: the great pillar at the left, waves breaking at its foot
    k.depth = 0.95
    nb = H * (0.86 if P else 1.05)
    sea_stack(k, W * (0.14 if P else 0.1), nb, H * (0.09 if P else 0.08), S * (0.3 if P else 0.26), tone=2, dark=4)
    foam(k, W * 0.16, nb, S * 0.42)
    k.shape(k.smooth([(W * 0.72, H + 20), (W * 0.8, H * 0.93), (W * 0.92, H * 0.9), (W * 1.04, H * 0.88), (W * 1.04, H + 20)]),
            tone=2, dark=3, angle=70)
    quiet_bottom(k)


# ================================================================================================ storm-sky
def bolt(k, x, y0, y1, branches=2):
    pts = [(x, y0)]
    y = y0
    while y < y1:
        y += k.r.uniform(18, 40); pts.append((pts[-1][0] + k.r.uniform(-28, 28), min(y, y1)))
    d = k.poly(pts, close=False)
    for i in range(branches):
        j = k.r.randrange(1, max(2, len(pts) - 2)); bx, by = pts[j]; s = k.r.choice((-1, 1))
        bp = [(bx, by)]
        for _ in range(k.r.randint(2, 4)):
            bp.append((bp[-1][0] + s * k.r.uniform(10, 30), bp[-1][1] + k.r.uniform(15, 30)))
        d += ' ' + k.poly(bp, close=False)
    soften(k, x, y0 + (y1 - y0) * 0.2, (y1 - y0) * 0.45, 0.6)
    k.ink.append(f'<path d="{d}" stroke="#000" stroke-width="8.5" fill="none" stroke-linejoin="round"/>'
                 f'<path d="{d}" stroke="#fff" stroke-width="4.6" fill="none" stroke-linejoin="round"/>')


def rain(k, x0, x1, y0, y1, n, slant=0.25, op=0.5, L=(20, 60)):
    d = ''
    for _ in range(n):
        x = k.r.uniform(x0, x1); y = k.r.uniform(y0, y1); l = k.r.uniform(*L)
        d += f'M{x:.1f},{y:.1f} l{l * slant:.1f},{l:.1f} '
    k.ink.append(f'<path d="{d}" stroke="#000" stroke-width="0.6" stroke-opacity="{op}" fill="none"/>')


def storm_sky(k, spec):
    W, H = k.w, k.h; P = _portrait(k); S = min(W, H)
    gl = H * (0.82 if P else 0.86)
    washes(k, spec, [(W * 0.5, H * 0.4, W * 0.35, H * 0.18, 0, 0.55), (W * 0.3, H * 0.12, W * 0.5, H * 0.15, 1, 0.5),
                     (W * 0.75, H * 0.6, W * 0.3, H * 0.15, 1, 0.35)])
    ruled_sky(k, spec, gl, dense=0.85)
    # far: a storm wall along the horizon, with rain hanging from it
    k.depth = 0.15
    for i in range(7):
        cloud(k, W * (i / 6) + k.r.uniform(-30, 30), gl - S * 0.05, S * 0.36, S * 0.13, tone=1, dark=3, outline=0.5, belly=False)
    for i in range(5):
        curtain(k, W * (0.1 + i * 0.2), gl - S * 0.05, gl, S * 0.12, 0.2, 40)
    # mid: towering masses at the sides with rain curtains, a break of light at the centre
    k.depth = 0.5
    masses = ((W * 0.06, H * (0.4 if P else 0.62), S * 0.7, S * 0.3), (W * 0.96, H * (0.36 if P else 0.58), S * 0.75, S * 0.32))
    for cx, cy, w, h in masses:
        cloud(k, cx, cy, w, h, tone=2, dark=4, outline=0.9)
        curtain(k, cx + (S * 0.1 if cx < W / 2 else -S * 0.1), cy, gl, w * 0.45, 0.25, 110 if P else 70)
    bolt(k, W * 0.82, H * (0.37 if P else 0.58), gl, 3)
    if P:
        bolt(k, W * 0.14, H * 0.41, gl - 20, 2)
    rain(k, 0, W, H * 0.1, gl, 220 if P else 140, op=0.3)
    soften(k, W * 0.5, H * (0.4 if P else 0.45), S * 0.4, 0.6)
    glow(k, spec, W * 0.5, H * 0.4, S * 0.3)
    # near: the storm ceiling overhead, hanging pouches, a dark ridge with wind-bent trees
    k.depth = 0.95
    ceil = H * (0.06 if P else 0.08)
    k.shape(k.foliage(-60, W + 60, ceil, 26, 9, top=-80), tone=3, dark=4, outline=1.2, angle=8)
    mammatus(k, -20, W * 0.42, ceil + S * 0.03, S * 0.05)
    mammatus(k, W * 0.6, W + 20, ceil + S * 0.03, S * 0.05)
    ridge = k.smooth([(-30, H + 30), (-30, gl - S * 0.03), (W * 0.25, gl + S * 0.01), (W * 0.55, gl - S * 0.03), (W * 0.8, gl), (W + 30, gl - S * 0.02), (W + 30, H + 30)])
    k.shape(ridge, tone=2, dark=4, angle=80)
    grass(k, 0, W, gl + 2, 80, S * 0.04, lean=0.6)
    windtree(k, W * 0.1, gl - S * 0.01, S * 0.24, 0.6)
    windtree(k, W * 0.86, gl - S * 0.015, S * 0.18, 0.6)
    quiet_bottom(k)


# ================================================================================================= sky-high
def cirrus(k, x, y, w, n):
    d = ''
    for i in range(n):
        yy = y + i * k.r.uniform(4, 9); xx = x + k.r.uniform(-w, w) * 0.1; L = w * k.r.uniform(0.4, 1.0)
        d += f'M{xx:.1f},{yy:.1f} q{L * 0.5:.1f},{-L * 0.06:.1f} {L:.1f},{-L * 0.02:.1f} q{L * 0.06:.1f},{-L * 0.02:.1f} {L * 0.1:.1f},{-L * 0.07:.1f} '
    k.line(d, 0.5, 0.7)


def cloud_tower(k, x, base, h, w, tone=1, dark=3, outline=0.9, drift=0.0):
    """A towering cumulus: stacked piles narrowing upward, the top drawn first so lower piles overlap it."""
    n = 4
    for j in reversed(range(n)):
        f = j / n
        cloud(k, x + drift * f, base - h * f, w * (1 - 0.18 * j), h / n * 1.6, tone=tone, dark=dark, outline=outline, belly=(j == 0))


def sky_high(k, spec):
    W, H = k.w, k.h; P = _portrait(k); S = min(W, H)
    hz = H * (0.64 if P else 0.74)
    washes(k, spec, [(W * 0.5, H * 0.22, W * 0.6, H * 0.2, 0, 0.55), (W * 0.5, hz, W * 0.6, H * 0.08, 1, 0.55),
                     (W * 0.2, H * 0.08, W * 0.25, H * 0.1, 1, 0.4)])
    # thin air: darker toward the top
    ruled_sky(k, spec, hz, dense=0.45)
    sun(k, spec, W * 0.78, H * (0.1 if P else 0.18), S * 0.05)
    k.depth = 0.2
    for x, y, w in ((W * 0.3, H * 0.06, W * 0.45), (W * 0.55, H * 0.17, W * 0.35), (W * 0.05, H * (0.3 if P else 0.42), W * 0.3),
                    (W * 0.62, H * (0.33 if P else 0.45), W * 0.3)):
        cirrus(k, x, y, w, 7)
    # far: the curve of the world and the top of the cloud sea, a field of small heads
    k.depth = 0.1
    curve = S * 0.05
    k.line(f'M-10,{hz - S * 0.045 + curve:.1f} Q{W / 2:.1f},{hz - S * 0.045 - curve:.1f} {W + 10},{hz - S * 0.045 + curve:.1f}', 0.9, 0.7, rough=False)
    for i in range(16):
        x = W * (i / 15) + k.r.uniform(-20, 20)
        cloud(k, x, hz + k.r.uniform(-3, 3), S * k.r.uniform(0.12, 0.2), S * k.r.uniform(0.025, 0.045), tone=0, dark=2, outline=0.5, belly=False)
    ruled_ground(k, hz + 2, wave=2, gap0=3, gap1=18, op=0.35)
    # mid: towers of cumulus rising from the cloud sea, framing the open sky
    k.depth = 0.45
    cloud_tower(k, W * 0.06, hz + S * 0.03, H * (0.42 if P else 0.6), S * 0.5, drift=S * 0.04)
    cloud_tower(k, W * 0.96, hz + S * 0.02, H * (0.28 if P else 0.45), S * 0.42, drift=-S * 0.03)
    cloud(k, W * 0.64, hz + S * 0.03, S * 0.3, S * 0.09, tone=0, dark=3)
    glow(k, spec, W * 0.5, H * 0.4, S * 0.3)
    # near: big billows at the bottom corners
    k.depth = 0.9
    cloud(k, W * 0.05, H * (0.9 if P else 1.08), S * 0.7, S * 0.22, tone=0, dark=3, outline=1.1)
    cloud(k, W * 0.95, H * (0.94 if P else 1.1), S * 0.75, S * 0.25, tone=0, dark=3, outline=1.1)
    cloud(k, W * 0.5, H * (1.02 if P else 1.2), S * 0.7, S * 0.14, tone=0, dark=2, outline=1.0)
    quiet_bottom(k)


# =================================================================================================== ruins
def column(k, bx, by, cw, ch, broken=True, fallen_top=False):
    """A fluted stone column on a plinth, in light perspective; broken columns end in a jagged top."""
    pl = cw * 1.35; ph = cw * 0.35
    k.shape(k.poly([(bx - pl / 2, by), (bx - pl / 2, by - ph), (bx + pl / 2, by - ph), (bx + pl / 2, by)]), tone=1, dark=3, angle=80)
    top = by - ph - ch
    if broken:
        tp = jagged(k, bx - cw / 2 * 0.9, top + k.r.uniform(-0.1, 0.1) * cw, bx + cw / 2 * 0.9, top + k.r.uniform(-0.3, 0.3) * cw, 5, cw * 0.12)
        body = [(bx - cw / 2, by - ph)] + tp + [(bx + cw / 2, by - ph)]
    else:
        body = [(bx - cw / 2, by - ph), (bx - cw / 2 * 0.88, top), (bx + cw / 2 * 0.88, top), (bx + cw / 2, by - ph)]
    d = k.poly(body)
    k.shape(d, tone=1, dark=4, angle=86, light=SIDE)
    # flutes, packed toward the edges as the cylinder turns away
    fd = ''
    for i in range(1, 8):
        u = math.cos(math.pi * i / 8)
        x = bx - u * cw / 2 * 0.85
        fd += f'M{x:.1f},{by - ph - 2:.1f} L{x:.1f},{top + cw * 0.15:.1f} '
    cid = _clip(k, d)
    k.ink.append(f'<path d="{fd}" clip-path="url(#{cid})" stroke="#000" stroke-width="{0.5 + 0.4 * k.depth:.2f}" fill="none" filter="url(#rough)"/>')
    # drum joints
    jd = ''
    y = by - ph - cw * 0.9
    while y > top + cw * 0.2:
        jd += f'M{bx - cw / 2:.1f},{y:.1f} Q{bx:.1f},{y + cw * 0.08:.1f} {bx + cw / 2:.1f},{y:.1f} '
        y -= cw * k.r.uniform(0.9, 1.3)
    k.line(jd, 0.6, 0.8)
    if not broken:
        cap = k.poly([(bx - cw * 0.75, top), (bx - cw * 0.6, top - cw * 0.3), (bx + cw * 0.6, top - cw * 0.3), (bx + cw * 0.75, top)])
        k.shape(cap, tone=1, dark=3, angle=80)
        k.shape(k.poly([(bx - cw * 0.8, top - cw * 0.3), (bx - cw * 0.8, top - cw * 0.5), (bx + cw * 0.8, top - cw * 0.5), (bx + cw * 0.8, top - cw * 0.3)]), tone=1, dark=2, angle=80)
    return top


def drum(k, x, y, r, L, ang=0.0):
    """A fallen column drum lying on the ground."""
    ca, sa = math.cos(ang), math.sin(ang)
    x1, y1 = x + ca * L, y + sa * L
    body = k.smooth([(x, y - r), (x1, y1 - r), (x1 + r * 0.3, y1), (x1, y1 + r), (x, y + r)])
    k.shape(body, tone=1, dark=4, angle=10)
    fd = ''
    for i in range(1, 7):
        v = math.cos(math.pi * i / 7) * r * 0.9
        fd += f'M{x:.1f},{y + v:.1f} L{x1:.1f},{y1 + v:.1f} '
    k.line(fd, 0.5, 0.7)
    k.shape(k.blob(x, y, r * 0.35, r, 16, 0.04), tone=0, dark=0, outline=1.0)
    k.line(k.blob(x, y, r * 0.18, r * 0.5, 12, 0.05), 0.5, 0.6)


def arch(k, cx, base, span, pier_h, pier_w, frac=0.62):
    """A broken stone arch: two coursed piers and a voussoir ring that breaks off part way across."""
    for px in (cx - span / 2 - pier_w / 2, cx + span / 2 + pier_w / 2):
        d = k.poly([(px - pier_w / 2, base), (px - pier_w / 2 * 0.95, base - pier_h), (px + pier_w / 2 * 0.95, base - pier_h), (px + pier_w / 2, base)])
        k.shape(d, tone=1, dark=4, angle=4, light=SIDE)
        cd = ''
        y = base; row = 0
        while y > base - pier_h + 4:
            y2 = max(base - pier_h, y - pier_w * 0.45)
            cd += f'M{px - pier_w / 2:.1f},{y2:.1f} h{pier_w:.1f} '
            jx = px - pier_w / 2 + pier_w * (0.35 if row % 2 else 0.7)
            cd += f'M{jx:.1f},{y:.1f} V{y2:.1f} '
            y = y2; row += 1
        k.line(cd, 0.6, 0.8)
    oy = base - pier_h; R = span / 2 + pier_w; r = span / 2
    n = 18; a1 = math.pi + math.pi * frac
    outer = [(cx + math.cos(math.pi + (a1 - math.pi) * i / n) * R, oy + math.sin(math.pi + (a1 - math.pi) * i / n) * R) for i in range(n + 1)]
    inner = [(cx + math.cos(math.pi + (a1 - math.pi) * i / n) * r, oy + math.sin(math.pi + (a1 - math.pi) * i / n) * r) for i in range(n + 1)]
    brk = jagged(k, outer[-1][0], outer[-1][1], inner[-1][0], inner[-1][1], 3, pier_w * 0.12)
    d = k.poly(outer + brk[1:-1] + inner[::-1])
    k.shape(d, tone=1, dark=3, angle=40)
    vd = ''
    for i in range(1, n, 2):
        vd += f'M{inner[i][0]:.1f},{inner[i][1]:.1f} L{outer[i][0]:.1f},{outer[i][1]:.1f} '
    k.line(vd, 0.6, 0.8)
    # the soffit in shadow
    k.shape(k.poly(inner + [(p[0] + (cx - p[0]) * 0.08, p[1] + (oy - p[1]) * 0.08 + 3) for p in inner[::-1]]), tone=3, dark=4, outline=0.4)
    # the fallen keystone pieces at its foot
    for _ in range(3):
        bx = cx + k.r.uniform(0, 0.6) * span; s = pier_w * k.r.uniform(0.25, 0.45)
        k.shape(k.poly([(bx - s, base), (bx - s * 0.8, base - s * 0.8), (bx + s * 0.7, base - s * 0.9), (bx + s, base)]), tone=1, dark=4, outline=0.8)


def ruins(k, spec):
    W, H = k.w, k.h; P = _portrait(k); S = min(W, H)
    gl = H * (0.6 if P else 0.72)
    vx, vy = W * 0.6, gl - S * 0.06
    washes(k, spec, [(W * 0.55, H * 0.25, W * 0.4, H * 0.2, 1, 0.55), (W * 0.35, gl, W * 0.45, H * 0.08, 0, 0.5),
                     (W * 0.85, H * 0.15, W * 0.2, H * 0.15, 0, 0.35)])
    ruled_sky(k, spec, gl)
    sun(k, spec, W * 0.72, gl - S * 0.2, S * 0.045)
    # far: distant broken arcade and a pale treeline
    k.depth = 0.15
    for i in range(15):
        x = W * (i / 14) + k.r.uniform(-15, 15)
        crown(k, x, gl - S * k.r.uniform(0.06, 0.12), S * k.r.uniform(0.07, 0.1), S * k.r.uniform(0.05, 0.08), 9, tone=1, dark=2, marks=False)
    # a far ruined wall: coursed blocks, broken skyline, in perspective toward the vanishing point
    wx0, wx1 = W * 0.36, W * 0.72
    wt = lambda x: gl - S * (0.13 - 0.06 * (x - wx0) / (wx1 - wx0)) + k.r.uniform(-1, 1) * S * 0.02
    sky_pts = [(wx0 + (wx1 - wx0) * i / 10, wt(wx0 + (wx1 - wx0) * i / 10)) for i in range(11)]
    wall = k.poly([(wx0, gl + 2)] + sky_pts + [(wx1, gl + 2)])
    k.shape(wall, tone=1, dark=2, outline=0.6, angle=4)
    wc = _clip(k, wall)
    cd = ''
    for j in range(1, 9):
        f = j / 9
        cd += f'M{wx0:.1f},{gl - S * 0.13 * f:.1f} L{wx1:.1f},{gl - S * 0.07 * f:.1f} '
    for i in range(1, 18):
        x = wx0 + (wx1 - wx0) * i / 18
        for j in range(0, 9, 2):
            f0, f1 = j / 9, (j + 1) / 9; hgt = S * (0.13 - 0.06 * i / 18)
            xx = x + ((wx1 - wx0) / 36 if (j // 2) % 2 else 0)
            cd += f'M{xx:.1f},{gl - hgt * f0:.1f} V{gl - hgt * f1:.1f} '
    k.ink.append(f'<path d="{cd}" clip-path="url(#{wc})" stroke="#000" stroke-width="0.45" stroke-opacity="0.8" fill="none"/>')
    for x in (wx0 + (wx1 - wx0) * 0.3, wx0 + (wx1 - wx0) * 0.7):
        k.paper(f'M{x - S * 0.02:.1f},{gl:.1f} V{gl - S * 0.05:.1f} Q{x:.1f},{gl - S * 0.08:.1f} {x + S * 0.02:.1f},{gl - S * 0.05:.1f} V{gl:.1f}Z')
        k.line(f'M{x - S * 0.02:.1f},{gl:.1f} V{gl - S * 0.05:.1f} Q{x:.1f},{gl - S * 0.08:.1f} {x + S * 0.02:.1f},{gl - S * 0.05:.1f} V{gl:.1f}', 0.6)
    ruled_ground(k, gl, wave=2, gap0=2.4, gap1=15, op=0.5)
    furrows(k, vx, vy, gl + 2, H, 11, W * 2.6, 0.5, 0.45)
    pd = ''
    y = gl + 6
    while y < H:     # paving joints, opening toward the viewer
        pd += f'M-10,{y:.1f} L{W + 10},{y + k.r.uniform(-3, 3):.1f} '
        y += 6 + (y - gl) * 0.22
    k.line(pd, 0.5, 0.4)
    # mid: colonnade receding along the left toward the vanishing point, an arch fragment at the right
    k.depth = 0.5
    nb = (W * 0.06, H * (0.86 if P else 1.0))
    for i in range(6, 0, -1):
        s = 1 / (1 + 0.55 * i)
        bx = vx + (nb[0] - vx) * s; by = vy + (nb[1] - vy) * s
        cw = S * 0.15 * s * (1 if P else 0.9); ch = S * (1.0 if P else 0.95) * s * k.r.uniform(0.45, 1.0)
        column(k, bx, by, cw, ch, broken=(i % 3 != 1))
    ax, ay = W * (0.8 if P else 0.82), gl + S * 0.05
    arch(k, ax, ay, S * 0.17, S * 0.3, S * 0.06)
    vine(k, ax - S * 0.1, ay - S * 0.42, S * 0.25)
    k.leafmarks(ax - S * 0.16, ax + S * 0.02, ay - S * 0.45, ay - S * 0.36, 30)
    for x, y, r, L, a in ((W * 0.42, gl + S * 0.08, S * 0.03, S * 0.1, 0.1), (W * 0.62, gl + S * 0.14, S * 0.04, S * 0.12, -0.15)):
        drum(k, x, y, r, L, a)
        grass(k, x - r, x + L + r, y + r, 12, r * 0.8)
    glow(k, spec, W * 0.5, gl, S * 0.3)
    # near: jungle canopy over everything, a great broken column with vines at the left edge, leaves at the right
    k.depth = 0.95
    corner_foliage(k, -1, W * (0.5 if P else 0.35), H * (0.1 if P else 0.2))
    corner_foliage(k, 1, W * (0.45 if P else 0.3), H * (0.08 if P else 0.18))
    top = column(k, W * 0.02, H * (0.95 if P else 1.15), S * 0.22, H * (0.7 if P else 0.9), broken=True)
    for x in (W * 0.0, W * 0.07):
        vine(k, x, top + 10, H * 0.35)
    leaf(k, W * 1.04, H * 0.06, S * 0.38, 2.4, wid=0.32, tone=2, dark=4, curl=0.1)
    leaf(k, W * 1.02, H * 0.2, S * 0.3, 2.85, wid=0.3, tone=2, dark=3, curl=0.06)
    vine(k, W * 0.72, H * 0.05, H * (0.2 if P else 0.35))
    drum(k, W * 0.82, H * (0.93 if P else 1.02), S * 0.06, S * 0.18, 0.08)
    quiet_bottom(k)


# ============================================================================================== battlefield
def stake(k, x, y, L, ang, w):
    """A broken spear or stake driven into the ground at an angle, its top splintered."""
    x1, y1 = x + math.cos(ang) * L, y + math.sin(ang) * L
    nx, ny = -math.sin(ang), math.cos(ang)
    spl = [(x1 + nx * w * 0.5 + math.cos(ang) * w * k.r.uniform(1, 4), y1 + ny * w * 0.5 + math.sin(ang) * w * k.r.uniform(1, 4)),
           (x1 + math.cos(ang) * w * k.r.uniform(0, 1.5), y1 + math.sin(ang) * w * k.r.uniform(0, 1.5)),
           (x1 - nx * w * 0.4 + math.cos(ang) * w * k.r.uniform(2, 6), y1 - ny * w * 0.4 + math.sin(ang) * w * k.r.uniform(2, 6))]
    pts = [(x + nx * w, y + ny * w), (x1 + nx * w * 0.6, y1 + ny * w * 0.6)] + spl + [(x1 - nx * w * 0.6, y1 - ny * w * 0.6), (x - nx * w, y - ny * w)]
    k.shape(k.poly(pts), tone=3, dark=4, angle=math.degrees(ang), outline=0.9)
    k.line(f'M{x:.1f},{y:.1f} l{math.cos(ang) * L * 0.9:.1f},{math.sin(ang) * L * 0.9:.1f}', 0.4, 0.6, rough=False)


def shell_plate(k, x, y, s, ang):
    """A shattered chitin plate lying on the ground: a curved shard with ridges and a white sheen."""
    ca, sa = math.cos(ang), math.sin(ang)

    def P(u, v): return (x + ca * u - sa * v, y + sa * u + ca * v)

    pts = [P(-s, 0), P(-s * 0.6, -s * 0.5), P(0, -s * 0.62), P(s * 0.55, -s * 0.45), P(s * 0.8, -s * 0.1), P(s * 0.5, s * 0.05), P(s * 0.2, -s * 0.1), P(-s * 0.2, s * 0.08)]
    d = k.poly(pts)
    k.shape(d, tone=3, dark=4, angle=math.degrees(ang) + 60)
    rd = ''
    for f in (0.3, 0.55):
        a, b, c = P(-s * 0.8, -s * f * 0.3), P(0, -s * 0.62 * (1 - f * 0.6)), P(s * 0.6, -s * f * 0.3)
        rd += f'M{a[0]:.1f},{a[1]:.1f} Q{b[0]:.1f},{b[1]:.1f} {c[0]:.1f},{c[1]:.1f} '
    k.ink.append(f'<path d="{rd}" stroke="#fff" stroke-width="1.6" fill="none" stroke-linecap="round"/>')


def crater(k, x, y, rx, ry):
    k.shape(k.blob(x, y, rx * 1.15, ry * 1.3, 16, 0.12), tone=1, dark=2, outline=0.7, angle=90)
    k.shape(k.blob(x, y + ry * 0.1, rx, ry, 16, 0.1), tone=2, dark=4, outline=1.0, angle=-20)
    pebbles(k, x - rx * 1.4, x + rx * 1.4, y - ry * 1.5, y + ry * 1.6, 6, rx * 0.08)


def battlefield(k, spec):
    W, H = k.w, k.h; P = _portrait(k); S = min(W, H)
    hz = H * (0.55 if P else 0.62)
    warm, cool = _warm_cool(spec)
    washes(k, spec, [(W * 0.5, hz - H * 0.05, W * 0.6, H * 0.12, 0, 0.6), (W * 0.25, H * 0.2, W * 0.4, H * 0.2, 1, 0.5),
                     (W * 0.8, H * 0.3, W * 0.25, H * 0.2, 0, 0.35)])
    ruled_sky(k, spec, hz, dense=0.55)
    # far: distant smoke plumes and shattered trunks on the skyline
    k.depth = 0.15
    for x in (W * 0.36, W * 0.64):
        smoke(k, x, hz - S * 0.02, H * 0.28, S * 0.025, S * 0.18, tone=1, dark=2)
    for _ in range(11):
        x = k.r.uniform(-0.02, 1.02) * W; h = S * k.r.uniform(0.05, 0.18); ww = S * k.r.uniform(0.006, 0.012)
        pts = [(x - ww, hz + 2), (x - ww * 0.6, hz - h * 0.7)] + jagged(k, x - ww * 0.5, hz - h, x + ww * 0.6, hz - h * k.r.uniform(0.7, 0.95), 3, 3) + [(x + ww, hz + 2)]
        k.shape(k.poly(pts), tone=2, dark=3, outline=0.6)
        if k.r.random() < 0.5:
            k.line(f'M{x:.1f},{hz - h * 0.6:.1f} l{k.r.choice((-1, 1)) * h * 0.25:.1f},{-h * 0.2:.1f}', 0.8)
    ruled_ground(k, hz, wave=3, tone=1, gap0=2.4, gap1=14, op=0.7)
    furrows(k, W * 0.5, hz - S * 0.04, hz + 3, H, 15, W * 3.0, 0.6, 0.45)
    # mid: smoke columns at the sides, craters, a toppled frame, an empty shell, broken stakes
    k.depth = 0.5
    smoke(k, W * 0.08, hz + S * 0.03, H * (0.55 if P else 0.75), S * 0.05, S * 0.22, tone=2, dark=4)
    smoke(k, W * 0.9, hz + S * 0.02, H * (0.5 if P else 0.7), S * 0.045, -S * 0.14, tone=2, dark=4)
    for x, y, r in ((W * 0.3, hz + S * 0.06, S * 0.07), (W * 0.74, hz + S * 0.1, S * 0.09), (W * 0.5, hz + S * 0.03, S * 0.04)):
        crater(k, x, y, r, r * 0.25)
    carapace(k, W * 0.66, hz + S * 0.035, S * 0.07, 0.05)
    web_wreck(k, W * 0.25, hz + S * 0.04, S * 0.12)
    for x, y, L, a in ((W * 0.62, hz + S * 0.05, S * 0.1, -1.4), (W * 0.82, hz + S * 0.04, S * 0.14, -2.1), (W * 0.42, hz + S * 0.12, S * 0.12, -0.9),
                       (W * 0.12, hz + S * 0.14, S * 0.16, -1.1)):
        stake(k, x, y, L, a, S * 0.007)
    for x, y, s, a in ((W * 0.55, hz + S * 0.15, S * 0.05, 0.2), (W * 0.18, hz + S * 0.2, S * 0.06, -0.3), (W * 0.36, hz + S * 0.09, S * 0.03, 0.5)):
        shell_plate(k, x, y, s, a)
    pebbles(k, W * 0.2, W * 0.8, hz + S * 0.02, hz + S * 0.2, 14, S * 0.01)
    if not glow(k, spec, W * 0.1, hz + S * 0.02, S * 0.28):
        k.watercolour(W * 0.1, hz, S * 0.12, S * 0.06, warm, 0.5, 3)
    k.stipple(W * 0.15, hz - S * 0.12, S * 0.12, S * 0.16, 70, (0.5, 1.3))
    k.stipple(W * 0.85, hz - S * 0.1, S * 0.1, S * 0.14, 50, (0.5, 1.3))
    # near: shattered plates and stakes at the bottom corners, scorched clods
    k.depth = 0.95
    shell_plate(k, W * 0.88, H * (0.88 if P else 0.95), S * 0.12, -0.4)
    stake(k, W * 0.05, H * 1.02, S * (0.42 if P else 0.6), -1.15, S * 0.014)
    stake(k, W * 0.96, H * 1.02, S * (0.34 if P else 0.5), -2.05, S * 0.012)
    pebbles(k, 0, W * 0.3, H * (0.9 if P else 0.92), H, 8, S * 0.02)
    quiet_bottom(k)


# ================================================================================================== anthill
def spire(k, x, base, top, w, tone=1, dark=4, lean=None):
    """A mound chimney: a tall, lumpy, blunt-topped earthen spire with deep gullies, accretion ridges and vents."""
    n = 12; ph = k.r.uniform(0, 6)
    lean = k.r.uniform(-0.06, 0.06) * (base - top) if lean is None else lean
    hw = lambda t: w / 2 * ((1 - t) ** 0.55) * (1 + 0.1 * math.sin(t * 11 + ph)) + w * 0.08
    cx = lambda t: x + lean * t * t
    ys = lambda t: base + (top - base) * t
    left = [(cx(t) - hw(t) * k.r.uniform(0.94, 1.06), ys(t)) for t in (i / n for i in range(n))]
    right = [(cx(t) + hw(t) * k.r.uniform(0.94, 1.06), ys(t)) for t in (i / n for i in range(n))]
    capx = cx(1)
    cap = [(capx - w * 0.07, top + w * 0.04), (capx - w * 0.02, top - w * 0.02), (capx + w * 0.04, top), (capx + w * 0.08, top + w * 0.05)]
    d = k.smooth(left + cap + right[::-1])
    k.shape(d, tone=tone, dark=dark, angle=k.r.uniform(-6, 6), light=SIDE)
    cid = _clip(k, d)
    sh = [(cx(t) + hw(t) * 0.25, ys(t)) for t in (i / n for i in range(n + 1))] + [(cx(t) + w, ys(t)) for t in (i / n for i in range(n, -1, -1))]
    k.shape(k.smooth(sh), tone=0, dark=4, outline=0, angle=k.r.uniform(55, 70), clip=cid, light=SIDE, knock=False)
    gd, gs = '', []
    for f in (-0.6, -0.25, 0.1, 0.45, 0.75):
        t1 = k.r.uniform(0.6, 0.92)
        pts = [(cx(t) + f * hw(t) + math.sin(t * 8 + f * 5) * w * 0.02, ys(t)) for t in [t1 * i / 8 for i in range(9)]]
        if f > 0:
            gs.append(tapered(k, pts, w * 0.022, w * 0.004))
        else:
            gd += k.smooth(pts, close=False) + ' '
    k.line(gd, 0.7, 0.8)
    for g in gs:
        k.ink.append(f'<path d="{g}" fill="#000" clip-path="url(#{cid})" filter="url(#rough)"/>')
    ad = ''
    for _ in range(int((base - top) / (w * 0.15))):
        t = k.r.uniform(0.05, 0.9); a = k.r.uniform(-0.8, 0.3)
        px = cx(t) + a * hw(t); L = hw(t) * k.r.uniform(0.3, 0.7)
        ad += f'M{px:.1f},{ys(t):.1f} q{L / 2:.1f},{w * 0.03:.1f} {L:.1f},{-w * 0.005:.1f} '
    k.line(ad, 0.6, 0.7)
    if k.r.random() < 0.6:
        t = k.r.uniform(0.25, 0.55)
        vx, vy = cx(t) + k.r.uniform(-0.35, 0.0) * hw(t), ys(t)
        k.solid(f'M{vx - w * 0.06:.1f},{vy:.1f} C{vx - w * 0.06:.1f},{vy - w * 0.1:.1f} {vx + w * 0.06:.1f},{vy - w * 0.1:.1f} {vx + w * 0.06:.1f},{vy:.1f}Z')
        k.line(f'M{vx - w * 0.09:.1f},{vy + w * 0.01:.1f} q{w * 0.09:.1f},{w * 0.04:.1f} {w * 0.18:.1f},0', 0.9)
    return d


def anthill(k, spec):
    W, H = k.w, k.h; P = _portrait(k); S = min(W, H)
    gl = H * (0.63 if P else 0.82)
    washes(k, spec, [(W * 0.5, H * 0.3, W * 0.45, H * 0.2, 0, 0.6), (W * 0.5, H * 0.1, W * 0.5, H * 0.12, 1, 0.5),
                     (W * 0.75, gl - H * 0.1, W * 0.25, H * 0.1, 1, 0.35)])
    ruled_sky(k, spec, gl)
    sun(k, spec, W * 0.62, H * (0.1 if P else 0.18), S * 0.045)
    # far: distant mounds on the plain
    k.depth = 0.12
    far = gl - S * 0.1
    for x, h, w in ((W * 0.04, S * 0.16, S * 0.09), (W * 0.42, S * 0.07, S * 0.05), (W * 0.58, S * 0.1, S * 0.06), (W * 0.97, S * 0.2, S * 0.1)):
        spire(k, x, far + 4, far - h, w, tone=1, dark=2)
    ruled_ground(k, far, wave=2, gap0=2.2, gap1=10, op=0.55)
    # mid: the fortress mound, a cluster of fused spires around a lower, lighter dome holding the gate
    k.depth = 0.5
    base = gl + S * 0.02
    sp = [(W * 0.13, H * (0.1 if P else 0.06), S * 0.22), (W * 0.29, H * (0.2 if P else 0.22), S * 0.17), (W * 0.84, H * (0.06 if P else 0.04), S * 0.24),
          (W * 0.69, H * (0.18 if P else 0.22), S * 0.17), (W * 0.97, H * (0.22 if P else 0.3), S * 0.16), (W * 0.02, H * (0.26 if P else 0.32), S * 0.15)]
    for x, top, w in sorted(sp, key=lambda s: s[1]):
        spire(k, x, base - S * 0.1, top, w)
    # one continuous lumpy mass fused from the spire bases, lower at the centre where the gate is
    tops = [(-0.12, 0.2), (0.0, 0.3), (0.1, 0.36), (0.2, 0.31), (0.3, 0.34), (0.4, 0.25), (0.5, 0.22), (0.6, 0.26), (0.7, 0.36), (0.8, 0.33),
            (0.9, 0.38), (1.0, 0.3), (1.12, 0.2)]
    tp = [(W * u, base - S * h * k.r.uniform(0.9, 1.1)) for u, h in tops]
    mass = k.smooth([(-W * 0.15, base + S * 0.08)] + tp + [(W * 1.15, base + S * 0.08)])
    k.shape(mass, tone=1, dark=3, angle=k.r.uniform(-6, 6))
    cid = _clip(k, mass)
    for (xa, ya), (xb, yb), (xc, yc) in zip(tp, tp[1:], tp[2:]):
        if yb < ya and yb < yc:       # a lump: shade its right flank
            lump = k.smooth([(xb - (xb - xa) * 0.1, yb), (xc, yc), (xc, base + 10), (xb + (xc - xb) * 0.1, base + 10)])
            k.shape(lump, tone=0, dark=4, outline=0, angle=k.r.uniform(55, 70), clip=cid, light=SIDE, knock=False)
            k.line(f'M{xb:.1f},{yb + 6:.1f} Q{xb + (xc - xb) * 0.1:.1f},{(yb + base) / 2:.1f} {xb - (xb - xa) * 0.05:.1f},{base:.1f}', 0.8, 0.8)
    fd = ''
    for i in range(46):
        xb = -W * 0.1 + W * 1.2 * i / 45
        fd += f'M{xb:.1f},{base + 10:.1f} Q{xb + k.r.uniform(-8, 8):.1f},{base - S * 0.15:.1f} {xb + k.r.uniform(-14, 14):.1f},{base - S * 0.42:.1f} '
    k.ink.append(f'<path d="{fd}" clip-path="url(#{cid})" stroke="#000" stroke-width="0.6" stroke-opacity="0.6" fill="none" filter="url(#rough)"/>')
    td = ''
    for _ in range(26):
        x = W * k.r.uniform(-0.05, 1.05); y = base - S * k.r.uniform(0.03, 0.3); L = S * k.r.uniform(0.03, 0.08)
        td += f'M{x:.1f},{y:.1f} q{L / 2:.1f},{S * 0.008:.1f} {L:.1f},0 '
    k.ink.append(f'<path d="{td}" clip-path="url(#{cid})" stroke="#000" stroke-width="0.7" fill="none" filter="url(#rough)"/>')
    for vx, vy in ((W * 0.08, base - S * 0.2), (W * 0.83, base - S * 0.22), (W * 0.3, base - S * 0.12)):
        k.solid(f'M{vx - S * 0.018:.1f},{vy:.1f} C{vx - S * 0.018:.1f},{vy - S * 0.03:.1f} {vx + S * 0.018:.1f},{vy - S * 0.03:.1f} {vx + S * 0.018:.1f},{vy:.1f}Z')
        k.line(f'M{vx - S * 0.03:.1f},{vy + S * 0.004:.1f} q{S * 0.03:.1f},{S * 0.012:.1f} {S * 0.06:.1f},0', 1.0)
    # the gate: a dark arch in a heavy rim of packed earth, two flanking buttresses
    gx, gy, gw = W * 0.5, base, S * 0.1
    for sx in (-1, 1):
        spire(k, gx + sx * gw * 1.25, gy + 4, gy - S * 0.22, S * 0.08, tone=1, dark=4, lean=sx * S * 0.01)
    rim = f'M{gx - gw * 1.1:.1f},{gy + 2:.1f} C{gx - gw * 1.15:.1f},{gy - gw * 1.6:.1f} {gx + gw * 1.15:.1f},{gy - gw * 1.6:.1f} {gx + gw * 1.1:.1f},{gy + 2:.1f}Z'
    k.shape(rim, tone=2, dark=4, angle=20, light=SIDE)
    gate = f'M{gx - gw * 0.8:.1f},{gy + 2:.1f} C{gx - gw * 0.85:.1f},{gy - gw * 1.2:.1f} {gx + gw * 0.85:.1f},{gy - gw * 1.2:.1f} {gx + gw * 0.8:.1f},{gy + 2:.1f}Z'
    k.solid(gate)
    k.line(f'M{gx - gw * 0.55:.1f},{gy - gw * 0.55:.1f} Q{gx - gw * 0.2:.1f},{gy - gw * 0.85:.1f} {gx + gw * 0.25:.1f},{gy - gw * 0.8:.1f}', 0.5, 0.5)
    road = ''
    for side in (-1, 1):
        for i in range(40):
            t = i / 39
            x = gx + side * W * (0.08 + 0.4 * t) + math.sin(t * 7) * S * 0.02
            y = gy - S * 0.01 + S * 0.05 * t * t
            road += f'M{x:.1f},{y:.1f} h{k.r.uniform(2, 4):.1f} '
    k.line(road, 1.3, 0.8, rough=False)
    glow(k, spec, gx, gy - S * 0.05, S * 0.3)
    # near: a ground rise, grass, pebbles, a leaf at the corner
    k.depth = 0.95
    ruled_ground(k, base + S * 0.04, wave=5, gap0=3, gap1=16, op=0.7)
    grass(k, -10, W * 0.3, H * (0.98 if P else 1.02), 50, S * 0.2, lean=0.25)
    grass(k, W * 0.75, W + 10, H * (0.98 if P else 1.02), 40, S * 0.18, lean=-0.25)
    pebbles(k, W * 0.3, W * 0.7, H * (0.9 if P else 0.95), H, 6, S * 0.025)
    quiet_bottom(k)


# =================================================================================================== temple
def crystal(k, x, y, h, w, tilt=0.0, tone=1, dark=2):
    """One hexagonal crystal prism from (x, y) up, tilted: three visible faces, a faceted tip, a glint on the lit face."""
    ca, sa = math.cos(tilt - math.pi / 2), math.sin(tilt - math.pi / 2)

    def P(u, v): return (x + ca * u - sa * v, y + sa * u + ca * v)

    sh = h * k.r.uniform(0.68, 0.8)          # where the shoulders of the tip start
    tipv = w * k.r.uniform(-0.12, 0.12)
    L, ML, MR, R = -w / 2, -w * 0.12, w * 0.22, w / 2
    tip = P(h, tipv)
    body = [P(0, L), P(sh, L), tip, P(sh, R), P(0, R)]
    k.shape(k.poly(body), tone=tone, dark=dark + 1, angle=math.degrees(tilt) + 20, light=SIDE)
    # the shadowed right face, denser
    k.shape(k.poly([P(0, MR), P(sh * 1.04, MR), tip, P(sh, R), P(0, R)]), tone=min(4, tone + 1), dark=4, outline=0.5,
            angle=math.degrees(tilt) + 75, light=SIDE)
    a, b = P(0, ML), P(sh * 1.06, ML)
    c, e = P(0, MR), P(sh * 1.04, MR)
    k.line(f'M{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f} L{tip[0]:.1f},{tip[1]:.1f} M{c[0]:.1f},{c[1]:.1f} L{e[0]:.1f},{e[1]:.1f} '
           f'M{P(sh, L)[0]:.1f},{P(sh, L)[1]:.1f} L{b[0]:.1f},{b[1]:.1f} L{e[0]:.1f},{e[1]:.1f} L{P(sh, R)[0]:.1f},{P(sh, R)[1]:.1f}', 0.8)
    # growth lines across the faces
    gd = ''
    for f in (0.2, 0.42, 0.6):
        p0, p1, p2, p3 = P(sh * f, L), P(sh * f + w * 0.03, ML), P(sh * f + w * 0.02, MR), P(sh * f - w * 0.02, R)
        gd += f'M{p0[0]:.1f},{p0[1]:.1f} L{p1[0]:.1f},{p1[1]:.1f} L{p2[0]:.1f},{p2[1]:.1f} L{p3[0]:.1f},{p3[1]:.1f} '
    k.line(gd, 0.45, 0.6, rough=False)
    g0, g1 = P(h * 0.12, -w * 0.32), P(sh * 0.95, -w * 0.32)
    k.ink.append(f'<path d="M{g0[0]:.1f},{g0[1]:.1f} L{g1[0]:.1f},{g1[1]:.1f}" stroke="#fff" stroke-width="{max(1.4, w * 0.07):.1f}" stroke-linecap="round"/>')


def drape(k, x0, y0, x1, y1, sag, w=0.6, op=0.9, beads=False):
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2 + sag * 2
    k.ink.append(f'<path d="M{x0:.1f},{y0:.1f} Q{mx:.1f},{my:.1f} {x1:.1f},{y1:.1f}" stroke="#000" stroke-width="{w * (0.5 + 0.6 * k.depth):.2f}" stroke-opacity="{op}" fill="none"/>')
    if beads:
        dots = ''
        for i in range(1, 12):
            t = i / 12
            px = (1 - t) ** 2 * x0 + 2 * (1 - t) * t * mx + t * t * x1; py = (1 - t) ** 2 * y0 + 2 * (1 - t) * t * my + t * t * y1
            dots += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="{k.r.uniform(1, 1.8):.1f}" fill="#fff" stroke="#000" stroke-width=".5"/>'
        k.ink.append(dots)


def sheet_web(k, cx, cy, R, a0, a1, n=9):
    """A fan of web in a corner: spokes from (cx, cy) between angles a0..a1, with sagging cross threads."""
    angs = [a0 + (a1 - a0) * i / (n - 1) for i in range(n)]
    d = ''
    for a in angs:
        d += f'M{cx:.1f},{cy:.1f} L{cx + math.cos(a) * R:.1f},{cy + math.sin(a) * R:.1f} '
    t = 0.15
    while t < 1:
        for a, b in zip(angs, angs[1:]):
            pa = (cx + math.cos(a) * R * t, cy + math.sin(a) * R * t); pb = (cx + math.cos(b) * R * t, cy + math.sin(b) * R * t)
            m = ((pa[0] + pb[0]) / 2 - (pa[0] + pb[0] - 2 * cx) * 0.03, (pa[1] + pb[1]) / 2 - (pa[1] + pb[1] - 2 * cy) * 0.03)
            d += f'M{pa[0]:.1f},{pa[1]:.1f} Q{m[0]:.1f},{m[1]:.1f} {pb[0]:.1f},{pb[1]:.1f} '
        t += 0.09 + t * 0.05
    k.line(d, 0.45, 0.8, rough=False)


def temple(k, spec):
    W, H = k.w, k.h; P = _portrait(k); S = min(W, H)
    night = _night(spec)
    fl = H * (0.66 if P else 0.82)
    cx = W * 0.5
    cool = _warm_cool(spec)[1]
    washes(k, spec, [(cx, H * 0.38, W * 0.32, H * 0.25, 1, 0.6), (cx, fl - H * 0.04, W * 0.4, H * 0.08, 0, 0.5),
                     (W * 0.2, H * 0.2, W * 0.2, H * 0.2, 0, 0.3)])
    # far: the back wall of the hall, ruled, cracked, with an oculus to the sky
    k.depth = 0.15
    back = k.poly([(-10, -10), (W + 10, -10), (W + 10, fl), (-10, fl)])
    k.shape(back, tone=2 if night else 1, dark=3, outline=0, angle=2)
    cd = ''
    for _ in range(36):
        x = k.r.uniform(0, W); y = k.r.uniform(0, fl); L = S * k.r.uniform(0.04, 0.14)
        cd += f'M{x:.1f},{y:.1f} l{k.r.uniform(-8, 8):.1f},{L * 0.4:.1f} l{k.r.uniform(-8, 8):.1f},{L * 0.6:.1f} '
    k.line(cd, 0.7, 0.6)
    ox, oy, orr = cx, H * (0.1 if P else 0.12), S * 0.09
    k.paper(k.blob(ox, oy, orr, orr * 0.8, 16, 0.05))
    if night:
        k.ink.append(f'<rect x="{ox - orr:.0f}" y="{oy - orr:.0f}" width="{orr * 2:.0f}" height="{orr * 2:.0f}" fill="url(#{k.hatch(90, 3.0, 0.6)})" clip-path="url(#{_clip(k, k.blob(ox, oy, orr, orr * 0.8, 16, 0.05))})"/>')
        stars(k, ox - orr, ox + orr, oy - orr * 0.7, oy + orr * 0.7, 14)
    k.line(k.blob(ox, oy, orr, orr * 0.8, 16, 0.05), 1.0)
    rays(k, ox, oy + orr, orr * 0.2, H * 0.4, 12, math.pi * 0.35, math.pi * 0.65, 0.5, 0.25)
    # floor and the stepped dais
    ruled_ground(k, fl, wave=0, gap0=2.5, gap1=14, op=0.6)
    furrows(k, cx, fl - S * 0.4, fl + 2, H, 13, W * 2.6, 0.5, 0.4)
    dw = S * 0.36
    for i in range(3, -1, -1):
        sw = dw * (1 + i * 0.35); y = fl + S * 0.035 * i - S * 0.05
        k.shape(k.poly([(cx - sw / 2, y), (cx + sw / 2, y), (cx + sw / 2 + S * 0.025, y + S * 0.035), (cx - sw / 2 - S * 0.025, y + S * 0.035)]),
                tone=1, dark=2, angle=90)
        k.shape(k.poly([(cx - sw / 2 - S * 0.025, y + S * 0.035), (cx + sw / 2 + S * 0.025, y + S * 0.035), (cx + sw / 2 + S * 0.025, y + S * 0.045),
                        (cx - sw / 2 - S * 0.025, y + S * 0.045)]), tone=3, dark=4, angle=0)
    # webs strung across the hall: sagging cables with fringes of beaded threads, two great orbs high in the vault
    k.depth = 0.35
    for i in range(3):
        y0 = H * (0.16 + i * 0.07) if P else H * (0.2 + i * 0.12)
        x0, x1 = W * 0.08, W * 0.92; sag = S * k.r.uniform(0.04, 0.08)
        drape(k, x0, y0, x1, y0 + k.r.uniform(-10, 10), sag, 0.7, 0.7)
        fd, beads = '', ''
        for j in range(40):
            tt = (j + k.r.uniform(0, 1)) / 40
            if 0.36 < tt < 0.64 and i > 0:
                continue          # keep the middle open over the crystal
            px = x0 + (x1 - x0) * tt; py = y0 + 4 * sag * tt * (1 - tt)
            L = S * k.r.uniform(0.02, 0.12) * (1.4 - abs(tt - 0.5))
            fd += f'M{px:.1f},{py:.1f} q{k.r.uniform(-3, 3):.1f},{L / 2:.1f} {k.r.uniform(-2, 2):.1f},{L:.1f} '
            beads += f'<circle cx="{px:.1f}" cy="{py + L:.1f}" r="{k.r.uniform(1.0, 2.0):.1f}" fill="#fff" stroke="#000" stroke-width=".5"/>'
        k.line(fd, 0.45, 0.7, rough=False)
        k.ink.append(beads)
    for wx, a0 in ((W * 0.2, 0), (W * 0.8, 1)):
        R = S * (0.13 if P else 0.12); wy = H * (0.22 if P else 0.3)
        sheet_web(k, wx, wy, R, 0, TAU * 0.999, 16)
    # the crystal centrepiece, light radiating from it
    k.depth = 0.5
    ch = S * (0.46 if P else 0.6)
    soften(k, cx, fl - ch * 0.5, ch * 0.95, 0.8)
    rays(k, cx, fl - ch * 0.55, ch * 0.35, ch * 1.5, 44, w=0.5, op=0.3)
    base = fl - S * 0.05
    for dx, hh, ww, tl in ((-0.24, 0.38, 0.13, -0.5), (0.25, 0.44, 0.14, 0.45), (-0.11, 0.68, 0.17, -0.2), (0.13, 0.6, 0.16, 0.22), (0.0, 1.0, 0.21, 0.02)):
        crystal(k, cx + dx * ch, base, ch * hh, ch * ww, tl)
    pebbles(k, cx - ch * 0.35, cx + ch * 0.35, base - 4, base + 6, 7, ch * 0.05)
    k.watercolour(cx, fl - ch * 0.5, ch * 0.45, ch * 0.6, cool, 0.55, 3)
    glow(k, spec, cx, fl - ch * 0.45, S * 0.35)
    # near: the cave mouth arching over, stalactites along its lip, webs in its corners
    k.depth = 0.95
    t = 0.1 if P else 0.13
    top = H * (0.05 if P else 0.08)
    mouth = []
    for i in range(29):           # left foot, up the wall, over the vault, down the right wall
        a = math.pi + math.pi * i / 28
        x = cx + math.cos(a) * W * (0.5 - t)
        y = (H * 0.55 if P else H * 0.62) + math.sin(a) * ((H * 0.55 if P else H * 0.62) - top)
        mouth.append((x + k.r.uniform(-1, 1) * S * 0.02, y + k.r.uniform(-1, 1) * S * 0.015))
    mouth = [(W * t * 0.7, H + 20), (W * t * 1.1, H * 0.85)] + mouth + [(W * (1 - t * 1.1), H * 0.85), (W * (1 - t * 0.7), H + 20)]
    frame = f'M-30,-30 L{W + 30},-30 L{W + 30},{H + 30} L-30,{H + 30}Z ' + k.smooth(mouth[::-1], close=True)
    k.shape(frame, tone=3 if night else 2, dark=4, angle=70, outline=1.4)
    cid = _clip(k, f'M-30,-30 L{W + 30},-30 L{W + 30},{H + 30} L-30,{H + 30}Z')
    cd = ''
    for f in (1.06, 1.14, 1.25, 1.4):
        pts = [(cx + (x - cx) * f + k.r.uniform(-6, 6), (H * 0.6) + (y - H * 0.6) * f + k.r.uniform(-6, 6)) for x, y in mouth[2:-2]]
        for j in range(0, len(pts) - 4, 5):
            seg = pts[j:j + k.r.randint(3, 6)]
            if len(seg) > 2:
                cd += k.smooth(seg, close=False) + ' '
    k.ink.append(f'<path d="{cd}" stroke="#000" stroke-width="0.8" stroke-opacity="0.8" fill="none" filter="url(#rough)"/>')
    for x, y in mouth[3:-3]:
        if y < (H * 0.32 if P else H * 0.4) and k.r.random() < 0.8:
            drip(k, x, y, S * k.r.uniform(0.04, 0.16), S * k.r.uniform(0.015, 0.035))
    k.depth = 0.7
    for i in range(3):
        y0 = H * (0.2 + i * 0.06) if P else H * (0.28 + i * 0.1)
        drape(k, W * (t + 0.03), y0, W * (1 - t - 0.03), y0 + k.r.uniform(-10, 10), S * k.r.uniform(0.04, 0.09), 0.6, 0.6, beads=(i % 2 == 0))
    sheet_web(k, W * (t + 0.02), H * (0.22 if P else 0.32), S * 0.28, -0.6, 0.9)
    sheet_web(k, W * (1 - t - 0.02), H * (0.22 if P else 0.32), S * 0.28, math.pi - 0.9, math.pi + 0.6)
    if spec.get('light') == 'firelight':     # braziers at the foot of the walls
        for x in (W * 0.2, W * 0.8):
            glow(k, spec, x, fl - S * 0.05, S * 0.2)
    quiet_bottom(k)


# ================================================================================================ silk-city
def qpt(p0, c, p1, t):
    return ((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t * t * p1[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t * t * p1[1])


def silk_bridge(k, x0, y0, x1, y1, sag, rise, deck=4.0, n=14):
    """A silk suspension bridge: a plank deck slung between anchors, a cable above it, hangers between."""
    m = ((x0 + x1) / 2, (y0 + y1) / 2)
    dp0, dp1 = (x0, y0), (x1, y1); dc = (m[0], m[1] + sag * 2)
    cp0, cp1 = (x0, y0 - rise), (x1, y1 - rise); cmid = (m[0], m[1] + sag - rise * 0.15)
    cc = (2 * cmid[0] - (cp0[0] + cp1[0]) / 2, 2 * cmid[1] - (cp0[1] + cp1[1]) / 2)
    top = [qpt(dp0, dc, dp1, i / 20) for i in range(21)]
    bot = [(x, y + deck) for x, y in top]
    k.shape(k.poly(top + bot[::-1]), tone=2, dark=3, outline=0.8, angle=20)
    k.ink.append(f'<path d="M{cp0[0]:.1f},{cp0[1]:.1f} Q{cc[0]:.1f},{cc[1]:.1f} {cp1[0]:.1f},{cp1[1]:.1f}" stroke="#000" stroke-width="{0.6 + 0.8 * k.depth:.2f}" fill="none"/>')
    hd = ''
    for i in range(1, n):
        t = i / n
        a = qpt(cp0, cc, cp1, t); b = qpt(dp0, dc, dp1, t)
        if b[1] - a[1] > 2:
            hd += f'M{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f} '
    k.line(hd, 0.45, 0.85, rough=False)
    # loose threads drooping under the deck
    for _ in range(2):
        t0 = k.r.uniform(0.1, 0.5); t1 = t0 + k.r.uniform(0.15, 0.4)
        a = qpt(dp0, dc, dp1, t0); b = qpt(dp0, dc, dp1, min(t1, 0.95))
        drape(k, a[0], a[1] + deck, b[0], b[1] + deck, abs(b[0] - a[0]) * 0.12, 0.4, 0.6)


def cocoon(k, x, y, h, w, tone=1, dark=3, lean=0.0):
    """A hanging spindle tower of woven silk: banded rings, a gallery of small slit openings, threads to its anchor."""
    def half(t): return w / 2 * (math.sin(math.pi * t) ** 0.65) * (1.1 - 0.25 * t)
    ts = [i / 12 for i in range(13)]
    cx = lambda t: x + lean * t
    left = [(cx(t) - half(t) * k.r.uniform(0.95, 1.05), y + h * t) for t in ts]
    right = [(cx(t) + half(t) * k.r.uniform(0.95, 1.05), y + h * t) for t in ts[1:-1]]
    d = k.smooth(left + right[::-1])
    k.shape(d, tone=tone, dark=dark, angle=k.r.uniform(60, 80), light=SIDE)
    bd = ''
    for t in (0.18, 0.3, 0.44, 0.58, 0.72, 0.85):
        hw = half(t); yy = y + h * t
        bd += f'M{cx(t) - hw:.1f},{yy:.1f} Q{cx(t):.1f},{yy + hw * 0.35:.1f} {cx(t) + hw:.1f},{yy:.1f} '
    k.line(bd, 0.6, 0.85)
    if w > 12:
        t = k.r.choice((0.37, 0.51)); hw = half(t); yy = y + h * t
        sd = ''
        for j in range(5):
            u = -0.65 + j * 0.3
            if abs(u) < 0.8:
                px = cx(t) + u * hw; py = yy + hw * 0.35 * (1 - u * u) - h * 0.02
                sd += f'M{px:.1f},{py:.1f} v{h * 0.045:.1f} '
        k.ink.append(f'<path d="{sd}" stroke="#000" stroke-width="{max(1.2, w * 0.05):.1f}" stroke-linecap="round" fill="none"/>')
    k.line(f'M{x:.1f},{y:.1f} L{x - w * 0.02:.1f},{y - h * 0.15:.1f}', 0.6, rough=False)
    k.line(f'M{cx(1):.1f},{y + h:.1f} q{w * 0.1:.1f},{h * 0.2:.1f} {-w * 0.05:.1f},{h * 0.4:.1f}', 0.5, 0.8, rough=False)
    return d


def collar(k, x, y, tw, w, tone=2, dark=4):
    """A woven silk collar wrapped round a trunk at (x, y): a flared skirt with guy threads up to the bark."""
    skirt = k.smooth([(x - tw * 0.55, y - w * 0.12), (x + tw * 0.55, y - w * 0.12), (x + w * 0.5, y + w * 0.12), (x + w * 0.42, y + w * 0.2),
                      (x, y + w * 0.24), (x - w * 0.42, y + w * 0.2), (x - w * 0.5, y + w * 0.12)])
    k.shape(skirt, tone=tone, dark=dark, angle=10, light=SIDE)
    rd = ''
    for i in range(9):
        u = -1 + 2 * i / 8
        rd += f'M{x + u * tw * 0.5:.1f},{y - w * 0.1:.1f} L{x + u * w * 0.46:.1f},{y + w * 0.16 + w * 0.06 * (1 - u * u):.1f} '
    k.line(rd, 0.5, 0.7)
    gd = ''
    for s_ in (-1, 1):
        for j in range(3):
            gd += f'M{x + s_ * w * (0.48 - j * 0.1):.1f},{y + w * 0.12:.1f} L{x + s_ * tw * 0.4:.1f},{y - w * (0.7 + j * 0.25):.1f} '
    k.line(gd, 0.4, 0.7, rough=False)


def silk_city(k, spec):
    W, H = k.w, k.h; P = _portrait(k); S = min(W, H)
    washes(k, spec, [(W * 0.5, H * 0.3, W * 0.4, H * 0.25, 0, 0.55), (W * 0.3, H * 0.12, W * 0.35, H * 0.12, 1, 0.5),
                     (W * 0.72, H * 0.55, W * 0.25, H * 0.15, 1, 0.4)])
    if _night(spec):
        ruled_sky(k, spec, H * 0.7)
    else:
        for i in range(6):
            x = W * (-0.1 + i * 0.2) + k.r.uniform(-15, 15)
            k.line(f'M{x:.0f},0 L{x + W * 0.3:.0f},{H * 0.75:.0f}', 0.5, 0.15, rough=False)
    # far: faint trunks, strung with bridges and hung with towers, lost in haze below
    k.depth = 0.1
    fx = [W * (f + k.r.uniform(-0.02, 0.02)) for f in (0.04, 0.17, 0.31, 0.44, 0.57, 0.7, 0.83, 0.96)]
    for x in fx:
        k.shape(trunk(k, x, S * 0.028, -20, H * 0.9, lean=k.r.uniform(-6, 6)), tone=1, dark=2, outline=0.5, angle=4)
    for a, b in zip(fx, fx[1:]):
        for y in sorted(H * k.r.uniform(lo, hi) for lo, hi in ((0.14, 0.24), (0.32, 0.44), (0.52, 0.66))):
            silk_bridge(k, a, y, b, y + k.r.uniform(-15, 15), S * 0.018, S * 0.01, deck=1.4, n=7)
        for _ in range(2):
            if k.r.random() < 0.75:
                cocoon(k, k.r.uniform(a, b), H * k.r.uniform(0.2, 0.55), S * k.r.uniform(0.07, 0.11), S * 0.025, tone=1, dark=2)
    soften(k, W * 0.5, H * (0.95 if P else 1.1), S * 0.6, 0.7)
    # mid: two trunks with collars, bridges, hanging towers
    k.depth = 0.5
    k.shape(k.foliage(-40, W + 40, H * (0.08 if P else 0.12), 30, 14), tone=2, dark=3, outline=1.0)
    k.leafmarks(0, W, 0, H * 0.08, 100)
    mx = [W * 0.24, W * 0.76]
    for x in mx:
        k.shape(trunk(k, x, S * 0.07, -20, H + 20, lean=k.r.uniform(-8, 8)), tone=2, dark=3, angle=4, light=SIDE)
        bark(k, x, S * 0.06, 0)
    silk_bridge(k, mx[0], H * 0.3, mx[1], H * 0.3, S * 0.05, S * 0.03, deck=3)
    silk_bridge(k, mx[0], H * 0.55, mx[1], H * 0.56, S * 0.035, S * 0.025, deck=3)
    silk_bridge(k, -20, H * 0.42, mx[0], H * 0.44, S * 0.025, S * 0.02, deck=2.5)
    silk_bridge(k, mx[1], H * 0.47, W + 20, H * 0.43, S * 0.025, S * 0.02, deck=2.5)
    for x in mx:
        for y in (H * 0.3, H * 0.55):
            collar(k, x, y + S * 0.01, S * 0.07, S * 0.13)
    cocoon(k, W * 0.36, H * 0.3 + S * 0.07, S * 0.2, S * 0.06, tone=1, dark=3)
    cocoon(k, W * 0.66, H * 0.3 + S * 0.07, S * 0.16, S * 0.05, tone=1, dark=3)
    cocoon(k, W * 0.12, H * 0.45, S * 0.18, S * 0.055, tone=1, dark=3)
    cocoon(k, W * 0.88, H * 0.47, S * 0.15, S * 0.05, tone=1, dark=3)
    cocoon(k, W * 0.33, H * 0.56 + S * 0.04, S * 0.12, S * 0.04, tone=1, dark=3)
    for x in mx:          # towers clustered on the trunks themselves, like seed pods
        for j in range(3):
            side = (-1) ** j
            cocoon(k, x + side * S * 0.05, H * (0.36 + 0.12 * j) - S * 0.02, S * k.r.uniform(0.09, 0.14), S * k.r.uniform(0.035, 0.05),
                   tone=1, dark=3, lean=side * S * 0.01)
    if spec.get('light') == 'firelight':
        for x, y in ((W * 0.12, H * 0.45), (W * 0.86, H * 0.55)):
            smoke(k, x, y, H * 0.3, S * 0.03, S * 0.08, tone=1, dark=3)
        glow(k, spec, W * 0.5, H * 0.58, S * 0.3)
        glow(k, spec, W * 0.15, H * 0.5, S * 0.18)
    else:
        glow(k, spec, W * 0.5, H * 0.45, S * 0.3)
    # near: great framing trunks, the main bridge across the top, a big tower at the right, anchor threads
    k.depth = 0.95
    nx = [(W * 0.02, S * 0.2, 16), (W * 0.98, S * 0.22, -18)]
    for x, w, lean in nx:
        k.shape(trunk(k, x, w, -20, H + 20, lean), tone=2, dark=4, angle=4, light=SIDE)
        bark(k, x, w, lean)
    y0 = H * (0.12 if P else 0.18)
    silk_bridge(k, W * 0.08, y0, W * 0.92, y0 + 8, S * 0.07, S * 0.06, deck=6, n=18)
    cocoon(k, W * 0.86, y0 + S * 0.12, S * 0.36, S * 0.1, tone=2, dark=4, lean=-S * 0.02)
    for a, b in (((W * 0.1, H * 0.3), (W * 0.4, H * 0.8)), ((W * 0.9, H * 0.4), (W * 0.62, H * 0.9)), ((W * 0.08, H * 0.6), (W * 0.3, H * 1.0))):
        k.line(f'M{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f}', 0.5, 0.6, rough=False)
    sheet_web(k, W * 0.08, H * (0.66 if P else 0.7), S * 0.25, -0.9, 0.5, 7)
    corner_foliage(k, 1, W * (0.45 if P else 0.3), H * (0.07 if P else 0.14))
    quiet_bottom(k)


# ================================================================================================== tunnels
def _ring_pts(k, cx, cy, rx, ry, floor, n=28, jit=0.06):
    pts = []
    for i in range(n):
        a = -math.pi / 2 + i / n * TAU
        s = 1 + k.r.uniform(-jit, jit)
        x, y = cx + math.cos(a) * rx * s, cy + math.sin(a) * ry * s
        pts.append((x, min(y, cy + ry * floor)))
    return pts


def tunnels(k, spec):
    W, H = k.w, k.h; P = _portrait(k); S = min(W, H)
    night = _night(spec); L = spec.get('light')
    vx, vy = W * 0.5, H * (0.42 if P else 0.5)          # far end of the tunnel
    warm, cool = _warm_cool(spec)
    washes(k, spec, [(vx, vy, S * 0.22, S * 0.2, 0, 0.6), (vx, vy + S * 0.25, W * 0.4, S * 0.15, 1, 0.45),
                     (W * 0.18, H * 0.3, W * 0.2, H * 0.2, 1, 0.3)])
    # sections from the far end outward; floor y and size grow together in perspective
    scales = [0.06, 0.1, 0.16, 0.25, 0.38, 0.56, 0.8, 1.15]
    rx0, ry0 = (W * 0.85, H * 1.0) if P else (W * 0.5, H * 1.05)
    fall = H * (0.55 if P else 0.42)
    secs = []
    for i, s_ in enumerate(scales):
        cx = vx + W * 0.04 * math.sin(i * 1.3) * s_
        fy = vy + fall * s_
        secs.append((cx, fy, _arch_pts(k, cx, fy, rx0 * s_, ry0 * s_, jit=0.04 + 0.03 * s_)))
    # far end: a pale opening
    k.depth = 0.1
    c0 = secs[0][2]
    k.shape(k.smooth(c0 + [(c0[-1][0], secs[0][1] + 2), (c0[0][0], secs[0][1] + 2)]), tone=2 if night else 0, dark=2 if night else 1, outline=0.6)
    # the floor: ruled in perspective from the far end to the frame foot, with ruts converging on the far end
    k.depth = 0.5
    fl = k.poly([(c0[0][0], secs[0][1]), (c0[-1][0], secs[0][1]), (W * 1.6, H + 20), (-W * 0.6, H + 20)])
    k.paper(fl)
    cid = _clip(k, fl)
    out = ''; y = secs[0][1]
    while y < H:
        t = (y - secs[0][1]) / (H - secs[0][1])
        xs = -20 - k.r.uniform(0, 50)
        while xs < W + 20:
            seg = k.r.uniform(15, 120); out += f'M{xs:.1f},{y:.1f} h{seg:.1f} '
            xs += seg + k.r.uniform(3, 12) + t * 30
        y += 2.2 + 18 * t ** 1.2
    k.ink.append(f'<path d="{out}" clip-path="url(#{cid})" stroke="#000" stroke-width="0.6" stroke-opacity="{0.9 if night else 0.65}" fill="none" filter="url(#rough)"/>')
    furrows(k, vx, secs[0][1], secs[0][1] + 2, H, 9, W * 2.2, 0.6, 0.5)
    # wall bands, far to near, hatched along the curve of the bore, darker toward the viewer
    for i in range(len(secs) - 1):
        k.depth = 0.12 + 0.85 * i / (len(secs) - 2)
        (_, fa, inner), (_, fb, outer) = secs[i], secs[i + 1]
        band = k.smooth(outer, close=False) + ' L' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in [(inner[-1][0], fa)] ) + ' ' + \
            k.smooth(inner[::-1], close=False).replace('M', 'L', 1) + f' L{outer[0][0]:.1f},{fb:.1f}Z'
        tone = min(4, 1 + (i >= 4) + (1 if night else 0))
        k.shape(band, tone=tone, dark=min(4, tone + 2), angle=(25 + i * 37) % 180, outline=0.5 + 0.15 * i)
        bcid = _clip(k, band)
        cd = ''
        for f in (0.2, 0.4, 0.6, 0.8):     # contour lines following the bore
            pts = [(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f) for a, b in zip(inner, outer)]
            j0 = k.r.randrange(0, 5); j1 = k.r.randrange(len(pts) - 5, len(pts))
            cd += k.smooth(pts[j0:j1], close=False) + ' '
        k.ink.append(f'<path d="{cd}" clip-path="url(#{bcid})" stroke="#000" stroke-width="{0.4 + 0.5 * k.depth:.2f}" stroke-opacity="0.8" fill="none" filter="url(#rough)"/>')
        md = ''
        for _ in range(4 + i * 3):          # pick and claw marks left by the diggers
            j = k.r.randrange(2, len(inner) - 2); f = k.r.uniform(0.2, 0.8)
            px = inner[j][0] + (outer[j][0] - inner[j][0]) * f; py = inner[j][1] + (outer[j][1] - inner[j][1]) * f
            sz = S * 0.008 * (1 + i)
            md += f'M{px:.1f},{py:.1f} l{sz * 0.5:.1f},{sz:.1f} M{px + sz * 0.4:.1f},{py - sz * 0.1:.1f} l{sz * 0.5:.1f},{sz:.1f} '
        k.line(md, 0.7, 0.8)
        if i == 3:
            a, b = inner[4], outer[4]
            ox, oy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + S * 0.02
            gy = fa + (fb - fa) * 0.5; gw = S * 0.032
            k.shape(f'M{ox - gw * 1.5:.1f},{gy:.1f} C{ox - gw * 1.6:.1f},{gy - gw * 2.6:.1f} {ox + gw * 1.6:.1f},{gy - gw * 2.6:.1f} {ox + gw * 1.5:.1f},{gy:.1f}Z',
                    tone=3, dark=4, outline=0.9)
            k.solid(f'M{ox - gw:.1f},{gy:.1f} C{ox - gw * 1.05:.1f},{gy - gw * 1.9:.1f} {ox + gw * 1.05:.1f},{gy - gw * 1.9:.1f} {ox + gw:.1f},{gy:.1f}Z')
        if i >= 2:
            for _ in range(2 + i // 2):
                px = k.r.uniform(inner[0][0], inner[-1][0]); py = k.r.uniform(fa, fb); sz = S * 0.004 * i * k.r.uniform(0.5, 1.2)
                k.shape(k.blob(px, py, sz, sz * 0.45, 9, 0.25), tone=2, dark=4, outline=0.6)
    # the nearest frame: everything outside the last section is earth
    k.depth = 0.95
    last = secs[-1][2]
    frame = f'M-40,-40 L{W + 40},-40 L{W + 40},{H + 40} L-40,{H + 40}Z ' + k.smooth(last[::-1] + [(last[0][0], H + 40), (last[-1][0], H + 40)][::-1], close=True)
    k.shape(frame, tone=3 if not night else 4, dark=4, angle=70, outline=1.3)
    # roots through the roof: fine, forking, hanging
    for _ in range(12):
        idx = k.r.randrange(3, len(secs)); sec = secs[idx][2]; s_ = scales[idx]
        j = k.r.randrange(6, len(sec) - 6)
        x0, y0 = sec[j]
        Lr = S * k.r.uniform(0.15, 0.35) * s_
        pts = [(x0, y0 - 2)]
        for q in range(1, 6):
            pts.append((pts[-1][0] + k.r.uniform(-1, 1) * Lr * 0.12, y0 + Lr * q / 5))
        k.solid(tapered(k, pts, S * 0.0035 * (0.4 + s_), S * 0.0006))
        bd = ''
        for q in (2, 3, 4):
            px, py = pts[q]; side = k.r.choice((-1, 1))
            bd += f'M{px:.1f},{py:.1f} q{side * Lr * 0.1:.1f},{Lr * 0.1:.1f} {side * Lr * 0.15:.1f},{Lr * 0.3:.1f} '
        k.line(bd, 0.4, 0.9, rough=False)
    # light: day comes down the bore from the far end; firelight is a torch on the wall; night is near-dark
    if L in ('day', 'dawn', 'dusk'):
        soften(k, vx, vy, S * 0.32, 0.75)
        rays(k, vx, vy, S * 0.06, S * 0.5, 30, w=0.45, op=0.25)
        k.watercolour(vx, vy, S * 0.12, S * 0.1, warm, 0.6, 3)
    elif L == 'firelight':
        tx, ty = secs[5][2][5]
        glow(k, spec, tx + S * 0.05, ty + S * 0.05, S * 0.35)
    elif L == 'screen-glow':
        glow(k, spec, vx, vy, S * 0.3)
    else:
        soften(k, vx, vy, S * 0.16, 0.5)
    quiet_bottom(k)


def curtain(k, x, y0, y1, w, slant=0.3, n=60):
    """A rain curtain: dense slanted strokes hanging from a cloud base, thinning toward the ground."""
    d = ''
    for _ in range(n):
        t = k.r.random() ** 1.6
        xx = x + k.r.uniform(-w / 2, w / 2) * (1 - 0.3 * t); yy = y0 + (y1 - y0) * t
        l = (y1 - y0) * k.r.uniform(0.15, 0.4)
        d += f'M{xx + (yy - y0) * slant:.1f},{yy:.1f} l{l * slant:.1f},{l:.1f} '
    k.ink.append(f'<path d="{d}" stroke="#000" stroke-width="0.7" stroke-opacity="0.55" fill="none" filter="url(#rough)"/>')


def mammatus(k, x0, x1, y, r, tone=2, dark=4):
    """The hanging pouches under a storm ceiling."""
    x = x0
    while x < x1:
        rr = r * k.r.uniform(0.7, 1.3)
        k.shape(lobed(k, x, y + k.r.uniform(-r, r) * 0.4, rr, rr * 0.75, k.r.randint(6, 8), (0.25, 0.45)), tone=tone, dark=dark, angle=k.r.uniform(30, 60))
        x += rr * k.r.uniform(1.2, 1.7)


def windtree(k, x, gl, h, lean):
    """A small tree bent by the wind, its crown streaming downwind."""
    k.shape(trunk(k, x, h * 0.1, gl - h * 0.8, gl + 4, lean=lean * h * 0.5), tone=2, dark=4)
    cx = x + lean * h * 0.55
    for i in range(3):
        crown(k, cx + lean * h * 0.18 * i, gl - h * (0.85 - 0.06 * i), h * (0.3 - 0.05 * i), h * 0.18, 7, tone=3, dark=4, marks=False)
    k.leafmarks(cx - h * 0.2, cx + lean * h * 0.5, gl - h, gl - h * 0.75, 12)


def banner(k, x, y, h, w, tone=1, dark=3):
    """A long sheet of woven silk hung from the vault: waved edges, folds, a frayed tail of threads."""
    n = 8
    left = [(x - w / 2 + math.sin(i * 1.3) * w * 0.06 - w * 0.06 * i / n, y + h * i / n) for i in range(n + 1)]
    right = [(x + w / 2 + math.sin(i * 1.1 + 1) * w * 0.06 + w * 0.04 * i / n, y + h * i / n) for i in range(n + 1)]
    tail = [(left[-1][0] + (right[-1][0] - left[-1][0]) * u, y + h + (w * 0.35 if 0 < u < 1 else 0) * math.sin(math.pi * u) * k.r.uniform(0.6, 1.2))
            for u in (0, 0.25, 0.5, 0.75, 1)]
    d = k.smooth(left + tail[1:-1][::-1][::-1] + right[::-1])
    k.shape(d, tone=tone, dark=dark, angle=k.r.uniform(-5, 5), light=SIDE)
    fd = ''
    for f in (0.22, 0.45, 0.68):
        pts = [(l[0] + (r[0] - l[0]) * f + math.sin(i * 0.9 + f * 7) * w * 0.05, l[1]) for i, (l, r) in enumerate(zip(left, right))]
        fd += k.smooth(pts, close=False) + ' '
    k.line(fd, 0.6, 0.6)
    hd = ''
    for f in (0.06, 0.1, 0.84, 0.88):      # woven hems with a zigzag band between
        i = f * n; l, r = left[int(i)], right[int(i)]; yy = y + h * f
        hd += f'M{l[0]:.1f},{yy:.1f} L{r[0]:.1f},{yy:.1f} '
    for f0 in (0.06, 0.84):
        i = int(f0 * n); l, r = left[i], right[i]; y0 = y + h * f0; m = 7
        hd += 'M' + ' L'.join(f'{l[0] + (r[0] - l[0]) * j / m:.1f},{y0 + (h * 0.04 if j % 2 else 0):.1f}' for j in range(m + 1)) + ' '
    k.line(hd, 0.7, 0.9)
    td = ''
    for _ in range(9):
        u = k.r.uniform(0.1, 0.9); px = left[-1][0] + (right[-1][0] - left[-1][0]) * u; py = y + h + w * 0.3 * math.sin(math.pi * u)
        td += f'M{px:.1f},{py - 4:.1f} q{k.r.uniform(-5, 5):.1f},{w * 0.4:.1f} {k.r.uniform(-8, 8):.1f},{w * k.r.uniform(0.4, 1.0):.1f} '
    k.line(td, 0.45, 0.8, rough=False)


def drip(k, x, y, L, w, tone=2, dark=4):
    """A stalactite hanging from (x, y)."""
    bend = k.r.uniform(-0.15, 0.15) * L
    pts = [(x - w / 2, y - 6), (x - w * 0.35, y + L * 0.3), (x - w * 0.12 + bend * 0.6, y + L * 0.75), (x + bend, y + L),
           (x + w * 0.15 + bend * 0.6, y + L * 0.72), (x + w * 0.4, y + L * 0.3), (x + w / 2, y - 6)]
    k.shape(k.smooth(pts), tone=tone, dark=dark, angle=k.r.uniform(-8, 8), outline=0.8, light=SIDE)
    k.line(f'M{x - w * 0.15:.1f},{y + L * 0.1:.1f} q{-w * 0.05:.1f},{L * 0.3:.1f} {bend * 0.5 + w * 0.02:.1f},{L * 0.55:.1f}', 0.5, 0.7)


def _arch_pts(k, cx, fy, rx, ry, n=22, jit=0.05):
    """A tunnel cross-section from the left floor corner, up and over, to the right floor corner."""
    pts = []
    for i in range(n + 1):
        a = math.pi + math.pi * i / n
        s = 1 + (k.r.uniform(-jit, jit) if 0 < i < n else 0)
        y = fy + math.sin(a) * ry * s
        x = cx + math.cos(a) * rx * s * (1.0 + 0.12 * (1 - abs(math.sin(a))))   # walls bulge a little at the foot
        pts.append((x, y))
    return pts


BACKDROPS = {
    'forest-floor': forest_floor,
    'clearing': clearing,
    'coast': coast,
    'storm-sky': storm_sky,
    'sky-high': sky_high,
    'ruins': ruins,
    'battlefield': battlefield,
    'anthill': anthill,
    'temple': temple,
    'silk-city': silk_city,
    'tunnels': tunnels,
}

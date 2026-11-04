"""Space and ship backdrops: an aging ark ship's interiors (one-point perspective, ribbed and patched) and orbital
scenes (ruled night skies with white stars, planets shaded with hatching that follows the sphere).

Engraving devices used here, all built from core.Ink primitives plus a few local helpers:
- swelling lines (_swell): ruled lines whose width varies along their length, so tone comes from line weight,
  as in a steel engraving sky or a globe;
- perspective hatching (_Persp): wall panels hatched along their orthogonals so the ruling converges on the
  vanishing point;
- a quiet factor (_quiet) that thins everything in the bottom 30% of a portrait, under the title.
"""
import math

# ======================================================================================= helpers
def _f(v):
    return f'{v:.1f}'

def _quiet(k, y):
    """Line-weight multiplier: 1 above 0.6H in portrait, falling to ~0.15 at the foot. Band frames stay 1."""
    if k.h <= k.w:
        return 1.0
    t = (y / k.h - 0.6) / 0.4
    if t <= 0:
        return 1.0
    return max(0.12, 1 - 0.88 * min(1, t) ** 0.8)

def _swell(pts, ws, minw=0.06):
    """Filled ribbons along a polyline with per-point half-width ws; runs break where the width vanishes."""
    out, run = [], []
    n = len(pts)

    def flush(run):
        if len(run) < 2:
            return
        L, R = [], []
        for j, i in enumerate(run):
            x, y = pts[i]
            a = pts[run[max(j - 1, 0)]]; b = pts[run[min(j + 1, len(run) - 1)]]
            dx, dy = b[0] - a[0], b[1] - a[1]; d = math.hypot(dx, dy) or 1
            nx, ny = -dy / d, dx / d; w = ws[i]
            L.append((x + nx * w, y + ny * w)); R.append((x - nx * w, y - ny * w))
        P = L + R[::-1]
        out.append('M' + ' L'.join(f'{px:.1f},{py:.1f}' for px, py in P) + 'Z')

    for i in range(n):
        if ws[i] >= minw:
            run.append(i)
        else:
            flush(run); run = []
    flush(run)
    return ''.join(out)

def _fill(k, d, white=False, rough=False):
    if d:
        k.ink.append(f'<path d="{d}" fill="{"#fff" if white else "#000"}"{" filter=\"url(#rough)\"" if rough else ""}/>')

def _strokes(k, ds, w=0.7, white=False, rough=False, opacity=1.0):
    """Many thin open strokes in one path element. Width is scaled by depth like Ink.line."""
    if not ds:
        return
    sw = w * (0.5 + 0.6 * k.depth)
    k.ink.append(f'<path d="{" ".join(ds)}" fill="none" stroke="{"#fff" if white else "#000"}" stroke-width="{sw:.2f}" '
                 f'stroke-linecap="round" stroke-linejoin="round" stroke-opacity="{opacity}"{" filter=\"url(#rough)\"" if rough else ""}/>')

def _seg(a, b):
    return f'M{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f}'

def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)

def _wrap_fade(k, start):
    """Fade everything drawn since `start` toward the bottom of a portrait (belt and braces for the title zone)."""
    if k.h <= k.w:
        return
    W, H = k.w, k.h
    mid = k.uid('fm'); gid = k.uid('fg')
    k.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="0" y1="{H * 0.62:.0f}" x2="0" y2="{H:.0f}">'
                  f'<stop offset="0" stop-color="#fff"/><stop offset="0.45" stop-color="#999"/><stop offset="1" stop-color="#3a3a3a"/></linearGradient>'
                  f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}"><rect width="{W}" height="{H}" fill="url(#{gid})"/></mask>')
    body = ''.join(k.ink[start:]); del k.ink[start:]
    k.ink.append(f'<g mask="url(#{mid})">{body}</g>')

def _focus(k):
    """Where the focus subject sits (see compose.placements)."""
    if k.h > k.w:
        return k.w * 0.5, k.h * 0.4
    return k.w * 0.5, k.h * 0.52

def _halo(k, x, y, rx=None, ry=None):
    """0 at the focus, 1 well away from it: used to keep the subject zone light."""
    fx, fy = _focus(k)
    rx = rx or k.w * 0.34; ry = ry or (k.h * 0.22 if k.h > k.w else k.h * 0.42)
    d = math.hypot((x - fx) / rx, (y - fy) / ry)
    return min(1.0, max(0.0, (d - 0.35) / 0.9))

def _night(spec):
    return spec.get('light') in ('night', 'starlight')

def _washes(k, spec, pools):
    """2-3 pooled tints. pools: [(cx, cy, rx, ry, which, opacity)]; night scenes get fewer and fainter."""
    w = spec['wash']
    if _night(spec):
        pools = pools[:2]
    for cx, cy, rx, ry, i, op in pools:
        k.watercolour(cx, cy, rx, ry, w[i], op * (0.7 if _night(spec) else 1.0))

def _light_pool(k, spec, x, y, r, n=16, a0=0, a1=2 * math.pi, reach=1.0):
    """Firelight / screen-glow: a tinted pool at the source and radiating ruled lines."""
    lt = spec.get('light')
    if lt not in ('firelight', 'screen-glow'):
        return
    w0, w1 = spec['wash']
    col = w1 if lt == 'firelight' else w0
    k.watercolour(x, y, r * 1.1, r * 0.9, col, 0.75, 5)
    ds = []
    for i in range(n):
        a = a0 + (a1 - a0) * (i + k.r.uniform(0.2, 0.8)) / n
        r0 = r * k.r.uniform(0.25, 0.45); r1 = r * reach * k.r.uniform(1.3, 2.4)
        ds.append(_seg((x + math.cos(a) * r0, y + math.sin(a) * r0), (x + math.cos(a) * r1, y + math.sin(a) * r1)))
    _strokes(k, ds, 0.5, opacity=0.35)

def _stars(k, n, ok, big=6, region=None):
    """White stars over ruled sky: dots, a few with crossed rays. ok(x, y) -> bool decides where they may fall."""
    W, H = k.w, k.h
    x0, y0, x1, y1 = region or (0, 0, W, H)
    dots, rays = [], []
    placed = 0; tries = 0
    while placed < n and tries < n * 6:
        tries += 1
        x, y = k.r.uniform(x0, x1), k.r.uniform(y0, y1)
        if not ok(x, y):
            continue
        placed += 1
        r = k.r.choice((0.8, 0.9, 1.0, 1.1, 1.2, 1.4, 1.6, 1.9, 2.3))
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}"/>')
    for _ in range(big):
        for _t in range(40):
            x, y = k.r.uniform(x0, x1), k.r.uniform(y0, y1)
            if ok(x, y):
                break
        else:
            continue
        L = k.r.uniform(9, 18); r = k.r.uniform(2.0, 3.0)
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}"/>')
        rays += [f'M{x - L:.1f},{y:.1f} L{x + L:.1f},{y:.1f}', f'M{x:.1f},{y - L:.1f} L{x:.1f},{y + L:.1f}',
                 f'M{x - L * 0.4:.1f},{y - L * 0.4:.1f} L{x + L * 0.4:.1f},{y + L * 0.4:.1f}',
                 f'M{x - L * 0.4:.1f},{y + L * 0.4:.1f} L{x + L * 0.4:.1f},{y - L * 0.4:.1f}']
    k.ink.append(f'<g fill="#fff">{"".join(dots)}</g>')
    if rays:
        k.ink.append(f'<path d="{" ".join(rays)}" stroke="#fff" stroke-width="1.1" stroke-linecap="round" fill="none"/>')

def _ruled_sky(k, dark, gap=4.4, y0=0, y1=None, angle=0.0, wmax=1.9, step=10):
    """An engraver's sky: parallel ruled lines whose weight swells with dark(x, y) in 0..1."""
    W, H = k.w, k.h
    y1 = H if y1 is None else y1
    ca, sa = math.cos(angle), math.sin(angle)
    span = math.hypot(W, H)
    paths = []
    y = y0 - W * abs(sa) - gap
    i = 0
    while y < y1 + W * abs(sa) + gap:
        pts, ws = [], []
        x = -20
        ph = k.r.uniform(0, 6.28)
        while x <= W + 20:
            yy = y + x * sa / max(ca, 1e-3) + 0.5 * math.sin(x / 41 + ph)
            if y0 - 10 <= yy <= y1 + 10:
                pts.append((x, yy))
                d = dark(x, yy)
                ws.append(0.5 * (0.18 + wmax * max(0, d)) * _quiet(k, yy) if d > 0.02 else 0)
            x += step
        if pts:
            paths.append(_swell(pts, ws))
        y += gap; i += 1
    _fill(k, ''.join(paths))

def _stipple_cloud(k, cx, cy, rx, ry, n, keep=None, size=(0.5, 1.2)):
    dots = []
    for _ in range(n):
        a = k.r.uniform(0, 2 * math.pi); t = k.r.random() ** 0.7
        x, y = cx + math.cos(a) * rx * t, cy + math.sin(a) * ry * t
        if keep and not keep(x, y):
            continue
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{k.r.uniform(*size) * _quiet(k, y):.2f}"/>')
    k.ink.append(f'<g fill="#000">{"".join(dots)}</g>')

def _noise3(x, y, z, seed):
    """Cheap smooth pseudo-noise on the sphere from summed sines (deterministic per seed)."""
    s = 0.0
    for i, (a, b, c, f, p) in enumerate(seed):
        s += math.sin(f * (a * x + b * y + c * z) + p) / (1 + i * 0.6)
    return s

def _sphere(k, cx, cy, R, tilt=0.35, rot=0.0, L=(-0.55, -0.6, 0.58), nlat=60, nlon=36, wmax=1.6,
            land=None, clouds=None, clip=None, step=5.0, terminator=0.0, atmos=True):
    """A planet engraved with hatching that follows the sphere: latitude rules swell toward the shadow,
    meridians cross them in the shade, the night side closes up. land/clouds: callables on the unit normal
    returning 0..1 that darken (land) or open (clouds) the ruling. clip: (x0, y0, x1, y1) drawing window."""
    W, H = k.w, k.h
    x0, y0, x1, y1 = clip or (-30, -30, W + 30, H + 30)
    start = len(k.ink)
    ll = math.sqrt(sum(v * v for v in L)); L = tuple(v / ll for v in L)
    ct, st = math.cos(tilt), math.sin(tilt)
    cr, sr = math.cos(rot), math.sin(rot)
    a = (0.0, -ct, st); u = (1.0, 0.0, 0.0); v = (0.0, st, ct)
    # disc knockout
    if R < 4000:
        k.paper(f'M{cx - R:.1f},{cy:.1f} a{R:.1f},{R:.1f} 0 1,0 {2 * R:.1f},0 a{R:.1f},{R:.1f} 0 1,0 {-2 * R:.1f},0Z')

    def proj(n):
        px, py = n[0] * R, n[1] * R
        return (cx + px * cr - py * sr, cy + px * sr + py * cr)

    def shade(n):
        lam = n[0] * L[0] + n[1] * L[1] + n[2] * L[2]
        dark = 1 - max(0.0, min(1.0, (lam - terminator + 0.15) / 1.0))
        if land:
            dark = min(1.0, dark + 0.55 * land(n) * (0.3 + 0.7 * (1 - dark)))
        if clouds:
            c = clouds(n)
            if c > 0 and lam > -0.05:
                dark = dark * (1 - 0.8 * c)
        rim = max(0.0, n[2])
        return dark, lam, rim

    def runs(curve, weight):
        out = []
        pts, ws = [], []
        for n in curve:
            if n[2] < 0:
                if pts: out.append(_swell(pts, ws)); pts, ws = [], []
                continue
            p = proj(n)
            if not (x0 <= p[0] <= x1 and y0 <= p[1] <= y1):
                if pts: out.append(_swell(pts, ws)); pts, ws = [], []
                continue
            pts.append(p); ws.append(weight(n, p))
        if pts: out.append(_swell(pts, ws))
        return ''.join(out)

    def samples(radius3):
        return max(24, int(2 * math.pi * R * radius3 / step))

    paths = []
    # latitude rules
    for i in range(1, nlat):
        phi = -math.pi / 2 + math.pi * i / nlat
        cphi, sphi = math.cos(phi), math.sin(phi)
        m = samples(cphi)
        curve = []
        for j in range(m + 1):
            th = 2 * math.pi * j / m
            c, s = math.cos(th), math.sin(th)
            curve.append(tuple(cphi * (c * u[q] + s * v[q]) + sphi * a[q] for q in range(3)))

        def wlat(n, p):
            dark, lam, rim = shade(n)
            w = 0.5 * (0.3 + wmax * dark ** 1.15)
            if clouds:
                w *= 1 - 0.9 * clouds(n) * (lam > -0.05)
            fs = rim ** 0.7
            return w * _quiet(k, p[1]) * (fs + (1 - fs) * dark)
        paths.append(runs(curve, wlat))
    # meridians, only in the shade
    for i in range(nlon):
        lon = 2 * math.pi * i / nlon
        c, s = math.cos(lon), math.sin(lon)
        m = samples(1.0) // 2
        curve = []
        for j in range(1, m):
            phi = -math.pi / 2 + math.pi * j / m
            cphi, sphi = math.cos(phi), math.sin(phi)
            curve.append(tuple(cphi * (c * u[q] + s * v[q]) + sphi * a[q] for q in range(3)))

        def wlon(n, p):
            dark, lam, rim = shade(n)
            t = max(0.0, (dark - 0.62) / 0.38)
            fs = rim ** 0.7
            return 0.5 * wmax * 0.7 * t ** 1.4 * _quiet(k, p[1]) * (fs + (1 - fs) * dark)
        paths.append(runs(curve, wlon))
    _fill(k, ''.join(paths))
    # limb line and atmosphere on the lit side
    if R < 4000:
        k.line(f'M{cx - R:.1f},{cy:.1f} a{R:.1f},{R:.1f} 0 1,0 {2 * R:.1f},0 a{R:.1f},{R:.1f} 0 1,0 {-2 * R:.1f},0', 0.9, rough=False)
    if atmos:
        la = math.atan2(L[1], L[0])
        ds = []
        for j, off in enumerate((4, 9, 15, 22)):
            span = 1.3 - j * 0.22
            rr = R + off
            pts = []
            for q in range(61):
                t = la - span + 2 * span * q / 60
                p = (cx + math.cos(t) * rr, cy + math.sin(t) * rr)
                if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
                    pts.append(p)
            if len(pts) > 1:
                ds.append('M' + ' L'.join(f'{px:.1f},{py:.1f}' for px, py in pts))
        _strokes(k, ds, 0.5, opacity=0.55)
        # crisp highlight just inside the lit limb
        hl = []
        for f, span, wd in ((0.992, 0.75, 3.2), (0.982, 0.45, 1.6)):
            pts = []
            for q in range(81):
                t = la - span + 2 * span * q / 80
                p = (cx + math.cos(t) * R * f, cy + math.sin(t) * R * f)
                if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
                    pts.append(p)
            if len(pts) > 1:
                k.ink.append(f'<path d="{k.poly(pts, close=False)}" fill="none" stroke="#fff" stroke-width="{wd}" stroke-linecap="round"/>')
    if clip:
        cid = k.uid('c')
        k.defs.append(f'<clipPath id="{cid}"><rect x="{x0:.1f}" y="{y0:.1f}" width="{x1 - x0:.1f}" height="{y1 - y0:.1f}"/></clipPath>')
        body = ''.join(k.ink[start:]); del k.ink[start:]
        k.ink.append(f'<g clip-path="url(#{cid})">{body}</g>')

def _green_world(seed_r):
    """Land and cloud fields for a forested green planet."""
    def mk(n):
        out = []
        for _ in range(n):
            v = [seed_r.gauss(0, 1) for _ in range(3)]; l = math.sqrt(sum(q * q for q in v)) or 1
            out.append((v[0] / l, v[1] / l, v[2] / l, seed_r.uniform(5, 13), seed_r.uniform(0, 6.3)))
        return out
    ls, cs, cs2 = mk(7), mk(5), mk(3)

    def land(n):
        v = _noise3(n[0], n[1], n[2], ls)
        return max(0.0, min(1.0, (v - 0.0) * 1.6))

    def clouds(n):
        v = _noise3(n[0], n[1], n[2], cs) + 0.7 * math.sin(30 * (n[1] + 0.15 * _noise3(n[0], n[1], n[2], cs2)))
        return max(0.0, min(1.0, (v - 1.35) * 2.2))
    return land, clouds

class _Persp:
    """One-point perspective: world (x right, y down, z depth) to screen around a vanishing point."""
    def __init__(self, vx, vy):
        self.vx, self.vy = vx, vy

    def p(self, x, y, z):
        return (self.vx + x / z, self.vy + y / z)

def _octagon(a, b, c):
    """Corridor cross-section (half-width a, half-height b, chamfer c), clockwise from top-left."""
    return [(-a + c, -b), (a - c, -b), (a, -b + c), (a, b - c), (a - c, b), (-a + c, b), (-a, b - c), (-a, -b + c)]

def _panel_hatch(P, A, B, z0, z1, n_long, n_cross, jitter=None):
    """Hatch a receding wall strip A->B (cross-section points) between depths z0 and z1:
    n_long rules along the orthogonals (converging on the vanishing point), n_cross transverse rules."""
    ds = []
    for i in range(n_long):
        t = (i + 0.5) / n_long
        q = _lerp(A, B, t)
        ds.append(_seg(P.p(q[0], q[1], z0), P.p(q[0], q[1], z1)))
    for i in range(n_cross):
        z = z0 + (z1 - z0) * (i + 0.5) / n_cross
        ds.append(_seg(P.p(A[0], A[1], z), P.p(B[0], B[1], z)))
    return ds

def _quad(P, A, B, z0, z1):
    return [P.p(A[0], A[1], z0), P.p(B[0], B[1], z0), P.p(B[0], B[1], z1), P.p(A[0], A[1], z1)]

# ======================================================================================= interiors
def _depth_of(z, zn, zf):
    """Map world depth to Ink depth (near heavy, far light)."""
    t = (math.log(z) - math.log(zn)) / (math.log(zf) - math.log(zn))
    return max(0.12, min(0.98, 0.98 - 0.86 * t))

def _ruled_panel(k, P, A, B, z0, z1, tone, angle_mode='long', wscale=1.0):
    """Hatch a receding strip with rules spaced by tone, along the orthogonals (and across them when dark)."""
    if tone <= 0:
        return
    sp = {1: 9.0, 2: 5.6, 3: 4.2, 4: 3.4}[min(4, tone)]
    qa, qb = P.p(*A, z0), P.p(*B, z0)
    scr = math.dist(qa, qb)
    n_long = max(1, int(scr / sp))
    ds = []
    if angle_mode in ('long', 'both'):
        ds += _panel_hatch(P, A, B, z0, z1, n_long, 0)
    if angle_mode == 'cross' or (tone >= 3 and angle_mode == 'both'):
        # transverse rules, evenly spaced on screen along the strip
        L0 = math.dist(P.p(*A, z0), P.p(*A, z1))
        n = max(1, int(L0 / (sp * 1.15)))
        inv0, inv1 = 1 / z0, 1 / z1
        for i in range(n):
            z = 1 / (inv0 + (inv1 - inv0) * (i + 0.5) / n)
            ds.append(_seg(P.p(*A, z), P.p(*B, z)))
    mid_y = (qa[1] + qb[1]) / 2
    _strokes(k, ds, (0.38 + 0.1 * tone) * wscale * _quiet(k, mid_y), rough=True)

def _shell_panels(k, P, sec, zs, base, db, zf, a, b, slots=True, patch=0.33, floor='grate', skip=()):
    """Hull bays between consecutive depths, far to near: ruled wall plates with seams and patches, a deck,
    ceiling light slots."""
    for idx in range(len(zs) - 1, 0, -1):
        z1, z0 = zs[idx], zs[idx - 1]
        k.depth = _depth_of(math.sqrt(z0 * z1), zs[1] if len(zs) > 1 else 0.5, zf)
        far = (z0 + z1) / 2 > zf * 0.45
        for s in range(len(sec)):
            if s in skip:
                continue
            A, B = sec[s], sec[(s + 1) % len(sec)]
            q = _quad(P, A, B, z0, z1)
            k.paper(k.poly(q))
            tone = base[s] + db - (1 if far else 0)
            if s == 4:
                if floor == 'grate':
                    _ruled_panel(k, P, A, B, z0, z1, 2, 'cross', 0.9)
                    _strokes(k, _panel_hatch(P, A, B, z0, z1, 3, 0), 0.9 * _quiet(k, q[0][1]))
                else:
                    _ruled_panel(k, P, A, B, z0, z1, 1, 'long', 0.8)
                    _strokes(k, [_seg(P.p(*A, (z0 + z1) / 2), P.p(*B, (z0 + z1) / 2))], 0.7 * _quiet(k, q[0][1]))
                continue
            _ruled_panel(k, P, A, B, z0, z1, tone, 'both')
            _strokes(k, [_seg(P.p(*A, (z0 + z1) / 2), P.p(*B, (z0 + z1) / 2))], 0.7 * _quiet(k, q[0][1]))
            if s in (0, 1, 2, 6, 7) and k.r.random() < patch:
                t0 = k.r.uniform(0.08, 0.4); t1 = min(0.94, t0 + k.r.uniform(0.25, 0.5))
                za = z0 + (z1 - z0) * k.r.uniform(0.08, 0.3); zb = z0 + (z1 - z0) * k.r.uniform(0.55, 0.9)
                quad = _quad(P, _lerp(A, B, t0), _lerp(A, B, t1), za, zb)
                k.shape(k.poly(quad), tone=min(4, tone + 1), dark=min(4, tone + 2), outline=0.9,
                        angle=k.r.choice((20, 65, 115, 150)))
                rv = ''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(0.7, 1.8 * k.depth):.1f}"/>' for x, y in quad)
                k.ink.append(f'<g fill="#000">{rv}</g>')
        if slots:
            zm0, zm1 = z0 + (z1 - z0) * 0.3, z0 + (z1 - z0) * 0.7
            q = _quad(P, (-a * 0.16, -b), (a * 0.16, -b), zm0, zm1)
            k.ink.append(f'<path d="{k.poly(q)}" fill="#fff" stroke="#000" stroke-width="{0.5 + 0.7 * k.depth:.2f}"/>')

def _shell_frames(k, P, sec, ribs, zf, db, a, b, c, th=0.07):
    """U-frames open across the deck, far to near: a dark ruled face, a light receding inner face, rivets and
    a white edge where the frame catches the light."""
    for z in reversed(ribs):
        k.depth = _depth_of(z, ribs[0], zf)
        o = [(sec[5][0] - c * 0.2, b)] + [sec[i] for i in (5, 6, 7, 0, 1, 2, 3)] + [(sec[4][0] + c * 0.2, b)]
        inn = [(x * (1 - th), y - b * th * (1 if y < 0 else -1) if abs(y) > b * 0.5 else y) for x, y in o]
        inn[0] = (o[0][0] + a * th, b); inn[-1] = (o[-1][0] - a * th, b)
        outer = [P.p(x, y, z) for x, y in o]
        inner = [P.p(x, y, z) for x, y in inn]
        back = [P.p(x, y, z * 1.07) for x, y in inn]
        k.paper(k.poly(inner + back[::-1]))
        _strokes(k, [_seg(inner[i], back[i]) for i in range(len(inner))] +
                 [_seg(_lerp(inner[i], back[i], 0.5), _lerp(inner[i + 1], back[i + 1], 0.5)) for i in range(len(inner) - 1)], 0.5)
        k.ink.append(f'<path d="{k.poly(back, close=False)}" fill="none" stroke="#000" stroke-width="{0.4 + 0.6 * k.depth:.2f}"/>')
        tone = 3 + db if k.depth > 0.35 else 2 + db
        k.shape(k.poly(outer + inner[::-1]), tone=min(tone, 4), dark=4, outline=1.0, angle=k.r.choice((35, 50, 130, 145)))
        rv = []
        for i in range(len(outer) - 1):
            for t in (0.3, 0.7):
                x, y = _lerp(_lerp(outer[i], outer[i + 1], t), _lerp(inner[i], inner[i + 1], t), 0.5)
                rv.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{max(0.8, 3.2 * k.depth):.1f}"/>')
        k.ink.append(f'<g fill="#fff" stroke="#000" stroke-width=".6">{"".join(rv)}</g>')
        hl = k.poly([_lerp(inner[i], outer[i], 0.25) for i in (2, 3, 4, 5)], close=False)
        k.ink.append(f'<path d="{hl}" fill="none" stroke="#fff" stroke-width="{0.8 + 1.6 * k.depth:.1f}" stroke-linecap="round"/>')

def _ribs(k, z0, zf, lo=1.33, hi=1.45):
    out, z = [], z0
    while z < zf * 0.9:
        out.append(z); z *= k.r.uniform(lo, hi)
    return out

def ship_corridor(k, spec):
    """A ribbed service corridor of the old ark in one-point perspective: U-frames receding to a lit bulkhead
    hatch, a conduit bundle along one shoulder, patched plates, ceiling light slots, a side hatch, deck grating."""
    W, H = k.w, k.h; start = len(k.ink)
    fx, fy = _focus(k)
    portrait = H > W
    P = _Persp(fx - W * 0.03, fy - H * (0.03 if portrait else 0.06))
    a = W * (0.6 if portrait else 0.46); b = a * (0.8 if portrait else 0.6); c = a * 0.3
    sec = _octagon(a, b, c)
    zf = 6.5 if portrait else 5.5
    ribs, z = [], 0.5
    while z < zf * 0.9:
        ribs.append(z); z *= k.r.uniform(1.33, 1.45)
    night = _night(spec); lt = spec.get('light')
    db = 1 if night else 0
    _washes(k, spec, [(P.vx, P.vy, W * 0.2, H * 0.1, 0, 0.75), (W * 0.15, H * 0.28, W * 0.22, H * 0.2, 1, 0.45),
                      (W * 0.85, H * 0.15, W * 0.2, H * 0.14, 0, 0.35)])
    # sides: 0 ceiling, 1 upper-right, 2 right wall, 3 lower-right, 4 floor, 5 lower-left, 6 left wall, 7 upper-left
    zs = [0.2] + ribs + [zf]
    _shell_panels(k, P, sec, zs, [3, 2, 2, 2, 1, 1, 2, 2], db, zf, a, b)
    # ------------------------------------------------ far bulkhead with a lit hatch
    k.depth = 0.15
    fq = [P.p(x, y, zf) for x, y in sec]
    k.shape(k.poly(fq), tone=2 + db, dark=3 + db, outline=0.8, angle=90)
    hw, hh = a * 0.3, b * 0.6
    hx0, hy0 = P.p(-hw, -hh, zf); hx1, hy1 = P.p(hw, b, zf)
    rr = (hx1 - hx0) * 0.3; m = (hx1 - hx0) * 0.14
    door = (f'M{hx0:.1f},{hy1:.1f} L{hx0:.1f},{hy0 + rr:.1f} Q{hx0:.1f},{hy0:.1f} {hx0 + rr:.1f},{hy0:.1f} L{hx1 - rr:.1f},{hy0:.1f} '
            f'Q{hx1:.1f},{hy0:.1f} {hx1:.1f},{hy0 + rr:.1f} L{hx1:.1f},{hy1:.1f}Z')
    frame = (f'M{hx0 - m:.1f},{hy1:.1f} L{hx0 - m:.1f},{hy0 + rr:.1f} Q{hx0 - m:.1f},{hy0 - m:.1f} {hx0 + rr:.1f},{hy0 - m:.1f} L{hx1 - rr:.1f},{hy0 - m:.1f} '
             f'Q{hx1 + m:.1f},{hy0 - m:.1f} {hx1 + m:.1f},{hy0 + rr:.1f} L{hx1 + m:.1f},{hy1:.1f}Z')
    k.shape(frame, tone=3, dark=4, outline=0.8, angle=45)
    k.ink.append(f'<path d="{door}" fill="#fff" stroke="#000" stroke-width="0.8"/>')
    lf = [(hx1 + m, hy0 + rr * 0.4), (hx1 + m + (hx1 - hx0) * 0.4, hy0 + rr * 0.1), (hx1 + m + (hx1 - hx0) * 0.4, hy1 + 3), (hx1 + m, hy1)]
    k.shape(k.poly(lf), tone=2, dark=4, outline=0.7, angle=95)
    hx, hy = (hx0 + hx1) / 2, (hy0 + hy1) / 2
    if night:
        _strokes(k, [_seg((hx0 + (hx1 - hx0) * t, hy0 + 4), (hx0 + (hx1 - hx0) * t, hy1)) for t in (0.2, 0.4, 0.6, 0.8)], 0.4, opacity=0.6)
    _light_pool(k, spec, hx, hy, (hx1 - hx0) * 0.9, n=22, reach=1.6)
    # ------------------------------------------------ conduit bundle on the upper-right shoulder, inside the frames
    A, B = sec[1], sec[2]
    nrm = (-(B[1] - A[1]), B[0] - A[0]); nl = math.hypot(*nrm); nrm = (nrm[0] / nl, nrm[1] / nl)   # points inward
    zpts = [ribs[0] * 0.8] + ribs + [zf]
    for j, (t, rad) in enumerate(((0.2, 0.04), (0.42, 0.028), (0.62, 0.036), (0.8, 0.022))):
        q = _lerp(A, B, t); r = a * rad; inset = a * 0.015 + r
        cq = (q[0] + nrm[0] * inset, q[1] + nrm[1] * inset)
        k.depth = 0.85
        L = [P.p(cq[0] - nrm[1] * r, cq[1] + nrm[0] * r, zz) for zz in zpts]
        R = [P.p(cq[0] + nrm[1] * r, cq[1] - nrm[0] * r, zz) for zz in zpts]
        # tube shading: rules along its length, crowding on the shadow side
        k.paper(k.poly(L + R[::-1]))
        ds = []
        for f in (0.55, 0.68, 0.78, 0.86, 0.93):
            ds.append(k.poly([_lerp(L[i], R[i], f) for i in range(len(L))], close=False))
        _strokes(k, ds, 0.6)
        _strokes(k, [k.poly(L, close=False), k.poly(R, close=False)], 1.1)
        k.ink.append(f'<path d="{k.poly([_lerp(L[i], R[i], 0.25) for i in range(len(L))], close=False)}" fill="none" stroke="#fff" stroke-width="1.2"/>')
        # clamps
        _strokes(k, [_seg(P.p(cq[0] - nrm[0] * r * 1.6, cq[1] - nrm[1] * r * 1.6, zz * 1.03),
                          P.p(cq[0] + nrm[0] * r * 1.4, cq[1] + nrm[1] * r * 1.4, zz * 1.03)) for zz in ribs], 2.0)
    _shell_frames(k, P, sec, ribs, zf, db, a, b, c)
    # ------------------------------------------------ side hatch on the left wall between frames 1 and 2
    if len(ribs) > 3:
        za, zb = ribs[1] * 1.12, ribs[2] * 0.95
        wy0, wy1 = -b * 0.4, b * 0.6
        quad = [P.p(-a, wy0, za), P.p(-a, wy0, zb), P.p(-a, wy1, zb), P.p(-a, wy1, za)]
        k.depth = 0.75
        k.shape(k.poly(quad), tone=3 + db, dark=4, outline=1.3, angle=8)
        ins = [P.p(-a, wy0 + b * 0.08, za + (zb - za) * 0.15), P.p(-a, wy0 + b * 0.08, zb - (zb - za) * 0.15),
               P.p(-a, wy1 - b * 0.06, zb - (zb - za) * 0.15), P.p(-a, wy1 - b * 0.06, za + (zb - za) * 0.15)]
        k.shape(k.poly(ins), tone=1, dark=3, outline=1.0, angle=82)
        cw = P.p(-a, (wy0 + wy1) / 2, (za + zb) / 2)
        sx = abs(ins[1][0] - ins[0][0]) * 0.28; sy = abs(ins[3][1] - ins[0][1]) * 0.16
        k.ink.append(f'<ellipse cx="{cw[0]:.1f}" cy="{cw[1]:.1f}" rx="{sx:.1f}" ry="{sy:.1f}" fill="none" stroke="#000" stroke-width="2.4"/>')
        _strokes(k, [_seg((cw[0], cw[1] - sy), (cw[0], cw[1] + sy)), _seg((cw[0] - sx, cw[1]), (cw[0] + sx, cw[1]))], 1.4)
    _wrap_fade(k, start)


# ======================================================================================= space
def _sky_dark(k, spec, base=None, halo=0.45, top=0.25):
    """Darkness field for a ruled night sky: heavier at the top and edges, opened up behind the focus."""
    lt = spec.get('light')
    b = base if base is not None else {'starlight': 0.78, 'night': 0.85, 'dusk': 0.62, 'dawn': 0.55,
                                        'day': 0.5, 'screen-glow': 0.7, 'firelight': 0.68}.get(lt, 0.75)
    H = k.h

    def dark(x, y):
        d = b + top * (0.5 - y / H)
        d -= halo * (1 - _halo(k, x, y))
        return max(0.08, min(1.0, d))
    return dark

def _sky_with_stars(k, spec, dark, inside=None, n=None, big=None, gap=4.2, angle=-0.04):
    """Ruled sky plus white stars where the sky is dark enough to hold them."""
    inside = inside or (lambda x, y: True)
    _ruled_sky(k, lambda x, y: dark(x, y) if inside(x, y) else 0, gap=gap, angle=angle)
    area = k.w * k.h / 1e6
    n = n if n is not None else int(520 * area)
    big = big if big is not None else max(4, int(9 * area))
    ok = lambda x, y: inside(x, y) and dark(x, y) * _quiet(k, y) > 0.5
    _stars(k, n, ok, big=big)

def planet_orbit(k, spec):
    """A green world's limb seen from orbit: a huge planet shaded with latitude ruling (forests darker, clouds
    open), a lit crescent toward the light, a thin atmosphere, a small moon, a ruled starry sky."""
    W, H = k.w, k.h; start = len(k.ink)
    portrait = H > W
    if portrait:
        cx, cy, R = W * 1.22, H * 0.8, W * 0.97
    else:
        cx, cy, R = W * 0.62, H * 0.74 + W * 1.25, W * 1.25
    dark = _sky_dark(k, spec)
    w0, w1 = spec['wash']
    ang = math.atan2(_focus(k)[1] - cy, _focus(k)[0] - cx)
    lx, ly = cx + math.cos(ang) * R * 0.88, cy + math.sin(ang) * R * 0.88
    k.watercolour(lx, ly, W * 0.32, H * (0.16 if portrait else 0.3), w0, 0.8, 5)
    k.watercolour(cx + math.cos(ang - 0.3) * R * 0.82, cy + math.sin(ang - 0.3) * R * 0.82, W * 0.25, H * 0.14, w0, 0.5)
    k.watercolour(cx + math.cos(ang + 0.1) * (R + 30), cy + math.sin(ang + 0.1) * (R + 30), W * 0.3, H * 0.08, w1, 0.55)
    # far: sky and stars, then a small moon high on the far side
    k.depth = 0.15
    _sky_with_stars(k, spec, dark)
    mx, my, mr = (W * 0.17, H * 0.12, W * 0.055) if portrait else (W * 0.1, H * 0.22, H * 0.075)
    k.depth = 0.3
    _sphere(k, mx, my, mr, tilt=0.5, rot=0.3, L=(-0.7, -0.45, 0.45), nlat=int(mr * 0.95), nlon=int(mr * 1.6), wmax=1.25, step=2.5,
            land=_crater_field(k.r), atmos=False)
    # the planet: an atmosphere gap, then the globe with its pole turned away
    k.depth = 0.75
    k.paper(f'M{cx - R - 22:.1f},{cy:.1f} a{R + 22:.1f},{R + 22:.1f} 0 1,0 {2 * R + 44:.1f},0 a{R + 22:.1f},{R + 22:.1f} 0 1,0 {-2 * R - 44:.1f},0Z')
    land, clouds = _green_world(k.r)
    _sphere(k, cx, cy, R, tilt=-0.25, rot=-0.35, L=(-0.62, -0.62, 0.2) if portrait else (-0.3, -0.75, 0.25),
            nlat=int(math.pi * R / 6.0), nlon=int(2 * math.pi * R / 9), wmax=1.8, step=7, land=land, clouds=clouds)
    _wrap_fade(k, start)

def _crater_field(r):
    craters = [((r.uniform(-1, 1), r.uniform(-1, 1), r.uniform(0.2, 1)), r.uniform(0.12, 0.3)) for _ in range(6)]

    def land(n):
        v = 0.0
        for (cx, cy, cz), rad in craters:
            l = math.sqrt(cx * cx + cy * cy + cz * cz)
            d = math.dist(n, (cx / l, cy / l, cz / l))
            if d < rad:
                v = max(v, 0.9 if d > rad * 0.7 else 0.35)
        return v
    return land

def deep_space(k, spec):
    """Open space: a ruled sky deepening to the edges, a faint nebula opening behind the focus with stippled
    filaments, a diagonal drift of the galaxy, a distant ringed world in a corner."""
    W, H = k.w, k.h; start = len(k.ink)
    fx, fy = _focus(k)
    w0, w1 = spec['wash']
    portrait = H > W
    # nebula: a few lobes around and above the focus that open the ruling
    lobes = [(fx + k.r.uniform(-0.25, 0.25) * W, fy + k.r.uniform(-0.25, 0.15) * H * (0.6 if portrait else 1),
              W * k.r.uniform(0.16, 0.3), H * k.r.uniform(0.08, 0.14) * (1 if portrait else 2.2)) for _ in range(5)]

    def neb(x, y):
        v = 0.0
        for cx, cy, rx, ry in lobes:
            v += math.exp(-(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2))
        return min(1.0, v)
    # galactic band: a diagonal of denser stars and stipple from upper right
    ga = -0.6 if portrait else -0.25
    gx, gy = W * 0.5, H * 0.32

    def band(x, y):
        d = abs((x - gx) * math.sin(ga) - (y - gy) * math.cos(ga))
        return math.exp(-(d / (H * (0.08 if portrait else 0.15))) ** 2)
    base = _sky_dark(k, spec, halo=0.25)
    dark = lambda x, y: max(0.06, base(x, y) - 0.55 * neb(x, y) - 0.15 * band(x, y))
    k.watercolour(fx, fy - H * 0.04, W * 0.35, H * (0.14 if portrait else 0.3), w1, 0.7, 5)
    k.watercolour(lobes[0][0], lobes[0][1], W * 0.25, H * 0.1, w0, 0.55)
    k.depth = 0.15
    _ruled_sky(k, dark, gap=4.0, angle=-0.03)
    # second, crossing ruling at the edges for the deepest tone
    _ruled_sky(k, lambda x, y: max(0, dark(x, y) - 0.62) * 2.2 * _halo(k, x, y), gap=5.5, angle=0.5, wmax=1.2)
    # nebula: stipple gathering at the rims of the glow, and fine streamlines curling along its contours
    def grad(x, y, e=6.0):
        return ((neb(x + e, y) - neb(x - e, y)) / (2 * e), (neb(x, y + e) - neb(x, y - e)) / (2 * e))
    dots = []
    for _ in range(int(9000 * W * H / 1e6)):
        x, y = k.r.uniform(0, W), k.r.uniform(0, H)
        v = neb(x, y); pr = 4 * v * (1 - v)
        if k.r.random() < pr * 0.9:
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{k.r.uniform(0.35, 0.9) * _quiet(k, y):.2f}"/>')
    k.ink.append(f'<g fill="#000">{"".join(dots)}</g>')
    ds = []
    for _ in range(int(260 * W * H / 1e6)):
        x, y = k.r.uniform(0, W), k.r.uniform(0, H)
        v = neb(x, y)
        if not 0.15 < v < 0.85 or _quiet(k, y) < 0.5:
            continue
        pts = [(x, y)]
        sgn = k.r.choice((-1, 1)); L = k.r.uniform(25, 90)
        for _s in range(int(L / 4)):
            gx, gy = grad(*pts[-1]); gl = math.hypot(gx, gy) or 1e-9
            tx, ty = -gy / gl * sgn, gx / gl * sgn
            pts.append((pts[-1][0] + tx * 4 + gx / gl * 0.6, pts[-1][1] + ty * 4 + gy / gl * 0.6))
        ds.append(k.poly(pts, close=False))
    _strokes(k, ds, 0.45, opacity=0.8)
    # stars: many fine, clustered along the band
    ok = lambda x, y: dark(x, y) * _quiet(k, y) > 0.42
    _stars(k, int(330 * W * H / 1e6), ok, big=max(4, int(8 * W * H / 1e6)))
    _stars(k, int(500 * W * H / 1e6), lambda x, y: ok(x, y) and k.r.random() < band(x, y), big=0)
    # a distant ringed world low in a corner
    k.depth = 0.35
    px, py, pr = (W * 0.84, H * 0.58, W * 0.07) if portrait else (W * 0.12, H * 0.72, H * 0.12)
    _ringed(k, px, py, pr, back=True)
    _sphere(k, px, py, pr, tilt=0.35, rot=0.35, nlat=int(pr * 0.95), nlon=int(pr * 1.6), wmax=1.25, step=2.5, atmos=False,
            land=lambda n: 0.35 * max(0, math.sin(n[1] * 9 + 1)))
    _ringed(k, px, py, pr, back=False)
    _wrap_fade(k, start)

def _ringed(k, cx, cy, r, back, tilt=0.28, rot=-0.35):
    """Rings around a small planet: back half first (behind the disc), front half after."""
    ds = []
    for f in (1.45, 1.55, 1.62, 1.75, 1.82, 1.9):
        pts = []
        rng = (math.pi, 2 * math.pi) if back else (0, math.pi)
        for i in range(41):
            t = rng[0] + (rng[1] - rng[0]) * i / 40
            x, y = math.cos(t) * r * f, math.sin(t) * r * f * tilt
            pts.append((cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot)))
        ds.append(k.poly(pts, close=False))
    if back:
        _strokes(k, ds, 3.2, white=True)
    _strokes(k, ds, 0.7)


def _ellipse_pt(cx, cy, rx, ry, t, rot=0.0):
    x, y = rx * math.cos(t), ry * math.sin(t)
    return (cx + x * math.cos(rot) - y * math.sin(rot), cy + x * math.sin(rot) + y * math.cos(rot))

def _truss(k, a, b, w0, w1, n=10, tone_w=1.0):
    """A lattice girder from a to b, tapering from width w0 to w1: two chords and zigzag bracing."""
    dx, dy = b[0] - a[0], b[1] - a[1]; L = math.hypot(dx, dy) or 1
    nx, ny = -dy / L, dx / L
    pl = [(a[0] + dx * t + nx * (w0 + (w1 - w0) * t) / 2, a[1] + dy * t + ny * (w0 + (w1 - w0) * t) / 2) for t in [i / n for i in range(n + 1)]]
    pr = [(a[0] + dx * t - nx * (w0 + (w1 - w0) * t) / 2, a[1] + dy * t - ny * (w0 + (w1 - w0) * t) / 2) for t in [i / n for i in range(n + 1)]]
    k.paper(k.poly(pl + pr[::-1]))
    ds = [k.poly(pl, close=False), k.poly(pr, close=False)]
    for i in range(n):
        ds.append(_seg(pl[i], pr[i + 1])); ds.append(_seg(pl[i], pr[i]))
    _strokes(k, ds[:2], 1.5 * tone_w)
    _strokes(k, ds[2:], 0.7 * tone_w)
    # shadow side ruling
    _strokes(k, [k.poly([_lerp(pl[i], pr[i], f) for i in range(n + 1)], close=False) for f in (0.7, 0.8, 0.9)], 0.4)

def station_exterior(k, spec):
    """The ring station from just above its plane: the near arc of the great wheel sweeps across the top, its
    lit roof (glazed strips, plating) above a shaded rim of windows, spokes running in to the hub at the top
    edge, a girder hanging toward the focus with a ship berthed, a crescent world far off, a ruled starry sky."""
    W, H = k.w, k.h; start = len(k.ink)
    portrait = H > W
    w0, w1 = spec['wash']
    if portrait:
        cx, cy, rx, ry, th = W * 0.56, -H * 0.02, W * 1.02, H * 0.21, H * 0.06
    else:
        cx, cy, rx, ry, th = W * 0.55, -H * 0.36, W * 0.82, H * 0.56, H * 0.13
    roof = 0.8                                     # inner edge of the roof as a fraction of the radius
    dark = _sky_dark(k, spec)
    k.watercolour(cx - rx * 0.35, cy + ry * 0.85, W * 0.38, th * 2.5, w0, 0.7, 5)
    k.watercolour(_focus(k)[0], _focus(k)[1], W * 0.3, H * 0.12, w1, 0.5)
    k.depth = 0.15
    _sky_with_stars(k, spec, dark)
    k.depth = 0.3
    px, py, pr = (W * 0.17, H * 0.6, W * 0.12) if portrait else (W * 0.9, H * 0.76, H * 0.19)
    _sphere(k, px, py, pr, tilt=0.3, rot=0.2, L=(-0.9, -0.3, -0.05), nlat=int(pr * 0.9), nlon=int(pr * 1.2), wmax=3.0,
            step=3, land=lambda n: 0.3 * max(0, math.sin(9 * n[1] + 3 * n[0])), atmos=True)
    # hub and spokes (inside the ring, drawn before it)
    k.depth = 0.5
    hub = (cx, cy + H * (0.03 if portrait else 0.1))
    for t in (math.pi * 0.7, math.pi * 0.42, math.pi * 0.12):
        base = _ellipse_pt(cx, cy, rx * roof, ry * roof, t)
        _truss(k, base, hub, th * 0.7, th * 0.35, n=12)
    hr = th * 1.3
    k.shape(f'M{hub[0] - hr:.1f},{hub[1] - hr:.1f} L{hub[0] - hr:.1f},{hub[1] + hr * 0.4:.1f} Q{hub[0]:.1f},{hub[1] + hr * 0.9:.1f} {hub[0] + hr:.1f},{hub[1] + hr * 0.4:.1f} L{hub[0] + hr:.1f},{hub[1] - hr:.1f}Z',
            tone=2, dark=4, outline=1.2, angle=88)
    # the arc
    k.depth = 0.85
    n = 200
    ts = [math.pi * i / n for i in range(n + 1)]
    inner = [_ellipse_pt(cx, cy, rx * roof, ry * roof, t) for t in ts]
    top = [_ellipse_pt(cx, cy, rx, ry, t) for t in ts]
    bot = [_ellipse_pt(cx, cy + th, rx, ry, t) for t in ts]
    k.paper(k.poly(inner + top[::-1]))
    k.paper(k.poly(top + bot[::-1]))
    # roof: lit, sparse rules following the arc, crossed by radial frames; long glazed strips
    paths = []
    for j in range(1, 9):
        f = j / 9
        pts = [_lerp(inner[i], top[i], f) for i in range(n + 1)]
        ws = [0.5 * (0.15 + 0.5 * abs(math.cos(ts[i])) ** 2 + 0.3 * (1 - f)) for i in range(n + 1)]
        paths.append(_swell(pts, ws))
    _fill(k, ''.join(paths))
    _strokes(k, [_seg(inner[i], top[i]) for i in range(0, n + 1, 8)], 0.7)
    glaze = []
    for f0 in (0.25, 0.6):
        a = [_lerp(inner[i], top[i], f0) for i in range(6, n - 5)]
        b = [_lerp(inner[i], top[i], f0 + 0.12) for i in range(6, n - 5)]
        glaze.append(k.poly(a + b[::-1]))
    k.ink.append(f'<path d="{"".join(glaze)}" fill="#fff" stroke="#000" stroke-width=".8"/>')
    _strokes(k, [_seg(_lerp(inner[i], top[i], f0), _lerp(inner[i], top[i], f0 + 0.12)) for i in range(8, n - 6, 3) for f0 in (0.25, 0.6)], 0.4)
    # rim: cylindrical shading, darker to the underside and toward the shadowed right end
    paths = []
    nr = int(th / 3.0)
    for j in range(nr + 1):
        f = j / nr
        pts = [_lerp(top[i], bot[i], f) for i in range(n + 1)]
        ws = []
        for i, t in enumerate(ts):
            d = 0.35 + 0.55 * f ** 1.3 + 0.3 * (0.5 + 0.5 * math.cos(t)) + 0.25 * abs(math.cos(t)) ** 3
            ws.append(0.5 * (0.25 + 1.6 * min(1, d) ** 1.4) * _quiet(k, pts[i][1]))
        paths.append(_swell(pts, ws))
    _fill(k, ''.join(paths))
    _strokes(k, [_seg(top[i], bot[i]) for i in range(0, n + 1, 5)], 0.8)
    wins, darkw = [], []
    for row in (0.28, 0.55):
        for i in range(3, n - 3):
            if abs(math.cos(ts[i])) > 0.9 or k.r.random() < 0.45 or i % 5 == 0:
                continue
            a, b = _lerp(top[i], bot[i], row), _lerp(top[i + 1], bot[i + 1], row)
            c, d = _lerp(top[i + 1], bot[i + 1], row + 0.13), _lerp(top[i], bot[i], row + 0.13)
            (wins if k.r.random() < 0.7 else darkw).append(k.poly([_lerp(a, b, 0.2), _lerp(a, b, 0.8), _lerp(d, c, 0.8), _lerp(d, c, 0.2)]))
    k.ink.append(f'<path d="{"".join(wins)}" fill="#fff"/>')
    k.ink.append(f'<path d="{"".join(darkw)}" fill="#000"/>')
    _strokes(k, [k.poly(inner, close=False)], 1.0)
    _strokes(k, [k.poly(top, close=False)], 1.4)
    _strokes(k, [k.poly(bot, close=False)], 2.2)
    k.ink.append(f'<path d="{k.poly([_lerp(top[i], bot[i], 0.05) for i in range(int(n * 0.25), int(n * 0.85))], close=False)}" fill="none" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/>')
    # docking girder with a berthed ship, hanging toward the focus but beside it
    gx = W * (0.84 if portrait else 0.83)
    t = math.acos(max(-1, min(1, (gx - cx) / rx)))
    p = _ellipse_pt(cx, cy + th, rx, ry, t)
    fx, fy = _focus(k)
    tip = (gx - W * 0.02, p[1] + (H * 0.07 if portrait else H * 0.14))
    k.depth = 0.75
    _truss(k, (p[0], p[1] - 2), tip, th * 0.55, th * 0.4, n=9)
    k.depth = 0.85
    L, Wd = th * (1.5 if portrait else 0.9), th * (0.4 if portrait else 0.24)
    sx, sy = tip[0], tip[1] + Wd * 0.9
    hull = k.smooth([(sx - L, sy), (sx - L * 0.7, sy - Wd), (sx + L * 0.6, sy - Wd * 0.9), (sx + L, sy - Wd * 0.2),
                     (sx + L, sy + Wd * 0.3), (sx + L * 0.6, sy + Wd), (sx - L * 0.7, sy + Wd * 0.9)])
    k.shape(hull, tone=2, dark=4, outline=1.2, angle=8)
    _strokes(k, [_seg((sx + L * q, sy - Wd * 0.9), (sx + L * q, sy + Wd * 0.95)) for q in (-0.4, 0.0, 0.35)], 0.7)
    k.ink.append(f'<path d="M{sx - L * 0.6:.1f},{sy - Wd * 0.6:.1f} Q{sx:.1f},{sy - Wd * 0.85:.1f} {sx + L * 0.6:.1f},{sy - Wd * 0.55:.1f}" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round"/>')
    k.solid(f'M{sx - L:.1f},{sy - Wd * 0.3:.1f} L{sx - L * 1.15:.1f},{sy - Wd * 0.45:.1f} L{sx - L * 1.15:.1f},{sy + Wd * 0.45:.1f} L{sx - L:.1f},{sy + Wd * 0.3:.1f}Z')
    _wrap_fade(k, start)

def _spindle(k, x, y, s, ang):
    """A silk city node: a spindle of wrapped silk with ruled shading and a white highlight."""
    ca, sa = math.cos(ang), math.sin(ang)
    P = lambda u, v: (x + u * ca - v * sa, y + u * sa + v * ca)
    pts = [P(-s, 0), P(-s * 0.4, -s * 0.32), P(s * 0.4, -s * 0.3), P(s, 0), P(s * 0.4, s * 0.34), P(-s * 0.4, s * 0.3)]
    d = k.smooth(pts)
    k.paper(d)
    ds = []
    for i in range(1, 9):
        u = -s + 2 * s * i / 9
        hw = s * 0.33 * math.sqrt(max(0, 1 - (u / s) ** 2))
        ds.append(f'M{P(u, -hw)[0]:.1f},{P(u, -hw)[1]:.1f} Q{P(u + s * 0.08, 0)[0]:.1f},{P(u + s * 0.08, 0)[1]:.1f} {P(u, hw)[0]:.1f},{P(u, hw)[1]:.1f}')
    _strokes(k, ds, 0.5)
    for f in (0.35, 0.6, 0.8):
        _strokes(k, [k.smooth([P(-s * 0.9, s * 0.3 * f * 0.4), P(0, s * 0.3 * f), P(s * 0.9, s * 0.3 * f * 0.4)], close=False)], 0.5)
    k.ink.append(f'<path d="{d}" fill="none" stroke="#000" stroke-width="{0.5 + 0.6 * k.depth:.2f}"/>')
    a, b = P(-s * 0.5, -s * 0.18), P(s * 0.4, -s * 0.2)
    k.ink.append(f'<path d="M{a[0]:.1f},{a[1]:.1f} L{b[0]:.1f},{b[1]:.1f}" stroke="#fff" stroke-width="{max(1, s * 0.06):.1f}" stroke-linecap="round"/>')

def orbital_web(k, spec):
    """A vast silk web city ringing a green planet: the planet's limb, an inclined orb web in the orbital plane
    (spiral threads as ellipses, radials falling to the surface as elevator threads), spindle cities at the
    crossings, and near strands with dew framing the top corners."""
    W, H = k.w, k.h; start = len(k.ink)
    portrait = H > W
    w0, w1 = spec['wash']
    if portrait:
        cx, cy, R = W * 1.22, H * 0.8, W * 0.97
        tilt, rot = 0.3, math.radians(36)
    else:
        cx, cy, R = W * 0.62, H * 0.82 + W * 1.25, W * 1.25
        tilt, rot = 0.97, math.radians(-3)
    disc = lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2 < R * R
    dark = _sky_dark(k, spec)
    ang = math.atan2(_focus(k)[1] - cy, _focus(k)[0] - cx)
    k.watercolour(cx + math.cos(ang) * R * 0.88, cy + math.sin(ang) * R * 0.88, W * 0.3, H * (0.15 if portrait else 0.3), w0, 0.8, 5)
    k.watercolour(cx + math.cos(ang) * R * 1.2, cy + math.sin(ang) * R * 1.2, W * 0.35, H * (0.12 if portrait else 0.25), w1, 0.6)
    k.depth = 0.15
    _sky_with_stars(k, spec, dark)
    f0, f1 = (1.1, 1.95) if portrait else (1.05, 1.42)
    fs = [f0 * (f1 / f0) ** (i / 11) for i in range(12)]
    nrad = 64
    trad = [2 * math.pi * i / nrad + k.r.uniform(-0.02, 0.02) for i in range(nrad)]

    def ring_pts(f, t0, t1, n=240):
        return [(t, _ellipse_pt(cx, cy, R * f, R * f * tilt, t, rot)) for t in [t0 + (t1 - t0) * i / n for i in range(n + 1)]]

    def back(t):
        return math.sin(t) < 0

    def web_layer(front):
        ds = []
        for f in fs:
            run = []
            for t, p in ring_pts(f, 0, 2 * math.pi, 400):
                vis = (back(t) != front) and not (back(t) and disc(p))
                if vis and -40 < p[0] < W + 40 and -40 < p[1] < H + 40:
                    run.append(p)
                else:
                    if len(run) > 1: ds.append(k.poly(run, close=False))
                    run = []
            if len(run) > 1: ds.append(k.poly(run, close=False))
        rads = []
        for t in trad:
            if back(t) == front:
                continue
            a = _ellipse_pt(cx, cy, R * 0.98, R * 0.98 * tilt, t, rot); b = _ellipse_pt(cx, cy, R * fs[-1] * 1.08, R * fs[-1] * 1.08 * tilt, t, rot)
            pts = [_lerp(a, b, i / 30) for i in range(31)]
            run = []
            for p in pts:
                if not (back(t) and disc(p)):
                    run.append(p)
                else:
                    if len(run) > 1: rads.append(k.poly(run, close=False))
                    run = []
            if len(run) > 1: rads.append(k.poly(run, close=False))
        return ds, rads
    # back half of the web, behind the planet
    k.depth = 0.35
    ds, rads = web_layer(False)
    _strokes(k, ds, 4.2); _strokes(k, ds, 2.6, white=True)
    _strokes(k, rads, 3.2); _strokes(k, rads, 1.8, white=True)
    nodes_back = []
    for t in trad[::2]:
        if back(t):
            f = k.r.choice(fs[2:9]); p = _ellipse_pt(cx, cy, R * f, R * f * tilt, t, rot)
            if not disc(p) and 0 < p[0] < W and 0 < p[1] < H:
                nodes_back.append((p, t, f))
    for p, t, f in nodes_back:
        _spindle(k, p[0], p[1], min(W, H) * 0.04 * (0.8 + 0.4 * k.r.random()), rot + t + math.pi / 2)
    # settlements: knots of spindles bound by local webbing at a few crossings, kept off the focus
    fxx, fyy = _focus(k)
    cands = [n for n in nodes_back if math.hypot(n[0][0] - fxx, n[0][1] - fyy) > min(W, H) * 0.3]
    k.r.shuffle(cands)
    for p, t, f in cands[:4]:
        s0 = min(W, H) * 0.05
        ds = [_seg(p, (p[0] + math.cos(a) * s0 * 2.4, p[1] + math.sin(a) * s0 * 1.6)) for a in [i * math.pi / 5 + k.r.uniform(-0.2, 0.2) for i in range(10)]]
        for rr in (0.8, 1.4, 2.0):
            ds.append(k.poly([(p[0] + math.cos(a) * s0 * rr * 1.2, p[1] + math.sin(a) * s0 * rr * 0.8) for a in [i * math.pi / 10 for i in range(21)]]))
        _strokes(k, ds, 2.2); _strokes(k, ds, 1.0, white=True)
        for j in range(3):
            a = k.r.uniform(0, 2 * math.pi)
            _spindle(k, p[0] + math.cos(a) * s0 * 1.1, p[1] + math.sin(a) * s0 * 0.7, s0 * k.r.uniform(0.6, 0.9), a + 1.2)
        _spindle(k, p[0], p[1], s0 * 1.1, rot + t + math.pi / 2)
    # the planet
    k.depth = 0.7
    k.paper(f'M{cx - R - 18:.1f},{cy:.1f} a{R + 18:.1f},{R + 18:.1f} 0 1,0 {2 * R + 36:.1f},0 a{R + 18:.1f},{R + 18:.1f} 0 1,0 {-2 * R - 36:.1f},0Z')
    land, clouds = _green_world(k.r)
    _sphere(k, cx, cy, R, tilt=-0.25, rot=-0.35, L=(-0.62, -0.62, 0.2) if portrait else (-0.3, -0.75, 0.25),
            nlat=int(math.pi * R / 6.5), nlon=int(2 * math.pi * R / 9), wmax=1.6, step=8, land=land, clouds=clouds)
    # front half of the web, over the planet: heavier, with white ground lines so it reads over the ruling
    k.depth = 0.75
    ds, rads = web_layer(True)
    _strokes(k, ds, 3.2, white=True); _strokes(k, ds, 1.3)
    _strokes(k, rads, 2.6, white=True); _strokes(k, rads, 0.9)
    for t in trad[1::3]:
        if not back(t):
            f = k.r.choice(fs[:4]); p = _ellipse_pt(cx, cy, R * f, R * f * tilt, t, rot)
            if 0 < p[0] < W and 0 < p[1] < H * 0.75:
                _spindle(k, p[0], p[1], min(W, H) * 0.05, rot + t + math.pi / 2)
    # near strands across the top corners, beaded with dew
    k.depth = 0.95
    strands = [((-20, H * 0.08), (W * 0.42, -20), 0.04), ((-20, H * 0.2), (W * 0.2, -20), 0.03),
               ((W * 0.62, -20), (W + 20, H * (0.12 if portrait else 0.3)), 0.05)]
    for a, b, sag in strands:
        m = ((a[0] + b[0]) / 2 + H * sag * 0.6, (a[1] + b[1]) / 2 + H * sag)
        d = f'M{a[0]:.1f},{a[1]:.1f} Q{m[0]:.1f},{m[1]:.1f} {b[0]:.1f},{b[1]:.1f}'
        k.line(d, 2.4, rough=False)
        k.ink.append(f'<path d="{d}" fill="none" stroke="#fff" stroke-width="1.1"/>')
        beads = ''
        for i in range(1, 14):
            t = i / 14 + k.r.uniform(-0.02, 0.02)
            x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * m[0] + t * t * b[0]
            y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * m[1] + t * t * b[1]
            r = k.r.uniform(1.6, 3.6)
            beads += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#fff" stroke="#000" stroke-width=".8"/>'
                      f'<circle cx="{x - r * 0.35:.1f}" cy="{y - r * 0.35:.1f}" r="{r * 0.3:.1f}" fill="#000"/>')
        k.ink.append(beads)
    _wrap_fade(k, start)

def _box(k, P, x0, x1, y0, y1, z0, z1, tone=2, top_tone=1, side_tone=None, outline=1.0):
    """A box in the room, seen from the eye at the origin: its front, one side and its top or underside."""
    side_tone = tone + 1 if side_tone is None else side_tone
    zc = (z0 + z1) / 2
    faces = []
    if x0 > 0:
        faces.append(([(x0, y0, z1), (x0, y0, z0), (x0, y1, z0), (x0, y1, z1)], side_tone, 'side'))
    elif x1 < 0:
        faces.append(([(x1, y0, z0), (x1, y0, z1), (x1, y1, z1), (x1, y1, z0)], side_tone, 'side'))
    if y0 > 0:
        faces.append(([(x0, y0, z1), (x1, y0, z1), (x1, y0, z0), (x0, y0, z0)], top_tone, 'top'))
    elif y1 < 0:
        faces.append(([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], side_tone, 'under'))
    faces.append(([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], tone, 'front'))
    out = {}
    for pts, t, name in faces:
        q = [P.p(*p) for p in pts]
        ang = {'front': 80, 'side': 15, 'top': 160, 'under': 120}[name]
        if _quiet(k, max(p[1] for p in q)) < 0.5:
            t = min(t, 1)
        k.shape(k.poly(q), tone=t, dark=min(4, t + 1), outline=outline, angle=ang)
        out[name] = q
    return out

def _screen(k, q, lines=5):
    """A lit display: a white quad with a dark bezel and faint scan rules."""
    k.ink.append(f'<path d="{k.poly(q)}" fill="#fff" stroke="#000" stroke-width="{0.8 + 0.8 * k.depth:.1f}"/>')
    ds = []
    for i in range(1, lines + 1):
        t = i / (lines + 1)
        a, b = _lerp(q[0], q[3], t), _lerp(q[1], q[2], t)
        e = k.r.uniform(0.3, 0.9)
        ds.append(_seg(_lerp(a, b, 0.1), _lerp(a, b, e)))
    _strokes(k, ds, 0.6, opacity=0.7)

def _pod(k, P, X, z, dz, ytop, ybot, side, db):
    """A suspension pod standing against the wall plane x=X: a rounded capsule with a frosted window."""
    def rr(u0, u1, v0, v1, ru, rv, n=6):
        pts = []
        corners = [(u1 - ru, v0 + rv, -math.pi / 2, 0), (u1 - ru, v1 - rv, 0, math.pi / 2),
                   (u0 + ru, v1 - rv, math.pi / 2, math.pi), (u0 + ru, v0 + rv, math.pi, 1.5 * math.pi)]
        for cu, cv, a0, a1 in corners:
            for i in range(n + 1):
                a = a0 + (a1 - a0) * i / n
                pts.append(P.p(X, cv + math.sin(a) * rv, cu + math.cos(a) * ru))
        return pts
    h = ybot - ytop
    shell = rr(z, z + dz, ytop, ybot, dz * 0.42, h * 0.2)
    k.shape(k.smooth(shell), tone=2 + db, dark=4, outline=1.2, angle=88 if side < 0 else 92)
    # base plinth and lid seam
    win = rr(z + dz * 0.16, z + dz * 0.84, ytop + h * 0.1, ytop + h * 0.62, dz * 0.28, h * 0.12)
    wd = k.smooth(win)
    k.ink.append(f'<path d="{wd}" fill="#fff" stroke="#000" stroke-width="{0.8 + 1.2 * k.depth:.1f}"/>')
    # frost: stipple settling at the window's lower edge, and a diagonal glint
    xs = [p[0] for p in win]; ys = [p[1] for p in win]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    rx, ry = (max(xs) - min(xs)) / 2, (max(ys) - min(ys)) / 2
    dots = []
    for _ in range(int(40 + rx * ry * 0.05)):
        x = cx + k.r.uniform(-0.85, 0.85) * rx; y = cy + ry * (1 - k.r.random() ** 2 * 1.4)
        if y < cy + ry * 0.92:
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{k.r.uniform(0.4, 1.0):.2f}"/>')
    k.ink.append(f'<g fill="#000" opacity=".7">{"".join(dots)}</g>')
    _strokes(k, [_seg((cx - rx * 0.5, cy - ry * 0.1), (cx - rx * 0.1, cy - ry * 0.7)), _seg((cx - rx * 0.25, cy + ry * 0.1), (cx + rx * 0.05, cy - ry * 0.35))], 0.6, opacity=0.6)
    # lid seam and status lamp
    seam = [P.p(X, ytop + h * 0.72, z + dz * 0.1), P.p(X, ytop + h * 0.72, z + dz * 0.9)]
    _strokes(k, [_seg(*seam)], 1.2)
    lp = P.p(X, ytop + h * 0.82, z + dz * 0.5)
    r = max(1.2, 5 * k.depth / z ** 0.5)
    k.ink.append(f'<circle cx="{lp[0]:.1f}" cy="{lp[1]:.1f}" r="{r:.1f}" fill="#fff" stroke="#000" stroke-width="1"/>')
    return (cx, cy, rx, ry)

def cryo_bay(k, spec):
    """The sleepers' hall: a long, low hull bay with rows of suspension pods standing against both walls,
    their windows frosted, cable runs sagging overhead, a sealed round door at the far end."""
    W, H = k.w, k.h; start = len(k.ink)
    fx, fy = _focus(k)
    portrait = H > W
    P = _Persp(fx + W * 0.02, fy - H * (0.02 if portrait else 0.08))
    a = W * (0.7 if portrait else 0.5); b = a * (0.62 if portrait else 0.45); c = a * 0.26
    sec = _octagon(a, b, c)
    zf = 6.0 if portrait else 5.0
    ribs = _ribs(k, 0.45, zf, 1.5, 1.6)
    db = 1 if _night(spec) else 0
    _washes(k, spec, [(P.vx, P.vy, W * 0.2, H * 0.08, 0, 0.6), (W * 0.15, H * 0.45, W * 0.2, H * 0.2, 1, 0.5),
                      (W * 0.85, H * 0.42, W * 0.2, H * 0.2, 0, 0.45)])
    zs = [0.2] + ribs + [zf]
    _shell_panels(k, P, sec, zs, [3, 2, 2, 2, 1, 1, 2, 2], db, zf, a, b, floor='plates', patch=0.2)
    # far wall: a round sealed door
    k.depth = 0.15
    fq = [P.p(x, y, zf) for x, y in sec]
    k.shape(k.poly(fq), tone=2 + db, dark=3 + db, outline=0.8, angle=90)
    dc = P.p(0, b * 0.15, zf); dr = b * 0.72 / zf
    k.shape(f'M{dc[0] - dr * 1.18:.1f},{dc[1]:.1f} a{dr * 1.18:.1f},{dr * 1.18:.1f} 0 1,0 {dr * 2.36:.1f},0 a{dr * 1.18:.1f},{dr * 1.18:.1f} 0 1,0 {-dr * 2.36:.1f},0Z',
            tone=3, dark=4, outline=0.8, angle=45)
    k.ink.append(f'<circle cx="{dc[0]:.1f}" cy="{dc[1]:.1f}" r="{dr:.1f}" fill="#fff" stroke="#000" stroke-width="1"/>')
    _strokes(k, [_seg((dc[0] + math.cos(t) * dr * 0.2, dc[1] + math.sin(t) * dr * 0.2), (dc[0] + math.cos(t) * dr * 0.95, dc[1] + math.sin(t) * dr * 0.95)) for t in [i * math.pi / 4 for i in range(8)]], 0.6)
    k.ink.append(f'<circle cx="{dc[0]:.1f}" cy="{dc[1]:.1f}" r="{dr * 0.2:.1f}" fill="none" stroke="#000" stroke-width="1.2"/>')
    # pods against each wall, far to near, two per bay
    pods = []
    for i in range(len(zs) - 2, 0, -1):
        z0, z1 = zs[i], zs[i + 1]
        for f in (0.55, 0.08):
            zz = z0 + (z1 - z0) * f; dz = (z1 - z0) * 0.38
            pods.append((zz, dz))
    pods.sort(key=lambda p: -p[0])
    glows = []
    for zz, dz in pods:
        k.depth = _depth_of(zz, 0.45, zf)
        for side in (-1, 1):
            X = side * a * 0.97
            g = _pod(k, P, X, zz, dz, -b * 0.62, b * 0.98, side, db)
            if zz > 0.7:
                glows.append(g)
    # sagging cable runs across the ceiling between frames
    k.depth = 0.6
    ds = []
    for z in ribs[1:]:
        for off in (-0.05, 0.04):
            p0, p1 = P.p(-a + c * 0.5, -b + c * 0.5, z * (1 + off)), P.p(a - c * 0.5, -b + c * 0.5, z * (1 + off))
            sag = (p1[0] - p0[0]) * 0.07
            ds.append(f'M{p0[0]:.1f},{p0[1]:.1f} Q{(p0[0] + p1[0]) / 2:.1f},{(p0[1] + p1[1]) / 2 + sag * 2:.1f} {p1[0]:.1f},{p1[1]:.1f}')
    _strokes(k, ds, 1.3)
    _shell_frames(k, P, sec, ribs, zf, db, a, b, c, th=0.06)
    # the light: pods glow into the aisle
    if spec.get('light') in ('screen-glow', 'firelight'):
        for cx, cy, rx, ry in glows[-4:]:
            k.watercolour(cx, cy, rx * 1.6, ry * 1.3, spec['wash'][0 if spec['light'] == 'screen-glow' else 1], 0.55, 3)
        _light_pool(k, spec, dc[0], dc[1], dr * 1.6, n=18, reach=1.4)
    _wrap_fade(k, start)

def _viewport_space(k, x0, y0, x1, y1, spec):
    """What a viewport shows: ruled dark sky with stars and the lit limb of the green world low in it."""
    W, H = k.w, k.h
    dark = _sky_dark(k, spec, base=0.82, halo=0.5)
    inside = lambda x, y: x0 < x < x1 and y0 < y < y1
    _sky_with_stars(k, spec, dark, inside=inside, n=int((x1 - x0) * (y1 - y0) / 1800), big=3)
    R = (x1 - x0) * 1.6
    cx, cy = x0 + (x1 - x0) * 0.62, y1 - (y1 - y0) * 0.4 + R
    k.depth = 0.35
    land, clouds = _green_world(k.r)
    _sphere(k, cx, cy, R, tilt=-0.25, rot=-0.2, L=(-0.5, -0.75, 0.45), nlat=int(math.pi * R / 5), nlon=int(2 * math.pi * R / 8),
            wmax=1.4, step=6, land=land, clouds=clouds, clip=(x0, y0, x1, y1), atmos=False)

def control_room(k, spec):
    """The ark's command deck: a broad, low room ending in a great segmented viewport onto space and the green
    world, banks of consoles with lit screens along both sides and a long desk under the window."""
    W, H = k.w, k.h; start = len(k.ink)
    fx, fy = _focus(k)
    portrait = H > W
    P = _Persp(fx - W * 0.02, fy + H * (0.02 if portrait else 0.0))
    a = W * (0.85 if portrait else 0.62); b = a * (0.62 if portrait else 0.38); c = a * 0.22
    sec = _octagon(a, b, c)
    zf = 1.9
    ribs = [0.42, 0.62, 0.9, 1.3]
    db = 1 if _night(spec) else 0
    w0, w1 = spec['wash']
    zs = [0.2] + ribs + [zf]
    _shell_panels(k, P, sec, zs, [3, 3, 2, 2, 1, 1, 2, 3], db, zf, a, b, floor='plates', patch=0.1, slots=False)
    # far wall with the viewport
    k.depth = 0.2
    fq = [P.p(x, y, zf) for x, y in sec]
    k.shape(k.poly(fq), tone=3 + db, dark=4, outline=0.9, angle=90)
    vx0, vy0 = P.p(-a * 0.9, -b * 0.88, zf); vx1, vy1 = P.p(a * 0.9, b * 0.5, zf)
    k.paper(k.poly([(vx0, vy0), (vx1, vy0), (vx1, vy1), (vx0, vy1)]))
    k.watercolour((vx0 + vx1) / 2, (vy0 + vy1) / 2, (vx1 - vx0) * 0.5, (vy1 - vy0) * 0.6, w1, 0.6, 4)
    _viewport_space(k, vx0, vy0, vx1, vy1, spec)
    # mullions: a heavy frame and curved ribs dividing the glass into panes
    k.depth = 0.3
    mw = (vx1 - vx0) * 0.018
    for t in (0.0, 0.34, 0.68, 1.0):
        x = vx0 + (vx1 - vx0) * t
        k.shape(k.poly([(x - mw, vy0), (x + mw, vy0), (x + mw, vy1), (x - mw, vy1)]), tone=3, dark=4, outline=0.8, angle=88)
    for t in (0.0, 1.0):
        y = vy0 + (vy1 - vy0) * t
        k.shape(k.poly([(vx0, y - mw), (vx1, y - mw), (vx1, y + mw), (vx0, y + mw)]), tone=3, dark=4, outline=0.8, angle=5)
    k.ink.append(f'<path d="M{vx0 + (vx1 - vx0) * 0.03:.1f},{vy0 + (vy1 - vy0) * 0.08:.1f} L{vx0 + (vx1 - vx0) * 0.2:.1f},{vy0 + (vy1 - vy0) * 0.08:.1f}" stroke="#fff" stroke-width="2"/>')
    # long desk beneath the viewport
    k.depth = 0.35
    desk = _box(k, P, -a * 0.55, a * 0.4, b * 0.66, b, zf * 0.8, zf * 0.9, tone=2 + db, top_tone=1)
    for u0 in (0.12, 0.42, 0.72):
        tq = desk['top']
        q = [_lerp(_lerp(tq[3], tq[2], u0), _lerp(tq[0], tq[1], u0), 0.2), _lerp(_lerp(tq[3], tq[2], u0 + 0.2), _lerp(tq[0], tq[1], u0 + 0.2), 0.2)]
        h = (vy1 - vy0) * 0.12
        _screen(k, [(q[0][0], q[0][1] - h), (q[1][0], q[1][1] - h), q[1], q[0]], 3)
    # side console banks, far to near, with sloped tops carrying screens
    for z0, z1 in ((1.45, 1.95), (0.95, 1.35), (0.62, 0.88)):
        k.depth = _depth_of(z0, 0.42, zf)
        for side in (-1, 1):
            xi, xo = side * a * 0.58, side * a * 0.98
            x0, x1 = min(xi, xo), max(xi, xo)
            f = _box(k, P, x0, x1, b * 0.5, b, z0, z1, tone=2 + db, top_tone=1)
            # sloped screen panel standing on the inner edge of the console
            sx = xi
            q = [P.p(sx, b * 0.5, z0 + 0.04 * z0), P.p(sx, b * 0.5, z1 - 0.04 * z0), P.p(sx + side * a * 0.12, b * 0.05, z1 - 0.04 * z0), P.p(sx + side * a * 0.12, b * 0.05, z0 + 0.04 * z0)]
            k.shape(k.poly(q), tone=3 + db, dark=4, outline=1.0, angle=10)
            inner = [_lerp(q[0], q[2], 0.1), _lerp(q[1], q[3], 0.1), _lerp(q[2], q[0], 0.1), _lerp(q[3], q[1], 0.1)]
            _screen(k, [inner[3], inner[2], inner[1], inner[0]] if side > 0 else inner, 4)
            # knobs on the console top
            if 'side' in f:
                sq = f['side']
                _strokes(k, [_seg(_lerp(sq[0], sq[3], v), _lerp(sq[1], sq[2], v)) for v in (0.2, 0.26, 0.32)], 0.8)
            top = f.get('top')
            if top:
                dots = ''.join(f'<circle cx="{_lerp(_lerp(top[0], top[1], u), _lerp(top[3], top[2], u), v)[0]:.1f}" cy="{_lerp(_lerp(top[0], top[1], u), _lerp(top[3], top[2], u), v)[1]:.1f}" r="{max(0.8, 3 * k.depth):.1f}"/>'
                               for u in (0.25, 0.5, 0.75) for v in (0.3, 0.7))
                k.ink.append(f'<g fill="#fff" stroke="#000" stroke-width=".8">{dots}</g>')
            if spec.get('light') == 'screen-glow' and z0 < 1.0:
                cx = sum(p[0] for p in q) / 4; cy = sum(p[1] for p in q) / 4
                _light_pool(k, spec, cx, cy, abs(q[2][0] - q[0][0]) + 20, n=10, a0=(-0.6 if side < 0 else math.pi - 0.6) - 0.4, a1=(0.6 if side < 0 else math.pi + 0.6) + 0.4, reach=0.9)
    _shell_frames(k, P, sec, ribs, zf, db, a, b, c, th=0.05)
    _wrap_fade(k, start)

def _cloth(k, top_l, top_r, drop, folds=6, tone=1):
    """A hanging cloth (curtain, tarp, washing): a draped top edge, a ragged hem, vertical fold rules."""
    (x0, y0), (x1, y1) = top_l, top_r
    sag = (x1 - x0) * 0.08
    hem = []
    for i in range(folds * 2 + 1):
        t = i / (folds * 2)
        hem.append((x0 + (x1 - x0) * t + k.r.uniform(-2, 2), y0 + (y1 - y0) * t + drop * (1 + 0.06 * math.sin(i * 1.7)) + (6 if i % 2 else 0)))
    d = (f'M{x0:.1f},{y0:.1f} Q{(x0 + x1) / 2:.1f},{(y0 + y1) / 2 + sag:.1f} {x1:.1f},{y1:.1f} '
         + ' '.join(f'L{x:.1f},{y:.1f}' for x, y in hem[::-1]) + 'Z')
    k.shape(d, tone=tone, dark=tone + 2, outline=0.9, angle=k.r.choice((80, 95, 100)))
    ds = []
    for i in range(1, folds * 2):
        t = i / (folds * 2)
        x = x0 + (x1 - x0) * t; ytop = y0 + (y1 - y0) * t + sag * 4 * t * (1 - t)
        ds.append(f'M{x:.1f},{ytop:.1f} q{k.r.uniform(-3, 3):.1f},{drop * 0.5:.1f} {k.r.uniform(-4, 4):.1f},{drop * 0.95:.1f}')
    _strokes(k, ds, 0.7)

def _lamp(k, spec, x, y, s, cord_top=-20):
    """A hanging work lamp: cord, conical shade (dark outside, white inside), a glowing bulb."""
    k.line(f'M{x:.1f},{cord_top:.1f} L{x:.1f},{y - s * 0.5:.1f}', 1.2, rough=False)
    shade = f'M{x - s * 0.18:.1f},{y - s * 0.5:.1f} L{x + s * 0.18:.1f},{y - s * 0.5:.1f} L{x + s * 0.7:.1f},{y + s * 0.15:.1f} L{x - s * 0.7:.1f},{y + s * 0.15:.1f}Z'
    k.shape(shade, tone=3, dark=4, outline=1.2, angle=70)
    k.ink.append(f'<ellipse cx="{x:.1f}" cy="{y + s * 0.15:.1f}" rx="{s * 0.7:.1f}" ry="{s * 0.12:.1f}" fill="#fff" stroke="#000" stroke-width="1.2"/>'
                 f'<circle cx="{x:.1f}" cy="{y + s * 0.2:.1f}" r="{s * 0.16:.1f}" fill="#fff" stroke="#000" stroke-width="1"/>')
    k.ink.append(f'<path d="M{x - s * 0.1:.1f},{y - s * 0.4:.1f} L{x - s * 0.5:.1f},{y + s * 0.08:.1f}" stroke="#fff" stroke-width="1.6"/>')

def ship_quarters(k, spec):
    """Crew quarters inside the hull: a low ribbed dormitory, two-tier bunks down both walls, curtains and patched
    tarps hung for privacy, washing on a line, lockers at the far end, a work lamp hanging in front."""
    W, H = k.w, k.h; start = len(k.ink)
    fx, fy = _focus(k)
    portrait = H > W
    P = _Persp(fx - W * 0.07, fy - H * (0.03 if portrait else 0.08))
    a = W * (0.78 if portrait else 0.55); b = a * (0.6 if portrait else 0.44); c = a * 0.3
    sec = _octagon(a, b, c)
    zf = 4.6 if portrait else 4.0
    ribs = _ribs(k, 0.45, zf, 1.45, 1.55)
    db = 1 if _night(spec) else 0
    w0, w1 = spec['wash']
    _washes(k, spec, [(P.vx, P.vy, W * 0.22, H * 0.1, 1, 0.6), (W * 0.2, H * 0.42, W * 0.22, H * 0.18, 0, 0.5),
                      (W * 0.82, H * 0.38, W * 0.2, H * 0.18, 1, 0.45)])
    zs = [0.2] + ribs + [zf]
    _shell_panels(k, P, sec, zs, [3, 2, 2, 2, 1, 1, 2, 2], db, zf, a, b, floor='plates', patch=0.35, slots=False)
    # far wall: lockers
    k.depth = 0.15
    fq = [P.p(x, y, zf) for x, y in sec]
    k.shape(k.poly(fq), tone=2 + db, dark=3 + db, outline=0.8, angle=90)
    for i in range(7):
        x0 = -a * 0.62 + i * a * 0.18
        q = [P.p(x0, -b * 0.45, zf), P.p(x0 + a * 0.16, -b * 0.45, zf), P.p(x0 + a * 0.16, b * 0.98, zf), P.p(x0, b * 0.98, zf)]
        k.shape(k.poly(q), tone=1 + (i % 3 == 1), dark=3, outline=0.7, angle=88)
        _strokes(k, [_seg(_lerp(q[0], q[1], 0.25), _lerp(q[0], q[1], 0.75)).replace('M', 'M') for _ in range(1)] +
                 [_seg(_lerp(_lerp(q[0], q[3], v), _lerp(q[1], q[2], v), 0.2), _lerp(_lerp(q[0], q[3], v), _lerp(q[1], q[2], v), 0.8)) for v in (0.08, 0.11, 0.14)], 0.6)
    _shell_frames(k, P, sec, ribs, zf, db, a, b, c, th=0.06)
    # bunks: two long tiers down each wall, in front of the frames
    zb0, zb1 = zs[1] * 0.75, zf * 0.93
    for side in (-1, 1):
        xo, xi = side * a * 0.99, side * a * 0.52
        x0, x1 = min(xo, xi), max(xo, xi)
        k.depth = 0.7
        # deep shadow under the lower tier
        k.shape(k.poly([P.p(xi, b * 0.56, zb0), P.p(xi, b * 0.56, zb1), P.p(xi, b, zb1), P.p(xi, b, zb0)]), tone=3 + db, dark=4, outline=0.8, angle=side * 20 + 90)
        for ylev in (b * 0.48, -b * 0.16):
            f = _box(k, P, x0, x1, ylev, ylev + b * 0.08, zb0, zb1, tone=2 + db, top_tone=1, side_tone=3 + db)
            if ylev > 0:
                # blankets and pillows, bay by bay, on the lower tier
                for zi in range(len(zs) - 2, 0, -1):
                    za, zc = max(zs[zi] * 1.05, zb0), min(zs[zi + 1] * 0.95, zb1)
                    if zc <= za:
                        continue
                    k.depth = _depth_of(za, 0.45, zf)
                    q = [P.p(xi, ylev, za), P.p(xi, ylev, zc), P.p(xo, ylev, zc), P.p(xo, ylev, za)]
                    hump = -b * 0.1 / za
                    d = (f'M{q[0][0]:.1f},{q[0][1]:.1f} C{q[0][0]:.1f},{q[0][1] + hump:.1f} {q[1][0]:.1f},{q[1][1] + hump * 1.2:.1f} {q[1][0]:.1f},{q[1][1]:.1f} '
                         f'L{q[2][0]:.1f},{q[2][1]:.1f} L{q[3][0]:.1f},{q[3][1]:.1f}Z')
                    k.shape(d, tone=1, dark=3, outline=0.9, angle=k.r.choice((30, 60, 120, 150)))
                    pil = _lerp(_lerp(q[1], q[2], 0.6), _lerp(q[0], q[3], 0.6), 0.15)
                    pr_ = math.dist(q[1], q[0]) * 0.16 + 3
                    k.shape(k.blob(pil[0], pil[1] + hump * 0.4, pr_, pr_ * 0.45, n=10, jitter=0.12), tone=0, dark=2, outline=0.9)
        # posts at each frame, and curtains hung from the upper tier
        for z in [zb0] + [r for r in ribs if zb0 < r < zb1] + [zb1]:
            k.depth = _depth_of(z, 0.45, zf)
            _strokes(k, [_seg(P.p(xi, -b * 0.18, z), P.p(xi, b, z))], 2.8)
        for zi in range(len(zs) - 2, 0, -1):
            za, zc = max(zs[zi] * 1.05, zb0), min(zs[zi + 1] * 0.95, zb1)
            if zc <= za or k.r.random() < 0.4:
                continue
            k.depth = _depth_of(za, 0.45, zf)
            zm = za + (zc - za) * k.r.uniform(0.0, 0.35)
            tl, tr = P.p(xi, -b * 0.08, zm), P.p(xi, -b * 0.08, zc)
            if tl[0] > tr[0]:
                tl, tr = tr, tl
            drop = (P.p(xi, b * 0.46, zm)[1] - P.p(xi, -b * 0.08, zm)[1]) * k.r.uniform(0.75, 1.0)
            _cloth(k, tl, tr, drop, folds=4, tone=1 + (k.r.random() < 0.4))
    # a washing line strung across the room mid-way, cloths pegged on it
    k.depth = 0.6
    zl = zs[2] * 1.1 if len(zs) > 3 else 1.2
    pl, pr = P.p(-a * 0.52, -b * 0.5, zl), P.p(a * 0.52, -b * 0.46, zl * 1.15)
    mid = ((pl[0] + pr[0]) / 2, (pl[1] + pr[1]) / 2 + (pr[0] - pl[0]) * 0.07)
    k.line(f'M{pl[0]:.1f},{pl[1]:.1f} Q{mid[0]:.1f},{mid[1]:.1f} {pr[0]:.1f},{pr[1]:.1f}', 1.1, rough=False)
    def qb(t):
        return ((1 - t) ** 2 * pl[0] + 2 * (1 - t) * t * mid[0] + t * t * pr[0], (1 - t) ** 2 * pl[1] + 2 * (1 - t) * t * mid[1] + t * t * pr[1])
    for t, wd, dr in ((0.06, 0.12, 0.6), (0.22, 0.08, 0.9), (0.74, 0.12, 0.7), (0.88, 0.08, 1.0)):
        _cloth(k, qb(t), qb(t + wd), (pr[0] - pl[0]) * 0.07 * dr, folds=3, tone=k.r.choice((1, 2)))
    # the work lamp, hung toward the upper right, with its pool of light
    lx, ly = W * 0.78, H * (0.17 if portrait else 0.26)
    k.depth = 0.9
    _lamp(k, spec, lx, ly, W * (0.07 if portrait else 0.05))
    if spec.get('light') in ('firelight', 'night', 'screen-glow', 'dusk'):
        k.watercolour(lx, ly + H * 0.08, W * 0.25, H * 0.14, w1 if spec.get('light') != 'screen-glow' else w0, 0.6, 4)
        ds = []
        for i in range(14):
            ang = math.pi * (0.15 + 0.7 * (i + 0.5) / 14)
            ds.append(_seg((lx + math.cos(ang) * W * 0.06, ly + math.sin(ang) * W * 0.06), (lx + math.cos(ang) * W * 0.3, ly + math.sin(ang) * W * 0.3)))
        _strokes(k, ds, 0.5, opacity=0.3)
    _wrap_fade(k, start)

def hangar(k, spec):
    """The shuttle bay: a tall, wide hull hall under transverse gantry girders, a crane trolley, cargo stacked
    along one wall, a fuel tank on the other, painted guide lines on the deck, and the great bay door half raised
    onto stars."""
    W, H = k.w, k.h; start = len(k.ink)
    fx, fy = _focus(k)
    portrait = H > W
    P = _Persp(fx + W * 0.03, fy + H * (0.04 if portrait else 0.02))
    a = W * (0.95 if portrait else 0.7); b = a * (0.8 if portrait else 0.5); c = a * 0.2
    sec = _octagon(a, b, c)
    zf = 3.6
    ribs = _ribs(k, 0.5, zf, 1.4, 1.5)
    db = 1 if _night(spec) else 0
    w0, w1 = spec['wash']
    zs = [0.2] + ribs + [zf]
    _shell_panels(k, P, sec, zs, [3, 2, 2, 2, 1, 1, 2, 2], db, zf, a, b, floor='plates', patch=0.3, slots=False)
    # far wall and bay door opening onto space
    k.depth = 0.15
    fq = [P.p(x, y, zf) for x, y in sec]
    k.shape(k.poly(fq), tone=2 + db, dark=3 + db, outline=0.8, angle=90)
    ox0, oy0 = P.p(-a * 0.7, -b * 0.72, zf); ox1, oy1 = P.p(a * 0.7, b, zf)
    k.paper(k.poly([(ox0, oy0), (ox1, oy0), (ox1, oy1), (ox0, oy1)]))
    k.watercolour((ox0 + ox1) / 2, (oy0 + oy1) / 2, (ox1 - ox0) * 0.5, (oy1 - oy0) * 0.5, w1, 0.6, 4)
    _viewport_space(k, ox0, oy0, ox1, oy1, spec)
    # door shutter: slats raised into the top of the opening
    k.depth = 0.2
    sh = (oy1 - oy0) * 0.16
    k.shape(k.poly([(ox0, oy0), (ox1, oy0), (ox1, oy0 + sh), (ox0, oy0 + sh)]), tone=2 + db, dark=4, outline=1.0, angle=3)
    _strokes(k, [_seg((ox0, oy0 + sh * t), (ox1, oy0 + sh * t)) for t in (0.2, 0.4, 0.6, 0.8)], 1.2)
    k.ink.append(f'<path d="M{ox0:.1f},{oy0 + sh + 1:.1f} L{ox1:.1f},{oy0 + sh + 1:.1f}" stroke="#000" stroke-width="3"/>')
    # door jambs with hazard chevrons
    jw = (ox1 - ox0) * 0.035
    for x in (ox0 - jw, ox1):
        k.shape(k.poly([(x, oy0), (x + jw, oy0), (x + jw, oy1), (x, oy1)]), tone=1, dark=2, outline=0.9, angle=0)
        ch = []
        n = int((oy1 - oy0) / (jw * 1.2))
        for i in range(n):
            y = oy0 + i * jw * 1.2
            ch.append(f'M{x:.1f},{y:.1f} L{x + jw:.1f},{y + jw * 0.6:.1f} L{x + jw:.1f},{y + jw * 1.0:.1f} L{x:.1f},{y + jw * 0.4:.1f}Z')
        k.ink.append(f'<path d="{"".join(ch)}" fill="#000"/>')
    # painted deck lines: a centre line of dashes and the edges of the landing lane
    k.depth = 0.5
    ds = []
    for xl in (-a * 0.42, a * 0.42):
        ds.append(_seg(P.p(xl, b, 0.3), P.p(xl, b, zf)))
    _strokes(k, ds, 1.4)
    dash = []
    z = 0.35
    while z < zf * 0.95:
        q = [P.p(-a * 0.025, b, z), P.p(a * 0.025, b, z), P.p(a * 0.025, b, z * 1.08), P.p(-a * 0.025, b, z * 1.08)]
        if _quiet(k, q[0][1]) > 0.3:
            dash.append(k.poly(q))
        z *= 1.2
    k.ink.append(f'<path d="{"".join(dash)}" fill="#000" opacity=".8"/>')
    # cargo stacked on the left, a fuel tank on the right
    for (x0, x1, y0, z0, z1) in ((-a * 0.98, -a * 0.68, b * 0.55, 1.5, 1.9), (-a * 0.98, -a * 0.74, b * 0.1, 1.55, 1.85),
                                 (-a * 0.95, -a * 0.62, b * 0.6, 0.9, 1.2), (-a * 0.98, -a * 0.7, b * 0.2, 0.92, 1.15)):
        k.depth = _depth_of(z0, 0.5, zf)
        f = _box(k, P, x0, x1, y0, y0 + (b - y0) if y0 > b * 0.4 else b * 0.55, z0, z1, tone=2 + db, top_tone=1)
        fr = f['front']
        _strokes(k, [_seg(fr[0], fr[2]), _seg(fr[1], fr[3])], 0.8)
    k.depth = 0.6
    tz0, tz1 = 1.0, 1.6
    tz0, tz1 = 1.2, 2.0
    tx, ty, tr = a * 0.66, b * 0.7, b * 0.28
    top = [P.p(tx, ty - tr, z) for z in (tz0, tz1)]; bot = [P.p(tx, ty + tr, z) for z in (tz0, tz1)]
    end = P.p(tx, ty, tz0); er = tr / tz0
    k.shape(k.poly([top[0], top[1], bot[1], bot[0]]), tone=2 + db, dark=4, outline=1.0, angle=5)
    _strokes(k, [_seg(P.p(tx, ty - tr * f, tz0), P.p(tx, ty - tr * f, tz1)) for f in (0.6, 0.2, -0.2, -0.5, -0.75)], 0.6)
    k.shape(f'M{end[0] - er * 0.45:.1f},{end[1]:.1f} a{er * 0.45:.1f},{er:.1f} 0 1,0 {er * 0.9:.1f},0 a{er * 0.45:.1f},{er:.1f} 0 1,0 {-er * 0.9:.1f},0Z', tone=1, dark=3, outline=1.2, angle=60)
    # gantry girders across the roof at each frame, a crane trolley on the nearest
    _shell_frames(k, P, sec, ribs, zf, db, a, b, c, th=0.05)
    for j, z in enumerate(ribs[1:]):
        k.depth = _depth_of(z, 0.5, zf)
        y = -b * 0.86
        pa, pb = P.p(-a + c * 0.4, y, z), P.p(a - c * 0.4, y, z)
        h = b * 0.1 / z
        _truss(k, ((pa[0], pa[1] + h / 2)), (pb[0], pb[1] + h / 2), h, h, n=18, tone_w=0.6 + 0.6 * k.depth)
        if j == 1:
            cx = pa[0] + (pb[0] - pa[0]) * 0.28
            lo = pa[1] + h
            k.shape(k.poly([(cx - h * 0.9, lo), (cx + h * 0.9, lo), (cx + h * 0.7, lo + h), (cx - h * 0.7, lo + h)]), tone=3, dark=4, outline=1.0, angle=70)
            hook_y = lo + h + (fy - lo) * 0.35
            _strokes(k, [_seg((cx - h * 0.25, lo + h), (cx - h * 0.25, hook_y)), _seg((cx + h * 0.25, lo + h), (cx + h * 0.25, hook_y))], 0.9)
            k.ink.append(f'<path d="M{cx:.1f},{hook_y:.1f} q{-h * 0.6:.1f},{h * 0.3:.1f} {-h * 0.35:.1f},{h * 0.85:.1f} q{h * 0.35:.1f},{h * 0.45:.1f} {h * 0.65:.1f},0" fill="none" stroke="#000" stroke-width="{2 + 2 * k.depth:.1f}"/>')
            k.ink.append(f'<path d="M{cx - h * 0.4:.1f},{hook_y - 2:.1f} L{cx + h * 0.4:.1f},{hook_y - 2:.1f}" stroke="#000" stroke-width="{3 + 2 * k.depth:.1f}"/>')
    # daylight from the bay: ruled shafts on the deck
    if spec.get('light') in ('day', 'dawn', 'dusk'):
        k.depth = 0.3
        _strokes(k, [_seg(((ox0 + ox1) / 2 + (ox1 - ox0) * u * 0.5, oy1), (P.vx + (ox1 - ox0) * u * 3.0, H * 0.75)) for u in (-0.8, -0.4, 0, 0.4, 0.8)], 0.5, opacity=0.35)
    _light_pool(k, spec, (ox0 + ox1) / 2, (oy0 + oy1) / 2, (ox1 - ox0) * 0.4, n=18)
    _wrap_fade(k, start)

def _vessel(k, x, y, s, kind):
    """Laboratory glass standing on (x, y), height ~s: white glass, a ruled liquid, highlight and outline."""
    if kind == 'round':
        r = s * 0.32
        body = (f'M{x - s * 0.06:.1f},{y - s:.1f} L{x - s * 0.06:.1f},{y - r * 1.9:.1f} A{r:.1f},{r:.1f} 0 1,0 {x + s * 0.06:.1f},{y - r * 1.9:.1f} '
                f'L{x + s * 0.06:.1f},{y - s:.1f}Z')
        liq = f'M{x - r * 0.92:.1f},{y - r * 0.6:.1f} A{r:.1f},{r:.1f} 0 0,0 {x + r * 0.92:.1f},{y - r * 0.6:.1f}Z'
        hl = f'M{x - r * 0.6:.1f},{y - r * 1.3:.1f} q{r * 0.1:.1f},{-r * 0.4:.1f} {r * 0.45:.1f},{-r * 0.55:.1f}'
    elif kind == 'cone':
        body = (f'M{x - s * 0.07:.1f},{y - s:.1f} L{x - s * 0.07:.1f},{y - s * 0.62:.1f} L{x - s * 0.36:.1f},{y:.1f} '
                f'L{x + s * 0.36:.1f},{y:.1f} L{x + s * 0.07:.1f},{y - s * 0.62:.1f} L{x + s * 0.07:.1f},{y - s:.1f}Z')
        liq = f'M{x - s * 0.25:.1f},{y - s * 0.24:.1f} L{x + s * 0.25:.1f},{y - s * 0.24:.1f} L{x + s * 0.36:.1f},{y:.1f} L{x - s * 0.36:.1f},{y:.1f}Z'
        hl = f'M{x - s * 0.2:.1f},{y - s * 0.1:.1f} L{x - s * 0.05:.1f},{y - s * 0.5:.1f}'
    else:   # jar with a lid
        wj = s * 0.28
        body = f'M{x - wj:.1f},{y - s * 0.85:.1f} L{x + wj:.1f},{y - s * 0.85:.1f} L{x + wj:.1f},{y:.1f} L{x - wj:.1f},{y:.1f}Z'
        liq = f'M{x - wj:.1f},{y - s * 0.5:.1f} L{x + wj:.1f},{y - s * 0.5:.1f} L{x + wj:.1f},{y:.1f} L{x - wj:.1f},{y:.1f}Z'
        hl = f'M{x - wj * 0.6:.1f},{y - s * 0.75:.1f} L{x - wj * 0.6:.1f},{y - s * 0.1:.1f}'
        k.solid(f'M{x - wj * 1.1:.1f},{y - s * 0.85:.1f} L{x + wj * 1.1:.1f},{y - s * 0.85:.1f} L{x + wj * 1.1:.1f},{y - s:.1f} L{x - wj * 1.1:.1f},{y - s:.1f}Z')
    k.paper(body)
    k.shape(liq, tone=2, dark=4, outline=0.6, angle=0, rough=False)
    k.ink.append(f'<path d="{body}" fill="none" stroke="#000" stroke-width="{0.6 + 0.8 * k.depth:.1f}" stroke-linejoin="round"/>')
    k.ink.append(f'<path d="{hl}" fill="none" stroke="#000" stroke-width="0.6" opacity=".6"/>')

def lab(k, spec):
    """A worn ship's laboratory: shelves of jars and flasks down one wall, a long bench of glassware and a coil
    still on the other, a tall specimen tank, framed diagrams on the far bulkhead, a hanging lamp."""
    W, H = k.w, k.h; start = len(k.ink)
    fx, fy = _focus(k)
    portrait = H > W
    P = _Persp(fx + W * 0.05, fy - H * (0.03 if portrait else 0.08))
    a = W * (0.75 if portrait else 0.55); b = a * (0.62 if portrait else 0.44); c = a * 0.28
    sec = _octagon(a, b, c)
    zf = 3.4
    ribs = _ribs(k, 0.45, zf, 1.5, 1.6)
    db = 1 if _night(spec) else 0
    w0, w1 = spec['wash']
    _washes(k, spec, [(W * 0.25, H * 0.35, W * 0.25, H * 0.18, 0, 0.6), (W * 0.75, H * 0.4, W * 0.22, H * 0.2, 1, 0.55),
                      (P.vx, P.vy, W * 0.2, H * 0.1, 0, 0.4)])
    zs = [0.2] + ribs + [zf]
    _shell_panels(k, P, sec, zs, [3, 2, 2, 2, 1, 1, 2, 2], db, zf, a, b, floor='plates', patch=0.3, slots=True)
    # far bulkhead with framed diagrams (orbits, a cell, a spiral)
    k.depth = 0.15
    fq = [P.p(x, y, zf) for x, y in sec]
    k.shape(k.poly(fq), tone=2 + db, dark=3 + db, outline=0.8, angle=90)
    for x0, x1, y0, y1, kind in ((-a * 0.6, -a * 0.22, -b * 0.6, -b * 0.05, 0), (-a * 0.12, a * 0.3, -b * 0.7, -b * 0.15, 1), (a * 0.38, a * 0.66, -b * 0.5, b * 0.05, 2)):
        q = [P.p(x0, y0, zf), P.p(x1, y0, zf), P.p(x1, y1, zf), P.p(x0, y1, zf)]
        k.ink.append(f'<path d="{k.poly(q)}" fill="#fff" stroke="#000" stroke-width="1.4"/>')
        cx, cy = (q[0][0] + q[2][0]) / 2, (q[0][1] + q[2][1]) / 2; r = (q[1][0] - q[0][0]) * 0.32
        if kind == 0:
            ds = [f'M{cx - r * f:.1f},{cy:.1f} a{r * f:.1f},{r * f * 0.6:.1f} 0 1,0 {2 * r * f:.1f},0 a{r * f:.1f},{r * f * 0.6:.1f} 0 1,0 {-2 * r * f:.1f},0' for f in (0.4, 0.75, 1.1)]
            k.ink.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r * 0.15:.1f}"/>')
        elif kind == 1:
            ds = [f'M{cx - r:.1f},{cy:.1f} a{r:.1f},{r * 0.8:.1f} 0 1,0 {2 * r:.1f},0 a{r:.1f},{r * 0.8:.1f} 0 1,0 {-2 * r:.1f},0',
                  f'M{cx - r * 0.3:.1f},{cy:.1f} a{r * 0.3:.1f},{r * 0.3:.1f} 0 1,0 {r * 0.6:.1f},0 a{r * 0.3:.1f},{r * 0.3:.1f} 0 1,0 {-r * 0.6:.1f},0']
        else:
            ds = [k.poly([(cx + math.cos(t) * r * t / 12, cy + math.sin(t) * r * t / 12) for t in [i * 0.2 for i in range(60)]], close=False)]
        _strokes(k, ds, 0.7)
    # left wall: shelves of jars, bay by bay
    for i in range(len(zs) - 2, 0, -1):
        z0, z1 = zs[i] * 1.05, zs[i + 1] * 0.95
        k.depth = _depth_of(z0, 0.45, zf)
        X = -a * 0.97
        for ys in (-b * 0.45, -b * 0.05, b * 0.35):
            board = [P.p(X, ys, z0), P.p(X, ys, z1), P.p(X + a * 0.16, ys, z1), P.p(X + a * 0.16, ys, z0)]
            k.shape(k.poly(board), tone=2, dark=3, outline=0.9, angle=0)
            n = 3 + int(3 * (z1 - z0) / z0)
            for j in range(n, 0, -1):
                zz = z0 + (z1 - z0) * (j - 0.5) / n
                px, py = P.p(X + a * 0.09, ys, zz)
                s = b * 0.27 / zz
                _vessel(k, px, py, s, k.r.choice(('jar', 'jar', 'round', 'cone')))
    _shell_frames(k, P, sec, ribs, zf, db, a, b, c, th=0.06)
    # right: long bench with glassware, and a tall specimen tank near the front
    k.depth = 0.6
    bz0, bz1 = 0.8, 2.2
    f = _box(k, P, a * 0.45, a * 0.98, b * 0.42, b, bz0, bz1, tone=2 + db, top_tone=1)
    for j in range(7, 0, -1):
        zz = bz0 + (bz1 - bz0) * (j - 0.5) / 7
        px, py = P.p(a * 0.6 + a * 0.12 * (j % 2), b * 0.42, zz)
        k.depth = _depth_of(zz, 0.45, zf)
        _vessel(k, px, py, b * 0.36 / zz, ('round', 'cone', 'jar', 'round', 'cone', 'jar', 'round')[j - 1])
    # coil still: a spiral of tube rising from the bench
    k.depth = 0.7
    sx, sy = P.p(a * 0.7, b * 0.42, 1.05)
    sr = b * 0.12 / 1.05
    pts = [(sx + math.cos(t) * sr, sy - sr * 0.2 - t * sr * 0.12) for t in [i * 0.25 for i in range(90)]]
    k.line(k.poly(pts, close=False), 1.4, rough=False)
    k.line(f'M{pts[-1][0]:.1f},{pts[-1][1]:.1f} Q{pts[-1][0] - sr * 2:.1f},{pts[-1][1] - sr:.1f} {sx - sr * 3.5:.1f},{sy - sr * 0.4:.1f}', 1.4, rough=False)
    # specimen tank: a cylinder with ruled liquid and a dim shape suspended in it
    k.depth = 0.9
    tx, ty0, ty1 = W * (0.88 if portrait else 0.9), H * (0.22 if portrait else 0.1), H * (0.62 if portrait else 0.95)
    tw = W * (0.1 if portrait else 0.07)
    k.paper(k.poly([(tx - tw, ty0), (tx + tw, ty0), (tx + tw, ty1), (tx - tw, ty1)]))
    k.shape(k.poly([(tx - tw, ty0 + (ty1 - ty0) * 0.18), (tx + tw, ty0 + (ty1 - ty0) * 0.18), (tx + tw, ty1), (tx - tw, ty1)]), tone=1, dark=3, outline=0, angle=0, rough=False)
    blob = k.blob(tx, ty0 + (ty1 - ty0) * 0.5, tw * 0.45, (ty1 - ty0) * 0.16, n=10, jitter=0.25)
    k.shape(blob, tone=3, dark=4, outline=0.8, angle=60)
    bub = ''.join(f'<circle cx="{tx + k.r.uniform(-0.7, 0.7) * tw:.1f}" cy="{ty0 + (ty1 - ty0) * k.r.uniform(0.22, 0.9):.1f}" r="{k.r.uniform(1, 3):.1f}" fill="#fff" stroke="#000" stroke-width=".7"/>' for _ in range(14))
    k.ink.append(bub)
    for yy in (ty0, ty1):
        k.shape(f'M{tx - tw * 1.12:.1f},{yy - tw * 0.18:.1f} L{tx + tw * 1.12:.1f},{yy - tw * 0.18:.1f} L{tx + tw * 1.12:.1f},{yy + tw * 0.18:.1f} L{tx - tw * 1.12:.1f},{yy + tw * 0.18:.1f}Z', tone=3, dark=4, outline=1.1, angle=80)
    k.ink.append(f'<path d="M{tx - tw * 1.0:.1f},{ty0:.1f} L{tx - tw * 1.0:.1f},{ty1:.1f} M{tx + tw:.1f},{ty0:.1f} L{tx + tw:.1f},{ty1:.1f}" stroke="#000" stroke-width="1.6"/>')
    k.ink.append(f'<path d="M{tx - tw * 0.7:.1f},{ty0 + tw * 0.4:.1f} L{tx - tw * 0.7:.1f},{ty1 - tw * 0.4:.1f}" stroke="#fff" stroke-width="2.4"/>')
    # a lamp over the bench
    lx, ly = W * (0.66 if portrait else 0.7), H * (0.14 if portrait else 0.18)
    k.depth = 0.85
    _lamp(k, spec, lx, ly, W * (0.06 if portrait else 0.045))
    if spec.get('light') in ('night', 'firelight', 'dusk', 'screen-glow'):
        k.watercolour(lx, ly + H * 0.1, W * 0.22, H * 0.14, w1, 0.65, 4)
        _strokes(k, [_seg((lx + math.cos(t) * W * 0.05, ly + math.sin(t) * W * 0.05), (lx + math.cos(t) * W * 0.28, ly + math.sin(t) * W * 0.28)) for t in [math.pi * (0.2 + 0.6 * i / 11) for i in range(12)]], 0.5, opacity=0.3)
    _wrap_fade(k, start)

BACKDROPS = {
    'ship-corridor': ship_corridor,
    'planet-orbit': planet_orbit,
    'deep-space': deep_space,
    'station-exterior': station_exterior,
    'orbital-web': orbital_web,
    'cryo-bay': cryo_bay,
    'control-room': control_room,
    'ship-quarters': ship_quarters,
    'hangar': hangar,
    'lab': lab,
}

"""Quasar engraving engine: ink line art with a pastel wash, generated from a chapter's scene spec.

Every motif draws into an Ink object: shapes are outlined and shaded with hatching that follows the light,
far layers lighter than near ones. A separate wash layer holds soft pastel tints. Both render to PNGs:
the ink as an alpha mask (the app tints it per reading theme) and the wash in colour.
"""
import math, random

class Ink:
    def __init__(self, w, h, seed=0, light=(-0.6, -0.8)):
        self.w, self.h = w, h
        self.defs, self.ink, self.wash = [], [], []
        self.r = random.Random(seed)
        self.light = light
        self._ids = 0
        self.depth = 1.0          # 0 = far (thin, light), 1 = near (heavy)

    # ---------- ids and patterns ----------
    def uid(self, p='i'):
        self._ids += 1; return f'{p}{self._ids}'

    def hatch(self, angle, gap, width):
        pid = self.uid('h')
        self.defs.append(f'<pattern id="{pid}" width="{gap:.2f}" height="{gap:.2f}" patternUnits="userSpaceOnUse" '
                         f'patternTransform="rotate({angle:.1f})"><line x1="0" y1="0" x2="0" y2="{gap:.2f}" '
                         f'stroke="#000" stroke-width="{width:.2f}"/></pattern>')
        return pid

    def tone_fills(self, tone, angle=40):
        """Pattern ids for a tone 0..4: 1 sparse, 2 medium, 3 cross, 4 dense cross. Depth thins the lines."""
        d = 0.55 + 0.45 * self.depth
        out = []
        if tone >= 1: out.append(self.hatch(angle, [0, 6.0, 4.4, 3.6, 3.0][min(tone, 4)], 0.75 * d))
        if tone >= 3: out.append(self.hatch(angle - 70, 4.6 - (tone - 3) * 1.2, 0.7 * d))
        if tone >= 4: out.append(self.hatch(angle + 35, 3.2, 0.6 * d))
        return out

    # ---------- primitives ----------
    def shape(self, d, tone=1, dark=3, outline=1.0, angle=None, light=None, clip=None, rough=True, knock=True):
        """A filled form: base tone everywhere, darker hatching fading in toward the shadow side, outlined."""
        angle = self.r.uniform(25, 55) if angle is None else angle
        lx, ly = light or self.light
        g = [f'<path d="{d}" fill="#fff"/>'] if knock else []
        for pid in self.tone_fills(tone, angle):
            g.append(f'<path d="{d}" fill="url(#{pid})"/>')
        if dark > tone:
            mid = self.uid('m'); grad = self.uid('g')
            # gradient runs from the lit side (transparent) to the shadow side (opaque)
            x1, y1, x2, y2 = 0.5 + lx * 0.5, 0.5 + ly * 0.5, 0.5 - lx * 0.5, 0.5 - ly * 0.5
            self.defs.append(f'<linearGradient id="{grad}" x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}">'
                             f'<stop offset="0.35" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>'
                             f'<mask id="{mid}" maskContentUnits="objectBoundingBox"><rect width="1" height="1" fill="url(#{grad})"/></mask>')
            dg = ''.join(f'<path d="{d}" fill="url(#{pid})"/>' for pid in self.tone_fills(dark, angle + 8)[len(self.tone_fills(0)):] )
            g.append(f'<g mask="url(#{mid})">{dg}</g>')
        if outline:
            g.append(f'<path d="{d}" fill="none" stroke="#000" stroke-width="{outline * (0.5 + 0.6 * self.depth):.2f}" stroke-linejoin="round"/>')
        cl = f' clip-path="url(#{clip})"' if clip else ''
        self.ink.append(f'<g{cl}{" filter=\"url(#rough)\"" if rough else ""}>{"".join(g)}</g>')

    def solid(self, d, outline=0):
        self.ink.append(f'<path d="{d}" fill="#000"/>')

    def line(self, d, w=1.0, opacity=1.0, rough=True):
        self.ink.append(f'<path d="{d}" fill="none" stroke="#000" stroke-width="{w * (0.5 + 0.6 * self.depth):.2f}" '
                        f'stroke-linecap="round" stroke-opacity="{opacity}"{" filter=\"url(#rough)\"" if rough else ""}/>')

    def paper(self, d):
        """Knock out ink beneath a nearer form (so near shapes occlude far hatching)."""
        self.ink.append(f'<path d="{d}" fill="#fff"/>')

    def stipple(self, cx, cy, rx, ry, n, size=(0.6, 1.6)):
        dots = []
        for _ in range(n):
            a = self.r.uniform(0, 2 * math.pi); t = math.sqrt(self.r.random())
            x, y = cx + math.cos(a) * rx * t, cy + math.sin(a) * ry * t
            dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{self.r.uniform(*size):.2f}"/>')
        self.ink.append(f'<g fill="#000">{"".join(dots)}</g>')

    def tint(self, d, color, opacity=0.55, blur=10):
        b = min((4, 10, 20, 40), key=lambda v: abs(v - blur))
        self.wash.append(f'<path d="{d}" fill="{color}" opacity="{opacity}" filter="url(#soft{b})"/>')

    def watercolour(self, cx, cy, rx, ry, color, opacity=0.5, n=4):
        """Pooled pastel: a few overlapping irregular blobs, darker where they overlap, like a hand-tint."""
        for i in range(n):
            self.tint(self.blob(cx + self.r.uniform(-rx, rx) * 0.3, cy + self.r.uniform(-ry, ry) * 0.3,
                                rx * self.r.uniform(0.55, 1.0), ry * self.r.uniform(0.55, 1.0), n=12, jitter=0.25),
                      color, opacity / n * 1.8, self.r.choice((10, 20)))

    # ---------- geometry helpers ----------
    @staticmethod
    def poly(pts, close=True):
        return 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts) + ('Z' if close else '')

    @staticmethod
    def smooth(pts, close=True):
        """Catmull-Rom through points, as cubic Beziers."""
        n = len(pts); P = pts + pts[:3] if close else [pts[0]] + pts + [pts[-1]]
        d = f'M{pts[0][0]:.1f},{pts[0][1]:.1f}'
        rng = range(n) if close else range(n - 1)
        for i in rng:
            p0, p1, p2, p3 = (P[i - 1] if close else P[i]), P[i] if close else P[i + 1], P[i + 1] if close else P[i + 2], P[i + 2] if close else P[i + 3]
            if close: p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            d += f' C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}'
        return d + ('Z' if close else '')

    def blob(self, cx, cy, rx, ry, n=14, jitter=0.18):
        pts = []
        for k in range(n):
            a = k / n * 2 * math.pi; s = 1 + self.r.uniform(-jitter, jitter)
            pts.append((cx + math.cos(a) * rx * s, cy + math.sin(a) * ry * s))
        return self.smooth(pts)

    def leafmarks(self, x0, x1, y0, y1, n):
        """Engraver's leaf texture: short curled ticks scattered in a band."""
        d = []
        for _ in range(n):
            x, y = self.r.uniform(x0, x1), self.r.uniform(y0, y1); s = self.r.uniform(4, 9); a = self.r.uniform(-0.6, 0.6)
            d.append(f'M{x:.1f},{y:.1f} q{s * math.cos(a):.1f},{-s * 0.8:.1f} {s * 1.6 * math.cos(a):.1f},{s * 0.2:.1f}')
        self.ink.append(f'<path d="{" ".join(d)}" fill="none" stroke="#000" stroke-width="{0.5 + 0.5 * self.depth:.2f}" stroke-linecap="round" filter="url(#rough)"/>')

    def foliage(self, x0, x1, y, depth, lobes, top=-60):
        """A hanging foliage mass: off-frame top edge, a lower edge of downward lobes."""
        step = (x1 - x0) / lobes
        d = f'M{x0:.1f},{top:.1f} L{x0:.1f},{y:.1f}'
        for i in range(lobes):
            xa = x0 + i * step; xb = xa + step
            ya = y + self.r.uniform(-depth * 0.5, depth * 0.5)
            dip = depth * self.r.uniform(0.6, 1.4)
            d += f' C{xa + step * 0.1:.1f},{ya + dip:.1f} {xb - step * 0.1:.1f},{ya + dip:.1f} {xb:.1f},{y + self.r.uniform(-depth * 0.4, depth * 0.4):.1f}'
        return d + f' L{x1:.1f},{top:.1f}Z'

    def scallop(self, x0, x1, y, depth, lobes, up=True):
        """A foliage edge: a run of rounded lobes."""
        pts = [(x0, y + (depth * 3 if up else -depth * 3))]
        step = (x1 - x0) / lobes
        for i in range(lobes + 1):
            x = x0 + i * step
            pts.append((x, y + self.r.uniform(-depth * 0.4, depth * 0.4)))
        pts.append((x1, y + (depth * 3 if up else -depth * 3)))
        d = f'M{pts[0][0]:.1f},{pts[0][1]:.1f} L{pts[1][0]:.1f},{pts[1][1]:.1f}'
        for i in range(1, len(pts) - 2):
            (xa, ya), (xb, yb) = pts[i], pts[i + 1]
            bulge = -depth if up else depth
            d += f' Q{(xa + xb) / 2:.1f},{min(ya, yb) + bulge * self.r.uniform(0.8, 1.3):.1f} {xb:.1f},{yb:.1f}'
        d += f' L{pts[-1][0]:.1f},{pts[-1][1]:.1f}Z'
        return d

    # ---------- output ----------
    def svg(self, layer):
        defs = ''.join(self.defs)
        filt = ('<filter id="rough" x="-5%" y="-5%" width="110%" height="110%"><feTurbulence type="fractalNoise" baseFrequency=".035" numOctaves="2" seed="3"/>'
                '<feDisplacementMap in="SourceGraphic" scale="2.4"/></filter>'
                + ''.join(f'<filter id="soft{b}" x="-20%" y="-20%" width="140%" height="140%"><feTurbulence type="fractalNoise" baseFrequency=".02" numOctaves="3" seed="{b}"/>'
                          f'<feDisplacementMap in="SourceGraphic" scale="{b * 2}"/><feGaussianBlur stdDeviation="{b}"/></filter>' for b in (4, 10, 20, 40)))
        body = ''.join(self.ink) if layer == 'ink' else ''.join(self.wash)
        bg = '<rect width="100%" height="100%" fill="#fff"/>' if layer == 'ink' else ''
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}">'
                f'<defs>{filt}{defs}</defs>{bg}{body}</svg>')

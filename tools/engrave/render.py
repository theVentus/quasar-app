"""Render a scene's ink and wash layers to PNG with headless Chromium."""
import io, os, sys, json
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

class Renderer:
    def __enter__(self):
        self.p = sync_playwright().start(); self.b = self.p.chromium.launch(); return self
    def __exit__(self, *a):
        self.b.close(); self.p.stop()
    def png(self, svg, w, h, scale=1.0):
        pg = self.b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=scale)
        pg.set_content(f'<html><body style="margin:0;background:transparent">{svg}</body></html>')
        data = pg.screenshot(omit_background=True, clip={'x': 0, 'y': 0, 'width': w, 'height': h})
        pg.close()
        return Image.open(io.BytesIO(data)).convert('RGBA')

def ink_mask(img):
    """Black-on-white ink to a white-on-transparent alpha mask (tinted in the app)."""
    g = img.convert('L'); a = ImageChops.invert(g)
    out = Image.new('LA', img.size, 255); out.putalpha(a); return out

def preview(ink, wash, paper=(244, 236, 216), ink_rgb=(43, 52, 40), wash_alpha=0.85):
    """Composite for review: paper, wash, then ink."""
    base = Image.new('RGBA', ink.size, paper + (255,))
    w = wash.copy(); w.putalpha(w.getchannel('A').point(lambda v: int(v * wash_alpha)))
    base = Image.alpha_composite(base, w)
    layer = Image.new('RGBA', ink.size, ink_rgb + (255,)); layer.putalpha(ink.getchannel('A'))
    return Image.alpha_composite(base, layer)

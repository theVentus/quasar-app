#!/usr/bin/env python3
"""Builds the test EPUBs in content/fixtures/ from original text written for this repo.

- field-guide-epub2.epub mirrors a Calibre conversion: EPUB 2, OPF at the root, `index_split_NNN.html`
  spine files, toc.ncx with filepos anchors, a <guide>, and the cover found through <meta name="cover">.
- field-guide-epub3.epub is a clean EPUB 3: OEBPS/ folder, nav.xhtml with a nested contents list,
  and a manifest item with properties="cover-image".

Run: python3 tools/make-fixture-epubs.py   (needs Pillow)
"""
import io, os, zipfile
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(__file__), "..", "content", "fixtures")
TITLE = "A Field Guide to Light"
AUTHOR = "Mira Okonjo"   # fictional

CHAPTERS = [
    ("The Patient Messenger", [
        "Light is the most patient messenger in the universe. It leaves a star, crosses distances that make a continent look like a grain of sand, and arrives without having aged a moment of its own. Everything we know about the sky beyond our atmosphere was carried here this way, one photon at a time, by a courier that never stops to rest.",
        "Stand outside on a clear night and the sky looks like a single picture. It is not. The nearest star you can see sent its light a few years ago; the faint smudge of a neighbouring galaxy sent its light before there were people to look up. The night sky is a collage of departures, each glued to the same dark page at a different date.",
        "This is the first idea of the guide, and the one everything else leans on: *seeing is always seeing the past*. The delay is tiny for the lamp across the room and enormous for the quasar at the edge of the observable universe, but it is never zero. Once you notice it, you cannot stop noticing it.",
        "The second idea is that the delay is useful. If a messenger always travels at the same speed, the time it takes to arrive tells you how far it came. Sailors once used the gap between a cannon's flash and its boom to estimate the distance to a ship. Engineers now do the same thing with radio pulses and atomic clocks, and the gap they measure is a few hundredths of a second.",
        "A few hundredths of a second is long enough to measure and short enough to get wrong. Most of the craft in this guide is about getting it right: knowing which clock started the stopwatch, which path the signal took, and what slowed it down along the way.",
    ]),
    ("Clocks That Disagree", [
        "Every clock is a counter attached to something that repeats. A pendulum swings, a quartz crystal rings, a caesium atom flips between two energy states. The counter does not know what time it is; it only knows how many repetitions have happened since someone set it going.",
        "Two clocks set together will drift apart. The drift may be a second a month for a cheap watch or a second in a hundred million years for the best laboratory standard, but it is always there. A navigator who forgets this will find their position wandering across the map for no reason they can see.",
        "* * *",
        "There is a stranger kind of disagreement too. A clock that moves quickly ticks slowly when seen from the ground, and a clock high above the Earth, where gravity is weaker, ticks fast. Neither clock is broken. Each keeps perfect time where it is; the disagreement is a property of the space between them.",
        "For a satellite the two effects pull in opposite directions and do not cancel. The net result is a few tens of microseconds a day, which sounds like nothing until you multiply by the speed of light and discover it is several kilometres of error, accumulating every single day.",
        "The fix is almost comically simple. Before launch, the satellite's clock is tuned to run very slightly slow, so that once it is in orbit it appears to tick at exactly the right rate. The physics is subtle; the engineering is a single number written into a frequency synthesiser.",
    ]),
    ("Listening to the Edge of the Sky", [
        "To check the clocks, and the shape of the Earth they sit on, astronomers turn to the most distant objects they can find. Quasars are galaxies whose centres blaze so brightly that they outshine everything around them, and they are so far away that they do not appear to move at all.",
        "Two radio dishes on different continents point at the same quasar and record its noise. The same wavefront reaches one dish a little before the other. Line the two recordings up, find the delay, and you have measured the distance between the dishes along the direction of the quasar, to within a few millimetres.",
        "Do this with many dishes and many quasars and the measurements knit together into a reference frame: a fixed scaffold against which the Earth's wobble, the length of the day and the positions of the ground stations can all be checked.",
        "It is a pleasing loop. The phone in your pocket finds its position from satellites; the satellites are tracked from stations on the ground; the stations are tied to quasars billions of light years away. The patient messenger closes the circle.",
    ]),
]


def cover_jpeg():
    w, h = 1000, 1500
    im = Image.new("RGB", (w, h), (18, 24, 44))
    d = ImageDraw.Draw(im)
    for r in range(80, 1400, 70):
        d.ellipse((760 - r, 260 - r, 760 + r, 260 + r), outline=(80 + r // 30, 100 + r // 25, 150), width=2)
    d.ellipse((740, 240, 780, 280), fill=(255, 236, 200))
    d.ellipse((230, 780, 330, 880), fill=(120, 160, 240))
    try:
        f1 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 92)
        f2 = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 44)
    except OSError:
        f1 = f2 = ImageFont.load_default()
    d.text((80, 1040), "A Field Guide", font=f1, fill=(245, 240, 228))
    d.text((80, 1150), "to Light", font=f1, fill=(245, 240, 228))
    d.text((84, 1300), AUTHOR.upper(), font=f2, fill=(200, 190, 170))
    b = io.BytesIO(); im.save(b, "JPEG", quality=80); return b.getvalue()


def diagram_png():
    im = Image.new("RGB", (800, 300), (250, 248, 242))
    d = ImageDraw.Draw(im)
    d.line((60, 150, 740, 150), fill=(60, 60, 60), width=3)
    d.ellipse((40, 130, 80, 170), fill=(240, 200, 120))
    d.ellipse((720, 130, 760, 170), fill=(90, 130, 220))
    for x in range(140, 700, 80):
        d.arc((x - 40, 90, x + 40, 210), -60, 60, fill=(120, 140, 190), width=2)
    b = io.BytesIO(); im.save(b, "PNG"); return b.getvalue()


def para_html(p):
    import re
    p = p.replace("&", "&amp;").replace("<", "&lt;")
    p = re.sub(r"\*(.+?)\*", r"<i>\1</i>", p)
    if p.strip() == "* * *":
        return '<p class="calibre_3">* * *</p>'
    return f'<p class="calibre_12">{p}</p>'


CSS = """.calibre { display: block; font-size: 1em; text-align: justify; margin: 0 5pt }
.calibre_3 { display: block; text-align: center; text-indent: 0; margin: 1em 0 }
.calibre_5 { display: block; font-weight: bold; text-align: center; text-indent: 0; margin: 15% 0 1.33em; font-size: 1.4em }
.calibre_12 { display: block; text-indent: 1em; margin: 0 }
.figure { display: block; text-align: center; margin: 1em 0 }
"""


def xhtml(title, body, css="stylesheet.css", epub3=False):
    ns = ' xmlns:epub="http://www.idpf.org/2007/ops"' if epub3 else ""
    return f"""<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml"{ns}>
<head><title>{title}</title><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>
<link href="{css}" rel="stylesheet" type="text/css"/></head>
<body class="calibre">
{body}
</body></html>
"""


def write_zip(path, files):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        for name, data in files:
            z.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED)


def epub2():
    files = [("META-INF/container.xml", """<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
   <rootfiles><rootfile full-path="content.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>""")]
    files.append(("cover1.jpeg", cover_jpeg()))
    files.append(("images/00001.png", diagram_png()))
    files.append(("stylesheet.css", CSS))
    files.append(("titlepage.xhtml", xhtml("Cover", '<div style="text-align:center"><img src="cover1.jpeg" alt="cover" style="height:100%"/></div>')))
    spine = ["titlepage.xhtml"]
    nav = []
    files.append(("index_split_000.html", xhtml(TITLE, f'<p class="calibre_3"><b>{TITLE}</b></p><p class="calibre_3">{AUTHOR}</p>')))
    spine.append("index_split_000.html")
    pos = 100
    for i, (name, paras) in enumerate(CHAPTERS, start=1):
        fn = f"index_split_{i:03d}.html"
        body = f'<div><a id="filepos{pos}"></a></div>\n<h4 class="calibre_5">{i}<br/>{name.upper()}</h4>\n'
        body += "\n".join(para_html(p) for p in paras)
        if i == 1:
            body += '\n<div class="figure"><img src="images/00001.png" alt="A signal crossing between two points"/></div>'
        files.append((fn, xhtml(TITLE, body)))
        spine.append(fn)
        nav.append((f"{i} {name.upper()}", f"{fn}#filepos{pos}"))
        pos += 4000
    manifest = '<item href="cover1.jpeg" id="cover" media-type="image/jpeg"/>\n'
    manifest += '<item href="images/00001.png" id="added" media-type="image/png"/>\n'
    manifest += '<item href="stylesheet.css" id="css" media-type="text/css"/>\n'
    manifest += '<item href="toc.ncx" id="ncx" media-type="application/x-dtbncx+xml"/>\n'
    for k, s in enumerate(spine):
        manifest += f'<item href="{s}" id="id{k}" media-type="application/xhtml+xml"/>\n'
    itemrefs = "".join(f'<itemref idref="id{k}"/>' for k in range(len(spine)))
    opf = f"""<?xml version='1.0' encoding='utf-8'?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="uuid_id" version="2.0">
  <metadata xmlns:calibre="http://calibre.kovidgoyal.net/2009/metadata" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">
    <dc:title>{TITLE}</dc:title>
    <dc:creator opf:file-as="Okonjo, Mira" opf:role="aut">{AUTHOR}</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="uuid_id" opf:scheme="uuid">7d3b1c9e-0f6a-4c55-9a1e-qbd-fixture-2</dc:identifier>
    <meta name="cover" content="cover"/>
    <meta name="calibre:series" content="Quasar Fixtures"/>
    <meta name="calibre:series_index" content="1"/>
  </metadata>
  <manifest>
{manifest}  </manifest>
  <spine toc="ncx">{itemrefs}</spine>
  <guide>
    <reference href="titlepage.xhtml" title="Cover" type="cover"/>
    <reference href="index_split_001.html#filepos100" title="1 THE PATIENT MESSENGER" type="text"/>
  </guide>
</package>"""
    points = "".join(f"""<navPoint id="n{k}" playOrder="{k + 1}"><navLabel><text>{t}</text></navLabel><content src="{src}"/></navPoint>"""
                     for k, (t, src) in enumerate(nav))
    ncx = f"""<?xml version='1.0' encoding='utf-8'?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1" xml:lang="en">
<head><meta content="7d3b1c9e" name="dtb:uid"/><meta content="1" name="dtb:depth"/></head>
<docTitle><text>{TITLE}</text></docTitle>
<navMap>{points}</navMap></ncx>"""
    files += [("content.opf", opf), ("toc.ncx", ncx)]
    write_zip(os.path.join(ROOT, "field-guide-epub2.epub"), files)


def epub3():
    files = [("META-INF/container.xml", """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="OEBPS/package.opf" media-type="application/oebps-package+xml"/></rootfiles>
</container>""")]
    files.append(("OEBPS/images/cover.jpg", cover_jpeg()))
    files.append(("OEBPS/css/book.css", CSS))
    spine = []
    for i, (name, paras) in enumerate(CHAPTERS, start=1):
        fn = f"text/chapter {i}.xhtml"   # a space, to exercise percent-encoded hrefs
        body = f'<section epub:type="chapter"><h1 id="c{i}" class="calibre_5">{name}</h1>\n'
        half = len(paras) // 2
        body += "\n".join(para_html(p) for p in paras[:half])
        body += f'\n<h2 id="c{i}s2">Part two</h2>\n' + "\n".join(para_html(p) for p in paras[half:]) + "</section>"
        files.append(("OEBPS/" + fn, xhtml(name, body, css="../css/book.css", epub3=True)))
        spine.append(fn)
    items = "".join(f"""<li><a href="{s.replace(' ', '%20')}#c{k + 1}">{CHAPTERS[k][0]}</a><ol><li><a href="{s.replace(' ', '%20')}#c{k + 1}s2">Part two</a></li></ol></li>"""
                    for k, s in enumerate(spine))
    nav = f"""<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Contents</title></head>
<body><nav epub:type="toc" id="toc"><h1>Contents</h1><ol>{items}</ol></nav>
<nav epub:type="landmarks" hidden="hidden"><ol><li><a epub:type="bodymatter" href="text/chapter%201.xhtml">Start</a></li></ol></nav></body></html>"""
    files.append(("OEBPS/nav.xhtml", nav))
    manifest = '<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n'
    manifest += '<item id="cover-img" href="images/cover.jpg" media-type="image/jpeg" properties="cover-image"/>\n'
    manifest += '<item id="css" href="css/book.css" media-type="text/css"/>\n'
    for k, s in enumerate(spine):
        manifest += f'<item id="ch{k + 1}" href="{s.replace(" ", "%20")}" media-type="application/xhtml+xml"/>\n'
    itemrefs = "".join(f'<itemref idref="ch{k + 1}"/>' for k in range(len(spine)))
    opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="pub-id" xml:lang="en">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:identifier id="pub-id">urn:uuid:5e0c2a7b-qbd-fixture-3</dc:identifier>
    <dc:title>{TITLE}</dc:title>
    <dc:creator id="a1">{AUTHOR}</dc:creator>
    <dc:language>en</dc:language>
    <meta property="dcterms:modified">2026-11-03T00:00:00Z</meta>
  </metadata>
  <manifest>
{manifest}  </manifest>
  <spine>{itemrefs}</spine>
</package>"""
    files.append(("OEBPS/package.opf", opf))
    write_zip(os.path.join(ROOT, "field-guide-epub3.epub"), files)


def fixture_package():
    """A qbd.book/1 package for CI screenshots: book.json + the EPUB 2 fixture."""
    import json, shutil
    d = os.path.join(ROOT, "fixture-books", "field-guide")
    os.makedirs(d, exist_ok=True)
    shutil.copy(os.path.join(ROOT, "field-guide-epub2.epub"), os.path.join(d, "book.epub"))
    json.dump({"schema": "qbd.book/1", "id": "field-guide", "subtitle": "Clocks, signals and the edge of the sky",
               "theme": {"accent": "#F2CDA7", "accentDeep": "#8A5A2B", "onAccent": "#3A2410", "landing": "cover"},
               "contents": {"style": "outline", "titleCase": True}, "startAt": "index_split_001.html",
               "about": "A short guide to the one idea that underlies every map, clock and satellite: light takes time to arrive. In three chapters it follows a signal from a distant quasar to the phone in your pocket, and shows why a few billionths of a second matter.\n\nWritten for readers with no physics beyond school, it keeps the maths to a single equation and the wonder intact.",
               "praise": [{"quote": "The clearest short account of why timing is everything.", "source": "Quasar Fixtures"},
                          {"quote": "A small book that makes the sky feel close.", "source": "Sample Review"}],
               "awards": "Sample book for Quasar",
               "scenes": [{"web": 0.1, "ship": 0.05, "pod": False, "spider": False, "signal": 0.4},
                          {"web": 0.6, "ship": 0.5, "pod": True, "spider": True, "signal": 1},
                          {"web": 1, "ship": 1, "pod": True, "spider": True, "signal": 1, "orbit": True}]},
              open(os.path.join(d, "book.json"), "w"), indent=2)


if __name__ == "__main__":
    os.makedirs(ROOT, exist_ok=True)
    epub2(); epub3(); fixture_package()
    print("wrote", os.listdir(ROOT))

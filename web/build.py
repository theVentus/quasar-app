"""Build the single-file web course: inline the subset Computer Modern fonts into src.html.

Usage: python3 web/build.py   (writes web/dist/quasar-to-blue-dot.html)
"""
import base64
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent
FACES = [
    ("CMU Serif", "cmu-serif-500-roman", "normal", 400), ("CMU Serif", "cmu-serif-500-italic", "italic", 400),
    ("CMU Serif", "cmu-serif-700-roman", "normal", 700), ("CMU Serif", "cmu-serif-700-italic", "italic", 700),
    ("CMU Typewriter", "cmu-typewriter-text-500-roman", "normal", 400),
    ("CMU Concrete", "cmu-concrete-500-roman", "normal", 400), ("CMU Concrete", "cmu-concrete-500-italic", "italic", 400),
    ("CMU Concrete", "cmu-concrete-700-roman", "normal", 700),
    ("CMU Sans Serif", "cmu-sans-serif-500-roman", "normal", 400), ("CMU Sans Serif", "cmu-sans-serif-500-italic", "italic", 400),
    ("CMU Sans Serif", "cmu-sans-serif-700-roman", "normal", 700),
]


def main():
    css = []
    for fam, fn, style, weight in FACES:
        b64 = base64.b64encode((ROOT / "fonts" / f"{fn}.woff2").read_bytes()).decode()
        css.append(f"@font-face{{font-family:'{fam}';src:url(data:font/woff2;base64,{b64}) format('woff2');font-style:{style};font-weight:{weight};font-display:swap}}")
    src = (ROOT / "src.html").read_text(encoding="utf-8")
    out = ROOT / "dist" / "quasar-to-blue-dot.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(src.replace("/*FONTS*/", "\n".join(css), 1), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()

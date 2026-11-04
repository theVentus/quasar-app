# Engraving style guide (for motif authors)

Look: a 19th-century book engraving, hand-tinted with a pastel wash. Ink is black on white in the SVG (rendered to
an alpha mask the app tints); colour lives only in the wash layer. Reference implementation: motifs.py
(forest_canopy, web, spider, fern, vine, trunk). Toolkit: core.py (do not edit; add helpers in your own module).

Rules
- Depth: set k.depth before drawing each layer: ~0.15 far, ~0.5 mid, ~0.95 near. Far = lighter tone (1–2), thinner
  lines; near = heavier (2–4) with darker shadow side. Draw far to near; k.shape() knocks out what is behind it.
- Shading: k.shape(path, tone, dark, angle) hatches the form and darkens toward the shadow side (light from upper
  left). Vary hatch angle per form so forms read separately. Use k.solid() for small near-black accents, white
  highlight strokes for gloss (see spider).
- Leave the subject zone readable: portrait frames (900x1500) put the focus subject around (0.5W, 0.4H); band frames
  (1200x520) around the centre. Backdrops should be lighter/sparser there and frame the edges. The bottom 30% of a
  portrait sits under the title text in the app: keep it light (tone ≤1) and quiet, fading out.
- Every backdrop must work in both formats, using k.w and k.h only, and must use spec['wash'] (two pastels) via
  k.watercolour(...) for 2–3 pooled tints, never full-frame flat fills.
- spec['light'] in {dawn, day, dusk, night, firelight, screen-glow, starlight}: night/starlight means a darker sky
  (hatched tone 2–3 with stippled stars) and fewer tints; firelight/screen-glow means a warm/cool pool of wash near
  the light source with radiating ruled lines.
- Deterministic: use k.r (seeded random), never the global random.
- Quality bar: it must look drawn, not clip-art. Prefer many fine lines, varied hatch, foliage leafmarks, irregular
  edges (rough filter is on by default), perspective where architecture appears. Avoid cute faces, flat rectangles,
  perfect symmetry.

Testing: `python3 -c` using compose.render_spec with specs from
/tmp/claude-0/-home-claude/a0bfae2e-11b9-5741-b301-a203a6bdce2f/scratchpad/cot/scenes.json (real chapter scenes) or
your own; save previews under /tmp/claude-0/-home-claude/a0bfae2e-11b9-5741-b301-a203a6bdce2f/scratchpad/engrave/<you>/ and LOOK at them with Read.
Iterate until each motif clears the quality bar. Render via `from render import Renderer` (headless Chromium).

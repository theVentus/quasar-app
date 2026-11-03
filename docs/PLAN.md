# Quasar to Blue Dot for iOS: app plan

Status: planning. Constraints confirmed 3 November 2026 (section 0a). The repo holds this plan, the course package and the web reference build; no Xcode project yet. Date of research: 3 November 2026.
Source studied: `scratchpad/build/src.html` (MODULES, PRESETS, BESPOKE, LAB, lesson format, RULES, `lessonPrompt`, `gradePrompt`, `chatPrompt`, Store, review logic, THEMES, FONTS).

Citations in square brackets point to the Sources list at the end. Items marked **(unverified)** are on the list at the end.

---

## 0. Decisions at a glance

| Area | Decision |
|---|---|
| Platform | iPhone first, SwiftUI, adaptive enough for iPad. Mac later. |
| Deployment target | **iOS 26.1** (the owner's iPhone 17 Pro Max runs current iOS 26). Liquid Glass APIs are iOS 26.0 [A1–A4], and `tabViewBottomAccessory(isEnabled:)` needs 26.1 [A6]. Build with the current Xcode (27.x). Since 28 April 2026, App Store Connect uploads must be built with Xcode 26 or later against the iOS 26 SDK [A9]. |
| Design | System components first, so Liquid Glass comes from the OS. Custom `glassEffect` only on floating controls in the navigation layer: the Lab control cluster and the reader's equation shelf. Lesson content is never glass [A8]. |
| Content | A versioned **course package**: `course.json` manifest, lesson files in the format the web app already uses (`TITLE/ABSTRACT/===BODY===/===QUESTIONS===/===KEY===/===REFERENCES===`), JSON model specs, and prompt templates. The web page and the app both read it. |
| Lesson rendering | A native block renderer. swift-markdown parses to an AST, then to `Block`s. Prose renders through TextKit 2 (`UITextView`), which gives real range selection for Explain and Ask and makes pagination possible. Maths renders with SwiftMath, CI lints every expression, and a KaTeX-in-`WebView` snapshot is the fallback for any expression SwiftMath can't render. |
| Explorables | The JSON spec maps to native views: `Slider` for each var, a Swift expression evaluator, Swift Charts for plots (including `.log` scales [A12]), and `Canvas` plus `TimelineView` for the bespoke simulations. |
| Persistence | SwiftData, **on-device only** for now: a free Apple ID cannot use iCloud/CloudKit. Keep the schema CloudKit-compatible [A10] so sync can be switched on if a paid membership is added; until then, JSON export and import. Course content stays as read-only files and is not stored in SwiftData. Exercise attempts are append-only events. |
| Claude | A `ClaudeTransport` protocol with three backends: (1) your own key in the Keychain, calling the Messages API directly (personal use; **the only backend in scope**, same pattern as the FX app's rates key); (2) an optional minimal proxy (Cloudflare Worker); (3) Anthropic **App Attest** through the Claude for Foundation Models package, which needs no key and no proxy but is beta and iOS 27+ [B3, B4]. No API key ships in the binary. |
| Repo | Public GitHub repo `theVentus/quasar-app` (public, so macOS CI minutes are free): a thin app target plus SwiftPM packages (`CourseKit`, `Reader`, `Lab`, `Tutor`, `Learning`, `Design`), `content/`, `tools/coursectl`, `web/`, `proxy/`, `docs/`. |
| CI | All builds run on GitHub Actions `macos-26` (no Mac; the owner develops on Windows). XcodeGen generates the project from `App/project.yml`; no `.xcodeproj` in git. Each push to app code runs unit tests, simulator screenshots and slowed transition recordings (pushed to a `ci-shots` branch for review), and an unsigned IPA plus an AltStore source on release `latest`. Failures are re-emitted as annotations. Linux jobs cover the pure-Swift packages, content validation and JS conformance tests. |

---

## 0a. Constraints confirmed on 3 November 2026

These supersede anything later in this plan that assumes otherwise.

- **No Mac.** The owner develops on Windows. Everything builds on GitHub Actions `macos-26`, as in the FX app (`theVentus/jubilant-octo-potato`).
- **Free Apple ID, no paid Developer Program.** Install by sideloading: CI publishes an unsigned IPA versioned `1.0.<run_number>` and an `altstore.json` source on release `latest`; AltStore with AltServer (Windows) re-signs every 7 days in the background, with Sideloadly as fallback. Consequences: no CloudKit sync, no TestFlight, no push notifications, no App Attest (backend C), and free provisioning allows 3 sideloaded apps at once (FX already uses one). Bundle id `com.theventus.qbd`.
- **Public repo.** macOS CI minutes are free, so screenshot runs can happen on every push to app code. Never commit keys; the Claude key lives only in the device Keychain.
- **Reuse the FX tooling:** `project.yml` (XcodeGen), `pick-sim.py` (newest iOS 26 iPhone 17 Pro Max simulator), `screenshots.sh` with launch arguments for fixed states (here: lesson, theme, layout, model, sheet), slow-motion recordings split into frames for transition checks, failure annotations, and `wait-ci.sh`, which lets Claude wait for a run and read its result from the sandbox.
- **Design lessons from FX:** the web version was abandoned because CSS blur does not read as Liquid Glass; native is the reason for this app. Glass belongs to the control layer only. Decide `.regular` versus `.clear` glass per appearance from screenshots rather than in advance, and keep backgrounds plain; decorative patterns added to show off refraction were removed in FX.

## 1. Product vision and principles

**Vision.** This is a quiet, book-like place to learn hard science from first principles. Each course is a graph of lessons. Each lesson is written to be read and worked through, not skimmed. A professor (Claude) sits one tap away and knows exactly where you are in the course.

**Principles**
1. **Content is the hero; glass is the frame.** Liquid Glass belongs to the floating navigation layer and never to lesson text, theorem boxes or tables [A8]. Reading surfaces use the four reading themes (Paper, Sepia, Dusk, Night).
2. **Native over imitation.** Use system `TabView`, toolbars, sheets, `Slider`, `Menu` and search, and let the OS supply the glass, edge effects and morphs. The web build hand-rolled a glass imitation in CSS; the app should drop that code.
3. **One course format, many surfaces.** The web page and the iOS app read the same package, and a course is data, not code. Bespoke simulations are the only code-backed content, and the package refers to them by name.
4. **Retrieval over recognition.** Every lesson ends in exercises that are written, graded and spaced. Quick checks and stepwise derivations sit inline.
5. **The tutor is contextual, not a chatbot tab.** Ask from a selection, a model's current state, an exercise or the whole course, and each request carries the matching context, as the web app already does.
6. **Minimal surface, few personality touches.** Each feature has to earn its place. The personality touches are listed below and kept deliberately small.

**Personality touches (kept from the web app)**
- A concept map as the course home.
- Calibration (Pythagoras, trig, vectors, derivative, matrices, regression) in Lesson 0.1, which drives which prerequisites get taught.
- Selecting text offers Explain and Ask.
- "Ask about this model" sends the model's current state (`__ixSummary`) to the tutor.
- A reading footer showing time left, percentage or position.
- Computer Modern as the default typeface.
- Standard and Deep tutor depth.

**Personality touches (new, native)**
- **Now reading accessory.** A `tabViewBottomAccessory` pill, like Music's mini player: "2.3 Iterating to a fix · 12 min left". Tap it to resume. It collapses inline when the tab bar minimises [A5, A6].
- **Equation shelf.** Long-press a numbered display equation to pin it to a small glass shelf that floats over the reader. Pinned equations stay in view in later sections and morph with `glassEffectID` [A4, A7]. Tapping "equation (2)" anywhere opens a peek. This is the one bespoke glass element in the reader.
- **Live model handoff.** In a lesson, an explorable can expand into the Lab full-screen with a zoom transition (`matchedTransitionSource` and `navigationTransition(.zoom)` [A5]), keeping its current state.
- **Haptic presets.** Slider presets such as "Phone quartz" and "Caesium" snap with `sensoryFeedback`, so tapping across orders of magnitude feels physical.

---

## 2. Information architecture

```
TabView (.tabBarMinimizeBehavior(.onScrollDown))
├── Library        NavigationStack: Library → Course → Lesson reader
├── Review         Today's due cards, then the learner record summary
├── Lab            All models across installed courses → full-screen model
├── Ask            Threads by context (course / lesson / model)
└── Search         Tab(role: .search): lessons, concepts, equations, references
+ tabViewBottomAccessory: Now reading (only when a lesson is in progress)
Profile and settings: avatar button in the Library toolbar, opens a sheet
```

The web app's Course, Lesson, Lab, Ask and Record tabs map onto this layout. The Lesson tab disappears because the reader is pushed from Library and resumed from the accessory. Record moves into Review and Profile.

| Screen | Contents | Liquid Glass application |
|---|---|---|
| **Library** | A grid of course covers: title, progress ring, next lesson. A "Snacks" row of short-form lessons (v0.4). An Import button. | System nav bar and tab bar. The large title collapses under the soft scroll edge effect [A8]. Covers sit in the content layer with no glass. Import uses `.buttonStyle(.glass)` in the toolbar [A11]. |
| **Course** | A hero header with the concept map, then module sections (tag, hours, why, dependencies) and lesson rows with status (Complete, In progress, Ready, Not written). It also lists textbooks and mastery levels. | The hero uses `backgroundExtensionEffect()` so the map art runs under the floating bar [A13]. The toolbar has Ask (course context) and an overflow `Menu`. |
| **Lesson reader** | Title block, abstract, numbered sections, theorem blocks, equations, tables, quick checks, step reveals, explorables, exercises, references. Scroll or paged layout. | The tab bar is hidden for immersion. Top toolbar: back, contents, title. Bottom toolbar: previous, progress, Ask, Aa, with `ToolbarSpacer` groups [A5]. Tapping the content toggles the chrome. Reading settings open in a `.presentationDetents([.medium, .large])` sheet, which gets the inset glass background automatically [A5]. The Ask sheet zooms out of its button. The equation shelf is a `GlassEffectContainer`. Theorem boxes, quick checks and model cards are content-layer cards in theme colours with no glass. |
| **Exercises** (inside the reader) | Answer field, then Check, Hint, Show solution. A verdict chip and feedback. | Check is `.glassProminent`, the single tinted primary action [A5, A8]. Everything else uses standard bordered styles. |
| **Lab** | A list of models, grouped by course and module. Full-screen model: plot or simulation canvas, then controls and outputs. | Full-screen model: the canvas is media-rich content, so floating glass controls are legitimate there. Play, reset and the transmitter count sit in a `GlassEffectContainer`, and the parameter tray morphs out of a glass button with `glassEffectID` [A3, A4]. Sliders inside the tray use standard fills and vibrancy, not nested glass, to avoid glass on glass [A8]. |
| **Ask** | Thread list. Chat with Markdown and maths, streaming. A context chip (Course, Lesson 2.3, or a model state). A Standard/Deep toggle. | The composer is a floating glass capsule at the bottom. The context chip is a glass capsule above it, in the same container, so they morph together. A hard scroll edge at the top if the thread header is pinned [A2]. |
| **Review** | Due cards: question, answer from memory, Check, verdict, Next. Then a summary: completed lessons, mastered / needs revision / missing prerequisites chips, and calibration. | System chrome. The Check button is `.glassProminent`. Cards stay in the content layer. |
| **Profile and settings** (sheet) | Learner record per course, calibration, reading defaults, Claude connection (key, proxy or App Attest status, model per task, usage this month), data (export, import web progress, reset), iCloud sync status. | A standard `Form` in a sheet. No custom glass. |

**Navigation rules**
- Deep links: `qbd://course/{courseId}/lesson/{lessonId}#block-{n}`. The Now reading accessory, search results and tutor citations all use them.
- The reader remembers its position per lesson, as a block index plus character offset, and syncs it.

---

## 3. Course content format (shared by web and app)

### 3.1 Package layout

```
quasar-to-blue-dot/                      ← directory in the repo; zipped as .qbdcourse for import
├── course.json                          manifest (schema "qbd.course/1")
├── lessons/
│   ├── 0-1.lesson.md                    existing web format, plus optional YAML front matter
│   └── …
├── shorts/                              short-form lessons (v0.4)
├── models/
│   ├── light-time.json                  "explore/1" spec (PRESETS entries, unchanged)
│   ├── clock-drift.json
│   ├── dilation.json
│   ├── ionosphere.json
│   ├── trilateration.json               {"spec":"bespoke/1","engine":"trilateration","params":{…}}
│   └── vlbi.json
├── prompts/                             Mustache-style templates, extracted from the web app
│   ├── rules.md                         (RULES; learner profile is a variable, not hard-coded)
│   ├── lesson.md  continue.md  grade.md  hint.md  solution.md  chat.md  short.md
│   └── components.md                    (IX_GUIDE + the supported LaTeX subset)
├── assets/                              concept-map.svg, figures
└── CHECKSUMS                            sha256 of every file; manifest carries a contentHash
```

### 3.2 `course.json` (abridged)

```json
{
  "schema": "qbd.course/1",
  "id": "quasar-to-blue-dot",
  "version": "1.0.0",
  "title": "Quasar to Blue Dot",
  "subtitle": "A first-principles course on satellite positioning",
  "language": "en-GB",
  "author": { "name": "Daksh Kushwah", "generator": "claude-opus-5-5" },
  "minAppVersion": "0.1",
  "audience": { "profile": "prompts/learner.md" },
  "modules": [
    { "id": 2, "title": "Solving for position", "tag": "Essential", "hours": 8, "deps": [1],
      "why": "The heart of the course: …",
      "lessons": [
        { "id": "2-1", "title": "Pseudorange and the clock-bias unknown", "file": "lessons/2-1.lesson.md",
          "status": "published", "minutes": 35, "concepts": ["pseudorange", "receiver clock bias"],
          "models": ["trilateration"] }
      ] }
  ],
  "shorts": [],
  "lab": [ { "model": "trilateration", "where": "Modules 1 and 2", "lesson": "2-1", "blurb": "…" } ],
  "references": [ { "id": "ashby2003", "text": "N. Ashby (2003) …", "url": "https://…" } ],
  "textbooks": ["P. Misra and P. Enge, …"],
  "mastery": [ ["Introductory", "…"], ["Undergraduate", "…"], ["Master’s", "…"] ],
  "calibration": [ ["pythagoras", "Pythagoras"], ["trig", "Sine and cosine"] ],
  "conceptMap": "assets/concept-map.svg",
  "constants": { "c": 299792458, "GM": 3.986004418e14, "R_E": 6.371e6, "f_L1": 1575.42e6 },
  "review": { "gapsDays": [1, 2, 5, 12, 30] }
}
```

### 3.3 Lesson file

The file keeps the format the web parser (`parseLesson`) and the generator already use, so no content migration is needed. The only addition is optional front matter:

```
---
id: 2-1
version: 3            # bump when regenerated or edited; attempts record it
status: published     # draft | published
generated: claude-opus-5-5 @ 2026-11-10
reviewed: 2026-11-12
---
TITLE: …
ABSTRACT: …
===BODY===
… Markdown, $…$ / $$…$$ / \begin{equation}, > **Definition (…).** blocks,
```quiz / ```steps / ```widget NAME``` / ```explore {json}``` fences, ==highlight== …
===QUESTIONS===
Q1 [explain] …
===KEY===
Q1: …
===REFERENCES===
[1] …
```

**Block grammar (normative, written up in `docs/content-format.md`)**
- Headings: `##` for sections (numbered by the renderer) and `###` for subsections.
- Theorem blockquotes: Definition, Example, Theorem, Exercise, Remark, Misconception, Key idea, Note, Intuition, Warning, Check, with an optional `(Title)`.
- Display maths: `\begin{equation}` (numbered), `$$…$$` and `\[…\]` (unnumbered).
- Fences: `quiz`, `steps`, `widget`, `explore`.
- Highlights: `==…==`, at most once per section.
- GFM tables.
- Questions carry a kind: explain, calculate, predict or apply.

**Conformance fixtures.** `content/fixtures/*.lesson.md` each have a matching `*.ast.json`. The JS parser (web) and the Swift parser (CourseKit) must produce the same AST, and CI runs both. This is the main protection against the two parsers drifting apart.

### 3.4 How courses are authored and added

`tools/coursectl` is a Swift command-line tool in the same SwiftPM workspace that reuses CourseKit's parser and validator.

1. **Capture.** `coursectl new --from <url|file>` stores the source (reel transcript or article text) in `authoring/` outside the package. The course itself never mentions its source, as `RULES` already requires.
2. **Syllabus.** The curriculum-architect prompt produces a draft `course.json`: modules, dependencies, why statements, lesson titles, verified references and textbooks. A human reviews it.
3. **Lessons.** `coursectl generate <lessonId>` renders `prompts/lesson.md` with the syllabus, the previous lesson's excerpt and a neutral learner profile, calls Claude from the Mac with the author's key, and writes the `.lesson.md` file as a draft. `continue.md` handles truncated replies.
4. **Lint.** `coursectl validate`:
   - checks the format and the block grammar;
   - checks every `$…$` against the SwiftMath subset (math lint);
   - evaluates every `explore` expression against the spec rules (at most 4 vars and 6 outputs, positive `min` when `log` is set, finite outputs across the range);
   - checks that `[n]` citations resolve and that URLs return 200;
   - forbids source-mentions;
   - checks word counts.
5. **Review and publish.** The status changes to `published`, the course `version` is bumped (semver: minor for new lessons, patch for fixes), and `coursectl pack` produces `.qbdcourse` (a zip) together with the inlined web build.
6. **Install.**
   - The first course is bundled in the app.
   - Later courses are imported from Files, AirDrop or iCloud Drive. The app registers a custom UTType, `com.dakshkushwah.qbdcourse` (exported).
   - Optionally, the app can fetch from a release URL (v0.4). A private repo needs a token, so prefer an iCloud Drive folder.
   - Installed packages are unpacked to Application Support. Updating a course keeps progress, because progress is keyed by `courseId/lessonId` and stores `lessonVersion`.

**Web page.** `web/build` inlines `course.json`, the lessons and the models into the single-file HTML, so the claude.ai artifact keeps working with `window.claude` sample and db. Hard-coded data (`MODULES`, `PRESETS`, `LAB`, `REFS`, `TEXTBOOKS`, `CALIB`) moves into the package, and the web page reads it from an inlined `<script type="application/json">`.

**Pre-written or personalised lessons.** The web app writes each lesson on demand and conditions it on the learner record. The app reads published, reviewed lessons by default, because they are stable, citeable, cheap and give exercise IDs that don't change. Personalisation moves into **addenda**: a short "Before you start: vectors refresher" generated in the app when the record flags a missing prerequisite, stored with the user's data rather than in the package. Draft courses can still be generated on demand in the app. This is open question 3.

---

## 4. Data model and persistence

**Choice: SwiftData with CloudKit private-database sync.**
- It is native and integrates with SwiftUI through `@Query`.
- Sync takes two capabilities (iCloud with CloudKit, and Background Modes with remote notifications) [A10].
- The data volume is small: thousands of rows.
- Alternatives considered:
  - GRDB/SQLite plus hand-written CloudKit sync: more control, much more code.
  - Core Data: no advantage here.
  - Fall back to GRDB only if SwiftData sync proves unreliable in v0.2 testing.

**CloudKit constraints the schema must meet [A10]**
- No `.unique` attributes. Identity is a string key field that the app de-duplicates.
- Every relationship is optional, and no relationship uses the `.deny` delete rule.
- Every attribute is optional or has a default.
- **The schema becomes additive-only once it is promoted to production.** Use `VersionedSchema` from day one, and promote to production only at v0.2 after the schema has had time to settle.

**Two stores**
- **Synced** (`cloudKitDatabase: .private(...)`): user state.
- **Local** (`cloudKitDatabase: .none` [A10]): installed-package index, render caches and search index.

**Synced entities** (all keyed by `courseId` and `lessonId` strings, never by object references to content):

| Entity | Key fields | Notes |
|---|---|---|
| `LessonProgress` | courseId, lessonId, lessonVersion, startedAt, completedAt?, position (block, offset), readSeconds | Last write wins. Merging is harmless. |
| `Attempt` | courseId, lessonId, lessonVersion, questionId, answer, verdict, feedback, gap, concept, model, at | **Append-only.** The review box and due date are *derived* from the attempt history using the web rule: correct moves up one box (to a maximum of 4), anything else resets to box 0, and due = last attempt plus GAPS[box]. Two devices can never conflict. |
| `QuickCheckResult` | courseId, lessonId, blockId, choice, correct, at | Feeds the record lightly. |
| `ConceptStatus` | courseId, concept (normalised lower-case), status (mastered / revision / missing), updatedAt, source | One row per concept, newest update wins. This replaces the web app's three capped arrays and keeps the `mergeRecord` semantics. |
| `Calibration` | key, value (0–2), updatedAt | Global across courses. |
| `ChatThread` / `ChatMessage` | context (course / lesson / model:id), role, text, at | Keep the last 60 messages per thread in prompts, as the web app does. |
| `Addendum` / `GeneratedLesson` | courseId, lessonId, text, model, at | Personal generated content. Each is well under the CloudKit record size limit (lessons run about 20 KB) **(unverified: exact limit)**. |
| `Highlight` (later) | courseId, lessonId, anchor, note | |

- **Settings.** Reading preferences (theme, font, size, line height, margins, alignment, layout, footer) go in `@AppStorage`, mirrored to `NSUbiquitousKeyValueStore` so they follow the user across devices. Tutor depth and model choices go in the same place.
- **Secrets.** The Claude API key is stored in the Keychain only, with `kSecAttrAccessibleWhenUnlockedThisDeviceOnly`, so it is excluded from iCloud Keychain and backups. It is never stored in SwiftData.
- **Migration from the web.** The web app gains an "Export progress (JSON)" button that dumps `answers`, `progress` and `chats`, and the app imports it once. No live sync between web and app, because that would need a backend.

---

## 5. Maths and interactive-model rendering

### 5.1 LaTeX options evaluated

| Option | How it works | Pros | Cons |
|---|---|---|---|
| **SwiftMath** (mgriebling) [D1] | A Swift port of iosMath. CoreText typesetting into a `UIView` (`MTMathUILabel`), wrapped in SwiftUI. MIT licence. Bundles Latin Modern Math (the default), XITS, TeX Gyre Termes and others. | Fully native and offline. Fast. Matches Computer Modern. Works with themes and Dynamic Type. Produces images for inline text attachments. | Subset of TeX. `\middle`, `\:`, `\;` and `\!` are missing [D1]. The parser has no `\tag`; whether `equation` environments and `\mathrm` work depends on factory tables the review could not see [D2]. No equation numbering, so the app must provide it. Release history is sparse. |
| **iosMath** (kostub) [D3] | The Objective-C original, distributed through SwiftPM. MIT licence. | Mature, with the same subset. | Older code base with 42 open issues [D3]. SwiftMath supersedes it. |
| **LaTeXSwiftUI** (colinc86) [D4] | MathJax through MathJaxSwift, rendered to SVG and drawn with SwiftDraw. | Full MathJax coverage. Built-in equation numbering, inline and block modes [D4]. | Runs a JS engine. By default it renders on the main queue, synchronously [D4]. Heavy for a 2,500-word lesson containing about 150 expressions. Last release was 1.5.0 in April 2025 [D4]. Licence not stated on the registry page. |
| **MathJax or KaTeX in `WebView`** (iOS 26 SwiftUI `WebView` and `WebPage` [A14]) | Render the whole lesson, or only the maths, in WebKit. | Exact parity with the web build, including the CSS column pagination that already exists. | The web view is not native text. Selection, Dynamic Type, accessibility and glass integration are poorer, and explorables would be web, not native. Memory use is high. |

**Recommendation: native-first and hybrid.**
1. **Prose** goes into a TextKit 2 `UITextView` (read-only, selectable) wrapped in `UIViewRepresentable`. Inline maths becomes an `NSTextAttachment` whose image SwiftMath renders. It is baseline-aligned using the descent, and the cache key is LaTeX + point size + colour + font. Range selection then works natively, and the edit menu gets two extra items, Explain and Ask. SwiftUI `Text` on iOS can't select a range **(unverified for iOS 26/27; check before building)**.
2. **Display equations** use a SwiftMath view. `\begin{equation}…\end{equation}` is stripped by the CourseKit preprocessor, and the renderer adds the number (1), (2) and so on, with its own counter in a trailing column.
3. **A LaTeX subset contract** is written into `prompts/components.md`, so Claude only writes LaTeX the app can render, and `coursectl validate` runs every expression through SwiftMath's parser in CI. Anything outside the subset fails the build.
4. **Fallback.** An expression that SwiftMath rejects at runtime, which is likely only in on-device generated lessons, is rendered once by an offscreen `WebPage` running KaTeX, snapshotted to an image and cached. This keeps maths from ever showing up broken.
5. **Escape hatch.** If more than about 2% of the corpus fails math lint at the v0.1 spike, switch prose blocks to a `WebView` reader and keep the interactive blocks native.

**Spike first, in week 1 of v0.1.** Run all of Lesson 0.1 and the 56 lessons generated next through the math lint, and measure render time for a full lesson on an iPhone 12-class device. The target is under 150 ms to first paint, with off-main-thread rendering of attachments.

### 5.2 Block renderers

| Block | Native view |
|---|---|
| Heading, paragraph, list | `ProseView` (TextKit 2) with theme typography. The 13 web fonts map to bundled OFL/GUST fonts. System sans becomes SF, and **New York** is added as the native serif option. |
| Theorem (Definition, Example, …) | A SwiftUI card styled per kind: bold, italic or boxed, following the `THM` table. Not glass. |
| Equation | A SwiftMath display view with a number. Long-press pins it to the equation shelf. |
| Table | `Grid` with horizontal scroll if it overflows. |
| `quiz` | Option buttons, then the reveal with explanation. Results go to `QuickCheckResult`. |
| `steps` | "Reveal next step" with a disclosure animation. Steps can contain display maths. |
| `widget NAME` / `explore {…}` | `ModelCard` from the Lab package. |
| Exercises | `ExerciseView` (Tutor and Learning packages). |
| References | A numbered list with link previews. `[n]` in the text opens a popover. |

**Paged layout.** v0.1 ships scroll only. v0.2 adds pages: blocks are measured, then packed into page-sized columns. Long prose blocks split at TextKit line fragments, and blocks such as theorems, equations and models are never split (the CSS `break-inside: avoid` rules). Pages display in `ScrollView(.horizontal)` with `.scrollTargetBehavior(.paging)`.

### 5.3 Explorable spec to native views (`explore/1`)

| Spec field | Native mapping |
|---|---|
| `vars[]` {id, label, min, max, value, step?, log?, unit?, presets?} | A `Slider` over the linear or log10 domain. Setting `step` gives automatic tick marks on iOS 26 [A5]. `presets` become a row of capsule chips with `sensoryFeedback(.selection)`. The value label uses `.monospacedDigit()`. |
| `defs[]` [[name, expr]] | Compiled once into an expression tree and evaluated in order. |
| `outputs[]` {label, expr, unit?, lookup?} | A `LabeledContent` grid. Units are SI auto-prefixed for s, m and Hz (a port of `fmtQ`). `lookup` maps to the "on the scale of" phrase. |
| `plot` {x, y[], labels?, logy?, xlabel, ylabel, yunit} | Swift Charts. A `LineMark` per series, sampled at 200 points (log-spaced if `x` is a log var). `.chartXScale(type: .log)` and `.chartYScale(type: .log)` [A12]. A `RuleMark` at the current x and a `PointMark` for each marker. |
| `caption` | A prose block (Markdown and maths). |
| "Ask about this model" | A generic summariser built from var labels, values and outputs (a port of `__ixSummary`). It opens Ask with the context `model:<id>` and the current state. |

**Expression evaluator.** A Swift port of the web grammar: `+ - * / ^`, parentheses, the functions `sqrt abs exp ln log10 sin cos tan asin acos atan atan2 min max pow hypot deg rad`, and the constants from `course.json` (`c, pi, G, GM, R_E, omega_E, DAY, f_L1, f_L2, f_L5, AU, ly`). Shared test vectors (`content/fixtures/expr-vectors.json`, with each expression, its environment and the expected value) run in both the JS and Swift test suites.

**Bespoke simulations** (`bespoke/1`, an engine registry in `Lab`):
- `trilateration`: a `Canvas` with `DragGesture` handles for the receiver and transmitters. The Gauss-Newton solver plus normal equations and HDOP is ported as pure Swift (`gnSolve`, `solveLin`, `normalEq`), unit-tested against outputs recorded from the JS version, and runs on Linux CI.
- `vlbi`: a `Canvas` for the Earth view and Swift Charts for the delay curve over a sidereal day, with `AreaMark` or `RectangleMark` bands for mutual visibility. Play uses `TimelineView(.animation)`.
- New bespoke engines need app code and an app release. The course package only refers to them by name, and `coursectl validate` checks that the name is in the app's registry list for the stated `minAppVersion`.

---

## 6. Claude integration

**Rule: no API key ever ships in the binary.** Anthropic's own docs warn that a key bundled into an app "is extractable from the shipping binary" [B4]. Direct browser access to the API has always been labelled `anthropic-dangerous-direct-browser-access` for the same reason [B5].

### 6.1 Backends behind one protocol

```swift
protocol ClaudeTransport: Sendable {
  func stream(_ request: MessagesRequest) -> AsyncThrowingStream<MessagesEvent, Error>
  func json<T: Decodable>(_ request: MessagesRequest, as: T.Type) async throws -> T
}
```

| Backend | How | Pros | Cons | Use |
|---|---|---|---|---|
| **A. Personal key in Keychain** | The user pastes a key into Settings. It is stored with `WhenUnlockedThisDeviceOnly`. A thin `URLSession` client posts to `https://api.anthropic.com/v1/messages` with `Authorization: Bearer` (or `x-api-key`) and `anthropic-version`, and parses SSE for streaming [B1, B2]. | No server. Fastest to build. Full Messages API features (prompt caching, stop sequences, structured outputs). | The key sits on the device, so the risk falls on a lost, unlocked or jailbroken phone. Only suitable for the key owner. Mitigations: create the key in a **dedicated workspace with a spend limit** [B1], set a key expiry (the Console offers presets up to 30 days, or custom [B2]), and offer rotation in Settings. | **v0.2 default.** Personal and TestFlight-internal use. |
| **B. Minimal proxy** | A Cloudflare Worker of about 80 lines in `proxy/`. It holds the key as a secret and accepts only `POST /v1/messages`. It enforces a model allowlist, a `max_tokens` cap and per-device rate limits, and authenticates the caller with a Sign in with Apple identity token (JWT verified against Apple's keys) or a per-install token. It streams the SSE response straight through. Client SDK pattern: `.proxied(headers:)` with `baseURL` [B4]. | The key never reaches a device. Usage can be metered per user. Works on iOS 26. | It is a service to run and secure, though at this volume it costs nothing. Sign in with Apple adds friction. | Required as soon as anyone other than you uses the app. |
| **C. Anthropic App Attest** | The Claude for Foundation Models Swift package (`ClaudeLanguageModel(name:auth: .appAttest(clientID:))`). Each genuine install attests with Apple's `DCAppAttestService` and receives a 1-hour, workspace-scoped token that **authorises only Messages API calls** [B3, B4]. The app is registered in the Console under App integrations with its Team ID and bundle IDs. | No key and no proxy. Integrations can be revoked [B3]. It works through Apple's `LanguageModelSession`, so streaming, `@Generable` structured output (good for grading JSON) and tool calling come with it. You can fall back to Apple's on-device model on `.rateLimited` [B4]. | **Beta.** It requires iOS 27 and Xcode 27, and the docs still say "OS 27 betas" [B4, B6]. It needs a physical device, not the Simulator [B3]. Tokens carry no user identity [B3]. It doesn't expose cache controls, stop sequences or token counting [B4]. Streaming yields cumulative snapshots, not deltas [B4]. Cost scales with every install. | Track it. Adopt when it leaves beta and if the deployment target moves to iOS 27 (open question 1). |

**No official Swift Messages SDK.** Anthropic's client SDK list covers Python, TypeScript, C#, Go, Java, PHP and Ruby [B2]. The Foundation Models package is "not a general-purpose Messages API client" [B4]. `Tutor` therefore owns a small Codable Messages client and SSE parser, about 400 lines with tests.

### 6.2 Tasks, prompts and models

All prompts come from the course package (`prompts/*.md`) and are rendered with the learner snapshot (`snapshot()` port), so the web and the app stay identical.

| Task | Prompt | Output | Default model (configurable) |
|---|---|---|---|
| Ask (Standard / Deep) | `chat.md` + `rules.md` + syllabus + record + lesson text (clipped at 9,000 characters) | Streaming Markdown with maths | Sonnet-class / Opus-class |
| Explain selection | `chat.md` with the selection and section | Streaming | Sonnet-class |
| Grade exercises | `grade.md` | JSON `{results[], record{}}`, using structured outputs [B7] instead of "reply with only JSON" | Sonnet-class |
| Hint / Solution | `hint.md` / `solution.md` | Short text / worked solution | Haiku-class / Sonnet-class |
| Addendum and draft lessons | `lesson.md`, `continue.md` | Lesson format. Validated by CourseKit before display. | Opus-class |

Model IDs are not hard-coded. They live in a `models.json` remote default plus Settings.

**Cost control**
- Put stable prefixes first so prompt caching applies: rules, syllabus, then lesson text **(caching details unverified for this plan)**.
- Clip context, as the web app does today.
- Count usage in a local ledger: a `ClaudeUsage` row per call with input and output tokens from the response `usage` field.

**Errors.** Map them to the web app's copy: rate limited, prompt too large, refused, invalid JSON, empty completion. Show them as a toast and keep the draft.

**Privacy.** Only lesson text, the learner record and chat leave the device. Nothing else does.

---

## 7. Short-form lessons (v0.4)

**What changes from a full lesson**

| | Full lesson | Short |
|---|---|---|
| Length | 1,500–2,500 words, 30–60 minutes | 300–600 words, 2–5 minutes |
| Scope | A full teaching sequence: intuition, definition, mechanism, maths, worked example, theory, application, misconceptions | **One idea**: a hook (a phenomenon or a question), the idea, at most one equation, one worked number, and "where this goes" |
| Interaction | 2–4 components, 4–6 written exercises | At most one component (a quick check or a single-var model). 1–2 retrieval prompts: one MCQ and one 1-line recall. |
| Grading | Claude-graded | MCQ graded locally. The recall prompt is self-graded (Got it / Shaky), with optional Claude grading. |
| Layout | Reader | A vertical card stack, one screen per beat, paged with `.scrollTargetBehavior(.paging)` |

**Where shorts sit in the course graph.** In `course.json`, each `shorts[]` entry has `{id, title, file, concepts[], anchors[{lesson, relation: "preview"|"refresher"|"deepen"}], prereqOf[]}`. Shorts show up in four places:
1. **Remediation.** When grading puts a concept in *revision* or *missing*, the matching short appears under the verdict ("2-minute refresher: vectors") and in Today.
2. **Calibration.** A low self-rating on, for example, Matrix multiplication queues the matching refresher shorts before the first lesson that needs them. This replaces the web app's "teach the prerequisite first" with something reusable.
3. **Snacks** in Library and Today: previews of the next lesson and spaced re-reads of finished ones.
4. **Standalone mini-courses.** A reel or article that doesn't justify a 13-module course becomes 5–10 linked shorts. It uses the same package format with `modules` empty and `shorts` populated, and the same pipeline with the `short.md` prompt.

Short-form completion updates `ConceptStatus` but never marks a full lesson complete.

---

## 8. Repo structure (private GitHub)

```
qbd/                                       private repo
├── App/
│   ├── QBD.xcodeproj                      thin app target only
│   └── QBD/                               @main App, RootTabs, DI container, entitlements,
│                                          Info.plist (UTType export), Assets, bundled course
├── Packages/                              one SwiftPM workspace (Package.swift with multiple products)
│   ├── CourseKit/      pure Swift, no UI, builds on Linux
│   │                   manifest Codable types · lesson parser → Block AST · LaTeX preprocessing ·
│   │                   expression evaluator · package import/validation · fixtures tests
│   ├── Learning/       SwiftData schema (VersionedSchema) · review scheduler (Leitner, GAPS) ·
│   │                   record merge · progress · web-progress import
│   ├── Reader/         block renderers · TextKit 2 ProseView · SwiftMath bridge + KaTeX fallback ·
│   │                   themes, fonts, typography · pagination · equation shelf
│   ├── Lab/            explore/1 → SwiftUI + Charts · bespoke engines (Canvas) · solvers (pure Swift target)
│   ├── Tutor/          ClaudeTransport + backends A/B/(C behind #if) · Messages client + SSE ·
│   │                   prompt templating · Keychain · usage ledger
│   └── Design/         tokens, glass components (GlassCluster, ContextChip), font registration, haptics
├── content/
│   ├── courses/quasar-to-blue-dot/        the package (§3)
│   └── fixtures/                          *.lesson.md + *.ast.json, expr-vectors.json, solver-vectors.json
├── tools/coursectl/                       Swift executable: new, generate, validate, lint-math, pack
├── web/                                   src.html → build script that inlines a package; node tests on fixtures
├── proxy/                                 Cloudflare Worker (optional, backend B) + wrangler.toml
├── docs/                                  PLAN.md, content-format.md, adr/0001-…md, glass-usage.md
└── .github/workflows/
    ├── ci-linux.yml     every push: swift test (CourseKit, Learning-core, Lab solvers, Tutor client),
    │                    coursectl validate content/, node web tests
    └── ci-macos.yml     main and tags: xcodebuild test (UI + snapshot tests), archive; or Xcode Cloud
```

- **Naming.** The brief's "Models" package is called `Lab` here, so it isn't confused with SwiftData models.
- **UI-free cores.** Packages that touch UIKit (Reader, Lab views) keep their non-UI logic in separate targets (`LabCore`, `ReaderCore`) so it can be tested on Linux.
- **CI cost.** On a private repo with GitHub Free, the allowance is $12 a month of compute, and macOS runners cost $0.062 a minute [C1]. That is about 190 macOS minutes, which is why macOS jobs are gated and Linux does the heavy testing. Xcode Cloud includes 25 compute hours a month with the Developer Program [C2] and is the better home for archives and TestFlight uploads.
- **Secrets.** No secrets go in the repo. The `coursectl` key comes from the macOS Keychain or `ANTHROPIC_API_KEY`. Proxy secrets are set with `wrangler secret`.

---

## 9. Roadmap

Each milestone ends with an internal TestFlight build and a short ADR for every decision that changed.

### v0.1: Library and reader, with this course (about 4–5 weeks)
- **Package and tools**
  - Extract MODULES, PRESETS, LAB, REFS, TEXTBOOKS, CALIB and lesson 0.1 into `content/courses/quasar-to-blue-dot/`.
  - Write `docs/content-format.md` and the conformance fixtures, and refactor the web build to read the inlined package.
  - Write `coursectl validate` and `lint-math`.
- **Spikes in week 1**
  - Math lint across the corpus and render timing (§5.1).
  - Range selection in a TextKit 2 view that contains inline math attachments.
- **Content workstream, in parallel**
  - Export any lessons already written in the web store.
  - Generate the rest with `coursectl generate` and review in batches.
  - v0.1 can ship with the lessons that are already published, and the others show "Not written".
- **App**
  - Root tabs: Library, Review placeholder, Lab placeholder, Ask placeholder, Search.
  - Library, Course with the concept map and modules, reader in scroll mode with every block type, and models rendered statically.
  - Reading settings sheet: themes, fonts, size, line height, margins, alignment, footer.
  - Now reading accessory, local progress, and lesson search.
- **Exit:** Lesson 0.1 and Module 1 read well on an iPhone in all four themes and at Dynamic Type sizes from default to XXL, maths renders correctly, and VoiceOver reads every equation through an accessibility label from a LaTeX-to-speech map.

### v0.2: Exercises, review and tutor (about 4 weeks)
- **Tutor:** backend A (Keychain key), the Messages client and SSE, and the prompts from the package.
- **Exercises:** answer, Check, Hint and Solution, structured-output grading, `Attempt` events, and `ConceptStatus` merge.
- **Review tab:** due queue from attempts and the learner record view.
- **Ask:** threads, contexts, selection Explain/Ask, and the Standard/Deep toggle.
- **Lesson 0.1:** calibration.
- **Sync:** CloudKit on, with the schema promoted to production at the end of this milestone; plus web progress import.
- **Reader:** paged layout.
- **Optional:** backend B (proxy).
- **Exit:**
  - A full loop of read, answer, grade, record and due-tomorrow works on two devices with sync.
  - The usage ledger shows the cost per lesson.

### v0.3: Lab (about 3–4 weeks)
- **Lab package:**
  - the `explore/1` engine with Charts and log scales;
  - the expression evaluator with shared vectors;
  - the Trilateration and VLBI engines, with solvers checked against JS vectors.
- **Lab tab:** full-screen model with the glass control cluster and morphing parameter tray, and the zoom transition from an inline card.
- **Tutor link:** "Ask about this model" with state.
- **Reader:** the equation shelf.
- **Exit:**
  - All six built-in models match the web outputs to 1e-9 relative error.
  - Sliders hold 60 fps on an iPhone 12-class device.

### v0.4: Short-form lessons and the second course (about 3–4 weeks)
- **Format:** the `shorts[]` schema and `short.md` prompt, and the card-stack reader.
- **Placement:** remediation and calibration hooks, and Snacks in Library and Today.
- **Authoring:** `coursectl new --from` for the reel/article pipeline.
- **Distribution:** importing `.qbdcourse` from Files and iCloud Drive.
- **Second course:** one mini-course of 5–10 shorts made through the pipeline end to end.
- **Exit:** a second course installs, syncs progress and appears in the Library next to the first with no code change.

**Later candidates:**
- Highlights and notes.
- iPad split view with the reader and Ask side by side.
- Mac.
- A widget for due cards.
- App Attest backend C.
- Tutor tool use that lets Claude open a model at given parameter values.

---

## 10. Main risks and mitigations

| Risk | Likelihood / impact | Mitigation |
|---|---|---|
| SwiftMath does not cover the maths Claude writes (`\mathrm`, `\ `, `\tag`, `aligned`, …) | Medium / High | A LaTeX subset contract in the prompts, math lint in CI, a KaTeX snapshot fallback, and the `WebView` escape hatch (§5.1). Settle this in week 1. |
| A TextKit 2 reader with selection, inline attachments and pagination takes much longer than planned | Medium / High | Ship scroll before paged. If selection with attachments misbehaves, fall back to SwiftUI `Text` with a "Select text" sheet. |
| Content quality and volume (56 more lessons, each 1,500–2,500 words, written by Claude; you have no STEM background to check the physics) | High / High | The source-only references list and "(to verify)" flags already in `RULES`. A `coursectl` check pass in which a second model call audits each lesson's numbers and derivations against the cited sources. Publish in modules, and let lesson versioning fix errors without losing progress. |
| SwiftData + CloudKit quirks; schema is additive-only after promotion [A10] | Medium / Medium | Append-only attempts, string keys, `VersionedSchema`, and a late promotion to production. GRDB is the fallback. |
| Liquid Glass legibility over Sepia and Dusk backgrounds; iOS 27 changes how glass looks (a user transparency setting) | Medium / Low | Use system bars and the regular variant only. Never use clear glass over text [A8]. Test every theme on both iOS 26 and iOS 27. |
| API key exposure or runaway spend | Low (personal) / Medium | Keychain with this-device-only access, a dedicated workspace with a spend limit, expiring keys, and the proxy or App Attest before anyone else uses the app. |
| Web and app drift: two parsers, two evaluators, two prompt copies | Medium / Medium | One package, shared fixtures and vectors run in both CI suites, and prompts live only in the package. |
| App Attest backend stays in beta, or its API changes | Medium / Low | Kept behind `ClaudeTransport`. Not on the critical path. |
| Font licensing and app size from 13 bundled families | Low / Low | All are OFL or GUST. Bundle regular, italic and bold only, as variable fonts where available, and lazy-load the rarely used families. |
| Building alone, with Claude Code doing most of the coding | High / Medium | Small packages with tests, ADRs, and a plan with clear exit criteria per milestone. |

---

## 11. Open questions

Answered on 3 November 2026: deployment target iOS 26.1 (Q1); personal sideloaded use only (Q2, backend A); no paid membership (Q5); no Mac. Still open: Q3 (frozen versus personalised lessons), Q4, Q6, Q7, Q8.


1. **Deployment target: iOS 26.1 or iOS 27?** iOS 27 shipped in September 2026 [E1, secondary source]. Targeting it would unlock App Attest and Foundation Models (backend C) and the iOS 27 toolbar and tab additions, at the cost of iPhones still on iOS 26. For a personal app, iOS 27 is reasonable. This plan assumes 26.1, as the brief asked.
2. **Distribution.** Personal or TestFlight only, or eventually the App Store? This decides whether backend A is enough or whether B or C is required, and whether Sign in with Apple is needed.
3. **Lessons: frozen and reviewed, or personalised on demand?** This plan recommends frozen lessons plus personal addenda (§3.4). Confirm.
4. **Existing web data.** Which lessons have already been written in the claude.ai artifact's db, and should they become the published versions or be regenerated?
5. **Apple Developer Program.** CloudKit, TestFlight, App Attest and Xcode Cloud all need a paid membership [A10, B3, C2]. Is one in place, and under which Team ID?
6. **Should the web page stay a first-class reader**, or become the authoring and preview surface only?
7. **Fonts.** Bundle all 13 web families, or start with Computer Modern, Concrete, CM Sans, Literata, New York and SF?
8. **iPad** in v0.2 (split reader and Ask), or later?

---

## 12. What could not be verified

- **The exact `anthropic-version` header value.** The authentication page's examples use `2023-06-01` [B2], while the API overview page gives `2026-10-21` as an example [B1]. Pin whichever the Messages reference states when implementing.
- **The status of the Claude for Foundation Models package on the shipped iOS 27.** The docs and README still say "OS 27 betas" and "may change before general availability" [B4, B6]. No release tag or date was visible.
- **Parts of SwiftMath's LaTeX coverage** (`\mathrm`, `\hat`, `equation`/`aligned` environments, `\quad` input). These live in `MTMathAtomFactory` tables the review couldn't see [D2]. `\tag` is not supported. The week-1 spike settles this.
- **Whether SwiftUI `Text` supports range selection on iOS 26 or 27.** Assumed not, which is why the plan uses a TextKit 2 `UITextView`.
- **iOS 27 SwiftUI additions** (`Tab(role: .prominent)`, `ToolbarOverflowMenu`, `.topBarPinnedTrailing`, `.navigationTransition(.crossFade)`) come from a secondary write-up [E2]. The Apple session page did not render for the review. None of them are relied on.
- **The exact CloudKit record size limit**, and **prompt-caching specifics.** Neither was re-checked for this plan.
- **The App Store Connect requirement.** It was confirmed on Apple's news page [A9]. The Xcode version table (newest Xcode 27.2 with the iOS 27.2 SDK; Xcode 26.6 with iOS 26.5) comes from Apple's Xcode support page as fetched today [A15].

---

## Sources

**Apple**
- [A1] `glassEffect(_:in:)`, iOS 26.0+, default `.regular` in a `Capsule`: https://developer.apple.com/documentation/swiftui/view/glasseffect(_:in:)
- [A2] `scrollEdgeEffectStyle(_:for:)`, iOS 26.0+: https://developer.apple.com/documentation/swiftui/view/scrolledgeeffectstyle(_:for:)
- [A3] `GlassEffectContainer`, `init(spacing:content:)`, iOS 26.0+: https://developer.apple.com/documentation/swiftui/glasseffectcontainer ; `Glass` (`regular`, `clear`, `identity`, `tint(_:)`, `interactive(_:)`): https://developer.apple.com/documentation/swiftui/glass
- [A4] `glassEffectID(_:in:)`, iOS 26.0+: https://developer.apple.com/documentation/swiftui/view/glasseffectid(_:in:)
- [A5] WWDC25 session 323, "Build a SwiftUI app with the new design". It covers `tabBarMinimizeBehavior(.onScrollDown)`, `tabViewBottomAccessory`, `tabViewBottomAccessoryPlacement`, `Tab(role: .search)`, `searchToolbarBehavior(.minimize)`, `ToolbarSpacer(.fixed/.flexible)`, `sharedBackgroundVisibility`, `presentationDetents` with inset glass, removing `presentationBackground`, `matchedTransitionSource` + `navigationTransition(.zoom)`, `.buttonStyle(.glass/.glassProminent)`, `scrollEdgeEffectStyle(.hard, for: .top)`, Slider ticks and `neutralValue`, `.rect(corner: .containerConcentric)`, and `backgroundExtensionEffect()`: https://developer.apple.com/videos/play/wwdc2025/323
- [A6] `tabViewBottomAccessory(isEnabled:content:)`, iOS **26.1**+: https://developer.apple.com/documentation/swiftui/view/tabviewbottomaccessory(isenabled:content:) ; `TabBarMinimizeBehavior` (`automatic`, `never`, `onScrollDown`, `onScrollUp`; iPhone only), iOS 26.0+: https://developer.apple.com/documentation/swiftui/tabbarminimizebehavior
- [A7] Glass morphing with a namespace: [A4] and [A5].
- [A8] WWDC25 session 219, "Meet Liquid Glass". Glass is for the navigation layer; "always avoid glass on glass"; regular and clear variants are never mixed; clear needs a dimming layer; tint only primary actions; soft and hard scroll edge effects: https://developer.apple.com/videos/play/wwdc2025/219/
- [A9] SDK minimum requirements: since 28 April 2026, apps uploaded to App Store Connect must be built with Xcode 26 or later using the iOS 26 SDK: https://developer.apple.com/news/upcoming-requirements/
- [A10] SwiftData, "Syncing model data across a person's devices". Covers the iCloud and Background Modes capabilities, no unique constraints, optional relationships, no `.deny`, additive-only production schema, and `cloudKitDatabase: .private(...)` / `.none`: https://developer.apple.com/documentation/swiftdata/syncing-model-data-across-a-persons-devices
- [A11] `PrimitiveButtonStyle.glass`, iOS 26.0+: https://developer.apple.com/documentation/swiftui/primitivebuttonstyle/glass
- [A12] Swift Charts `ScaleType.log` (iOS 16+): https://developer.apple.com/documentation/charts/scaletype/log ; `ScaleType`: https://developer.apple.com/documentation/charts/scaletype
- [A13] `backgroundExtensionEffect()`, iOS 26.0+: https://developer.apple.com/documentation/swiftui/view/backgroundextensioneffect()
- [A14] WebKit for SwiftUI `WebView` and `WebPage`, iOS 26.0+: https://developer.apple.com/documentation/webkit/webview-swift.struct
- [A15] Xcode versions and SDKs: https://developer.apple.com/support/xcode

**Anthropic**
- [B1] API overview (base URL, headers, workspaces for spend separation): https://platform.claude.com/docs/en/api
- [B2] Authentication: API keys, key types and expiry; `Authorization: Bearer` or legacy `x-api-key`; Workload Identity Federation; App Attest overview; the client SDK languages: https://platform.claude.com/docs/en/manage-claude/authentication
- [B3] App Attest for iOS and macOS apps (Console registration, `clid_…`, 1-hour tokens, Messages-only scope, physical device only, revocation): https://platform.claude.com/docs/en/manage-claude/app-attest
- [B4] Apple Foundation Models library (`ClaudeLanguageModel`, `.appAttest` / `.proxied` / `.apiKey`, the warning about bundled keys, streaming snapshots, `@Generable`, unsupported features, beta and iOS 27 requirement): https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/apple-foundation-models
- [B5] S. Willison on the `anthropic-dangerous-direct-browser-access` header (secondary): https://simonwillison.net/2024/Aug/23/anthropic-dangerous-direct-browser-access
- [B6] ClaudeForFoundationModels README (beta, OS 27 betas, Xcode 27 beta): https://github.com/anthropics/ClaudeForFoundationModels
- [B7] Structured outputs (linked from [B4]): https://platform.claude.com/docs/en/build-with-claude/structured-outputs

**CI**
- [C1] GitHub Actions billing: private repos on Free get $12 a month of included compute; macOS 3/4-core runners cost $0.062 a minute: https://docs.github.com/en/billing/concepts/product-billing/github-actions
- [C2] 25 hours of Xcode Cloud included with the Apple Developer Program: https://developer.apple.com/news/?id=ik9z4ll6

**Maths libraries**
- [D1] SwiftMath README (MIT licence, iOS 11+, bundled fonts, supported features, missing `\middle \: \; \!`): https://github.com/mgriebling/swiftmath
- [D2] SwiftMath parser source, `MTMathListBuilder.swift` (no `\tag`; `\operatorname` and `\left`/`\right` supported; font and accent tables live elsewhere): https://raw.githubusercontent.com/mgriebling/SwiftMath/main/Sources/SwiftMath/MathRender/MTMathListBuilder.swift
- [D3] iosMath: https://github.com/kostub/iosMath
- [D4] LaTeXSwiftUI (MathJaxSwift and SVG, numbering, synchronous main-queue render by default, v1.5.0 of 11 April 2025): https://swiftpackageregistry.com/colinc86/LaTeXSwiftUI
- swift-markdown (cmark-gfm based, Apache-2.0): https://github.com/swiftlang/swift-markdown

**Secondary (context only)**
- [E1] MacRumors, iOS 27 release date announced: https://macrumors.com/2026/09/09/apple-announces-ios-27-release-date/
- [E2] Swift with Majid, What's new in SwiftUI after WWDC26: https://swiftwithmajid.com/2026/06/08/what-is-new-in-swiftui-after-wwdc26/

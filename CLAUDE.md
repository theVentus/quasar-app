# Quasar (quasar-app)

Library app for rigorous, interactive courses. iOS 26, SwiftUI, Liquid Glass. Plan: `docs/PLAN.md`.

## Layout
- `content/courses/<id>/` — course packages (`qbd.course/1`): `course.json`, `lessons/*.lesson.md`, `models/*.json`. Bundled into the app as a folder resource.
- `Packages/QBDKit` — `CourseKit`: manifest, lesson parser, inline TeX → Unicode, expression evaluator, quantity formatting. Platform-free; tested with `swift test`.
- `App/` — XcodeGen spec (`project.yml`) and the `QBD` app target. `QBD.xcodeproj` and `Info.plist` are generated; never commit them.
- `web/` — the single-file web reader (`web/build.py` embeds fonts).
- Books (`qbd.book/1`): a package is `book.json` + `book.epub`. `Packages/QBDKit` `BookKit` parses EPUB 2/3 (OPF, NCX, nav, cover), infers parts/chapters (`BookOutline`) and seals packages (`Vault`, `qbd-seal`). Owned books live only in the private `theVentus/quasar-vault` repo (`books/<id>/`); CI seals them with `LIBRARY_PASSPHRASE` into `App/build/vault/*.qbdvault` (hashed names). The app unlocks them once with the passphrase (kept in the Keychain). `content/fixtures/` holds an original sample book for tests and screenshots (`tools/make-fixture-epubs.py`).

## Building
No Mac in the dev loop. Every push to `main` touching `App/`, `Packages/`, `content/` runs `.github/workflows/ios.yml` on `macos-26`:
CourseKit tests → xcodegen → simulator screenshots (pushed to the `ci-shots` branch) → unsigned IPA + `altstore.json` on release `latest`.
After pushing, run `App/scripts/wait-ci.sh` to wait for the run and print failed steps and annotations. Compile errors arrive as `::error::` annotations.
Screenshot states are launch arguments (`-tab home|library|review|lab|search`, `-course YES`, `-open 0-1`, `-theme`, `-scroll N`, `-showSettings YES`); add new states to `App/scripts/screenshots.sh`.

## Rules
- No API keys or secrets in the repo, ever. The Claude key lives only in the device Keychain.
- Lessons are fixed and reviewed: written once, frozen, with stable exercise IDs. Claude is a tutor at runtime, not an author.
- Course content never refers to the reel, video or article that prompted it. Sources for discovery stay in `authoring/` (git-ignored).
- Liquid Glass is for system chrome only (tab bar, toolbars, sheets, the bottom accessory, one prominent action). Reading surfaces are never glass.
- Reading themes: paper, sepia (default), dusk, night. Pastel tints only, as highlighter colours.
- Pastels across the app. Each course sets `theme` in `course.json`: a pastel `accent` for fills, `accentDeep` for text and icons on light surfaces, `onAccent` for labels on pastel, and its `landing` backdrop. Home is the landing page of the last-opened course; Library holds every course as a poster.
- Never commit a book's EPUB, text or cover to this public repo, never print titles in CI logs, and never render a real book in CI screenshots: screenshots use the fixture (`-fixtureBooks YES`). A book becomes part of the app like a course: its `book.json` sets the accent and landing backdrop (`cover` for any book, or a bespoke one like `web`), and new books arrive with a new build, not by in-app import.
- Commits: author `theVentus <50719962+theVentus@users.noreply.github.com>` (GitHub no-reply; never the personal email), end with the session attribution lines.

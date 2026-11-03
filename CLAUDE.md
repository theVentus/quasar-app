# Quasar (quasar-app)

Library app for rigorous, interactive courses. iOS 26, SwiftUI, Liquid Glass. Plan: `docs/PLAN.md`.

## Layout
- `content/courses/<id>/` — course packages (`qbd.course/1`): `course.json`, `lessons/*.lesson.md`, `models/*.json`. Bundled into the app as a folder resource.
- `Packages/QBDKit` — `CourseKit`: manifest, lesson parser, inline TeX → Unicode, expression evaluator, quantity formatting. Platform-free; tested with `swift test`.
- `App/` — XcodeGen spec (`project.yml`) and the `QBD` app target. `QBD.xcodeproj` and `Info.plist` are generated; never commit them.
- `web/` — the single-file web reader (`web/build.py` embeds fonts).

## Building
No Mac in the dev loop. Every push to `main` touching `App/`, `Packages/`, `content/` runs `.github/workflows/ios.yml` on `macos-26`:
CourseKit tests → xcodegen → simulator screenshots (pushed to the `ci-shots` branch) → unsigned IPA + `altstore.json` on release `latest`.
After pushing, run `App/scripts/wait-ci.sh` to wait for the run and print failed steps and annotations. Compile errors arrive as `::error::` annotations.
Screenshot states are launch arguments (`-tab`, `-course YES`, `-open 0-1`, `-theme`, `-scroll N`, `-showSettings YES`); add new states to `App/scripts/screenshots.sh`.

## Rules
- No API keys or secrets in the repo, ever. The Claude key lives only in the device Keychain.
- Lessons are fixed and reviewed: written once, frozen, with stable exercise IDs. Claude is a tutor at runtime, not an author.
- Course content never refers to the reel, video or article that prompted it. Sources for discovery stay in `authoring/` (git-ignored).
- Liquid Glass is for system chrome only (tab bar, toolbars, sheets, the bottom accessory, one prominent action). Reading surfaces are never glass.
- Reading themes: paper, sepia (default), dusk, night. Pastel tints only, as highlighter colours.
- Commits: author `theVentus`, end with the session attribution lines.

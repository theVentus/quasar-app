# Quasar to Blue Dot

A native iOS library of first-principles courses, built on Apple's Liquid Glass design language. Each course is a graph of lessons with worked derivations, interactive models, graded exercises, spaced review and a Claude tutor that knows where you are. The first course, *Quasar to Blue Dot*, explains how a phone finds its position, all the way down to the quasars that anchor Earth's orientation.

Status: planning. See [docs/PLAN.md](docs/PLAN.md) for the product plan, architecture and roadmap.

## Layout

| Path | Contents |
|---|---|
| `content/courses/` | Course packages in the shared `qbd.course/1` format: `course.json`, lessons, model specs |
| `content/fixtures/` | Conformance fixtures shared by the web and Swift parsers (to come) |
| `web/` | The single-file web reader (`src.html`), its fonts and build script. It is the reference implementation the app must match |
| `App/` | Xcode app target (to come in v0.1) |
| `Packages/` | SwiftPM packages: CourseKit, Learning, Reader, Lab, Tutor, Design (to come) |
| `tools/coursectl/` | Course authoring CLI: generate, validate, lint maths, pack (to come) |
| `proxy/` | Optional Claude API proxy (to come) |
| `docs/` | Plan, content format, architecture decision records |

## Web build

```sh
python3 web/build.py   # writes web/dist/quasar-to-blue-dot.html
```

## Rules

- No API keys or other secrets in the repo.
- Courses never refer to the reel or article that prompted them; sources stay in authoring notes outside the package.

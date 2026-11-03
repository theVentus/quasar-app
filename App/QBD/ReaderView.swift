import SwiftUI
import Observation
import CourseKit

/// Scroll-driven reader state, kept out of the reader's own body so scrolling only re-renders the glass bar,
/// never the page.
@Observable
final class ReaderScrollState {
    var progress = 0.0
    var compact = false
    var topVisible = 0
    @ObservationIgnored private var travel: CGFloat = 0

    /// Compacts after ~60 pt of steady downward scroll; restores after ~40 pt up or near the top. Ignores bounce.
    func scrolled(from old: CGFloat, to new: CGFloat, maxOffset: CGFloat, locked: Bool) {
        guard !locked else { return }
        if new < 120 { set(false); travel = 0; return }
        if new > maxOffset - 4 || old > maxOffset - 4 { return }
        let d = new - old
        travel = (d >= 0) == (travel >= 0) ? travel + d : d
        if travel > 60 { set(true) } else if travel < -40 { set(false) }
    }

    private func set(_ value: Bool) {
        guard value != compact else { return }
        withAnimation(.smooth(duration: 0.3)) { compact = value }
    }
}

struct ReaderView: View {
    @Environment(Library.self) private var library
    let course: CoursePackage
    let lessonID: String

    @AppStorage("theme") private var themeRaw = ReadingTheme.sepia.rawValue
    @AppStorage("textSize") private var textSize = 18.0
    @AppStorage("lastCourse") private var lastCourse = ""
    @AppStorage("lastItem") private var lastItem = ""
    @State private var panelOpen = false
    @State private var showContents = false
    @State private var scroll = ReaderScrollState()
    @State private var jump: Int?
    @Environment(\.colorScheme) private var systemScheme

    private var theme: ReadingTheme { ReadingTheme(rawValue: themeRaw) ?? .sepia }
    private var ref: CourseManifest.LessonRef? { course.manifest.lesson(lessonID) }

    var body: some View {
        Group {
            if let lesson = library.lesson(course: course, id: lessonID), let ref {
                let outline = Outline(lesson)
                ScrollViewReader { proxy in
                    ScrollView {
                        LessonBody(lesson: lesson, ref: ref, module: course.manifest.module(of: lessonID))
                            .padding(.horizontal, 22)
                            .padding(.top, 8)
                            .padding(.bottom, 40)
                    }
                    .onScrollGeometryChange(for: ScrollMetrics.self) { g in
                        ScrollMetrics(offset: g.contentOffset.y + g.contentInsets.top,
                                      range: g.contentSize.height - g.containerSize.height + g.contentInsets.top + g.contentInsets.bottom)
                    } action: { old, new in
                        let p = new.range > 0 ? min(1, max(0, new.offset / new.range)) : 0
                        if abs(p - scroll.progress) > 0.002 { scroll.progress = p }
                        scroll.scrolled(from: old.offset, to: new.offset, maxOffset: new.range, locked: panelOpen)
                    }
                    .onScrollTargetVisibilityChange(idType: Int.self, threshold: 0.01) { ids in
                        let top = ids.min() ?? 0
                        if top != scroll.topVisible { scroll.topVisible = top }
                    }
                    .safeAreaBar(edge: .bottom) {
                        ReaderBar(themeRaw: $themeRaw, textSize: $textSize, panelOpen: $panelOpen, scroll: scroll, outline: outline) {
                            showContents = true
                        }
                    }
                    .onChange(of: jump) { _, n in
                        guard let n else { return }
                        withAnimation(.smooth) { proxy.scrollTo(n, anchor: .top) }
                        jump = nil
                    }
                    .onAppear { applyLaunchState(proxy, lesson: lesson) }
                    .sheet(isPresented: $showContents) {
                        ContentsSheet(outline: outline, currentID: outline.entry(at: scroll.topVisible)?.id) { id in
                            showContents = false
                            jump = id
                        }
                        .presentationDetents([.medium, .large])
                    }
                }
            } else {
                ContentUnavailableView("Not written yet", systemImage: "doc.text", description: Text("This lesson hasn’t been published in this course version."))
            }
        }
        .environment(\.reading, ReadingStyle(theme: theme, size: textSize))
        .environment(\.labEntries, Dictionary(course.manifest.lab.map { ($0.model, $0) }, uniquingKeysWith: { a, _ in a }))
        .environment(\.coursePackage, course)
        // The theme's appearance applies to this screen only (not the whole window), so going back is instant.
        .environment(\.colorScheme, theme.scheme)
        .toolbarColorScheme(theme.scheme, for: .navigationBar)
        .statusBarHidden(theme.scheme != systemScheme)
        .background(theme.background.ignoresSafeArea())
        .toolbar(.hidden, for: .tabBar)
        .navigationTitle("Lesson \(ref?.number ?? lessonID)")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .principal) { Color.clear.frame(width: 1, height: 1) } }
    }

    private func applyLaunchState(_ proxy: ScrollViewProxy, lesson: Lesson) {
        lastCourse = course.id
        lastItem = "course:" + course.id
        if var n = LaunchState.scrollTo {
            // Negative values pick the nth interactive block (-1 = first), so screenshots don't depend on block counts.
            if n < 0 {
                let widgets = lesson.blocks.indices.filter {
                    if case .widget = lesson.blocks[$0] { return true }
                    if case .explore = lesson.blocks[$0] { return true }
                    return false
                }
                n = widgets.indices.contains(-n - 1) ? widgets[-n - 1] : 0
            }
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { proxy.scrollTo(n, anchor: .top) }
        }
        if LaunchState.showSettings {
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) { withAnimation(Motion.morph) { panelOpen = true } }
        }
        if LaunchState.showContents {
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { showContents = true }
        }
    }
}

/// Headings of a lesson, for the progress pill and the contents sheet.
struct Outline {
    struct Entry: Identifiable {
        let id: Int
        let number: String
        let title: String
        let level: Int
    }
    let entries: [Entry]
    let lessonTitle: String

    init(_ lesson: Lesson) {
        let numbers = SectionNumbering(lesson.blocks)
        var e: [Entry] = []
        for (i, b) in lesson.blocks.enumerated() {
            if case .heading(let level, let text) = b {
                e.append(Entry(id: i, number: numbers.label(at: i) ?? "", title: text, level: level))
            }
        }
        if !lesson.questions.isEmpty {
            e.append(Entry(id: LessonBody.exercisesAnchor, number: "\(numbers.next)", title: "Exercises", level: 2))
        }
        entries = e
        lessonTitle = lesson.title
    }

    func entry(at index: Int) -> Entry? { entries.last { $0.id <= index } }
    func title(at index: Int) -> String { entry(at: index).map { "\($0.number)  \($0.title)" } ?? lessonTitle }
}

/// Floating Liquid Glass controls over the page. The Aa button morphs into the appearance panel; the bar
/// compacts to a single progress pill while reading.
struct ScrollMetrics: Equatable {
    var offset: CGFloat
    var range: CGFloat
}

struct ReaderBar: View {
    @Environment(\.reading) private var r
    @Binding var themeRaw: String
    @Binding var textSize: Double
    @Binding var panelOpen: Bool
    let scroll: ReaderScrollState
    let outline: Outline
    let showContents: () -> Void
    @Namespace private var ns

    var body: some View {
        let compact = scroll.compact
        let section = outline.title(at: scroll.topVisible)
        let progress = scroll.progress
        GlassEffectContainer(spacing: 10) {
            VStack(spacing: 10) {
                if panelOpen {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack {
                            Text("Appearance").font(.headline)
                            Spacer()
                            Button { withAnimation(Motion.morph) { panelOpen = false } } label: {
                                Image(systemName: "xmark").font(.subheadline.weight(.semibold)).frame(width: 32, height: 32).contentShape(.circle)
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel("Close appearance")
                        }
                        ThemeSwatches(themeRaw: $themeRaw)
                        TextSizeControl(textSize: $textSize)
                    }
                    .padding(18)
                    .glassEffect(.regular, in: .rect(cornerRadius: 30))
                    .glassEffectID("aa", in: ns)
                }
                HStack(spacing: 10) {
                    if !compact {
                        Button(action: showContents) {
                            Image(systemName: "list.bullet").font(.body.weight(.medium)).frame(width: 50, height: 50).contentShape(.circle)
                        }
                        .buttonStyle(.plain)
                        .glassEffect(.regular.interactive(), in: .circle)
                        .glassEffectID("contents", in: ns)
                        .accessibilityLabel("Contents")
                    }
                    ProgressPill(section: section, progress: progress, compact: compact)
                        .glassEffect(.regular.interactive(), in: .capsule)
                        .glassEffectID("progress", in: ns)
                        .onTapGesture(perform: showContents)
                    if !compact && !panelOpen {
                        Button { withAnimation(Motion.morph) { panelOpen = true } } label: {
                            Text("Aa").font(Typeface.serif(19)).frame(width: 50, height: 50).contentShape(.circle)
                        }
                        .buttonStyle(.plain)
                        .glassEffect(.regular.interactive(), in: .circle)
                        .glassEffectID("aa", in: ns)
                        .accessibilityLabel("Appearance")
                    }
                }
                .frame(maxWidth: compact ? 250 : .infinity)
            }
            .foregroundStyle(r.theme.ink)
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 4)
    }
}

struct ProgressPill: View {
    @Environment(\.accent) private var accent
    let section: String
    let progress: Double
    let compact: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 6) {
                Text(section).font(.footnote.weight(.semibold)).lineLimit(1)
                Spacer(minLength: 6)
                Text("\(Int((progress * 100).rounded()))%")
                    .font(.caption.weight(.medium))
                    .monospacedDigit()
                    .opacity(0.6)
            }
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.primary.opacity(0.12))
                    Capsule().fill(accent.pastel).frame(width: max(3, g.size.width * progress))
                }
            }
            .frame(height: 3)
        }
        .padding(.horizontal, 18)
        .frame(height: compact ? 42 : 50)
        .frame(maxWidth: .infinity)
        .contentShape(.capsule)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(section), \(Int(progress * 100)) percent read")
        .accessibilityAddTraits(.isButton)
    }
}

struct ContentsSheet: View {
    let outline: Outline
    let currentID: Int?
    let go: (Int) -> Void

    var body: some View {
        NavigationStack {
            List(outline.entries) { e in
                Button { go(e.id) } label: {
                    HStack(alignment: .firstTextBaseline, spacing: 12) {
                        Text(e.number).monospacedDigit().foregroundStyle(.secondary).frame(width: 30, alignment: .leading)
                        Text(e.title).font(Typeface.serif(18)).foregroundStyle(.primary)
                        Spacer()
                        if e.id == currentID {
                            Image(systemName: "bookmark.fill").font(.caption).foregroundStyle(.tint)
                        }
                    }
                    .padding(.leading, e.level > 2 ? 20 : 0)
                }
            }
            .navigationTitle(outline.lessonTitle)
            .navigationBarTitleDisplayMode(.inline)
        }
    }
}

struct LessonBody: View {
    /// Scroll anchor for the exercises (`-scroll 10000`).
    static let exercisesAnchor = 10_000
    @Environment(\.reading) private var r
    let lesson: Lesson
    let ref: CourseManifest.LessonRef
    let module: CourseManifest.Module?

    var body: some View {
        let numbers = SectionNumbering(lesson.blocks)
        LazyVStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 12) {
                Text("LESSON \(ref.number)" + (module.map { " · MODULE \($0.id): \($0.title.uppercased())" } ?? ""))
                    .font(.caption.weight(.semibold))
                    .tracking(1.1)
                    .foregroundStyle(r.theme.ink3)
                Text(lesson.title)
                    .font(Typeface.serif(r.size * 1.75))
                    .foregroundStyle(r.theme.ink)
                if !lesson.abstract.isEmpty {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Abstract").font(Typeface.serif(r.size * 0.88, bold: true))
                        Text(Prose.attributed(lesson.abstract, style: r, scale: 0.88))
                    }
                    .foregroundStyle(r.theme.ink)
                    .padding(.top, 4)
                }
            }
            .padding(.bottom, 6)

            ForEach(Array(lesson.blocks.enumerated()), id: \.offset) { i, block in
                BlockView(block: block, number: numbers.label(at: i))
                    .id(i)
            }

            if !lesson.questions.isEmpty {
                ExercisesView(questions: lesson.questions, number: numbers.next)
                    .id(LessonBody.exercisesAnchor)
            }
            if !lesson.references.isEmpty {
                ReferencesView(references: lesson.references)
            }
        }
        .scrollTargetLayout()
        .foregroundStyle(r.theme.ink)
    }
}

/// LaTeX-style section numbers for top-level `##` headings.
struct SectionNumbering {
    private var labels: [Int: String] = [:]
    private(set) var next = 1

    init(_ blocks: [Block]) {
        var s = 0, sub = 0
        for (i, b) in blocks.enumerated() {
            if case .heading(let level, _) = b {
                if level == 2 { s += 1; sub = 0; labels[i] = "\(s)" } else { sub += 1; labels[i] = "\(s).\(sub)" }
            }
        }
        next = s + 1
    }

    func label(at i: Int) -> String? { labels[i] }
}

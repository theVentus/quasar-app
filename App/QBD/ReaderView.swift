import SwiftUI
import CourseKit

struct ReaderView: View {
    @Environment(Library.self) private var library
    let course: CoursePackage
    let lessonID: String

    @AppStorage("theme") private var themeRaw = ReadingTheme.sepia.rawValue
    @AppStorage("textSize") private var textSize = 18.0
    @State private var showSettings = false

    private var theme: ReadingTheme { ReadingTheme(rawValue: themeRaw) ?? .sepia }
    private var ref: CourseManifest.LessonRef? { course.manifest.lesson(lessonID) }

    var body: some View {
        Group {
            if let lesson = library.lesson(course: course, id: lessonID), let ref {
                ScrollViewReader { proxy in
                    ScrollView {
                        LessonBody(lesson: lesson, ref: ref, module: course.manifest.module(of: lessonID))
                            .padding(.horizontal, 22)
                            .padding(.top, 8)
                            .padding(.bottom, 60)
                    }
                    .scrollEdgeEffectStyle(.soft, for: .top)
                    .onAppear {
                        if let n = LaunchState.scrollTo {
                            DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { proxy.scrollTo(n, anchor: .top) }
                        }
                    }
                }
            } else {
                ContentUnavailableView("Not written yet", systemImage: "doc.text", description: Text("This lesson hasn’t been published in this course version."))
            }
        }
        .environment(\.reading, ReadingStyle(theme: theme, size: textSize))
        .environment(\.labEntries, Dictionary(course.manifest.lab.map { ($0.model, $0) }, uniquingKeysWith: { a, _ in a }))
        .background(theme.background.ignoresSafeArea())
        .preferredColorScheme(theme.scheme)
        .toolbar(.hidden, for: .tabBar)
        .navigationTitle("Lesson \(ref?.number ?? lessonID)")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { showSettings = true } label: { Image(systemName: "textformat.size") }
                    .accessibilityLabel("Reading settings")
            }
        }
        .sheet(isPresented: $showSettings) {
            ReadingSettingsSheet(themeRaw: $themeRaw, textSize: $textSize)
                .presentationDetents([.medium, .large])
        }
        .onAppear { if LaunchState.showSettings { showSettings = true } }
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

struct ReadingSettingsSheet: View {
    @Binding var themeRaw: String
    @Binding var textSize: Double
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section("Theme") {
                    HStack(spacing: 12) {
                        ForEach(ReadingTheme.allCases) { t in
                            Button { themeRaw = t.rawValue } label: {
                                VStack(spacing: 6) {
                                    Text("Aa")
                                        .font(Typeface.serif(22))
                                        .foregroundStyle(t.ink)
                                        .frame(maxWidth: .infinity)
                                        .frame(height: 56)
                                        .background(t.background, in: .rect(cornerRadius: 14))
                                        .overlay {
                                            RoundedRectangle(cornerRadius: 14)
                                                .strokeBorder(themeRaw == t.rawValue ? Color.accentColor : Color.secondary.opacity(0.25),
                                                              lineWidth: themeRaw == t.rawValue ? 2.5 : 0.5)
                                        }
                                    Text(t.label).font(.caption).foregroundStyle(.secondary)
                                }
                            }
                            .buttonStyle(.plain)
                            .accessibilityLabel("\(t.label) theme")
                            .accessibilityAddTraits(themeRaw == t.rawValue ? .isSelected : [])
                        }
                    }
                    .padding(.vertical, 4)
                }
                Section("Text size") {
                    HStack {
                        Text("A").font(Typeface.serif(14))
                        Slider(value: $textSize, in: 15...24, step: 0.5)
                        Text("A").font(Typeface.serif(24))
                    }
                }
                Section {
                    Text("More fonts, spacing, margins and paged layout arrive with the full reader.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
            .navigationTitle("Appearance")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } }
            }
        }
    }
}

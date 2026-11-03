import SwiftUI
import CourseKit

/// Review: spaced retrieval of exercises (v0.2). Honest empty state until then.
struct ReviewView: View {
    var body: some View {
        ContentUnavailableView {
            Label("Nothing to review yet", systemImage: "rectangle.stack")
        } description: {
            Text("Exercises you attempt will come back here on a spaced schedule: 1, 3, 7 and 21 days later.")
        }
        .navigationTitle("Review")
    }
}

/// Lab: every interactive model across installed courses. Explore models open live; bespoke engines follow.
struct LabView: View {
    @Environment(Library.self) private var library
    @State private var open: LabTarget?

    struct LabTarget: Hashable, Identifiable {
        var course: String
        var model: String
        var id: String { course + "/" + model }
    }

    var body: some View {
        List {
            ForEach(library.courses) { course in
                Section(course.manifest.title) {
                    ForEach(course.manifest.lab) { entry in
                        let live = course.exploreModel(entry.model) != nil
                        Button { if live { open = LabTarget(course: course.id, model: entry.model) } } label: {
                            HStack(alignment: .top, spacing: 14) {
                                Image(systemName: live ? "slider.horizontal.3" : "testtube.2")
                                    .foregroundStyle(.tint)
                                    .frame(width: 28)
                                VStack(alignment: .leading, spacing: 3) {
                                    Text(entry.title).font(Typeface.serif(18)).foregroundStyle(.primary)
                                    Text(entry.blurb).font(.subheadline).foregroundStyle(.secondary)
                                    Text("Lesson \(entry.lesson.replacingOccurrences(of: "-", with: ".")) · " + (live ? entry.`where` : "simulation arrives with the full Lab"))
                                        .font(.caption)
                                        .foregroundStyle(.tertiary)
                                }
                                Spacer(minLength: 0)
                                if live { Image(systemName: "chevron.right").font(.footnote.weight(.semibold)).foregroundStyle(.tertiary) }
                            }
                            .padding(.vertical, 4)
                            .contentShape(.rect)
                        }
                        .buttonStyle(.plain)
                        .accessibilityElement(children: .combine)
                    }
                }
            }
        }
        .navigationTitle("Lab")
        .navigationDestination(item: $open) { t in
            if let c = library.course(t.course), let m = c.exploreModel(t.model) {
                LabModelPage(course: c, model: m)
            }
        }
        .onAppear {
            if let m = LaunchState.labModel, let c = library.courses.first, open == nil { open = LabTarget(course: c.id, model: m) }
        }
    }
}

/// One model on its own page, in the reader's theme.
struct LabModelPage: View {
    let course: CoursePackage
    let model: ExploreModel
    @AppStorage("theme") private var themeRaw = ReadingTheme.sepia.rawValue
    @AppStorage("textSize") private var textSize = 18.0
    @Environment(\.colorScheme) private var systemScheme

    var body: some View {
        let theme = ReadingTheme.resolve(themeRaw)
        ScrollView {
            ExploreCard(model: model)
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
        }
        .environment(\.reading, ReadingStyle(theme: theme, size: textSize))
        .environment(\.coursePackage, course)
        .environment(\.colorScheme, theme.scheme)
        .toolbarColorScheme(theme.scheme, for: .navigationBar)
        .statusBarHidden(theme.scheme != systemScheme)
        .background(theme.background.ignoresSafeArea())
        .navigationTitle(model.title)
        .navigationBarTitleDisplayMode(.inline)
    }
}

/// Ask: Claude as tutor, using the reader's own API key kept in the Keychain (v0.2).
struct AskView: View {
    var body: some View {
        ContentUnavailableView {
            Label("Ask Claude", systemImage: "bubble.left.and.text.bubble.right")
        } description: {
            Text("Select a passage in any lesson to have it explained, or ask a question here. Arrives in v0.2. Your key stays on this iPhone.")
        }
        .navigationTitle("Ask")
    }
}

/// Search across lesson titles in every installed course.
struct SearchView: View {
    @Environment(Library.self) private var library
    @State private var query = ""

    private var results: [(CoursePackage, CourseManifest.LessonRef)] {
        let q = query.trimmingCharacters(in: .whitespaces)
        return library.courses.flatMap { c in
            c.manifest.allLessons
                .filter { q.isEmpty || $0.title.localizedCaseInsensitiveContains(q) || $0.number.hasPrefix(q) }
                .map { (c, $0) }
        }
    }

    var body: some View {
        List {
            ForEach(Array(results.enumerated()), id: \.offset) { _, pair in
                let (course, lesson) = pair
                if lesson.isPublished {
                    NavigationLink(value: Route.lesson(course: course.id, lesson: lesson.id)) { LessonRow(lesson: lesson) }
                } else {
                    LessonRow(lesson: lesson)
                }
            }
        }
        .overlay {
            if results.isEmpty { ContentUnavailableView.search(text: query) }
        }
        .searchable(text: $query, prompt: "Lessons")
        .navigationTitle("Search")
    }
}

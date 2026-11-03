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

/// Lab: every interactive model across installed courses.
struct LabView: View {
    @Environment(Library.self) private var library

    var body: some View {
        List {
            ForEach(library.courses) { course in
                Section(course.manifest.title) {
                    ForEach(course.manifest.lab) { entry in
                        HStack(alignment: .top, spacing: 14) {
                            Image(systemName: "testtube.2")
                                .foregroundStyle(.tint)
                                .frame(width: 28)
                            VStack(alignment: .leading, spacing: 3) {
                                Text(entry.title).font(Typeface.serif(18))
                                Text(entry.blurb).font(.subheadline).foregroundStyle(.secondary)
                                Text("Lesson \(entry.lesson.replacingOccurrences(of: "-", with: ".")) · \(entry.`where`)")
                                    .font(.caption)
                                    .foregroundStyle(.tertiary)
                            }
                        }
                        .padding(.vertical, 4)
                        .accessibilityElement(children: .combine)
                    }
                }
            }
            Section {
                Text("Models become live, with sliders and plots, in v0.3.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Lab")
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

import SwiftUI
import CourseKit

struct CourseView: View {
    let course: CoursePackage
    private var m: CourseManifest { course.manifest }

    var body: some View {
        List {
            Section {
                VStack(alignment: .leading, spacing: 10) {
                    CoverArt()
                        .frame(height: 150)
                        .clipShape(.rect(cornerRadius: 18))
                    Text(m.subtitle)
                        .font(Typeface.serif(19, italic: true))
                    Text("Thirteen modules, built backwards from what you need to explain, calculate and critically assess satellite positioning.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .listRowInsets(EdgeInsets(top: 12, leading: 12, bottom: 12, trailing: 12))
            }
            ForEach(m.modules) { module in
                Section {
                    ForEach(module.lessons) { lesson in
                        if lesson.isPublished {
                            NavigationLink(value: Route.lesson(course: course.id, lesson: lesson.id)) {
                                LessonRow(lesson: lesson)
                            }
                        } else {
                            LessonRow(lesson: lesson)
                        }
                    }
                } header: {
                    HStack(alignment: .firstTextBaseline) {
                        Text("M\(module.id)").monospacedDigit().foregroundStyle(.tertiary)
                        Text(module.title)
                        Spacer()
                        Text(tagLabel(module.tag))
                            .font(.caption2.weight(.semibold))
                            .padding(.horizontal, 6).padding(.vertical, 2)
                            .background(Color.secondary.opacity(0.14), in: .rect(cornerRadius: 5))
                    }
                } footer: {
                    Text(module.why)
                }
            }
            Section("Key sources") {
                ForEach(Array(m.references.enumerated()), id: \.offset) { i, r in
                    VStack(alignment: .leading, spacing: 2) {
                        Text("[\(i + 1)] \(r.text)").font(.footnote)
                        if let u = r.url, let url = URL(string: u) {
                            Link(u, destination: url).font(.caption).lineLimit(1)
                        }
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
        .navigationTitle(m.title)
        .navigationBarTitleDisplayMode(.large)
    }

    private func tagLabel(_ tag: String) -> String {
        tag.lowercased().hasPrefix("mostly optional") || tag.lowercased().hasPrefix("optional") ? "Optional" : "Essential"
    }
}

struct LessonRow: View {
    let lesson: CourseManifest.LessonRef

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 10) {
            Text(lesson.number)
                .font(.subheadline.weight(.medium))
                .monospacedDigit()
                .foregroundStyle(.secondary)
                .frame(width: 36, alignment: .leading)
            Text(lesson.title)
                .font(Typeface.serif(17))
                .foregroundStyle(lesson.isPublished ? .primary : .secondary)
            Spacer(minLength: 6)
            if !lesson.isPublished {
                Text("Not written")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
        }
        .accessibilityElement(children: .combine)
    }
}

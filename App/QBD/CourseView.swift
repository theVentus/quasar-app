import SwiftUI
import CourseKit

/// Syllabus: the sky as a hero under the navigation bar, and a glass module rail that tracks the scroll.
struct CourseView: View {
    let course: CoursePackage
    @AppStorage("lastCourse") private var lastCourse = ""
    @State private var current: Int?
    private var m: CourseManifest { course.manifest }

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                VStack(spacing: 0) {
                    CourseHero(manifest: m)
                    LazyVStack(alignment: .leading, spacing: 40) {
                        ForEach(m.modules) { module in
                            ModuleSection(course: course, module: module).id(module.id)
                        }
                        SourcesSection(references: m.references)
                    }
                    .scrollTargetLayout()
                    .padding(.horizontal, 16)
                    .padding(.top, 28)
                    .padding(.bottom, 40)
                }
            }
            .onScrollTargetVisibilityChange(idType: Int.self, threshold: 0.05) { ids in
                if let first = ids.min(), first != current { withAnimation(Motion.morph) { current = first } }
            }
            .safeAreaBar(edge: .top) {
                ModuleRail(modules: m.modules, current: current ?? 0) { id in
                    withAnimation(.smooth) { proxy.scrollTo(id, anchor: .top) }
                }
            }
            .onAppear {
                lastCourse = course.id
                if let n = LaunchState.scrollTo, m.modules.contains(where: { $0.id == n }) {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { proxy.scrollTo(n, anchor: .top) }
                }
            }
        }
        .navigationTitle(m.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .principal) { Color.clear.frame(width: 1, height: 1) } }
    }
}

/// The sky extends 600 pt above the hero so it fills the area under the navigation bar and rail, and the overscroll.
struct CourseHero: View {
    let manifest: CourseManifest

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Spacer(minLength: 0)
            Text("\(manifest.modules.count) MODULES · \(manifest.allLessons.count) LESSONS")
                .font(.caption.weight(.semibold))
                .tracking(1.6)
                .foregroundStyle(.white.opacity(0.6))
            Text(manifest.title)
                .font(Typeface.serif(40))
                .foregroundStyle(.white)
            Text(manifest.subtitle)
                .font(Typeface.serif(18, italic: true))
                .foregroundStyle(.white.opacity(0.78))
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
        .frame(height: 340)
        .background(alignment: .bottom) {
            SkyView(quasar: UnitPoint(x: 0.16, y: 0.56), earth: UnitPoint(x: 0.84, y: 0.70))
                .frame(height: 940)
        }
        .environment(\.colorScheme, .dark)
    }
}

/// Glass chips; the current module's chip widens to show its title and the glass morphs between them.
struct ModuleRail: View {
    @Environment(\.accent) private var accent
    let modules: [CourseManifest.Module]
    let current: Int
    let select: (Int) -> Void

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView(.horizontal) {
                GlassEffectContainer(spacing: 6) {
                    HStack(spacing: 6) {
                        ForEach(modules) { mod in
                            let on = mod.id == current
                            Button { select(mod.id) } label: {
                                HStack(spacing: 7) {
                                    Text("\(mod.id)").monospacedDigit().fontWeight(.bold)
                                    if on { Text(mod.title).lineLimit(1) }
                                }
                                .font(.subheadline)
                                .foregroundStyle(on ? accent.onPastel : Color.primary)
                                .padding(.horizontal, 14)
                                .padding(.vertical, 9)
                                .contentShape(.capsule)
                            }
                            .buttonStyle(.plain)
                            .glassEffect(on ? Glass.regular.tint(accent.pastel.opacity(0.9)).interactive() : Glass.regular.interactive(), in: .capsule)
                            .id(mod.id)
                            .accessibilityLabel("Module \(mod.id), \(mod.title)")
                            .accessibilityAddTraits(on ? .isSelected : [])
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 6)
                }
            }
            .scrollIndicators(.hidden)
            .onChange(of: current) { _, c in withAnimation(.smooth) { proxy.scrollTo(c, anchor: .center) } }
        }
    }
}

struct ModuleSection: View {
    @Environment(\.accent) private var accent
    let course: CoursePackage
    let module: CourseManifest.Module
    private var optional: Bool { module.tag.lowercased().contains("optional") }

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline) {
                Text("MODULE \(module.id)")
                    .font(.caption.weight(.semibold))
                    .tracking(1.4)
                    .foregroundStyle(.secondary)
                Spacer()
                Text(optional ? "Optional" : "Essential")
                    .font(.caption2.weight(.semibold))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .foregroundStyle(optional ? Color.secondary : accent.tint)
                    .background(optional ? Color.secondary.opacity(0.12) : accent.pastel.opacity(0.35), in: .capsule)
            }
            Text(module.title).font(Typeface.serif(28))
            Text(module.why)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
            VStack(spacing: 0) {
                ForEach(Array(module.lessons.enumerated()), id: \.element.id) { i, lesson in
                    if i > 0 { Divider().padding(.leading, 62) }
                    if lesson.isPublished {
                        NavigationLink(value: Route.lesson(course: course.id, lesson: lesson.id)) {
                            LessonRow(lesson: lesson, showsChevron: true)
                                .padding(.horizontal, 16)
                                .padding(.vertical, 14)
                                .contentShape(.rect)
                        }
                        .buttonStyle(.plain)
                    } else {
                        LessonRow(lesson: lesson)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 14)
                    }
                }
            }
            .background(.background.secondary, in: .rect(cornerRadius: 22))
            .padding(.top, 4)
        }
    }
}

struct SourcesSection: View {
    let references: [CourseManifest.Reference]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("KEY SOURCES")
                .font(.caption.weight(.semibold))
                .tracking(1.4)
                .foregroundStyle(.secondary)
            ForEach(Array(references.enumerated()), id: \.offset) { i, r in
                VStack(alignment: .leading, spacing: 2) {
                    Text("[\(i + 1)] \(r.text)").font(.footnote)
                    if let u = r.url, let url = URL(string: u) {
                        Link(u, destination: url).font(.caption).lineLimit(1)
                    }
                }
            }
        }
    }
}

struct LessonRow: View {
    let lesson: CourseManifest.LessonRef
    var showsChevron = false

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
            } else if showsChevron {
                Image(systemName: "chevron.right")
                    .font(.footnote.weight(.semibold))
                    .foregroundStyle(.tertiary)
            }
        }
        .accessibilityElement(children: .combine)
    }
}

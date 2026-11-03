import SwiftUI
import CourseKit

/// Two directions under review, switchable in Settings: an immersive night sky, or poster cards.
struct LibraryView: View {
    @Environment(Library.self) private var library
    @Binding var path: [Route]
    @AppStorage("libraryStyle") private var style = "sky"
    @State private var showSettings = false

    var body: some View {
        Group {
            if style == "poster" { posterLibrary } else { skyLibrary }
        }
        .sheet(isPresented: $showSettings) {
            AppSettingsView().presentationDetents([.medium, .large])
        }
        .onAppear { if LaunchState.showAppSettings { showSettings = true } }
    }

    private func open(_ course: CoursePackage, _ lessonID: String?) {
        path = lessonID.map { [.course(course.id), .lesson(course: course.id, lesson: $0)] } ?? [.course(course.id)]
    }

    // MARK: Night sky

    private var skyLibrary: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                HStack {
                    Text("Library").font(.largeTitle.bold())
                    Spacer()
                    Button { showSettings = true } label: {
                        Image(systemName: "gearshape").font(.title3).frame(width: 46, height: 46).contentShape(.circle)
                    }
                    .buttonStyle(.plain)
                    .glassEffect(.regular.interactive(), in: .circle)
                    .accessibilityLabel("Settings")
                }
                .padding(.horizontal, 20)
                .padding(.top, 6)

                ForEach(Array(library.courses.enumerated()), id: \.offset) { i, course in
                    SkyPoster(course: course, index: i) { open(course, $0) }
                        .containerRelativeFrame(.vertical) { h, _ in h * 0.8 }
                }
                if let e = library.loadError {
                    Text(e).font(.footnote).foregroundStyle(.secondary).padding(20)
                }
            }
        }
        .scrollIndicators(.hidden)
        .background { SkyView().ignoresSafeArea() }
        .environment(\.colorScheme, .dark)
        .toolbar(.hidden, for: .navigationBar)
    }

    // MARK: Posters

    private var posterLibrary: some View {
        ScrollView {
            VStack(spacing: 20) {
                ForEach(Array(library.courses.enumerated()), id: \.offset) { i, course in
                    PosterCard(course: course, index: i) { open(course, $0) }
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 24)
        }
        .navigationTitle("Library")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { showSettings = true } label: { Image(systemName: "gearshape") }
                    .accessibilityLabel("Settings")
            }
        }
    }
}

/// A course as typography on the sky. Glass only on the chips and actions.
struct SkyPoster: View {
    let course: CoursePackage
    let index: Int
    let open: (String?) -> Void
    private var m: CourseManifest { course.manifest }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Spacer(minLength: 0)
            Text("COURSE \(index + 1)")
                .font(.caption.weight(.semibold))
                .tracking(2)
                .foregroundStyle(.white.opacity(0.6))
            Text(m.title)
                .font(Typeface.serif(50))
                .foregroundStyle(.white)
                .lineLimit(2)
                .minimumScaleFactor(0.6)
            Text(m.subtitle)
                .font(Typeface.serif(20, italic: true))
                .foregroundStyle(.white.opacity(0.75))
            CourseStats(manifest: m).padding(.top, 4)
            CourseActions(manifest: m, open: open).padding(.top, 8)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(.horizontal, 24)
        .padding(.bottom, 28)
    }
}

/// A course as a full-bleed card with glass controls over its art.
struct PosterCard: View {
    let course: CoursePackage
    let index: Int
    let open: (String?) -> Void
    private var m: CourseManifest { course.manifest }

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            SkyView(quasar: UnitPoint(x: 0.8, y: 0.15), earth: UnitPoint(x: 0.24, y: 0.36))
            LinearGradient(colors: [.clear, .black.opacity(0.5)], startPoint: .center, endPoint: .bottom)
            VStack(alignment: .leading, spacing: 12) {
                Text(m.title).font(Typeface.serif(38)).foregroundStyle(.white)
                Text(m.subtitle).font(Typeface.serif(18, italic: true)).foregroundStyle(.white.opacity(0.8))
                CourseStats(manifest: m)
                CourseActions(manifest: m, open: open).padding(.top, 4)
            }
            .padding(20)
        }
        .frame(height: 540)
        .clipShape(.rect(cornerRadius: 38))
        .environment(\.colorScheme, .dark)
        .contentShape(.rect(cornerRadius: 38))
        .onTapGesture { open(nil) }
    }
}

struct CourseStats: View {
    let manifest: CourseManifest

    var body: some View {
        let hours = Int(manifest.modules.reduce(0) { $0 + $1.hours })
        GlassEffectContainer(spacing: 8) {
            HStack(spacing: 8) {
                chip("\(manifest.modules.count) modules")
                chip("\(manifest.allLessons.count) lessons")
                chip("≈ \(hours) h")
            }
        }
    }

    private func chip(_ s: String) -> some View {
        Text(s)
            .font(.footnote.weight(.semibold))
            .monospacedDigit()
            .padding(.horizontal, 12)
            .padding(.vertical, 7)
            .glassEffect(.regular, in: .capsule)
    }
}

struct CourseActions: View {
    let manifest: CourseManifest
    let open: (String?) -> Void
    private var next: CourseManifest.LessonRef? { manifest.allLessons.first(where: \.isPublished) }

    var body: some View {
        GlassEffectContainer(spacing: 12) {
            HStack(spacing: 12) {
                if let next {
                    Button { open(next.id) } label: {
                        Label("Start \(next.number)", systemImage: "play.fill")
                            .font(.headline)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 8)
                    }
                    .buttonStyle(.glassProminent)
                }
                Button { open(nil) } label: {
                    Text("Syllabus")
                        .font(.headline)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                }
                .buttonStyle(.glass)
            }
        }
    }
}

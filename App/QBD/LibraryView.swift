import SwiftUI
import CourseKit
import BookKit

/// Every installed course as a poster card.
struct LibraryView: View {
    @Environment(Library.self) private var library
    @Environment(Bookshelf.self) private var shelf
    @AppStorage("lastCourse") private var lastCourse = ""
    @Binding var path: [Route]
    @State private var showSettings = false

    var body: some View {
        ScrollViewReader { proxy in
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                ShelfHeader(title: "Courses", count: library.courses.count)
                ForEach(Array(library.courses.enumerated()), id: \.offset) { _, course in
                    PosterCard(course: course) { lessonID in
                        lastCourse = course.id
                        path = lessonID.map { [.course(course.id), .lesson(course: course.id, lesson: $0)] } ?? [.course(course.id)]
                    }
                }
                if !shelf.books.isEmpty || shelf.lockedCount > 0 {
                    ShelfHeader(title: "Books", count: shelf.books.count).padding(.top, 12).id("books")
                    if shelf.lockedCount > 0 { LockedBooksCard() }
                    ForEach(shelf.books) { book in
                        BookPoster(book: book) { route in path = [route] }
                    }
                }
                if let e = library.loadError {
                    Text(e).font(.footnote).foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 24)
        }
        .onAppear {
            if LaunchState.libraryBooks {
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.8) { proxy.scrollTo("books", anchor: .top) }
            }
        }
        }
        .navigationTitle("Library")
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button { showSettings = true } label: { Image(systemName: "gearshape") }
                    .accessibilityLabel("Settings")
            }
        }
        .sheet(isPresented: $showSettings) {
            AppSettingsView().presentationDetents([.medium, .large])
        }
    }
}

struct ShelfHeader: View {
    let title: String
    let count: Int

    var body: some View {
        HStack(alignment: .firstTextBaseline) {
            Text(title).font(Typeface.serif(26))
            Spacer()
            Text("\(count)").font(.subheadline.weight(.semibold)).monospacedDigit().foregroundStyle(.secondary)
        }
        .padding(.horizontal, 4)
        .accessibilityAddTraits(.isHeader)
    }
}

/// A course as a full-bleed card with glass controls over its art. The card carries its own course's accent.
struct PosterCard: View {
    let course: CoursePackage
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
        .overlay { RoundedRectangle(cornerRadius: 38).strokeBorder(.white.opacity(0.14), lineWidth: 1) }
        .environment(\.colorScheme, .dark)
        .environment(\.accent, CourseAccent(m.theme))
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

/// Start is the one prominent action: pastel glass with dark ink, so it reads on any backdrop.
struct CourseActions: View {
    @Environment(\.accent) private var accent
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
                            .foregroundStyle(accent.onPastel)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 8)
                    }
                    .buttonStyle(.glassProminent)
                    .tint(accent.pastel)
                }
                Button { open(nil) } label: {
                    Text("Syllabus")
                        .font(.headline)
                        .foregroundStyle(.primary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                }
                .buttonStyle(.glass)
            }
        }
    }
}

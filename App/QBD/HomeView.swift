import SwiftUI
import CourseKit
import BookKit

/// Home is the landing page of the course or book you last opened, drawn in its own style.
struct HomeView: View {
    @Environment(Library.self) private var library
    @Environment(Bookshelf.self) private var shelf
    @AppStorage("lastCourse") private var lastCourse = ""
    @AppStorage("lastItem") private var lastItem = ""
    @Binding var path: [Route]
    @State private var showSettings = false

    private var lastBook: Book? {
        if case .book(let id)? = LastItem(LaunchState.lastItem ?? lastItem) { return shelf.book(id) }
        return nil
    }

    var body: some View {
        Group {
            if let book = lastBook {
                BookLanding(book: book, showSettings: $showSettings) { route in
                    path = [route]
                }
                .environment(\.accent, CourseAccent(book.manifest.theme))
            } else if let course = library.course(lastCourse) ?? library.courses.first {
                CourseLanding(course: course, showSettings: $showSettings) { lessonID in
                    path = lessonID.map { [.course(course.id), .lesson(course: course.id, lesson: $0)] } ?? [.course(course.id)]
                }
            } else {
                ContentUnavailableView("No courses installed", systemImage: "books.vertical",
                                       description: Text(library.loadError ?? "Courses appear here once installed."))
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .sheet(isPresented: $showSettings) {
            AppSettingsView().presentationDetents([.medium, .large])
        }
        .onAppear { if LaunchState.showAppSettings { showSettings = true } }
    }
}

/// Each course chooses its landing backdrop in `course.json` (`theme.landing`). Only `sky` exists so far.
struct CourseLanding: View {
    let course: CoursePackage
    @Binding var showSettings: Bool
    let open: (String?) -> Void
    private var m: CourseManifest { course.manifest }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                HStack {
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

                VStack(alignment: .leading, spacing: 14) {
                    Spacer(minLength: 0)
                    Text("NOW STUDYING")
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
                .containerRelativeFrame(.vertical) { h, _ in h * 0.82 }
            }
        }
        .scrollIndicators(.hidden)
        .background { backdrop.ignoresSafeArea() }
        .environment(\.colorScheme, .dark)
    }

    @ViewBuilder private var backdrop: some View {
        switch m.theme?.landing ?? "sky" {
        default: SkyView(quasar: UnitPoint(x: 0.8, y: 0.15), earth: UnitPoint(x: 0.22, y: 0.3))
        }
    }
}

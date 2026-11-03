import SwiftUI

@main
struct QBDApp: App {
    @State private var library = Library()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(library)
        }
    }
}

/// Liquid Glass comes from system components: the tab bar (minimises on scroll), toolbars, sheets and the bottom accessory.
/// Course content is never glass.
struct RootView: View {
    @Environment(Library.self) private var library
    @State private var tab: AppTab = .library
    @State private var libraryPath: [Route] = []
    @State private var searchPath: [Route] = []

    var body: some View {
        TabView(selection: $tab) {
            Tab("Library", systemImage: "books.vertical", value: AppTab.library) {
                NavigationStack(path: $libraryPath) {
                    LibraryView(path: $libraryPath)
                        .navigationDestination(for: Route.self) { RouteView(route: $0) }
                }
            }
            Tab("Review", systemImage: "rectangle.stack", value: AppTab.review) {
                NavigationStack { ReviewView() }
            }
            Tab("Lab", systemImage: "testtube.2", value: AppTab.lab) {
                NavigationStack { LabView() }
            }
            Tab("Ask", systemImage: "bubble.left.and.text.bubble.right", value: AppTab.ask) {
                NavigationStack { AskView() }
            }
            Tab(value: AppTab.search, role: .search) {
                NavigationStack(path: $searchPath) {
                    SearchView()
                        .navigationDestination(for: Route.self) { RouteView(route: $0) }
                }
            }
        }
        .tabBarMinimizeBehavior(.onScrollDown)
        .tabViewBottomAccessory {
            NowReadingAccessory { course, lesson in
                tab = .library
                libraryPath = [.course(course), .lesson(course: course, lesson: lesson)]
            }
        }
        .onAppear(perform: applyLaunchState)
    }

    private func applyLaunchState() {
        if let t = LaunchState.tab { tab = t }
        guard let c = library.courses.first else { return }
        if LaunchState.openCourse { libraryPath = [.course(c.id)] }
        if let l = LaunchState.openLesson { tab = .library; libraryPath = [.course(c.id), .lesson(course: c.id, lesson: l)] }
    }
}

struct RouteView: View {
    @Environment(Library.self) private var library
    let route: Route

    var body: some View {
        switch route {
        case .course(let id):
            if let c = library.course(id) { CourseView(course: c) } else { MissingView() }
        case .lesson(let cid, let lid):
            if let c = library.course(cid) { ReaderView(course: c, lessonID: lid) } else { MissingView() }
        }
    }
}

struct MissingView: View {
    var body: some View {
        ContentUnavailableView("Not found", systemImage: "questionmark.folder", description: Text("This course or lesson isn’t installed."))
    }
}

/// Music-style "Now reading" pill above the tab bar.
struct NowReadingAccessory: View {
    @Environment(Library.self) private var library
    let open: (String, String) -> Void

    var body: some View {
        if let now = library.nowReading() {
            let course = now.0, lesson = now.1
            Button { open(course.id, lesson.id) } label: {
                HStack(spacing: 12) {
                    Image(systemName: "book.pages")
                        .font(.body.weight(.semibold))
                    VStack(alignment: .leading, spacing: 1) {
                        Text("\(lesson.number)  \(lesson.title)")
                            .font(.subheadline.weight(.semibold))
                            .lineLimit(1)
                        Text(course.manifest.title)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .lineLimit(1)
                    }
                    Spacer(minLength: 8)
                    Image(systemName: "play.fill")
                        .font(.subheadline)
                }
                .padding(.horizontal, 16)
                .contentShape(.rect)
            }
            .buttonStyle(.plain)
            .accessibilityLabel("Resume Lesson \(lesson.number), \(lesson.title)")
        }
    }
}

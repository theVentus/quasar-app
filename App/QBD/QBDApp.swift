import SwiftUI
import BookKit

@main
struct QBDApp: App {
    @State private var shelf = Bookshelf()
    @State private var highlights = HighlightStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(shelf)
                .environment(highlights)
        }
    }
}

/// Liquid Glass comes from system components: the tab bar (minimises on scroll), toolbars, sheets and the bottom accessory.
/// Pages are never glass.
struct RootView: View {
    @Environment(Bookshelf.self) private var shelf
    @AppStorage("lastItem") private var lastItem = """
    @State private var tab: AppTab = .home
    @State private var homePath: [Route] = []
    @State private var libraryPath: [Route] = []
    @State private var highlightsPath: [Route] = []
    @State private var searchPath: [Route] = []

    /// The app wears the accent of the book you last opened.
    private var accent: CourseAccent {
        if case .book(let id)? = LastItem(LaunchState.lastItem ?? lastItem), let book = shelf.book(id) {
            return CourseAccent(book.manifest.theme)
        }
        return CourseAccent(shelf.books.first?.manifest.theme)
    }

    var body: some View {
        TabView(selection: $tab) {
            Tab("Home", systemImage: "house", value: AppTab.home) {
                NavigationStack(path: $homePath) {
                    HomeView(path: $homePath)
                        .navigationDestination(for: Route.self) { RouteView(route: $0) }
                }
            }
            Tab("Library", systemImage: "books.vertical", value: AppTab.library) {
                NavigationStack(path: $libraryPath) {
                    LibraryView(path: $libraryPath)
                        .navigationDestination(for: Route.self) { RouteView(route: $0) }
                }
            }
            Tab("Highlights", systemImage: "highlighter", value: AppTab.highlights) {
                NavigationStack(path: $highlightsPath) {
                    AllHighlightsView(path: $highlightsPath)
                        .navigationDestination(for: Route.self) { RouteView(route: $0) }
                }
            }
            Tab(value: AppTab.search, role: .search) {
                NavigationStack(path: $searchPath) {
                    SearchView()
                        .navigationDestination(for: Route.self) { RouteView(route: $0) }
                }
            }
        }
        .tabBarMinimizeBehavior(.onScrollDown)
        .tabViewBottomAccessory(isEnabled: showsAccessory) {
            NowReadingAccessory { route in
                tab = .home
                homePath = route
            }
        }
        .environment(\.accent, accent)
        .tint(accent.tint)
        .onAppear(perform: applyLaunchState)
    }

    /// The resume pill lives on tab roots only: not on Home (the landing page is the resume), not inside a course or book.
    private var showsAccessory: Bool {
        switch tab {
        case .home: return false
        case .library: return libraryPath.isEmpty
        case .highlights: return highlightsPath.isEmpty
        case .search: return searchPath.isEmpty
        }
    }

    private func applyLaunchState() {
        LaunchState.signalReadyIfAsked()
        if let t = LaunchState.tab { tab = t }
        if let b = LaunchState.openBook { tab = .home; homePath = [.book(id: b, toc: nil)] }
        if let b = LaunchState.openBookContents { tab = .home; homePath = [.bookContents(b)] }
    }
}

struct RouteView: View {
    @Environment(Bookshelf.self) private var shelf
    let route: Route

    var body: some View {
        switch route {
        case .bookContents(let id):
            if let b = shelf.book(id) { BookContentsView(book: b).environment(\.accent, CourseAccent(b.manifest.theme)) } else { MissingView() }
        case .book(let id, let toc, let hl):
            BookReaderView(bookID: id, startTOC: toc, startHighlight: hl)
                .environment(\.accent, CourseAccent(shelf.book(id)?.manifest.theme))
        }
    }
}

struct MissingView: View {
    var body: some View {
        ContentUnavailableView("Not found", systemImage: "questionmark.folder", description: Text("This book isn’t installed."))
    }
}

/// Music-style "Now reading" pill above the tab bar: the last book opened.
struct NowReadingAccessory: View {
    @Environment(Bookshelf.self) private var shelf
    @AppStorage("lastItem") private var lastItem = ""
    let open: ([Route]) -> Void

    var body: some View {
        if case .book(let id)? = LastItem(LaunchState.lastItem ?? lastItem), let book = shelf.book(id) {
            let p = shelf.progress(book)
            row(icon: "book.closed", title: book.title, subtitle: p > 0 ? "\(Int((p * 100).rounded()))% read" : book.authors.joined(separator: ", "),
                label: "Resume \(book.title)") { open([.book(id: book.id, toc: nil)]) }
        }
    }

    private func row(icon: String, title: String, subtitle: String, label: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: icon).font(.body.weight(.semibold))
                VStack(alignment: .leading, spacing: 1) {
                    Text(title).font(.subheadline.weight(.semibold)).lineLimit(1)
                    Text(subtitle).font(.caption).foregroundStyle(.secondary).lineLimit(1)
                }
                Spacer(minLength: 8)
                Image(systemName: "play.fill").font(.subheadline)
            }
            .padding(.horizontal, 16)
            .contentShape(.rect)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }
}

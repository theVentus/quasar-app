import SwiftUI
import BookKit

/// Home is the landing page of the book you last opened, drawn in its own style.
struct HomeView: View {
    @Environment(Bookshelf.self) private var shelf
    @AppStorage("lastItem") private var lastItem = ""
    @Binding var path: [Route]
    @State private var showSettings = false

    /// The last book opened, else the first on the shelf.
    private var lastBook: Book? {
        if case .book(let id)? = LastItem(LaunchState.lastItem ?? lastItem), let b = shelf.book(id) { return b }
        return shelf.books.first
    }

    var body: some View {
        Group {
            if let book = lastBook {
                BookLanding(book: book, showSettings: $showSettings) { route in
                    path = [route]
                }
                .environment(\.accent, CourseAccent(book.manifest.theme))
            } else if shelf.lockedCount > 0 {
                VStack(spacing: 20) {
                    ContentUnavailableView("Your books are locked", systemImage: "lock",
                                           description: Text("They ship encrypted. Unlock them once with your library passphrase."))
                    LockedBooksCard().padding(.horizontal, 20)
                }
            } else {
                ContentUnavailableView("No books yet", systemImage: "books.vertical",
                                       description: Text("Books arrive with the next build of the app."))
            }
        }
        .toolbar(.hidden, for: .navigationBar)
        .sheet(isPresented: $showSettings) {
            AppSettingsView().presentationDetents([.medium, .large])
        }
        .onAppear { if LaunchState.showAppSettings { showSettings = true } }
    }
}


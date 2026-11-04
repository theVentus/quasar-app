import SwiftUI
import BookKit

/// Every installed book as a poster card.
struct LibraryView: View {
    @Environment(Bookshelf.self) private var shelf
    @Binding var path: [Route]
    @State private var showSettings = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                if shelf.lockedCount > 0 { LockedBooksCard() }
                ForEach(shelf.books) { book in
                    BookPoster(book: book) { route in path = [route] }
                }
                if shelf.books.isEmpty && shelf.lockedCount == 0 {
                    ContentUnavailableView("No books yet", systemImage: "books.vertical",
                                           description: Text("Books arrive with the next build of the app."))
                        .padding(.top, 60)
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


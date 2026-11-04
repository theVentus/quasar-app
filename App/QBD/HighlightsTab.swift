import SwiftUI
import BookKit

/// Every highlight across the library, newest first, grouped by book.
struct AllHighlightsView: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(HighlightStore.self) private var store
    @Binding var path: [Route]

    var body: some View {
        let books = shelf.books.filter { !store.highlights(for: $0.id).isEmpty }
        Group {
            if books.isEmpty {
                ContentUnavailableView("No highlights yet", systemImage: "highlighter",
                                       description: Text("Select text while reading and choose Highlight."))
            } else {
                List {
                    ForEach(books) { book in
                        Section {
                            ForEach(store.highlights(for: book.id)) { h in
                                Button { path = [.book(id: book.id, toc: nil, highlight: h.id)] } label: {
                                    VStack(alignment: .leading, spacing: 6) {
                                        Text(h.text).font(Typeface.serif(16)).foregroundStyle(.primary).lineLimit(5)
                                        if let n = h.note { Text(n).font(.subheadline).foregroundStyle(.secondary) }
                                        Text(h.chapter).font(.caption).foregroundStyle(.tertiary)
                                    }
                                    .padding(.vertical, 4)
                                }
                                .buttonStyle(.plain)
                                .swipeActions { Button(role: .destructive) { store.remove(h.id) } label: { Label("Delete", systemImage: "trash") } }
                            }
                        } header: {
                            Text(book.title).font(Typeface.serif(17, bold: true)).textCase(nil)
                        }
                    }
                }
            }
        }
        .navigationTitle("Highlights")
    }
}

/// Search titles, authors, chapters and your highlights.
struct SearchView: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(HighlightStore.self) private var store
    @State private var query = ""

    var body: some View {
        let q = query.trimmingCharacters(in: .whitespaces)
        List {
            ForEach(shelf.books) { book in
                let matchesBook = q.isEmpty || book.title.localizedCaseInsensitiveContains(q) || book.authors.joined().localizedCaseInsensitiveContains(q)
                let chapters = q.isEmpty ? [] : book.outline.parts.flatMap { p in (p.entry.map { [$0] } ?? []) + p.chapters }
                    .filter { $0.title.localizedCaseInsensitiveContains(q) }
                let hs = q.isEmpty ? [] : store.highlights(for: book.id).filter { $0.text.localizedCaseInsensitiveContains(q) || ($0.note ?? "").localizedCaseInsensitiveContains(q) }
                if matchesBook || !chapters.isEmpty || !hs.isEmpty {
                    Section(book.title) {
                        if matchesBook {
                            NavigationLink(value: Route.bookContents(book.id)) {
                                Label(book.authors.joined(separator: ", "), systemImage: "book.closed")
                            }
                        }
                        ForEach(chapters) { ch in
                            NavigationLink(value: Route.book(id: book.id, toc: ch.id)) {
                                HStack(alignment: .firstTextBaseline) {
                                    Text(ch.number ?? "").monospacedDigit().foregroundStyle(.secondary).frame(width: 36, alignment: .leading)
                                    Text(ch.title).font(Typeface.serif(17))
                                }
                            }
                        }
                        ForEach(hs) { h in
                            NavigationLink(value: Route.book(id: book.id, toc: nil, highlight: h.id)) {
                                Text(h.text).font(Typeface.serif(15)).lineLimit(3)
                            }
                        }
                    }
                }
            }
        }
        .overlay {
            if !q.isEmpty && shelf.books.isEmpty { ContentUnavailableView.search(text: q) }
        }
        .searchable(text: $query, prompt: "Books, chapters, highlights")
        .navigationTitle("Search")
    }
}

import SwiftUI
import BookKit

/// Names met so far, grouped by the chapter where each first appeared. Nothing from beyond the current page.
struct WhosWhoSheet: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(\.accent) private var accent
    @Environment(\.dismiss) private var dismiss
    let book: Book
    let spine: Int
    @State private var query = ""

    var body: some View {
        let index = shelf.names(for: book)
        let known = index.known(upTo: spine).filter { query.isEmpty || $0.name.localizedCaseInsensitiveContains(query) }
        let chapters = known.reduce(into: [(String, [NameIndex.Entry])]()) { acc, e in
            let ch = chapterTitle(spine: e.firstSpine)
            if let i = acc.firstIndex(where: { $0.0 == ch }) { acc[i].1.append(e) } else { acc.append((ch, [e])) }
        }
        NavigationStack {
            Group {
                if known.isEmpty {
                    ContentUnavailableView("No one yet", systemImage: "person.2", description: Text("Names appear here as you meet them."))
                } else {
                    List {
                        ForEach(chapters, id: \.0) { ch, entries in
                            Section {
                                ForEach(entries) { e in
                                    VStack(alignment: .leading, spacing: 4) {
                                        HStack(alignment: .firstTextBaseline) {
                                            Text(e.name).font(Typeface.serif(18))
                                            Spacer()
                                            Text(e.count > 1 ? "×\(e.count)" : "").font(.caption).monospacedDigit().foregroundStyle(.tertiary)
                                        }
                                        Text(e.firstSentence)
                                            .font(.subheadline)
                                            .foregroundStyle(.secondary)
                                            .lineLimit(3)
                                    }
                                    .padding(.vertical, 2)
                                }
                            } header: {
                                Text("First met in \(ch)")
                            }
                        }
                    }
                }
            }
            .searchable(text: $query, prompt: "Names")
            .navigationTitle("Who’s who")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
    }

    private func chapterTitle(spine: Int) -> String {
        guard let e = book.package.tocEntry(spine: spine), let ch = book.outline.chapter(forTOC: e.id) else { return "the opening" }
        return [ch.number, ch.title].compactMap { $0 }.joined(separator: " ")
    }
}

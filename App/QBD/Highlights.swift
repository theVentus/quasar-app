import SwiftUI
import Observation
import BookKit

/// A passage the reader marked. Located by spine document plus the passage text itself, which is re-found on load.
struct Highlight: Codable, Identifiable, Hashable {
    var id = UUID()
    var book: String
    var spine: Int
    var text: String
    var chapter: String
    var note: String?
    var created = Date()
}

@Observable
final class HighlightStore {
    private(set) var all: [Highlight] = []
    private let url = Bookshelf.root.appendingPathComponent("_highlights.json")

    init() {
        if let data = try? Data(contentsOf: url), let saved = try? JSONDecoder().decode([Highlight].self, from: data) { all = saved }
        // CI screenshots: two highlights in the sample book (its own original text).
        if LaunchState.seedHighlights, !all.contains(where: { $0.book == "field-guide" }) {
            all += [
                Highlight(book: "field-guide", spine: 2, text: "Light is the most patient messenger in the universe.", chapter: "1  The Patient Messenger"),
                Highlight(book: "field-guide", spine: 3, text: "Neither clock is broken. Each keeps perfect time where it is; the disagreement is a property of the space between them.",
                          chapter: "2  Clocks That Disagree", note: "Relativity in one line."),
            ]
        }
    }

    func highlights(for book: String) -> [Highlight] { all.filter { $0.book == book }.sorted { $0.created > $1.created } }
    func highlights(for book: String, spine: Int) -> [Highlight] { all.filter { $0.book == book && $0.spine == spine } }

    func add(_ h: Highlight) { all.append(h); save() }
    func remove(_ id: UUID) { all.removeAll { $0.id == id }; save() }
    func setNote(_ note: String?, for id: UUID) {
        guard let i = all.firstIndex(where: { $0.id == id }) else { return }
        all[i].note = note?.isEmpty == true ? nil : note
        save()
    }

    private func save() {
        try? FileManager.default.createDirectory(at: Bookshelf.root, withIntermediateDirectories: true)
        try? JSONEncoder().encode(all).write(to: url, options: .atomic)
    }

    /// Markdown export, grouped by chapter in reading order.
    func markdown(for book: Book) -> String {
        let hs = all.filter { $0.book == book.id }.sorted { ($0.spine, $0.created) < ($1.spine, $1.created) }
        var out = "# \(book.title)\n\n"
        var chapter = ""
        for h in hs {
            if h.chapter != chapter { chapter = h.chapter; out += "\n## \(chapter)\n\n" }
            out += "> \(h.text.replacingOccurrences(of: "\n", with: " "))\n\n"
            if let n = h.note { out += "\(n)\n\n" }
        }
        return out
    }
}

/// On the landing page: the last three highlights, newest first. Absent until the reader has marked something.
struct HighlightsSection: View {
    @Environment(HighlightStore.self) private var store
    @Environment(\.accent) private var accent
    let book: Book
    let open: (Route) -> Void
    @State private var showAll = false

    var body: some View {
        let hs = store.highlights(for: book.id)
        if !hs.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .firstTextBaseline) {
                    Text("YOUR HIGHLIGHTS")
                        .font(.caption.weight(.semibold))
                        .tracking(1.6)
                        .foregroundStyle(.primary.opacity(0.6))
                    Spacer()
                    Button("All \(hs.count)") { showAll = true }
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.primary.opacity(0.8))
                        .buttonStyle(.plain)
                }
                ForEach(hs.prefix(3)) { h in
                    Button { open(.book(id: book.id, toc: nil, highlight: h.id)) } label: {
                        HighlightCard(highlight: h)
                    }
                    .buttonStyle(.plain)
                }
            }
            .sheet(isPresented: $showAll) { HighlightsList(book: book, open: open).presentationDetents([.large]) }
        }
    }
}

struct HighlightCard: View {
    @Environment(\.accent) private var accent
    let highlight: Highlight

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(highlight.text)
                .font(Typeface.serif(16))
                .foregroundStyle(.primary.opacity(0.92))
                .lineLimit(4)
                .fixedSize(horizontal: false, vertical: true)
            if let n = highlight.note {
                Text(n).font(.subheadline).foregroundStyle(.primary.opacity(0.7)).lineLimit(2)
            }
            Text(highlight.chapter.uppercased())
                .font(.caption2.weight(.semibold))
                .tracking(1.2)
                .foregroundStyle(.primary.opacity(0.5))
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(alignment: .leading) { Rectangle().fill(accent.pastel).frame(width: 3) }
        .background(.primary.opacity(0.06), in: .rect(cornerRadius: 14))
        .clipShape(.rect(cornerRadius: 14))
        .accessibilityElement(children: .combine)
    }
}

/// Every highlight in a book, by chapter, with notes editable and Markdown export.
struct HighlightsList: View {
    @Environment(HighlightStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    let book: Book
    let open: (Route) -> Void

    var body: some View {
        let hs = store.highlights(for: book.id).sorted { ($0.spine, $0.created) < ($1.spine, $1.created) }
        let chapters = hs.reduce(into: [String]()) { if !$0.contains($1.chapter) { $0.append($1.chapter) } }
        NavigationStack {
            List {
                ForEach(chapters, id: \.self) { ch in
                    Section(ch) {
                        ForEach(hs.filter { $0.chapter == ch }) { h in
                            VStack(alignment: .leading, spacing: 6) {
                                Text(h.text).font(Typeface.serif(16))
                                NoteField(highlight: h)
                            }
                            .padding(.vertical, 4)
                            .swipeActions {
                                Button(role: .destructive) { store.remove(h.id) } label: { Label("Delete", systemImage: "trash") }
                                Button { dismiss(); open(.book(id: book.id, toc: nil, highlight: h.id)) } label: { Label("Open", systemImage: "book") }
                                    .tint(.accentColor)
                            }
                        }
                    }
                }
            }
            .navigationTitle("Highlights")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    ShareLink(item: store.markdown(for: book), preview: SharePreview("\(book.title) highlights")) { Image(systemName: "square.and.arrow.up") }
                }
                ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } }
            }
        }
    }
}

struct NoteField: View {
    @Environment(HighlightStore.self) private var store
    let highlight: Highlight
    @State private var note = ""

    var body: some View {
        TextField("Add a note", text: $note, axis: .vertical)
            .font(.subheadline)
            .onAppear { note = highlight.note ?? "" }
            .onSubmit { store.setNote(note, for: highlight.id) }
            .onChange(of: note) { _, n in store.setNote(n, for: highlight.id) }
    }
}

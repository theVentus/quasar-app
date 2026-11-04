import SwiftUI
import BookKit

/// A small emblem for an entity: initials on a disc tinted by kind, ringed in the storyline colour.
struct Sigil: View {
    let name: String
    let kind: String
    var size: CGFloat = 36

    private var initials: String {
        let words = name.split(separator: " ").filter { $0.first?.isUppercase == true }
        let letters = words.prefix(2).compactMap(\.first)
        return letters.isEmpty ? String(name.prefix(1)).uppercased() : String(letters)
    }

    static func hue(_ kind: String) -> Color {
        switch kind {
        case "character": Color(hex: 0xC9B8E8)
        case "group": Color(hex: 0xBCDDBE)
        case "place": Color(hex: 0xF2D4A7)
        case "ship": Color(hex: 0xA9C4F5)
        case "technology": Color(hex: 0xB9E2E6)
        default: Color(hex: 0xE6C9C2)
        }
    }

    var body: some View {
        Text(initials)
            .font(Typeface.serif(size * 0.42, bold: true))
            .foregroundStyle(Color(hex: 0x1D1B22))
            .frame(width: size, height: size)
            .background(Self.hue(kind).gradient, in: .circle)
            .overlay { Circle().strokeBorder(.white.opacity(0.35), lineWidth: 0.6) }
            .accessibilityHidden(true)
    }
}

/// X-Ray: who and what the reader has met, as of the page they're on. Nothing past it.
struct XRaySheet: View {
    @Environment(\.dismiss) private var dismiss
    let index: CompanionIndex
    let spine: Int
    var focus: String? = nil
    @State private var query = ""
    @State private var selected: Companion.Entity?

    private static let order = ["character", "group", "ship", "place", "technology", "term"]
    private static let titles = ["character": "People", "group": "Peoples and factions", "ship": "Ships", "place": "Places",
                                 "technology": "Technology", "term": "Terms"]

    var body: some View {
        let known = index.known(at: spine)
            .filter { query.isEmpty || $0.entity.name.localizedCaseInsensitiveContains(query) || ($0.entity.aliases ?? []).contains { $0.localizedCaseInsensitiveContains(query) } }
        let here = Set(index.present(at: spine))
        NavigationStack {
            Group {
                if known.isEmpty {
                    ContentUnavailableView("No one yet", systemImage: "person.2", description: Text("People, places and terms appear here as you meet them."))
                } else {
                    List {
                        let inChapter = known.filter { here.contains($0.entity.id) }
                        if !inChapter.isEmpty && query.isEmpty {
                            Section("In this chapter") { ForEach(inChapter, id: \.entity.id) { row($0.entity, $0.text) } }
                        }
                        ForEach(Self.order, id: \.self) { kind in
                            let items = known.filter { $0.entity.kind == kind && (query.isEmpty ? !here.contains($0.entity.id) : true) }
                            if !items.isEmpty {
                                Section(Self.titles[kind] ?? kind.capitalized) { ForEach(items, id: \.entity.id) { row($0.entity, $0.text) } }
                            }
                        }
                    }
                }
            }
            .searchable(text: $query, prompt: "Names and terms")
            .navigationTitle("X-Ray")
            .navigationBarTitleDisplayMode(.inline)
            .navigationDestination(item: $selected) { EntityDetail(index: index, entity: $0, spine: spine) }
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
            .onAppear {
                if let f = focus, let e = index.companion.entities.first(where: { $0.id == f }) { selected = e }
            }
        }
    }

    private func row(_ e: Companion.Entity, _ text: String) -> some View {
        Button { selected = e } label: {
            HStack(alignment: .top, spacing: 12) {
                Sigil(name: e.name, kind: e.kind)
                VStack(alignment: .leading, spacing: 3) {
                    Text(e.name).font(Typeface.serif(18)).foregroundStyle(.primary)
                    Text(text).font(.subheadline).foregroundStyle(.secondary).lineLimit(3)
                }
            }
            .padding(.vertical, 2)
        }
        .buttonStyle(.plain)
    }
}

/// One entity: what's known now, how that understanding grew, and where they've appeared so far.
struct EntityDetail: View {
    @Environment(\.accent) private var accent
    let index: CompanionIndex
    let entity: Companion.Entity
    let spine: Int

    var body: some View {
        let seen = index.appearances(of: entity.id, through: spine)
        let states = index.visibleStates(of: entity, at: spine)
        List {
            Section {
                HStack(spacing: 14) {
                    Sigil(name: entity.name, kind: entity.kind, size: 56)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(entity.name).font(Typeface.serif(24))
                        if let a = entity.aliases, !a.isEmpty {
                            Text("Also " + a.joined(separator: ", ")).font(.footnote).foregroundStyle(.secondary)
                        }
                    }
                }
                .listRowBackground(Color.clear)
                if let now = index.description(of: entity, at: spine) {
                    Text(now).font(Typeface.serif(17))
                }
            }
            if states.count > 1 {
                Section("How you came to know them") {
                    ForEach(Array(states.enumerated()), id: \.offset) { _, s in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(index.companion.chapters.first { $0.href == s.href }?.title ?? "").font(.caption).foregroundStyle(.tertiary)
                            Text(s.text).font(.subheadline)
                        }
                    }
                }
            }
            if !seen.isEmpty {
                Section("Appears in") {
                    ForEach(Array(seen.enumerated()), id: \.offset) { _, c in
                        HStack {
                            Circle().fill(Color(hex: UInt32(c.palette.first.flatMap { UInt32($0.dropFirst(), radix: 16) } ?? 0x888888))).frame(width: 8, height: 8)
                            Text(c.title).font(Typeface.serif(16))
                            Spacer()
                            Text(index.companion.storylines[c.storyline] ?? "").font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
        .navigationTitle(entity.name)
        .navigationBarTitleDisplayMode(.inline)
    }
}

/// The card shown when a name is tapped in the text.
struct EntityCard: View {
    let index: CompanionIndex
    let entity: Companion.Entity
    let spine: Int
    let more: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(spacing: 12) {
                Sigil(name: entity.name, kind: entity.kind, size: 44)
                VStack(alignment: .leading, spacing: 2) {
                    Text(entity.name).font(Typeface.serif(21))
                    Text(entity.kind.capitalized).font(.caption.weight(.semibold)).foregroundStyle(.secondary)
                }
                Spacer()
            }
            Text(index.description(of: entity, at: spine) ?? "").font(Typeface.serif(17)).fixedSize(horizontal: false, vertical: true)
            let seen = index.appearances(of: entity.id, through: spine).count
            HStack {
                Text(seen == 1 ? "First met in this chapter" : "In \(seen) chapters so far").font(.footnote).foregroundStyle(.secondary)
                Spacer()
                Button("More", action: more).font(.footnote.weight(.semibold))
            }
        }
        .padding(20)
        .presentationDetents([.height(240), .medium])
        .presentationBackground(.regularMaterial)
    }
}

/// "Previously": the last finished chapter's recap, shown when returning after a break.
struct PreviouslyCard: View {
    let chapter: Companion.Chapter
    let dismiss: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("PREVIOUSLY").font(.caption.weight(.semibold)).tracking(1.6).foregroundStyle(.secondary)
                Spacer()
                Button(action: dismiss) { Image(systemName: "xmark").font(.caption.weight(.bold)) }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Dismiss")
            }
            Text(chapter.title).font(Typeface.serif(18, bold: true))
            Text(chapter.recap).font(Typeface.serif(16)).fixedSize(horizontal: false, vertical: true)
        }
        .padding(18)
        .frame(maxWidth: .infinity, alignment: .leading)
        .glassEffect(.regular, in: .rect(cornerRadius: 26))
        .onTapGesture(perform: dismiss)
        .task { try? await Task.sleep(for: .seconds(12)); dismiss() }
    }
}

import Foundation

/// `companion.json`, schema `qbd.companion/1`: a reading companion written once per book and frozen.
/// Every item is keyed to the chapter where it becomes known, so the app can show only what the reader has reached.
public struct Companion: Codable, Sendable, Hashable {
    public struct Chapter: Codable, Sendable, Hashable {
        public var href: String
        public var title: String
        public var storyline: String
        public var setting: String
        public var era: String?
        public var mood: String
        public var palette: [String]
        public var imagery: [String]
        public var teaser: String
        public var recap: String
        public var people: [String]
    }

    public struct State: Codable, Sendable, Hashable {
        public var href: String
        /// `intro`: what the reader learns on first meeting; `end`: what is known by the end of that chapter.
        public var at: String
        public var text: String
    }

    public struct Entity: Codable, Sendable, Hashable, Identifiable {
        public var id: String
        public var name: String
        public var kind: String
        public var aliases: [String]?
        public var states: [State]
    }

    public struct Annotation: Codable, Sendable, Hashable {
        public var href: String
        public var anchor: String
        public var kind: String
        public var note: String
    }

    public var schema: String
    public var storylines: [String: String]
    public var chapters: [Chapter]
    public var entities: [Entity]
    public var annotations: [Annotation]

    public static func load(_ url: URL) -> Companion? {
        guard let data = try? Data(contentsOf: url) else { return nil }
        return try? JSONDecoder().decode(Companion.self, from: data)
    }
}

/// A companion resolved against a book's reading order: hrefs become spine indices.
public struct CompanionIndex: Sendable {
    public let companion: Companion
    private let chapterBySpine: [Int: Companion.Chapter]
    private let spineOf: [String: Int]

    public init(_ companion: Companion, package: BookPackage) {
        self.companion = companion
        let base = package.opfURL.deletingLastPathComponent()
        var map: [String: Int] = [:]
        for href in Set(companion.chapters.map(\.href) + companion.entities.flatMap { $0.states.map(\.href) } + companion.annotations.map(\.href)) {
            if let i = package.spineIndex(of: BookPackage.resolve(href, against: base)) { map[href] = i }
        }
        spineOf = map
        var bySpine: [Int: Companion.Chapter] = [:]
        for c in companion.chapters { if let i = map[c.href] { bySpine[i] = c } }
        chapterBySpine = bySpine
    }

    public func spine(of href: String) -> Int? { spineOf[href] }

    /// The companion chapter for a spine document, or the nearest earlier one (split files share a chapter).
    public func chapter(atSpine i: Int) -> Companion.Chapter? {
        if let c = chapterBySpine[i] { return c }
        return chapterBySpine.filter { $0.key <= i }.max { $0.key < $1.key }?.value
    }

    /// Whether a state is visible to a reader at spine `i`: anything from earlier chapters, and intro lines of this one.
    func visible(_ s: Companion.State, at i: Int) -> Bool {
        guard let si = spineOf[s.href] else { return false }
        let current = chapterStart(i)
        return si < current || (si == current && s.at == "intro")
    }

    /// Spine index where the chapter containing `i` starts.
    private func chapterStart(_ i: Int) -> Int {
        chapterBySpine.keys.filter { $0 <= i }.max() ?? i
    }

    /// The states of an entity the reader may see at spine `i`, in story order.
    public func visibleStates(of e: Companion.Entity, at i: Int) -> [Companion.State] {
        e.states.filter { visible($0, at: i) }
    }

    /// The latest visible description of an entity at spine `i`, or nil if the reader hasn't met it.
    public func description(of e: Companion.Entity, at i: Int) -> String? {
        e.states.filter { visible($0, at: i) }.max { (spineOf[$0.href] ?? 0, $0.at == "end" ? 1 : 0) < (spineOf[$1.href] ?? 0, $1.at == "end" ? 1 : 0) }?.text
    }

    /// Entities the reader has met by spine `i`, with their current descriptions.
    public func known(at i: Int) -> [(entity: Companion.Entity, text: String)] {
        companion.entities.compactMap { e in description(of: e, at: i).map { (e, $0) } }
    }

    /// Ids of entities present in the chapter at spine `i` (only those already met).
    public func present(at i: Int) -> [String] {
        guard let c = chapter(atSpine: i) else { return [] }
        let met = Set(known(at: i).map(\.entity.id))
        return c.people.filter { met.contains($0) }
    }

    /// Chapters (spine starts) up to and including the one at `i`, in reading order.
    public func chaptersRead(through i: Int) -> [Companion.Chapter] {
        let start = chapterStart(i)
        return chapterBySpine.filter { $0.key <= start }.sorted { $0.key < $1.key }.map(\.value)
    }

    /// Chapters where an entity appears, up to the reader's position.
    public func appearances(of id: String, through i: Int) -> [Companion.Chapter] {
        chaptersRead(through: i).filter { $0.people.contains(id) }
    }

    public func annotations(atSpine i: Int) -> [Companion.Annotation] {
        companion.annotations.filter { spineOf[$0.href] == i }
    }

    /// Recap of the chapter before the one at spine `i` (for "previously" on return).
    public func previousRecap(before i: Int) -> Companion.Chapter? {
        let start = chapterStart(i)
        return chapterBySpine.filter { $0.key < start }.max { $0.key < $1.key }?.value
    }

    /// Aliases → entity id for names the reader has met, longest first so "Doctor Kern" wins over "Kern".
    public func nameMap(at i: Int) -> [(String, String)] {
        // A name shared by several entities (a namesake in a later era) points at the most recently introduced one.
        var best: [String: (id: String, since: Int)] = [:]
        for (e, _) in known(at: i) where e.kind == "character" || e.kind == "group" || e.kind == "ship" || e.kind == "place" {
            let since = e.states.compactMap { spineOf[$0.href] }.min() ?? 0
            for n in Set([e.name] + (e.aliases ?? [])) where n.count >= 3 && !n.contains("(") {
                if let b = best[n], b.since > since { continue }
                best[n] = (e.id, since)
            }
        }
        return best.map { ($0.key, $0.value.id) }.sorted { $0.0.count > $1.0.count }
    }
}

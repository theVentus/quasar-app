import Foundation

/// Parts and chapters for a book's contents page, inferred from the EPUB contents.
/// Nested contents use their levels; flat contents numbered "1", "1.1", "1.2", "2" … are grouped by number.
public struct BookOutline: Sendable, Hashable {
    public struct Chapter: Sendable, Hashable, Identifiable {
        public var id: Int            // TOC entry id
        public var number: String?
        public var title: String
        public var spineIndex: Int?
        public var fragment: String?
    }

    public struct Part: Sendable, Hashable, Identifiable {
        public var id: Int
        public var number: String?
        public var title: String
        /// The part's own contents entry (its opening page), if it has one.
        public var entry: Chapter?
        public var chapters: [Chapter]
    }

    public let parts: [Part]

    public var chapterCount: Int { parts.reduce(0) { $0 + max($1.chapters.count, $1.entry == nil ? 0 : ($1.chapters.isEmpty ? 1 : 0)) } }
    /// True when the book has real parts (more than one group, or a named group).
    public var hasParts: Bool { parts.count > 1 || parts.first?.title.isEmpty == false }

    public func chapter(forTOC id: Int) -> Chapter? {
        for p in parts {
            if p.entry?.id == id { return p.entry }
            if let c = p.chapters.first(where: { $0.id == id }) { return c }
        }
        return nil
    }

    public func part(containingTOC id: Int) -> Part? {
        parts.first { $0.entry?.id == id || $0.chapters.contains { $0.id == id } }
    }

    public init(toc: [BookPackage.TOCEntry], inferNumbering: Bool = true, titleCase: Bool = true) {
        func chapter(_ e: BookPackage.TOCEntry) -> Chapter {
            let (num, rest) = Self.splitNumber(e.title)
            let title = titleCase ? Self.titleCased(rest) : rest
            return Chapter(id: e.id, number: num, title: title.isEmpty ? e.title : title, spineIndex: e.spineIndex, fragment: e.fragment)
        }

        var parts: [Part] = []
        let nested = toc.contains { $0.level > 1 }
        let numbered = inferNumbering && toc.filter { Self.splitNumber($0.title).0 != nil }.count >= max(2, toc.count / 2)

        if nested {
            for e in toc {
                if e.level == 1 {
                    let c = chapter(e)
                    parts.append(Part(id: parts.count, number: c.number, title: c.title, entry: c, chapters: []))
                } else if !parts.isEmpty {
                    parts[parts.count - 1].chapters.append(chapter(e))
                }
            }
            // Top-level entries without children are chapters of an unnamed group.
            if parts.allSatisfy({ $0.chapters.isEmpty }) {
                parts = [Part(id: 0, number: nil, title: "", entry: nil, chapters: parts.compactMap(\.entry))]
            }
        } else if numbered {
            for e in toc {
                let c = chapter(e)
                let depth = c.number?.split(separator: ".").count ?? 0
                if depth == 1 {
                    parts.append(Part(id: parts.count, number: c.number, title: c.title, entry: c, chapters: []))
                } else if parts.isEmpty {
                    parts.append(Part(id: 0, number: nil, title: "", entry: nil, chapters: [c]))
                } else {
                    parts[parts.count - 1].chapters.append(c)
                }
            }
        } else {
            parts = [Part(id: 0, number: nil, title: "", entry: nil, chapters: toc.map(chapter))]
        }
        self.parts = parts
    }

    /// "1.2 BRAVE NEW WORDS" → ("1.2", "BRAVE NEW WORDS"); "Prologue" → (nil, "Prologue").
    static func splitNumber(_ s: String) -> (String?, String) {
        let t = s.trimmingCharacters(in: .whitespaces)
        var digits = ""
        var idx = t.startIndex
        while idx < t.endIndex, t[idx].isNumber || (t[idx] == "." && !digits.isEmpty) {
            digits.append(t[idx]); idx = t.index(after: idx)
        }
        if digits.hasSuffix(".") { digits.removeLast() }
        guard !digits.isEmpty, idx == t.endIndex || t[idx].isWhitespace || t[idx] == "." else { return (nil, t) }
        let rest = t[idx...].trimmingCharacters(in: CharacterSet.whitespaces.union(CharacterSet(charactersIn: ".:–—-")))
        return (digits, rest)
    }

    private static let small: Set<String> = ["a", "an", "and", "as", "at", "but", "by", "for", "from", "in", "into", "nor", "of", "on", "or", "the", "to", "with"]

    /// Title-cases text only when it is shouted in capitals; mixed-case titles are left as published.
    static func titleCased(_ s: String) -> String {
        let letters = s.unicodeScalars.filter { CharacterSet.letters.contains($0) }
        guard !letters.isEmpty, letters.allSatisfy({ CharacterSet.uppercaseLetters.contains($0) }) else { return s }
        var words = s.lowercased().split(separator: " ", omittingEmptySubsequences: false).map(String.init)
        for i in words.indices where !words[i].isEmpty {
            let w = words[i]
            let isEdge = i == 0 || i == words.count - 1 || words[i - 1].hasSuffix(":") || words[i - 1] == "/"
            if isEdge || !small.contains(w) { words[i] = w.prefix(1).uppercased() + w.dropFirst() }
        }
        return words.joined(separator: " ")
    }
}

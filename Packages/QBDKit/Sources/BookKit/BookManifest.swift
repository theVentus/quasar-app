import Foundation

/// `book.json`, schema `qbd.book/1`: what turns an EPUB into a book that lives in the app like a course.
/// It sits beside `book.epub` in a book package. Text of the book itself never goes in here.
public struct BookManifest: Codable, Hashable, Sendable {
    public var schema: String
    public var id: String
    /// Display overrides; the EPUB's own metadata fills anything left out.
    public var title: String?
    public var subtitle: String?
    public var authors: [String]?
    public var series: String?
    public var theme: Theme?
    public var contents: Contents?
    /// Href (relative to the OPF) of the first page a new reader should land on, skipping front matter.
    public var startAt: String?
    /// Back-cover material: the publisher's description, press quotes, an award line.
    public var about: String?
    public var praise: [Praise]?
    public var awards: String?
    /// One scene per part for a progressive landing backdrop; the backdrop advances as the reader does.
    public var scenes: [Scene]?

    public struct Praise: Codable, Hashable, Sendable {
        public var quote: String
        public var source: String
    }

    /// Dimensionless 0…1 dials a bespoke backdrop reads; unknown keys are ignored by backdrops that don't use them.
    public struct Scene: Codable, Hashable, Sendable {
        public var web: Double?
        public var ship: Double?
        public var pod: Bool?
        public var spider: Bool?
        public var signal: Double?
        public var orbit: Bool?
    }

    public struct Theme: Codable, Hashable, Sendable {
        public var accent: String
        public var accentDeep: String
        public var onAccent: String?
        /// Landing backdrop: `cover` (any book), or a bespoke one such as `web` or `sky`.
        public var landing: String?
    }

    public struct Contents: Codable, Hashable, Sendable {
        /// `outline`: infer parts and chapters from "1", "1.1" numbering in a flat contents list.
        public var style: String?
        /// Convert ALL-CAPS contents titles to title case for display.
        public var titleCase: Bool?
    }

    public init(schema: String = "qbd.book/1", id: String, title: String? = nil, subtitle: String? = nil, authors: [String]? = nil,
                series: String? = nil, theme: Theme? = nil, contents: Contents? = nil, startAt: String? = nil) {
        self.schema = schema; self.id = id; self.title = title; self.subtitle = subtitle; self.authors = authors
        self.series = series; self.theme = theme; self.contents = contents; self.startAt = startAt
    }

    /// The scene for a part index, interpolating toward the next part by `fraction` through it.
    public func scene(part: Int, fraction: Double) -> (Scene, Scene, Double)? {
        guard let scenes, !scenes.isEmpty else { return nil }
        let i = min(max(0, part), scenes.count - 1)
        let j = min(i + 1, scenes.count - 1)
        return (scenes[i], scenes[j], min(1, max(0, fraction)))
    }
}

/// A book package directory: `book.json` + `book.epub`, unpacked into `epub/` on install.
public struct Book: Sendable, Identifiable {
    public var id: String { manifest.id }
    public let manifest: BookManifest
    public let package: BookPackage
    public let outline: BookOutline
    /// Approximate word count of the reading order, measured at install.
    public let words: Int

    public init(manifest: BookManifest, package: BookPackage, words: Int) {
        self.manifest = manifest
        self.package = package
        self.words = words
        self.outline = BookOutline(toc: package.toc, inferNumbering: manifest.contents?.style != "flat",
                                   titleCase: manifest.contents?.titleCase ?? true)
    }

    public var title: String { manifest.title ?? package.metadata.title }
    public var authors: [String] { manifest.authors ?? package.metadata.authors }
    public var readingHours: Double { Double(words) / 250 / 60 }

    /// Where a new reader starts: `startAt` if set, else the first contents entry, else the first spine document.
    public var startSpineIndex: Int {
        if let s = manifest.startAt, let i = package.spineIndex(of: BookPackage.resolve(s, against: package.opfURL.deletingLastPathComponent())) { return i }
        return package.toc.first?.spineIndex ?? 0
    }

    /// Whole-book progress at which part `index` begins and ends.
    public func partRange(_ index: Int) -> (start: Double, end: Double) {
        let parts = outline.parts
        guard parts.indices.contains(index) else { return (0, 0) }
        func first(_ p: BookOutline.Part) -> Int? { p.entry?.spineIndex ?? p.chapters.first?.spineIndex }
        let start = first(parts[index]) ?? 0
        let end = (index + 1 < parts.count ? first(parts[index + 1]) : nil) ?? package.spine.count
        return (package.progress(spine: start, fraction: 0), package.progress(spine: end, fraction: 0))
    }

    /// 0…1 through part `index` for a whole-book progress value.
    public func progress(inPart index: Int, bookProgress p: Double) -> Double {
        let r = partRange(index)
        guard r.end > r.start else { return p >= r.end ? 1 : 0 }
        return min(1, max(0, (p - r.start) / (r.end - r.start)))
    }

    /// Counts words across the spine documents by stripping markup. Cheap enough to run at install.
    public static func countWords(_ package: BookPackage) -> Int {
        var total = 0
        for item in package.spine {
            guard let data = try? Data(contentsOf: item.url), let s = String(data: data, encoding: .utf8) else { continue }
            var inTag = false, inWord = false
            for ch in s.unicodeScalars {
                if ch == "<" { inTag = true; inWord = false; continue }
                if ch == ">" { inTag = false; continue }
                if inTag { continue }
                let letter = CharacterSet.alphanumerics.contains(ch)
                if letter && !inWord { total += 1 }
                inWord = letter || (inWord && (ch == "'" || ch == "’" || ch == "-"))
            }
        }
        return total
    }
}

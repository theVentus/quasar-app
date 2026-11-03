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

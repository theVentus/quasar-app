import Foundation
import ZIPFoundation

/// An unpacked EPUB (2 or 3): metadata, reading order, contents and cover.
public struct BookPackage: Sendable {
    public struct Metadata: Sendable, Hashable, Codable {
        public var title: String
        public var authors: [String]
        public var language: String?
        public var publisher: String?
        public var identifier: String?
        public var series: String?
        public var seriesIndex: String?
    }

    public struct SpineItem: Sendable, Hashable {
        public var id: String
        public var url: URL
        public var mediaType: String
        public var linear: Bool
    }

    public struct TOCEntry: Sendable, Hashable, Identifiable {
        public var id: Int
        public var title: String
        public var url: URL
        public var fragment: String?
        public var level: Int
        /// Index into `spine` of the document this entry points into, if any.
        public var spineIndex: Int?
    }

    public enum PackageError: Error, CustomStringConvertible {
        case noRootfile, emptySpine, encrypted

        public var description: String {
            switch self {
            case .noRootfile: return "This file has no EPUB package document."
            case .emptySpine: return "This book has no readable chapters."
            case .encrypted: return "This book is protected by DRM and can’t be opened."
            }
        }
    }

    public let root: URL
    public let opfURL: URL
    public let version: String
    public let metadata: Metadata
    public let spine: [SpineItem]
    public let toc: [TOCEntry]
    public let coverURL: URL?
    /// File size of each spine document, the basis for whole-book progress.
    public let spineWeights: [Double]

    /// Unzips `epub` into `directory` (created if needed) and parses it.
    public static func unpack(epub: URL, to directory: URL) throws -> BookPackage {
        let fm = FileManager.default
        try? fm.removeItem(at: directory)
        try fm.createDirectory(at: directory, withIntermediateDirectories: true)
        try fm.unzipItem(at: epub, to: directory)
        return try BookPackage(root: directory)
    }

    /// Unzips any archive (used for sealed book packages).
    public static func extract(zip: URL, to directory: URL) throws {
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try FileManager.default.unzipItem(at: zip, to: directory)
    }

    public init(root: URL) throws {
        let root = root.standardizedFileURL
        self.root = root
        let fm = FileManager.default

        // Font obfuscation is fine (we use our own fonts); anything else in encryption.xml means DRM.
        let enc = root.appendingPathComponent("META-INF/encryption.xml")
        if fm.fileExists(atPath: enc.path), let tree = try? XMLTree.parse(contentsOf: enc) {
            let algorithms = tree.all("EncryptionMethod").compactMap { $0["Algorithm"] }
            if algorithms.contains(where: { !$0.contains("obfuscation") && !$0.contains("idpf.org/2008/embedding") }) {
                throw PackageError.encrypted
            }
        }

        let container = try XMLTree.parse(contentsOf: root.appendingPathComponent("META-INF/container.xml"))
        guard let path = container.first("rootfile")?["full-path"] else { throw PackageError.noRootfile }
        let opfURL = Self.resolve(path, against: root)
        self.opfURL = opfURL
        let opfDir = opfURL.deletingLastPathComponent()

        let pkg = try XMLTree.parse(contentsOf: opfURL)
        version = pkg["version"] ?? "2.0"
        let meta = pkg.first("metadata")

        // Metadata
        let uniqueID = pkg["unique-identifier"]
        let identifiers = meta?.all("identifier") ?? []
        let metas = meta?.all("meta") ?? []
        func metaContent(_ name: String) -> String? { metas.first { $0["name"] == name }?["content"] }
        func metaProperty(_ property: String) -> String? { metas.first { $0["property"] == property }?.text.nonEmpty }
        metadata = Metadata(
            title: meta?.first("title")?.text.nonEmpty ?? opfURL.deletingPathExtension().lastPathComponent,
            authors: (meta?.all("creator") ?? []).filter { ($0["role"] ?? "aut") == "aut" }.compactMap { $0.text.nonEmpty },
            language: meta?.first("language")?.text.nonEmpty,
            publisher: meta?.first("publisher")?.text.nonEmpty,
            identifier: (identifiers.first { $0["id"] == uniqueID } ?? identifiers.first)?.text.nonEmpty,
            series: metaContent("calibre:series") ?? metaProperty("belongs-to-collection"),
            seriesIndex: metaContent("calibre:series_index") ?? metaProperty("group-position")
        )

        // Manifest
        struct Item { var id: String; var url: URL; var mediaType: String; var properties: Set<String> }
        var manifest: [String: Item] = [:]
        for node in pkg.first("manifest")?.children("item") ?? [] {
            guard let id = node["id"], let href = node["href"] else { continue }
            let props = Set((node["properties"] ?? "").split(separator: " ").map(String.init))
            manifest[id] = Item(id: id, url: Self.resolve(href, against: opfDir).deletingFragment, mediaType: node["media-type"] ?? "", properties: props)
        }

        // Spine
        let spineNode = pkg.first("spine")
        spine = (spineNode?.children("itemref") ?? []).compactMap { ref in
            guard let idref = ref["idref"], let item = manifest[idref] else { return nil }
            guard item.mediaType.contains("html") || item.mediaType.contains("xml") || item.url.pathExtension.lowercased().hasPrefix("htm") else { return nil }
            return SpineItem(id: idref, url: item.url, mediaType: item.mediaType, linear: ref["linear"] != "no")
        }
        guard !spine.isEmpty else { throw PackageError.emptySpine }
        spineWeights = spine.map { item in
            let size = (try? fm.attributesOfItem(atPath: item.url.path)[.size] as? NSNumber)?.doubleValue ?? 1
            return max(1, size)
        }

        // Contents: EPUB 3 nav, else NCX, else one entry per spine document
        var raw: [(title: String, href: URL, fragment: String?, level: Int)] = []
        if let navItem = manifest.values.first(where: { $0.properties.contains("nav") }),
           let nav = try? XMLTree.parse(contentsOf: navItem.url) {
            raw = Self.navEntries(nav, base: navItem.url.deletingLastPathComponent())
        }
        if raw.isEmpty {
            let ncxItem = spineNode?["toc"].flatMap { manifest[$0] }
                ?? manifest.values.first { $0.mediaType == "application/x-dtbncx+xml" }
            if let ncxItem, let ncx = try? XMLTree.parse(contentsOf: ncxItem.url) {
                raw = Self.ncxEntries(ncx, base: ncxItem.url.deletingLastPathComponent())
            }
        }
        let spinePaths = spine.map(\.url.standardizedFileURL.path)
        if raw.isEmpty {
            raw = spine.enumerated().map { (title: "Section \($0.offset + 1)", href: $0.element.url, fragment: String?.none, level: 1) }
        }
        toc = raw.enumerated().map { i, e in
            TOCEntry(id: i, title: e.title, url: e.href, fragment: e.fragment, level: e.level,
                     spineIndex: spinePaths.firstIndex(of: e.href.standardizedFileURL.path))
        }

        // Cover
        let images = manifest.values.filter { $0.mediaType.hasPrefix("image/") }
        var cover = manifest.values.first { $0.properties.contains("cover-image") }?.url
        if cover == nil, let id = metaContent("cover"), let item = manifest[id] {
            if item.mediaType.hasPrefix("image/") { cover = item.url }
        }
        if cover == nil, let ref = pkg.first("guide")?.children("reference").first(where: { $0["type"] == "cover" }), let href = ref["href"] {
            let url = Self.resolve(href, against: opfDir).deletingFragment
            if ["jpg", "jpeg", "png", "gif", "webp"].contains(url.pathExtension.lowercased()) {
                cover = url
            } else if let doc = try? XMLTree.parse(contentsOf: url) {
                let src = doc.first("img")?["src"] ?? doc.first("image")?["href"]
                cover = src.map { Self.resolve($0, against: url.deletingLastPathComponent()).deletingFragment }
            }
        }
        if cover == nil {
            cover = images.first { $0.id.lowercased().contains("cover") || $0.url.lastPathComponent.lowercased().contains("cover") }?.url
        }
        coverURL = cover.flatMap { fm.fileExists(atPath: $0.path) ? $0 : nil }
    }

    // MARK: Locations

    /// Spine index for a document URL (fragments ignored).
    public func spineIndex(of url: URL) -> Int? {
        let path = url.deletingFragment.standardizedFileURL.path
        return spine.firstIndex { $0.url.standardizedFileURL.path == path }
    }

    /// Whole-book progress for a position `fraction` (0…1) through spine document `index`, weighted by document size.
    public func progress(spine index: Int, fraction: Double) -> Double {
        guard spine.indices.contains(index) else { return 0 }
        let total = spineWeights.reduce(0, +)
        let before = spineWeights[..<index].reduce(0, +)
        return min(1, max(0, (before + spineWeights[index] * min(1, max(0, fraction))) / total))
    }

    /// The deepest contents entry at or before a spine position.
    public func tocEntry(spine index: Int) -> TOCEntry? {
        toc.last { ($0.spineIndex ?? Int.max) <= index }
    }

    // MARK: Parsing helpers

    static func resolve(_ href: String, against base: URL) -> URL {
        let parts = href.split(separator: "#", maxSplits: 1, omittingEmptySubsequences: false)
        let path = String(parts.first ?? "").removingPercentEncoding ?? String(parts.first ?? "")
        var url = path.isEmpty ? base : base.appendingPathComponent(path).standardizedFileURL
        if parts.count > 1, var comps = URLComponents(url: url, resolvingAgainstBaseURL: false) {
            comps.fragment = String(parts[1])
            url = comps.url ?? url
        }
        return url
    }

    private static func split(_ url: URL) -> (URL, String?) {
        (url.deletingFragment, url.fragment)
    }

    static func ncxEntries(_ ncx: XMLNode, base: URL) -> [(title: String, href: URL, fragment: String?, level: Int)] {
        var out: [(String, URL, String?, Int)] = []
        func walk(_ node: XMLNode, level: Int) {
            for point in node.children("navPoint") {
                if let src = point.child("content")?["src"] {
                    let (url, fragment) = split(resolve(src, against: base))
                    let title = point.child("navLabel")?.text.nonEmpty ?? "Untitled"
                    out.append((title, url, fragment, level))
                }
                walk(point, level: level + 1)
            }
        }
        if let map = ncx.first("navMap") { walk(map, level: 1) }
        return out.map { (title: $0.0, href: $0.1, fragment: $0.2, level: $0.3) }
    }

    static func navEntries(_ doc: XMLNode, base: URL) -> [(title: String, href: URL, fragment: String?, level: Int)] {
        let navs = doc.all("nav")
        guard let nav = navs.first(where: { $0["type"] == "toc" }) ?? navs.first, let list = nav.first("ol") else { return [] }
        var out: [(String, URL, String?, Int)] = []
        func walk(_ ol: XMLNode, level: Int) {
            for li in ol.children("li") {
                if let a = li.child("a") ?? li.first("a"), let href = a["href"] {
                    let (url, fragment) = split(resolve(href, against: base))
                    out.append((a.text.nonEmpty ?? "Untitled", url, fragment, level))
                } else if let span = li.child("span"), let sub = li.child("ol"), let first = sub.first("a")?["href"] {
                    let (url, fragment) = split(resolve(first, against: base))
                    out.append((span.text.nonEmpty ?? "Untitled", url, fragment, level))
                }
                if let sub = li.child("ol") { walk(sub, level: level + 1) }
            }
        }
        walk(list, level: 1)
        return out.map { (title: $0.0, href: $0.1, fragment: $0.2, level: $0.3) }
    }
}

extension URL {
    var deletingFragment: URL {
        guard fragment != nil, var c = URLComponents(url: self, resolvingAgainstBaseURL: false) else { return self }
        c.fragment = nil
        return c.url ?? self
    }
}

extension String {
    var nonEmpty: String? {
        let t = trimmingCharacters(in: .whitespacesAndNewlines)
        return t.isEmpty ? nil : t
    }
}

import Foundation
#if canImport(FoundationXML)
import FoundationXML
#endif

/// A small DOM over XMLParser. Element and attribute names are stored without namespace prefixes,
/// so `dc:title`, `opf:role` and `epub:type` are `title`, `role` and `type`.
final class XMLNode {
    let name: String
    let attributes: [String: String]
    private(set) var children: [XMLNode] = []
    fileprivate var directText = ""

    init(name: String, attributes: [String: String]) {
        self.name = name
        self.attributes = attributes
    }

    fileprivate func append(_ child: XMLNode) { children.append(child) }

    subscript(_ attribute: String) -> String? { attributes[attribute] }

    /// All text inside this element, whitespace collapsed.
    var text: String {
        let raw = directText + children.map(\.text).joined(separator: " ")
        return raw.split(whereSeparator: \.isWhitespace).joined(separator: " ")
    }

    func child(_ name: String) -> XMLNode? { children.first { $0.name == name } }
    func children(_ name: String) -> [XMLNode] { children.filter { $0.name == name } }

    /// Depth-first descendants with the given name.
    func all(_ name: String) -> [XMLNode] {
        var out: [XMLNode] = []
        for c in children {
            if c.name == name { out.append(c) }
            out += c.all(name)
        }
        return out
    }

    func first(_ name: String) -> XMLNode? {
        for c in children {
            if c.name == name { return c }
            if let hit = c.first(name) { return hit }
        }
        return nil
    }
}

enum XMLTree {
    struct ParseError: Error, CustomStringConvertible {
        let description: String
    }

    /// HTML named entities that XHTML navigation documents sometimes use without a DTD.
    private static let entities: [String: String] = [
        "&nbsp;": "&#160;", "&mdash;": "&#8212;", "&ndash;": "&#8211;", "&hellip;": "&#8230;",
        "&lsquo;": "&#8216;", "&rsquo;": "&#8217;", "&ldquo;": "&#8220;", "&rdquo;": "&#8221;", "&copy;": "&#169;",
    ]

    static func parse(_ data: Data) throws -> XMLNode {
        var data = data
        if var s = String(data: data, encoding: .utf8), s.contains("&") {
            for (k, v) in entities { s = s.replacingOccurrences(of: k, with: v) }
            data = Data(s.utf8)
        }
        let builder = Builder()
        let parser = XMLParser(data: data)
        parser.shouldProcessNamespaces = false
        parser.shouldResolveExternalEntities = false
        parser.delegate = builder
        guard parser.parse(), let root = builder.root else {
            throw ParseError(description: parser.parserError?.localizedDescription ?? "Malformed XML")
        }
        return root
    }

    static func parse(contentsOf url: URL) throws -> XMLNode {
        try parse(Data(contentsOf: url))
    }

    private static func local(_ name: String) -> String {
        name.split(separator: ":").last.map(String.init) ?? name
    }

    private final class Builder: NSObject, XMLParserDelegate {
        var root: XMLNode?
        var stack: [XMLNode] = []

        func parser(_ parser: XMLParser, didStartElement elementName: String, namespaceURI: String?,
                    qualifiedName qName: String?, attributes attributeDict: [String: String] = [:]) {
            var attrs: [String: String] = [:]
            for (k, v) in attributeDict where attrs[local(k)] == nil { attrs[local(k)] = v }
            let node = XMLNode(name: local(elementName), attributes: attrs)
            if let parent = stack.last { parent.append(node) } else { root = node }
            stack.append(node)
        }

        func parser(_ parser: XMLParser, didEndElement elementName: String, namespaceURI: String?, qualifiedName qName: String?) {
            _ = stack.popLast()
        }

        func parser(_ parser: XMLParser, foundCharacters string: String) {
            stack.last?.directText += string
        }

        func parser(_ parser: XMLParser, foundCDATA CDATABlock: Data) {
            if let s = String(data: CDATABlock, encoding: .utf8) { stack.last?.directText += s }
        }
    }
}

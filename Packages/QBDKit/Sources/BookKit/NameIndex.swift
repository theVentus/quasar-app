import Foundation

/// Names in a book and where each first appears, built once from the text so a "who's who" can be shown
/// without ever looking past the reader's position. Purely lexical: capitalised words that recur and are
/// not merely sentence openers.
public struct NameIndex: Codable, Sendable, Hashable {
    public struct Entry: Codable, Sendable, Hashable, Identifiable {
        public var name: String
        public var count: Int
        public var firstSpine: Int
        /// The sentence in which the name first occurs, lightly trimmed.
        public var firstSentence: String
        public var id: String { name }
    }

    public var entries: [Entry]

    /// Entries the reader has already met: first seen at or before `spine`.
    public func known(upTo spine: Int) -> [Entry] {
        entries.filter { $0.firstSpine <= spine }
    }

    static let stop: Set<String> = [
        "The", "A", "An", "And", "But", "Or", "So", "If", "Then", "When", "While", "Where", "What", "Why", "How", "Who", "Whom", "Which",
        "This", "That", "These", "Those", "There", "Here", "It", "Its", "He", "She", "They", "We", "You", "I", "His", "Her", "Their", "Our",
        "Your", "My", "Me", "Him", "Them", "Us", "In", "On", "At", "By", "For", "To", "Of", "From", "With", "Without", "Into", "Onto",
        "Over", "Under", "After", "Before", "Between", "Through", "Not", "No", "Yes", "Now", "Still", "Even", "Only", "Just", "Also",
        "Perhaps", "Maybe", "Nothing", "Something", "Everything", "Anything", "Nobody", "Somebody", "Everyone", "Someone", "Anyone",
        "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten", "First", "Second", "Third", "Last", "Next",
        "Yet", "Because", "Although", "Though", "Since", "Until", "Unless", "Once", "Again", "Instead", "Rather", "Almost", "Already",
        "Chapter", "Part", "Book", "Contents", "Copyright", "Acknowledgements", "Prologue", "Epilogue", "Mr", "Mrs", "Ms", "Dr",
        "God", "Earth", "Lord", "Sir", "Madam", "Oh", "Ah", "Well", "Okay", "Right", "Good", "Fine", "Please", "Thank", "Thanks",
        "All", "Some", "Any", "Each", "Every", "Both", "Either", "Neither", "Most", "Many", "Much", "More", "Less", "Few", "Such",
        "Very", "Too", "Let", "Do", "Does", "Did", "Is", "Are", "Was", "Were", "Be", "Been", "Have", "Has", "Had", "Will", "Would",
        "Can", "Could", "Should", "May", "Might", "Must", "Shall", "Get", "Got", "Go", "Come", "Look", "See", "Say", "Said", "Tell",
        "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "January", "February", "March", "April", "June",
        "July", "August", "September", "October", "November", "December", "North", "South", "East", "West",
    ]

    /// Builds the index from the spine documents in reading order. Linear in the book's length.
    public static func build(_ package: BookPackage, minCount: Int = 4) -> NameIndex {
        struct Acc { var count = 0; var starts = 0; var firstSpine = Int.max; var firstSentence = "" }
        var acc: [String: Acc] = [:]
        for (si, item) in package.spine.enumerated() {
            guard let data = try? Data(contentsOf: item.url), let html = String(data: data, encoding: .utf8) else { continue }
            let text = strip(html)
            for sentence in sentences(text) {
                let words = sentence.split(whereSeparator: { $0 == " " || $0 == "\n" }).map(String.init)
                var i = 0
                while i < words.count {
                    let clean = trim(words[i])
                    guard isCap(clean), !stop.contains(clean) else { i += 1; continue }
                    // Extend to a two- or three-word name ("Doctor Avrana Kern")
                    var name = clean
                    var j = i + 1
                    while j < words.count, j - i < 3 {
                        let next = trim(words[j])
                        guard isCap(next), !stop.contains(next), !words[j - 1].hasSuffix(".") else { break }
                        name += " " + next; j += 1
                    }
                    var a = acc[name] ?? Acc()
                    a.count += 1
                    if i == 0 { a.starts += 1 }
                    if si < a.firstSpine { a.firstSpine = si; a.firstSentence = String(sentence.prefix(220)) }
                    acc[name] = a
                    i = j
                }
            }
        }
        // Keep names that recur and are not mostly sentence openers; fold a single-word name into a longer one
        // that contains it when the longer one is at least as common as half of it.
        var kept = acc.filter { $0.value.count >= minCount && Double($0.value.starts) / Double($0.value.count) < 0.6 }
        for (name, a) in kept where !name.contains(" ") {
            if let longer = kept.first(where: { $0.key != name && $0.key.split(separator: " ").contains(Substring(name)) && $0.value.count * 2 >= a.count }) {
                kept[longer.key]!.count += a.count
                kept[longer.key]!.firstSpine = min(kept[longer.key]!.firstSpine, a.firstSpine)
                if a.firstSpine < longer.value.firstSpine { kept[longer.key]!.firstSentence = a.firstSentence }
                kept[name] = nil
            }
        }
        let entries = kept.map { Entry(name: $0.key, count: $0.value.count, firstSpine: $0.value.firstSpine, firstSentence: $0.value.firstSentence) }
            .sorted { ($0.firstSpine, -$0.count, $0.name) < ($1.firstSpine, -$1.count, $1.name) }
        return NameIndex(entries: entries)
    }

    static func strip(_ html: String) -> String {
        var out = ""
        var inTag = false, inScript = false
        var tag = ""
        for ch in html {
            if ch == "<" { inTag = true; tag = ""; continue }
            if ch == ">" {
                inTag = false
                let t = tag.lowercased()
                if t.hasPrefix("style") || t.hasPrefix("script") { inScript = true }
                if t.hasPrefix("/style") || t.hasPrefix("/script") { inScript = false }
                if t.hasPrefix("/p") || t.hasPrefix("br") || t.hasPrefix("/h") || t.hasPrefix("/div") { out.append("\n") }
                continue
            }
            if inTag { tag.append(ch); continue }
            if !inScript { out.append(ch) }
        }
        return out.replacingOccurrences(of: "&nbsp;", with: " ").replacingOccurrences(of: "&amp;", with: "&")
            .replacingOccurrences(of: "&#8217;", with: "’").replacingOccurrences(of: "&#8220;", with: "“").replacingOccurrences(of: "&#8221;", with: "”")
    }

    static func sentences(_ text: String) -> [String] {
        var out: [String] = []
        var cur = ""
        for ch in text {
            cur.append(ch)
            if ch == "." || ch == "!" || ch == "?" || ch == "\n" {
                let t = cur.trimmingCharacters(in: .whitespacesAndNewlines)
                if !t.isEmpty { out.append(t) }
                cur = ""
            }
        }
        let t = cur.trimmingCharacters(in: .whitespacesAndNewlines)
        if !t.isEmpty { out.append(t) }
        return out
    }

    static func trim(_ w: String) -> String {
        var s = Substring(w)
        while let f = s.first, !f.isLetter { s = s.dropFirst() }
        while let l = s.last, !l.isLetter { s = s.dropLast() }
        if let r = s.range(of: "’s"), r.upperBound == s.endIndex { s = s[..<r.lowerBound] }
        if let r = s.range(of: "'s"), r.upperBound == s.endIndex { s = s[..<r.lowerBound] }
        return String(s)
    }

    static func isCap(_ w: String) -> Bool {
        guard let f = w.first, f.isUppercase, w.count >= 2 else { return false }
        let rest = w.dropFirst()
        return rest.allSatisfy { $0.isLetter } && !rest.allSatisfy { $0.isUppercase }
    }
}

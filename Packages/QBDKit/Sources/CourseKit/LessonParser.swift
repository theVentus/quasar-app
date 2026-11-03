import Foundation

/// Parses the lesson format shared with the web reader:
/// optional `---` front matter, `TITLE:`, `ABSTRACT:`, then `===BODY===`, `===QUESTIONS===`, `===KEY===`, `===REFERENCES===`.
public enum LessonParser {
    static let markers = ["BODY", "QUESTIONS", "KEY", "REFERENCES"]

    public static func parse(_ raw: String, id: String) -> Lesson {
        var text = raw.replacingOccurrences(of: "\r\n", with: "\n")
        var front: [String: String] = [:]
        if text.hasPrefix("---\n"), let end = text.range(of: "\n---\n", range: text.index(text.startIndex, offsetBy: 4)..<text.endIndex) {
            let fm = text[text.index(text.startIndex, offsetBy: 4)..<end.lowerBound]
            for line in fm.split(separator: "\n") {
                if let c = line.firstIndex(of: ":") {
                    front[line[..<c].trimmingCharacters(in: .whitespaces)] = line[line.index(after: c)...].trimmingCharacters(in: .whitespaces)
                }
            }
            text = String(text[end.upperBound...])
        }
        let head = text.components(separatedBy: "===BODY===").first ?? ""
        let title = value(after: "TITLE:", in: head, singleLine: true)
        let abstract = value(after: "ABSTRACT:", in: head, singleLine: false)
        var ctx = BlockParser.Context()
        let blocks = BlockParser.parse(section("BODY", in: text), ctx: &ctx)
        let questions = numbered(section("QUESTIONS", in: text)).map { (pair: (Int, String)) -> Question in
            let n = pair.0
            var kind = "", body = pair.1
            if body.hasPrefix("["), let close = body.firstIndex(of: "]") {
                kind = String(body[body.index(after: body.startIndex)..<close]).trimmingCharacters(in: .whitespaces).lowercased()
                body = String(body[body.index(after: close)...])
            }
            return Question(id: "q\(n)", kind: kind, text: stripLead(body))
        }
        var key: [String: String] = [:]
        for (n, rest) in numbered(section("KEY", in: text)) { key["q\(n)"] = stripLead(rest) }
        let refs = section("REFERENCES", in: text).split(separator: "\n").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty }
        return Lesson(id: id, title: title, abstract: abstract, blocks: blocks, questions: questions.filter { !$0.text.isEmpty }, key: key, references: refs, frontMatter: front)
    }

    static func value(after label: String, in head: String, singleLine: Bool) -> String {
        guard let r = head.range(of: label) else { return "" }
        let rest = head[r.upperBound...]
        if singleLine { return String(rest.split(separator: "\n", omittingEmptySubsequences: false).first ?? "").trimmingCharacters(in: .whitespaces) }
        return rest.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    static func section(_ name: String, in text: String) -> String {
        guard let r = text.range(of: "===\(name)===") else { return "" }
        var end = text.endIndex
        for m in markers where m != name {
            if let r2 = text.range(of: "===\(m)===", range: r.upperBound..<text.endIndex), r2.lowerBound < end { end = r2.lowerBound }
        }
        return String(text[r.upperBound..<end]).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    /// Lines like `Q3 [apply] ...` or `Q3: ...`, with continuation lines appended.
    static func numbered(_ text: String) -> [(Int, String)] {
        var out: [(Int, String)] = []
        for line in text.split(separator: "\n", omittingEmptySubsequences: false) {
            let l = line.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: "**", with: "")
            if l.hasPrefix("Q"), let n = Int(l.dropFirst().prefix { $0.isNumber }) {
                let rest = l.dropFirst(1 + String(n).count)
                out.append((n, String(rest).trimmingCharacters(in: .whitespaces)))
            } else if !out.isEmpty, !l.isEmpty {
                out[out.count - 1].1 += "\n" + l
            }
        }
        return out
    }

    static func stripLead(_ s: String) -> String {
        var t = Substring(s).drop { $0 == " " }
        if let f = t.first, ":.)-–".contains(f) { t = t.dropFirst() }
        return t.trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

/// Markdown-subset block parser for lesson bodies.
public enum BlockParser {
    public struct Context {
        var counters: [TheoremKind: Int] = [:]
        var equation = 0
        public init() {}
    }

    static let theoremWords = ["Definition", "Example", "Theorem", "Exercise", "Remark", "Misconception", "Key idea", "Note", "Intuition", "Warning", "Check"]

    public static func parse(_ text: String, ctx: inout Context) -> [Block] {
        let lines = text.replacingOccurrences(of: "\r\n", with: "\n").components(separatedBy: "\n")
        var out: [Block] = []
        var i = 0
        func isStart(_ l: String) -> Bool {
            let t = l.trimmingCharacters(in: .whitespaces)
            return t.hasPrefix("#") || t.hasPrefix(">") || t.hasPrefix("```") || t.hasPrefix("|") || t.hasPrefix("\\begin{")
                || isListItem(t) || t == "---" || t == "***"
        }
        while i < lines.count {
            let line = lines[i]
            let t = line.trimmingCharacters(in: .whitespaces)
            if t.isEmpty { i += 1; continue }

            // Single-line widget: ```widget name```
            if t.hasPrefix("```widget"), t.hasSuffix("```"), t.count > 13 {
                let name = t.dropFirst(9).dropLast(3).trimmingCharacters(in: .whitespaces)
                out.append(.widget(name)); i += 1; continue
            }
            if t.hasPrefix("```") {
                let lang = t.dropFirst(3).trimmingCharacters(in: .whitespaces).lowercased()
                var body: [String] = []
                i += 1
                while i < lines.count, lines[i].trimmingCharacters(in: .whitespaces) != "```" { body.append(lines[i]); i += 1 }
                i += 1
                out.append(fenced(lang: String(lang.split(separator: " ").first ?? ""), body: body.joined(separator: "\n"), ctx: &ctx))
                continue
            }
            if t.hasPrefix("#") {
                let level = t.prefix { $0 == "#" }.count
                out.append(.heading(level: level <= 2 ? 2 : 3, text: t.dropFirst(level).trimmingCharacters(in: .whitespaces)))
                i += 1; continue
            }
            if t == "---" || t == "***" { out.append(.rule); i += 1; continue }
            if t.hasPrefix(">") {
                var inner: [String] = []
                while i < lines.count {
                    let l = lines[i].trimmingCharacters(in: .whitespaces)
                    guard l.hasPrefix(">") else { break }
                    var s = l.dropFirst()
                    if s.first == " " { s = s.dropFirst() }
                    inner.append(String(s)); i += 1
                }
                out.append(quote(inner.joined(separator: "\n"), ctx: &ctx))
                continue
            }
            if t.hasPrefix("\\begin{") {
                var body: [String] = [t]
                let env = t.dropFirst(7).prefix { $0 != "}" }
                i += 1
                if !t.contains("\\end{\(env)}") {
                    while i < lines.count { body.append(lines[i]); let done = lines[i].contains("\\end{\(env)}"); i += 1; if done { break } }
                }
                out.append(equation(body.joined(separator: "\n"), env: String(env), ctx: &ctx))
                continue
            }
            if t.hasPrefix("|"), i + 1 < lines.count, lines[i + 1].trimmingCharacters(in: .whitespaces).hasPrefix("|"),
               lines[i + 1].contains("--") {
                var rows: [[String]] = []
                while i < lines.count, lines[i].trimmingCharacters(in: .whitespaces).hasPrefix("|") { rows.append(cells(lines[i])); i += 1 }
                out.append(.table(header: rows.first ?? [], rows: Array(rows.dropFirst(2))))
                continue
            }
            if isListItem(t) {
                let ordered = t.first?.isNumber ?? false
                var items: [String] = []
                while i < lines.count {
                    let l = lines[i].trimmingCharacters(in: .whitespaces)
                    if isListItem(l) { items.append(stripListMarker(l)); i += 1 }
                    else if !l.isEmpty, !isStart(l), !items.isEmpty, lines[i].hasPrefix("  ") { items[items.count - 1] += " " + l; i += 1 }
                    else { break }
                }
                out.append(.list(ordered: ordered, items: items))
                continue
            }
            var para: [String] = [line]
            i += 1
            while i < lines.count {
                let l = lines[i]
                if l.trimmingCharacters(in: .whitespaces).isEmpty || isStart(l) { break }
                para.append(l); i += 1
            }
            out.append(contentsOf: paragraphs(para.joined(separator: "\n"), ctx: &ctx))
        }
        return out
    }

    static func isListItem(_ t: String) -> Bool {
        if t.hasPrefix("- ") || t.hasPrefix("* ") || t.hasPrefix("• ") { return true }
        let digits = t.prefix { $0.isNumber }
        guard !digits.isEmpty else { return false }
        let rest = t.dropFirst(digits.count)
        return rest.hasPrefix(". ") || rest.hasPrefix(") ")
    }

    static func stripListMarker(_ t: String) -> String {
        if t.hasPrefix("- ") || t.hasPrefix("* ") || t.hasPrefix("• ") { return String(t.dropFirst(2)) }
        let digits = t.prefix { $0.isNumber }
        return t.dropFirst(digits.count + 2).trimmingCharacters(in: .whitespaces)
    }

    static func cells(_ row: String) -> [String] {
        var r = row.trimmingCharacters(in: .whitespaces)
        if r.hasPrefix("|") { r.removeFirst() }
        if r.hasSuffix("|") { r.removeLast() }
        return r.components(separatedBy: "|").map { $0.trimmingCharacters(in: .whitespaces) }
    }

    /// Splits a paragraph on `$$…$$` so display maths inside prose becomes its own block.
    static func paragraphs(_ text: String, ctx: inout Context) -> [Block] {
        let parts = text.components(separatedBy: "$$")
        guard parts.count >= 3 else { return [.paragraph(text.trimmingCharacters(in: .whitespacesAndNewlines))] }
        var out: [Block] = []
        for (k, part) in parts.enumerated() {
            let p = part.trimmingCharacters(in: .whitespacesAndNewlines)
            if p.isEmpty { continue }
            if k % 2 == 1, k < parts.count - 1 { out.append(.displayMath(latex: p, number: nil)) }
            else { out.append(.paragraph(p)) }
        }
        return out
    }

    static func equation(_ src: String, env: String, ctx: inout Context) -> Block {
        var body = src
        if let a = body.range(of: "\\begin{\(env)}") { body = String(body[a.upperBound...]) }
        if let b = body.range(of: "\\end{\(env)}") { body = String(body[..<b.lowerBound]) }
        let starred = env.hasSuffix("*")
        var number: Int? = nil
        if !starred && (env.hasPrefix("equation") || env.hasPrefix("align") || env.hasPrefix("gather")) { ctx.equation += 1; number = ctx.equation }
        return .displayMath(latex: body.trimmingCharacters(in: .whitespacesAndNewlines), number: number)
    }

    static func quote(_ inner: String, ctx: inout Context) -> Block {
        // > **Definition (Title).** body
        let t = inner.trimmingCharacters(in: .whitespaces)
        guard t.hasPrefix("**") else { return .theorem(kind: .note, number: nil, title: nil, body: parse(inner, ctx: &ctx)) }
        let afterStars = t.dropFirst(2)
        for word in theoremWords where afterStars.lowercased().hasPrefix(word.lowercased()) {
            guard let kind = TheoremKind.from(word), let close = afterStars.range(of: "**") else { continue }
            var head = afterStars[afterStars.index(afterStars.startIndex, offsetBy: word.count)..<close.lowerBound].trimmingCharacters(in: .whitespaces)
            if head.hasSuffix(".") { head.removeLast() }
            var title: String? = nil
            if head.hasPrefix("("), let rp = head.lastIndex(of: ")") {
                title = String(head[head.index(after: head.startIndex)..<rp])
            }
            var rest = afterStars[close.upperBound...].drop { $0 == " " }
            if rest.first == "." { rest = rest.dropFirst() }
            var number: Int? = nil
            if kind.isNumbered { ctx.counters[kind, default: 0] += 1; number = ctx.counters[kind] }
            return .theorem(kind: kind, number: number, title: title, body: parse(String(rest), ctx: &ctx))
        }
        return .theorem(kind: .note, number: nil, title: nil, body: parse(inner, ctx: &ctx))
    }

    static func fenced(lang: String, body: String, ctx: inout Context) -> Block {
        switch lang {
        case "widget": return .widget(body.trimmingCharacters(in: .whitespacesAndNewlines))
        case "explore": return .explore(body)
        case "quiz": return quiz(body).map(Block.quiz) ?? .code(body)
        case "steps": return .steps(steps(body, ctx: &ctx))
        default: return .code(body)
        }
    }

    public static func quiz(_ body: String) -> Quiz? {
        var q: [String] = [], opts: [String] = [], why: [String] = []
        var correct = -1
        for line in body.components(separatedBy: "\n") {
            let l = line.trimmingCharacters(in: .whitespaces)
            if l.hasPrefix("- [") || l.hasPrefix("* ["), l.count > 5 {
                let mark = l[l.index(l.startIndex, offsetBy: 3)]
                if mark == "x" || mark == "X" { correct = opts.count }
                opts.append(l.dropFirst(6).trimmingCharacters(in: .whitespaces))
            } else if l.hasPrefix(">") {
                why.append(l.dropFirst().trimmingCharacters(in: .whitespaces))
            } else if !why.isEmpty {
                why.append(l)
            } else if opts.isEmpty {
                q.append(l.hasPrefix("Q:") ? String(l.dropFirst(2)).trimmingCharacters(in: .whitespaces) : l)
            }
        }
        guard !opts.isEmpty, correct >= 0 else { return nil }
        return Quiz(question: q.joined(separator: " ").trimmingCharacters(in: .whitespaces), options: opts, correct: correct,
                    explanation: why.joined(separator: " ").trimmingCharacters(in: .whitespaces))
    }

    static func steps(_ body: String, ctx: inout Context) -> Steps {
        var chunks: [[String]] = [[]]
        for line in body.components(separatedBy: "\n") {
            if line.trimmingCharacters(in: .whitespaces) == "---" { chunks.append([]) } else { chunks[chunks.count - 1].append(line) }
        }
        var title = ""
        if let idx = chunks[0].firstIndex(where: { $0.trimmingCharacters(in: .whitespaces).lowercased().hasPrefix("title:") }) {
            title = chunks[0][idx].trimmingCharacters(in: .whitespaces).dropFirst(6).trimmingCharacters(in: .whitespaces)
            chunks[0].remove(at: idx)
        }
        let steps = chunks.map { $0.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }
            .map { parse($0, ctx: &ctx) }
        return Steps(title: title, steps: steps)
    }
}

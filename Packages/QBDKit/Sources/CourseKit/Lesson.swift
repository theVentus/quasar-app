import Foundation

public struct Lesson: Hashable, Sendable {
    public var id: String
    public var title: String
    public var abstract: String
    public var blocks: [Block]
    public var questions: [Question]
    public var key: [String: String]
    public var references: [String]
    public var frontMatter: [String: String]
}

public struct Question: Hashable, Sendable, Identifiable {
    public var id: String        // "q1"
    public var kind: String      // explain | calculate | predict | apply
    public var text: String
}

public enum TheoremKind: String, Hashable, Sendable, CaseIterable {
    case definition, example, theorem, exercise, remark, misconception, keyIdea, note, intuition, warning, check

    public var label: String {
        switch self {
        case .keyIdea: return "Key idea"
        default: return rawValue.prefix(1).uppercased() + rawValue.dropFirst()
        }
    }
    /// Numbered like LaTeX amsthm environments.
    public var isNumbered: Bool { [.definition, .example, .theorem, .exercise].contains(self) }

    static func from(_ word: String) -> TheoremKind? {
        switch word.lowercased() {
        case "key idea": return .keyIdea
        default: return TheoremKind(rawValue: word.lowercased())
        }
    }
}

public struct Quiz: Hashable, Sendable {
    public var question: String
    public var options: [String]
    public var correct: Int
    public var explanation: String
}

public struct Steps: Hashable, Sendable {
    public var title: String
    public var steps: [[Block]]
}

public indirect enum Block: Hashable, Sendable {
    case heading(level: Int, text: String)
    case paragraph(String)
    case theorem(kind: TheoremKind, number: Int?, title: String?, body: [Block])
    case displayMath(latex: String, number: Int?)
    case list(ordered: Bool, items: [String])
    case table(header: [String], rows: [[String]])
    case quiz(Quiz)
    case steps(Steps)
    case widget(String)
    case explore(String)
    case code(String)
    case rule
}

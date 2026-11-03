import Foundation

/// A run of inline text with its style, or an inline maths expression.
public struct InlineRun: Hashable, Sendable {
    public enum Kind: Hashable, Sendable { case text, math }
    public var kind: Kind
    public var text: String
    public var bold = false
    public var italic = false
    public var mark = false
}

public enum InlineParser {
    /// Splits prose into styled runs: `$maths$`, `**bold**`, `*italic*`, `==highlight==`, `[text](url)` → text.
    public static func parse(_ s: String) -> [InlineRun] {
        var runs: [InlineRun] = []
        var bold = false, italic = false, mark = false
        var buf = ""
        let chars = Array(s.replacingOccurrences(of: "\n", with: " "))
        var i = 0
        func flush() {
            if !buf.isEmpty { runs.append(InlineRun(kind: .text, text: buf, bold: bold, italic: italic, mark: mark)); buf = "" }
        }
        while i < chars.count {
            let c = chars[i]
            let next: Character? = i + 1 < chars.count ? chars[i + 1] : nil
            if c == "\\", next == "$" { buf.append("$"); i += 2; continue }
            if c == "$" {
                var j = i + 1
                while j < chars.count, !(chars[j] == "$" && chars[j - 1] != "\\") { j += 1 }
                if j < chars.count, j > i + 1 {
                    flush()
                    runs.append(InlineRun(kind: .math, text: String(chars[(i + 1)..<j]), bold: bold, italic: false, mark: mark))
                    i = j + 1; continue
                }
            }
            if c == "*", next == "*" { flush(); bold.toggle(); i += 2; continue }
            if c == "*", (italic || (next != nil && next != " ")) { flush(); italic.toggle(); i += 1; continue }
            if c == "=", next == "=" { flush(); mark.toggle(); i += 2; continue }
            if c == "[", let close = chars[i...].firstIndex(of: "]"), close + 1 < chars.count, chars[close + 1] == "(",
               let paren = chars[(close + 1)...].firstIndex(of: ")") {
                buf.append(contentsOf: chars[(i + 1)..<close]); i = paren + 1; continue
            }
            buf.append(c); i += 1
        }
        flush()
        return runs
    }
}

/// Converts simple inline TeX to readable Unicode. A v0.1 stopgap until inline maths is typeset natively (plan §5.1).
public enum TeXInline {
    static let symbols: [String: String] = [
        "times": "×", "cdot": "·", "approx": "≈", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "neq": "≠", "pm": "±", "mp": "∓",
        "infty": "∞", "to": "→", "rightarrow": "→", "leftarrow": "←", "propto": "∝", "sim": "∼", "partial": "∂", "nabla": "∇",
        "Delta": "Δ", "delta": "δ", "mu": "μ", "pi": "π", "lambda": "λ", "tau": "τ", "theta": "θ", "omega": "ω", "Omega": "Ω",
        "sigma": "σ", "Sigma": "Σ", "rho": "ρ", "alpha": "α", "beta": "β", "gamma": "γ", "epsilon": "ε", "varepsilon": "ε",
        "phi": "φ", "varphi": "φ", "psi": "ψ", "nu": "ν", "eta": "η", "kappa": "κ", "chi": "χ", "xi": "ξ", "Phi": "Φ", "Psi": "Ψ",
        "ldots": "…", "dots": "…", "cdots": "⋯", "circ": "∘", "degree": "°", "prime": "′", "%": "%", "{": "{", "}": "}",
    ]
    static let sup: [Character: Character] = ["0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
                                              "-": "⁻", "−": "⁻", "+": "⁺", "n": "ⁿ", "i": "ⁱ", "(": "⁽", ")": "⁾", "=": "⁼"]
    static let sub: [Character: Character] = ["0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
                                              "-": "₋", "+": "₊", "a": "ₐ", "e": "ₑ", "o": "ₒ", "x": "ₓ", "h": "ₕ", "k": "ₖ", "l": "ₗ",
                                              "m": "ₘ", "n": "ₙ", "p": "ₚ", "s": "ₛ", "t": "ₜ", "i": "ᵢ", "j": "ⱼ", "r": "ᵣ", "u": "ᵤ", "v": "ᵥ"]

    public static func unicode(_ tex: String) -> String {
        let c = Array(tex)
        var i = 0
        func group() -> String {
            // Reads `{…}` or a single token after ^, _ or a command.
            while i < c.count, c[i] == " " { i += 1 }
            guard i < c.count else { return "" }
            if c[i] == "{" {
                var depth = 0, j = i
                repeat { if c[j] == "{" { depth += 1 } else if c[j] == "}" { depth -= 1 }; j += 1 } while j < c.count && depth > 0
                let inner = String(c[(i + 1)..<max(i + 1, j - 1)]); i = j
                return unicode(inner)
            }
            if c[i] == "\\" { let start = i; i += 1; while i < c.count, c[i].isLetter { i += 1 }; return unicode(String(c[start..<i])) }
            defer { i += 1 }
            return String(c[i])
        }
        var out = ""
        while i < c.count {
            let ch = c[i]
            if ch == "\\" {
                i += 1
                guard i < c.count else { break }
                if !c[i].isLetter {
                    let s = c[i]; i += 1
                    switch s { case ",", ":", ";", " ", "!": out += s == "!" ? "" : "\u{2009}"; default: out += symbols[String(s)] ?? String(s) }
                    continue
                }
                var name = ""
                while i < c.count, c[i].isLetter { name.append(c[i]); i += 1 }
                while i < c.count, c[i] == " " { i += 1 }   // TeX swallows spaces after a control word
                switch name {
                case "mathrm", "text", "mathbf", "mathit", "operatorname", "textrm", "boldsymbol", "mathsf": out += group()
                case "frac": let a = group(), b = group(); out += wrap(a) + "/" + wrap(b)
                case "sqrt": out += "√" + wrap(group())
                case "hat": out += group() + "\u{0302}"
                case "vec": out += group() + "\u{20D7}"
                case "bar", "overline": out += group() + "\u{0305}"
                case "dot": out += group() + "\u{0307}"
                case "left", "right", "big", "Big", "bigl", "bigr", "displaystyle": continue
                case "quad", "qquad": out += "  "
                default: out += symbols[name] ?? name
                }
                continue
            }
            if ch == "^" || ch == "_" {
                i += 1
                let g = group()
                let table = ch == "^" ? sup : sub
                if g.allSatisfy({ table[$0] != nil }) { out += String(g.map { table[$0]! }) } else { out += (ch == "^" ? "^" : "_") + wrap(g) }
                continue
            }
            if ch == "{" || ch == "}" { i += 1; continue }
            if ch == "~" { out += "\u{00A0}"; i += 1; continue }
            out.append(ch == "-" ? "−" : ch); i += 1
        }
        return out
    }

    static func wrap(_ s: String) -> String { s.count > 1 && s.contains(where: { "+−-×/ ".contains($0) }) ? "(\(s))" : s }
}

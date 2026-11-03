import Foundation

/// Safe arithmetic for explorable models: a port of the web reader's `xparse`/`xeval`.
/// Grammar: + - * / ^ (right-associative), unary minus, parentheses, identifiers, function calls.
public indirect enum Expr: Hashable, Sendable {
    case num(Double)
    case id(String)
    case neg(Expr)
    case bin(Character, Expr, Expr)
    case fn(String, [Expr])

    public enum ParseError: Error, Equatable { case token, unexpected, trailing, unknownFunction(String), tooLong }

    public static let constants: [String: Double] = [
        "pi": .pi, "c": 299_792_458, "G": 6.674e-11, "GM": 3.986004418e14, "R_E": 6.371e6, "omega_E": 7.2921151467e-5,
        "DAY": 86_400, "f_L1": 1575.42e6, "f_L2": 1227.6e6, "f_L5": 1176.45e6, "AU": 1.495978707e11, "ly": 9.4607304725808e15,
    ]

    static let functions: [String: ([Double]) -> Double] = [
        "sqrt": { sqrt($0[0]) }, "abs": { abs($0[0]) }, "exp": { exp($0[0]) }, "ln": { log($0[0]) }, "log": { log($0[0]) },
        "log10": { log10($0[0]) }, "sin": { sin($0[0]) }, "cos": { cos($0[0]) }, "tan": { tan($0[0]) }, "asin": { asin($0[0]) },
        "acos": { acos($0[0]) }, "atan": { atan($0[0]) }, "atan2": { atan2($0[0], $0.count > 1 ? $0[1] : .nan) },
        "min": { $0.min() ?? .nan }, "max": { $0.max() ?? .nan }, "pow": { pow($0[0], $0.count > 1 ? $0[1] : .nan) },
        "hypot": { sqrt($0.reduce(0) { $0 + $1 * $1 }) }, "floor": { floor($0[0]) }, "round": { ($0[0]).rounded() },
        "deg": { $0[0] * 180 / .pi }, "rad": { $0[0] * .pi / 180 },
    ]

    enum Tok: Equatable { case n(Double), id(String), op(Character) }

    public static func parse(_ src: String) throws -> Expr {
        guard src.count <= 500 else { throw ParseError.tooLong }
        var toks: [Tok] = []
        let s = Array(src)
        var i = 0
        while i < s.count {
            let ch = s[i]
            if ch == " " || ch == "\t" || ch == "\n" { i += 1; continue }
            if ch.isNumber || (ch == "." && i + 1 < s.count && s[i + 1].isNumber) {
                var j = i
                while j < s.count, s[j].isNumber || s[j] == "." { j += 1 }
                if j < s.count, s[j] == "e" || s[j] == "E" {
                    var k = j + 1
                    if k < s.count, s[k] == "+" || s[k] == "-" { k += 1 }
                    if k < s.count, s[k].isNumber { j = k; while j < s.count, s[j].isNumber { j += 1 } }
                }
                guard let v = Double(String(s[i..<j])) else { throw ParseError.token }
                toks.append(.n(v)); i = j; continue
            }
            if ch.isLetter || ch == "_" {
                var j = i
                while j < s.count, s[j].isLetter || s[j].isNumber || s[j] == "_" { j += 1 }
                toks.append(.id(String(s[i..<j]))); i = j; continue
            }
            if ch == "*", i + 1 < s.count, s[i + 1] == "*" { toks.append(.op("^")); i += 2; continue }
            if "+-*/^(),".contains(ch) { toks.append(.op(ch)); i += 1; continue }
            throw ParseError.token
        }
        var p = 0
        func peek(_ c: Character) -> Bool { p < toks.count && toks[p] == .op(c) }
        func take(_ c: Character) throws { guard peek(c) else { throw ParseError.unexpected }; p += 1 }
        func expr() throws -> Expr {
            var l = try term()
            while peek("+") || peek("-") { let o: Character = peek("+") ? "+" : "-"; p += 1; l = .bin(o, l, try term()) }
            return l
        }
        func term() throws -> Expr {
            var l = try unary()
            while peek("*") || peek("/") { let o: Character = peek("*") ? "*" : "/"; p += 1; l = .bin(o, l, try unary()) }
            return l
        }
        func unary() throws -> Expr {
            if peek("-") { p += 1; return .neg(try unary()) }
            if peek("+") { p += 1; return try unary() }
            return try power()
        }
        func power() throws -> Expr {
            let a = try atom()
            if peek("^") { p += 1; return .bin("^", a, try unary()) }
            return a
        }
        func atom() throws -> Expr {
            guard p < toks.count else { throw ParseError.unexpected }
            let t = toks[p]; p += 1
            switch t {
            case .n(let v): return .num(v)
            case .id(let name):
                if peek("(") {
                    p += 1
                    var args: [Expr] = []
                    if !peek(")") { args.append(try expr()); while peek(",") { p += 1; args.append(try expr()) } }
                    try take(")")
                    guard functions[name] != nil else { throw ParseError.unknownFunction(name) }
                    return .fn(name, args)
                }
                return .id(name)
            case .op("("):
                let e = try expr(); try take(")"); return e
            default: throw ParseError.unexpected
            }
        }
        let e = try expr()
        guard p == toks.count else { throw ParseError.trailing }
        return e
    }

    public func eval(_ env: [String: Double]) -> Double {
        switch self {
        case .num(let v): return v
        case .id(let n): return env[n] ?? Expr.constants[n] ?? .nan
        case .neg(let a): return -a.eval(env)
        case .fn(let f, let args): return args.isEmpty ? .nan : (Expr.functions[f]?(args.map { $0.eval(env) }) ?? .nan)
        case .bin(let o, let a, let b):
            let x = a.eval(env), y = b.eval(env)
            switch o { case "+": return x + y; case "-": return x - y; case "*": return x * y; case "/": return x / y; default: return pow(x, y) }
        }
    }
}

/// Number formatting with SI prefixes: a port of the web reader's `fmtQ`, so both surfaces print identical values.
public enum Quantity {
    static let prefixes: [(Double, String)] = [(1e9, "G"), (1e6, "M"), (1e3, "k"), (1, ""), (1e-3, "m"), (1e-6, "μ"), (1e-9, "n"), (1e-12, "p"), (1e-15, "f")]
    static let superscripts: [Character: Character] = ["-": "⁻", "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹"]

    public static func sig(_ x: Double, _ d: Int = 3) -> String {
        let f = NumberFormatter()
        f.locale = Locale(identifier: "en_GB")
        f.numberStyle = .decimal
        f.usesSignificantDigits = true
        f.maximumSignificantDigits = d
        f.minimumSignificantDigits = 1
        f.usesGroupingSeparator = true
        return f.string(from: NSNumber(value: x)) ?? String(x)
    }

    public static func sci(_ a: Double, _ d: Int = 3) -> String {
        var e = Int(floor(log10(a)))
        var m = Double(String(format: "%.\(max(0, d - 1))e", a / pow(10, Double(e))).split(separator: "e")[0]) ?? a / pow(10, Double(e))
        if m >= 10 { m /= 10; e += 1 }
        let exp = String(String(e).map { superscripts[$0] ?? $0 })
        return (m == 1 ? "" : sig(m, d) + " × ") + "10" + exp
    }

    public static func format(_ v: Double, unit: String = "", digits d: Int = 3) -> String {
        guard v.isFinite else { return "—" }
        let sp = unit.isEmpty ? "" : " "
        if v == 0 { return "0" + sp + unit }
        let a = abs(v), neg = v < 0 ? "−" : ""
        if unit == "s", a >= 120 {
            if a >= 172_800 { return neg + sig(a / 86_400, d) + " days" }
            if a >= 7_200 { return neg + sig(a / 3_600, d) + " h" }
            return neg + sig(a / 60, d) + " min"
        }
        if unit == "m" {
            if a >= 1_000 { return neg + (a < 1e8 ? sig(a / 1_000, d) : sci(a / 1_000, d)) + " km" }
            if a >= 1 { return neg + sig(a, d) + " m" }
            if a >= 0.01 { return neg + sig(a * 100, d) + " cm" }
        }
        if ["s", "m", "Hz", "W", "J", "V", "A"].contains(unit) {
            for (f, p) in prefixes {
                if unit == "m" && f > 1 { continue }
                if a >= f * 0.9995 { return neg + sig(a / f, d) + " " + p + unit }
            }
            return neg + sci(a, d) + " " + unit
        }
        return neg + (a >= 1e6 || a < 1e-3 ? sci(a, d) : sig(a, d)) + sp + unit
    }
}

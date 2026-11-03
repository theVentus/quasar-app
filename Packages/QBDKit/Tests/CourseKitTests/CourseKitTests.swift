import XCTest
@testable import CourseKit

/// Paths into the repo's content folder (tests run from a checkout, on Linux and macOS CI).
enum Fixture {
    static let repo = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        .deletingLastPathComponent().deletingLastPathComponent()
    static let course = repo.appendingPathComponent("content/courses/quasar-to-blue-dot")
}

final class ManifestTests: XCTestCase {
    func testCourseManifestDecodes() throws {
        let pkg = try CoursePackage(root: Fixture.course)
        let m = pkg.manifest
        XCTAssertEqual(m.schema, "qbd.course/1")
        XCTAssertEqual(m.theme?.landing, "sky")
        XCTAssertEqual(m.theme?.accent, "#A9C4F5")
        XCTAssertEqual(m.modules.count, 13)
        XCTAssertEqual(m.allLessons.count, 57)
        XCTAssertEqual(m.publishedCount, 1)
        XCTAssertEqual(m.lab.count, 6)
        XCTAssertEqual(m.lesson("2-1")?.number, "2.1")
        XCTAssertEqual(m.module(of: "6-3")?.title, "Relativity in GNSS")
    }
}

final class LessonParserTests: XCTestCase {
    var lesson: Lesson!

    override func setUpWithError() throws {
        let pkg = try CoursePackage(root: Fixture.course)
        lesson = try pkg.lesson(pkg.manifest.lesson("0-1")!)
    }

    private func flatten(_ blocks: [Block]) -> [Block] {
        blocks.flatMap { b -> [Block] in
            switch b {
            case .theorem(_, _, _, let body): return [b] + flatten(body)
            case .steps(let s): return [b] + s.steps.flatMap(flatten)
            default: return [b]
            }
        }
    }

    func testHeader() {
        XCTAssertEqual(lesson.title, "Time is distance")
        XCTAssertTrue(lesson.abstract.hasPrefix("Satellite positioning turns"))
        XCTAssertEqual(lesson.frontMatter["status"], "published")
    }

    func testSectionsAndBlocks() {
        let all = flatten(lesson.blocks)
        let h2 = all.compactMap { if case .heading(2, let t) = $0 { return t } else { return nil } }
        XCTAssertEqual(h2, ["Intuition", "The defining constant", "Powers of ten", "The ranging equation", "Worked examples", "Deeper theory", "Misconceptions"])
        let numbered = all.compactMap { if case .displayMath(_, let n?) = $0 { return n } else { return nil } }
        XCTAssertEqual(numbered, [1, 2, 3])
        XCTAssertEqual(all.filter { if case .quiz = $0 { return true } else { return false } }.count, 2)
        XCTAssertEqual(all.filter { if case .steps = $0 { return true } else { return false } }.count, 1)
        let widgets = all.compactMap { if case .widget(let n) = $0 { return n } else { return nil } }
        XCTAssertEqual(widgets, ["light-time", "clock-drift"])
        XCTAssertTrue(all.contains { if case .table(let h, let rows) = $0 { return h == ["Prefix", "Symbol", "Factor"] && rows.count == 7 } else { return false } })
    }

    func testTheorems() {
        let thms = flatten(lesson.blocks).compactMap { b -> (TheoremKind, Int?, String?)? in
            if case .theorem(let k, let n, let t, _) = b { return (k, n, t) } else { return nil }
        }
        XCTAssertEqual(thms.first?.0, .remark)
        XCTAssertEqual(thms.first?.2, "Where the analogy breaks")
        let examples = thms.filter { $0.0 == .example }
        XCTAssertEqual(examples.map { $0.1 }, [1, 2, 3])
        XCTAssertEqual(examples.last?.2, "Clocks that run at the wrong rate")
        XCTAssertTrue(thms.contains { $0.0 == .keyIdea })
        XCTAssertEqual(thms.filter { $0.0 == .misconception }.count, 2)
    }

    func testQuizAndSteps() {
        let all = flatten(lesson.blocks)
        guard case .quiz(let q)? = all.first(where: { if case .quiz = $0 { return true } else { return false } }) else { return XCTFail("no quiz") }
        XCTAssertEqual(q.options.count, 4)
        XCTAssertEqual(q.correct, 1)
        XCTAssertTrue(q.explanation.hasPrefix("Nano means"))
        guard case .steps(let s)? = all.first(where: { if case .steps = $0 { return true } else { return false } }) else { return XCTFail("no steps") }
        XCTAssertEqual(s.title, "The precision needed for a one-metre range")
        XCTAssertEqual(s.steps.count, 3)
    }

    func testExercisesKeyReferences() {
        XCTAssertEqual(lesson.questions.map(\.id), ["q1", "q2", "q3", "q4"])
        XCTAssertEqual(lesson.questions.map(\.kind), ["explain", "calculate", "apply", "predict"])
        XCTAssertTrue(lesson.questions[2].text.contains("3 m over 30 s"))
        XCTAssertTrue(lesson.key["q3"]?.contains("3.3e-10") ?? false)
        XCTAssertEqual(lesson.references.count, 5)
    }
}

final class InlineTests: XCTestCase {
    func testRuns() {
        let runs = InlineParser.parse("Because $c$ is **enormous**, ==small errors== grow. See [the BIPM](https://bipm.org).")
        XCTAssertEqual(runs.map(\.kind), [.text, .math, .text, .text, .text, .text, .text])
        XCTAssertEqual(runs[1].text, "c")
        XCTAssertTrue(runs[3].bold)
        XCTAssertTrue(runs[5].mark)
        XCTAssertTrue(runs.last!.text.hasSuffix("See the BIPM."))
    }

    func testTeXToUnicode() {
        XCTAssertEqual(TeXInline.unicode("3\\times10^{-9}"), "3×10⁻⁹")
        XCTAssertEqual(TeXInline.unicode("\\Delta d = c\\,\\Delta t"), "Δd = c\u{2009}Δt")
        XCTAssertEqual(TeXInline.unicode("299\\,792\\,458"), "299\u{2009}792\u{2009}458")
        XCTAssertEqual(TeXInline.unicode("0.3\\ \\mathrm{m}"), "0.3\u{2009}m")
        XCTAssertEqual(TeXInline.unicode("v=c/n"), "v=c/n")
    }
}

final class ExpressionTests: XCTestCase {
    func ev(_ s: String, _ env: [String: Double] = [:]) throws -> Double { try Expr.parse(s).eval(env) }

    func testGrammar() throws {
        XCTAssertEqual(try ev("2+3*4^2"), 50)
        XCTAssertEqual(try ev("-2^2"), -4)
        XCTAssertEqual(try ev("2^-1"), 0.5)
        XCTAssertEqual(try ev("2**3"), 8)
        XCTAssertEqual(try ev("max(1, 7, 3)"), 7)
        XCTAssertThrowsError(try Expr.parse("constructor(1)"))
        XCTAssertThrowsError(try Expr.parse("alert(1);"))
        XCTAssertTrue(try ev("constructor").isNaN)
    }

    /// Same physics checks as the web reader's model tests.
    func testDilationModel() throws {
        var env: [String: Double] = ["h": 2.02e7]
        for (n, e) in [("r", "R_E + h"), ("v", "sqrt(GM/r)"), ("sr", "-v^2/(2*c^2)*DAY*1e6"), ("gr", "GM/c^2*(1/R_E - 1/r)*DAY*1e6")] {
            env[n] = try Expr.parse(e).eval(env)
        }
        XCTAssertEqual(env["sr"]!, -7.211, accuracy: 0.01)
        XCTAssertEqual(env["gr"]!, 45.724, accuracy: 0.01)
        XCTAssertEqual(env["sr"]! + env["gr"]!, 38.514, accuracy: 0.01)
    }

    func testIonosphereRecovery() throws {
        var env: [String: Double] = ["TEC": 1]
        for (n, e) in [("K", "40.3*TEC*1e16"), ("I1", "K/f_L1^2"), ("I2", "K/f_L2^2")] { env[n] = try Expr.parse(e).eval(env) }
        XCTAssertEqual(env["I1"]!, 0.16237, accuracy: 1e-4)
        XCTAssertEqual(try ev("(I2 - I1)*f_L2^2/(f_L1^2 - f_L2^2)", env), env["I1"]!, accuracy: 1e-12)
    }

    func testModelSpecsParse() throws {
        let dir = Fixture.course.appendingPathComponent("models")
        for name in ["light-time", "clock-drift", "dilation", "ionosphere"] {
            let data = try Data(contentsOf: dir.appendingPathComponent(name + ".json"))
            let obj = try JSONSerialization.jsonObject(with: data) as! [String: Any]
            for o in obj["outputs"] as! [[String: Any]] { XCTAssertNoThrow(try Expr.parse(o["expr"] as! String), name) }
            for d in (obj["defs"] as? [[String]]) ?? [] { XCTAssertNoThrow(try Expr.parse(d[1]), name) }
        }
    }
}

final class QuantityTests: XCTestCase {
    /// Expected strings match the web reader's fmtQ output.
    func testFormatting() {
        XCTAssertEqual(Quantity.format(1e-7, unit: "s"), "100 ns")
        XCTAssertEqual(Quantity.format(30, unit: "m"), "30 m")
        XCTAssertEqual(Quantity.format(0.3, unit: "m"), "30 cm")
        XCTAssertEqual(Quantity.format(11600, unit: "m"), "11.6 km")
        XCTAssertEqual(Quantity.format(86400, unit: "s"), "24 h")
        XCTAssertEqual(Quantity.format(4.46e-10), "4.46 × 10⁻¹⁰")
        XCTAssertEqual(Quantity.format(1575.42e6, unit: "Hz", digits: 4), "1.575 GHz")
        XCTAssertEqual(Quantity.format(-7.21, unit: "μs/day"), "−7.21 μs/day")
        XCTAssertEqual(Quantity.format(3873.6, unit: "m/s"), "3,870 m/s")
    }
}

import SwiftUI
import CourseKit

/// Prose → AttributedString. Inline maths is converted to Unicode for v0.1 (plan §5.1); highlights use the pastel yellow tint.
enum Prose {
    static func attributed(_ s: String, style: ReadingStyle, scale: CGFloat = 1, bold forceBold: Bool = false) -> AttributedString {
        var out = AttributedString()
        let size = style.size * scale
        for run in InlineParser.parse(s) {
            var piece: AttributedString
            var italic = run.italic
            if run.kind == .math {
                let u = TeXInline.unicode(run.text)
                piece = AttributedString(u)
                // Single symbols and letter-only expressions read as variables: italic, as in TeX.
                italic = !u.contains(where: \.isNumber) && u.contains(where: \.isLetter) && u.count <= 3
            } else {
                piece = AttributedString(run.text)
            }
            piece[AttributeScopes.SwiftUIAttributes.FontAttribute.self] = Typeface.serif(size, bold: run.bold || forceBold, italic: italic)
            if run.mark {
                piece[AttributeScopes.SwiftUIAttributes.BackgroundColorAttribute.self] = style.theme.tint(.yellow)
            }
            out.append(piece)
        }
        return out
    }
}

struct ProseText: View {
    @Environment(\.reading) private var r
    let text: String
    var scale: CGFloat = 1

    var body: some View {
        Text(Prose.attributed(text, style: r, scale: scale))
            .lineSpacing(r.size * scale * 0.28)
            .fixedSize(horizontal: false, vertical: true)
            .frame(maxWidth: .infinity, alignment: .leading)
    }
}

struct BlockView: View {
    @Environment(\.reading) private var r
    let block: Block
    var number: String? = nil

    var body: some View {
        switch block {
        case .heading(let level, let text):
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                if let number { Text(number).monospacedDigit() }
                Text(text)
            }
            .font(Typeface.serif(r.size * (level == 2 ? 1.3 : 1.1), bold: true))
            .padding(.top, level == 2 ? 18 : 8)
            .accessibilityAddTraits(.isHeader)

        case .paragraph(let text):
            ProseText(text: text)

        case .theorem(let kind, let n, let title, let body):
            TheoremView(kind: kind, number: n, title: title, content: body)

        case .displayMath(let latex, let n):
            DisplayMath(latex: latex, number: n)

        case .list(let ordered, let items):
            VStack(alignment: .leading, spacing: 8) {
                ForEach(Array(items.enumerated()), id: \.offset) { i, item in
                    HStack(alignment: .firstTextBaseline, spacing: 10) {
                        Text(ordered ? "\(i + 1)." : "•")
                            .font(Typeface.serif(r.size))
                            .foregroundStyle(r.theme.ink2)
                            .frame(minWidth: 16, alignment: .trailing)
                        ProseText(text: item)
                    }
                }
            }

        case .table(let header, let rows):
            TableView(header: header, rows: rows)

        case .quiz(let quiz):
            QuizView(quiz: quiz)

        case .steps(let steps):
            StepsView(steps: steps)

        case .widget(let name):
            LabCard(name: name)

        case .explore(let json):
            LabCard(name: Self.exploreName(json))

        case .code(let code):
            ScrollView(.horizontal, showsIndicators: false) {
                Text(code)
                    .font(.system(size: r.size * 0.78, design: .monospaced))
                    .padding(12)
            }
            .background(r.theme.panel, in: .rect(cornerRadius: 10))

        case .rule:
            Rectangle().fill(r.theme.rule).frame(height: 1).padding(.vertical, 8)
        }
    }

    static func exploreName(_ json: String) -> String {
        guard let data = json.data(using: .utf8),
              let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return "explorer" }
        return (obj["title"] as? String) ?? (obj["model"] as? String) ?? "explorer"
    }
}

/// amsthm-style environment: bold label, optional title, pastel tint by kind.
struct TheoremView: View {
    @Environment(\.reading) private var r
    let kind: TheoremKind
    let number: Int?
    let title: String?
    let content: [Block]

    var body: some View {
        let tint = r.theme.tint(for: kind)
        VStack(alignment: .leading, spacing: 10) {
            HStack(alignment: .firstTextBaseline, spacing: 6) {
                Text(kind.label + (number.map { " \($0)" } ?? ""))
                    .font(Typeface.serif(r.size, bold: true))
                if let title {
                    Text("(\(title))").font(Typeface.serif(r.size))
                }
            }
            ForEach(Array(content.enumerated()), id: \.offset) { _, b in
                BlockView(block: b)
            }
        }
        .padding(.horizontal, tint == nil ? 0 : 14)
        .padding(.vertical, tint == nil ? 0 : 12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(tint ?? .clear, in: .rect(cornerRadius: 12))
        .accessibilityElement(children: .contain)
    }
}

struct DisplayMath: View {
    @Environment(\.reading) private var r
    let latex: String
    let number: Int?

    var body: some View {
        HStack(spacing: 8) {
            ViewThatFits(in: .horizontal) {
                MathView(latex: latex, fontSize: r.size * 1.1, color: r.theme.ink)
                    .frame(maxWidth: .infinity)
                ScrollView(.horizontal, showsIndicators: false) {
                    MathView(latex: latex, fontSize: r.size * 1.1, color: r.theme.ink)
                }
            }
            if let number {
                Text("(\(number))")
                    .font(Typeface.serif(r.size))
                    .foregroundStyle(r.theme.ink2)
            }
        }
        .padding(.vertical, 4)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(TeXInline.unicode(latex) + (number.map { ", equation \($0)" } ?? ""))
    }
}

struct TableView: View {
    @Environment(\.reading) private var r
    let header: [String]
    let rows: [[String]]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            Grid(alignment: .leading, horizontalSpacing: 18, verticalSpacing: 8) {
                GridRow {
                    ForEach(Array(header.enumerated()), id: \.offset) { _, h in
                        Text(Prose.attributed(h, style: r, scale: 0.86, bold: true))
                    }
                }
                Rectangle().fill(r.theme.ink2).frame(height: 0.8).gridCellUnsizedAxes(.horizontal)
                ForEach(Array(rows.enumerated()), id: \.offset) { _, row in
                    GridRow {
                        ForEach(Array(row.enumerated()), id: \.offset) { _, cell in
                            Text(Prose.attributed(cell, style: r, scale: 0.86))
                                .fixedSize(horizontal: false, vertical: true)
                        }
                    }
                }
                Rectangle().fill(r.theme.ink2).frame(height: 0.8).gridCellUnsizedAxes(.horizontal)
            }
            .padding(.vertical, 4)
        }
    }
}

/// Check-yourself question. The answer stays hidden until the reader commits to an option.
struct QuizView: View {
    @Environment(\.reading) private var r
    let quiz: Quiz
    @State private var chosen: Int?

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label("Check yourself", systemImage: "questionmark.circle")
                .font(.caption.weight(.semibold))
                .textCase(.uppercase)
                .foregroundStyle(r.theme.ink3)
            ProseText(text: quiz.question)
            ForEach(Array(quiz.options.enumerated()), id: \.offset) { i, option in
                Button {
                    withAnimation(.snappy) { chosen = i }
                } label: {
                    HStack(alignment: .firstTextBaseline, spacing: 10) {
                        Text(["a", "b", "c", "d", "e", "f", "g", "h"][min(i, 7)] + ")")
                            .font(Typeface.serif(r.size, italic: true))
                            .foregroundStyle(r.theme.ink2)
                        ProseText(text: option, scale: 0.95)
                        if let chosen, i == quiz.correct || i == chosen {
                            Image(systemName: i == quiz.correct ? "checkmark" : "xmark")
                                .font(.subheadline.weight(.semibold))
                        }
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .background(fill(i), in: .rect(cornerRadius: 10))
                    .overlay { RoundedRectangle(cornerRadius: 10).strokeBorder(r.theme.rule, lineWidth: chosen == nil ? 1 : 0) }
                    .contentShape(.rect)
                }
                .buttonStyle(.plain)
                .disabled(chosen != nil)
            }
            if let chosen {
                VStack(alignment: .leading, spacing: 6) {
                    Text(chosen == quiz.correct ? "Right." : "Not quite.")
                        .font(Typeface.serif(r.size, bold: true))
                    ProseText(text: quiz.explanation, scale: 0.95)
                    Button("Try again") { withAnimation(.snappy) { self.chosen = nil } }
                        .font(.subheadline)
                        .padding(.top, 2)
                }
                .transition(.opacity)
            }
        }
        .padding(14)
        .background(r.theme.panel.opacity(0.6), in: .rect(cornerRadius: 14))
    }

    private func fill(_ i: Int) -> Color {
        guard let chosen else { return .clear }
        if i == quiz.correct { return r.theme.tint(.green) }
        if i == chosen { return r.theme.tint(.rose) }
        return .clear
    }
}

/// Worked solution revealed one step at a time, so the reader can attempt each step first.
struct StepsView: View {
    @Environment(\.reading) private var r
    let steps: Steps
    @State private var shown = 0

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Label(steps.title.isEmpty ? "Worked solution" : steps.title, systemImage: "list.number")
                .font(.caption.weight(.semibold))
                .textCase(.uppercase)
                .foregroundStyle(r.theme.ink3)
            ForEach(0..<min(shown, steps.steps.count), id: \.self) { i in
                HStack(alignment: .firstTextBaseline, spacing: 10) {
                    Text("\(i + 1)")
                        .font(Typeface.serif(r.size, bold: true))
                        .foregroundStyle(r.theme.ink2)
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(Array(steps.steps[i].enumerated()), id: \.offset) { _, b in BlockView(block: b) }
                    }
                }
                .transition(.opacity.combined(with: .move(edge: .top)))
            }
            HStack {
                if shown < steps.steps.count {
                    Button(shown == 0 ? "Show step 1" : "Next step") { withAnimation(.snappy) { shown += 1 } }
                        .buttonStyle(.bordered)
                    Text("\(shown) of \(steps.steps.count)")
                        .font(.caption)
                        .monospacedDigit()
                        .foregroundStyle(r.theme.ink3)
                } else {
                    Button("Hide steps") { withAnimation(.snappy) { shown = 0 } }
                        .buttonStyle(.bordered)
                }
            }
            .tint(r.theme.ink2)
        }
        .padding(14)
        .background(r.theme.panel.opacity(0.6), in: .rect(cornerRadius: 14))
    }
}

/// Interactive models open in the Lab (v0.3). Until then the card names the model and where it lives.
struct LabCard: View {
    @Environment(\.reading) private var r
    let name: String

    var body: some View {
        HStack(spacing: 14) {
            Image(systemName: "testtube.2")
                .font(.title3)
                .frame(width: 40, height: 40)
                .background(r.theme.tint(.blue), in: .circle)
            VStack(alignment: .leading, spacing: 2) {
                Text(Self.title(name)).font(Typeface.serif(r.size, bold: true))
                Text("Interactive model · opens in the Lab in v0.3").font(.footnote).foregroundStyle(r.theme.ink3)
            }
            Spacer(minLength: 0)
        }
        .padding(14)
        .background(r.theme.panel.opacity(0.6), in: .rect(cornerRadius: 14))
        .accessibilityElement(children: .combine)
    }

    static func title(_ slug: String) -> String {
        let s = slug.replacingOccurrences(of: "-", with: " ")
        return s.prefix(1).uppercased() + s.dropFirst()
    }
}

struct ExercisesView: View {
    @Environment(\.reading) private var r
    let questions: [Question]
    let number: Int

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text("\(number)").monospacedDigit()
                Text("Exercises")
            }
            .font(Typeface.serif(r.size * 1.3, bold: true))
            .padding(.top, 18)
            .accessibilityAddTraits(.isHeader)
            Text("Answering and grading arrive in v0.2. Attempt each on paper first.")
                .font(.footnote)
                .foregroundStyle(r.theme.ink3)
            ForEach(Array(questions.enumerated()), id: \.element.id) { i, q in
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 8) {
                        Text("Exercise \(i + 1)").font(Typeface.serif(r.size, bold: true))
                        Text(q.kind.capitalized)
                            .font(.caption.weight(.semibold))
                            .padding(.horizontal, 7).padding(.vertical, 2)
                            .background(r.theme.tint(forKind: q.kind), in: .capsule)
                    }
                    ProseText(text: q.text)
                }
            }
        }
    }
}

struct ReferencesView: View {
    @Environment(\.reading) private var r
    let references: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("References")
                .font(Typeface.serif(r.size * 1.3, bold: true))
                .padding(.top, 18)
                .accessibilityAddTraits(.isHeader)
            ForEach(Array(references.enumerated()), id: \.offset) { i, ref in
                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text("[\(i + 1)]").font(Typeface.serif(r.size * 0.86)).foregroundStyle(r.theme.ink2)
                    ProseText(text: ref, scale: 0.86)
                }
            }
        }
    }
}

import SwiftUI
import BookKit

/// Ask about a passage. Claude is told where the reader is and to say nothing from beyond it.
struct AskSheet: View {
    @Environment(\.dismiss) private var dismiss
    let title: String
    let author: String
    let location: String
    let passage: String
    @State private var question = ""
    @State private var answer: String?
    @State private var busy = false
    @State private var error: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text(passage)
                        .font(Typeface.serif(16, italic: true))
                        .padding(14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(.secondary.opacity(0.12), in: .rect(cornerRadius: 12))
                    FlowLayout {
                        ForEach(["Explain this", "Who is this?", "What does this word mean?", "Why does this matter?"], id: \.self) { q in
                            Button(q) { question = q; send() }
                                .font(.subheadline)
                                .buttonStyle(.bordered)
                        }
                    }
                    HStack {
                        TextField("Ask about this passage", text: $question, axis: .vertical)
                            .textFieldStyle(.roundedBorder)
                            .onSubmit(send)
                        Button(action: send) { Image(systemName: "arrow.up.circle.fill").font(.title2) }
                            .disabled(question.isEmpty || busy)
                    }
                    if busy { ProgressView().frame(maxWidth: .infinity) }
                    if let error { Text(error).font(.footnote).foregroundStyle(.red) }
                    if let answer {
                        Text(answer).font(Typeface.serif(17)).textSelection(.enabled)
                    }
                    Text("Claude is asked to use only what you've read so far (\(location)).")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .padding(20)
            }
            .navigationTitle("Ask")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
    }

    private func send() {
        let q = question.trimmingCharacters(in: .whitespaces)
        guard !q.isEmpty else { return }
        busy = true; error = nil; answer = nil
        let system = Claude.bookSystem(title: title, author: author, upTo: location)
        let user = "Passage:\n\(passage)\n\nQuestion: \(q)"
        Task {
            do { answer = try await Claude.ask(system: system, user: user) } catch { self.error = error.localizedDescription }
            busy = false
        }
    }
}

/// Wraps buttons onto as many rows as needed.
struct FlowLayout: Layout {
    var spacing: CGFloat = 8
    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let w = proposal.width ?? 320
        var x: CGFloat = 0, y: CGFloat = 0, rowH: CGFloat = 0
        for v in subviews {
            let s = v.sizeThatFits(.unspecified)
            if x + s.width > w, x > 0 { x = 0; y += rowH + spacing; rowH = 0 }
            x += s.width + spacing; rowH = max(rowH, s.height)
        }
        return CGSize(width: w, height: y + rowH)
    }
    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var x = bounds.minX, y = bounds.minY, rowH: CGFloat = 0
        for v in subviews {
            let s = v.sizeThatFits(.unspecified)
            if x + s.width > bounds.maxX, x > bounds.minX { x = bounds.minX; y += rowH + spacing; rowH = 0 }
            v.place(at: CGPoint(x: x, y: y), proposal: .unspecified)
            x += s.width + spacing; rowH = max(rowH, s.height)
        }
    }
}

/// Settings row: the key is entered once and shown only as a status afterwards.
struct ClaudeKeySection: View {
    @AppStorage("claudeModel") private var model = "claude-sonnet-5-5"
    @State private var draft = ""
    @State private var hasKey = ClaudeKey.value != nil

    var body: some View {
        Section {
            if hasKey {
                LabeledContent("API key", value: "Saved in Keychain")
                Button("Remove key", role: .destructive) { ClaudeKey.value = nil; hasKey = false }
            } else {
                SecureField("Paste your Claude API key", text: $draft)
                    .textContentType(.password)
                    .autocorrectionDisabled()
                Button("Save key") { ClaudeKey.value = draft; draft = ""; hasKey = ClaudeKey.value != nil }
                    .disabled(draft.isEmpty)
            }
            Picker("Model", selection: $model) {
                Text("Sonnet 5.5").tag("claude-sonnet-5-5")
                Text("Haiku 5.5").tag("claude-haiku-5-5")
                Text("Opus 5.5").tag("claude-opus-5-5")
            }
        } header: {
            Text("Ask Claude")
        } footer: {
            Text("Used for Ask on selected passages. The key lives only in this iPhone’s Keychain and is sent only to api.anthropic.com.")
        }
    }
}

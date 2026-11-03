import SwiftUI

struct ThemeSwatches: View {
    @Binding var themeRaw: String

    var body: some View {
        HStack(spacing: 0) {
            ForEach(ReadingTheme.allCases) { t in
                let on = themeRaw == t.rawValue
                Button { withAnimation(.snappy) { themeRaw = t.rawValue } } label: {
                    VStack(spacing: 6) {
                        Text("Aa")
                            .font(Typeface.serif(17))
                            .foregroundStyle(t.ink)
                            .frame(width: 48, height: 48)
                            .background(t.background, in: .circle)
                            .overlay {
                                Circle().strokeBorder(on ? Color.accentColor : Color.secondary.opacity(0.35), lineWidth: on ? 2.5 : 0.5)
                            }
                        Text(t.label).font(.caption2).foregroundStyle(.secondary)
                    }
                    .frame(maxWidth: .infinity)
                    .contentShape(.rect)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("\(t.label) theme")
                .accessibilityAddTraits(on ? .isSelected : [])
            }
        }
    }
}

struct TextSizeControl: View {
    @Binding var textSize: Double

    var body: some View {
        HStack(spacing: 12) {
            Button { withAnimation(.snappy) { textSize = max(15, textSize - 1) } } label: {
                Text("A").font(Typeface.serif(15)).frame(width: 32, height: 32).contentShape(.rect)
            }
            .accessibilityLabel("Smaller text")
            Slider(value: $textSize, in: 15...24, step: 0.5)
            Button { withAnimation(.snappy) { textSize = min(24, textSize + 1) } } label: {
                Text("A").font(Typeface.serif(24)).frame(width: 32, height: 32).contentShape(.rect)
            }
            .accessibilityLabel("Larger text")
        }
        .buttonStyle(.plain)
    }
}

struct AppSettingsView: View {
    @AppStorage("libraryStyle") private var libraryStyle = "sky"
    @AppStorage("theme") private var themeRaw = ReadingTheme.sepia.rawValue
    @AppStorage("textSize") private var textSize = 18.0
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Picker("Library", selection: $libraryStyle) {
                        Text("Night sky").tag("sky")
                        Text("Posters").tag("poster")
                    }
                    .pickerStyle(.segmented)
                } header: {
                    Text("Library")
                } footer: {
                    Text("Night sky gives each course the whole screen. Posters stack courses as cards.")
                }
                Section("Reading") {
                    ThemeSwatches(themeRaw: $themeRaw).padding(.vertical, 4)
                    TextSizeControl(textSize: $textSize)
                }
                Section {
                    LabeledContent("Version", value: Bundle.main.infoDictionary?["CFBundleShortVersionString"] as? String ?? "–")
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } }
            }
        }
    }
}

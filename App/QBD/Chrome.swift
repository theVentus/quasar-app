import SwiftUI

/// Section name and a thin progress line, in a glass capsule.
struct ProgressPill: View {
    @Environment(\.accent) private var accent
    let section: String
    let progress: Double
    let compact: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(spacing: 6) {
                Text(section).font(.footnote.weight(.semibold)).lineLimit(1)
                Spacer(minLength: 6)
                Text("\(Int((progress * 100).rounded()))%")
                    .font(.caption.weight(.medium))
                    .monospacedDigit()
                    .opacity(0.6)
            }
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Capsule().fill(Color.primary.opacity(0.12))
                    Capsule().fill(accent.pastel).frame(width: max(3, g.size.width * progress))
                }
            }
            .frame(height: 3)
        }
        .padding(.horizontal, 18)
        .frame(height: compact ? 42 : 50)
        .frame(maxWidth: .infinity)
        .contentShape(.capsule)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("\(section), \(Int(progress * 100)) percent read")
        .accessibilityAddTraits(.isButton)
    }
}

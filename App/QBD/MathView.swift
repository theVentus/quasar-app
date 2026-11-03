import SwiftUI
import UIKit
import SwiftMath

/// Display maths typeset with SwiftMath (Latin Modern, the OpenType successor of Computer Modern).
struct MathView: UIViewRepresentable {
    let latex: String
    let fontSize: CGFloat
    let color: Color

    func makeUIView(context: Context) -> MTMathUILabel {
        let label = MTMathUILabel()
        label.labelMode = .display
        label.textAlignment = .center
        label.backgroundColor = .clear
        label.setContentHuggingPriority(.required, for: .horizontal)
        label.setContentHuggingPriority(.required, for: .vertical)
        return label
    }

    func updateUIView(_ label: MTMathUILabel, context: Context) {
        label.latex = Self.clean(latex)
        label.fontSize = fontSize
        label.textColor = UIColor(color)
        label.invalidateIntrinsicContentSize()
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: MTMathUILabel, context: Context) -> CGSize? {
        uiView.intrinsicContentSize
    }

    /// SwiftMath has no `\ ` control space; a thin space keeps spacing close.
    static func clean(_ s: String) -> String {
        s.replacingOccurrences(of: "\\ ", with: "\\,")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }
}

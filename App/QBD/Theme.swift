import SwiftUI
import CourseKit

/// Reading themes shared with the web reader. They colour the reading surface only; system chrome stays native glass.
enum ReadingTheme: String, CaseIterable, Identifiable {
    case paper, sepia, dusk, night
    var id: String { rawValue }
    var label: String { rawValue.capitalized }
    var isDark: Bool { self == .dusk || self == .night }
    var scheme: ColorScheme { isDark ? .dark : .light }

    var background: Color {
        switch self { case .paper: Color(hex: 0xFFFFFF); case .sepia: Color(hex: 0xF2E8D3); case .dusk, .night: Color(hex: 0x000000) }
    }
    var ink: Color {
        switch self { case .paper: Color(hex: 0x111111); case .sepia: Color(hex: 0x33281B); case .dusk: Color(hex: 0xE9DDC4); case .night: Color(hex: 0xF2F2F2) }
    }
    var ink2: Color {
        switch self { case .paper: Color(hex: 0x4A4A4A); case .sepia: Color(hex: 0x5F4F3B); case .dusk: Color(hex: 0xB8A98C); case .night: Color(hex: 0xA3A3A3) }
    }
    var ink3: Color {
        switch self { case .paper: Color(hex: 0x858585); case .sepia: Color(hex: 0x8B7B62); case .dusk: Color(hex: 0x7F735C); case .night: Color(hex: 0x6B6B6B) }
    }
    var rule: Color {
        switch self { case .paper: Color(hex: 0xE0E0E0); case .sepia: Color(hex: 0xD6C6A6); case .dusk: Color(hex: 0x2C261C); case .night: Color(hex: 0x262626) }
    }
    var panel: Color {
        switch self { case .paper: Color(hex: 0xF3F3F3); case .sepia: Color(hex: 0xE7DBC1); case .dusk: Color(hex: 0x15120C); case .night: Color(hex: 0x121212) }
    }

    /// Pastel highlighter tints, as on the web: blue definitions, sage examples, yellow key ideas, rose misconceptions, lilac remarks.
    enum Hue { case yellow, blue, green, rose, lilac, sand }
    func tint(_ hue: Hue) -> Color {
        let light: [Hue: (Double, Double, Double, Double)] = [.yellow: (246, 200, 60, 0.32), .blue: (96, 140, 196, 0.15), .green: (96, 156, 104, 0.15),
                                                             .rose: (214, 112, 96, 0.14), .lilac: (138, 116, 190, 0.14), .sand: (150, 120, 70, 0.10)]
        let dark: [Hue: (Double, Double, Double, Double)] = [.yellow: (240, 196, 80, 0.18), .blue: (120, 165, 225, 0.15), .green: (130, 190, 135, 0.13),
                                                            .rose: (235, 135, 118, 0.14), .lilac: (172, 150, 232, 0.15), .sand: (210, 180, 130, 0.10)]
        let t = (isDark ? dark : light)[hue]!
        return Color(.sRGB, red: t.0 / 255, green: t.1 / 255, blue: t.2 / 255, opacity: t.3)
    }

    func tint(for kind: TheoremKind) -> Color? {
        switch kind {
        case .definition, .theorem: tint(.blue)
        case .example: tint(.green)
        case .keyIdea: tint(.yellow)
        case .misconception, .warning: tint(.rose)
        case .remark, .note, .intuition: tint(.lilac)
        case .check: tint(.sand)
        case .exercise: nil
        }
    }

    func tint(forKind kind: String) -> Color {
        switch kind { case "explain": tint(.blue); case "calculate": tint(.yellow); case "predict": tint(.lilac); case "apply": tint(.green); default: tint(.sand) }
    }
}

extension Color {
    init(hex: UInt32) {
        self.init(.sRGB, red: Double((hex >> 16) & 0xFF) / 255, green: Double((hex >> 8) & 0xFF) / 255, blue: Double(hex & 0xFF) / 255, opacity: 1)
    }
}

/// Computer Modern (CMU Serif) is bundled; it is the course's default face.
enum Typeface {
    static func serif(_ size: CGFloat, bold: Bool = false, italic: Bool = false) -> Font {
        let name = switch (bold, italic) {
        case (false, false): "CMUSerif-Roman"
        case (false, true): "CMUSerif-Italic"
        case (true, false): "CMUSerif-Bold"
        case (true, true): "CMUSerif-BoldItalic"
        }
        return .custom(name, size: size, relativeTo: .body)
    }
}

struct ReadingStyle {
    var theme: ReadingTheme = .sepia
    var size: CGFloat = 18
}

extension EnvironmentValues {
    @Entry var reading = ReadingStyle()
}

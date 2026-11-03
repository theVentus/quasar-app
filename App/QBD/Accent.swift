import SwiftUI
import UIKit
import CourseKit
import BookKit

/// A course's pastel accent. Pastels fill (prominent buttons, selected chips, progress); the deeper shade carries
/// text and icons on light surfaces, where a pastel would be too faint to read.
struct CourseAccent {
    let pastel: Color
    let onPastel: Color
    /// System tint: the deep shade in light appearance, the pastel in dark.
    let tint: Color

    init(_ theme: CourseManifest.Theme?) {
        self.init(accent: theme?.accent, deep: theme?.accentDeep, on: theme?.onAccent)
    }

    init(_ theme: BookManifest.Theme?) {
        self.init(accent: theme?.accent, deep: theme?.accentDeep, on: theme?.onAccent)
    }

    init(accent: String?, deep: String?, on: String?) {
        let p = Self.hex(accent) ?? 0xA9C4F5
        let d = Self.hex(deep) ?? 0x41609A
        let on = Self.hex(on) ?? 0x132341
        pastel = Color(hex: p)
        onPastel = Color(hex: on)
        tint = Color(uiColor: UIColor { traits in
            UIColor(rgb: traits.userInterfaceStyle == .dark ? p : d)
        })
    }

    static let standard = CourseAccent(accent: nil, deep: nil, on: nil)

    static func hex(_ s: String?) -> UInt32? {
        guard var s else { return nil }
        if s.hasPrefix("#") { s.removeFirst() }
        return UInt32(s, radix: 16)
    }
}

extension UIColor {
    convenience init(rgb: UInt32) {
        self.init(red: CGFloat((rgb >> 16) & 0xFF) / 255, green: CGFloat((rgb >> 8) & 0xFF) / 255, blue: CGFloat(rgb & 0xFF) / 255, alpha: 1)
    }
}

extension EnvironmentValues {
    @Entry var accent = CourseAccent.standard
}

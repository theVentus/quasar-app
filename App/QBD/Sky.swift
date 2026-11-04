import SwiftUI

/// A deep-sky backdrop: wavefronts leaving a quasar and sweeping past a blue dot, which brightens as each one arrives.
/// Glass placed over it has real structure to refract. Static when Reduce Motion is on.
struct SkyView: View {
    var animated = true
    var quasar = UnitPoint(x: 0.82, y: 0.14)
    var earth = UnitPoint(x: 0.24, y: 0.62)
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        let live = animated && !reduceMotion
        TimelineView(.animation(minimumInterval: 1.0 / 30, paused: !live)) { timeline in
            let t = live ? timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 100_000) : 40
            Canvas { ctx, size in
                SkyPainter.draw(&ctx, size: size, t: t, quasar: quasar, earth: earth)
            }
        }
        .accessibilityHidden(true)
    }
}

enum SkyPainter {
    struct Star { var x, y, r, phase: Double }

    /// Deterministic star field (SplitMix64), identical on every launch.
    static let stars: [Star] = {
        var seed: UInt64 = 0x2545F4914F6CDD1D
        func next() -> Double {
            seed &+= 0x9E3779B97F4A7C15
            var z = seed
            z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
            z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
            z = z ^ (z >> 31)
            return Double(z >> 11) / 9_007_199_254_740_992.0
        }
        return (0..<170).map { _ in Star(x: next(), y: next(), r: 0.35 + 1.3 * pow(next(), 4), phase: next() * 2 * .pi) }
    }()

    static func draw(_ ctx: inout GraphicsContext, size: CGSize, t: Double, quasar: UnitPoint, earth: UnitPoint) {
        let w = size.width, h = size.height
        ctx.fill(Path(CGRect(origin: .zero, size: size)),
                 with: .linearGradient(Gradient(colors: [Color(hex: 0x04050A), Color(hex: 0x0B1226), Color(hex: 0x05070D)]),
                                       startPoint: .zero, endPoint: CGPoint(x: w * 0.35, y: h)))

        for s in stars {
            let a = 0.2 + 0.5 * (0.5 + 0.5 * sin(t * 0.9 + s.phase))
            ctx.fill(Path(ellipseIn: CGRect(x: s.x * w - s.r, y: s.y * h - s.r, width: 2 * s.r, height: 2 * s.r)),
                     with: .color(.white.opacity(a)))
        }

        let q = CGPoint(x: quasar.x * w, y: quasar.y * h)
        let e = CGPoint(x: earth.x * w, y: earth.y * h)
        let d = hypot(e.x - q.x, e.y - q.y)

        // Wavefronts
        let spacing = 64.0, speed = 22.0
        let maxR = hypot(w, h) * 1.05
        let count = Int(maxR / spacing) + 1
        let span = Double(count) * spacing
        var nearest = Double.infinity
        for k in 0..<count {
            let r = (t * speed + Double(k) * spacing).truncatingRemainder(dividingBy: span)
            nearest = min(nearest, abs(r - d))
            let alpha = 0.3 * max(0, 1 - r / maxR) * min(1, r / 40)
            ctx.stroke(Path(ellipseIn: CGRect(x: q.x - r, y: q.y - r, width: 2 * r, height: 2 * r)),
                       with: .color(Color(hex: 0xA9C2F0).opacity(alpha)), lineWidth: 0.9)
        }

        // Quasar: glow, jet, core
        ctx.fill(Path(ellipseIn: CGRect(x: q.x - 72, y: q.y - 72, width: 144, height: 144)),
                 with: .radialGradient(Gradient(colors: [Color(hex: 0xFFD99A).opacity(0.42), .clear]), center: q, startRadius: 0, endRadius: 72))
        let a = CGPoint(x: q.x - 50, y: q.y + 32), b = CGPoint(x: q.x + 50, y: q.y - 32)
        var jet = Path(); jet.move(to: a); jet.addLine(to: b)
        ctx.stroke(jet, with: .linearGradient(Gradient(colors: [.clear, Color(hex: 0xFFE7C2).opacity(0.55), .clear]), startPoint: a, endPoint: b), lineWidth: 1.2)
        ctx.fill(Path(ellipseIn: CGRect(x: q.x - 4, y: q.y - 4, width: 8, height: 8)), with: .color(Color(hex: 0xFFF3DC)))

        // Blue dot, pulsing as a wavefront passes
        let pulse = exp(-pow(nearest / 14, 2))
        let glowR = 46 + 16 * pulse
        ctx.fill(Path(ellipseIn: CGRect(x: e.x - glowR, y: e.y - glowR, width: 2 * glowR, height: 2 * glowR)),
                 with: .radialGradient(Gradient(colors: [Color(hex: 0x3A84FF).opacity(0.32 + 0.28 * pulse), .clear]), center: e, startRadius: 0, endRadius: glowR))
        let dot = CGRect(x: e.x - 13, y: e.y - 13, width: 26, height: 26)
        ctx.fill(Path(ellipseIn: dot), with: .color(Color(hex: 0x3A84FF)))
        ctx.fill(Path(ellipseIn: dot), with: .radialGradient(Gradient(colors: [.white.opacity(0.38), .clear]),
                                                              center: CGPoint(x: e.x - 5, y: e.y - 5), startRadius: 0, endRadius: 16))
    }
}

enum Motion {
    /// Glass morphs. `-slowmo YES` stretches them so CI screenshots can catch the transition.
    static var morph: Animation { LaunchState.slowmo ? .bouncy(duration: 4) : .bouncy(duration: 0.5) }
}

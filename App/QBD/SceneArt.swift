import SwiftUI
import BookKit

/// Procedural chapter art, chosen by a chapter's setting and coloured by its palette. Layers: sky gradient, a
/// celestial body or light source, a horizon or interior silhouette, and drifting particles. Animated slowly.
struct SceneArt: View {
    let setting: String
    let palette: [Color]
    var seed: Int = 1
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    enum Family { case space, interior, forest, open, water, built }

    static func family(_ setting: String) -> Family {
        switch setting {
        case "space", "orbit", "station": .space
        case "ship-interior", "cryo", "lab": .interior
        case "jungle", "forest-canopy", "nest": .forest
        case "ocean", "river", "storm": .water
        case "city", "temple", "battle", "underground", "ruins": .built
        default: .open
        }
    }

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30, paused: reduceMotion)) { tl in
            let t = reduceMotion ? 20 : tl.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 100_000)
            Canvas { ctx, size in
                ScenePainter(setting: setting, family: Self.family(setting), palette: palette, seed: seed).draw(&ctx, size, t)
            }
        }
        .accessibilityHidden(true)
    }
}

struct ScenePainter {
    let setting: String
    let family: SceneArt.Family
    let palette: [Color]
    let seed: Int

    private var c0: Color { palette.first ?? Color(hex: 0x0B1020) }
    private var c1: Color { palette.count > 1 ? palette[1] : Color(hex: 0x3E6E9E) }
    private var c2: Color { palette.count > 2 ? palette[2] : Color(hex: 0xE8C170) }

    /// Deterministic noise per seed.
    private func rand(_ i: Int) -> Double {
        var z = UInt64(truncatingIfNeeded: i &* 0x9E3779B97F4A7C15 &+ seed &* 0x632BE59BD9B4E019)
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9
        z = (z ^ (z >> 27)) &* 0x94D049BB133111EB
        z ^= z >> 31
        return Double(z >> 11) / 9_007_199_254_740_992.0
    }

    func draw(_ ctx: inout GraphicsContext, _ size: CGSize, _ t: Double) {
        let w = size.width, h = size.height
        // Sky
        ctx.fill(Path(CGRect(origin: .zero, size: size)),
                 with: .linearGradient(Gradient(colors: [c0, c0.mix(with: c1, by: 0.35), c0.mix(with: .black, by: 0.4)]),
                                       startPoint: .zero, endPoint: CGPoint(x: w * 0.2, y: h)))
        switch family {
        case .space: space(&ctx, w, h, t)
        case .interior: interior(&ctx, w, h, t)
        case .forest: forest(&ctx, w, h, t)
        case .water: water(&ctx, w, h, t)
        case .built: built(&ctx, w, h, t)
        case .open: open(&ctx, w, h, t)
        }
        // Vignette for type legibility
        ctx.fill(Path(CGRect(origin: .zero, size: size)),
                 with: .linearGradient(Gradient(colors: [.black.opacity(0.0), .black.opacity(0.15), .black.opacity(0.7)]),
                                       startPoint: CGPoint(x: 0, y: h * 0.35), endPoint: CGPoint(x: 0, y: h)))
    }

    private func stars(_ ctx: inout GraphicsContext, _ w: Double, _ h: Double, _ t: Double, count: Int, top: Double) {
        for i in 0..<count {
            let x = rand(i) * w, y = rand(i + 999) * h * top
            let r = 0.4 + 1.2 * pow(rand(i + 77), 4)
            let a = 0.25 + 0.6 * (0.5 + 0.5 * sin(t * (0.6 + rand(i + 5)) + rand(i + 3) * 6))
            ctx.fill(Path(ellipseIn: CGRect(x: x - r, y: y - r, width: 2 * r, height: 2 * r)), with: .color(.white.opacity(a)))
        }
    }

    private func glow(_ ctx: inout GraphicsContext, _ p: CGPoint, _ r: Double, _ color: Color, _ a: Double) {
        ctx.fill(Path(ellipseIn: CGRect(x: p.x - r, y: p.y - r, width: 2 * r, height: 2 * r)),
                 with: .radialGradient(Gradient(colors: [color.opacity(a), .clear]), center: p, startRadius: 0, endRadius: r))
    }

    // MARK: Families

    private func space(_ ctx: inout GraphicsContext, _ w: Double, _ h: Double, _ t: Double) {
        stars(&ctx, w, h, t, count: 160, top: 1)
        // A planet limb lit from one side
        let R = w * 0.95
        let c = CGPoint(x: w * (0.15 + 0.7 * rand(1)), y: h * 1.02 + R * 0.55)
        glow(&ctx, c, R * 1.08, c1, 0.35)
        ctx.fill(Path(ellipseIn: CGRect(x: c.x - R, y: c.y - R, width: 2 * R, height: 2 * R)),
                 with: .linearGradient(Gradient(colors: [c1, c1.mix(with: c0, by: 0.6), .black]),
                                       startPoint: CGPoint(x: c.x - R * 0.4, y: c.y - R), endPoint: CGPoint(x: c.x + R * 0.3, y: c.y - R * 0.5)))
        // Cloud bands drifting across the limb
        for k in 0..<5 {
            let y = c.y - R + Double(k) * 18 + 10
            let off = (t * 4 + Double(k) * 60).truncatingRemainder(dividingBy: w)
            var band = Path()
            band.addEllipse(in: CGRect(x: c.x - R * 0.7 + off * 0.2, y: y, width: R * 1.2, height: 6 + 4 * rand(k + 40)))
            ctx.fill(band, with: .color(.white.opacity(0.05)))
        }
        // A station or ship crossing slowly, with running lights
        let sx = (w * 1.2 - (t * 6).truncatingRemainder(dividingBy: w * 1.6)), sy = h * 0.32
        var hull = Path(); hull.addRoundedRect(in: CGRect(x: sx, y: sy, width: 70, height: 6), cornerSize: CGSize(width: 3, height: 3))
        ctx.fill(hull, with: .color(Color(hex: 0xB9C2C8).opacity(0.8)))
        for k in 0..<3 {
            ctx.stroke(Path(ellipseIn: CGRect(x: sx + 18 + Double(k) * 14, y: sy - 5, width: 6, height: 16)), with: .color(.white.opacity(0.45)), lineWidth: 0.7)
        }
        let blink = 0.3 + 0.7 * pow(0.5 + 0.5 * sin(t * 3), 10)
        ctx.fill(Path(ellipseIn: CGRect(x: sx - 2, y: sy + 1, width: 4, height: 4)), with: .color(Color(hex: 0xFF6B6B).opacity(blink)))
        glow(&ctx, CGPoint(x: sx + 72, y: sy + 3), 14, c2, 0.8)
        // Sun flare
        let sun = CGPoint(x: w * 0.82, y: h * 0.14)
        glow(&ctx, sun, 140, c2, 0.35)
        glow(&ctx, sun, 30, .white, 0.9)
        for k in 0..<4 {
            let p = CGPoint(x: sun.x - Double(k + 1) * 55, y: sun.y + Double(k + 1) * 70)
            glow(&ctx, p, 10 + Double(k) * 6, c2, 0.12)
        }
    }

    private func interior(_ ctx: inout GraphicsContext, _ w: Double, _ h: Double, _ t: Double) {
        // A corridor in one-point perspective
        let vp = CGPoint(x: w * 0.5, y: h * 0.42)
        for k in 0..<10 {
            let f = Double(k) / 10
            let rw = w * (0.15 + f * 1.1), rh = h * (0.12 + f * 0.9)
            let r = CGRect(x: vp.x - rw / 2, y: vp.y - rh / 2, width: rw, height: rh)
            ctx.stroke(Path(roundedRect: r, cornerRadius: 10 + f * 30), with: .color(c1.opacity(0.12 + 0.18 * (1 - f))), lineWidth: 1 + f * 2)
        }
        // Pods along the walls
        if setting == "cryo" || setting == "ship-interior" {
            for k in 0..<5 {
                let f = 0.2 + Double(k) * 0.16
                for side in [-1.0, 1.0] {
                    let x = vp.x + side * w * (0.12 + f * 0.45) - 9 * f * 2, y = vp.y - h * 0.06 * f
                    let pod = CGRect(x: x, y: y, width: 18 * f * 2, height: 46 * f * 2)
                    ctx.fill(Path(roundedRect: pod, cornerRadius: 9 * f * 2), with: .color(c1.opacity(0.25)))
                    ctx.stroke(Path(roundedRect: pod, cornerRadius: 9 * f * 2), with: .color(.white.opacity(0.25)), lineWidth: 0.6)
                    glow(&ctx, CGPoint(x: pod.midX, y: pod.midY), 20 * f * 2, c2, 0.12 + 0.08 * sin(t * 1.5 + Double(k)))
                }
            }
        }
        // Warning light sweep
        let sweep = 0.5 + 0.5 * sin(t * 1.4)
        glow(&ctx, CGPoint(x: vp.x, y: h * 0.1), w * 0.6, c2, 0.06 + 0.12 * sweep)
        // Frost / dust motes
        for i in 0..<70 {
            let x = (rand(i) * w + t * 6 * (rand(i + 5) - 0.5)).truncatingRemainder(dividingBy: w)
            let y = (rand(i + 300) * h + t * 8 * rand(i + 9)).truncatingRemainder(dividingBy: h)
            ctx.fill(Path(ellipseIn: CGRect(x: x, y: y, width: 1.6, height: 1.6)), with: .color(.white.opacity(0.25 * rand(i + 2))))
        }
    }

    private func forest(_ ctx: inout GraphicsContext, _ w: Double, _ h: Double, _ t: Double) {
        // Shafts of light through a canopy
        for k in 0..<5 {
            let x = w * (0.1 + 0.2 * Double(k)) + 20 * sin(t * 0.2 + Double(k))
            var beam = Path()
            beam.move(to: CGPoint(x: x, y: 0)); beam.addLine(to: CGPoint(x: x + 40, y: 0))
            beam.addLine(to: CGPoint(x: x + 140, y: h)); beam.addLine(to: CGPoint(x: x + 60, y: h)); beam.closeSubpath()
            ctx.fill(beam, with: .linearGradient(Gradient(colors: [c2.opacity(0.18), .clear]), startPoint: CGPoint(x: x, y: 0), endPoint: CGPoint(x: x, y: h)))
        }
        // Layered leaf silhouettes, darker toward the front
        for layer in 0..<4 {
            let depth = Double(layer) / 3
            let color = c1.mix(with: .black, by: 0.35 + depth * 0.5)
            let baseY = h * (0.45 + depth * 0.18)
            var p = Path()
            p.move(to: CGPoint(x: 0, y: h))
            var x = -20.0
            var i = layer * 100
            while x < w + 40 {
                let lw = 40 + 60 * rand(i), lh = 60 + 120 * rand(i + 1)
                let sway = 4 * sin(t * 0.6 + Double(i))
                p.addLine(to: CGPoint(x: x, y: baseY))
                p.addQuadCurve(to: CGPoint(x: x + lw, y: baseY), control: CGPoint(x: x + lw / 2 + sway, y: baseY - lh))
                x += lw * 0.7; i += 2
            }
            p.addLine(to: CGPoint(x: w, y: h)); p.closeSubpath()
            ctx.fill(p, with: .color(color))
        }
        // Threads of silk catching light
        for k in 0..<6 {
            var s = Path()
            let x0 = w * rand(k + 600), y0 = h * 0.15 * rand(k + 601)
            s.move(to: CGPoint(x: x0, y: y0))
            s.addQuadCurve(to: CGPoint(x: x0 + 120, y: y0 + 160), control: CGPoint(x: x0 + 80 + 10 * sin(t * 0.5), y: y0 + 30))
            ctx.stroke(s, with: .color(.white.opacity(0.18)), lineWidth: 0.6)
        }
        // Spores / fireflies
        for i in 0..<50 {
            let x = rand(i) * w + 10 * sin(t * 0.5 + Double(i))
            let y = (rand(i + 50) * h - t * 6 * (0.3 + rand(i + 51))).truncatingRemainder(dividingBy: h)
            let yy = y < 0 ? y + h : y
            glow(&ctx, CGPoint(x: x, y: yy), 4, c2, 0.5 * (0.5 + 0.5 * sin(t * 2 + Double(i))))
        }
    }

    private func water(_ ctx: inout GraphicsContext, _ w: Double, _ h: Double, _ t: Double) {
        if setting == "storm" {
            let flash = pow(max(0, sin(t * 0.7)), 40)
            ctx.fill(Path(CGRect(x: 0, y: 0, width: w, height: h)), with: .color(.white.opacity(0.25 * flash)))
            for i in 0..<120 {
                let x = (rand(i) * w + t * 60).truncatingRemainder(dividingBy: w)
                let y = (rand(i + 7) * h + t * 400 * (0.6 + rand(i + 3))).truncatingRemainder(dividingBy: h)
                var d = Path(); d.move(to: CGPoint(x: x, y: y)); d.addLine(to: CGPoint(x: x - 4, y: y + 14))
                ctx.stroke(d, with: .color(.white.opacity(0.25)), lineWidth: 0.7)
            }
        } else {
            glow(&ctx, CGPoint(x: w * 0.7, y: h * 0.25), 120, c2, 0.4)
        }
        for k in 0..<8 {
            let y = h * 0.55 + Double(k) * h * 0.06
            var wave = Path()
            wave.move(to: CGPoint(x: 0, y: y))
            var x = 0.0
            while x <= w {
                wave.addLine(to: CGPoint(x: x, y: y + 6 * sin(x / 40 + t * (0.8 + Double(k) * 0.1) + Double(k))))
                x += 8
            }
            wave.addLine(to: CGPoint(x: w, y: h)); wave.addLine(to: CGPoint(x: 0, y: h)); wave.closeSubpath()
            ctx.fill(wave, with: .color(c1.mix(with: .black, by: 0.3 + Double(k) * 0.08).opacity(0.85)))
        }
    }

    private func built(_ ctx: inout GraphicsContext, _ w: Double, _ h: Double, _ t: Double) {
        stars(&ctx, w, h, t, count: 60, top: 0.4)
        glow(&ctx, CGPoint(x: w * 0.3, y: h * 0.3), 160, c2, 0.25)
        // Towers / domes in two depths
        for layer in 0..<2 {
            var x = -10.0, i = layer * 50
            let base = h * (0.62 + Double(layer) * 0.1)
            let color = c0.mix(with: .black, by: 0.3 + Double(layer) * 0.4)
            while x < w {
                let bw = 30 + 50 * rand(i), bh = 60 + 180 * rand(i + 1) * (setting == "underground" ? 0.4 : 1)
                let r = CGRect(x: x, y: base - bh, width: bw, height: bh + h)
                if rand(i + 2) > 0.6 {
                    ctx.fill(Path(ellipseIn: CGRect(x: x, y: base - bh - bw / 2, width: bw, height: bw)), with: .color(color))
                }
                ctx.fill(Path(r), with: .color(color))
                // lit windows
                for k in 0..<Int(bh / 18) where rand(i * 10 + k) > 0.7 {
                    let a = 0.3 + 0.4 * (0.5 + 0.5 * sin(t + Double(k)))
                    ctx.fill(Path(CGRect(x: x + bw * 0.4, y: base - bh + Double(k) * 18 + 6, width: 3, height: 5)), with: .color(c2.opacity(a)))
                }
                x += bw + 6; i += 3
            }
        }
        if setting == "battle" {
            for i in 0..<40 {
                let x = rand(i) * w, y = (h - (t * 30 * (0.5 + rand(i + 1)) + rand(i + 2) * h).truncatingRemainder(dividingBy: h))
                glow(&ctx, CGPoint(x: x, y: y), 3, Color(hex: 0xFFB070), 0.8)
            }
        }
    }

    private func open(_ ctx: inout GraphicsContext, _ w: Double, _ h: Double, _ t: Double) {
        stars(&ctx, w, h, t, count: 80, top: 0.45)
        let sun = CGPoint(x: w * (0.3 + 0.4 * rand(3)), y: h * 0.5)
        glow(&ctx, sun, 180, c2, 0.45)
        glow(&ctx, sun, 26, .white, 0.7)
        for layer in 0..<3 {
            let base = h * (0.55 + Double(layer) * 0.12)
            var p = Path(); p.move(to: CGPoint(x: 0, y: h))
            var x = 0.0
            while x <= w {
                p.addLine(to: CGPoint(x: x, y: base - 26 * sin(x / (120 + Double(layer) * 40) + Double(layer) * 2 + rand(layer) * 6)))
                x += 10
            }
            p.addLine(to: CGPoint(x: w, y: h)); p.closeSubpath()
            ctx.fill(p, with: .color(c1.mix(with: .black, by: 0.3 + Double(layer) * 0.22)))
        }
        if setting == "ruins" {
            for k in 0..<5 {
                let x = w * (0.1 + 0.18 * Double(k)), hh = 40 + 80 * rand(k + 20)
                ctx.fill(Path(CGRect(x: x, y: h * 0.62 - hh, width: 12, height: hh)), with: .color(c0.mix(with: .black, by: 0.5)))
            }
        }
        for i in 0..<40 {
            let x = (rand(i) * w + t * 10).truncatingRemainder(dividingBy: w)
            let y = h * 0.4 + rand(i + 1) * h * 0.5
            ctx.fill(Path(ellipseIn: CGRect(x: x, y: y, width: 1.4, height: 1.4)), with: .color(c2.opacity(0.35)))
        }
    }
}

extension Color {
    /// "#RRGGBB" → Color.
    init(css: String) {
        self.init(hex: UInt32(css.trimmingCharacters(in: CharacterSet(charactersIn: "#")), radix: 16) ?? 0x888888)
    }
}

/// Full-screen opener shown when a chapter begins: art from the chapter's setting, its title, storyline and a teaser.
struct ChapterTitleCard: View {
    let chapter: Companion.Chapter
    let number: String?
    let storyline: String?
    let seed: Int
    let dismiss: () -> Void
    @State private var shown = false

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            SceneArt(setting: chapter.setting, palette: chapter.palette.map { Color(css: $0) }, seed: seed)
                .ignoresSafeArea()
            VStack(alignment: .leading, spacing: 12) {
                if let storyline {
                    Text(storyline.uppercased())
                        .font(.caption.weight(.semibold)).tracking(2)
                        .foregroundStyle(Color(css: chapter.palette.last ?? "#E8C170"))
                }
                if let number { Text(number).font(Typeface.serif(22)).foregroundStyle(.white.opacity(0.7)) }
                Text(chapter.title).font(Typeface.serif(40)).foregroundStyle(.white).fixedSize(horizontal: false, vertical: true)
                if let era = chapter.era, !era.isEmpty {
                    Text(era).font(.subheadline.weight(.medium)).foregroundStyle(.white.opacity(0.7))
                }
                Text(chapter.teaser).font(Typeface.serif(18, italic: true)).foregroundStyle(.white.opacity(0.85))
                    .fixedSize(horizontal: false, vertical: true)
                HStack(spacing: 6) {
                    Image(systemName: "hand.tap")
                    Text("Tap to begin")
                }
                .font(.footnote).foregroundStyle(.white.opacity(0.5)).padding(.top, 10)
            }
            .padding(28)
            .padding(.bottom, 30)
            .opacity(shown ? 1 : 0)
            .offset(y: shown ? 0 : 16)
        }
        .environment(\.colorScheme, .dark)
        .contentShape(.rect)
        .onTapGesture(perform: dismiss)
        .gesture(DragGesture(minimumDistance: 20).onEnded { _ in dismiss() })
        .onAppear { withAnimation(.smooth(duration: 0.9).delay(0.25)) { shown = true } }
        .accessibilityElement(children: .combine)
        .accessibilityAddTraits(.isButton)
        .accessibilityHint("Begins the chapter")
    }
}

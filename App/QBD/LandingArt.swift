import SwiftUI
import CoreMotion
import BookKit

/// Small device-tilt offsets for parallax. Off when Reduce Motion is on.
@Observable
final class Tilt {
    static let shared = Tilt()
    private(set) var x = 0.0
    private(set) var y = 0.0
    @ObservationIgnored private let manager = CMMotionManager()
    @ObservationIgnored private var users = 0

    func start() {
        users += 1
        guard users == 1, manager.isDeviceMotionAvailable else { return }
        manager.deviceMotionUpdateInterval = 1.0 / 30
        manager.startDeviceMotionUpdates(to: .main) { [weak self] m, _ in
            guard let self, let m else { return }
            // Gentle, clamped, eased toward the new value
            let tx = max(-1, min(1, m.attitude.roll / 0.6)), ty = max(-1, min(1, (m.attitude.pitch - 0.7) / 0.6))
            self.x += (tx - self.x) * 0.12
            self.y += (ty - self.y) * 0.12
        }
    }

    func stop() {
        users = max(0, users - 1)
        if users == 0 { manager.stopDeviceMotionUpdates() }
    }
}

/// The rebuilt progressive landing: a GPU-drawn sky and planet, then an ark ship, a satellite and its signal,
/// a sentinel pod and an orb web drawn above it. Everything advances with the reader's place in the story.
struct LandingArt: View {
    var scene = SceneState()
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @State private var tilt = Tilt.shared

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30, paused: reduceMotion)) { tl in
            let t = reduceMotion ? 30 : tl.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 10_000)
            let progress = Self.progress(scene)
            let tx = reduceMotion ? 0 : tilt.x, ty = reduceMotion ? 0 : tilt.y
            ZStack {
                Rectangle()
                    .visualEffect { content, proxy in
                        content.colorEffect(ShaderLibrary.landingSky(.float2(proxy.size), .float(t), .float(progress),
                                                                     .float(scene.orbit ? 1 : max(0, scene.web - 0.6) * 2), .float2(tx, ty)))
                    }
                Canvas { ctx, size in
                    LandingPainter(scene: scene, t: t, tilt: CGPoint(x: tx, y: ty)).draw(&ctx, size)
                }
            }
        }
        .onAppear { if !reduceMotion { tilt.start() } }
        .onDisappear { tilt.stop() }
        .accessibilityHidden(true)
    }

    /// One number for the shader: how far the story has come.
    static func progress(_ s: SceneState) -> Double { min(1, max(0, 0.5 * s.ship + 0.5 * s.web)) }
}

struct LandingPainter {
    let scene: SceneState
    let t: Double
    let tilt: CGPoint

    func draw(_ ctx: inout GraphicsContext, _ size: CGSize) {
        let w = size.width, h = size.height
        // The planet's geometry, matching the shader (units of height)
        let R = 1.05 * h
        let pc = CGPoint(x: w * 0.70 + tilt.x * 0.018 * h, y: h * (1.0 + 1.05 * 0.58) + tilt.y * 0.018 * h)

        satellite(&ctx, w, h, pc, R)
        ship(&ctx, w, h)
        web(&ctx, w, h)
    }

    private func glow(_ ctx: inout GraphicsContext, _ p: CGPoint, _ r: Double, _ c: Color, _ a: Double) {
        ctx.fill(Path(ellipseIn: CGRect(x: p.x - r, y: p.y - r, width: 2 * r, height: 2 * r)),
                 with: .radialGradient(Gradient(colors: [c.opacity(a), .clear]), center: p, startRadius: 0, endRadius: r))
    }

    // MARK: Orbit: the satellite, its signal and the sentinel pod

    private func satellite(_ ctx: inout GraphicsContext, _ w: Double, _ h: Double, _ pc: CGPoint, _ R: Double) {
        let orbit = CGRect(x: pc.x - R * 1.16, y: pc.y - R * 1.07, width: R * 2.32, height: R * 0.36)
        func on(_ a: Double) -> CGPoint { CGPoint(x: orbit.midX + cos(a) * orbit.width / 2, y: orbit.midY + sin(a) * orbit.height / 2) }
        var path = Path(); path.addEllipse(in: orbit)
        ctx.stroke(path, with: .color(Color(hex: 0xBFE8D8).opacity(0.10)), style: StrokeStyle(lineWidth: 0.7, dash: [2, 5]))

        let sat = on(-2.5 + 0.03 * sin(t * 0.05))
        // Panels and body
        var ctx2 = ctx
        ctx2.translateBy(x: sat.x, y: sat.y)
        ctx2.rotate(by: .radians(-0.2))
        ctx2.fill(Path(CGRect(x: -14, y: -2, width: 10, height: 4)), with: .color(Color(hex: 0x6FA3C9).opacity(0.85)))
        ctx2.fill(Path(CGRect(x: 4, y: -2, width: 10, height: 4)), with: .color(Color(hex: 0x6FA3C9).opacity(0.85)))
        ctx2.fill(Path(roundedRect: CGRect(x: -4, y: -3, width: 8, height: 6), cornerRadius: 1.5), with: .color(Color(hex: 0xE9EEF0)))
        glow(&ctx, sat, 10, Color(hex: 0xDFF5E0), 0.35)

        // Its voice: rings that travel down toward the surface
        if scene.signal > 0 {
            let target = CGPoint(x: pc.x - R * 0.42, y: pc.y - R * 0.93)
            for k in 0..<3 {
                let ph = (t * 0.35 + Double(k) / 3).truncatingRemainder(dividingBy: 1)
                let p = CGPoint(x: sat.x + (target.x - sat.x) * ph, y: sat.y + (target.y - sat.y) * ph)
                let r = 3 + 10 * ph
                ctx.stroke(Path(ellipseIn: CGRect(x: p.x - r, y: p.y - r * 0.5, width: 2 * r, height: r)),
                           with: .color(Color(hex: 0xBCDDBE).opacity(scene.signal * (1 - ph) * 0.7)), lineWidth: 0.9)
            }
        }
        if scene.pod {
            let pod = on(-0.7 + 0.02 * sin(t * 0.07))
            let blink = 0.3 + 0.7 * pow(0.5 + 0.5 * sin(t * 2.4), 10)
            ctx.fill(Path(ellipseIn: CGRect(x: pod.x - 2.2, y: pod.y - 2.2, width: 4.4, height: 4.4)), with: .color(Color(hex: 0xF7D9A8)))
            glow(&ctx, pod, 9, Color(hex: 0xF7D9A8), 0.5 * blink)
        }
        if scene.orbit {
            // A thread climbs from the surface to orbit
            var thread = Path()
            let base = CGPoint(x: pc.x - R * 0.3, y: pc.y - R * 0.97)
            thread.move(to: base)
            thread.addQuadCurve(to: sat, control: CGPoint(x: (base.x + sat.x) / 2 + 20 * sin(t * 0.3), y: (base.y + sat.y) / 2))
            ctx.stroke(thread, with: .color(Color(hex: 0xE8F2EA).opacity(0.35)), lineWidth: 0.8)
        }
    }

    // MARK: The ark ship

    private func ship(_ ctx: inout GraphicsContext, _ w: Double, _ h: Double) {
        let s = scene.ship
        guard s > 0 else { return }
        // From a glint on the right horizon to a close pass across the upper sky
        let cx = w * (0.92 - 0.55 * s) + tilt.x * 10 * s - 6 * sin(t * 0.05)
        let cy = h * (0.46 - 0.30 * s) + tilt.y * 8 * s + 2 * sin(t * 0.3)
        let L = 8 + 230 * s * s        // hull length
        let T = max(1.2, L * 0.045)     // hull thickness
        var c = ctx
        c.translateBy(x: cx, y: cy)
        c.rotate(by: .radians(-0.16))

        let hullDark = Color(hex: 0x39424A), hullLit = Color(hex: 0xB9C4C8)
        if L < 30 {
            c.fill(Path(roundedRect: CGRect(x: -L / 2, y: -T / 2, width: L, height: T), cornerRadius: T / 2), with: .color(hullLit))
            glow(&c, CGPoint(x: L / 2 + 2, y: 0), 6, Color(hex: 0xBFE3FF), 0.8)
            return
        }
        // Spine, lit along its upper edge
        let spine = CGRect(x: -L / 2, y: -T / 2, width: L, height: T)
        c.fill(Path(roundedRect: spine, cornerRadius: T * 0.3),
               with: .linearGradient(Gradient(colors: [hullLit, hullDark]), startPoint: CGPoint(x: 0, y: -T / 2), endPoint: CGPoint(x: 0, y: T / 2)))
        // Forward command block
        let bow = CGRect(x: -L / 2 - T * 1.2, y: -T * 1.1, width: T * 2.2, height: T * 2.2)
        c.fill(Path(roundedRect: bow, cornerRadius: T * 0.4),
               with: .linearGradient(Gradient(colors: [hullLit, hullDark]), startPoint: CGPoint(x: 0, y: bow.minY), endPoint: CGPoint(x: 0, y: bow.maxY)))
        // Cargo and habitat modules along the spine
        for k in 0..<7 {
            let x = -L / 2 + T * 2 + Double(k) * (L * 0.09)
            let mh = T * (k % 3 == 0 ? 1.9 : 1.4)
            let m = CGRect(x: x, y: -mh / 2, width: L * 0.06, height: mh)
            c.fill(Path(roundedRect: m, cornerRadius: 1.5), with: .linearGradient(Gradient(colors: [hullLit.opacity(0.95), hullDark]), startPoint: CGPoint(x: 0, y: m.minY), endPoint: CGPoint(x: 0, y: m.maxY)))
            c.stroke(Path(roundedRect: m, cornerRadius: 1.5), with: .color(.black.opacity(0.35)), lineWidth: 0.5)
        }
        // Rotating habitat ring, seen nearly edge-on, with a bright segment travelling round
        let ringC = CGPoint(x: L * 0.12, y: 0)
        let rw = T * 1.6, rh = T * 4.2
        let ring = CGRect(x: ringC.x - rw / 2, y: ringC.y - rh / 2, width: rw, height: rh)
        c.stroke(Path(ellipseIn: ring), with: .color(hullLit.opacity(0.9)), lineWidth: max(1, T * 0.28))
        for k in 0..<6 {
            let a = Double(k) / 6 * 2 * .pi + t * 0.6
            let p = CGPoint(x: ringC.x + cos(a) * rw / 2, y: ringC.y + sin(a) * rh / 2)
            var spoke = Path(); spoke.move(to: ringC); spoke.addLine(to: p)
            c.stroke(spoke, with: .color(hullLit.opacity(cos(a) > 0 ? 0.55 : 0.2)), lineWidth: 0.6)
        }
        let a = t * 0.6
        let lp = CGPoint(x: ringC.x + cos(a) * rw / 2, y: ringC.y + sin(a) * rh / 2)
        glow(&c, lp, T * 0.9, Color(hex: 0xFFF2D6), cos(a) > 0 ? 0.7 : 0.15)
        // Engine cluster and drive plume
        let stern = L / 2
        for k in -1...1 {
            let n = CGRect(x: stern - T * 0.2, y: Double(k) * T * 0.75 - T * 0.32, width: T * 1.1, height: T * 0.64)
            c.fill(Path(roundedRect: n, cornerRadius: T * 0.2), with: .color(hullDark))
        }
        let flicker = 0.85 + 0.15 * sin(t * 9)
        let plume = CGRect(x: stern + T * 0.8, y: -T * 1.1, width: T * 9 * flicker, height: T * 2.2)
        c.fill(Path(ellipseIn: plume), with: .radialGradient(Gradient(colors: [Color(hex: 0xBFE3FF).opacity(0.85), Color(hex: 0x4FA3D9).opacity(0.25), .clear]),
                                                               center: CGPoint(x: plume.minX + T, y: 0), startRadius: 0, endRadius: plume.width))
        glow(&c, CGPoint(x: stern + T, y: 0), T * 2.2, .white, 0.7 * flicker)
        // Running lights
        let blink = pow(0.5 + 0.5 * sin(t * 3.1), 12)
        c.fill(Path(ellipseIn: CGRect(x: -L / 2 - T * 1.3, y: -T * 1.2, width: 3, height: 3)), with: .color(Color(hex: 0xFF6B6B).opacity(0.3 + 0.7 * blink)))
        c.fill(Path(ellipseIn: CGRect(x: stern - T, y: T * 0.9, width: 3, height: 3)), with: .color(Color(hex: 0x7CFFB2).opacity(0.3 + 0.7 * (1 - blink))))
        // Sun glint along the hull
        glow(&c, CGPoint(x: -L * 0.2 + L * 0.1 * sin(t * 0.07), y: -T * 0.5), T * 2.5, Color(hex: 0xFFF6E0), 0.35)
    }

    // MARK: The orb web, grown as the story advances

    private func web(_ ctx: inout GraphicsContext, _ w: Double, _ h: Double) {
        let amount = scene.web
        guard amount > 0.02 else { return }
        let hub = CGPoint(x: w * 0.24 + 4 * sin(t * 0.5) + tilt.x * 14, y: h * 0.22 + 3 * cos(t * 0.37) + tilt.y * 10)
        let spokes = 19
        let reach = max(w, h) * 0.5
        var angles: [Double] = []
        for k in 0..<spokes { angles.append(Double(k) / Double(spokes) * 2 * .pi + 0.07 * sin(Double(k) * 1.7)) }
        func point(_ a: Double, _ r: Double) -> CGPoint {
            let sway = 0.012 * sin(t * 0.8 + r / 60)
            return CGPoint(x: hub.x + cos(a + sway) * r, y: hub.y + sin(a + sway) * r * 0.92)
        }
        let silk = Color(hex: 0xE8F2EA)
        let spokeReach = reach * min(1, 0.2 + amount)
        for a in angles {
            var p = Path(); p.move(to: hub); p.addLine(to: point(a, spokeReach))
            ctx.stroke(p, with: .linearGradient(Gradient(colors: [silk.opacity(0.28), silk.opacity(0.02)]), startPoint: hub, endPoint: point(a, spokeReach)), lineWidth: 0.6)
        }
        var spiral = Path()
        var first = true
        var r = 12.0
        let limit = reach * 0.85 * amount
        while r < limit {
            for a in angles {
                let pt = point(a, r)
                if first { spiral.move(to: pt); first = false } else { spiral.addLine(to: pt) }
                r += 20.0 / Double(spokes) * (1 + r / 240)
            }
        }
        ctx.stroke(spiral, with: .color(silk.opacity(0.16)), lineWidth: 0.5)
        // Dew, catching the sun as it passes
        for (k, s) in SkyPainter.stars.prefix(60).enumerated() {
            let rr0 = 24 + s.x * reach * 0.8
            guard rr0 < limit + 12 else { continue }
            let pt = point(angles[k % spokes], rr0)
            let glint = 0.2 + 0.8 * pow(0.5 + 0.5 * sin(t * 1.1 + s.phase * 3 - rr0 / 40), 8)
            let rad = 0.8 + s.r
            ctx.fill(Path(ellipseIn: CGRect(x: pt.x - rad, y: pt.y - rad, width: 2 * rad, height: 2 * rad)), with: .color(silk.opacity(glint)))
            if glint > 0.8 { glow(&ctx, pt, 6, silk, 0.25) }
        }
        if scene.spider {
            let breath = 1 + 0.03 * sin(t * 1.1)
            let body = Color(hex: 0x060908), rim = Color(hex: 0xBCDDBE).opacity(0.5)
            for k in 0..<8 {
                let side: Double = k < 4 ? -1 : 1
                let i = Double(k % 4)
                let base = CGPoint(x: hub.x + side * 3, y: hub.y - 2 + i * 3)
                let ang = (side > 0 ? 0 : Double.pi) + side * (-0.9 + i * 0.55)
                let knee = CGPoint(x: base.x + cos(ang) * 13, y: base.y + sin(ang) * 9 - 7)
                let tip = CGPoint(x: base.x + cos(ang) * 25, y: base.y + sin(ang) * 18 + 3)
                var leg = Path(); leg.move(to: base); leg.addLine(to: knee); leg.addLine(to: tip)
                ctx.stroke(leg, with: .color(body), style: StrokeStyle(lineWidth: 1.6, lineCap: .round, lineJoin: .round))
                ctx.stroke(leg, with: .color(rim.opacity(0.5)), style: StrokeStyle(lineWidth: 0.4, lineCap: .round, lineJoin: .round))
            }
            let ab = CGRect(x: hub.x - 7 * breath, y: hub.y, width: 14 * breath, height: 19 * breath)
            ctx.fill(Path(ellipseIn: ab), with: .color(body))
            ctx.stroke(Path(ellipseIn: ab), with: .color(rim), lineWidth: 0.6)
            let head = CGRect(x: hub.x - 5, y: hub.y - 9, width: 10, height: 10)
            ctx.fill(Path(ellipseIn: head), with: .color(body))
            ctx.stroke(Path(ellipseIn: head), with: .color(rim), lineWidth: 0.6)
            for e in [-2.2, 2.2] { glow(&ctx, CGPoint(x: hub.x + e, y: hub.y - 6), 2.4, Color(hex: 0xBCDDBE), 0.8) }
        }
    }
}

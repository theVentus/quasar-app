import SwiftUI
import UIKit
import BookKit

// MARK: Backdrops

/// A book's landing backdrop, chosen in its book.json (`theme.landing`).
struct BookBackdrop: View {
    @Environment(Bookshelf.self) private var shelf
    let book: Book
    var style: String? = nil

    var body: some View {
        let location = LaunchState.sceneOverride ?? shelf.location(book.id)
        let scene = SceneState.current(for: book, location: location)
        let landing = style ?? LaunchState.landingOverride ?? book.manifest.theme?.landing ?? "cover"
        switch landing {
        case "stages" where shelf.stages(for: book) != nil:
            let set = shelf.stages(for: book)!
            LandingStages(set: set, position: StagePosition.current(for: book, location: location, count: set.count))
        case "web", "stages": LandingArt(scene: scene)
        case "web-classic": WebBackdrop(scene: scene)
        case "sky": SkyView()
        default: CoverBackdrop(book: book)
        }
    }
}

/// Any book: its own cover, blurred into a field of colour, with a vignette for legible type.
struct CoverBackdrop: View {
    let book: Book

    var body: some View {
        ZStack {
            Color.black
            if let image = BookCover.image(for: book) {
                Image(uiImage: image)
                    .resizable()
                    .scaledToFill()
                    .blur(radius: 60)
                    .saturation(1.2)
                    .opacity(0.85)
            }
            LinearGradient(colors: [.black.opacity(0.15), .black.opacity(0.35), .black.opacity(0.75)], startPoint: .top, endPoint: .bottom)
        }
        .clipped()
        .accessibilityHidden(true)
    }
}

/// An orb web strung across a dark sky above a green world. Threads sway; dew catches the light.
/// The state of a progressive backdrop: dials from the book's `scenes`, interpolated to the reader's position.
struct SceneState: Equatable {
    var web = 1.0, ship = 0.5, signal = 1.0
    var pod = true, spider = true, orbit = false

    static func lerp(_ a: Double, _ b: Double, _ t: Double) -> Double { a + (b - a) * t }

    init() {}

    init(_ a: BookManifest.Scene, _ b: BookManifest.Scene, _ t: Double) {
        web = Self.lerp(a.web ?? 1, b.web ?? a.web ?? 1, t)
        ship = Self.lerp(a.ship ?? 0.5, b.ship ?? a.ship ?? 0.5, t)
        signal = Self.lerp(a.signal ?? 1, b.signal ?? a.signal ?? 1, t)
        pod = a.pod ?? true
        spider = a.spider ?? true
        orbit = a.orbit ?? false
    }

    /// Where the reader is: the part containing the current position and how far through it.
    static func current(for book: Book, location: BookLocation?) -> SceneState {
        guard let scenes = book.manifest.scenes, !scenes.isEmpty else { return SceneState() }
        let parts = book.outline.parts
        guard let loc = location, let entry = book.package.tocEntry(spine: loc.spine),
              let part = book.outline.part(containingTOC: entry.id),
              let pi = parts.firstIndex(where: { $0.id == part.id }) else {
            let (a, b, t) = book.manifest.scene(part: 0, fraction: 0)!
            return SceneState(a, b, t)
        }
        let f = book.progress(inPart: pi, bookProgress: book.package.progress(spine: loc.spine, fraction: loc.fraction))
        let (a, b, t) = book.manifest.scene(part: pi, fraction: f)!
        return SceneState(a, b, t)
    }
}

/// An orb web strung across a dark sky above a green world. The scene advances with the reader:
/// threads fill in, a sentinel pod blinks into orbit, a satellite's signal pulses down, a ship crosses the sky.
struct WebBackdrop: View {
    var scene = SceneState()
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30, paused: reduceMotion)) { timeline in
            let t = reduceMotion ? 12 : timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 100_000)
            Canvas { ctx, size in WebPainter.draw(&ctx, size: size, t: t, scene: scene) }
        }
        .animation(.smooth(duration: 1.2), value: scene)
        .accessibilityHidden(true)
    }
}

enum WebPainter {
    static func draw(_ ctx: inout GraphicsContext, size: CGSize, t: Double, scene: SceneState) {
        let w = size.width, h = size.height
        ctx.fill(Path(CGRect(origin: .zero, size: size)),
                 with: .linearGradient(Gradient(colors: [Color(hex: 0x05080A), Color(hex: 0x0B1712), Color(hex: 0x0E2016)]),
                                       startPoint: .zero, endPoint: CGPoint(x: 0, y: h)))
        for s in SkyPainter.stars.prefix(110) {
            let a = 0.15 + 0.35 * (0.5 + 0.5 * sin(t * 0.7 + s.phase))
            ctx.fill(Path(ellipseIn: CGRect(x: s.x * w - s.r, y: s.y * h * 0.7 - s.r, width: 2 * s.r, height: 2 * s.r)), with: .color(.white.opacity(a)))
        }

        // The green world
        let R = w * 1.25
        let pc = CGPoint(x: w * 0.62, y: h + R * 0.62)
        ctx.fill(Path(ellipseIn: CGRect(x: pc.x - R - 26, y: pc.y - R - 26, width: 2 * R + 52, height: 2 * R + 52)),
                 with: .radialGradient(Gradient(colors: [.clear, Color(hex: 0x9FE0B0).opacity(0.25), .clear]),
                                       center: pc, startRadius: R - 4, endRadius: R + 26))
        ctx.fill(Path(ellipseIn: CGRect(x: pc.x - R, y: pc.y - R, width: 2 * R, height: 2 * R)),
                 with: .linearGradient(Gradient(colors: [Color(hex: 0x3F7A52), Color(hex: 0x1C3A27), Color(hex: 0x0A1A10)]),
                                       startPoint: CGPoint(x: pc.x - R * 0.3, y: pc.y - R), endPoint: CGPoint(x: pc.x + R * 0.2, y: pc.y - R * 0.6)))

        // Orbit ring with the satellite; the sentinel pod joins it later in the story.
        let ringRect = CGRect(x: pc.x - R * 1.18, y: pc.y - R * 1.02, width: R * 2.36, height: R * 0.5)
        var ring = Path(); ring.addEllipse(in: ringRect)
        ctx.stroke(ring, with: .color(Color(hex: 0xCFE8D5).opacity(0.18)), lineWidth: 0.8)
        func onRing(_ angle: Double) -> CGPoint {
            CGPoint(x: ringRect.midX + cos(angle) * ringRect.width / 2, y: ringRect.midY + sin(angle) * ringRect.height / 2)
        }
        let sat = onRing(-2.35 + 0.02 * sin(t * 0.1))
        ctx.fill(Path(ellipseIn: CGRect(x: sat.x - 2.5, y: sat.y - 2.5, width: 5, height: 5)), with: .color(Color(hex: 0xF4F1E6)))
        // Its signal: a pulse travelling down to the surface
        if scene.signal > 0 {
            let phase = (t * 0.45).truncatingRemainder(dividingBy: 1)
            let target = CGPoint(x: pc.x - R * 0.55, y: pc.y - R * 0.74)
            var beam = Path(); beam.move(to: sat); beam.addLine(to: target)
            ctx.stroke(beam, with: .color(Color(hex: 0xBCDDBE).opacity(0.08 * scene.signal)), lineWidth: 0.6)
            let pt = CGPoint(x: sat.x + (target.x - sat.x) * phase, y: sat.y + (target.y - sat.y) * phase)
            let a = scene.signal * (1 - phase) * 0.9
            ctx.fill(Path(ellipseIn: CGRect(x: pt.x - 2, y: pt.y - 2, width: 4, height: 4)), with: .color(Color(hex: 0xDFF5E0).opacity(a)))
        }
        if scene.pod {
            let pod = onRing(-0.6 + 0.015 * sin(t * 0.13))
            let blink = 0.35 + 0.65 * pow(0.5 + 0.5 * sin(t * 2.2), 8)
            ctx.fill(Path(ellipseIn: CGRect(x: pod.x - 2, y: pod.y - 2, width: 4, height: 4)), with: .color(Color(hex: 0xF7D9A8).opacity(blink)))
            ctx.stroke(Path(ellipseIn: CGRect(x: pod.x - 5, y: pod.y - 5, width: 10, height: 10)), with: .color(Color(hex: 0xF7D9A8).opacity(0.25 * blink)), lineWidth: 0.6)
        }

        // The ark ship: a long hull with a drive glow, crossing from the far horizon to overhead as the story advances.
        if scene.ship > 0 {
            let s = scene.ship
            let sx = w * (0.95 - 0.8 * s), sy = h * (0.42 - 0.32 * s) + 2 * sin(t * 0.3)
            let len = 6 + 62 * s * s, thick = 1 + 3.2 * s
            let angle = -0.28
            var hull = Path()
            hull.move(to: CGPoint(x: sx - len / 2, y: sy)); hull.addLine(to: CGPoint(x: sx + len / 2, y: sy))
            var ctx2 = ctx
            ctx2.translateBy(x: sx, y: sy); ctx2.rotate(by: .radians(angle)); ctx2.translateBy(x: -sx, y: -sy)
            ctx2.stroke(hull, with: .color(Color(hex: 0x9EA8A3).opacity(0.75)), style: StrokeStyle(lineWidth: thick, lineCap: .round))
            if s > 0.25 {
                // Rotating habitat rings and the drive
                let n = s > 0.6 ? 3 : 2
                for k in 0..<n {
                    let x = sx - len / 2 + len * (0.35 + 0.2 * Double(k))
                    ctx2.stroke(Path(ellipseIn: CGRect(x: x - thick * 0.9, y: sy - thick * 1.6, width: thick * 1.8, height: thick * 3.2)),
                                with: .color(Color(hex: 0xC9D1CC).opacity(0.5)), lineWidth: 0.7)
                }
                let drive = CGPoint(x: sx + len / 2 + 2, y: sy)
                let g = 4 + 14 * s * (0.8 + 0.2 * sin(t * 6))
                ctx2.fill(Path(ellipseIn: CGRect(x: drive.x - g, y: drive.y - g * 0.5, width: g * 2, height: g)),
                          with: .radialGradient(Gradient(colors: [Color(hex: 0xBFE3FF).opacity(0.7), .clear]), center: drive, startRadius: 0, endRadius: g))
            }
        }

        // The web, with as many rings as the story has earned
        let hub = CGPoint(x: w * 0.3 + 4 * sin(t * 0.5), y: h * 0.26 + 3 * cos(t * 0.37))
        let spokes = 17
        let reach = max(w, h) * 0.55
        var angles: [Double] = []
        for k in 0..<spokes { angles.append(Double(k) / Double(spokes) * 2 * .pi + 0.08 * sin(Double(k) * 1.7)) }
        func point(_ a: Double, _ r: Double) -> CGPoint {
            let sway = 0.012 * sin(t * 0.8 + r / 60)
            return CGPoint(x: hub.x + cos(a + sway) * r, y: hub.y + sin(a + sway) * r * 0.92)
        }
        let silk = Color(hex: 0xE8F2EA)
        let spokeReach = reach * min(1, 0.15 + scene.web)
        for a in angles {
            var p = Path(); p.move(to: hub); p.addLine(to: point(a, spokeReach))
            ctx.stroke(p, with: .color(silk.opacity(0.16)), lineWidth: 0.6)
        }
        var spiral = Path()
        var first = true
        var r = 14.0
        let limit = reach * 0.82 * scene.web
        while r < limit {
            for a in angles {
                let pt = point(a, r)
                if first { spiral.move(to: pt); first = false } else { spiral.addLine(to: pt) }
                r += 22.0 / Double(spokes) * (1 + r / 260)
            }
        }
        ctx.stroke(spiral, with: .color(silk.opacity(0.13)), lineWidth: 0.5)
        if scene.orbit {
            // A single thread leaves the web for orbit
            var up = Path(); up.move(to: hub); up.addLine(to: sat)
            ctx.stroke(up, with: .color(silk.opacity(0.22)), style: StrokeStyle(lineWidth: 0.7, dash: [1, 0]))
        }

        // Dew on the threads
        for (k, s) in SkyPainter.stars.prefix(48).enumerated() {
            let a = angles[k % spokes]
            let rr0 = 30 + s.x * reach * 0.75
            guard rr0 < limit + 20 else { continue }
            let pt = point(a, rr0)
            let glint = 0.25 + 0.6 * pow(0.5 + 0.5 * sin(t * 1.3 + s.phase * 3), 6)
            let rr = 0.8 + s.r * 0.9
            ctx.fill(Path(ellipseIn: CGRect(x: pt.x - rr, y: pt.y - rr, width: 2 * rr, height: 2 * rr)), with: .color(silk.opacity(glint)))
        }

        // She waits at the hub: a small silhouette, legs along the spokes, breathing slowly.
        if scene.spider {
            let breath = 1 + 0.03 * sin(t * 1.1)
            let body = Color(hex: 0x070A08)
            let rim = silk.opacity(0.35)
            let ab = CGRect(x: hub.x - 7 * breath, y: hub.y - 2, width: 14 * breath, height: 20 * breath)
            ctx.fill(Path(ellipseIn: ab), with: .color(body))
            ctx.stroke(Path(ellipseIn: ab), with: .color(rim), lineWidth: 0.6)
            let head = CGRect(x: hub.x - 4.5, y: hub.y - 10, width: 9, height: 9)
            ctx.fill(Path(ellipseIn: head), with: .color(body))
            ctx.stroke(Path(ellipseIn: head), with: .color(rim), lineWidth: 0.6)
            for k in 0..<8 {
                let side: Double = k < 4 ? -1 : 1
                let a = side * (0.35 + 0.55 * Double(k % 4)) - .pi / 2 + (side > 0 ? 0 : 0)
                let ang = side > 0 ? a : (.pi - a)
                let knee = CGPoint(x: hub.x + cos(ang) * 14, y: hub.y - 4 + sin(ang) * 10 + Double(k % 4) * 3)
                let tip = CGPoint(x: hub.x + cos(ang) * 26, y: hub.y - 2 + sin(ang) * 18 + Double(k % 4) * 5)
                var leg = Path(); leg.move(to: CGPoint(x: hub.x + side * 4, y: hub.y + Double(k % 4) * 3)); leg.addLine(to: knee); leg.addLine(to: tip)
                ctx.stroke(leg, with: .color(body), style: StrokeStyle(lineWidth: 1.4, lineCap: .round, lineJoin: .round))
                ctx.stroke(leg, with: .color(rim.opacity(0.5)), style: StrokeStyle(lineWidth: 0.4, lineCap: .round, lineJoin: .round))
            }
        }
    }
}

// MARK: Cover

enum BookCover {
    private static var cache: [String: UIImage] = [:]

    static func image(for book: Book) -> UIImage? {
        if let hit = cache[book.id] { return hit }
        guard let url = book.package.coverURL, let image = UIImage(contentsOfFile: url.path) else { return nil }
        let target = CGSize(width: 600, height: 600 * image.size.height / max(1, image.size.width))
        let small = UIGraphicsImageRenderer(size: target).image { _ in image.draw(in: CGRect(origin: .zero, size: target)) }
        cache[book.id] = small
        return small
    }
}

struct CoverImage: View {
    let book: Book
    var width: CGFloat

    var body: some View {
        Group {
            if let image = BookCover.image(for: book) {
                Image(uiImage: image).resizable().scaledToFit()
            } else {
                ZStack {
                    LinearGradient(colors: [Color(hex: 0x2A2F3A), Color(hex: 0x151820)], startPoint: .top, endPoint: .bottom)
                    Text(book.title).font(Typeface.serif(width * 0.12)).foregroundStyle(.white).multilineTextAlignment(.center).padding(10)
                }
                .aspectRatio(2.0 / 3.0, contentMode: .fit)
            }
        }
        .frame(width: width)
        .clipShape(.rect(cornerRadius: 6))
        .shadow(color: .black.opacity(0.45), radius: 18, y: 10)
        .accessibilityHidden(true)
    }
}

// MARK: Landing

/// Home for a book. The art owns the screen; at its foot sit the part you are in, the title, one press line,
/// a progress hairline and the actions. The award, the description and your highlights wait one scroll down,
/// where the art dims behind them.
struct BookLanding: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(\.accent) private var accent
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let book: Book
    @Binding var showSettings: Bool
    let open: (Route) -> Void
    @State private var stage = 0
    @State private var expanded = false
    @State private var quoteIndex = 0
    @State private var dim = 0.0

    private var praise: [BookManifest.Praise] { book.manifest.praise ?? [] }
    private var isCoverStyle: Bool { (book.manifest.theme?.landing ?? "cover") == "cover" }

    /// "PART 4 · ENLIGHTENMENT" while reading a book with parts; otherwise "UP NEXT" / "NOW READING".
    private var eyebrow: String {
        guard let l = shelf.location(book.id) else { return "UP NEXT" }
        guard book.outline.hasParts, book.outline.parts.count > 1, let e = book.package.tocEntry(spine: l.spine),
              let part = book.outline.part(containingTOC: e.id) else { return "NOW READING" }
        let n = part.number.map { "PART \($0)" }
        return [n, part.title.isEmpty ? nil : part.title.uppercased()].compactMap { $0 }.joined(separator: " · ")
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 0) {
                HStack {
                    Spacer()
                    Button { showSettings = true } label: {
                        Image(systemName: "gearshape").font(.title3).frame(width: 46, height: 46).contentShape(.circle)
                    }
                    .buttonStyle(.plain)
                    .glassEffect(.regular.interactive(), in: .circle)
                    .accessibilityLabel("Settings")
                }
                .padding(.horizontal, 20)
                .padding(.top, 6)

                VStack(alignment: .leading, spacing: 0) {
                    Spacer(minLength: 0)
                    if isCoverStyle {
                        CoverImage(book: book, width: 96).padding(.bottom, 16).reveal(stage >= 1)
                    }
                    Text(eyebrow)
                        .font(.caption.weight(.semibold))
                        .tracking(2)
                        .foregroundStyle(.white.opacity(0.62))
                        .reveal(stage >= 1)
                    Text(book.title)
                        .font(Typeface.serif(42))
                        .foregroundStyle(.white)
                        .lineLimit(3)
                        .minimumScaleFactor(0.55)
                        .padding(.top, 8)
                        .reveal(stage >= 1)
                    Text(book.authors.joined(separator: ", "))
                        .font(Typeface.serif(19, italic: true))
                        .foregroundStyle(.white.opacity(0.75))
                        .padding(.top, 4)
                        .reveal(stage >= 1)
                    if !praise.isEmpty {
                        PressLine(praise: praise, index: quoteIndex)
                            .padding(.top, 16)
                            .reveal(stage >= 2)
                    }
                    ProgressHairline(book: book).padding(.top, 20).reveal(stage >= 3)
                    BookActions(book: book, open: open).padding(.top, 16).reveal(stage >= 3)
                    Label("About · Highlights", systemImage: "chevron.down")
                        .labelStyle(TrailingIcon())
                        .font(.caption2.weight(.semibold))
                        .tracking(1.4)
                        .textCase(.uppercase)
                        .foregroundStyle(.white.opacity(0.4))
                        .frame(maxWidth: .infinity)
                        .padding(.top, 18)
                        .reveal(stage >= 4)
                        .accessibilityHidden(true)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 24)
                .padding(.bottom, 14)
                .containerRelativeFrame(.vertical) { h, _ in max(h * 0.93, 560) }

                AboutSection(book: book, expanded: $expanded)
                    .padding(.horizontal, 24)
                    .padding(.top, 8)
                    .padding(.bottom, 28)
                HighlightsSection(book: book, open: open)
                    .padding(.horizontal, 20)
                    .padding(.bottom, 40)
            }
        }
        .defaultScrollAnchor(LaunchState.scrollTo != nil ? .bottom : .top)
        .scrollIndicators(.hidden)
        .onScrollGeometryChange(for: Double.self) { g in Double(g.contentOffset.y + g.contentInsets.top) } action: { _, y in
            dim = min(1, max(0, y / 360))
        }
        .background {
            BookBackdrop(book: book)
                .overlay {
                    // Legibility at the foot of the art, and a deeper dim once you scroll into the details.
                    LinearGradient(stops: [.init(color: .clear, location: 0.48), .init(color: .black.opacity(0.55), location: 0.7),
                                           .init(color: .black.opacity(0.88), location: 1)], startPoint: .top, endPoint: .bottom)
                }
                .overlay(Color.black.opacity(dim * 0.6))
                .ignoresSafeArea()
        }
        .environment(\.colorScheme, .dark)
        .task {
            if reduceMotion || LaunchState.isScreenshotting { stage = 4; return }
            for i in 1...4 {
                try? await Task.sleep(for: .milliseconds(i == 1 ? 60 : 120))
                withAnimation(.smooth(duration: 0.5)) { stage = i }
            }
        }
        .task(id: praise.count) {
            guard praise.count > 1 else { return }
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(9))
                withAnimation(.smooth(duration: 0.8)) { quoteIndex = (quoteIndex + 1) % praise.count }
            }
        }
    }
}

struct TrailingIcon: LabelStyle {
    func makeBody(configuration: Configuration) -> some View {
        HStack(spacing: 5) { configuration.title; configuration.icon }
    }
}

/// A thin line for how far you have read, with the percentage; or the length when you have not started.
struct ProgressHairline: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(\.accent) private var accent
    let book: Book

    var body: some View {
        let p = shelf.progress(book)
        HStack(spacing: 12) {
            GeometryReader { g in
                ZStack(alignment: .leading) {
                    Capsule().fill(.white.opacity(0.16))
                    Capsule().fill(accent.pastel).frame(width: max(2, g.size.width * CGFloat(p)))
                }
            }
            .frame(height: 2)
            Text(p > 0 ? "\(Int((p * 100).rounded()))%" : "≈ \(max(1, Int(book.readingHours.rounded()))) h")
                .font(.footnote.weight(.medium))
                .monospacedDigit()
                .foregroundStyle(.white.opacity(0.72))
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(p > 0 ? "\(Int((p * 100).rounded())) percent read" : "About \(max(1, Int(book.readingHours.rounded()))) hours")
    }
}

/// Below the fold: the award, the description and the book's shape, set quietly.
struct AboutSection: View {
    let book: Book
    @Binding var expanded: Bool
    @Environment(\.accent) private var accent

    var body: some View {
        let o = book.outline
        VStack(alignment: .leading, spacing: 12) {
            Text("ABOUT")
                .font(.caption.weight(.semibold))
                .tracking(1.6)
                .foregroundStyle(.white.opacity(0.6))
            if let awards = book.manifest.awards {
                Text(awards.uppercased())
                    .font(.caption2.weight(.semibold))
                    .tracking(1.4)
                    .foregroundStyle(accent.pastel)
            }
            if let about = book.manifest.about {
                Blurb(text: about, expanded: $expanded)
            }
            let bits: [String?] = [o.parts.count > 1 ? "\(o.parts.count) parts" : nil, "\(o.chapterCount) chapters",
                                   "≈ \(max(1, Int(book.readingHours.rounded()))) h"]
            Text(bits.compactMap { $0 }.joined(separator: "  ·  "))
                .font(.footnote.weight(.medium))
                .monospacedDigit()
                .foregroundStyle(.white.opacity(0.55))
        }
    }
}

/// A single press quote, the way one sits on a paperback, crossfading to the next every few seconds.
struct PressLine: View {
    let praise: [BookManifest.Praise]
    let index: Int

    var body: some View {
        let p = praise[min(index, praise.count - 1)]
        VStack(alignment: .leading, spacing: 4) {
            Text("‘\(p.quote)’")
                .font(Typeface.serif(17, italic: true))
                .foregroundStyle(.white.opacity(0.9))
                .fixedSize(horizontal: false, vertical: true)
            Text(p.source.uppercased())
                .font(.caption2.weight(.semibold))
                .tracking(1.2)
                .foregroundStyle(.white.opacity(0.55))
        }
        .id(index)
        .transition(.opacity)
        .accessibilityElement(children: .combine)
    }
}

/// The description: two lines trailing into a fade, unfolding in place on tap.
struct Blurb: View {
    let text: String
    @Binding var expanded: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(text)
                .font(.subheadline)
                .foregroundStyle(.white.opacity(0.78))
                .lineLimit(expanded ? nil : 4)
                .fixedSize(horizontal: false, vertical: true)
                .mask {
                    if expanded { Rectangle() } else {
                        LinearGradient(stops: [.init(color: .black, location: 0.55), .init(color: .clear, location: 1)], startPoint: .top, endPoint: .bottom)
                    }
                }
            Button(expanded ? "Less" : "More") { withAnimation(.smooth(duration: 0.4)) { expanded.toggle() } }
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.white)
                .buttonStyle(.plain)
        }
        .contentShape(.rect)
        .onTapGesture { withAnimation(.smooth(duration: 0.4)) { expanded.toggle() } }
        .accessibilityElement(children: .combine)
        .accessibilityHint(expanded ? "Collapses the description" : "Expands the description")
    }
}

extension View {
    /// Staged entrance: fades in and rises a few points.
    func reveal(_ on: Bool) -> some View {
        opacity(on ? 1 : 0).offset(y: on ? 0 : 10)
    }
}

struct BookStats: View {
    @Environment(Bookshelf.self) private var shelf
    let book: Book

    var body: some View {
        let o = book.outline
        let progress = shelf.progress(book)
        GlassEffectContainer(spacing: 8) {
            HStack(spacing: 8) {
                if o.parts.count > 1 && o.parts.contains(where: { !$0.chapters.isEmpty }) {
                    chip("\(o.parts.count) parts")
                }
                chip("\(o.chapterCount) chapters")
                chip(progress > 0 ? "\(Int((progress * 100).rounded()))% read" : "≈ \(max(1, Int(book.readingHours.rounded()))) h")
            }
        }
    }

    private func chip(_ s: String) -> some View {
        Text(s)
            .font(.footnote.weight(.semibold))
            .monospacedDigit()
            .padding(.horizontal, 12)
            .padding(.vertical, 7)
            .glassEffect(.regular, in: .capsule)
    }
}

struct BookActions: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(\.accent) private var accent
    let book: Book
    let open: (Route) -> Void

    private var continueLabel: String {
        guard let l = shelf.location(book.id), let entry = book.package.tocEntry(spine: l.spine),
              let ch = book.outline.chapter(forTOC: entry.id) else { return "Start reading" }
        return "Continue \(ch.number ?? "")".trimmingCharacters(in: .whitespaces)
    }

    var body: some View {
        GlassEffectContainer(spacing: 12) {
            HStack(spacing: 12) {
                Button { open(.book(id: book.id, toc: nil)) } label: {
                    Label(continueLabel, systemImage: "book.fill")
                        .font(.headline)
                        .foregroundStyle(accent.onPastel)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                }
                .buttonStyle(.glassProminent)
                .tint(accent.pastel)
                Button { open(.bookContents(book.id)) } label: {
                    Image(systemName: "list.bullet").font(.headline).foregroundStyle(.primary).frame(width: 26, height: 26).padding(6)
                }
                .buttonStyle(.glass)
                .buttonBorderShape(.circle)
                .accessibilityLabel("Contents")
            }
        }
    }
}

/// A book in the Library: its backdrop as poster art, its cover, glass chips and actions.
struct BookPoster: View {
    let book: Book
    let open: (Route) -> Void

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            BookBackdrop(book: book)
            LinearGradient(colors: [.clear, .black.opacity(0.55)], startPoint: .center, endPoint: .bottom)
            VStack(alignment: .leading, spacing: 12) {
                HStack(alignment: .bottom, spacing: 16) {
                    CoverImage(book: book, width: 92)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(book.title).font(Typeface.serif(30)).foregroundStyle(.white).lineLimit(3).minimumScaleFactor(0.7)
                        Text(book.authors.joined(separator: ", ")).font(Typeface.serif(17, italic: true)).foregroundStyle(.white.opacity(0.8))
                    }
                }
                BookStats(book: book)
                BookActions(book: book, open: open).padding(.top, 4)
            }
            .padding(20)
        }
        .frame(height: 540)
        .clipShape(.rect(cornerRadius: 38))
        .overlay { RoundedRectangle(cornerRadius: 38).strokeBorder(.white.opacity(0.14), lineWidth: 1) }
        .environment(\.colorScheme, .dark)
        .environment(\.accent, CourseAccent(book.manifest.theme))
        .contentShape(.rect(cornerRadius: 38))
        .onTapGesture { open(.bookContents(book.id)) }
    }
}

// MARK: Contents page

/// A book's syllabus: backdrop hero, a glass rail of parts, and chapters grouped under them.
struct BookContentsView: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(\.accent) private var accent
    @AppStorage("lastItem") private var lastItem = ""
    let book: Book
    @State private var current: Int?

    private var currentTOC: Int? {
        shelf.location(book.id).flatMap { book.package.tocEntry(spine: $0.spine)?.id }
    }

    var body: some View {
        let parts = book.outline.parts
        ScrollViewReader { proxy in
            ScrollView {
                VStack(spacing: 0) {
                    BookHero(book: book)
                    if parts.count > 1 {
                        PartsMap(book: book, parts: parts) { id in withAnimation(.smooth) { proxy.scrollTo(id, anchor: .top) } }
                            .padding(.horizontal, 16)
                            .padding(.top, 18)
                    }
                    LazyVStack(alignment: .leading, spacing: 36) {
                        ForEach(parts) { part in
                            PartSection(book: book, part: part, currentTOC: currentTOC).id(part.id)
                        }
                    }
                    .scrollTargetLayout()
                    .padding(.horizontal, 16)
                    .padding(.top, 28)
                    .padding(.bottom, 40)
                }
            }
            .onScrollTargetVisibilityChange(idType: Int.self, threshold: 0.05) { ids in
                if let first = ids.min(), first != current { withAnimation(.snappy(duration: 0.25)) { current = first } }
            }
            .safeAreaBar(edge: .top) {
                if book.outline.hasParts && parts.count > 1 {
                    PartRail(parts: parts, current: current ?? 0) { id in withAnimation(.smooth) { proxy.scrollTo(id, anchor: .top) } }
                }
            }
        }
        .onAppear { lastItem = "book:" + book.id }
        .navigationTitle(book.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .principal) { Color.clear.frame(width: 1, height: 1) } }
    }
}

/// The shape of the book at a glance: one thin bar per part, filled to where you've read.
struct PartsMap: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(\.accent) private var accent
    let book: Book
    let parts: [BookOutline.Part]
    let select: (Int) -> Void

    var body: some View {
        let p = shelf.progress(book)
        VStack(alignment: .leading, spacing: 6) {
            GeometryReader { g in
                let gaps = CGFloat(parts.count - 1) * 3
                HStack(spacing: 3) {
                    ForEach(Array(parts.enumerated()), id: \.element.id) { i, part in
                        let r = book.partRange(i)
                        let f = book.progress(inPart: i, bookProgress: p)
                        let w = max(6, (g.size.width - gaps) * CGFloat(r.end - r.start))
                        ZStack(alignment: .leading) {
                            Capsule().fill(Color.secondary.opacity(0.18))
                            Capsule().fill(accent.pastel).frame(width: max(f > 0 ? 3 : 0, w * f))
                        }
                        .frame(width: w, height: 5)
                        .contentShape(.rect)
                        .onTapGesture { select(part.id) }
                        .accessibilityLabel("Part \(part.number ?? "\(i + 1)"), \(Int(f * 100)) percent read")
                    }
                }
            }
            .frame(height: 5)
            Text(p > 0 ? "\(Int((p * 100).rounded()))% read · \(parts.count) parts" : "\(parts.count) parts")
                .font(.caption)
                .foregroundStyle(.secondary)
                .monospacedDigit()
        }
    }
}

struct BookHero: View {
    let book: Book

    var body: some View {
        HStack(alignment: .bottom, spacing: 18) {
            VStack(alignment: .leading, spacing: 10) {
                Spacer(minLength: 0)
                Text(book.authors.joined(separator: ", ").uppercased())
                    .font(.caption.weight(.semibold))
                    .tracking(1.6)
                    .foregroundStyle(.white.opacity(0.6))
                Text(book.title).font(Typeface.serif(36)).foregroundStyle(.white).lineLimit(3).minimumScaleFactor(0.6)
                if let s = book.manifest.subtitle {
                    Text(s).font(Typeface.serif(17, italic: true)).foregroundStyle(.white.opacity(0.78))
                }
            }
            Spacer(minLength: 0)
            CoverImage(book: book, width: 96)
        }
        .padding(.horizontal, 20)
        .padding(.bottom, 24)
        .frame(height: 340)
        .background(alignment: .bottom) {
            BookBackdrop(book: book).frame(height: 940)
        }
        .environment(\.colorScheme, .dark)
    }
}

struct PartRail: View {
    @Environment(\.accent) private var accent
    let parts: [BookOutline.Part]
    let current: Int
    let select: (Int) -> Void

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView(.horizontal) {
                GlassEffectContainer(spacing: 6) {
                    HStack(spacing: 6) {
                        ForEach(parts) { part in
                            let on = part.id == current
                            Button { select(part.id) } label: {
                                HStack(spacing: 7) {
                                    Text(part.number ?? "\(part.id + 1)").monospacedDigit().fontWeight(.bold)
                                    if on, !part.title.isEmpty { Text(part.title).lineLimit(1) }
                                }
                                .font(.subheadline)
                                .foregroundStyle(on ? accent.onPastel : Color.primary)
                                .padding(.horizontal, 14)
                                .padding(.vertical, 9)
                                .contentShape(.capsule)
                            }
                            .buttonStyle(.plain)
                            .glassEffect(on ? Glass.regular.tint(accent.pastel.opacity(0.9)).interactive() : Glass.regular.interactive(), in: .capsule)
                            .id(part.id)
                            .accessibilityLabel("Part \(part.number ?? ""), \(part.title)")
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 6)
                }
            }
            .scrollIndicators(.hidden)
            .onChange(of: current) { _, c in withAnimation(.smooth) { proxy.scrollTo(c, anchor: .center) } }
        }
    }
}

struct PartSection: View {
    @Environment(\.accent) private var accent
    let book: Book
    let part: BookOutline.Part
    let currentTOC: Int?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if !part.title.isEmpty && !part.chapters.isEmpty {
                Text("PART \(part.number ?? "\(part.id + 1)")")
                    .font(.caption.weight(.semibold))
                    .tracking(1.4)
                    .foregroundStyle(.secondary)
                if let entry = part.entry {
                    NavigationLink(value: Route.book(id: book.id, toc: entry.id)) {
                        Text(part.title).font(Typeface.serif(28)).foregroundStyle(.primary)
                    }
                    .buttonStyle(.plain)
                } else {
                    Text(part.title).font(Typeface.serif(28))
                }
            }
            let rows = part.chapters.isEmpty ? (part.entry.map { [$0] } ?? []) : part.chapters
            VStack(spacing: 0) {
                ForEach(Array(rows.enumerated()), id: \.element.id) { i, ch in
                    if i > 0 { Divider().padding(.leading, 62) }
                    NavigationLink(value: Route.book(id: book.id, toc: ch.id)) {
                        HStack(alignment: .firstTextBaseline, spacing: 10) {
                            Text(ch.number ?? "")
                                .font(.subheadline.weight(.medium))
                                .monospacedDigit()
                                .foregroundStyle(.secondary)
                                .frame(width: 36, alignment: .leading)
                            Text(ch.title).font(Typeface.serif(17)).foregroundStyle(.primary)
                            Spacer(minLength: 6)
                            if ch.id == currentTOC {
                                Circle().fill(accent.pastel).frame(width: 9, height: 9)
                                    .accessibilityLabel("You are here")
                            }
                            Image(systemName: "chevron.right").font(.footnote.weight(.semibold)).foregroundStyle(.tertiary)
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 14)
                        .contentShape(.rect)
                    }
                    .buttonStyle(.plain)
                }
            }
            .background(.background.secondary, in: .rect(cornerRadius: 22))
            .padding(.top, 4)
        }
    }
}

// MARK: Unlock

struct LockedBooksCard: View {
    @Environment(Bookshelf.self) private var shelf
    @State private var showUnlock = false

    var body: some View {
        Button { showUnlock = true } label: {
            HStack(spacing: 14) {
                Image(systemName: "lock.fill").font(.title3).frame(width: 44, height: 44).glassEffect(.regular, in: .circle)
                VStack(alignment: .leading, spacing: 2) {
                    Text(shelf.lockedCount == 1 ? "1 book is locked" : "\(shelf.lockedCount) books are locked").font(.headline)
                    Text("Enter your library passphrase once to open them on this iPhone.").font(.subheadline).foregroundStyle(.secondary)
                }
                Spacer(minLength: 0)
            }
            .padding(16)
            .background(.background.secondary, in: .rect(cornerRadius: 24))
        }
        .buttonStyle(.plain)
        .sheet(isPresented: $showUnlock) { UnlockSheet().presentationDetents([.medium]) }
    }
}

struct UnlockSheet: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(\.dismiss) private var dismiss
    @State private var passphrase = ""

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    SecureField("Library passphrase", text: $passphrase)
                        .textContentType(.password)
                        .submitLabel(.go)
                        .onSubmit(unlock)
                } footer: {
                    Text(shelf.unlockError ?? "Your books ship encrypted inside the app. The passphrase stays in this iPhone’s Keychain.")
                        .foregroundStyle(shelf.unlockError == nil ? Color.secondary : Color.red)
                }
            }
            .navigationTitle("Unlock books")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    if shelf.isUnlocking { ProgressView() } else { Button("Unlock", action: unlock).disabled(passphrase.isEmpty) }
                }
            }
        }
    }

    private func unlock() {
        Task {
            await shelf.unlock(passphrase)
            if shelf.unlockError == nil { dismiss() }
        }
    }
}

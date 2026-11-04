import SwiftUI
import UIKit
import ImageIO
import BookKit

/// Pre-rendered landing art that changes with the reader's place in the book: one still per stage (`stage-N.jpg`)
/// with an optional layer of spacecraft (`objects-N.png`) that floats over it. Stages map to parts; late in a part
/// the art blends toward the next stage.
struct StageSet: Equatable {
    let base: [URL]
    let objects: [URL?]
    var count: Int { base.count }

    static func load(_ dir: URL?) -> StageSet? {
        guard let dir else { return nil }
        var base: [URL] = [], objects: [URL?] = []
        let fm = FileManager.default
        for n in 1...32 {
            let b = dir.appendingPathComponent("stage-\(n).jpg")
            guard fm.fileExists(atPath: b.path) else { break }
            base.append(b)
            let o = dir.appendingPathComponent("objects-\(n).png")
            objects.append(fm.fileExists(atPath: o.path) ? o : nil)
        }
        return base.isEmpty ? nil : StageSet(base: base, objects: objects)
    }
}

struct StagePosition: Equatable {
    var index = 0, next = 0
    var blend = 0.0

    /// Stage for the reader's location: part index scaled onto the stages, blending over the last quarter of a part.
    static func current(for book: Book, location: BookLocation?, count: Int) -> StagePosition {
        guard count > 1, let loc = location, let entry = book.package.tocEntry(spine: loc.spine),
              let part = book.outline.part(containingTOC: entry.id) else { return StagePosition() }
        let parts = book.outline.parts
        guard let pi = parts.firstIndex(where: { $0.id == part.id }) else { return StagePosition() }
        let f = book.progress(inPart: pi, bookProgress: book.package.progress(spine: loc.spine, fraction: loc.fraction))
        let x = (Double(pi) + f) * Double(count) / Double(max(parts.count, 1))
        let i = min(count - 1, max(0, Int(x)))
        let frac = x - Double(i)
        let t = min(1, max(0, (frac - 0.75) / 0.25))
        return StagePosition(index: i, next: min(count - 1, i + 1), blend: i == count - 1 ? 0 : t * t * (3 - 2 * t))
    }
}

enum StageImages {
    private static let cache = NSCache<NSURL, UIImage>()

    /// Decodes at screen size, not the file's full size.
    static func image(_ url: URL, maxPixel: CGFloat) -> UIImage? {
        if let hit = cache.object(forKey: url as NSURL) { return hit }
        guard let src = CGImageSourceCreateWithURL(url as CFURL, nil) else { return nil }
        let opts: [CFString: Any] = [kCGImageSourceCreateThumbnailFromImageAlways: true,
                                     kCGImageSourceThumbnailMaxPixelSize: maxPixel,
                                     kCGImageSourceCreateThumbnailWithTransform: true,
                                     kCGImageSourceShouldCacheImmediately: true]
        guard let cg = CGImageSourceCreateThumbnailAtIndex(src, 0, opts as CFDictionary) else { return nil }
        let img = UIImage(cgImage: cg)
        cache.setObject(img, forKey: url as NSURL)
        return img
    }
}

/// The stage art, alive: a slow drift on the still, spacecraft floating on their own layer with deeper tilt
/// parallax, and a few stars that glint.
struct LandingStages: View {
    let set: StageSet
    let position: StagePosition
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    @Environment(\.displayScale) private var displayScale
    @State private var tilt = Tilt.shared

    var body: some View {
        GeometryReader { geo in
            let maxPixel = max(geo.size.width, geo.size.height) * displayScale
            TimelineView(.animation(minimumInterval: 1.0 / 30, paused: reduceMotion)) { tl in
                let t = reduceMotion ? 0 : tl.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 100_000)
                let tx = reduceMotion ? 0 : tilt.x, ty = reduceMotion ? 0 : tilt.y
                ZStack {
                    stage(position.index, t: t, tx: tx, ty: ty, size: geo.size, maxPixel: maxPixel)
                    if position.blend > 0 {
                        stage(position.next, t: t, tx: tx, ty: ty, size: geo.size, maxPixel: maxPixel).opacity(position.blend)
                    }
                    Canvas { ctx, size in Glints.draw(&ctx, size: size, t: t) }
                        .allowsHitTesting(false)
                }
            }
        }
        .ignoresSafeArea()
        .background(Color.black)
        .animation(.smooth(duration: 1.2), value: position)
        .onAppear { if !reduceMotion { tilt.start() } }
        .onDisappear { tilt.stop() }
        .accessibilityHidden(true)
    }

    @ViewBuilder
    private func stage(_ i: Int, t: Double, tx: Double, ty: Double, size: CGSize, maxPixel: CGFloat) -> some View {
        let drift = 1.035 + 0.012 * sin(t / 23)
        ZStack {
            if let img = StageImages.image(set.base[i], maxPixel: maxPixel) {
                Image(uiImage: img).resizable().scaledToFill()
                    .frame(width: size.width, height: size.height)
                    .scaleEffect(drift)
                    .offset(x: tx * 7, y: ty * 7)
            }
            if let url = set.objects[i], let img = StageImages.image(url, maxPixel: maxPixel) {
                Image(uiImage: img).resizable().scaledToFill()
                    .frame(width: size.width, height: size.height)
                    .scaleEffect(drift)
                    .offset(x: tx * 18 + 3 * sin(t / 7), y: ty * 18 + 5 * sin(t / 4.7))
            }
        }
        .frame(width: size.width, height: size.height)
        .clipped()
    }
}

/// A handful of stars that flare and fade, scattered over the open sky.
enum Glints {
    static func rnd(_ i: Int, _ salt: Int) -> Double {
        var z = UInt64(truncatingIfNeeded: i) &* 0x9E3779B97F4A7C15 &+ UInt64(truncatingIfNeeded: salt) &* 0x632BE59BD9B4E019
        z = (z ^ (z >> 30)) &* 0xBF58476D1CE4E5B9; z = (z ^ (z >> 27)) &* 0x94D049BB133111EB; z ^= z >> 31
        return Double(z >> 11) / Double(1 << 53)
    }

    static func draw(_ ctx: inout GraphicsContext, size: CGSize, t: Double) {
        for i in 0..<14 {
            let fx = rnd(i, 11), fy = rnd(i, 29) * 0.42
            let period = 5 + rnd(i, 47) * 7
            let phase = (t / period + rnd(i, 61)).truncatingRemainder(dividingBy: 1)
            let a = max(0, sin(phase * .pi * 2)) * (phase < 0.5 ? 1 : 0)
            guard a > 0.02 else { continue }
            let p = CGPoint(x: fx * size.width, y: fy * size.height)
            let r = (1.2 + rnd(i, 83) * 1.6) * a
            let gold = Color(red: 1, green: 0.9, blue: 0.72)
            ctx.fill(Path(ellipseIn: CGRect(x: p.x - r, y: p.y - r, width: r * 2, height: r * 2)), with: .color(gold.opacity(a)))
            var spike = Path()
            spike.move(to: CGPoint(x: p.x - r * 6, y: p.y)); spike.addLine(to: CGPoint(x: p.x + r * 6, y: p.y))
            spike.move(to: CGPoint(x: p.x, y: p.y - r * 6)); spike.addLine(to: CGPoint(x: p.x, y: p.y + r * 6))
            ctx.stroke(spike, with: .color(gold.opacity(a * 0.55)), lineWidth: 0.6)
        }
    }
}

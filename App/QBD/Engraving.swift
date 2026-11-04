import SwiftUI
import UIKit
import BookKit

/// A chapter's engraving: ink line art (white-on-black luminance, tinted per theme) over a soft pastel wash.
/// Files live beside the book in `art/scenes/<chapter file stem>-{p,b}-{ink,wash}.png`; p = portrait, b = band.
struct EngravingFiles: Equatable {
    let ink: URL
    let wash: URL?
}

extension Bookshelf {
    func engraving(for book: Book, href: String, band: Bool) -> EngravingFiles? {
        let stem = (href as NSString).deletingPathExtension.replacingOccurrences(of: "/", with: "_")
        let dir = Self.root.appendingPathComponent(book.id).appendingPathComponent("art/scenes", isDirectory: true)
        let f = band ? "b" : "p"
        let ink = dir.appendingPathComponent("\(stem)-\(f)-ink.png")
        guard FileManager.default.fileExists(atPath: ink.path) else { return nil }
        let wash = dir.appendingPathComponent("\(stem)-\(f)-wash.png")
        return EngravingFiles(ink: ink, wash: FileManager.default.fileExists(atPath: wash.path) ? wash : nil)
    }
}

/// Colours for drawing an engraving on a given surface.
struct EngravingInk {
    var paper: Color
    var ink: Color
    var wash: Double

    static let paper = EngravingInk(paper: Color(hex: 0xF4ECD8), ink: Color(hex: 0x2B3428), wash: 0.9)
    static let night = EngravingInk(paper: Color(hex: 0x12110D), ink: Color(hex: 0xE6DCC4), wash: 0.28)

    static func reading(_ t: ReadingTheme) -> EngravingInk {
        switch t {
        case .paper: EngravingInk(paper: t.background, ink: Color(hex: 0x2A2A26), wash: 0.8)
        case .sepia: EngravingInk(paper: t.background, ink: Color(hex: 0x3A2E20), wash: 0.75)
        case .dusk: EngravingInk(paper: t.background, ink: Color(hex: 0xD9CCAE), wash: 0.24)
        case .night: EngravingInk(paper: t.background, ink: Color(hex: 0xD8D8D2), wash: 0.2)
        }
    }
}

/// Draws an engraving. `reveal` 0…1 sketches the ink in from the upper left; the wash bleeds in after it.
struct EngravingView: View {
    let files: EngravingFiles
    var colours = EngravingInk.paper
    var reveal = 1.0
    @Environment(\.displayScale) private var displayScale

    var body: some View {
        GeometryReader { geo in
            let maxPixel = max(geo.size.width, geo.size.height) * displayScale
            ZStack {
                colours.paper
                if let w = files.wash, let img = StageImages.image(w, maxPixel: maxPixel / 3) {
                    Image(uiImage: img).resizable().scaledToFill()
                        .frame(width: geo.size.width, height: geo.size.height)
                        .opacity(colours.wash * max(0, min(1, (reveal - 0.45) / 0.55)))
                }
                if let img = StageImages.image(files.ink, maxPixel: maxPixel) {
                    // The ink file is white lines on black: luminance becomes the mask for the ink colour.
                    colours.ink
                        .mask { Image(uiImage: img).resizable().scaledToFill().frame(width: geo.size.width, height: geo.size.height).luminanceToAlpha() }
                        .frame(width: geo.size.width, height: geo.size.height)
                        .mask {
                            if reveal >= 1 { Rectangle() } else {
                                let r = reveal * 1.25
                                LinearGradient(stops: [.init(color: .black, location: max(0, r - 0.25)),
                                                       .init(color: .clear, location: max(0.0001, min(1, r)))],
                                               startPoint: .topLeading, endPoint: .bottomTrailing)
                            }
                        }
                }
            }
            .frame(width: geo.size.width, height: geo.size.height)
            .clipped()
        }
        .accessibilityHidden(true)
    }
}

/// The landing in the engraving style: the scene of the chapter you are in. When the chapter has changed since you
/// last came home, the new scene draws itself in. It breathes slightly and tilts with the phone.
struct EngravingBackdrop: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(\.accessibilityReduceMotion) private var reduceMotion
    let book: Book
    var colours = EngravingInk.paper
    @State private var tilt = Tilt.shared
    @State private var start = Date.distantPast
    @AppStorage("engravingSeen") private var seen = ""

    private var href: String? {
        guard let c = shelf.companion(for: book) else { return nil }
        let spine = (LaunchState.sceneOverride ?? shelf.location(book.id))?.spine ?? 0
        return (c.chapter(atSpine: spine) ?? c.companion.chapters.first)?.href
    }

    var body: some View {
        if let href, let files = shelf.engraving(for: book, href: href, band: false) {
            TimelineView(.animation(minimumInterval: 1.0 / 30, paused: reduceMotion)) { tl in
                let t = tl.date.timeIntervalSinceReferenceDate
                let reveal = reduceMotion || LaunchState.isScreenshotting ? 1 : min(1, tl.date.timeIntervalSince(start) / 2.6)
                EngravingView(files: files, colours: colours, reveal: reveal)
                    .scaleEffect(1.04 + 0.01 * sin(t / 17))
                    .offset(x: reduceMotion ? 0 : tilt.x * 9, y: reduceMotion ? 0 : tilt.y * 9)
            }
            .background(colours.paper)
            .onAppear {
                if !reduceMotion { tilt.start() }
                let key = "\(book.id):\(href)"
                if seen != key { start = Date(); seen = key }
            }
            .onDisappear { tilt.stop() }
        } else {
            CoverBackdrop(book: book)
        }
    }
}

import SwiftUI
import UIKit
import BookKit

// MARK: Backdrops

/// A book's landing backdrop, chosen in its book.json (`theme.landing`).
struct BookBackdrop: View {
    let book: Book
    var style: String? = nil

    var body: some View {
        switch style ?? LaunchState.landingOverride ?? book.manifest.theme?.landing ?? "cover" {
        case "web": WebBackdrop()
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
struct WebBackdrop: View {
    @Environment(\.accessibilityReduceMotion) private var reduceMotion

    var body: some View {
        TimelineView(.animation(minimumInterval: 1.0 / 30, paused: reduceMotion)) { timeline in
            let t = reduceMotion ? 12 : timeline.date.timeIntervalSinceReferenceDate.truncatingRemainder(dividingBy: 100_000)
            Canvas { ctx, size in WebPainter.draw(&ctx, size: size, t: t) }
        }
        .accessibilityHidden(true)
    }
}

enum WebPainter {
    static func draw(_ ctx: inout GraphicsContext, size: CGSize, t: Double) {
        let w = size.width, h = size.height
        ctx.fill(Path(CGRect(origin: .zero, size: size)),
                 with: .linearGradient(Gradient(colors: [Color(hex: 0x05080A), Color(hex: 0x0B1712), Color(hex: 0x0E2016)]),
                                       startPoint: .zero, endPoint: CGPoint(x: 0, y: h)))
        for s in SkyPainter.stars.prefix(110) {
            let a = 0.15 + 0.35 * (0.5 + 0.5 * sin(t * 0.7 + s.phase))
            ctx.fill(Path(ellipseIn: CGRect(x: s.x * w - s.r, y: s.y * h * 0.7 - s.r, width: 2 * s.r, height: 2 * s.r)), with: .color(.white.opacity(a)))
        }

        // A green world rising from the bottom, with atmosphere and a thin orbital ring.
        let R = w * 1.25
        let pc = CGPoint(x: w * 0.62, y: h + R * 0.62)
        ctx.fill(Path(ellipseIn: CGRect(x: pc.x - R - 26, y: pc.y - R - 26, width: 2 * R + 52, height: 2 * R + 52)),
                 with: .radialGradient(Gradient(colors: [.clear, Color(hex: 0x9FE0B0).opacity(0.25), .clear]),
                                       center: pc, startRadius: R - 4, endRadius: R + 26))
        ctx.fill(Path(ellipseIn: CGRect(x: pc.x - R, y: pc.y - R, width: 2 * R, height: 2 * R)),
                 with: .linearGradient(Gradient(colors: [Color(hex: 0x3F7A52), Color(hex: 0x1C3A27), Color(hex: 0x0A1A10)]),
                                       startPoint: CGPoint(x: pc.x - R * 0.3, y: pc.y - R), endPoint: CGPoint(x: pc.x + R * 0.2, y: pc.y - R * 0.6)))
        var ring = Path()
        ring.addEllipse(in: CGRect(x: pc.x - R * 1.18, y: pc.y - R * 1.02, width: R * 2.36, height: R * 0.5))
        ctx.stroke(ring, with: .color(Color(hex: 0xCFE8D5).opacity(0.18)), lineWidth: 0.8)
        let station = CGPoint(x: pc.x - R * 0.72, y: pc.y - R * 0.86)
        ctx.fill(Path(ellipseIn: CGRect(x: station.x - 2.5, y: station.y - 2.5, width: 5, height: 5)), with: .color(Color(hex: 0xF4F1E6)))

        // The web: anchored off the top-left, radial threads and a spiral, swaying gently.
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
        for a in angles {
            var p = Path(); p.move(to: hub); p.addLine(to: point(a, reach))
            ctx.stroke(p, with: .color(silk.opacity(0.16)), lineWidth: 0.6)
        }
        var spiral = Path()
        var first = true
        var r = 14.0
        while r < reach * 0.82 {
            for a in angles {
                let pt = point(a, r)
                if first { spiral.move(to: pt); first = false } else { spiral.addLine(to: pt) }
                r += 22.0 / Double(spokes) * (1 + r / 260)
            }
        }
        ctx.stroke(spiral, with: .color(silk.opacity(0.13)), lineWidth: 0.5)

        // Dew on the threads
        for (k, s) in SkyPainter.stars.prefix(48).enumerated() {
            let a = angles[k % spokes]
            let pt = point(a, 30 + s.x * reach * 0.75)
            let glint = 0.25 + 0.6 * pow(0.5 + 0.5 * sin(t * 1.3 + s.phase * 3), 6)
            let rr = 0.8 + s.r * 0.9
            ctx.fill(Path(ellipseIn: CGRect(x: pt.x - rr, y: pt.y - rr, width: 2 * rr, height: 2 * rr)), with: .color(silk.opacity(glint)))
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

/// Home for a book: the same shape as a course landing, in the book's own style.
struct BookLanding: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(\.accent) private var accent
    let book: Book
    @Binding var showSettings: Bool
    let open: (Route) -> Void

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

                VStack(alignment: .leading, spacing: 14) {
                    Spacer(minLength: 0)
                    if book.manifest.theme?.landing == "cover" || book.manifest.theme?.landing == nil {
                        CoverImage(book: book, width: 120).padding(.bottom, 10)
                    }
                    Text(shelf.location(book.id) == nil ? "UP NEXT" : "NOW READING")
                        .font(.caption.weight(.semibold))
                        .tracking(2)
                        .foregroundStyle(.white.opacity(0.6))
                    Text(book.title)
                        .font(Typeface.serif(46))
                        .foregroundStyle(.white)
                        .lineLimit(3)
                        .minimumScaleFactor(0.55)
                    Text(book.manifest.subtitle ?? book.authors.joined(separator: ", "))
                        .font(Typeface.serif(20, italic: true))
                        .foregroundStyle(.white.opacity(0.75))
                    if book.manifest.subtitle != nil, !book.authors.isEmpty {
                        Text(book.authors.joined(separator: ", ")).font(.subheadline).foregroundStyle(.white.opacity(0.6))
                    }
                    BookStats(book: book).padding(.top, 4)
                    BookActions(book: book, open: open).padding(.top, 8)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 24)
                .padding(.bottom, 28)
                .containerRelativeFrame(.vertical) { h, _ in h * 0.82 }
            }
        }
        .scrollIndicators(.hidden)
        .background { BookBackdrop(book: book).ignoresSafeArea() }
        .environment(\.colorScheme, .dark)
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
                    Text("Contents").font(.headline).foregroundStyle(.primary).padding(.horizontal, 10).padding(.vertical, 8)
                }
                .buttonStyle(.glass)
            }
        }
    }
}

/// A book in the Library: its backdrop as poster art, its cover, and the same glass chips and actions as a course.
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

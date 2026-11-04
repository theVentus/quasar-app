import SwiftUI
import Combine
import UIKit
import WebKit
import BookKit

/// Faces offered for books. `publisher` keeps the book's own fonts.
enum BookFont: String, CaseIterable, Identifiable {
    case cmu, newYork, charter, iowan, georgia, sans, publisher
    var id: String { rawValue }
    var label: String {
        switch self {
        case .cmu: "Computer Modern"; case .newYork: "New York"; case .charter: "Charter"; case .iowan: "Iowan"
        case .georgia: "Georgia"; case .sans: "San Francisco"; case .publisher: "Original"
        }
    }
    var css: String? {
        switch self {
        case .cmu: "'QBD CMU Serif', serif"
        case .newYork: "ui-serif, 'New York', serif"
        case .charter: "Charter, 'Charter BT', serif"
        case .iowan: "'Iowan Old Style', serif"
        case .georgia: "Georgia, serif"
        case .sans: "-apple-system, system-ui, sans-serif"
        case .publisher: nil
        }
    }
    /// How the chip previews the face in SwiftUI.
    var preview: Font {
        switch self {
        case .cmu: Typeface.serif(17)
        case .newYork: .system(size: 17, design: .serif)
        case .charter: .custom("Charter-Roman", size: 17)
        case .iowan: .custom("IowanOldStyle-Roman", size: 17)
        case .georgia: .custom("Georgia", size: 17)
        case .sans: .system(size: 17)
        case .publisher: .system(size: 15, weight: .medium)
        }
    }
}

/// Everything the page layout depends on. A change re-lays the chapter and keeps the reader's place.
struct BookStyle: Equatable {
    var theme: ReadingTheme
    var size: Double
    var font: BookFont
    var spacing: Double
    var margin: Int
    var justify: Bool
    var paged: Bool
    var accent: String
    var turn: String = "slide"
    var finish: Bool = true
}

enum BookTarget: Equatable {
    case fraction(Double)
    case end
    case anchor(String)
    /// The page containing this passage (a highlight being reopened).
    case text(String)
}

struct Passage: Identifiable {
    let id = UUID()
    let text: String
}

/// What the reader did with a selected passage.
enum SelectionAction: String { case highlight, ask }

/// Reading a book: the same chrome as a lesson (floating glass bar, Aa panel, contents) around a paginated web view.
struct BookReaderView: View {
    @Environment(Bookshelf.self) private var shelf
    @Environment(\.accent) private var accent
    let bookID: String
    let startTOC: Int?
    var startHighlight: UUID? = nil
    @Environment(HighlightStore.self) private var highlights
    @State private var askPassage: Passage?
    @State private var showWhosWho = false
    @State private var titleCard: Companion.Chapter?
    @State private var entityCard: Companion.Entity?
    @State private var xrayFocus: String?
    @State private var previously: Companion.Chapter?
    @AppStorage("chapterOpeners") private var chapterOpeners = true

    @AppStorage("theme") private var themeRaw = ReadingTheme.sepia.rawValue
    @AppStorage("textSize") private var textSize = 18.0
    @AppStorage("bookFont") private var fontRaw = BookFont.cmu.rawValue
    @AppStorage("bookSpacing") private var spacing = 1.5
    @AppStorage("bookMargin") private var margin = 1
    @AppStorage("bookJustify") private var justify = true
    @AppStorage("bookPaged") private var paged = true
    @AppStorage("bookTurn") private var turnRaw = "slide"
    @AppStorage("bookFinish") private var finish = true
    @AppStorage("lastItem") private var lastItem = ""
    @Environment(\.colorScheme) private var systemScheme

    @State private var spine = 0
    @State private var target: BookTarget = .fraction(0)
    @State private var loadToken = 0
    @State private var page = 0
    @State private var pages = 1
    @State private var fraction = 0.0
    @State private var chrome = true
    @State private var panelOpen = false
    @State private var showContents = false
    @State private var started = false
    @State private var reentry: String?

    private var theme: ReadingTheme { ReadingTheme.resolve(themeRaw) }
    private var book: Book? { shelf.book(bookID) }

    var body: some View {
        Group {
            if let book {
                reader(book)
            } else {
                ContentUnavailableView("Book unavailable", systemImage: "book.closed", description: Text("Unlock your library to read this book."))
            }
        }
        .toolbar(.hidden, for: .tabBar)
        .toolbar(chrome ? .visible : .hidden, for: .navigationBar)
        .navigationBarBackButtonHidden(!chrome)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar { ToolbarItem(placement: .principal) { Color.clear.frame(width: 1, height: 1) } }
        .onAppear { lastItem = "book:" + bookID }
    }

    @ViewBuilder
    private func reader(_ book: Book) -> some View {
        let style = BookStyle(theme: theme, size: textSize, font: BookFont(rawValue: fontRaw) ?? .cmu, spacing: spacing,
                              margin: margin, justify: justify, paged: paged, accent: accentHex(book), turn: turnRaw, finish: finish)
        let entry = book.package.tocEntry(spine: spine)
        let chapter = entry.flatMap { book.outline.chapter(forTOC: $0.id) }
        let sectionTitle = chapter.map { [$0.number, $0.title].compactMap { $0 }.joined(separator: "  ") } ?? book.title
        let overall = book.package.progress(spine: spine, fraction: fraction)
        let companion = shelf.companion(for: book)
        let scene = companion?.chapter(atSpine: spine)

        ZStack(alignment: .bottom) {
            theme.background.ignoresSafeArea()
            BookWebView(book: book, spine: spine, target: target, loadToken: loadToken, style: style,
                        marks: highlights.highlights(for: book.id, spine: spine).map(\.text),
                        names: companion?.nameMap(at: spine) ?? [],
                        tint: scene?.palette.dropFirst().first,
                        onEntity: { id in entityCard = companion?.companion.entities.first { $0.id == id } },
                        onSelect: { action, text in
                            let t = text.trimmingCharacters(in: .whitespacesAndNewlines)
                            guard !t.isEmpty else { return }
                            switch action {
                            case .highlight:
                                highlights.add(Highlight(book: book.id, spine: spine, text: t, chapter: sectionTitle))
                            case .ask:
                                askPassage = Passage(text: t)
                            }
                        },
                        onLocation: { s, f, p, n in
                            spine = s; fraction = f; page = p; pages = n
                            shelf.save(BookLocation(spine: s, fraction: f), for: book.id)
                            if started, chrome, !panelOpen { withAnimation(.smooth) { chrome = false } }
                            started = true
                        },
                        onTap: { withAnimation(.smooth) { chrome.toggle(); if !chrome { panelOpen = false } } },
                        onEdge: { dir in step(book, dir) })
                .ignoresSafeArea()

            if let card = titleCard {
                let ch = book.package.tocEntry(spine: spine).flatMap { book.outline.chapter(forTOC: $0.id) }
                ChapterTitleCard(chapter: card, number: ch?.number, storyline: companion?.companion.storylines[card.storyline],
                                 seed: spine) { withAnimation(.smooth(duration: 0.5)) { titleCard = nil } }
                    .transition(.opacity)
                    .zIndex(2)
            }
            if let prev = previously {
                PreviouslyCard(chapter: prev) { withAnimation(.smooth) { previously = nil } }
                    .padding(.horizontal, 16)
                    .padding(.bottom, chrome ? 8 : 40)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                    .zIndex(1)
            }
            if let reentry, previously == nil {
                Text(reentry)
                    .font(.footnote.weight(.medium))
                    .foregroundStyle(theme.ink)
                    .padding(.horizontal, 16).padding(.vertical, 10)
                    .glassEffect(.regular, in: .capsule)
                    .padding(.bottom, chrome ? 0 : 24)
                    .transition(.move(edge: .bottom).combined(with: .opacity))
                    .allowsHitTesting(false)
                    .accessibilityLabel(reentry)
            }
            if !chrome {
                Text(pagesLeftLabel)
                    .font(.caption2.weight(.medium))
                    .monospacedDigit()
                    .foregroundStyle(theme.ink3)
                    .padding(.bottom, 6)
                    .allowsHitTesting(false)
                    .transition(.opacity)
            }
        }
        .safeAreaBar(edge: .bottom) {
            if chrome {
                BookBar(style: style, fontRaw: $fontRaw, spacing: $spacing, margin: $margin, justify: $justify, paged: $paged, turnRaw: $turnRaw, finish: $finish,
                        themeRaw: $themeRaw, textSize: $textSize, panelOpen: $panelOpen,
                        section: sectionTitle, progress: overall, showContents: { showContents = true }, showPeople: { showWhosWho = true })
                    .transition(.move(edge: .bottom).combined(with: .opacity))
            }
        }
        .environment(\.reading, ReadingStyle(theme: theme, size: textSize))
        .environment(\.colorScheme, theme.scheme)
        .toolbarColorScheme(theme.scheme, for: .navigationBar)
        .statusBarHidden(!chrome || theme.scheme != systemScheme)
        .sheet(isPresented: $showContents) {
            BookContentsSheet(book: book, currentTOC: entry?.id) { tocID in
                showContents = false
                jump(book, toc: tocID)
            }
            .presentationDetents([.medium, .large])
        }
        .sheet(item: $askPassage) { passage in
            AskSheet(title: book.title, author: book.authors.joined(separator: ", "), location: sectionTitle, passage: passage.text,
                     context: companion.map { askContext($0) } ?? "")
                .presentationDetents([.medium, .large])
        }
        .sheet(isPresented: $showWhosWho) {
            if let companion {
                XRaySheet(index: companion, spine: spine, focus: xrayFocus).presentationDetents([.medium, .large])
            } else {
                WhosWhoSheet(book: book, spine: spine).presentationDetents([.medium, .large])
            }
        }
        .sheet(item: $entityCard) { e in
            if let companion {
                EntityCard(index: companion, entity: e, spine: spine) {
                    entityCard = nil
                    xrayFocus = e.id
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { showWhosWho = true }
                }
            }
        }
        .onChange(of: showWhosWho) { _, open in if !open { xrayFocus = nil } }
        .onAppear { if !started { begin(book) } }
        .onReceive(NotificationCenter.default.publisher(for: .bookJump)) { n in
            guard let s = n.userInfo?["spine"] as? Int else { return }
            let f = n.userInfo?["fragment"] as? String ?? ""
            spine = s
            target = f.isEmpty ? .fraction(0) : .anchor(f)
            loadToken += 1
        }
    }

    private var pagesLeftLabel: String {
        guard paged else { return "\(Int((fraction * 100).rounded()))%" }
        let left = max(0, pages - page - 1)
        return left == 0 ? "Last page in chapter" : left == 1 ? "1 page left in chapter" : "\(left) pages left in chapter"
    }

    private func accentHex(_ book: Book) -> String { book.manifest.theme?.accent ?? "#A9C4F5" }

    /// What Claude may know: recaps of chapters already finished and who the reader has met, as of now.
    private func askContext(_ c: CompanionIndex) -> String {
        let done = c.chaptersRead(through: spine).dropLast().suffix(8)
        let recaps = done.map { "- \($0.title): \($0.recap)" }.joined(separator: "\n")
        let people = c.known(at: spine).prefix(30).map { "- \($0.entity.name): \($0.text)" }.joined(separator: "\n")
        return "Recaps of recent chapters the reader has finished:\n\(recaps)\n\nPeople, places and terms the reader has met so far:\n\(people)"
    }

    /// Shows the chapter opener when a chapter starts from its first page.
    private func openChapter(_ book: Book, at s: Int) {
        guard chapterOpeners, let c = shelf.companion(for: book), let ch = c.chapter(atSpine: s), c.spine(of: ch.href) == s else { return }
        withAnimation(.smooth(duration: 0.4)) { titleCard = ch }
    }

    private func begin(_ book: Book) {
        if LaunchState.showPeople { DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { showWhosWho = true } }
        if let h = startHighlight, let hl = highlights.all.first(where: { $0.id == h }) {
            spine = hl.spine; target = .text(hl.text); loadToken += 1; return
        }
        if let t = startTOC ?? LaunchState.openTOC {
            jump(book, toc: t)
            if let e = book.package.toc.first(where: { $0.id == t }), let s = e.spineIndex {
                if LaunchState.showOpener { openChapter(book, at: s) }
                if LaunchState.showReentry, let prev = shelf.companion(for: book)?.previousRecap(before: s) {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { withAnimation(.smooth) { previously = prev } }
                }
            }
            return
        }
        if let l = shelf.location(book.id) {
            spine = l.spine; target = .fraction(l.fraction)
            // Away for a while: name the chapter you're picking up, briefly.
            if Date().timeIntervalSince(l.updated) > 4 * 3600 || LaunchState.showReentry,
               let e = book.package.tocEntry(spine: l.spine), let ch = book.outline.chapter(forTOC: e.id) {
                let part = book.outline.part(containingTOC: e.id)
                let label = [ch.number, ch.title].compactMap { $0 }.joined(separator: "  ")
                let text = "Picking up · " + (part.map { !$0.title.isEmpty && $0.entry?.id != ch.id ? "\($0.title) · " : "" } ?? "") + label
                if let prev = shelf.companion(for: book)?.previousRecap(before: l.spine) {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { withAnimation(.smooth) { previously = prev } }
                } else {
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.6) { withAnimation(.smooth) { reentry = text } }
                    DispatchQueue.main.asyncAfter(deadline: .now() + 4.2) { withAnimation(.smooth) { reentry = nil } }
                }
            }
        } else {
            spine = book.startSpineIndex; target = .fraction(0)
            openChapter(book, at: spine)
        }
        loadToken += 1
        if LaunchState.showSettings { DispatchQueue.main.asyncAfter(deadline: .now() + 1.2) { withAnimation(Motion.morph) { panelOpen = true } } }
        if LaunchState.showContents { DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) { showContents = true } }
        if LaunchState.hideChrome { DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { chrome = false } }
    }

    private func jump(_ book: Book, toc id: Int) {
        guard let e = book.package.toc.first(where: { $0.id == id }), let s = e.spineIndex else { return }
        let fresh = s != spine
        spine = s
        target = e.fragment.map { .anchor($0) } ?? .fraction(0)
        loadToken += 1
        if fresh, started { openChapter(book, at: s) }
    }

    private func step(_ book: Book, _ dir: Int) {
        let next = spine + dir
        guard book.package.spine.indices.contains(next) else { return }
        spine = next
        target = dir > 0 ? .fraction(0) : .end
        loadToken += 1
        if dir > 0 { openChapter(book, at: next) }
    }
}

// MARK: Web view

struct BookWebView: UIViewRepresentable {
    let book: Book
    let spine: Int
    let target: BookTarget
    let loadToken: Int
    let style: BookStyle
    var marks: [String] = []
    /// Names the reader has met → entity id, longest first; drawn as tappable names in the text.
    var names: [(String, String)] = []
    /// The chapter's atmosphere colour, washed faintly into the page margins.
    var tint: String? = nil
    var onEntity: (String) -> Void = { _ in }
    var onSelect: (SelectionAction, String) -> Void = { _, _ in }
    let onLocation: (Int, Double, Int, Int) -> Void
    let onTap: () -> Void
    let onEdge: (Int) -> Void

    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeUIView(context: Context) -> WKWebView {
        let config = WKWebViewConfiguration()
        let controller = WKUserContentController()
        controller.addUserScript(WKUserScript(source: BookScript.source, injectionTime: .atDocumentEnd, forMainFrameOnly: true))
        controller.add(context.coordinator, name: "qbd")
        config.userContentController = controller
        config.dataDetectorTypes = []
        let web = ReaderWebView(frame: .zero, configuration: config)
        web.onSelection = { [weak coordinator = context.coordinator] action in coordinator?.selected(action) }
        web.isOpaque = false
        web.navigationDelegate = context.coordinator
        web.scrollView.delegate = context.coordinator
        web.scrollView.contentInsetAdjustmentBehavior = .never
        web.scrollView.showsHorizontalScrollIndicator = false
        web.scrollView.showsVerticalScrollIndicator = false
        web.scrollView.decelerationRate = .fast
        web.scrollView.minimumZoomScale = 1
        web.scrollView.maximumZoomScale = 1
        web.scrollView.bouncesZoom = false
        // No fade under the bottom glass bar: the text should pass under it and refract.
        web.scrollView.bottomEdgeEffect.isHidden = true
        web.allowsLinkPreview = false
        // With Curl or Fade chosen, native paging is off and swipes drive the same animated turn as taps.
        for dir in [UISwipeGestureRecognizer.Direction.left, .right] {
            let swipe = UISwipeGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.swiped(_:)))
            swipe.direction = dir
            swipe.delegate = context.coordinator
            web.addGestureRecognizer(swipe)
        }
        let tap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.tapped(_:)))
        tap.cancelsTouchesInView = false
        tap.delegate = context.coordinator
        web.addGestureRecognizer(tap)
        context.coordinator.web = web
        return web
    }

    func updateUIView(_ web: WKWebView, context: Context) {
        let c = context.coordinator
        c.parent = self
        web.backgroundColor = UIColor(style.theme.background)
        web.scrollView.backgroundColor = UIColor(style.theme.background)
        web.scrollView.isPagingEnabled = style.paged
        // Animated turns (Curl, Fade) own the horizontal gesture; Slide uses the scroll view's own paging.
        web.scrollView.isScrollEnabled = !(style.paged && style.turn != "slide")
        web.scrollView.alwaysBounceHorizontal = style.paged
        web.scrollView.alwaysBounceVertical = !style.paged
        if c.loadedToken != loadToken {
            c.loadedToken = loadToken
            c.load(spine: spine, target: target)
        } else if c.style != style {
            c.restyle(style)
        } else if c.marks != marks {
            c.marks = marks
            c.applyMarks()
        } else if c.namesApplied != names.map(\.0) {
            c.applyNames()
        }
    }

    static func dismantleUIView(_ web: WKWebView, coordinator: Coordinator) {
        web.configuration.userContentController.removeScriptMessageHandler(forName: "qbd")
    }

    final class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler, UIScrollViewDelegate, UIGestureRecognizerDelegate {
        var parent: BookWebView?
        weak var web: WKWebView?
        var loadedToken = -1
        var style: BookStyle?
        var marks: [String] = []
        var namesApplied: [String] = []
        private var lastEntityTap = Date.distantPast
        private var spine = 0
        private var pending: BookTarget?
        private var ready = false
        private var pages = 1
        private var lastReported: (Int, Int)?

        // MARK: Loading and styling

        func load(spine: Int, target: BookTarget) {
            guard let parent, let web, parent.book.package.spine.indices.contains(spine) else { return }
            self.spine = spine
            pending = target
            ready = false
            web.alpha = 0
            web.loadFileURL(parent.book.package.spine[spine].url, allowingReadAccessTo: Bookshelf.root)
        }

        func restyle(_ style: BookStyle) {
            guard ready, let web else { self.style = style; return }
            pending = .fraction(currentFraction())
            apply(style, to: web)
        }

        private func apply(_ style: BookStyle, to web: WKWebView) {
            self.style = style
            let insets = Self.deviceInsets()
            let t = style.theme
            let margins = [14.0, 24.0, 38.0][min(2, max(0, style.margin))]
            let accentDeep = t.isDark ? style.accent : (parent?.book.manifest.theme?.accentDeep ?? style.accent)
            let settings: [String: Any] = [
                "bg": t.background.hex, "ink": t.ink.hex, "ink2": t.ink2.hex, "accent": style.accent, "accentDeep": accentDeep, "finish": style.finish,
                "tint": parent?.tint ?? "", "tintAlpha": t.isDark ? 0.22 : 0.14,
                "font": style.font.css ?? "", "size": style.size, "lh": style.spacing, "margin": margins,
                "top": insets.top + 40, "bottom": insets.bottom + 34, "justify": style.justify, "paged": style.paged,
                "fonts": Bookshelf.fontsURL.absoluteString, "lang": parent?.book.package.metadata.language ?? "en",
            ]
            guard let data = try? JSONSerialization.data(withJSONObject: settings), let json = String(data: data, encoding: .utf8) else { return }
            web.evaluateJavaScript("window.qbd && qbd.apply(\(json))")
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            guard let style = parent?.style else { return }
            marks = parent?.marks ?? []
            apply(style, to: webView)
        }

        /// Wraps names the reader has met in tappable spans (dotted underline).
        func applyNames() {
            guard ready, let web, let parent else { return }
            let pairs = parent.names.map { [$0.0, $0.1] }
            guard let data = try? JSONSerialization.data(withJSONObject: pairs), let json = String(data: data, encoding: .utf8) else { return }
            web.evaluateJavaScript("window.qbd && qbd.names(\(json))")
            namesApplied = parent.names.map(\.0)
        }

        /// Re-finds each highlighted passage in the page and wraps it in a pastel mark.
        func applyMarks() {
            guard ready, let web, let data = try? JSONSerialization.data(withJSONObject: marks),
                  let json = String(data: data, encoding: .utf8) else { return }
            web.evaluateJavaScript("window.qbd && qbd.mark(\(json))")
        }

        func selected(_ action: SelectionAction) {
            guard let web, let parent else { return }
            web.evaluateJavaScript("window.getSelection().toString()") { result, _ in
                guard let text = result as? String else { return }
                DispatchQueue.main.async {
                    parent.onSelect(action, text)
                    web.evaluateJavaScript("window.getSelection().removeAllRanges()")
                }
            }
        }

        func webView(_ webView: WKWebView, decidePolicyFor action: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard action.navigationType == .linkActivated, let url = action.request.url else { return decisionHandler(.allow) }
            decisionHandler(.cancel)
            if url.isFileURL, let parent, let i = parent.book.package.spineIndex(of: url) {
                if i == spine, let f = url.fragment { pending = .anchor(f); position() } else {
                    parent.onLocationJump(i, url.fragment)
                }
            } else if ["http", "https", "mailto"].contains(url.scheme ?? "") {
                UIApplication.shared.open(url)
            }
        }

        func userContentController(_ controller: WKUserContentController, didReceive message: WKScriptMessage) {
            guard let body = message.body as? [String: Any], let type = body["type"] as? String else { return }
            if type == "entity", let id = body["id"] as? String {
                lastEntityTap = Date()
                parent?.onEntity(id)
                return
            }
            if type == "layout" {
                pages = max(1, body["pages"] as? Int ?? 1)
                ready = true
                position()
            }
        }

        /// Places the page for the pending target, then reveals the view.
        private func position() {
            guard let web, let target = pending else { return }
            pending = nil
            let js: String
            switch target {
            case .fraction(let f): js = "qbd.goFraction(\(f))"
            case .end: js = "qbd.goFraction(1)"
            case .anchor(let id): js = "qbd.goAnchor(\(Self.quoted(id)))"
            case .text(let t): js = "qbd.goText(\(Self.quoted(t)))"
            }
            applyMarks()
            applyNames()
            web.evaluateJavaScript(js) { [weak self] _, _ in
                DispatchQueue.main.async {
                    UIView.animate(withDuration: 0.18) { web.alpha = 1 }
                    self?.report(force: true)
                }
            }
        }

        // MARK: Position

        private func currentFraction() -> Double {
            guard let sv = web?.scrollView else { return 0 }
            if style?.paged ?? true {
                let w = max(1, sv.bounds.width)
                let n = max(1, Int((sv.contentSize.width / w).rounded()))
                return n > 1 ? Double(Int((sv.contentOffset.x / w).rounded())) / Double(n - 1) : 0
            }
            let range = sv.contentSize.height - sv.bounds.height
            return range > 0 ? min(1, max(0, sv.contentOffset.y / range)) : 0
        }

        private func report(force: Bool = false) {
            guard ready, let sv = web?.scrollView, let parent else { return }
            let paged = style?.paged ?? true
            let w = max(1, sv.bounds.width)
            let n = paged ? max(1, Int((sv.contentSize.width / w).rounded())) : 1
            let p = paged ? min(n - 1, max(0, Int((sv.contentOffset.x / w).rounded()))) : 0
            let f = currentFraction()
            let key = paged ? (p, n) : (Int(f * 200), 0)
            if !force, let last = lastReported, last == key { return }
            lastReported = key
            parent.onLocation(spine, f, p, n)
        }

        func scrollViewDidEndDecelerating(_ scrollView: UIScrollView) { report() }
        func scrollViewDidEndScrollingAnimation(_ scrollView: UIScrollView) { report() }

        func scrollViewDidScroll(_ scrollView: UIScrollView) {
            if !(style?.paged ?? true) { report() }
        }

        /// Pulling past the first or last page moves to the neighbouring chapter.
        func scrollViewWillEndDragging(_ sv: UIScrollView, withVelocity velocity: CGPoint, targetContentOffset: UnsafeMutablePointer<CGPoint>) {
            guard ready, let parent else { return }
            if style?.paged ?? true {
                let maxX = sv.contentSize.width - sv.bounds.width
                if sv.contentOffset.x < -44 { parent.onEdge(-1) } else if sv.contentOffset.x > maxX + 44 { parent.onEdge(1) }
            } else {
                let maxY = sv.contentSize.height - sv.bounds.height
                if sv.contentOffset.y < -90 { parent.onEdge(-1) } else if sv.contentOffset.y > maxY + 90 { parent.onEdge(1) }
            }
        }

        // MARK: Taps

        @objc func swiped(_ g: UISwipeGestureRecognizer) {
            guard ready, style?.paged ?? true, (style?.turn ?? "slide") != "slide" else { return }
            turn(g.direction == .left ? 1 : -1)
        }

        @objc func tapped(_ g: UITapGestureRecognizer) {
            guard let web, ready else { return }
            let x = g.location(in: web).x / max(1, web.bounds.width)
            // A tap on a name opens its card instead; the page script reports it first.
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.12) { [weak self] in
                guard let self, Date().timeIntervalSince(self.lastEntityTap) > 0.4 else { return }
                self.handleTap(x: x)
            }
        }

        private func handleTap(x: CGFloat) {
            guard let parent else { return }
            guard style?.paged ?? true else { return parent.onTap() }
            if x < 0.28 { turn(-1) } else if x > 0.72 { turn(1) } else { parent.onTap() }
        }

        private func turn(_ dir: Int) {
            guard let web, let parent else { return }
            let sv = web.scrollView
            let w = max(1, sv.bounds.width)
            let n = max(1, Int((sv.contentSize.width / w).rounded()))
            let p = Int((sv.contentOffset.x / w).rounded()) + dir
            if p < 0 { return parent.onEdge(-1) }
            if p >= n { return parent.onEdge(1) }
            let target = CGPoint(x: CGFloat(p) * w, y: 0)
            switch style?.turn ?? "slide" {
            case "curl", "fade":
                // Snapshot the current page over the web view, move underneath, then animate the snapshot away.
                guard let snap = web.snapshotView(afterScreenUpdates: false) else { return sv.setContentOffset(target, animated: true) }
                snap.frame = web.bounds
                web.addSubview(snap)
                sv.setContentOffset(target, animated: false)
                let curl = style?.turn == "curl"
                let options: UIView.AnimationOptions = curl ? (dir > 0 ? .transitionCurlUp : .transitionCurlDown) : .transitionCrossDissolve
                UIView.transition(with: web, duration: curl ? 0.45 : 0.25, options: [options, .allowAnimatedContent]) {
                    snap.removeFromSuperview()
                } completion: { [weak self] _ in self?.report() }
            default:
                sv.setContentOffset(target, animated: true)
            }
        }

        func gestureRecognizer(_ g: UIGestureRecognizer, shouldRecognizeSimultaneouslyWith other: UIGestureRecognizer) -> Bool { true }

        // MARK: Helpers

        static func deviceInsets() -> UIEdgeInsets {
            let scene = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first
            return scene?.windows.first(where: \.isKeyWindow)?.safeAreaInsets ?? scene?.windows.first?.safeAreaInsets ?? UIEdgeInsets(top: 59, left: 0, bottom: 34, right: 0)
        }

        static func quoted(_ s: String) -> String {
            let data = try? JSONSerialization.data(withJSONObject: [s])
            let arr = data.flatMap { String(data: $0, encoding: .utf8) } ?? "[\"\"]"
            return String(arr.dropFirst().dropLast())
        }
    }
}

/// Adds Highlight and Ask to the text-selection menu.
final class ReaderWebView: WKWebView {
    var onSelection: ((SelectionAction) -> Void)?

    override func buildMenu(with builder: any UIMenuBuilder) {
        super.buildMenu(with: builder)
        let highlight = UIAction(title: "Highlight", image: UIImage(systemName: "highlighter")) { [weak self] _ in self?.onSelection?(.highlight) }
        let ask = UIAction(title: "Ask", image: UIImage(systemName: "sparkles")) { [weak self] _ in self?.onSelection?(.ask) }
        builder.insertSibling(UIMenu(options: .displayInline, children: [highlight, ask]), beforeMenu: .standardEdit)
    }

    override func canPerformAction(_ action: Selector, withSender sender: Any?) -> Bool {
        // Keep the menu short: copy and look up, plus ours.
        if action == #selector(copy(_:)) || NSStringFromSelector(action).hasPrefix("_define") || NSStringFromSelector(action).hasPrefix("_lookup") { return true }
        if NSStringFromSelector(action).contains("share") || NSStringFromSelector(action).contains("translate") || NSStringFromSelector(action).contains("Search") { return false }
        return super.canPerformAction(action, withSender: sender)
    }
}

extension BookWebView {
    /// A link to another chapter: reload at that chapter and anchor.
    func onLocationJump(_ spine: Int, _ fragment: String?) {
        NotificationCenter.default.post(name: .bookJump, object: nil, userInfo: ["spine": spine, "fragment": fragment ?? ""])
    }
}

extension Notification.Name {
    static let bookJump = Notification.Name("qbd.bookJump")
}

extension Color {
    /// "#RRGGBB" for CSS.
    var hex: String {
        let c = UIColor(self).resolvedColor(with: UITraitCollection(userInterfaceStyle: .light))
        var r: CGFloat = 0, g: CGFloat = 0, b: CGFloat = 0, a: CGFloat = 0
        c.getRed(&r, green: &g, blue: &b, alpha: &a)
        return String(format: "#%02X%02X%02X", Int(r * 255), Int(g * 255), Int(b * 255))
    }
}

// MARK: Page script

/// Styles a chapter for the reading theme and lays it out as pages (CSS columns) or one scroll.
enum BookScript {
    static let source = #"""
    (function () {
      if (window.qbd) return;
      const post = (m) => window.webkit.messageHandlers.qbd.postMessage(m);
      let s = null;
      function css(s) {
        const face = s.font ? `
          @font-face { font-family: 'QBD CMU Serif'; src: url('${s.fonts}cmu-serif-500-roman.ttf'); font-weight: normal; font-style: normal; }
          @font-face { font-family: 'QBD CMU Serif'; src: url('${s.fonts}cmu-serif-500-italic.ttf'); font-weight: normal; font-style: italic; }
          @font-face { font-family: 'QBD CMU Serif'; src: url('${s.fonts}cmu-serif-700-roman.ttf'); font-weight: bold; font-style: normal; }
          @font-face { font-family: 'QBD CMU Serif'; src: url('${s.fonts}cmu-serif-700-italic.ttf'); font-weight: bold; font-style: italic; }
          body, body * { font-family: ${s.font} !important; }` : '';
        return `${face}
          :root { color-scheme: light dark; }
          html { background: ${s.bg} !important; -webkit-text-size-adjust: 100% !important; }
          html, body { margin: 0 !important; }
          body { background: transparent !important; color: ${s.ink} !important; font-size: ${s.size}px !important;
                 line-height: ${s.lh} !important; -webkit-hyphens: auto; hyphens: auto; widows: 2; orphans: 2;
                 overflow-wrap: break-word; text-rendering: optimizeLegibility; }
          body * { color: inherit !important; background-color: transparent !important; line-height: inherit !important; max-width: 100%; }
          a, a * { color: ${s.accent} !important; text-decoration: none !important; }
          img, svg, video { max-width: 100% !important; height: auto !important; object-fit: contain; }
          h1, h2, h3, h4, h5, h6 { -webkit-hyphens: manual !important; hyphens: manual !important; }
          .qbd-ragged { text-align: left !important; }
          html.qbd-finish body { hanging-punctuation: first last; }
          html.qbd-finish h1 + p::first-letter, html.qbd-finish h2 + p::first-letter, html.qbd-finish h3 + p::first-letter, html.qbd-finish h4 + p::first-letter, html.qbd-finish .qbd-first::first-letter {
            float: left; font-size: 3.1em; line-height: 0.82; padding: 0.06em 0.08em 0 0; color: ${s.accentDeep} !important; font-weight: normal; }
          html.qbd-finish h1 + p::first-line, html.qbd-finish h2 + p::first-line, html.qbd-finish h3 + p::first-line, html.qbd-finish h4 + p::first-line, html.qbd-finish .qbd-first::first-line { font-variant-caps: small-caps; letter-spacing: 0.02em; }
          ::selection { background: ${s.accent}66; }
          span.qbd-x { text-decoration: underline dotted ${s.accent} !important; text-underline-offset: 0.18em; text-decoration-thickness: 1.5px; }
          html { background: ${s.tint ? `radial-gradient(ellipse 120% 85% at 50% 45%, ${s.bg} 62%, ${s.tint}${Math.round(s.tintAlpha * 255).toString(16).padStart(2, '0')} 100%)` : s.bg} !important; background-attachment: fixed !important; }
          mark.qbd-hl { background: ${s.accent}80 !important; color: inherit !important; border-radius: 2px; padding: 0.05em 0; }
          html.qbd-paged { height: 100vh !important; overflow-y: hidden !important; }
          html.qbd-paged body { box-sizing: content-box !important; height: calc(100vh - ${s.top + s.bottom}px) !important;
                 padding: ${s.top}px ${s.margin}px ${s.bottom}px ${s.margin}px !important;
                 column-width: calc(100vw - ${2 * s.margin}px) !important; column-gap: ${2 * s.margin}px !important; column-fill: auto !important; }
          html.qbd-paged img, html.qbd-paged svg { max-height: calc(100vh - ${s.top + s.bottom + 8}px) !important; break-inside: avoid; }
          html:not(.qbd-paged) body { padding: ${s.top}px ${s.margin}px ${s.bottom + 90}px ${s.margin}px !important; }`;
      }
      function ragged(justify) {
        document.querySelectorAll('.qbd-ragged').forEach(e => e.classList.remove('qbd-ragged'));
        if (justify) return;
        document.querySelectorAll('p, div, li, blockquote').forEach(e => {
          if (getComputedStyle(e).textAlign === 'justify') e.classList.add('qbd-ragged');
        });
      }
      function pages() {
        if (!s.paged) return 1;
        const w = window.innerWidth;
        return Math.max(1, Math.ceil((document.documentElement.scrollWidth - 2) / w));
      }
      function pad() {
        let sp = document.getElementById('qbd-spacer');
        if (!s.paged) { if (sp) sp.remove(); return; }
        if (!sp) { sp = document.createElement('div'); sp.id = 'qbd-spacer'; document.documentElement.appendChild(sp); }
        sp.style.cssText = 'position:absolute;top:0;left:0;width:1px;height:1px;';
        const n = pages();
        sp.style.left = (n * window.innerWidth - 1) + 'px';
      }
      function layout() {
        pad();
        requestAnimationFrame(() => requestAnimationFrame(() => { pad(); post({ type: 'layout', pages: pages() }); }));
      }
      window.qbd = {
        apply(next) {
          s = next;
          // EPUB documents rarely declare a viewport, so WebKit would lay them out 980 px wide and shrink them.
          let vp = document.querySelector('meta[name="viewport"]');
          if (!vp) { vp = document.createElement('meta'); vp.name = 'viewport'; (document.head || document.documentElement).appendChild(vp); }
          vp.content = 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover';
          if (!document.documentElement.lang) document.documentElement.lang = s.lang || 'en';
          let el = document.getElementById('qbd-style');
          if (!el) { el = document.createElement('style'); el.id = 'qbd-style'; (document.head || document.documentElement).appendChild(el); }
          el.textContent = css(s);
          document.documentElement.classList.toggle('qbd-paged', !!s.paged);
          document.documentElement.classList.toggle('qbd-finish', !!s.finish);
          // Mark the first real paragraph after a heading (skips empty spacer paragraphs Calibre leaves behind).
          document.querySelectorAll('.qbd-first').forEach(e => e.classList.remove('qbd-first'));
          const h = document.querySelector('h1, h2, h3, h4');
          if (h) { let e = h.nextElementSibling; while (e && (e.tagName !== 'P' || e.textContent.trim().length < 20)) e = e.nextElementSibling; if (e) e.classList.add('qbd-first'); }
          ragged(s.justify);
          if (document.fonts && document.fonts.ready) document.fonts.ready.then(layout); else layout();
        },
        goFraction(f) {
          if (s.paged) {
            const n = pages(), w = window.innerWidth;
            window.scrollTo(Math.round(Math.min(1, Math.max(0, f)) * (n - 1)) * w, 0);
          } else {
            const h = document.documentElement.scrollHeight - window.innerHeight;
            window.scrollTo(0, Math.max(0, f * h));
          }
        },
        // Highlights: wrap the first occurrence of each passage. Passages that straddle elements get their first
        // text node marked, which is enough to find them again.
        mark(texts) {
          document.querySelectorAll('mark.qbd-hl').forEach(m => { const p = m.parentNode; while (m.firstChild) p.insertBefore(m.firstChild, m); p.removeChild(m); p.normalize(); });
          const walker = () => document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          for (const t of texts) {
            const needle = t.replace(/\s+/g, ' ').trim(); if (!needle) continue;
            const head = needle.slice(0, 60);
            let w = walker(), node, done = false;
            while (!done && (node = w.nextNode())) {
              const hay = node.nodeValue.replace(/\s+/g, ' ');
              let i = hay.indexOf(needle), len = needle.length;
              if (i < 0) { i = hay.indexOf(head); len = head.length; }
              if (i < 0) continue;
              // map collapsed index back to the raw node text
              let raw = 0, col = 0; while (col < i && raw < node.nodeValue.length) { if (!/\s/.test(node.nodeValue[raw]) || (raw > 0 && !/\s/.test(node.nodeValue[raw-1]))) col++; raw++; }
              const range = document.createRange();
              try { range.setStart(node, raw); range.setEnd(node, Math.min(node.nodeValue.length, raw + len)); } catch (e) { continue; }
              const m = document.createElement('mark'); m.className = 'qbd-hl';
              try { range.surroundContents(m); } catch (e) { continue; }
              done = true;
            }
          }
        },
        // Names the reader has met: wrap each occurrence in a tappable span. Longest names first.
        names(pairs) {
          document.querySelectorAll('span.qbd-x').forEach(m => { const p = m.parentNode; while (m.firstChild) p.insertBefore(m.firstChild, m); p.removeChild(m); p.normalize(); });
          if (!pairs.length) return;
          const esc = x => x.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
          const re = new RegExp('\\b(' + pairs.map(p => esc(p[0])).join('|') + ')\\b', 'g');
          const ids = Object.fromEntries(pairs.map(p => [p[0], p[1]]));
          const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, { acceptNode: n =>
            (n.parentElement && n.parentElement.closest('span.qbd-x, h1, h2, h3, h4, script, style')) ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
          const nodes = []; let n; while ((n = w.nextNode())) nodes.push(n);
          for (const node of nodes) {
            const t = node.nodeValue; re.lastIndex = 0; if (!re.test(t)) continue; re.lastIndex = 0;
            const frag = document.createDocumentFragment(); let last = 0, m;
            while ((m = re.exec(t))) {
              frag.appendChild(document.createTextNode(t.slice(last, m.index)));
              const sp = document.createElement('span'); sp.className = 'qbd-x'; sp.dataset.id = ids[m[1]]; sp.textContent = m[1];
              frag.appendChild(sp); last = m.index + m[1].length;
            }
            frag.appendChild(document.createTextNode(t.slice(last)));
            node.parentNode.replaceChild(frag, node);
          }
        },
        goText(t) {
          const needle = t.replace(/\s+/g, ' ').trim().slice(0, 60);
          const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
          let node;
          while ((node = w.nextNode())) {
            if (node.nodeValue.replace(/\s+/g, ' ').indexOf(needle) >= 0) {
              const el = node.parentElement; if (!el) return;
              if (s.paged) { const w2 = window.innerWidth; const x = el.getBoundingClientRect().left + window.scrollX; window.scrollTo(Math.max(0, Math.floor(x / w2)) * w2, 0); }
              else { window.scrollTo(0, Math.max(0, el.getBoundingClientRect().top + window.scrollY - s.top)); }
              return;
            }
          }
        },
        goAnchor(id) {
          const el = document.getElementById(id) || document.getElementsByName(id)[0];
          if (!el) return;
          if (s.paged) {
            const w = window.innerWidth;
            const x = el.getBoundingClientRect().left + window.scrollX;
            window.scrollTo(Math.max(0, Math.floor(x / w)) * w, 0);
          } else {
            window.scrollTo(0, Math.max(0, el.getBoundingClientRect().top + window.scrollY - s.top));
          }
        }
      };
      window.addEventListener('resize', () => { if (s) layout(); });
      document.addEventListener('click', e => {
        const x = e.target.closest && e.target.closest('span.qbd-x');
        if (x && !window.getSelection().toString()) { post({ type: 'entity', id: x.dataset.id }); }
      }, true);
    })();
    """#
}

// MARK: Chrome

/// The lesson reader's glass bar, with the book's extra layout controls in the Aa panel.
struct BookBar: View {
    @Environment(\.reading) private var r
    @Environment(\.accent) private var accent
    let style: BookStyle
    @Binding var fontRaw: String
    @Binding var spacing: Double
    @Binding var margin: Int
    @Binding var justify: Bool
    @Binding var paged: Bool
    @Binding var turnRaw: String
    @Binding var finish: Bool
    @Binding var themeRaw: String
    @Binding var textSize: Double
    @Binding var panelOpen: Bool
    let section: String
    let progress: Double
    let showContents: () -> Void
    var showPeople: () -> Void = {}
    @Namespace private var ns

    var body: some View {
        GlassEffectContainer(spacing: 10) {
            VStack(spacing: 10) {
                if panelOpen {
                    panel
                        .padding(18)
                        .glassEffect(.regular, in: .rect(cornerRadius: 30))
                        .glassEffectID("aa", in: ns)
                }
                HStack(spacing: 10) {
                    Button(action: showContents) {
                        Image(systemName: "list.bullet").font(.body.weight(.medium)).frame(width: 50, height: 50).contentShape(.circle)
                    }
                    .buttonStyle(.plain)
                    .glassEffect(.regular.interactive(), in: .circle)
                    .glassEffectID("contents", in: ns)
                    .accessibilityLabel("Contents")
                    ProgressPill(section: section, progress: progress, compact: false)
                        .glassEffect(.regular.interactive(), in: .capsule)
                        .glassEffectID("progress", in: ns)
                        .onTapGesture(perform: showContents)
                    if !panelOpen {
                        Button(action: showPeople) {
                            Image(systemName: "person.2").font(.body.weight(.medium)).frame(width: 50, height: 50).contentShape(.circle)
                        }
                        .buttonStyle(.plain)
                        .glassEffect(.regular.interactive(), in: .circle)
                        .glassEffectID("people", in: ns)
                        .accessibilityLabel("Who’s who")
                        Button { withAnimation(Motion.morph) { panelOpen = true } } label: {
                            Text("Aa").font(Typeface.serif(19)).frame(width: 50, height: 50).contentShape(.circle)
                        }
                        .buttonStyle(.plain)
                        .glassEffect(.regular.interactive(), in: .circle)
                        .glassEffectID("aa", in: ns)
                        .accessibilityLabel("Appearance")
                    }
                }
            }
            .foregroundStyle(r.theme.ink)
        }
        .padding(.horizontal, 16)
        .padding(.bottom, 4)
    }

    private var panel: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("Appearance").font(.headline)
                Spacer()
                Button { withAnimation(Motion.morph) { panelOpen = false } } label: {
                    Image(systemName: "xmark").font(.subheadline.weight(.semibold)).frame(width: 32, height: 32).contentShape(.circle)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Close appearance")
            }
            ThemeSwatches(themeRaw: $themeRaw)
            TextSizeControl(textSize: $textSize)
            ScrollView(.horizontal) {
                HStack(spacing: 8) {
                    ForEach(BookFont.allCases) { f in
                        let on = fontRaw == f.rawValue
                        Button { fontRaw = f.rawValue } label: {
                            VStack(spacing: 2) {
                                Text(f == .publisher ? "Book" : "Ag").font(f.preview)
                                Text(f.label).font(.caption2).lineLimit(1)
                            }
                            .frame(width: 78, height: 52)
                            .background(on ? accent.pastel.opacity(0.45) : Color.primary.opacity(0.06), in: .rect(cornerRadius: 12))
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(f.label)
                        .accessibilityAddTraits(on ? .isSelected : [])
                    }
                }
            }
            .scrollIndicators(.hidden)
            HStack(spacing: 10) {
                Picker("Spacing", selection: $spacing) {
                    Image(systemName: "text.alignleft").tag(1.35)
                    Image(systemName: "text.justify.leading").tag(1.5)
                    Image(systemName: "line.3.horizontal").tag(1.7)
                }
                .pickerStyle(.segmented)
                .accessibilityLabel("Line spacing")
                Picker("Margins", selection: $margin) {
                    Text("S").tag(0); Text("M").tag(1); Text("L").tag(2)
                }
                .pickerStyle(.segmented)
                .accessibilityLabel("Margins")
            }
            HStack(spacing: 10) {
                Picker("Layout", selection: $paged) {
                    Label("Pages", systemImage: "book").tag(true)
                    Label("Scroll", systemImage: "scroll").tag(false)
                }
                .pickerStyle(.segmented)
                Toggle(isOn: $justify) { Image(systemName: "text.justify") }
                    .toggleStyle(.button)
                    .accessibilityLabel("Justify text")
            }
            if paged {
                HStack(spacing: 10) {
                    Picker("Page turn", selection: $turnRaw) {
                        Text("Slide").tag("slide"); Text("Curl").tag("curl"); Text("Fade").tag("fade")
                    }
                    .pickerStyle(.segmented)
                    .accessibilityLabel("Page turn")
                    Toggle(isOn: $finish) { Text("Aa").font(Typeface.serif(15, bold: true)) }
                        .toggleStyle(.button)
                        .accessibilityLabel("Drop capitals and small caps")
                }
            }
        }
    }
}

struct BookContentsSheet: View {
    @Environment(\.accent) private var accent
    let book: Book
    let currentTOC: Int?
    let go: (Int) -> Void

    var body: some View {
        NavigationStack {
            ScrollViewReader { proxy in
                List {
                    ForEach(book.outline.parts) { part in
                        Section {
                            if part.chapters.isEmpty, let e = part.entry {
                                row(e)
                            }
                            ForEach(part.chapters) { row($0) }
                        } header: {
                            if !part.title.isEmpty && !part.chapters.isEmpty {
                                Button { if let e = part.entry { go(e.id) } } label: {
                                    Text([part.number, part.title].compactMap { $0 }.joined(separator: "  ")).font(Typeface.serif(17, bold: true))
                                }
                                .buttonStyle(.plain)
                                .textCase(nil)
                            }
                        }
                    }
                }
                .onAppear { if let c = currentTOC { proxy.scrollTo(c, anchor: .center) } }
            }
            .navigationTitle(book.title)
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private func row(_ ch: BookOutline.Chapter) -> some View {
        Button { go(ch.id) } label: {
            HStack(alignment: .firstTextBaseline, spacing: 12) {
                Text(ch.number ?? "").monospacedDigit().foregroundStyle(.secondary).frame(width: 36, alignment: .leading)
                Text(ch.title).font(Typeface.serif(17)).foregroundStyle(.primary)
                Spacer()
                if ch.id == currentTOC { Circle().fill(accent.pastel).frame(width: 9, height: 9) }
            }
        }
        .id(ch.id)
    }
}

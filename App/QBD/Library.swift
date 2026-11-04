import SwiftUI
import Observation

enum Route: Hashable {
    case bookContents(String)
    case book(id: String, toc: Int?, highlight: UUID? = nil)
}

/// What Home shows: the last book opened (`lastItem` = "book:<id>").
enum LastItem {
    case book(String)
    init?(_ raw: String) {
        guard raw.hasPrefix("book:") else { return nil }
        self = .book(String(raw.dropFirst(5)))
    }
}

enum AppTab: String, Hashable {
    case home, library, highlights, search
}

/// Launch arguments for fixed states, used by CI screenshots (`-tab lab`, `-open 0-1`, `-theme night`, `-showSettings YES`, `-scroll 12`).
enum LaunchState {
    static var defaults: UserDefaults { .standard }
    static var tab: AppTab? { defaults.string(forKey: "tab").flatMap(AppTab.init(rawValue:)) }
    static var openLesson: String? { defaults.string(forKey: "open") }
    static var openCourse: Bool { defaults.bool(forKey: "course") }
    static var showSettings: Bool { defaults.bool(forKey: "showSettings") }
    static var showContents: Bool { defaults.bool(forKey: "showContents") }
    static var showAppSettings: Bool { defaults.bool(forKey: "appSettings") }
    static var slowmo: Bool { defaults.bool(forKey: "slowmo") }
    static var fixtureBooks: Bool { defaults.bool(forKey: "fixtureBooks") }
    static var openBook: String? { defaults.string(forKey: "openBook") }
    static var openBookContents: String? { defaults.string(forKey: "bookContents") }
    static var openTOC: Int? { defaults.object(forKey: "toc") == nil ? nil : defaults.integer(forKey: "toc") }
    static var libraryBooks: Bool { defaults.bool(forKey: "libraryBooks") }
    static var labModel: String? { defaults.string(forKey: "labModel") }
    /// `-scene 3` fakes a reading position at the start of part 3 (0-based) for backdrop screenshots.
    static var sceneOverride: BookLocation? {
        guard defaults.object(forKey: "scene") != nil else { return nil }
        return BookLocation(spine: defaults.integer(forKey: "scene"), fraction: 0)
    }
    /// Any CI launch argument present: skip entrance animations so stills are deterministic.
    static var isScreenshotting: Bool { defaults.bool(forKey: "fixtureBooks") || tab != nil || openLesson != nil || openCourse }
    static var showReentry: Bool { defaults.bool(forKey: "reentry") }
    static var seedHighlights: Bool { defaults.bool(forKey: "seedHighlights") }
    static var showPeople: Bool { defaults.bool(forKey: "showPeople") }
    /// CI: after launch states have had time to render, write Documents/qbd-ready so screenshots don't wait blind.
    static func signalReadyIfAsked() {
        guard defaults.bool(forKey: "readyFile") else { return }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.7) {
            let docs = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
            try? FileManager.default.createDirectory(at: docs, withIntermediateDirectories: true)
            FileManager.default.createFile(atPath: docs.appendingPathComponent("qbd-ready").path, contents: Data())
        }
    }
    static var hideChrome: Bool { defaults.bool(forKey: "hideChrome") }
    static var landingOverride: String? { defaults.string(forKey: "landing") }
    static var lastItem: String? { defaults.string(forKey: "last") }
    static var scrollTo: Int? { defaults.object(forKey: "scroll") == nil ? nil : defaults.integer(forKey: "scroll") }
}

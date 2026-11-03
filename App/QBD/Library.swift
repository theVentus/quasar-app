import SwiftUI
import Observation
import CourseKit

/// Installed course packages. v0.1 ships one, bundled from `content/courses`.
@Observable
final class Library {
    private(set) var courses: [CoursePackage] = []
    private(set) var loadError: String?
    @ObservationIgnored private var cache: [String: Lesson] = [:]

    init() {
        guard let base = Bundle.main.url(forResource: "courses", withExtension: nil),
              let dirs = try? FileManager.default.contentsOfDirectory(at: base, includingPropertiesForKeys: nil) else {
            loadError = "No course packages were bundled with this build."
            return
        }
        for dir in dirs.sorted(by: { $0.lastPathComponent < $1.lastPathComponent }) {
            do { courses.append(try CoursePackage(root: dir)) } catch { loadError = "Couldn’t read \(dir.lastPathComponent): \(error.localizedDescription)" }
        }
    }

    func course(_ id: String) -> CoursePackage? { courses.first { $0.manifest.id == id } }

    func lesson(course: CoursePackage, id: String) -> Lesson? {
        let key = course.manifest.id + "/" + id
        if let hit = cache[key] { return hit }
        guard let ref = course.manifest.lesson(id), ref.isPublished, let lesson = try? course.lesson(ref) else { return nil }
        cache[key] = lesson
        return lesson
    }

    /// The lesson the "Now reading" pill resumes: the first published lesson until progress tracking lands in v0.2.
    func nowReading() -> (CoursePackage, CourseManifest.LessonRef)? {
        for c in courses { if let l = c.manifest.allLessons.first(where: \.isPublished) { return (c, l) } }
        return nil
    }
}

enum Route: Hashable {
    case course(String)
    case lesson(course: String, lesson: String)
}

enum AppTab: String, Hashable {
    case library, review, lab, ask, search
}

/// Launch arguments for fixed states, used by CI screenshots (`-tab lab`, `-open 0-1`, `-theme night`, `-showSettings YES`, `-scroll 12`).
enum LaunchState {
    static var defaults: UserDefaults { .standard }
    static var tab: AppTab? { defaults.string(forKey: "tab").flatMap(AppTab.init(rawValue:)) }
    static var openLesson: String? { defaults.string(forKey: "open") }
    static var openCourse: Bool { defaults.bool(forKey: "course") }
    static var showSettings: Bool { defaults.bool(forKey: "showSettings") }
    static var scrollTo: Int? { defaults.object(forKey: "scroll") == nil ? nil : defaults.integer(forKey: "scroll") }
}

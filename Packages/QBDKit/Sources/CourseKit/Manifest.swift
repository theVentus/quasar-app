import Foundation

/// `course.json`, schema `qbd.course/1`. See docs/PLAN.md §3.
public struct CourseManifest: Codable, Hashable, Sendable {
    public var schema: String
    public var id: String
    public var version: String
    public var title: String
    public var subtitle: String
    public var language: String?
    public var modules: [Module]
    public var lab: [LabEntry]
    public var references: [Reference]
    public var textbooks: [String]
    public var mastery: [[String]]
    public var calibration: [[String]]
    public var review: Review?

    public struct Module: Codable, Hashable, Sendable, Identifiable {
        public var id: Int
        public var title: String
        public var tag: String
        public var hours: Double
        public var deps: [Int]
        public var why: String
        public var lessons: [LessonRef]
    }

    public struct LessonRef: Codable, Hashable, Sendable, Identifiable {
        public var id: String
        public var title: String
        public var file: String
        public var status: Status
        /// "0-1" → "0.1"
        public var number: String { id.replacingOccurrences(of: "-", with: ".") }
        public var isPublished: Bool { status == .published }
    }

    public enum Status: String, Codable, Hashable, Sendable {
        case published, draft, planned
    }

    public struct LabEntry: Codable, Hashable, Sendable, Identifiable {
        public var model: String
        public var title: String
        public var `where`: String
        public var lesson: String
        public var blurb: String
        public var id: String { model }
    }

    public struct Reference: Codable, Hashable, Sendable {
        public var text: String
        public var url: String?
    }

    public struct Review: Codable, Hashable, Sendable {
        public var gapsDays: [Int]
    }

    public var allLessons: [LessonRef] { modules.flatMap(\.lessons) }
    public var publishedCount: Int { allLessons.filter(\.isPublished).count }
    public func module(of lessonID: String) -> Module? { modules.first { $0.lessons.contains { $0.id == lessonID } } }
    public func lesson(_ id: String) -> LessonRef? { allLessons.first { $0.id == id } }
}

/// A course package on disk: `course.json` plus lesson files.
public struct CoursePackage: Sendable, Identifiable {
    public var id: String { manifest.id }
    public let root: URL
    public let manifest: CourseManifest

    public init(root: URL) throws {
        self.root = root
        let data = try Data(contentsOf: root.appendingPathComponent("course.json"))
        self.manifest = try JSONDecoder().decode(CourseManifest.self, from: data)
    }

    public func lesson(_ ref: CourseManifest.LessonRef) throws -> Lesson {
        let text = try String(contentsOf: root.appendingPathComponent(ref.file), encoding: .utf8)
        return LessonParser.parse(text, id: ref.id)
    }
}

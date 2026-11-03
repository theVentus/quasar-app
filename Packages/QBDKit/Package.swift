// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "QBDKit",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "CourseKit", targets: ["CourseKit"]),
    ],
    targets: [
        // Pure Swift, Foundation only: builds and tests on Linux CI as well as Apple platforms.
        .target(name: "CourseKit"),
        .testTarget(name: "CourseKitTests", dependencies: ["CourseKit"]),
    ],
    swiftLanguageVersions: [.v5]
)

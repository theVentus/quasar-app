// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "QBDKit",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "BookKit", targets: ["BookKit"]),
    ],
    dependencies: [
        .package(url: "https://github.com/weichsel/ZIPFoundation.git", from: "0.9.19"),
    ],
    targets: [
        // EPUB 2/3 packages: unzip, metadata, reading order, contents, cover.
        .target(name: "BookKit", dependencies: [.product(name: "ZIPFoundation", package: "ZIPFoundation")]),
        .testTarget(name: "BookKitTests", dependencies: ["BookKit"]),
        // CI tool: encrypts private book packages into a public build (macOS).
        .executableTarget(name: "qbd-seal", dependencies: ["BookKit", .product(name: "ZIPFoundation", package: "ZIPFoundation")]),
    ],
    swiftLanguageVersions: [.v5]
)

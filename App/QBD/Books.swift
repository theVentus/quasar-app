import SwiftUI
import Observation
import Security
import BookKit

/// Where a reader is in a book: a spine document and a fraction through it.
struct BookLocation: Codable, Hashable {
    var spine: Int
    var fraction: Double
    var updated = Date()
}

/// Books shipped inside the build. Sealed packages (`vault/*.qbdvault`) are opened with the library passphrase,
/// kept in the Keychain after the first unlock, and installed into Application Support. CI screenshots use plain
/// fixture packages (`fixture-books/`) instead, with `-fixtureBooks YES`.
@Observable
final class Bookshelf {
    private(set) var books: [Book] = []
    private(set) var lockedCount = 0
    private(set) var isUnlocking = false
    var unlockError: String?
    private(set) var locations: [String: BookLocation] = [:]

    static let root: URL = {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("Books", isDirectory: true)
    }()
    static var fontsURL: URL { root.appendingPathComponent("_fonts", isDirectory: true) }

    private struct Install: Codable { var digest: String }

    init() {
        let fm = FileManager.default
        try? fm.createDirectory(at: Self.root, withIntermediateDirectories: true)
        Self.copyFonts()
        if let data = UserDefaults.standard.data(forKey: "bookLocations"),
           let saved = try? JSONDecoder().decode([String: BookLocation].self, from: data) {
            locations = saved
        }
        if LaunchState.fixtureBooks { installFixtures() }
        reload()
        if lockedCount > 0, let passphrase = Keychain.passphrase {
            Task { await unlock(passphrase, remember: false) }
        }
    }

    func book(_ id: String) -> Book? { books.first { $0.id == id } }

    @ObservationIgnored private var nameCache: [String: NameIndex] = [:]

    /// The book's name index, built on first use and kept beside the book.
    func names(for book: Book) -> NameIndex {
        if let hit = nameCache[book.id] { return hit }
        let url = Self.root.appendingPathComponent(book.id).appendingPathComponent("names.json")
        if let data = try? Data(contentsOf: url), let idx = try? JSONDecoder().decode(NameIndex.self, from: data) {
            nameCache[book.id] = idx; return idx
        }
        let idx = NameIndex.build(book.package)
        try? JSONEncoder().encode(idx).write(to: url, options: .atomic)
        nameCache[book.id] = idx
        return idx
    }

    // MARK: Progress

    func location(_ id: String) -> BookLocation? { locations[id] }

    func save(_ location: BookLocation, for id: String) {
        locations[id] = location
        if let data = try? JSONEncoder().encode(locations) { UserDefaults.standard.set(data, forKey: "bookLocations") }
    }

    func progress(_ book: Book) -> Double {
        guard let l = locations[book.id] else { return 0 }
        return book.package.progress(spine: l.spine, fraction: l.fraction)
    }

    // MARK: Loading

    private var sealedFiles: [URL] {
        guard let dir = Bundle.main.url(forResource: "vault", withExtension: nil) else { return [] }
        return ((try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)) ?? [])
            .filter { $0.pathExtension == Vault.fileExtension }
    }

    /// Reads installed books, and counts sealed files whose current version isn't installed yet.
    func reload() {
        let fm = FileManager.default
        var loaded: [Book] = []
        var installedDigests: Set<String> = []
        for dir in (try? fm.contentsOfDirectory(at: Self.root, includingPropertiesForKeys: nil)) ?? [] where !dir.lastPathComponent.hasPrefix("_") {
            guard let data = try? Data(contentsOf: dir.appendingPathComponent("book.json")),
                  let manifest = try? JSONDecoder().decode(BookManifest.self, from: data),
                  let package = try? BookPackage(root: dir.appendingPathComponent("epub")) else { continue }
            if let i = try? JSONDecoder().decode(Install.self, from: Data(contentsOf: dir.appendingPathComponent("install.json"))) {
                installedDigests.insert(i.digest)
            }
            let words = (try? String(contentsOf: dir.appendingPathComponent("words.txt"), encoding: .utf8))
                .flatMap { Int($0.trimmingCharacters(in: .whitespacesAndNewlines)) }
            loaded.append(Book(manifest: manifest, package: package, words: words ?? Book.countWords(package)))
        }
        books = loaded.sorted { $0.title.localizedCaseInsensitiveCompare($1.title) == .orderedAscending }
        lockedCount = sealedFiles.filter { url in
            guard let d = try? Data(contentsOf: url) else { return false }
            return !installedDigests.contains(Vault.digest(d))
        }.count
    }

    // MARK: Installing

    /// Unpacks a book package directory (book.json + book.epub) into the library.
    private static func install(packageAt dir: URL, digest: String) throws {
        let fm = FileManager.default
        let manifest = try JSONDecoder().decode(BookManifest.self, from: Data(contentsOf: dir.appendingPathComponent("book.json")))
        let target = root.appendingPathComponent(manifest.id, isDirectory: true)
        try? fm.removeItem(at: target)
        try fm.createDirectory(at: target, withIntermediateDirectories: true)
        try fm.copyItem(at: dir.appendingPathComponent("book.json"), to: target.appendingPathComponent("book.json"))
        let package = try BookPackage.unpack(epub: dir.appendingPathComponent("book.epub"), to: target.appendingPathComponent("epub"))
        try String(Book.countWords(package)).write(to: target.appendingPathComponent("words.txt"), atomically: true, encoding: .utf8)
        try JSONEncoder().encode(Install(digest: digest)).write(to: target.appendingPathComponent("install.json"))
        try? JSONEncoder().encode(NameIndex.build(package)).write(to: target.appendingPathComponent("names.json"), options: .atomic)
    }

    private func installFixtures() {
        guard let dir = Bundle.main.url(forResource: "fixture-books", withExtension: nil),
              let packages = try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil) else { return }
        for p in packages { try? Self.install(packageAt: p, digest: "fixture") }
    }

    /// Opens every sealed book not yet installed. Wrong passphrase leaves everything locked.
    @MainActor
    func unlock(_ passphrase: String, remember: Bool = true) async {
        isUnlocking = true
        unlockError = nil
        let files = sealedFiles
        let result: Result<Int, Error> = await Task.detached(priority: .userInitiated) {
            do {
                var installed = 0
                let fm = FileManager.default
                for url in files {
                    let blob = try Data(contentsOf: url)
                    let digest = Vault.digest(blob)
                    let zip = try Vault.open(blob, passphrase: passphrase)
                    let tmp = fm.temporaryDirectory.appendingPathComponent("unseal-\(UUID().uuidString)")
                    let zipURL = tmp.appendingPathExtension("zip")
                    try zip.write(to: zipURL)
                    try fm.createDirectory(at: tmp, withIntermediateDirectories: true)
                    try BookPackage.extract(zip: zipURL, to: tmp)
                    try Self.install(packageAt: tmp, digest: digest)
                    try? fm.removeItem(at: tmp); try? fm.removeItem(at: zipURL)
                    installed += 1
                }
                return .success(installed)
            } catch {
                return .failure(error)
            }
        }.value
        switch result {
        case .success:
            if remember { Keychain.passphrase = passphrase }
        case .failure(let error):
            unlockError = (error as? Vault.VaultError)?.description ?? error.localizedDescription
            if !remember { Keychain.passphrase = nil }
        }
        reload()
        isUnlocking = false
    }

    /// WKWebView may only read under the books folder, so the bundled faces are copied beside the books.
    private static func copyFonts() {
        let fm = FileManager.default
        try? fm.createDirectory(at: fontsURL, withIntermediateDirectories: true)
        for name in ["cmu-serif-500-roman", "cmu-serif-500-italic", "cmu-serif-700-roman", "cmu-serif-700-italic"] {
            let dest = fontsURL.appendingPathComponent(name + ".ttf")
            if !fm.fileExists(atPath: dest.path), let src = Bundle.main.url(forResource: name, withExtension: "ttf") {
                try? fm.copyItem(at: src, to: dest)
            }
        }
    }
}


/// The library passphrase, kept on this device only.
enum Keychain {
    private static let service = "com.theventus.qbd.library"

    static var passphrase: String? {
        get {
            let query: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service,
                                        kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
            var out: AnyObject?
            guard SecItemCopyMatching(query as CFDictionary, &out) == errSecSuccess, let data = out as? Data else { return nil }
            return String(data: data, encoding: .utf8)
        }
        set {
            let base: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service]
            SecItemDelete(base as CFDictionary)
            guard let newValue else { return }
            var add = base
            add[kSecValueData as String] = Data(newValue.utf8)
            add[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
            SecItemAdd(add as CFDictionary, nil)
        }
    }
}

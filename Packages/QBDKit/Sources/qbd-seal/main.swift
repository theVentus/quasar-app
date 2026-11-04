// Seals book packages for a public build.
// Usage: LIBRARY_PASSPHRASE=… swift run qbd-seal <books dir> <out dir>
// Each subdirectory of <books dir> holding book.json + one .epub becomes <out dir>/<hash of id>.qbdvault.
// Prints counts only, never titles, because CI logs are public.
import Foundation
import BookKit
import ZIPFoundation

#if canImport(CryptoKit)
let args = CommandLine.arguments
guard args.count == 3, let passphrase = ProcessInfo.processInfo.environment["LIBRARY_PASSPHRASE"], !passphrase.isEmpty else {
    FileHandle.standardError.write(Data("usage: LIBRARY_PASSPHRASE=… qbd-seal <books dir> <out dir>\n".utf8))
    exit(2)
}
let fm = FileManager.default
let source = URL(fileURLWithPath: args[1], isDirectory: true)
let out = URL(fileURLWithPath: args[2], isDirectory: true)
try fm.createDirectory(at: out, withIntermediateDirectories: true)

var sealed = 0
for dir in try fm.contentsOfDirectory(at: source, includingPropertiesForKeys: nil).sorted(by: { $0.path < $1.path }) {
    // book.json plus one .epub of any name (uploads keep their original file names).
    let json = dir.appendingPathComponent("book.json")
    let epubs = ((try? fm.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)) ?? []).filter { $0.pathExtension.lowercased() == "epub" }
    guard fm.fileExists(atPath: json.path), let epub = epubs.sorted(by: { $0.path < $1.path }).first else { continue }
    let manifest = try JSONDecoder().decode(BookManifest.self, from: Data(contentsOf: json))

    // Validate before sealing: the EPUB must parse.
    let check = fm.temporaryDirectory.appendingPathComponent("seal-check-\(UUID().uuidString)")
    _ = try BookPackage.unpack(epub: epub, to: check)
    try? fm.removeItem(at: check)

    let stage = fm.temporaryDirectory.appendingPathComponent("seal-\(UUID().uuidString)")
    try fm.createDirectory(at: stage, withIntermediateDirectories: true)
    try fm.copyItem(at: json, to: stage.appendingPathComponent("book.json"))
    try fm.copyItem(at: epub, to: stage.appendingPathComponent("book.epub"))
    // The reading companion travels sealed with the book when it exists.
    let companion = dir.appendingPathComponent("companion.json")
    if fm.fileExists(atPath: companion.path) {
        _ = try JSONDecoder().decode(Companion.self, from: Data(contentsOf: companion))   // must decode
        try fm.copyItem(at: companion, to: stage.appendingPathComponent("companion.json"))
    }
    let zip = fm.temporaryDirectory.appendingPathComponent("seal-\(UUID().uuidString).zip")
    try fm.zipItem(at: stage, to: zip, shouldKeepParent: false)
    let blob = try Vault.seal(Data(contentsOf: zip), passphrase: passphrase)
    _ = try Vault.open(blob, passphrase: passphrase)   // round-trip check
    try blob.write(to: out.appendingPathComponent(Vault.sealedName(for: manifest.id)))
    try? fm.removeItem(at: stage); try? fm.removeItem(at: zip)
    sealed += 1
}
print("qbd-seal: sealed \(sealed) book(s)")
#else
print("qbd-seal needs CryptoKit (macOS)")
exit(1)
#endif

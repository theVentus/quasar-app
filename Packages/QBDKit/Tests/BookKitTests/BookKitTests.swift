import XCTest
@testable import BookKit

final class BookKitTests: XCTestCase {
    /// content/fixtures, from this file: Tests/BookKitTests → QBDKit → Packages → repo.
    static let fixtures = URL(fileURLWithPath: #filePath)
        .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        .deletingLastPathComponent().deletingLastPathComponent()
        .appendingPathComponent("content/fixtures")

    private func unpack(_ name: String) throws -> BookPackage {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("bookkit-\(name)-\(UUID().uuidString)")
        return try BookPackage.unpack(epub: Self.fixtures.appendingPathComponent(name), to: dir)
    }

    func testCalibreStyleEPUB2() throws {
        let book = try unpack("field-guide-epub2.epub")
        XCTAssertEqual(book.version, "2.0")
        XCTAssertEqual(book.metadata.title, "A Field Guide to Light")
        XCTAssertEqual(book.metadata.authors, ["Mira Okonjo"])
        XCTAssertEqual(book.metadata.language, "en")
        XCTAssertEqual(book.metadata.series, "Quasar Fixtures")
        XCTAssertEqual(book.spine.count, 5)                       // cover page, title page, three chapters
        XCTAssertEqual(book.spine.first?.url.lastPathComponent, "titlepage.xhtml")
        XCTAssertEqual(book.toc.map(\.title), ["1 THE PATIENT MESSENGER", "2 CLOCKS THAT DISAGREE", "3 LISTENING TO THE EDGE OF THE SKY"])
        XCTAssertEqual(book.toc.map(\.spineIndex), [2, 3, 4])
        XCTAssertEqual(book.toc.first?.fragment, "filepos100")
        XCTAssertEqual(book.coverURL?.lastPathComponent, "cover1.jpeg")
        XCTAssertEqual(book.spineWeights.count, 5)
    }

    func testEPUB3WithNestedNav() throws {
        let book = try unpack("field-guide-epub3.epub")
        XCTAssertEqual(book.version, "3.0")
        XCTAssertEqual(book.metadata.identifier, "urn:uuid:5e0c2a7b-qbd-fixture-3")
        XCTAssertEqual(book.spine.count, 3)
        XCTAssertEqual(book.spine[0].url.lastPathComponent, "chapter 1.xhtml")   // %20 decoded
        XCTAssertEqual(book.toc.count, 6)
        XCTAssertEqual(book.toc.map(\.level), [1, 2, 1, 2, 1, 2])
        XCTAssertEqual(book.toc[0].title, "The Patient Messenger")
        XCTAssertEqual(book.toc[1].fragment, "c1s2")
        XCTAssertEqual(book.toc[4].spineIndex, 2)
        XCTAssertEqual(book.coverURL?.lastPathComponent, "cover.jpg")
    }

    func testProgressAndLocation() throws {
        let book = try unpack("field-guide-epub3.epub")
        XCTAssertEqual(book.progress(spine: 0, fraction: 0), 0, accuracy: 1e-9)
        XCTAssertEqual(book.progress(spine: 2, fraction: 1), 1, accuracy: 1e-9)
        let mid = book.progress(spine: 1, fraction: 0.5)
        XCTAssertGreaterThan(mid, 0.2)
        XCTAssertLessThan(mid, 0.8)
        XCTAssertEqual(book.tocEntry(spine: 1)?.title, "Part two")
        XCTAssertEqual(book.spineIndex(of: book.toc[3].url), 1)
    }

    func testRejectsDRM() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("bookkit-drm-\(UUID().uuidString)")
        _ = try BookPackage.unpack(epub: Self.fixtures.appendingPathComponent("field-guide-epub2.epub"), to: dir)
        let enc = """
        <encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container" xmlns:enc="http://www.w3.org/2001/04/xmlenc#">
        <enc:EncryptedData><enc:EncryptionMethod Algorithm="http://www.w3.org/2001/04/xmlenc#aes128-cbc"/></enc:EncryptedData></encryption>
        """
        try enc.write(to: dir.appendingPathComponent("META-INF/encryption.xml"), atomically: true, encoding: .utf8)
        XCTAssertThrowsError(try BookPackage(root: dir)) { error in
            guard case .encrypted? = error as? BookPackage.PackageError else { return XCTFail("expected .encrypted, got \(error)") }
        }
    }

    func testNavWithHTMLEntities() throws {
        let xhtml = """
        <html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops"><body>
        <nav epub:type="toc"><ol><li><a href="a.xhtml">One&nbsp;&mdash; Two</a></li></ol></nav></body></html>
        """
        let tree = try XMLTree.parse(Data(xhtml.utf8))
        let entries = BookPackage.navEntries(tree, base: URL(fileURLWithPath: "/tmp/book"))
        XCTAssertEqual(entries.count, 1)
        XCTAssertEqual(entries[0].href.path, "/tmp/book/a.xhtml")
        XCTAssertTrue(entries[0].title.hasPrefix("One"))
    }
}

final class BookOutlineTests: XCTestCase {
    private func entry(_ id: Int, _ title: String, level: Int = 1) -> BookPackage.TOCEntry {
        .init(id: id, title: title, url: URL(fileURLWithPath: "/b/\(id).html"), fragment: nil, level: level, spineIndex: id)
    }

    func testNumberedFlatContentsBecomePartsAndChapters() {
        let toc = [entry(0, "1 FIRST LIGHT"), entry(1, "1.1 THE LONG WAY ROUND"), entry(2, "1.2 A MAP OF THE SKY"),
                   entry(3, "2 NORTH / SOUTH"), entry(4, "2.1 OUT OF THE DARK")]
        let o = BookOutline(toc: toc)
        XCTAssertEqual(o.parts.count, 2)
        XCTAssertEqual(o.parts[0].title, "First Light")
        XCTAssertEqual(o.parts[0].number, "1")
        XCTAssertEqual(o.parts[0].chapters.map(\.title), ["The Long Way Round", "A Map of the Sky"])
        XCTAssertEqual(o.parts[0].chapters.map(\.number), ["1.1", "1.2"])
        XCTAssertEqual(o.parts[1].title, "North / South")
        XCTAssertEqual(o.chapterCount, 3)
        XCTAssertTrue(o.hasParts)
        XCTAssertEqual(o.part(containingTOC: 4)?.number, "2")
    }

    func testMixedCaseTitlesAreKept() {
        XCTAssertEqual(BookOutline.titleCased("The Patient Messenger"), "The Patient Messenger")
        XCTAssertEqual(BookOutline.titleCased("THE SKY’S OTHER SIDE"), "The Sky’s Other Side")
        XCTAssertEqual(BookOutline.splitNumber("Prologue").0, nil)
        XCTAssertEqual(BookOutline.splitNumber("3.10 LANTERNS").0, "3.10")
    }

    func testFixtureOutlines() throws {
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent("outline-\(UUID().uuidString)")
        let p2 = try BookPackage.unpack(epub: BookKitTests.fixtures.appendingPathComponent("field-guide-epub2.epub"), to: dir)
        let o2 = BookOutline(toc: p2.toc)
        XCTAssertEqual(o2.parts.count, 3)                      // "1 THE PATIENT MESSENGER" … are parts with no chapters
        XCTAssertEqual(o2.parts[0].title, "The Patient Messenger")
        let dir3 = FileManager.default.temporaryDirectory.appendingPathComponent("outline3-\(UUID().uuidString)")
        let p3 = try BookPackage.unpack(epub: BookKitTests.fixtures.appendingPathComponent("field-guide-epub3.epub"), to: dir3)
        let o3 = BookOutline(toc: p3.toc)
        XCTAssertEqual(o3.parts.count, 3)
        XCTAssertEqual(o3.parts[1].chapters.map(\.title), ["Part two"])
        let book = Book(manifest: BookManifest(id: "fixture"), package: p3, words: Book.countWords(p3))
        XCTAssertGreaterThan(book.words, 600)
        XCTAssertLessThan(book.words, 3000)
    }
}

#if canImport(CryptoKit)
final class VaultTests: XCTestCase {
    func testSealAndOpen() throws {
        let plain = Data("a small book".utf8)
        let sealed = try Vault.seal(plain, passphrase: "correct horse", rounds: 1_000)
        XCTAssertEqual(try Vault.open(sealed, passphrase: "correct horse"), plain)
        XCTAssertThrowsError(try Vault.open(sealed, passphrase: "wrong")) { error in
            guard case .wrongPassphrase? = error as? Vault.VaultError else { return XCTFail("\(error)") }
        }
        XCTAssertThrowsError(try Vault.open(Data("nope".utf8), passphrase: "x"))
        XCTAssertTrue(Vault.sealedName(for: "some-book").hasSuffix(".qbdvault"))
        XCTAssertFalse(Vault.sealedName(for: "some-book").contains("some"))
    }
}
#endif

final class BookManifestTests: XCTestCase {
    func testBackCoverFieldsDecode() throws {
        let json = """
        {"schema":"qbd.book/1","id":"x","about":"A book.","praise":[{"quote":"Good.","source":"Someone"}],
         "scenes":[{"web":0.1,"ship":0,"pod":false},{"web":1,"ship":1,"orbit":true}]}
        """
        let m = try JSONDecoder().decode(BookManifest.self, from: Data(json.utf8))
        XCTAssertEqual(m.praise?.first?.source, "Someone")
        let (a, b, t) = try XCTUnwrap(m.scene(part: 0, fraction: 0.5))
        XCTAssertEqual(a.web, 0.1); XCTAssertEqual(b.orbit, true); XCTAssertEqual(t, 0.5)
        XCTAssertEqual(try XCTUnwrap(m.scene(part: 9, fraction: 0)).0.web, 1)   // clamps
        XCTAssertNil(BookManifest(id: "y").scene(part: 0, fraction: 0))
    }
}

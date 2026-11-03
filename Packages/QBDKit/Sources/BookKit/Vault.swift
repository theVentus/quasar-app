#if canImport(CryptoKit) && canImport(CommonCrypto)
import Foundation
import CryptoKit
import CommonCrypto

/// Sealed book packages for public builds. A `.qbdvault` file is
/// `"QBDV" | version (1) | salt (16) | PBKDF2 rounds (UInt32 BE) | AES-256-GCM combined box (nonce 12 | ciphertext | tag 16)`,
/// keyed by PBKDF2-HMAC-SHA256 of the reader's library passphrase. The plaintext is a zip of `book.json` and `book.epub`.
public enum Vault {
    public static let fileExtension = "qbdvault"
    static let magic = Data("QBDV".utf8)
    static let version: UInt8 = 1
    public static let defaultRounds: UInt32 = 210_000

    public enum VaultError: Error, CustomStringConvertible {
        case badFormat, wrongPassphrase, keyDerivation
        public var description: String {
            switch self {
            case .badFormat: return "Not a sealed book."
            case .wrongPassphrase: return "That passphrase doesn’t open these books."
            case .keyDerivation: return "Couldn’t derive the key."
            }
        }
    }

    public static func key(passphrase: String, salt: Data, rounds: UInt32) throws -> SymmetricKey {
        var derived = [UInt8](repeating: 0, count: 32)
        let password = Array(passphrase.utf8).map { CChar(bitPattern: $0) }
        let status = salt.withUnsafeBytes { (saltBytes: UnsafeRawBufferPointer) -> Int32 in
            CCKeyDerivationPBKDF(CCPBKDFAlgorithm(kCCPBKDF2), password, password.count,
                                 saltBytes.bindMemory(to: UInt8.self).baseAddress, salt.count,
                                 CCPseudoRandomAlgorithm(kCCPRFHmacAlgSHA256), rounds, &derived, derived.count)
        }
        guard status == Int32(kCCSuccess) else { throw VaultError.keyDerivation }
        return SymmetricKey(data: derived)
    }

    public static func seal(_ plaintext: Data, passphrase: String, rounds: UInt32 = defaultRounds) throws -> Data {
        let salt = Data((0..<16).map { _ in UInt8.random(in: 0...255) })
        let box = try AES.GCM.seal(plaintext, using: try key(passphrase: passphrase, salt: salt, rounds: rounds))
        guard let combined = box.combined else { throw VaultError.badFormat }
        var out = magic
        out.append(version)
        out.append(salt)
        withUnsafeBytes(of: rounds.bigEndian) { out.append(contentsOf: $0) }
        out.append(combined)
        return out
    }

    public static func open(_ sealed: Data, passphrase: String) throws -> Data {
        let blob = Data(sealed)   // normalise indices to start at 0
        guard blob.count > 4 + 1 + 16 + 4 + 12 + 16, blob.prefix(4) == magic, blob[4] == version else { throw VaultError.badFormat }
        let salt = blob.subdata(in: 5..<21)
        let rounds = blob.subdata(in: 21..<25).reduce(UInt32(0)) { $0 << 8 | UInt32($1) }
        let box = try AES.GCM.SealedBox(combined: blob.subdata(in: 25..<blob.count))
        do {
            return try AES.GCM.open(box, using: try key(passphrase: passphrase, salt: salt, rounds: rounds))
        } catch is CryptoKitError {
            throw VaultError.wrongPassphrase
        }
    }

    /// File name for a sealed book: a hash of its id, so public builds don't reveal titles.
    public static func sealedName(for id: String) -> String {
        SHA256.hash(data: Data(id.utf8)).prefix(8).map { String(format: "%02x", $0) }.joined() + "." + fileExtension
    }

    /// Hex SHA-256 of a sealed file, to tell whether an installed copy is current.
    public static func digest(_ data: Data) -> String {
        SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
    }
}
#endif

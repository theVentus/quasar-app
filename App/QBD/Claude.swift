import Foundation
import Security

/// Backend A from the plan: the reader's own key, kept in the Keychain, calling the Messages API directly.
/// No key ever ships in the binary.
enum ClaudeKey {
    private static let service = "com.theventus.qbd.claude"

    static var value: String? {
        get {
            let q: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service,
                                    kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
            var out: AnyObject?
            guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let d = out as? Data else { return nil }
            return String(data: d, encoding: .utf8)
        }
        set {
            let base: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrService as String: service]
            SecItemDelete(base as CFDictionary)
            guard let v = newValue?.trimmingCharacters(in: .whitespacesAndNewlines), !v.isEmpty else { return }
            var add = base
            add[kSecValueData as String] = Data(v.utf8)
            add[kSecAttrAccessible as String] = kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            SecItemAdd(add as CFDictionary, nil)
        }
    }

    static var isSet: Bool { value != nil }
}

struct ClaudeError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

enum Claude {
    /// Chosen in Settings; Sonnet by default.
    static var model: String { UserDefaults.standard.string(forKey: "claudeModel") ?? "claude-sonnet-5-5" }

    /// One non-streaming call. `system` carries the tutor's rules; `user` the passage and question.
    static func ask(system: String, user: String, maxTokens: Int = 700) async throws -> String {
        guard let key = ClaudeKey.value else { throw ClaudeError(message: "Add your Claude API key in Settings first.") }
        var req = URLRequest(url: URL(string: "https://api.anthropic.com/v1/messages")!)
        req.httpMethod = "POST"
        req.setValue(key, forHTTPHeaderField: "x-api-key")
        req.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body: [String: Any] = [
            "model": model, "max_tokens": maxTokens, "system": system,
            "messages": [["role": "user", "content": user]],
        ]
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, resp) = try await URLSession.shared.data(for: req)
        guard let http = resp as? HTTPURLResponse else { throw ClaudeError(message: "No response.") }
        let json = (try? JSONSerialization.jsonObject(with: data)) as? [String: Any] ?? [:]
        guard http.statusCode == 200 else {
            let msg = ((json["error"] as? [String: Any])?["message"] as? String) ?? "HTTP \(http.statusCode)"
            throw ClaudeError(message: msg)
        }
        let parts = (json["content"] as? [[String: Any]]) ?? []
        let text = parts.compactMap { $0["type"] as? String == "text" ? $0["text"] as? String : nil }.joined()
        guard !text.isEmpty else { throw ClaudeError(message: "Empty reply.") }
        return text
    }

    /// The tutor's rules when asked about a passage of a book. Spoiler safety is explicit and absolute.
    static func bookSystem(title: String, author: String, upTo location: String) -> String {
        """
        You are a quiet, well-read companion for someone reading "\(title)" by \(author). \
        The reader has read up to \(location) and no further. Answer only from what appears in the book up to that point \
        and from general knowledge that does not depend on later chapters. Never reveal, hint at, or allude to anything \
        that happens later, even if asked directly; if a question can only be answered with later events, say so in one \
        sentence and stop. Be concise: two to five sentences, plain prose, no headings or lists. British spelling.
        """
    }
}

import Foundation

/// An `explore/1` model: sliders over named variables, derived quantities, formatted outputs and an optional plot.
/// The same JSON drives the web reader and the app.
public struct ExploreModel: Codable, Hashable, Sendable, Identifiable {
    public struct Variable: Codable, Hashable, Sendable, Identifiable {
        public var id: String
        public var label: String
        public var min: Double
        public var max: Double
        public var value: Double
        public var log: Bool?
        public var step: Double?
        public var unit: String?
        public var digits: Int?
        public var presets: [Preset]?

        public var isLog: Bool { log ?? false }
    }

    /// `["GPS", 20200000]` in JSON.
    public struct Preset: Codable, Hashable, Sendable {
        public var label: String
        public var value: Double

        public init(from decoder: Decoder) throws {
            var c = try decoder.unkeyedContainer()
            label = try c.decode(String.self)
            value = try c.decode(Double.self)
        }

        public func encode(to encoder: Encoder) throws {
            var c = encoder.unkeyedContainer()
            try c.encode(label)
            try c.encode(value)
        }
    }

    /// `[threshold, "a city block"]`: the last entry whose threshold is at or below the value is shown.
    public struct Lookup: Codable, Hashable, Sendable {
        public var threshold: Double
        public var text: String

        public init(from decoder: Decoder) throws {
            var c = try decoder.unkeyedContainer()
            threshold = try c.decode(Double.self)
            text = try c.decode(String.self)
        }

        public func encode(to encoder: Encoder) throws {
            var c = encoder.unkeyedContainer()
            try c.encode(threshold)
            try c.encode(text)
        }
    }

    public struct Output: Codable, Hashable, Sendable {
        public var label: String
        public var expr: String
        public var unit: String?
        public var lookup: [Lookup]?
        public var digits: Int?
    }

    public struct Plot: Codable, Hashable, Sendable {
        public var x: String
        public var y: [String]
        public var labels: [String]?
        public var logy: Bool?
        public var xlabel: String?
        public var ylabel: String?
        public var yunit: String?
    }

    public var spec: String
    public var id: String
    public var title: String
    public var vars: [Variable]
    /// `[name, expression]` pairs evaluated in order before the outputs.
    public var defs: [[String]]?
    public var outputs: [Output]
    public var plot: Plot?
    public var caption: String?

    public static func load(_ data: Data) throws -> ExploreModel {
        try JSONDecoder().decode(ExploreModel.self, from: data)
    }

    public var defaults: [String: Double] {
        Dictionary(uniqueKeysWithValues: vars.map { ($0.id, $0.value) })
    }

    /// The variables plus every `defs` entry, evaluated in order.
    public func environment(_ values: [String: Double]) -> [String: Double] {
        var env = defaults.merging(values) { _, new in new }
        for pair in defs ?? [] where pair.count == 2 {
            env[pair[0]] = (try? Expr.parse(pair[1]))?.eval(env) ?? .nan
        }
        return env
    }

    public func value(of expr: String, _ values: [String: Double]) -> Double {
        (try? Expr.parse(expr))?.eval(environment(values)) ?? .nan
    }

    /// Display strings for each output at the given variable values.
    public func evaluate(_ values: [String: Double]) -> [(label: String, text: String)] {
        let env = environment(values)
        return outputs.map { o in
            let v = (try? Expr.parse(o.expr))?.eval(env) ?? .nan
            if let lookup = o.lookup {
                let hit = lookup.last { v >= $0.threshold } ?? lookup.first
                return (o.label, hit?.text ?? "—")
            }
            return (o.label, Quantity.format(v, unit: o.unit ?? "", digits: o.digits ?? 3))
        }
    }

    /// Plot samples: the x variable swept across its range (log-spaced if the slider is), other variables held.
    public func series(_ values: [String: Double], samples: Int = 120) -> [(x: Double, ys: [Double])] {
        guard let plot, let xv = vars.first(where: { $0.id == plot.x }) else { return [] }
        let exprs = plot.y.compactMap { try? Expr.parse($0) }
        return (0..<samples).map { i in
            let t = Double(i) / Double(samples - 1)
            let x = xv.isLog ? exp(Foundation.log(xv.min) + t * (Foundation.log(xv.max) - Foundation.log(xv.min))) : xv.min + t * (xv.max - xv.min)
            var vals = values
            vals[plot.x] = x
            let env = environment(vals)
            return (x, exprs.map { $0.eval(env) })
        }
    }
}

public extension CoursePackage {
    /// An `explore/1` model from `models/<id>.json`; nil for bespoke models or missing files.
    func exploreModel(_ id: String) -> ExploreModel? {
        let url = root.appendingPathComponent("models/\(id).json")
        guard let data = try? Data(contentsOf: url), let model = try? ExploreModel.load(data), model.spec == "explore/1" else { return nil }
        return model
    }
}

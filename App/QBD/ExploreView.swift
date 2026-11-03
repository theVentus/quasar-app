import SwiftUI
import Charts
import CourseKit

extension EnvironmentValues {
    /// The course being read, so lesson blocks can resolve `widget` models.
    @Entry var coursePackage: CoursePackage? = nil
}

/// A live `explore/1` model: sliders and presets on the inputs, outputs that update as you drag, and a plot
/// with a marker at the current value. Reads as part of the page, not as glass.
struct ExploreCard: View {
    @Environment(\.reading) private var r
    @Environment(\.accent) private var accent
    let model: ExploreModel
    @State private var values: [String: Double] = [:]

    private var current: [String: Double] { model.defaults.merging(values) { _, v in v } }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Label(model.title, systemImage: "slider.horizontal.3")
                .font(.caption.weight(.semibold))
                .textCase(.uppercase)
                .foregroundStyle(r.theme.ink3)

            ForEach(model.vars) { v in
                VariableControl(variable: v, value: binding(v))
            }

            VStack(spacing: 0) {
                ForEach(Array(model.evaluate(current).enumerated()), id: \.offset) { i, o in
                    if i > 0 { Rectangle().fill(r.theme.rule).frame(height: 0.5) }
                    HStack(alignment: .firstTextBaseline, spacing: 12) {
                        Text(o.label)
                            .font(Typeface.serif(r.size * 0.86))
                            .foregroundStyle(r.theme.ink2)
                        Spacer(minLength: 8)
                        Text(o.text)
                            .font(.system(size: r.size * 0.92, weight: .semibold, design: .rounded))
                            .monospacedDigit()
                            .foregroundStyle(r.theme.ink)
                            .contentTransition(.numericText())
                            .multilineTextAlignment(.trailing)
                    }
                    .padding(.vertical, 8)
                }
            }
            .padding(.horizontal, 12)
            .background(r.theme.background.opacity(0.55), in: .rect(cornerRadius: 10))

            if model.plot != nil { ExplorePlot(model: model, values: current) }

            if let caption = model.caption {
                ProseText(text: caption, scale: 0.84)
                    .foregroundStyle(r.theme.ink2)
            }
        }
        .padding(14)
        .background(r.theme.tint(.blue), in: .rect(cornerRadius: 14))
        .animation(.snappy(duration: 0.2), value: values)
    }

    private func binding(_ v: ExploreModel.Variable) -> Binding<Double> {
        Binding(get: { values[v.id] ?? v.value }, set: { values[v.id] = $0 })
    }
}

struct VariableControl: View {
    @Environment(\.reading) private var r
    @Environment(\.accent) private var accent
    let variable: ExploreModel.Variable
    @Binding var value: Double

    /// Log variables slide on log10(value) so every decade gets the same travel.
    private var position: Binding<Double> {
        Binding(
            get: { variable.isLog ? log10(max(value, variable.min)) : value },
            set: { p in
                var v = variable.isLog ? pow(10, p) : p
                if let step = variable.step { v = (v / step).rounded() * step }
                value = min(variable.max, max(variable.min, v))
            })
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack(alignment: .firstTextBaseline) {
                Text(variable.label).font(Typeface.serif(r.size * 0.86)).foregroundStyle(r.theme.ink2)
                Spacer(minLength: 8)
                Text(Quantity.format(value, unit: variable.unit ?? "", digits: variable.digits ?? 3))
                    .font(.system(size: r.size * 0.86, weight: .semibold, design: .rounded))
                    .monospacedDigit()
                    .contentTransition(.numericText())
            }
            Slider(value: position,
                   in: variable.isLog ? log10(variable.min)...log10(variable.max) : variable.min...variable.max)
                .tint(accent.pastel)
                .accessibilityLabel(variable.label)
                .accessibilityValue(Quantity.format(value, unit: variable.unit ?? ""))
            if let presets = variable.presets, !presets.isEmpty {
                ScrollView(.horizontal) {
                    HStack(spacing: 6) {
                        ForEach(presets, id: \.label) { p in
                            let on = abs(p.value - value) <= abs(p.value) * 1e-6
                            Button { withAnimation(.snappy) { value = p.value } } label: {
                                Text(p.label)
                                    .font(.caption.weight(.semibold))
                                    .padding(.horizontal, 10)
                                    .padding(.vertical, 5)
                                    .foregroundStyle(on ? accent.onPastel : r.theme.ink2)
                                    .background(on ? accent.pastel : r.theme.background.opacity(0.6), in: .capsule)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
                .scrollIndicators(.hidden)
            }
        }
    }
}

struct ExplorePlot: View {
    @Environment(\.reading) private var r
    @Environment(\.accent) private var accent
    let model: ExploreModel
    let values: [String: Double]

    private struct Point: Identifiable {
        let id: Int
        let x: Double
        let y: Double
        let series: String
    }

    var body: some View {
        let plot = model.plot!
        let xVar = model.vars.first { $0.id == plot.x }
        let names = plot.labels ?? plot.y.map { _ in plot.ylabel ?? "" }
        let samples = model.series(values, samples: 90)
        let logY = plot.logy ?? false
        let points: [Point] = samples.enumerated().flatMap { i, s in
            s.ys.enumerated().compactMap { k, y in
                (y.isFinite && (!logY || y > 0)) ? Point(id: i * 10 + k, x: s.x, y: y, series: names[min(k, names.count - 1)]) : nil
            }
        }
        let xNow = values[plot.x] ?? xVar?.value ?? 0
        let colors: [Color] = [accent.tint, r.theme.ink3, r.theme.ink2.opacity(0.6)]

        VStack(alignment: .leading, spacing: 6) {
            Chart {
                ForEach(points) { p in
                    LineMark(x: .value(plot.xlabel ?? "x", p.x), y: .value(plot.ylabel ?? "y", p.y), series: .value("Series", p.series))
                        .foregroundStyle(by: .value("Series", p.series))
                        .lineStyle(StrokeStyle(lineWidth: p.series == names.first ? 2.2 : 1.4))
                        .interpolationMethod(.monotone)
                }
                RuleMark(x: .value("Now", xNow))
                    .foregroundStyle(accent.tint.opacity(0.7))
                    .lineStyle(StrokeStyle(lineWidth: 1, dash: [3, 3]))
            }
            .chartForegroundStyleScale(domain: names, range: Array(colors.prefix(max(1, names.count))))
            .chartLegend(names.count > 1 ? .visible : .hidden)
            .chartXScale(type: (xVar?.isLog ?? false) ? .log : .linear)
            .chartYScale(type: logY ? .log : .linear)
            .chartXAxis {
                AxisMarks(values: .automatic(desiredCount: 4)) { v in
                    AxisGridLine().foregroundStyle(r.theme.rule)
                    AxisValueLabel {
                        if let d = v.as(Double.self) { Text(Quantity.format(d, unit: xVar?.unit ?? "", digits: 2)).font(.caption2) }
                    }
                }
            }
            .chartYAxis {
                AxisMarks(position: .leading, values: .automatic(desiredCount: 4)) { v in
                    AxisGridLine().foregroundStyle(r.theme.rule)
                    AxisValueLabel {
                        if let d = v.as(Double.self) { Text(Quantity.format(d, unit: plot.yunit ?? "", digits: 2)).font(.caption2) }
                    }
                }
            }
            .frame(height: 190)
            .foregroundStyle(r.theme.ink2)
            if let xl = plot.xlabel, let yl = plot.ylabel {
                Text("\(yl) against \(xl.lowercased())")
                    .font(.caption)
                    .foregroundStyle(r.theme.ink3)
            }
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel("Plot of \(plot.ylabel ?? "output") against \(plot.xlabel ?? "input")")
    }
}

/// Bespoke models (least-squares positioning, interferometry) need their own engines; they arrive with the Lab.
struct BespokeModelCard: View {
    @Environment(\.reading) private var r
    let title: String

    var body: some View {
        HStack(alignment: .top, spacing: 14) {
            Image(systemName: "testtube.2")
                .font(.title3)
                .frame(width: 40, height: 40)
                .background(r.theme.tint(.blue), in: .circle)
            VStack(alignment: .leading, spacing: 2) {
                Text(title).font(Typeface.serif(r.size, bold: true))
                Text("Interactive simulation · arrives with the Lab").font(.footnote).foregroundStyle(r.theme.ink3)
            }
            Spacer(minLength: 0)
        }
        .padding(14)
        .background(r.theme.panel.opacity(0.6), in: .rect(cornerRadius: 14))
    }
}

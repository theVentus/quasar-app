import SwiftUI
import CourseKit

struct LibraryView: View {
    @Environment(Library.self) private var library
    @Binding var path: [Route]

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                ForEach(library.courses) { course in
                    CourseCard(course: course) { lessonID in
                        path = lessonID.map { [.course(course.id), .lesson(course: course.id, lesson: $0)] } ?? [.course(course.id)]
                    }
                }
                if let e = library.loadError {
                    Text(e).font(.footnote).foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 16)
            .padding(.top, 8)
            .padding(.bottom, 24)
        }
        .navigationTitle("Library")
    }
}

/// A course cover: content layer, no glass. The single prominent action is the glass button.
struct CourseCard: View {
    let course: CoursePackage
    let open: (String?) -> Void

    private var m: CourseManifest { course.manifest }
    private var hours: Int { Int(m.modules.reduce(0) { $0 + $1.hours }) }
    private var next: CourseManifest.LessonRef? { m.allLessons.first(where: \.isPublished) }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            CoverArt()
                .frame(height: 190)
                .clipShape(.rect(cornerRadius: 22))
                .padding(10)
            VStack(alignment: .leading, spacing: 8) {
                Text(m.title)
                    .font(Typeface.serif(30))
                Text(m.subtitle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Text("\(m.modules.count) modules · \(m.allLessons.count) lessons · about \(hours) hours")
                    .font(.footnote)
                    .foregroundStyle(.tertiary)
                    .monospacedDigit()
                HStack(spacing: 12) {
                    if let next {
                        Button { open(next.id) } label: {
                            Label("Start \(next.number)", systemImage: "book")
                                .padding(.horizontal, 4)
                        }
                        .buttonStyle(.glassProminent)
                    }
                    Button { open(nil) } label: { Text("Syllabus") }
                        .buttonStyle(.bordered)
                    Spacer()
                    ProgressRing(fraction: Double(m.publishedCount) / Double(max(1, m.allLessons.count)))
                        .frame(width: 34, height: 34)
                }
                .padding(.top, 6)
            }
            .padding(.horizontal, 18)
            .padding(.bottom, 18)
            .padding(.top, 4)
        }
        .background(.background.secondary, in: .rect(cornerRadius: 32))
        .contentShape(.rect(cornerRadius: 32))
        .onTapGesture { open(nil) }
    }
}

/// Wavefronts from a distant quasar reaching a blue dot: the course in one picture.
struct CoverArt: View {
    var body: some View {
        Canvas { ctx, size in
            ctx.fill(Path(CGRect(origin: .zero, size: size)), with: .color(Color(hex: 0x08080A)))
            let dot = CGPoint(x: size.width * 0.34, y: size.height * 0.68)
            for (k, r) in [60.0, 110, 160, 210, 260].enumerated() {
                let rect = CGRect(x: dot.x - r, y: dot.y - r, width: 2 * r, height: 2 * r)
                ctx.stroke(Path(ellipseIn: rect), with: .color(Color(hex: 0x9FB4DC).opacity(0.55 - Double(k) * 0.08)), lineWidth: 1)
            }
            let q = CGPoint(x: size.width * 0.82, y: size.height * 0.22)
            ctx.fill(Path(ellipseIn: CGRect(x: q.x - 22, y: q.y - 22, width: 44, height: 44)), with: .color(Color(hex: 0xFFD68C).opacity(0.25)))
            ctx.fill(Path(ellipseIn: CGRect(x: q.x - 5, y: q.y - 5, width: 10, height: 10)), with: .color(Color(hex: 0xFFF0D2)))
            ctx.fill(Path(ellipseIn: CGRect(x: dot.x - 34, y: dot.y - 34, width: 68, height: 68)), with: .color(Color(hex: 0x3A84FF).opacity(0.25)))
            ctx.fill(Path(ellipseIn: CGRect(x: dot.x - 14, y: dot.y - 14, width: 28, height: 28)), with: .color(Color(hex: 0x3A84FF)))
        }
        .accessibilityHidden(true)
    }
}

struct ProgressRing: View {
    let fraction: Double
    var body: some View {
        ZStack {
            Circle().stroke(.quaternary, lineWidth: 4)
            Circle().trim(from: 0, to: max(0.02, fraction))
                .stroke(.tint, style: StrokeStyle(lineWidth: 4, lineCap: .round))
                .rotationEffect(.degrees(-90))
        }
        .accessibilityLabel("\(Int(fraction * 100)) percent of lessons published")
    }
}

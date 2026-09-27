import Foundation
import Vision
import ImageIO

struct Line {
    let text: String
    let x: CGFloat
    let y: CGFloat
    let w: CGFloat
    let h: CGFloat
}

func recognize(path: String) throws -> [Line] {
    let url = URL(fileURLWithPath: path)
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = ["ja-JP"]
    request.usesLanguageCorrection = true
    if #available(macOS 13.0, *) {
        request.automaticallyDetectsLanguage = false
    }
    let handler = VNImageRequestHandler(url: url, options: [:])
    try handler.perform([request])
    let observations = request.results ?? []
    var lines: [Line] = []
    for obs in observations {
        guard let top = obs.topCandidates(1).first else { continue }
        let box = obs.boundingBox
        let text = top.string.trimmingCharacters(in: .whitespacesAndNewlines)
        if text.isEmpty { continue }
        lines.append(Line(text: text, x: box.midX, y: box.maxY, w: box.width, h: box.height))
    }
    return lines
}

func readingOrder(_ lines: [Line]) -> String {
    if lines.isEmpty { return "" }
    let sorted = lines.sorted { $0.x > $1.x }
    var columns: [[Line]] = []
    let gap: CGFloat = 0.018
    for line in sorted {
        if var last = columns.last, let anchor = last.first, abs(line.x - anchor.x) < gap {
            last.append(line)
            columns[columns.count - 1] = last
        } else {
            columns.append([line])
        }
    }
    var parts: [String] = []
    for column in columns {
        let ordered = column.sorted { $0.y > $1.y }
        let joined = ordered.map(\.text).joined()
        parts.append(joined)
    }
    return parts.joined(separator: "\n")
}

let path = CommandLine.arguments[1]
let lines = try recognize(path: path)
print(readingOrder(lines))

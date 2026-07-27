import AppKit
import Foundation

let width: CGFloat = 2560
let height: CGFloat = 1920
let canvas = NSSize(width: width, height: height)
let referencePath = "/var/folders/ty/6kw9zrnj60b1lhr2pstwr12m0000gp/T/codex-clipboard-87639f89-a3fe-4a98-b975-f2c42a8ba5fe.png"
let herbPath = "/Users/xxm/Documents/AI/ZY-demo/ai-medical-consultant/backend/data/herbs/柴胡.jpg"
let outputPath = "/Users/xxm/Documents/AI/ZY-demo/output/covers/chaihu_family_baokuan_landscape_2560x1920.png"

func color(_ hex: UInt32, alpha: CGFloat = 1) -> NSColor {
    NSColor(
        calibratedRed: CGFloat((hex >> 16) & 0xff) / 255,
        green: CGFloat((hex >> 8) & 0xff) / 255,
        blue: CGFloat(hex & 0xff) / 255,
        alpha: alpha
    )
}

let ink = color(0x0E0A07)
let darkBrown = color(0x3C1E0E)
let brown = color(0x6A3418)
let red = color(0xA51F13)
let darkRed = color(0x71120D)
let gold = color(0xF5B92E)
let cream = color(0xFFF0C4)
let green = color(0x4E5E34)

func topRect(_ x: CGFloat, _ y: CGFloat, _ w: CGFloat, _ h: CGFloat) -> NSRect {
    NSRect(x: x, y: height - y - h, width: w, height: h)
}

func rounded(_ rect: NSRect, radius: CGFloat) -> NSBezierPath {
    NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius)
}

func fill(_ rect: NSRect, _ fillColor: NSColor, radius: CGFloat = 10) {
    fillColor.setFill()
    rounded(rect, radius: radius).fill()
}

func stroke(_ rect: NSRect, _ strokeColor: NSColor, width: CGFloat = 3, radius: CGFloat = 10) {
    strokeColor.setStroke()
    let shape = rounded(rect, radius: radius)
    shape.lineWidth = width
    shape.stroke()
}

func font(_ size: CGFloat, serif: Bool = true) -> NSFont {
    let names = serif
        ? ["STKaiti", "Kaiti SC", "STSongti-SC-Black", "STSong"]
        : ["Hiragino Sans GB W6", "Heiti SC", "PingFang SC Semibold"]
    for name in names {
        if let selected = NSFont(name: name, size: size) { return selected }
    }
    return .boldSystemFont(ofSize: size)
}

func drawText(
    _ value: String,
    rect: NSRect,
    size: CGFloat,
    textColor: NSColor,
    alignment: NSTextAlignment = .center,
    serif: Bool = true,
    outlineColor: NSColor? = nil,
    outlineWidth: CGFloat = 0
) {
    let paragraph = NSMutableParagraphStyle()
    paragraph.alignment = alignment
    paragraph.lineBreakMode = .byWordWrapping
    paragraph.lineSpacing = 0

    if let outlineColor, outlineWidth > 0 {
        let outlineAttributes: [NSAttributedString.Key: Any] = [
            .font: font(size, serif: serif),
            .foregroundColor: NSColor.clear,
            .paragraphStyle: paragraph,
            .strokeColor: outlineColor,
            .strokeWidth: outlineWidth,
            .kern: 0
        ]
        (value as NSString).draw(
            with: rect,
            options: [.usesLineFragmentOrigin, .usesFontLeading],
            attributes: outlineAttributes
        )
    }

    let attributes: [NSAttributedString.Key: Any] = [
        .font: font(size, serif: serif),
        .foregroundColor: textColor,
        .paragraphStyle: paragraph,
        .kern: 0
    ]
    (value as NSString).draw(
        with: rect,
        options: [.usesLineFragmentOrigin, .usesFontLeading],
        attributes: attributes
    )
}

func drawOutlinedTitle(_ value: String, rect: NSRect, size: CGFloat, textColor: NSColor) {
    drawText(value, rect: rect, size: size, textColor: textColor, outlineColor: .white, outlineWidth: 16)
    drawText(value, rect: rect, size: size, textColor: textColor, outlineColor: ink, outlineWidth: 9)
}

func drawPaperBackground() {
    let gradient = NSGradient(colors: [color(0xF5D99B), color(0xE7BC6C), color(0xD99B47)])!
    gradient.draw(in: NSRect(origin: .zero, size: canvas), angle: -10)

    var generator = SystemRandomNumberGenerator()
    for _ in 0..<6500 {
        let x = CGFloat.random(in: 0..<width, using: &generator)
        let y = CGFloat.random(in: 0..<height, using: &generator)
        let radius = CGFloat.random(in: 0.5...2.3, using: &generator)
        color(0x65401D, alpha: CGFloat.random(in: 0.018...0.075, using: &generator)).setFill()
        NSBezierPath(ovalIn: NSRect(x: x, y: y, width: radius, height: radius)).fill()
    }

    color(0x26331F, alpha: 0.20).setStroke()
    for row in 0..<4 {
        let mountain = NSBezierPath()
        mountain.move(to: NSPoint(x: -80, y: height - 600 + CGFloat(row) * 80))
        for index in 0...26 {
            let x = CGFloat(index) * 110 - 80
            let peak = CGFloat((index * 61 + row * 97) % 145)
            mountain.line(to: NSPoint(x: x, y: height - 560 + CGFloat(row) * 62 + peak))
        }
        mountain.lineWidth = 7
        mountain.stroke()
    }

    for side in [CGFloat(-24), width - 155] {
        for index in 0..<5 {
            let x = side + CGFloat(index) * 34
            ink.withAlphaComponent(0.33).setStroke()
            let stem = NSBezierPath()
            stem.move(to: NSPoint(x: x, y: 70))
            stem.line(to: NSPoint(x: x + 90, y: height - 40))
            stem.lineWidth = 13
            stem.stroke()
            for leafIndex in 0..<9 {
                let y = 170 + CGFloat(leafIndex) * 185
                color(0x273322, alpha: 0.26).setFill()
                NSBezierPath(ovalIn: NSRect(x: x - 52, y: y, width: 120, height: 26)).fill()
            }
        }
    }
}

func drawBrushBadge() {
    let shape = NSBezierPath()
    shape.move(to: NSPoint(x: 52, y: height - 50))
    shape.line(to: NSPoint(x: 455, y: height - 34))
    shape.line(to: NSPoint(x: 420, y: height - 166))
    shape.line(to: NSPoint(x: 78, y: height - 176))
    shape.close()
    red.setFill()
    shape.fill()
    drawText("新手必看", rect: topRect(83, 63, 336, 92), size: 66, textColor: .white, serif: true, outlineColor: ink, outlineWidth: 4)
}

func drawVerticalSeal() {
    let rect = topRect(1228, 330, 98, 210)
    fill(rect, darkRed, radius: 3)
    stroke(rect.insetBy(dx: 6, dy: 6), cream, width: 4, radius: 1)
    for (index, char) in ["经", "方", "经", "典"].enumerated() {
        drawText(char, rect: topRect(1244, 348 + CGFloat(index) * 43, 66, 40), size: 38, textColor: cream, serif: true)
    }
}

func drawTitleBlock() {
    drawBrushBadge()
    drawOutlinedTitle("柴胡家族", rect: topRect(96, 130, 1260, 320), size: 245, textColor: gold)
    drawOutlinedTitle("怎么学", rect: topRect(470, 410, 780, 250), size: 206, textColor: cream)
    drawVerticalSeal()

    let subtitle = topRect(105, 660, 1225, 116)
    fill(subtitle, color(0xF6DFA8), radius: 4)
    stroke(subtitle, ink, width: 5, radius: 4)
    fill(topRect(105, 660, 480, 116), red, radius: 4)
    drawText("经方必看", rect: topRect(132, 678, 425, 80), size: 70, textColor: .white, serif: true, outlineColor: ink, outlineWidth: 4)
    drawText("｜易混淆方剂讲解", rect: topRect(602, 678, 680, 80), size: 57, textColor: ink, serif: true)
}

func drawReferenceCrop() {
    guard let reference = NSImage(contentsOfFile: referencePath) else { return }

    NSGraphicsContext.saveGraphicsState()
    let personRect = NSRect(x: 1520, y: 95, width: 760, height: 1350)
    rounded(personRect, radius: 0).addClip()
    reference.draw(
        in: personRect,
        from: NSRect(x: 320, y: 0, width: 580, height: 1030),
        operation: .sourceOver,
        fraction: 1
    )
    NSGraphicsContext.restoreGraphicsState()

    color(0xFFF0C4, alpha: 0.34).setStroke()
    let glow = NSBezierPath(rect: personRect.insetBy(dx: -6, dy: -6))
    glow.lineWidth = 12
    glow.stroke()

    let cover = topRect(1512, 475, 780, 238)
    let gradient = NSGradient(colors: [color(0xE9C27B), color(0xD99B47)])!
    gradient.draw(in: cover, angle: -10)
    color(0x26331F, alpha: 0.17).setStroke()
    let mountain = NSBezierPath()
    mountain.move(to: NSPoint(x: cover.minX - 20, y: cover.minY + 80))
    for index in 0...8 {
        let x = cover.minX + CGFloat(index) * 110
        let peak = CGFloat((index * 73) % 118)
        mountain.line(to: NSPoint(x: x, y: cover.minY + 82 + peak))
    }
    mountain.lineWidth = 6
    mountain.stroke()
}

func drawHerbPhoto() {
    guard let image = NSImage(contentsOfFile: herbPath) else { return }
    let frame = topRect(2020, 1388, 410, 274)
    fill(frame, color(0xF8E8BD, alpha: 0.96), radius: 18)
    stroke(frame, brown, width: 6, radius: 18)
    let photoRect = frame.insetBy(dx: 16, dy: 16)
    NSGraphicsContext.saveGraphicsState()
    rounded(photoRect, radius: 12).addClip()
    image.draw(in: photoRect, from: NSRect(origin: .zero, size: image.size), operation: .sourceOver, fraction: 1)
    NSGraphicsContext.restoreGraphicsState()
    fill(topRect(2046, 1412, 142, 54), darkRed, radius: 6)
    drawText("柴胡", rect: topRect(2058, 1420, 118, 38), size: 32, textColor: .white, serif: true)
}

func drawComparisonCard(_ x: CGFloat, _ y: CGFloat, _ title: String, _ detail: String, _ titleSize: CGFloat = 48) {
    let rect = topRect(x, y, 520, 166)
    fill(rect, color(0xF6DEAA, alpha: 0.97), radius: 8)
    stroke(rect, brown, width: 4, radius: 8)
    drawText(title, rect: topRect(x + 150, y + 18, 340, 56), size: titleSize, textColor: ink, serif: true)
    drawText(detail, rect: topRect(x + 150, y + 80, 340, 74), size: 29, textColor: darkBrown, serif: true)

    color(0x6A3418, alpha: 0.20).setStroke()
    let icon = topRect(x + 28, y + 30, 86, 86)
    let path = NSBezierPath(ovalIn: icon)
    path.lineWidth = 5
    path.stroke()
}

func drawComparisonPanel() {
    let label = topRect(94, 835, 410, 94)
    fill(label, darkRed, radius: 7)
    stroke(label, color(0xD4A65F), width: 5, radius: 7)
    drawText("方剂对比", rect: topRect(114, 850, 370, 65), size: 66, textColor: .white, serif: true, outlineColor: ink, outlineWidth: 3)

    drawComparisonCard(105, 945, "小柴胡汤", "和解少阳\n寒热往来")
    drawComparisonCard(105, 1124, "大柴胡汤", "少阳兼里实\n心下急满")
    drawComparisonCard(105, 1303, "柴胡桂枝汤", "少阳兼太阳\n肢节烦疼", 42)
    drawComparisonCard(105, 1482, "柴胡桂枝\n干姜汤", "少阳兼津伤", 39)
}

func drawFamilyNode(_ rect: NSRect, title: String, detail: String, size: CGFloat = 42) {
    fill(rect, color(0xF6DEAA, alpha: 0.98), radius: 7)
    stroke(rect, brown, width: 4, radius: 7)
    drawText(title, rect: NSRect(x: rect.minX + 12, y: rect.minY + rect.height - 76, width: rect.width - 24, height: 54), size: size, textColor: ink, serif: true)
    drawText(detail, rect: NSRect(x: rect.minX + 16, y: rect.minY + 24, width: rect.width - 32, height: 48), size: 28, textColor: darkBrown, serif: true)
}

func drawFamilyMap() {
    let panel = topRect(690, 840, 780, 700)
    fill(panel, color(0xF0D49A, alpha: 0.84), radius: 16)
    stroke(panel, color(0x6A3418, alpha: 0.72), width: 5, radius: 16)

    let plaque = topRect(910, 888, 340, 80)
    fill(plaque, darkRed, radius: 7)
    stroke(plaque, color(0xD4A65F), width: 5, radius: 7)
    drawText("柴胡家族", rect: topRect(930, 902, 300, 54), size: 50, textColor: gold, serif: true)

    let hub = topRect(930, 1198, 310, 138)
    let nodes: [(NSRect, String, String, CGFloat)] = [
        (topRect(725, 988, 280, 125), "小柴胡汤", "和解少阳", 40),
        (topRect(1135, 988, 280, 125), "大柴胡汤", "少阳兼里实", 40),
        (topRect(725, 1394, 280, 125), "柴胡桂枝汤", "少阳兼太阳", 34),
        (topRect(1135, 1394, 280, 125), "柴胡桂枝\n干姜汤", "少阳兼津伤", 31)
    ]
    let hubCenter = NSPoint(x: hub.midX, y: hub.midY)
    darkRed.setStroke()
    for (rect, _, _, _) in nodes {
        let line = NSBezierPath()
        line.move(to: hubCenter)
        line.line(to: NSPoint(x: rect.midX, y: rect.midY))
        line.lineWidth = 7
        line.stroke()
    }

    fill(hub, red, radius: 18)
    stroke(hub.insetBy(dx: 8, dy: 8), cream, width: 5, radius: 12)
    drawText("小柴胡汤", rect: topRect(955, 1220, 260, 58), size: 46, textColor: .white, serif: true)
    drawText("核心方证", rect: topRect(970, 1278, 230, 40), size: 30, textColor: cream, serif: true)

    for (rect, title, detail, size) in nodes {
        drawFamilyNode(rect, title: title, detail: detail, size: size)
    }
}

func drawDrawerLabels() {
    let labels = ["柴胡", "黄芩", "半夏", "人参", "生姜"]
    for (index, label) in labels.enumerated() {
        let rect = topRect(2325, 690 + CGFloat(index) * 108, 150, 64)
        fill(rect, color(0x4A240F, alpha: 0.94), radius: 5)
        stroke(rect, color(0xB68038), width: 3, radius: 5)
        drawText(label, rect: topRect(2338, 701 + CGFloat(index) * 108, 124, 42), size: 34, textColor: gold, serif: true)
    }
}

func saveCover() {
    let image = NSImage(size: canvas)
    image.lockFocus()
    NSGraphicsContext.current?.imageInterpolation = .high
    drawPaperBackground()
    drawTitleBlock()
    drawComparisonPanel()
    drawFamilyMap()
    drawReferenceCrop()
    drawDrawerLabels()
    drawHerbPhoto()
    image.unlockFocus()

    guard let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let png = bitmap.representation(using: .png, properties: [:]) else {
        fatalError("Could not encode cover")
    }

    try! FileManager.default.createDirectory(
        atPath: (outputPath as NSString).deletingLastPathComponent,
        withIntermediateDirectories: true
    )
    try! png.write(to: URL(fileURLWithPath: outputPath))
    print("saved \(outputPath) \(Int(width))x\(Int(height))")
}

saveCover()

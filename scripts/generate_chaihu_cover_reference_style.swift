import AppKit
import Foundation

let width: CGFloat = 1242
let height: CGFloat = 1656
let canvas = NSSize(width: width, height: height)
let referencePath = "/var/folders/ty/6kw9zrnj60b1lhr2pstwr12m0000gp/T/codex-clipboard-f41e7943-a889-40e4-bb9c-056976880cf2.png"
let outputPath = "/Users/xxm/Documents/AI/ZY-demo/output/covers/chaihu_family_reference_style_source_1242x1656.png"

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
let paper = color(0xEACB8B)
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
    drawText(value, rect: rect, size: size, textColor: textColor, outlineColor: .white, outlineWidth: 12)
    drawText(value, rect: rect, size: size, textColor: textColor, outlineColor: ink, outlineWidth: 7)
}

func drawPaperPatch(_ rect: NSRect) {
    let gradient = NSGradient(colors: [color(0xF2DBA5), color(0xE2B963), color(0xD39A48)])!
    gradient.draw(in: rect, angle: -12)

    var generator = SystemRandomNumberGenerator()
    for _ in 0..<1600 {
        let x = CGFloat.random(in: rect.minX..<rect.maxX, using: &generator)
        let y = CGFloat.random(in: rect.minY..<rect.maxY, using: &generator)
        let radius = CGFloat.random(in: 0.4...1.7, using: &generator)
        color(0x65401D, alpha: CGFloat.random(in: 0.02...0.08, using: &generator)).setFill()
        NSBezierPath(ovalIn: NSRect(x: x, y: y, width: radius, height: radius)).fill()
    }

    color(0x26331F, alpha: 0.18).setStroke()
    for row in 0..<3 {
        let mountain = NSBezierPath()
        mountain.move(to: NSPoint(x: -30, y: rect.minY + 65 + CGFloat(row * 45)))
        for index in 0...14 {
            let x = CGFloat(index) * 100 - 30
            let peak = CGFloat((index * 61 + row * 97) % 135)
            mountain.line(to: NSPoint(x: x, y: rect.minY + 90 + CGFloat(row * 36) + peak))
        }
        mountain.lineWidth = 5
        mountain.stroke()
    }
}

func drawBrushBadge() {
    let shape = NSBezierPath()
    shape.move(to: NSPoint(x: 24, y: height - 32))
    shape.line(to: NSPoint(x: 350, y: height - 28))
    shape.line(to: NSPoint(x: 325, y: height - 118))
    shape.line(to: NSPoint(x: 40, y: height - 124))
    shape.close()
    red.setFill()
    shape.fill()

    for offset in stride(from: CGFloat(0), through: 26, by: 6) {
        color(0x7A120D, alpha: 0.45).setStroke()
        let brush = NSBezierPath()
        brush.move(to: NSPoint(x: 35 + offset, y: height - 125 - offset * 0.2))
        brush.line(to: NSPoint(x: 330 + offset * 0.4, y: height - 120 + offset * 0.4))
        brush.lineWidth = 3
        brush.stroke()
    }

    drawText("新手必看", rect: topRect(40, 42, 290, 72), size: 54, textColor: .white, serif: true, outlineColor: ink, outlineWidth: 4)
}

func drawVerticalSeal() {
    let rect = topRect(1110, 304, 94, 204)
    fill(rect, darkRed, radius: 3)
    stroke(rect.insetBy(dx: 5, dy: 5), cream, width: 3, radius: 1)
    drawText("经\n方\n经\n典", rect: topRect(1123, 319, 68, 175), size: 38, textColor: cream, serif: true)
}

func drawHeader() {
    let header = topRect(0, 0, width, 626)
    drawPaperPatch(header)

    // Ink bamboo at the edge recreates the layered, full-bleed reference composition.
    for side in [CGFloat(-8), width - 90] {
        for index in 0..<4 {
            let x = side + CGFloat(index) * 24
            ink.withAlphaComponent(0.38).setStroke()
            let stem = NSBezierPath()
            stem.move(to: NSPoint(x: x, y: height - 610))
            stem.line(to: NSPoint(x: x + 45, y: height - 2))
            stem.lineWidth = 8
            stem.stroke()
            for leafIndex in 0..<7 {
                let visualY = CGFloat(90 + leafIndex * 75)
                color(0x273322, alpha: 0.31).setFill()
                NSBezierPath(ovalIn: topRect(x - 28, visualY, 64, 17)).fill()
            }
        }
    }

    drawBrushBadge()
    drawOutlinedTitle("柴胡家族", rect: topRect(92, 72, 1058, 270), size: 222, textColor: gold)
    drawOutlinedTitle("怎么学", rect: topRect(350, 292, 700, 220), size: 188, textColor: cream)
    drawVerticalSeal()

    let subtitle = topRect(70, 514, 1092, 96)
    fill(subtitle, color(0xF6DFA8), radius: 4)
    stroke(subtitle, ink, width: 4, radius: 4)
    let redStrip = topRect(70, 514, 430, 96)
    fill(redStrip, red, radius: 4)
    drawText("经方必看", rect: topRect(91, 529, 382, 66), size: 55, textColor: .white, serif: true, outlineColor: ink, outlineWidth: 3)
    drawText("｜易混淆方剂讲解", rect: topRect(505, 529, 635, 66), size: 48, textColor: ink, serif: true)

    // The reference image has a second subtitle strip immediately below its first one;
    // cover that remnant so the requested subtitle appears only once.
    drawPaperPatch(topRect(0, 620, width, 68))
}

func drawCardTextPatch(
    top: CGFloat,
    title: String,
    detail: String,
    titleSize: CGFloat = 34
) {
    let patch = topRect(126, top, 242, 142)
    fill(patch, color(0xF3DBA4, alpha: 0.97), radius: 4)
    drawText(title, rect: topRect(133, top + 9, 226, 59), size: titleSize, textColor: ink, serif: true)
    drawText(detail, rect: topRect(137, top + 74, 218, 56), size: 22, textColor: darkBrown, serif: true)
}

func drawLeftCards() {
    // Preserve the original illustrated icons and replace only the formula copy.
    drawCardTextPatch(top: 774, title: "小柴胡汤", detail: "和解少阳\n寒热往来")
    drawCardTextPatch(top: 917, title: "大柴胡汤", detail: "少阳兼里实\n心下急满")
    drawCardTextPatch(top: 1060, title: "柴胡桂枝汤", detail: "少阳兼太阳\n肢节烦疼", titleSize: 29)
    drawCardTextPatch(top: 1204, title: "柴胡桂枝\n干姜汤", detail: "少阳兼津伤", titleSize: 27)
}

func drawPlaque(_ title: String) {
    let outer = topRect(824, 682, 260, 75)
    fill(outer, darkBrown, radius: 6)
    stroke(outer, color(0xD4A65F), width: 4, radius: 6)
    fill(outer.insetBy(dx: 8, dy: 8), darkRed, radius: 3)
    drawText(title, rect: topRect(836, 698, 236, 49), size: 35, textColor: gold, serif: true)
}

func drawFamilyNode(top: CGFloat, title: String, size: CGFloat = 31) {
    let node = topRect(844, top, 232, 78)
    fill(node, color(0xF2D79D, alpha: 0.98), radius: 4)
    stroke(node, brown, width: 3, radius: 4)
    drawText(title, rect: topRect(853, top + 12, 214, 58), size: size, textColor: ink, serif: true)
}

func drawRightFamily() {
    drawPlaque("柴胡家族")

    brown.setStroke()
    let spine = NSBezierPath()
    spine.move(to: NSPoint(x: 827, y: height - 760))
    spine.line(to: NSPoint(x: 827, y: height - 1125))
    spine.lineWidth = 4
    spine.stroke()

    for top in [775, 858, 941, 1024] {
        let y = height - CGFloat(top + 33)
        let connector = NSBezierPath()
        connector.move(to: NSPoint(x: 827, y: y))
        connector.line(to: NSPoint(x: 844, y: y))
        connector.lineWidth = 4
        connector.stroke()
        brown.setFill()
        NSBezierPath(ovalIn: NSRect(x: 821, y: y - 6, width: 12, height: 12)).fill()
    }

    drawFamilyNode(top: 775, title: "小柴胡汤")
    drawFamilyNode(top: 858, title: "大柴胡汤")
    drawFamilyNode(top: 941, title: "柴胡桂枝汤", size: 28)
    drawFamilyNode(top: 1024, title: "柴胡加龙骨\n牡蛎汤", size: 25)
}

func drawDrawerLabel(_ label: String, top: CGFloat) {
    let rect = topRect(1095, top, 116, 50)
    fill(rect, color(0x4A240F, alpha: 0.94), radius: 3)
    stroke(rect, color(0xB68038), width: 2, radius: 3)
    drawText(label, rect: topRect(1101, top + 9, 104, 34), size: 24, textColor: gold, serif: true)
}

func drawDrawerLabels() {
    drawDrawerLabel("柴胡", top: 755)
    drawDrawerLabel("黄芩", top: 838)
    drawDrawerLabel("半夏", top: 921)
    drawDrawerLabel("人参", top: 1004)
    drawDrawerLabel("生姜", top: 1087)
}

func saveCover() {
    guard let reference = NSImage(contentsOfFile: referencePath) else {
        fatalError("Could not load reference image")
    }

    let result = NSImage(size: canvas)
    result.lockFocus()
    NSGraphicsContext.current?.imageInterpolation = .high
    reference.draw(
        in: NSRect(origin: .zero, size: canvas),
        from: NSRect(origin: .zero, size: reference.size),
        operation: .sourceOver,
        fraction: 1
    )
    drawHeader()
    drawLeftCards()
    drawRightFamily()
    drawDrawerLabels()
    result.unlockFocus()

    guard let tiff = result.tiffRepresentation,
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

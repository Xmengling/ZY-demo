import AppKit
import Foundation

let canvas = NSSize(width: 1536, height: 2048)
let avatarPath = "/Users/xxm/Documents/AI/ZY-demo/avatar.jpg"
let herbPath = "/Users/xxm/Documents/AI/ZY-demo/ai-medical-consultant/backend/data/herbs/柴胡.jpg"
let outputPath = "/Users/xxm/Documents/AI/ZY-demo/output/covers/chaihu_family_tcm_source_1536x2048.png"

func color(_ hex: UInt32, alpha: CGFloat = 1) -> NSColor {
    NSColor(
        calibratedRed: CGFloat((hex >> 16) & 0xff) / 255,
        green: CGFloat((hex >> 8) & 0xff) / 255,
        blue: CGFloat(hex & 0xff) / 255,
        alpha: alpha
    )
}

let ink = color(0x1A120D)
let red = color(0xA52318)
let darkRed = color(0x70140F)
let gold = color(0xF4BE3B)
let cream = color(0xFFF0C4)
let brown = color(0x673A20)
let green = color(0x435936)
let paleGreen = color(0xDCE0C1)

func font(_ size: CGFloat, serif: Bool = true) -> NSFont {
    let names = serif
        ? ["STKaiti", "Kaiti SC", "Songti SC", "STSong"]
        : ["Hiragino Sans GB W6", "Heiti SC", "PingFang SC Semibold"]
    for name in names {
        if let result = NSFont(name: name, size: size) { return result }
    }
    return .boldSystemFont(ofSize: size)
}

func rounded(_ rect: NSRect, radius: CGFloat) -> NSBezierPath {
    NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius)
}

func fill(_ rect: NSRect, _ fillColor: NSColor, radius: CGFloat = 16) {
    fillColor.setFill()
    rounded(rect, radius: radius).fill()
}

func stroke(_ rect: NSRect, _ strokeColor: NSColor, width: CGFloat = 4, radius: CGFloat = 16) {
    strokeColor.setStroke()
    let shape = rounded(rect, radius: radius)
    shape.lineWidth = width
    shape.stroke()
}

func drawText(
    _ value: String,
    in rect: NSRect,
    size: CGFloat,
    textColor: NSColor = ink,
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
        let outline: [NSAttributedString.Key: Any] = [
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
            attributes: outline
        )
    }

    let textAttributes: [NSAttributedString.Key: Any] = [
        .font: font(size, serif: serif),
        .foregroundColor: textColor,
        .paragraphStyle: paragraph,
        .kern: 0
    ]
    (value as NSString).draw(
        with: rect,
        options: [.usesLineFragmentOrigin, .usesFontLeading],
        attributes: textAttributes
    )
}

func line(from start: NSPoint, to end: NSPoint, lineColor: NSColor, width: CGFloat = 5) {
    lineColor.setStroke()
    let shape = NSBezierPath()
    shape.move(to: start)
    shape.line(to: end)
    shape.lineWidth = width
    shape.lineCapStyle = .round
    shape.stroke()
}

func drawPaperBackground() {
    let gradient = NSGradient(colors: [color(0xF8E8BD), color(0xE9C985), color(0xD7A95C)])!
    gradient.draw(in: NSRect(origin: .zero, size: canvas), angle: -9)

    var generator = SystemRandomNumberGenerator()
    for _ in 0..<5200 {
        let x = CGFloat.random(in: 0..<canvas.width, using: &generator)
        let y = CGFloat.random(in: 0..<canvas.height, using: &generator)
        let radius = CGFloat.random(in: 0.5...2.2, using: &generator)
        color(0x6D411F, alpha: CGFloat.random(in: 0.018...0.075, using: &generator)).setFill()
        NSBezierPath(ovalIn: NSRect(x: x, y: y, width: radius, height: radius)).fill()
    }

    // Light ink-wash mountains keep the title readable while giving the poster depth.
    for row in 0..<3 {
        let mountain = NSBezierPath()
        mountain.move(to: NSPoint(x: -80, y: 1500 + CGFloat(row * 72)))
        for index in 0...16 {
            let x = CGFloat(index) * 110 - 80
            let peak = CGFloat((index * 67 + row * 89) % 180)
            mountain.line(to: NSPoint(x: x, y: 1540 + CGFloat(row * 56) + peak))
        }
        color(0x32412E, alpha: 0.16).setStroke()
        mountain.lineWidth = 6
        mountain.stroke()
    }

    // Bamboo silhouettes frame the composition without competing with the copy.
    for side in [CGFloat(0), canvas.width - 145] {
        for index in 0..<4 {
            let x = side + CGFloat(index) * 38
            line(from: NSPoint(x: x, y: 1050), to: NSPoint(x: x + 75, y: 2010), lineColor: color(0x33452E, alpha: 0.32), width: 13)
            for leafIndex in 0..<7 {
                let y = 1160 + CGFloat(leafIndex) * 118
                let leafX = x + CGFloat(leafIndex) * 9
                color(0x33452E, alpha: 0.27).setFill()
                NSBezierPath(ovalIn: NSRect(x: leafX - 34, y: y, width: 72, height: 20)).fill()
            }
        }
    }

    fill(NSRect(x: 0, y: 0, width: canvas.width, height: 88), color(0x3A2115), radius: 0)
    fill(NSRect(x: 0, y: 88, width: canvas.width, height: 10), red, radius: 0)
}

func drawBadge() {
    let rect = NSRect(x: 80, y: 1880, width: 330, height: 104)
    fill(rect, red, radius: 8)
    stroke(rect.insetBy(dx: 8, dy: 8), cream, width: 3, radius: 5)
    drawText("新手必看", in: NSRect(x: 88, y: 1898, width: 314, height: 72), size: 50, textColor: .white, serif: true, outlineColor: ink, outlineWidth: 3)
}

func drawTitle() {
    // Two outline passes recreate the thick, high-contrast short-video cover lettering.
    let firstLine = NSRect(x: 120, y: 1640, width: 1296, height: 260)
    drawText("柴胡家族", in: firstLine, size: 200, textColor: gold, serif: true, outlineColor: .white, outlineWidth: 11)
    drawText("柴胡家族", in: firstLine, size: 200, textColor: gold, serif: true, outlineColor: ink, outlineWidth: 7)

    let secondLine = NSRect(x: 250, y: 1450, width: 1036, height: 230)
    drawText("怎么学", in: secondLine, size: 176, textColor: cream, serif: true, outlineColor: .white, outlineWidth: 11)
    drawText("怎么学", in: secondLine, size: 176, textColor: cream, serif: true, outlineColor: ink, outlineWidth: 7)

    // A small seal-like question mark gives the title a clear visual stop.
    fill(NSRect(x: 1260, y: 1506, width: 132, height: 132), red, radius: 14)
    stroke(NSRect(x: 1267, y: 1513, width: 118, height: 118), cream, width: 4, radius: 10)
    drawText("？", in: NSRect(x: 1266, y: 1525, width: 120, height: 94), size: 76, textColor: .white, serif: false)
}

func drawSubtitle() {
    let outer = NSRect(x: 82, y: 1335, width: 1372, height: 112)
    fill(outer, color(0xF7E3AE, alpha: 0.98), radius: 9)
    stroke(outer, ink, width: 5, radius: 9)
    fill(NSRect(x: 82, y: 1335, width: 430, height: 112), darkRed, radius: 9)
    drawText("经方必看", in: NSRect(x: 105, y: 1353, width: 385, height: 78), size: 57, textColor: .white, serif: true)
    drawText("｜易混淆方剂讲解", in: NSRect(x: 510, y: 1353, width: 920, height: 78), size: 54, textColor: ink, serif: true)
}

func drawNode(_ title: String, detail: String, rect: NSRect, accent: NSColor) {
    fill(rect, color(0xFFF1C9, alpha: 0.98), radius: 18)
    stroke(rect, brown, width: 5, radius: 18)
    fill(NSRect(x: rect.minX + 8, y: rect.maxY - 64, width: rect.width - 16, height: 56), accent, radius: 12)
    drawText(title, in: NSRect(x: rect.minX + 14, y: rect.maxY - 59, width: rect.width - 28, height: 45), size: title.count > 7 ? 31 : 38, textColor: .white, serif: true)
    drawText(detail, in: NSRect(x: rect.minX + 16, y: rect.minY + 19, width: rect.width - 32, height: rect.height - 92), size: 29, textColor: ink, serif: true)
}

func drawFamilyMap() {
    let panel = NSRect(x: 74, y: 590, width: 1388, height: 710)
    fill(panel, color(0xF3DDA8, alpha: 0.72), radius: 26)
    stroke(panel, color(0x70401F, alpha: 0.72), width: 5, radius: 26)

    fill(NSRect(x: 112, y: 1208, width: 300, height: 58), darkRed, radius: 8)
    drawText("柴胡家族关系图", in: NSRect(x: 120, y: 1218, width: 284, height: 40), size: 31, textColor: .white, serif: true)

    let hubCenter = NSPoint(x: 768, y: 968)
    let hubRect = NSRect(x: 608, y: 858, width: 320, height: 220)
    let nodes: [(NSRect, String, String, NSColor)] = [
        (NSRect(x: 120, y: 1045, width: 390, height: 175), "柴胡桂枝汤", "少阳兼太阳", green),
        (NSRect(x: 1025, y: 1045, width: 390, height: 175), "大柴胡汤", "少阳兼里实", red),
        (NSRect(x: 120, y: 670, width: 390, height: 175), "柴胡桂枝干姜汤", "少阳兼津伤", green),
        (NSRect(x: 1025, y: 670, width: 390, height: 175), "柴胡加龙骨牡蛎汤", "少阳兼烦惊", red)
    ]

    for (rect, _, _, _) in nodes {
        line(from: hubCenter, to: NSPoint(x: rect.midX, y: rect.midY), lineColor: darkRed, width: 8)
        red.setFill()
        NSBezierPath(ovalIn: NSRect(x: rect.midX - 8, y: rect.midY - 8, width: 16, height: 16)).fill()
    }

    fill(hubRect, red, radius: 34)
    stroke(hubRect.insetBy(dx: 10, dy: 10), cream, width: 5, radius: 26)
    drawText("小柴胡汤", in: NSRect(x: 630, y: 970, width: 276, height: 68), size: 49, textColor: .white, serif: true)
    drawText("和解少阳", in: NSRect(x: 640, y: 903, width: 256, height: 50), size: 34, textColor: cream, serif: true)

    for (rect, title, detail, accent) in nodes {
        drawNode(title, detail: detail, rect: rect, accent: accent)
    }
}

func drawHerbPhoto() {
    let frame = NSRect(x: 82, y: 168, width: 490, height: 352)
    fill(frame, color(0xF8E8BD), radius: 22)
    stroke(frame, brown, width: 7, radius: 22)
    guard let image = NSImage(contentsOfFile: herbPath) else { return }
    let photoRect = frame.insetBy(dx: 18, dy: 18)
    NSGraphicsContext.saveGraphicsState()
    rounded(photoRect, radius: 14).addClip()
    image.draw(in: photoRect, from: NSRect(origin: .zero, size: image.size), operation: .sourceOver, fraction: 1)
    NSGraphicsContext.restoreGraphicsState()
    fill(NSRect(x: 111, y: 190, width: 165, height: 62), darkRed, radius: 8)
    drawText("柴胡", in: NSRect(x: 120, y: 201, width: 147, height: 43), size: 34, textColor: .white, serif: true)
}

func drawAvatar() {
    guard let image = NSImage(contentsOfFile: avatarPath) else { return }
    let target = NSRect(x: 930, y: 118, width: 450, height: 450)
    NSGraphicsContext.saveGraphicsState()
    NSBezierPath(ovalIn: target).addClip()
    let source = NSRect(x: 133, y: 35, width: 1180, height: 1180)
    image.draw(in: target, from: source, operation: .sourceOver, fraction: 1)
    NSGraphicsContext.restoreGraphicsState()

    cream.setStroke()
    let inner = NSBezierPath(ovalIn: target.insetBy(dx: 2, dy: 2))
    inner.lineWidth = 18
    inner.stroke()
    red.setStroke()
    let outer = NSBezierPath(ovalIn: target.insetBy(dx: -7, dy: -7))
    outer.lineWidth = 7
    outer.stroke()

    fill(NSRect(x: 978, y: 112, width: 354, height: 70), darkRed, radius: 31)
    drawText("经方学习笔记", in: NSRect(x: 992, y: 126, width: 326, height: 48), size: 33, textColor: .white, serif: true)
}

func drawFooterNote() {
    drawText("先抓核心方证  ·  再辨病机分支", in: NSRect(x: 84, y: 103, width: 760, height: 48), size: 32, textColor: cream, alignment: .left, serif: true)
}

func save() {
    let image = NSImage(size: canvas)
    image.lockFocus()
    NSGraphicsContext.current?.imageInterpolation = .high
    drawPaperBackground()
    drawBadge()
    drawTitle()
    drawSubtitle()
    drawFamilyMap()
    drawHerbPhoto()
    drawAvatar()
    drawFooterNote()
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
    print("saved \(outputPath) \(Int(canvas.width))x\(Int(canvas.height))")
}

save()

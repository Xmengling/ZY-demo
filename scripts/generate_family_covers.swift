import AppKit
import Foundation

let canvas = NSSize(width: 2560, height: 1920)
let sourceMahuang = "/var/folders/ty/6kw9zrnj60b1lhr2pstwr12m0000gp/T/codex-clipboard-fe6a2d3b-edad-45d4-8d8c-3003d6e3044b.png"
let sourceGuizhi = "/var/folders/ty/6kw9zrnj60b1lhr2pstwr12m0000gp/T/codex-clipboard-23f429d8-2ac7-471a-a5da-d857290b1571.png"
let outputDir = "/Users/xxm/Documents/AI/ZY-demo/output/covers"

func c(_ hex: UInt32, _ alpha: CGFloat = 1) -> NSColor {
    NSColor(
        calibratedRed: CGFloat((hex >> 16) & 0xff) / 255,
        green: CGFloat((hex >> 8) & 0xff) / 255,
        blue: CGFloat(hex & 0xff) / 255,
        alpha: alpha
    )
}

let ink = c(0x17100B)
let red = c(0x9E170F)
let darkRed = c(0x6E0F0B)
let gold = c(0xF2B92F)
let cream = c(0xF4DFAD)
let paper = c(0xEBC77B)
let brown = c(0x6A3517)
let green = c(0x40542D)

func font(_ size: CGFloat, bold: Bool = true, serif: Bool = false) -> NSFont {
    let preferred = serif ? ["STKaiti", "Kaiti SC", "Songti SC"] : ["Hiragino Sans GB W6", "Heiti SC", "PingFang SC"]
    for name in preferred {
        if let f = NSFont(name: name, size: size) { return f }
    }
    return bold ? .boldSystemFont(ofSize: size) : .systemFont(ofSize: size)
}

func path(_ rect: NSRect, radius: CGFloat = 18) -> NSBezierPath {
    NSBezierPath(roundedRect: rect, xRadius: radius, yRadius: radius)
}

func fill(_ rect: NSRect, _ color: NSColor, radius: CGFloat = 18) {
    color.setFill()
    path(rect, radius: radius).fill()
}

func stroke(_ rect: NSRect, _ color: NSColor, width: CGFloat = 4, radius: CGFloat = 18) {
    color.setStroke()
    let p = path(rect, radius: radius)
    p.lineWidth = width
    p.stroke()
}

func text(_ value: String, in rect: NSRect, size: CGFloat, color: NSColor = ink,
          alignment: NSTextAlignment = .center, strokeColor: NSColor? = nil,
          strokeWidth: CGFloat = 0, serif: Bool = false) {
    let para = NSMutableParagraphStyle()
    para.alignment = alignment
    para.lineBreakMode = .byWordWrapping
    let attrs: [NSAttributedString.Key: Any] = [
        .font: font(size, serif: serif),
        .foregroundColor: color,
        .paragraphStyle: para,
        .kern: 0
    ]
    if let outline = strokeColor, strokeWidth != 0 {
        let outlineAttrs: [NSAttributedString.Key: Any] = [
            .font: font(size, serif: serif),
            .foregroundColor: NSColor.clear,
            .paragraphStyle: para,
            .strokeColor: outline,
            .strokeWidth: abs(strokeWidth),
            .kern: 0
        ]
        (value as NSString).draw(with: rect, options: [.usesLineFragmentOrigin, .usesFontLeading], attributes: outlineAttrs)
    }
    (value as NSString).draw(with: rect, options: [.usesLineFragmentOrigin, .usesFontLeading], attributes: attrs)
}

func line(_ a: NSPoint, _ b: NSPoint, color: NSColor, width: CGFloat = 4) {
    color.setStroke()
    let p = NSBezierPath()
    p.move(to: a)
    p.line(to: b)
    p.lineWidth = width
    p.stroke()
}

func parchment() {
    let gradient = NSGradient(colors: [c(0xF3D99D), c(0xE1B764), c(0xC98C3E)])!
    gradient.draw(in: NSRect(origin: .zero, size: canvas), angle: -12)

    var rng = SystemRandomNumberGenerator()
    for _ in 0..<3500 {
        let x = CGFloat.random(in: 0..<canvas.width, using: &rng)
        let y = CGFloat.random(in: 0..<canvas.height, using: &rng)
        let r = CGFloat.random(in: 0.5...2.3, using: &rng)
        c(0x5E3215, CGFloat.random(in: 0.025...0.11, using: &rng)).setFill()
        NSBezierPath(ovalIn: NSRect(x: x, y: y, width: r, height: r)).fill()
    }

    // Restrained ink mountains keep the two covers in the same visual family.
    c(0x26311F, 0.22).setStroke()
    for row in 0..<3 {
        let p = NSBezierPath()
        p.move(to: NSPoint(x: -80, y: 1420 + CGFloat(row * 90)))
        for i in 0...18 {
            let x = CGFloat(i) * 160 - 80
            let peak = CGFloat((i * 71 + row * 97) % 230)
            p.line(to: NSPoint(x: x, y: 1500 + CGFloat(row * 65) + peak))
        }
        p.lineWidth = 8
        p.stroke()
    }

    fill(NSRect(x: 0, y: 0, width: canvas.width, height: 115), c(0x3A1D0C, 0.95), radius: 0)
    fill(NSRect(x: 0, y: 115, width: canvas.width, height: 12), red, radius: 0)
}

func badge(_ label: String, x: CGFloat, y: CGFloat, width: CGFloat) {
    fill(NSRect(x: x, y: y, width: width, height: 116), red, radius: 10)
    stroke(NSRect(x: x + 7, y: y + 7, width: width - 14, height: 102), cream, width: 3, radius: 7)
    text(label, in: NSRect(x: x, y: y + 13, width: width, height: 88), size: 64, color: .white,
         strokeColor: ink, strokeWidth: -4, serif: true)
}

func subtitle(_ x: CGFloat, _ y: CGFloat, _ width: CGFloat) {
    fill(NSRect(x: x, y: y, width: width, height: 112), c(0xF1D99D, 0.96), radius: 6)
    stroke(NSRect(x: x, y: y, width: width, height: 112), ink, width: 5, radius: 6)
    fill(NSRect(x: x, y: y, width: 390, height: 112), darkRed, radius: 6)
    text("经方必看", in: NSRect(x: x + 18, y: y + 15, width: 355, height: 83), size: 60, color: .white,
         strokeColor: ink, strokeWidth: -3, serif: true)
    text("易混淆方剂讲解", in: NSRect(x: x + 420, y: y + 18, width: width - 440, height: 78), size: 55,
         color: ink, serif: true)
}

func avatar(imagePath: String, crop: NSRect, target: NSRect) {
    guard let image = NSImage(contentsOfFile: imagePath) else { return }
    NSGraphicsContext.saveGraphicsState()
    let clip = NSBezierPath(ovalIn: target)
    clip.addClip()
    image.draw(in: target, from: crop, operation: .sourceOver, fraction: 1)
    NSGraphicsContext.restoreGraphicsState()
    c(0xFFF3CF).setStroke()
    let border = NSBezierPath(ovalIn: target.insetBy(dx: 2, dy: 2))
    border.lineWidth = 18
    border.stroke()
    red.setStroke()
    let outer = NSBezierPath(ovalIn: target.insetBy(dx: -7, dy: -7))
    outer.lineWidth = 8
    outer.stroke()
    fill(NSRect(x: target.midX - 160, y: target.minY - 35, width: 320, height: 76), darkRed, radius: 34)
    text("经方张老师", in: NSRect(x: target.midX - 150, y: target.minY - 21, width: 300, height: 56), size: 36, color: .white, serif: true)
}

func node(_ title: String, detail: String, center: NSPoint, size: NSSize, accent: NSColor = red) {
    let r = NSRect(x: center.x - size.width / 2, y: center.y - size.height / 2, width: size.width, height: size.height)
    fill(r, c(0xF4D99E, 0.98), radius: 22)
    stroke(r, ink, width: 7, radius: 22)
    fill(NSRect(x: r.minX + 10, y: r.maxY - 62, width: r.width - 20, height: 52), accent, radius: 12)
    text(title, in: NSRect(x: r.minX + 14, y: r.maxY - 58, width: r.width - 28, height: 43), size: title.count > 7 ? 34 : 40, color: .white, serif: true)
    text(detail, in: NSRect(x: r.minX + 18, y: r.minY + 28, width: r.width - 36, height: r.height - 100), size: 31, color: ink, serif: true)
}

func herbSprigs(origin: NSPoint, scale: CGFloat, color: NSColor) {
    for i in 0..<7 {
        let x = origin.x + CGFloat(i) * 36 * scale
        line(NSPoint(x: x, y: origin.y), NSPoint(x: x + CGFloat(i % 2 == 0 ? 34 : -16) * scale, y: origin.y + 370 * scale), color: color, width: 12 * scale)
        for j in 1...5 {
            let yy = origin.y + CGFloat(j) * 58 * scale
            color.setFill()
            NSBezierPath(ovalIn: NSRect(x: x - 12 * scale, y: yy, width: 25 * scale, height: 13 * scale)).fill()
        }
    }
    brown.setStroke()
    let tie = NSBezierPath(ovalIn: NSRect(x: origin.x - 30 * scale, y: origin.y + 45 * scale, width: 300 * scale, height: 75 * scale))
    tie.lineWidth = 13 * scale
    tie.stroke()
}

func checkmark(_ label: String, x: CGFloat) {
    fill(NSRect(x: x, y: 22, width: 430, height: 72), c(0xF7E8BC), radius: 6)
    stroke(NSRect(x: x, y: 22, width: 430, height: 72), brown, width: 4, radius: 6)
    text("✓", in: NSRect(x: x + 12, y: 26, width: 70, height: 56), size: 50, color: red)
    text(label, in: NSRect(x: x + 70, y: 29, width: 345, height: 52), size: 38, color: ink, serif: true)
}

func drawMahuang() {
    parchment()
    badge("新手必看", x: 105, y: 1742, width: 440)
    text("麻黄家族", in: NSRect(x: 90, y: 1340, width: 1320, height: 365), size: 255, color: gold,
         strokeColor: ink, strokeWidth: -8, serif: true)
    text("怎么学？", in: NSRect(x: 210, y: 1090, width: 1080, height: 285), size: 205, color: c(0xFFF1D0),
         strokeColor: ink, strokeWidth: -9, serif: true)
    subtitle(110, 980, 1280)

    // A radial family map replaces the repeated five-column card layout.
    let hub = NSPoint(x: 1430, y: 620)
    let points = [
        NSPoint(x: 520, y: 700), NSPoint(x: 870, y: 430),
        NSPoint(x: 1370, y: 320), NSPoint(x: 1810, y: 520),
        NSPoint(x: 1880, y: 820)
    ]
    for p in points { line(hub, p, color: darkRed, width: 10) }
    c(0xB61C12).setFill()
    NSBezierPath(ovalIn: NSRect(x: hub.x - 160, y: hub.y - 160, width: 320, height: 320)).fill()
    c(0xF8E7B6).setStroke()
    let hubRing = NSBezierPath(ovalIn: NSRect(x: hub.x - 145, y: hub.y - 145, width: 290, height: 290))
    hubRing.lineWidth = 7
    hubRing.stroke()
    text("麻黄汤\n发汗解表", in: NSRect(x: hub.x - 140, y: hub.y - 83, width: 280, height: 180), size: 48, color: .white, serif: true)
    node("大青龙汤", detail: "表实兼里热\n不汗而烦躁", center: points[0], size: NSSize(width: 350, height: 220))
    node("小青龙汤", detail: "表寒夹水饮\n咳喘痰清稀", center: points[1], size: NSSize(width: 350, height: 220), accent: green)
    node("桂枝麻黄各半汤", detail: "表郁轻证\n微发其汗", center: points[2], size: NSSize(width: 430, height: 220))
    node("麻杏石甘汤", detail: "肺热壅盛\n汗出而喘", center: points[3], size: NSSize(width: 350, height: 220), accent: green)
    node("麻黄附子细辛汤", detail: "少阴兼表\n恶寒无汗", center: points[4], size: NSSize(width: 390, height: 220))

    herbSprigs(origin: NSPoint(x: 2220, y: 1040), scale: 0.72, color: green)
    avatar(imagePath: sourceMahuang, crop: NSRect(x: 1740, y: 1160, width: 620, height: 620),
           target: NSRect(x: 2050, y: 170, width: 410, height: 410))
    checkmark("先抓核心方证", x: 70)
    checkmark("再看病机分支", x: 535)
    checkmark("最后辨类方边界", x: 1000)
    checkmark("一张图记家族", x: 1465)
}

func scrollCard(_ index: Int, title: String, detail: String, x: CGFloat, y: CGFloat, height: CGFloat) {
    fill(NSRect(x: x, y: y, width: 360, height: height), c(0xF3DDA8, 0.98), radius: 6)
    stroke(NSRect(x: x, y: y, width: 360, height: height), brown, width: 7, radius: 6)
    fill(NSRect(x: x - 18, y: y + height - 38, width: 396, height: 44), brown, radius: 20)
    fill(NSRect(x: x - 18, y: y - 7, width: 396, height: 44), brown, radius: 20)
    c(0xB21C13).setFill()
    NSBezierPath(ovalIn: NSRect(x: x + 135, y: y + height - 98, width: 90, height: 90)).fill()
    text("\(index)", in: NSRect(x: x + 140, y: y + height - 84, width: 80, height: 60), size: 42, color: .white)
    text(title, in: NSRect(x: x + 24, y: y + height - 208, width: 312, height: 115), size: title.count > 7 ? 38 : 48, color: ink, serif: true)
    line(NSPoint(x: x + 55, y: y + height - 225), NSPoint(x: x + 305, y: y + height - 225), color: red, width: 5)
    text(detail, in: NSRect(x: x + 34, y: y + 48, width: 292, height: height - 290), size: 35, color: ink, serif: true)
}

func drawGuizhi() {
    parchment()
    badge("新手必看", x: 105, y: 1742, width: 440)

    // A strong vertical seal and right-shifted title deliberately separate this cover from the radial Mahuang version.
    fill(NSRect(x: 95, y: 1040, width: 190, height: 600), darkRed, radius: 12)
    stroke(NSRect(x: 108, y: 1053, width: 164, height: 574), cream, width: 5, radius: 8)
    text("桂\n枝\n家\n族", in: NSRect(x: 115, y: 1100, width: 150, height: 500), size: 82, color: .white, serif: true)
    text("怎么学？", in: NSRect(x: 350, y: 1280, width: 1460, height: 350), size: 250, color: gold,
         strokeColor: ink, strokeWidth: -9, serif: true)
    text("从桂枝汤出发", in: NSRect(x: 430, y: 1120, width: 1250, height: 140), size: 88, color: c(0xFFF1D0),
         strokeColor: darkRed, strokeWidth: -5, serif: true)
    subtitle(360, 1010, 1370)

    // Stepwise hanging scrolls communicate progression rather than a comparison table.
    scrollCard(1, title: "桂枝汤", detail: "营卫不和\n汗出恶风", x: 90, y: 245, height: 650)
    scrollCard(2, title: "加葛根汤", detail: "项背强几几\n兼见下利", x: 500, y: 245, height: 610)
    scrollCard(3, title: "加厚朴杏子汤", detail: "桂枝汤证\n兼喘咳", x: 910, y: 245, height: 570)
    scrollCard(4, title: "加芍药汤", detail: "太阳误下\n腹满时痛", x: 1320, y: 245, height: 530)
    scrollCard(5, title: "小建中汤", detail: "里虚腹痛\n喜温喜按", x: 1730, y: 245, height: 490)
    for x in stride(from: CGFloat(445), through: 1710, by: 410) {
        line(NSPoint(x: x, y: 520), NSPoint(x: x + 35, y: 520), color: red, width: 12)
        line(NSPoint(x: x + 35, y: 520), NSPoint(x: x + 12, y: 540), color: red, width: 8)
        line(NSPoint(x: x + 35, y: 520), NSPoint(x: x + 12, y: 500), color: red, width: 8)
    }

    // Cinnamon twigs form a compact theme mark, not another full-height prop.
    for i in 0..<7 {
        let x = 2070 + CGFloat(i) * 44
        line(NSPoint(x: x, y: 1120), NSPoint(x: x + 120, y: 1580), color: brown, width: 25)
        line(NSPoint(x: x + 8, y: 1160), NSPoint(x: x + 128, y: 1620), color: c(0xC07B36), width: 6)
    }
    line(NSPoint(x: 2050, y: 1260), NSPoint(x: 2400, y: 1340), color: darkRed, width: 22)
    avatar(imagePath: sourceGuizhi, crop: NSRect(x: 865, y: 590, width: 520, height: 480),
           target: NSRect(x: 2110, y: 160, width: 360, height: 360))
    checkmark("先守桂枝汤", x: 70)
    checkmark("按兼证做加减", x: 535)
    checkmark("抓住营卫与里虚", x: 1000)
    checkmark("路线清楚不混淆", x: 1465)
}

func save(name: String, draw: () -> Void) {
    let image = NSImage(size: canvas)
    image.lockFocus()
    NSGraphicsContext.current?.imageInterpolation = .high
    draw()
    image.unlockFocus()
    guard let tiff = image.tiffRepresentation,
          let bitmap = NSBitmapImageRep(data: tiff),
          let png = bitmap.representation(using: .png, properties: [:]) else {
        fatalError("Could not encode image")
    }
    try! png.write(to: URL(fileURLWithPath: "\(outputDir)/\(name)"))
}

try! FileManager.default.createDirectory(atPath: outputDir, withIntermediateDirectories: true)
save(name: "mahuang-family-cover-v2.png", draw: drawMahuang)
save(name: "guizhi-family-cover-v2.png", draw: drawGuizhi)

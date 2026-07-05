import math
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "sports"
W, H = 960, 620
SCALE = 1


def mix(a, b, t):
    return tuple(int(a[i] * (1 - t) + b[i] * t) for i in range(3))


def make_canvas(bg=(246, 249, 250)):
    w, h = W * SCALE, H * SCALE
    return [[(*bg, 255) for _ in range(w)] for _ in range(h)]


def set_px(img, x, y, color):
    if 0 <= x < len(img[0]) and 0 <= y < len(img):
        img[y][x] = color


def circle(img, cx, cy, r, color):
    cx *= SCALE
    cy *= SCALE
    r *= SCALE
    x0, x1 = int(cx - r), int(cx + r)
    y0, y1 = int(cy - r), int(cy + r)
    rr = r * r
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if (x - cx) ** 2 + (y - cy) ** 2 <= rr:
                set_px(img, x, y, color)


def rect(img, x0, y0, x1, y1, color):
    x0, y0, x1, y1 = [int(v * SCALE) for v in (x0, y0, x1, y1)]
    if x0 > x1:
        x0, x1 = x1, x0
    if y0 > y1:
        y0, y1 = y1, y0
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            set_px(img, x, y, color)


def polygon(img, pts, color):
    pts = [(int(x * SCALE), int(y * SCALE)) for x, y in pts]
    ys = [p[1] for p in pts]
    for y in range(min(ys), max(ys) + 1):
        xs = []
        for i, p1 in enumerate(pts):
            p2 = pts[(i + 1) % len(pts)]
            if (p1[1] <= y < p2[1]) or (p2[1] <= y < p1[1]):
                x = p1[0] + (y - p1[1]) * (p2[0] - p1[0]) / (p2[1] - p1[1])
                xs.append(int(x))
        xs.sort()
        for a, b in zip(xs[0::2], xs[1::2]):
            for x in range(a, b + 1):
                set_px(img, x, y, color)


def line(img, x0, y0, x1, y1, width, color):
    x0 *= SCALE
    y0 *= SCALE
    x1 *= SCALE
    y1 *= SCALE
    width *= SCALE
    dx, dy = x1 - x0, y1 - y0
    steps = int(max(abs(dx), abs(dy))) + 1
    for i in range(steps + 1):
        t = i / max(steps, 1)
        x = x0 + dx * t
        y = y0 + dy * t
        r = width / 2
        for yy in range(int(y - r), int(y + r) + 1):
            for xx in range(int(x - r), int(x + r) + 1):
                if (xx - x) ** 2 + (yy - y) ** 2 <= r * r:
                    set_px(img, xx, yy, color)


def ellipse(img, cx, cy, rx, ry, color, angle=0):
    cx *= SCALE
    cy *= SCALE
    rx *= SCALE
    ry *= SCALE
    ca, sa = math.cos(angle), math.sin(angle)
    rmax = max(rx, ry)
    for y in range(int(cy - rmax), int(cy + rmax) + 1):
        for x in range(int(cx - rmax), int(cx + rmax) + 1):
            px, py = x - cx, y - cy
            ux = px * ca + py * sa
            uy = -px * sa + py * ca
            if (ux / rx) ** 2 + (uy / ry) ** 2 <= 1:
                set_px(img, x, y, color)


def downsample(img):
    out = []
    for y in range(H):
        row = []
        for x in range(W):
            acc = [0, 0, 0, 0]
            for yy in range(SCALE):
                for xx in range(SCALE):
                    px = img[y * SCALE + yy][x * SCALE + xx]
                    for i in range(4):
                        acc[i] += px[i]
            n = SCALE * SCALE
            row.append(tuple(v // n for v in acc))
        out.append(row)
    return out


def write_png(path, pixels):
    raw = bytearray()
    for row in pixels:
        raw.append(0)
        for r, g, b, a in row:
            raw.extend([r, g, b, a])
    def chunk(name, data):
        return (
            struct.pack(">I", len(data))
            + name
            + data
            + struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
        )
    data = b"".join([
        b"\x89PNG\r\n\x1a\n",
        chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0)),
        chunk(b"IDAT", zlib.compress(bytes(raw), 9)),
        chunk(b"IEND", b""),
    ])
    path.write_bytes(data)


def base(title_color):
    img = make_canvas()
    bg2 = mix((246, 249, 250), title_color, 0.09)
    for y in range(H * SCALE):
        t = y / (H * SCALE)
        color = mix((246, 249, 250), bg2, t)
        for x in range(W * SCALE):
            img[y][x] = (*color, 255)
    rect(img, 0, 0, W, 18, (*title_color, 255))
    circle(img, 480, 310, 220, (*mix((255, 255, 255), title_color, 0.07), 255))
    return img


def person(img, x, y, c=(24, 36, 52, 255), pose="run"):
    circle(img, x, y - 86, 30, c)
    if pose == "jump":
        line(img, x, y - 54, x + 42, y + 20, 34, c)
        line(img, x + 14, y - 32, x + 82, y - 78, 22, c)
        line(img, x + 28, y + 8, x + 96, y + 68, 24, c)
        line(img, x + 18, y + 10, x - 50, y + 72, 24, c)
        line(img, x - 4, y - 28, x - 76, y - 4, 20, c)
    else:
        line(img, x, y - 54, x + 34, y + 28, 34, c)
        line(img, x + 6, y - 30, x + 78, y - 56, 22, c)
        line(img, x + 22, y + 14, x + 92, y + 74, 24, c)
        line(img, x + 20, y + 18, x - 40, y + 90, 24, c)
        line(img, x - 4, y - 30, x - 72, y - 4, 20, c)


def equipment_ball(img, x, y, r, c):
    circle(img, x, y, r, c)
    line(img, x - r * 0.7, y, x + r * 0.7, y, 5, (246, 249, 250, 255))
    line(img, x, y - r * 0.7, x, y + r * 0.7, 5, (246, 249, 250, 255))


def draw_baseball(img):
    navy, accent = (20, 35, 54, 255), (190, 54, 46, 255)
    line(img, 360, 410, 650, 166, 34, navy)
    line(img, 632, 154, 702, 94, 16, accent)
    equipment_ball(img, 318, 198, 72, accent)
    line(img, 278, 170, 358, 226, 7, (246, 249, 250, 255))
    line(img, 278, 226, 358, 170, 7, (246, 249, 250, 255))


def draw_soccer(img):
    navy, accent = (17, 48, 67, 255), (22, 126, 93, 255)
    equipment_ball(img, 418, 312, 142, navy)
    polygon(img, [(418, 206), (486, 258), (460, 342), (376, 342), (350, 258)], accent)
    line(img, 266, 312, 570, 312, 9, (246, 249, 250, 255))
    line(img, 418, 160, 418, 464, 9, (246, 249, 250, 255))
    rect(img, 638, 218, 770, 404, navy)
    rect(img, 662, 242, 770, 404, (246, 249, 250, 255))


def draw_tennis(img):
    navy, accent = (31, 43, 58, 255), (190, 123, 37, 255)
    ellipse(img, 390, 278, 116, 156, navy, -0.68)
    ellipse(img, 390, 278, 88, 126, (246, 249, 250, 255), -0.68)
    for offset in (-44, -18, 8, 34):
        line(img, 318 + offset, 186, 454 + offset, 370, 5, accent)
    line(img, 446, 396, 590, 514, 26, navy)
    equipment_ball(img, 666, 184, 46, accent)


def draw_basketball(img):
    navy, accent = (26, 39, 54, 255), (198, 84, 39, 255)
    equipment_ball(img, 398, 310, 148, accent)
    line(img, 256, 310, 540, 310, 8, (246, 249, 250, 255))
    line(img, 398, 168, 398, 452, 8, (246, 249, 250, 255))
    line(img, 648, 266, 778, 266, 18, navy)
    rect(img, 748, 140, 778, 406, navy)
    ellipse(img, 646, 304, 92, 28, accent, 0)


def draw_volleyball(img):
    navy, accent = (27, 48, 71, 255), (49, 91, 154, 255)
    equipment_ball(img, 374, 246, 128, accent)
    line(img, 292, 182, 456, 310, 7, (246, 249, 250, 255))
    line(img, 300, 312, 452, 182, 7, (246, 249, 250, 255))
    line(img, 580, 200, 804, 200, 14, navy)
    line(img, 580, 150, 580, 462, 10, navy)
    line(img, 804, 150, 804, 462, 10, navy)
    line(img, 580, 276, 804, 276, 8, navy)
    line(img, 580, 352, 804, 352, 8, navy)


def draw_badminton(img):
    navy, accent = (30, 42, 58, 255), (108, 74, 162, 255)
    ellipse(img, 392, 240, 86, 126, navy, -0.55)
    ellipse(img, 392, 240, 64, 102, (246, 249, 250, 255), -0.55)
    line(img, 440, 346, 594, 494, 24, navy)
    polygon(img, [(636, 170), (782, 132), (742, 338)], accent)
    line(img, 636, 170, 742, 338, 8, (246, 249, 250, 255))
    line(img, 684, 158, 742, 338, 8, (246, 249, 250, 255))
    line(img, 732, 146, 742, 338, 8, (246, 249, 250, 255))


def draw_futsal(img):
    navy, accent = (21, 49, 60, 255), (45, 128, 107, 255)
    rect(img, 228, 198, 458, 420, navy)
    rect(img, 264, 234, 458, 420, (246, 249, 250, 255))
    line(img, 248, 496, 458, 198, 9, accent)
    equipment_ball(img, 638, 366, 102, accent)
    polygon(img, [(638, 292), (690, 328), (670, 394), (606, 394), (586, 328)], (246, 249, 250, 255))


def draw_rugby(img):
    navy, accent = (38, 43, 45, 255), (122, 75, 43, 255)
    ellipse(img, 472, 304, 232, 122, accent, -0.18)
    line(img, 320, 304, 624, 304, 10, (246, 249, 250, 255))
    line(img, 398, 242, 398, 366, 7, (246, 249, 250, 255))
    line(img, 472, 232, 472, 376, 7, (246, 249, 250, 255))
    line(img, 546, 242, 546, 366, 7, (246, 249, 250, 255))
    line(img, 732, 162, 732, 452, 12, navy)
    line(img, 656, 162, 808, 162, 12, navy)


def draw_other(img):
    navy, accent = (33, 44, 62, 255), (66, 82, 107, 255)
    equipment_ball(img, 330, 238, 84, accent)
    line(img, 480, 454, 650, 274, 26, navy)
    ellipse(img, 674, 246, 74, 98, navy, 0.62)
    rect(img, 280, 388, 522, 452, navy)
    line(img, 326, 388, 326, 452, 8, (246, 249, 250, 255))
    line(img, 404, 388, 404, 452, 8, (246, 249, 250, 255))
    line(img, 482, 388, 482, 452, 8, (246, 249, 250, 255))


SPORTS = {
    "baseball.png": ((31, 111, 139), draw_baseball),
    "soccer.png": ((15, 122, 98), draw_soccer),
    "tennis.png": ((178, 96, 29), draw_tennis),
    "basketball.png": ((154, 59, 36), draw_basketball),
    "volleyball.png": ((49, 91, 154), draw_volleyball),
    "badminton.png": ((109, 74, 162), draw_badminton),
    "futsal.png": ((45, 128, 107), draw_futsal),
    "rugby.png": ((122, 75, 43), draw_rugby),
    "other.png": ((66, 82, 107), draw_other),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for filename, (tone, draw) in SPORTS.items():
        img = base(tone)
        draw(img)
        pixels = downsample(img)
        write_png(OUT / filename, pixels)
        print(f"wrote {OUT / filename}")


if __name__ == "__main__":
    main()

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
    dark = mix((8, 17, 31), title_color, 0.22)
    img = make_canvas(dark)
    glow = mix((255, 255, 255), title_color, 0.22)
    for y in range(H * SCALE):
        ty = y / (H * SCALE)
        for x in range(W * SCALE):
            tx = x / (W * SCALE)
            color = mix(dark, title_color, min(0.55, tx * 0.45 + ty * 0.18))
            img[y][x] = (*color, 255)
    circle(img, 750, 170, 230, (*mix(glow, title_color, 0.38), 255))
    circle(img, 820, 500, 180, (*mix(dark, (255, 255, 255), 0.08), 255))
    line(img, 46, 520, 910, 520, 4, (255, 255, 255, 64))
    line(img, 92, 84, 880, 84, 2, (255, 255, 255, 46))
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
    line(img, x - r * 0.72, y, x + r * 0.72, y, 7, (255, 255, 255, 230))
    line(img, x, y - r * 0.72, x, y + r * 0.72, 7, (255, 255, 255, 230))


def draw_baseball(img):
    white, accent, deep = (255, 255, 255, 255), (231, 68, 57, 255), (13, 29, 48, 255)
    line(img, 470, 472, 780, 158, 56, white)
    line(img, 760, 140, 840, 60, 26, accent)
    equipment_ball(img, 280, 240, 120, accent)
    line(img, 214, 198, 346, 286, 10, white)
    line(img, 214, 286, 346, 198, 10, white)
    line(img, 160, 456, 420, 456, 6, (255, 255, 255, 90))
    polygon(img, [(650, 520), (878, 520), (878, 590), (584, 590)], deep)


def draw_soccer(img):
    white, accent, deep = (255, 255, 255, 255), (34, 177, 128, 255), (11, 35, 55, 255)
    equipment_ball(img, 342, 330, 158, white)
    polygon(img, [(342, 212), (416, 270), (388, 360), (296, 360), (268, 270)], deep)
    line(img, 174, 330, 510, 330, 10, accent)
    line(img, 342, 162, 342, 498, 10, accent)
    rect(img, 626, 212, 810, 430, white)
    rect(img, 658, 244, 810, 430, deep)
    line(img, 626, 212, 810, 430, 4, (255, 255, 255, 80))


def draw_tennis(img):
    white, accent = (255, 255, 255, 255), (235, 174, 58, 255)
    ellipse(img, 360, 288, 138, 188, white, -0.7)
    ellipse(img, 360, 288, 104, 150, (15, 24, 40, 255), -0.7)
    for offset in (-54, -24, 6, 36, 66):
        line(img, 276 + offset, 168, 470 + offset, 410, 6, accent)
    line(img, 448, 420, 656, 580, 34, white)
    equipment_ball(img, 700, 180, 62, accent)


def draw_basketball(img):
    white, accent, deep = (255, 255, 255, 255), (229, 91, 45, 255), (15, 24, 40, 255)
    equipment_ball(img, 350, 320, 178, accent)
    line(img, 182, 320, 520, 320, 10, white)
    line(img, 350, 152, 350, 488, 10, white)
    ellipse(img, 350, 320, 68, 178, (255, 255, 255, 190), 0)
    ellipse(img, 350, 320, 178, 68, (255, 255, 255, 190), 0)
    line(img, 632, 250, 820, 250, 26, white)
    rect(img, 780, 118, 820, 448, white)
    ellipse(img, 620, 308, 128, 38, accent, 0)
    rect(img, 820, 118, 900, 448, deep)


def draw_volleyball(img):
    white, accent = (255, 255, 255, 255), (78, 116, 204, 255)
    equipment_ball(img, 344, 258, 148, white)
    line(img, 240, 186, 448, 330, 9, accent)
    line(img, 254, 342, 446, 182, 9, accent)
    line(img, 574, 172, 836, 172, 18, white)
    line(img, 574, 124, 574, 492, 12, white)
    line(img, 836, 124, 836, 492, 12, white)
    for y in (250, 326, 402):
        line(img, 574, y, 836, y, 8, (255, 255, 255, 170))


def draw_badminton(img):
    white, accent = (255, 255, 255, 255), (146, 103, 220, 255)
    ellipse(img, 344, 238, 104, 150, white, -0.55)
    ellipse(img, 344, 238, 78, 120, (16, 24, 42, 255), -0.55)
    line(img, 402, 366, 620, 572, 30, white)
    polygon(img, [(610, 154), (824, 96), (764, 386)], accent)
    for x in (610, 668, 726, 784):
        line(img, x, 154 - (x - 610) * 0.27, 764, 386, 8, white)


def draw_futsal(img):
    white, accent, deep = (255, 255, 255, 255), (60, 174, 142, 255), (10, 36, 52, 255)
    rect(img, 214, 178, 500, 450, white)
    rect(img, 254, 218, 500, 450, deep)
    line(img, 230, 536, 500, 178, 10, accent)
    equipment_ball(img, 658, 366, 130, accent)
    polygon(img, [(658, 268), (724, 316), (696, 404), (620, 404), (592, 316)], white)


def draw_rugby(img):
    white, accent = (255, 255, 255, 255), (154, 100, 55, 255)
    ellipse(img, 432, 310, 270, 136, accent, -0.18)
    line(img, 250, 310, 614, 310, 12, white)
    for x in (344, 432, 520):
        line(img, x, 232, x, 388, 8, white)
    line(img, 760, 132, 760, 498, 16, white)
    line(img, 666, 132, 854, 132, 16, white)


def draw_other(img):
    white, accent = (255, 255, 255, 255), (90, 110, 144, 255)
    equipment_ball(img, 284, 224, 104, accent)
    line(img, 476, 478, 672, 280, 34, white)
    ellipse(img, 706, 246, 88, 118, white, 0.62)
    rect(img, 250, 410, 566, 486, white)
    for x in (318, 414, 510):
        line(img, x, 410, x, 486, 10, (18, 29, 48, 255))


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

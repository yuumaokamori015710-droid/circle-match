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
    bg2 = mix((246, 249, 250), title_color, 0.12)
    for y in range(H * SCALE):
        t = y / (H * SCALE)
        color = mix((246, 249, 250), bg2, t)
        for x in range(W * SCALE):
            img[y][x] = (*color, 255)
    rect(img, 0, 0, W, 52, (*title_color, 255))
    line(img, 84, 526, 876, 526, 14, (28, 47, 68, 255))
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
    person(img, 386, 370, navy)
    line(img, 458, 286, 660, 168, 20, accent)
    equipment_ball(img, 722, 146, 34, accent)
    line(img, 250, 512, 760, 512, 7, accent)


def draw_soccer(img):
    navy, accent = (17, 48, 67, 255), (22, 126, 93, 255)
    person(img, 390, 380, navy)
    equipment_ball(img, 682, 430, 58, accent)
    polygon(img, [(610, 430), (662, 394), (724, 412), (724, 472), (664, 490)], (246, 249, 250, 255))


def draw_tennis(img):
    navy, accent = (31, 43, 58, 255), (190, 123, 37, 255)
    person(img, 416, 378, navy, "jump")
    ellipse(img, 650, 202, 58, 92, accent, -0.7)
    ellipse(img, 650, 202, 44, 76, (246, 249, 250, 255), -0.7)
    line(img, 612, 270, 522, 352, 17, accent)
    equipment_ball(img, 742, 176, 26, accent)


def draw_basketball(img):
    navy, accent = (26, 39, 54, 255), (198, 84, 39, 255)
    person(img, 414, 390, navy, "jump")
    equipment_ball(img, 674, 176, 64, accent)
    line(img, 738, 260, 822, 260, 16, navy)
    rect(img, 798, 160, 822, 354, navy)


def draw_volleyball(img):
    navy, accent = (27, 48, 71, 255), (49, 91, 154, 255)
    person(img, 392, 380, navy, "jump")
    equipment_ball(img, 690, 156, 56, accent)
    line(img, 612, 320, 826, 320, 12, navy)
    line(img, 612, 254, 612, 442, 8, navy)
    line(img, 826, 254, 826, 442, 8, navy)


def draw_badminton(img):
    navy, accent = (30, 42, 58, 255), (108, 74, 162, 255)
    person(img, 410, 380, navy)
    ellipse(img, 648, 194, 50, 72, accent, -0.55)
    ellipse(img, 648, 194, 38, 58, (246, 249, 250, 255), -0.55)
    line(img, 610, 254, 522, 336, 14, accent)
    polygon(img, [(742, 160), (804, 144), (782, 220)], accent)
    line(img, 742, 160, 782, 220, 6, (246, 249, 250, 255))


def draw_futsal(img):
    navy, accent = (21, 49, 60, 255), (45, 128, 107, 255)
    person(img, 386, 382, navy)
    equipment_ball(img, 646, 438, 48, accent)
    rect(img, 700, 296, 842, 444, navy)
    rect(img, 726, 322, 842, 444, (246, 249, 250, 255))
    line(img, 716, 522, 842, 296, 8, accent)


def draw_rugby(img):
    navy, accent = (38, 43, 45, 255), (122, 75, 43, 255)
    person(img, 398, 388, navy)
    ellipse(img, 660, 286, 104, 58, accent, -0.18)
    line(img, 592, 286, 728, 286, 8, (246, 249, 250, 255))
    line(img, 626, 250, 626, 322, 5, (246, 249, 250, 255))
    line(img, 694, 250, 694, 322, 5, (246, 249, 250, 255))


def draw_other(img):
    navy, accent = (33, 44, 62, 255), (66, 82, 107, 255)
    person(img, 364, 382, navy, "jump")
    equipment_ball(img, 660, 208, 46, accent)
    line(img, 622, 374, 760, 236, 18, accent)
    ellipse(img, 782, 214, 54, 74, accent, 0.6)
    rect(img, 610, 430, 788, 476, navy)
    line(img, 642, 430, 642, 476, 8, (246, 249, 250, 255))
    line(img, 702, 430, 702, 476, 8, (246, 249, 250, 255))


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

#!/usr/bin/env python3
"""Draw all of The Big Giant Robot's art in code.

Writes src/art.c and src/art.h (generated, do not edit) and previews in art/*.png.
Usage: python3 tools/make_art.py
"""
import math
import os
import random
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(ROOT, "art")
SRC = os.path.join(ROOT, "src")


# ---------------------------------------------------------------- colors

def H(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))


def g15(c):
    r, g, b = c
    return (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)


def mix(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def mul(c, f):
    return tuple(max(0, min(255, int(round(v * f)))) for v in c)


def ramp4(base):
    """dark, mid, light, highlight from one base color."""
    return [mul(base, 0.42), mul(base, 0.72), base, mix(base, (255, 255, 255), 0.45)]


# ---------------------------------------------------------------- canvas

class Canvas:
    def __init__(s, w, h, fill=0):
        s.w, s.h = w, h
        s.p = [[fill] * w for _ in range(h)]

    def px(s, x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < s.w and 0 <= y < s.h:
            s.p[y][x] = c

    def get(s, x, y):
        if 0 <= x < s.w and 0 <= y < s.h:
            return s.p[y][x]
        return 0

    def rect(s, x0, y0, x1, y1, c):
        for y in range(max(0, int(round(y0))), min(s.h - 1, int(round(y1))) + 1):
            row = s.p[y]
            for x in range(max(0, int(round(x0))), min(s.w - 1, int(round(x1))) + 1):
                row[x] = c

    def ellipse(s, cx, cy, rx, ry, c):
        ax, ay = (rx + 0.5) ** 2, (ry + 0.5) ** 2
        for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if (x - cx) ** 2 / ax + (y - cy) ** 2 / ay <= 1.0:
                    s.px(x, y, c)

    def capsule(s, x0, y0, x1, y1, r, c):
        dx, dy = x1 - x0, y1 - y0
        ll = dx * dx + dy * dy or 1e-9
        for y in range(int(min(y0, y1) - r) - 1, int(max(y0, y1) + r) + 2):
            for x in range(int(min(x0, x1) - r) - 1, int(max(x0, x1) + r) + 2):
                t = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / ll))
                px, py = x0 + dx * t, y0 + dy * t
                if (x - px) ** 2 + (y - py) ** 2 <= (r + 0.3) ** 2:
                    s.px(x, y, c)

    def poly(s, pts, c):
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)) - 1, int(max(ys)) + 2):
            yc = y + 0.5
            xs = []
            n = len(pts)
            for i in range(n):
                (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
                if (ya <= yc < yb) or (yb <= yc < ya):
                    xs.append(xa + (yc - ya) * (xb - xa) / (yb - ya))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(math.ceil(xs[i] - 0.5)), int(math.floor(xs[i + 1] - 0.5)) + 1):
                    s.px(x, y, c)

    def line(s, x0, y0, x1, y1, c, w=1):
        n = int(max(abs(x1 - x0), abs(y1 - y0)) * 2) + 1
        for i in range(n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            if w == 1:
                s.px(x, y, c)
            else:
                for oy in range(w):
                    for ox in range(w):
                        s.px(x + ox - w // 2, y + oy - w // 2, c)

    def outline(s, oc, diag=False):
        add = []
        for y in range(s.h):
            for x in range(s.w):
                if s.p[y][x]:
                    continue
                nb = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                if diag:
                    nb += [(1, 1), (-1, 1), (1, -1), (-1, -1)]
                for ox, oy in nb:
                    v = s.get(x + ox, y + oy)
                    if v and v != oc:
                        add.append((x, y))
                        break
        for x, y in add:
            s.p[y][x] = oc

    def paste(s, o, dx=0, dy=0):
        for y in range(o.h):
            for x in range(o.w):
                v = o.p[y][x]
                if v:
                    s.px(x + dx, y + dy, v)

    def hflip(s):
        c = Canvas(s.w, s.h)
        for y in range(s.h):
            c.p[y] = s.p[y][::-1]
        return c

    def crop(s, x0, y0, w, h):
        c = Canvas(w, h)
        for y in range(h):
            for x in range(w):
                c.p[y][x] = s.get(x0 + x, y0 + y)
        return c


def shade(mask, ramp, oc=1):
    """Turn a one-color mask into a lit part: light top/left edge, dark bottom/right, outline."""
    d, m, l, hi = ramp
    out = Canvas(mask.w, mask.h)
    g = mask.get
    for y in range(mask.h):
        for x in range(mask.w):
            if not mask.p[y][x]:
                continue
            c = m
            if not g(x + 1, y) or not g(x, y + 1) or not g(x, y + 2):
                c = d
            up, lf = g(x, y - 1), g(x - 1, y)
            if not up or not lf:
                c = l
            if not up and not lf:
                c = hi
            if up and lf and not g(x, y - 2) and g(x + 1, y):
                c = l if c == m else c
            out.p[y][x] = c
    if oc:
        out.outline(oc)
    return out


def part(cv, ramp, fn, oc=1):
    m = Canvas(cv.w, cv.h)
    fn(m)
    cv.paste(shade(m, ramp, oc))


def ik(s, t, a, b, bend):
    dx, dy = t[0] - s[0], t[1] - s[1]
    d = math.hypot(dx, dy)
    d = max(abs(a - b) + 0.01, min(a + b - 0.01, d))
    ang = math.atan2(dy, dx)
    cs = (a * a + d * d - b * b) / (2 * a * d)
    off = math.acos(max(-1.0, min(1.0, cs)))
    ea = ang + bend * off
    e = (s[0] + a * math.cos(ea), s[1] + a * math.sin(ea))
    ux, uy = t[0] - e[0], t[1] - e[1]
    ul = math.hypot(ux, uy) or 1
    end = (e[0] + ux / ul * b, e[1] + uy / ul * b)
    return e, end


# ---------------------------------------------------------------- tile export

def tiles4(cv, tw=None):
    """Canvas -> list of 8x8 tiles (each a list of 64 indices), row-major over the canvas."""
    out = []
    for ty in range(cv.h // 8):
        for tx in range(cv.w // 8):
            t = []
            for y in range(8):
                t.extend(cv.p[ty * 8 + y][tx * 8:(tx + 1) * 8])
            out.append(t)
    return out


def meta_tiles(cv):
    """Canvas made of 32x32 pieces -> tiles piece by piece (each piece is a 1D-mapped 32x32 sprite)."""
    out = []
    for py in range(cv.h // 32):
        for pxx in range(cv.w // 32):
            out.extend(tiles4(cv.crop(pxx * 32, py * 32, 32, 32)))
    return out


def pack4(tile):
    words = []
    for y in range(8):
        v = 0
        for x in range(8):
            v |= (tile[y * 8 + x] & 15) << (4 * x)
        words.append(v)
    return words


def pack8(tile):
    words = []
    for i in range(0, 64, 4):
        words.append(tile[i] | (tile[i + 1] << 8) | (tile[i + 2] << 16) | (tile[i + 3] << 24))
    return words


def tflip(t, h, v):
    rows = [t[y * 8:(y + 1) * 8] for y in range(8)]
    if h:
        rows = [r[::-1] for r in rows]
    if v:
        rows = rows[::-1]
    return tuple(x for r in rows for x in r)


class TileSet:
    """Deduplicated BG tiles (with flips). Index 0 is the empty tile."""

    def __init__(s, start=0):
        s.tiles = [tuple([0] * 64)]
        s.lookup = {s.tiles[0]: (0, 0, 0)}

    def add(s, t):
        t = tuple(t)
        if t in s.lookup:
            return s.lookup[t]
        idx = len(s.tiles)
        s.tiles.append(t)
        for h in (0, 1):
            for v in (0, 1):
                k = tflip(t, h, v)
                if k not in s.lookup:
                    s.lookup[k] = (idx, h, v)
        return (idx, 0, 0)

    def map_canvas(s, cv, pal, mw=None):
        """Return map entries (row-major over cv in tiles)."""
        ents = []
        for ty in range(cv.h // 8):
            for tx in range(cv.w // 8):
                t = []
                for y in range(8):
                    t.extend(cv.p[ty * 8 + y][tx * 8:(tx + 1) * 8])
                i, h, v = s.add(t)
                ents.append(i | (h << 10) | (v << 11) | (pal << 12))
        return ents


# ---------------------------------------------------------------- output collection

C_OUT = []
H_OUT = []


def emit_u32(name, words):
    lines = []
    for i in range(0, len(words), 8):
        lines.append(", ".join("0x%08X" % w for w in words[i:i + 8]))
    C_OUT.append("const u32 %s[%d] = {\n%s\n};\n" % (name, len(words), ",\n".join(lines)))
    H_OUT.append("extern const u32 %s[%d];" % (name, len(words)))


def emit_u16(name, vals):
    lines = []
    for i in range(0, len(vals), 16):
        lines.append(", ".join("0x%04X" % (v & 0xFFFF) for v in vals[i:i + 16]))
    C_OUT.append("const u16 %s[%d] = {\n%s\n};\n" % (name, len(vals), ",\n".join(lines)))
    H_OUT.append("extern const u16 %s[%d];" % (name, len(vals)))


def emit_s8(name, vals):
    C_OUT.append("const s8 %s[%d] = { %s };\n" % (name, len(vals), ", ".join(str(int(v)) for v in vals)))
    H_OUT.append("extern const s8 %s[%d];" % (name, len(vals)))


def emit_pal(name, cols):
    cols = list(cols) + [(0, 0, 0)] * (16 - len(cols))
    emit_u16(name, [g15(c) for c in cols])


def define(name, val):
    H_OUT.append("#define %s %s" % (name, val))


def preview(name, cv, pal, scale=3):
    img = Image.new("RGB", (cv.w, cv.h))
    bg = (40, 0, 40)
    data = []
    for y in range(cv.h):
        for x in range(cv.w):
            v = cv.p[y][x]
            data.append(pal[v] if v else bg)
    img.putdata(data)
    img = img.resize((cv.w * scale, cv.h * scale), Image.NEAREST)
    img.save(os.path.join(ART, name))


# ---------------------------------------------------------------- the robot

ROBOT_PAL = [(0, 0, 0), H("#0e1216"), H("#353d46"), H("#545e69"), H("#7a8692"), H("#a3adb8"),
             H("#d4dae0"), H("#060608"), H("#4a5a72"), H("#b01818"), H("#ff5a40"), H("#2a6aff"),
             H("#b0e0ff"), H("#b02424"), H("#5e1010"), H("#e8b020")]
FRONT = (3, 4, 5, 6)
BACK = (2, 2, 3, 4)
DARK = (2, 2, 3, 3)


def r_leg(cv, hip, ankle, ramp):
    knee, end = ik(hip, ankle, 17, 17, -1)
    part(cv, ramp, lambda m: m.capsule(hip[0], hip[1], knee[0], knee[1], 6.5, 1))
    part(cv, ramp, lambda m: m.capsule(knee[0], knee[1], end[0], end[1], 5.5, 1))
    part(cv, ramp, lambda m: m.ellipse(knee[0] + 1, knee[1], 3.5, 3.5, 1))
    ax, ay = end

    def foot(m):
        m.poly([(ax - 7, ay - 2), (ax + 5, ay - 3), (ax + 12, ay + 2), (ax + 12, ay + 7),
                (ax - 8, ay + 7), (ax - 8, ay)], 1)
    part(cv, ramp, foot)
    cv.rect(ax - 6, ay + 5, ax + 10, ay + 5, ramp[0])


def r_arm(cv, sh, hand, ramp, palm):
    elbow, end = ik(sh, hand, 13, 14, 1)
    part(cv, ramp, lambda m: m.capsule(sh[0], sh[1], elbow[0], elbow[1], 4.5, 1))
    part(cv, ramp, lambda m: m.capsule(elbow[0], elbow[1], end[0], end[1], 5.5, 1))
    hx, hy = end
    ux, uy = end[0] - elbow[0], end[1] - elbow[1]
    ul = math.hypot(ux, uy) or 1
    ux, uy = ux / ul, uy / ul
    if palm:
        part(cv, ramp, lambda m: m.ellipse(hx, hy, 5, 5, 1))
        cv.ellipse(hx + ux * 3, hy + uy * 3, 2.6, 2.6, 11)
        cv.ellipse(hx + ux * 3.5, hy + uy * 3.5, 1.2, 1.2, 12)
    else:
        part(cv, ramp, lambda m: m.poly([(hx - 5, hy - 3), (hx - 3, hy - 5), (hx + 3, hy - 5), (hx + 5, hy - 3),
                                        (hx + 5, hy + 4), (hx + 3, hy + 6), (hx - 3, hy + 6), (hx - 5, hy + 4)], 1))
        cv.px(hx + ux * 4, hy + uy * 4, 11)
        cv.px(hx + ux * 4 + 1, hy + uy * 4, 12)
    return end


def r_torso(cv, ln, dy):
    """Chest twists with the walk: the V plate slides further than the shoulders and the belly turns the
    other way, so the chest piece visibly moves each step."""
    o = lambda pts: [(x + ln, y + dy) for x, y in pts]
    tw = ln * 0.9                       # extra twist of the chest plate
    part(cv, DARK, lambda m: m.rect(27 + ln, 23 + dy, 35 + ln, 31 + dy, 1))
    part(cv, (2, 3, 4, 5), lambda m: m.rect(20 + ln * 0.3, 53 + dy, 42 + ln * 0.3, 62 + dy, 1))
    part(cv, (2, 3, 4, 4), lambda m: m.rect(23 - tw * 0.4, 48 + dy, 39 - tw * 0.4, 57 + dy, 1))
    part(cv, BACK, lambda m: m.ellipse(21 + ln, 32 + dy, 7, 6, 1))
    part(cv, FRONT, lambda m: m.poly(o([(15, 28), (47, 28), (50, 35), (45, 50), (38, 55), (24, 55),
                                         (17, 50), (12, 35)]), 1))
    # raised chest plate behind the V (turns with the twist)
    c = 31 + ln + tw
    lx, rx = 19 + ln + tw * 0.4, 43 + ln + tw * 1.3
    tip = 45 + dy - abs(tw) * 0.4
    part(cv, (3, 4, 5, 6), lambda m: m.poly([(lx, 30 + dy), (rx, 30 + dy), (rx - 2, 36 + dy), (c + 1, tip + 4),
                                            (c - 1, tip + 4), (lx + 2, 36 + dy)], 1), oc=2)
    # the angry red V
    cv.line(lx + 1, 33 + dy, c, tip, 14, 2)
    cv.line(rx - 1, 33 + dy, c, tip, 14, 2)
    cv.line(lx + 1, 32 + dy, c, tip - 1, 13, 2)
    cv.line(rx - 1, 32 + dy, c, tip - 1, 13, 2)
    cv.px(c, tip - 3, 6)
    for bx in (lx - 2, rx + 2):
        cv.px(bx, 33 + dy, 6)
        cv.px(bx, 34 + dy, 2)
    for vy in (48, 50):
        cv.rect(26 + ln + tw * 0.5, vy + dy, 36 + ln + tw * 0.5, vy + dy, 2)
    for ry in (51, 54):
        cv.rect(24 - tw * 0.4, ry + dy, 38 - tw * 0.4, ry + dy, 2)
    cv.rect(21 + ln * 0.3, 58 + dy, 41 + ln * 0.3, 58 + dy, 1)
    cv.px(31 + ln * 0.3, 60 + dy, 15)


def r_head(cv, hx, hy, eyes):
    """3/4 view looking right: the face sits toward the front, the side of the head shows at the back."""
    o = lambda pts: [(x + hx, y + hy) for x, y in pts]
    part(cv, FRONT, lambda m: m.poly(o([(25, 8), (28, 0), (30, 0), (33, 8)]), 1))
    part(cv, (2, 3, 4, 5), lambda m: m.ellipse(18 + hx, 15 + hy, 3, 3.5, 1))
    part(cv, FRONT, lambda m: m.poly(o([(20, 6), (42, 6), (45, 9), (45, 22), (42, 27), (22, 27),
                                         (18, 22), (18, 8)]), 1))
    # side of the head (back), darker, with a seam
    cv.poly(o([(19, 9), (24, 7), (24, 25), (20, 22)]), 3)
    cv.line(24 + hx, 7 + hy, 24 + hx, 26 + hy, 2)
    cv.px(21 + hx, 12 + hy, 5)
    # recessed face plate, toward the front
    cv.rect(26 + hx, 11 + hy, 43 + hx, 19 + hy, 3)
    cv.rect(26 + hx, 19 + hy, 43 + hx, 19 + hy, 2)
    # eyes: far eye small, near eye big, both slanted angry
    ec, ecore = (9, 10) if eyes == "on" else (2, 2)
    cv.line(27 + hx, 14 + hy, 31 + hx, 16 + hy, ec, 2)
    cv.line(42 + hx, 14 + hy, 36 + hx, 16 + hy, ec, 2)
    cv.px(29 + hx, 15 + hy, ecore)
    cv.px(39 + hx, 15 + hy, ecore)
    # heavy brows slanting down to the middle
    cv.poly(o([(25, 9), (32, 12), (32, 14.5), (25, 11.5)]), 1)
    cv.poly(o([(34, 12), (44, 8), (44, 11), (34, 14.5)]), 1)
    cv.line(26 + hx, 9.5 + hy, 31 + hx, 12 + hy, 13)
    cv.line(35 + hx, 12 + hy, 43 + hx, 8.5 + hy, 13)
    # frowning mouth grill, toward the front
    cv.poly(o([(28, 26), (30, 22), (41, 22), (43, 26)]), 1)
    for tx in (31, 34, 37, 40):
        cv.rect(tx + hx, 23 + hy, tx + hx, 24 + hy, 3)
    cv.rect(30 + hx, 21 + hy, 41 + hx, 21 + hy, 5)


ROBOT_POSES = [
    # name, dy, lean, front ankle, back ankle, front hand, back hand, palm, head dy, eyes
    ("stand", 0, 0, (37, 89), (25, 89), (36, 58), (19, 57), 0, 0, "on"),
    ("walk1", 2, 4, (49, 89), (13, 89), (10, 50), (38, 57), 0, 0, "on"),
    ("walk2", 0, 1, (35, 89), (31, 77), (33, 59), (22, 58), 0, 0, "on"),
    ("walk3", 2, -3, (16, 89), (46, 89), (49, 54), (2, 50), 0, 0, "on"),
    ("walk4", 0, 0, (37, 77), (27, 89), (38, 59), (17, 58), 0, 0, "on"),
    ("shoot", 0, 1, (37, 89), (25, 89), (57, 44), (53, 41), 1, 0, "on"),
    ("shoot1", 2, 4, (49, 89), (13, 89), (57, 46), (53, 43), 1, 0, "on"),
    ("shoot2", 0, 2, (35, 89), (31, 77), (57, 44), (53, 41), 1, 0, "on"),
    ("shoot3", 2, -2, (16, 89), (46, 89), (57, 46), (53, 43), 1, 0, "on"),
    ("shoot4", 0, 1, (37, 77), (27, 89), (57, 44), (53, 41), 1, 0, "on"),
    ("stomp_up", -1, 0, (45, 70), (24, 89), (52, 42), (8, 46), 0, 0, "on"),
    ("stomp_dn", 3, 2, (47, 89), (21, 89), (50, 56), (13, 56), 0, 0, "on"),
    ("crouch", 9, -1, (41, 89), (21, 89), (19, 64), (10, 62), 0, 0, "on"),
    ("jump", -2, 0, (40, 79), (24, 82), (44, 9), (26, 9), 0, 0, "on"),
    ("land", 11, 3, (46, 89), (17, 89), (52, 90), (40, 91), 0, 1, "on"),
    ("clap_open", 0, 0, (40, 89), (21, 89), (58, 27), (4, 27), 0, 0, "on"),
    ("clap_shut", 1, 1, (40, 89), (21, 89), (46, 26), (43, 27), 0, 0, "on"),
    ("hurt", 1, -3, (39, 89), (23, 89), (53, 40), (8, 42), 0, -1, "on"),
    ("dead", 14, 4, (47, 89), (15, 89), (53, 91), (12, 90), 0, 2, "off"),
]


def robot_frame(pose):
    name, dy, ln, ff, bf, fh, bh, palm, hdy, eyes = pose
    cv = Canvas(64, 96)
    hipy = 57 + dy
    fhip, bhip = (35 + ln * 0.5, hipy), (27 + ln * 0.5, hipy)
    # shoulders follow their arm: they roll back when the arm swings back, forward when it swings forward
    roll = lambda hx, rest: max(-8, min(4, (hx - rest) * 0.4))
    fr, br = roll(fh[0], 36), roll(bh[0], 19)
    fsh = (37 + ln + fr, 32 + dy + abs(fr) * 0.2)
    bsh = (21 + ln + br, 32 + dy + abs(br) * 0.2)
    r_leg(cv, bhip, bf, BACK)
    r_arm(cv, bsh, bh, BACK, palm)
    r_torso(cv, ln, dy)
    r_head(cv, ln + 1, dy + hdy, eyes)
    r_leg(cv, fhip, ff, FRONT)
    hand = r_arm(cv, fsh, fh, FRONT, palm)
    part(cv, FRONT, lambda m: m.ellipse(fsh[0], fsh[1] - 1, 7, 6, 1))
    cv.px(fsh[0] - 2, fsh[1] - 3, 6)
    anchor = (18 + ln + 1, 13 + dy + hdy)
    eye = (38 + ln + 1, 15 + dy + hdy)
    return cv, anchor, eye, (int(round(hand[0])), int(round(hand[1])))


def glasses():
    """3/4 view: narrow far lens, wide near lens, the arm runs back to the ear."""
    cv = Canvas(32, 8)
    cv.rect(0, 1, 7, 1, 1)
    cv.rect(7, 0, 28, 1, 1)
    cv.poly([(7.5, 1), (14.5, 1), (14, 7), (8.5, 7)], 7)
    cv.poly([(16, 1), (28.5, 1), (27.5, 7), (17, 7)], 7)
    cv.outline(1)
    cv.rect(14, 1, 16, 2, 1)
    cv.line(9, 2, 10, 4, 8)
    cv.px(9, 2, 6)
    cv.line(19, 2, 21, 4, 8)
    cv.px(23, 2, 8)
    cv.px(19, 2, 6)
    return cv


def build_robot():
    frames = []
    anchors, eyes, hands = [], [], []
    for p in ROBOT_POSES:
        cv, a, e, h = robot_frame(p)
        frames.append(cv)
        anchors.append(a)
        eyes.append(e)
        hands.append(h)
    words = []
    for cv in frames:
        for t in meta_tiles(cv):
            words.extend(pack4(t))
    emit_u32("robot_tiles", words)
    emit_pal("robot_pal", ROBOT_PAL)
    for i, p in enumerate(ROBOT_POSES):
        define("RF_" + p[0].upper(), i)
    define("RF_COUNT", len(ROBOT_POSES))
    emit_s8("robot_glass_x", [a[0] for a in anchors])
    emit_s8("robot_glass_y", [a[1] for a in anchors])
    emit_s8("robot_eye_x", [e[0] for e in eyes])
    emit_s8("robot_eye_y", [e[1] for e in eyes])
    emit_s8("robot_hand_x", [h[0] for h in hands])
    emit_s8("robot_hand_y", [h[1] for h in hands])
    g = glasses()
    words = []
    for t in tiles4(g):
        words.extend(pack4(t))
    emit_u32("glasses_tiles", words)
    # preview sheet: every pose, glasses on
    sheet = Canvas(64 * 10, 96 * 2)
    for i, cv in enumerate(frames):
        x, y = (i % 10) * 64, (i // 10) * 96
        sheet.paste(cv, x, y)
        sheet.paste(g, x + anchors[i][0], y + anchors[i][1])
    preview("robot_sheet.png", sheet, ROBOT_PAL, 2)
    return frames, anchors, g


# ---------------------------------------------------------------- normal enemies (War Machine style)

ENEMY_SUITS = [("gunmetal", "#5a606c"), ("red", "#c83030"), ("gold", "#d8a428"), ("blue", "#3a66d0"),
               ("green", "#3c9c3c"), ("purple", "#8a44c0")]


def enemy_pal(suit):
    r = ramp4(H(suit))
    return [(0, 0, 0), H("#0c0e12"), r[0], r[1], r[2], r[3], H("#3a3f46"), H("#7d8590"), H("#c4cad2"),
            H("#fff4b0"), H("#ff7a18"), H("#ffe040"), H("#a8f4ff"), H("#000000")]


SUIT = (2, 3, 4, 5)
METAL = (6, 7, 8, 8)


def enemy_frame(kind):
    cv = Canvas(16, 32)
    up = 2 if kind.startswith("fly") else 0
    if kind == "squish":
        part(cv, SUIT, lambda m: m.ellipse(8, 29, 6.5, 1.8, 1))
        part(cv, METAL, lambda m: m.rect(1, 29, 4, 31, 1))
        part(cv, METAL, lambda m: m.rect(11, 29, 14, 31, 1))
        part(cv, SUIT, lambda m: m.ellipse(8, 27, 3, 1.5, 1))
        cv.px(7, 27, 9)
        cv.px(9, 27, 9)
        cv.line(12, 26, 15, 24, 7)
        return cv
    y = -up
    if kind == "walk1":
        legs = [((7, 23), (5, 29)), ((9, 23), (11, 29))]
    elif kind == "walk2":
        legs = [((7, 23), (7, 29)), ((9, 23), (9, 29))]
    elif kind.startswith("fly"):
        legs = [((7, 23), (6, 28)), ((9, 23), (8, 28))]
    else:
        legs = [((7, 23), (6, 29)), ((9, 23), (10, 29))]
    for (a, b) in legs:
        part(cv, (2, 2, 3, 4), lambda m, a=a, b=b: m.capsule(a[0], a[1] + y, b[0], b[1] + y, 1.3, 1))
    for (a, b) in legs:
        bx, by = b[0], b[1] + y
        part(cv, METAL, lambda m, bx=bx, by=by: m.rect(bx - 2, by, bx + 2, by + 2, 1))
    if kind.startswith("fly"):
        fl = 1 if kind == "fly1" else 2
        for (a, b) in legs:
            bx, by = b[0], b[1] + y + 3
            cv.rect(bx - 1, by, bx + 1, by + fl - 1 + 1, 10)
            cv.px(bx, by, 11)
            cv.px(bx, by + fl + 1, 10)
    # back arm
    part(cv, (2, 2, 3, 4), lambda m: m.capsule(4, 16 + y, 3, 21 + y, 1.3, 1))
    # torso + shoulders
    part(cv, SUIT, lambda m: m.rect(4, 15 + y, 11, 23 + y, 1))
    part(cv, SUIT, lambda m: m.ellipse(4, 15 + y, 2, 2, 1))
    cv.px(8, 18 + y, 12)
    cv.px(7, 21 + y, 2)
    cv.px(8, 21 + y, 2)
    # helmet with face plate and visor slit
    part(cv, SUIT, lambda m: m.rect(4, 7 + y, 10, 13 + y, 1))
    cv.rect(7, 9 + y, 10, 12 + y, 8)
    cv.rect(7, 10 + y, 10, 10 + y, 1)
    cv.rect(8, 10 + y, 10, 10 + y, 9)
    cv.rect(7, 12 + y, 10, 12 + y, 6)
    cv.px(5, 8 + y, 5)
    # shoulder gun (the War Machine cannon)
    part(cv, METAL, lambda m: m.rect(10, 13 + y, 15, 14 + y, 1))
    part(cv, SUIT, lambda m: m.ellipse(11, 15 + y, 2, 2, 1))
    cv.px(9, 14 + y, 6)
    if kind == "shoot":
        part(cv, (2, 3, 4, 5), lambda m: m.capsule(11, 17 + y, 14, 17 + y, 1.3, 1))
        cv.px(15, 12 + y, 11)
        cv.px(15, 13 + y, 9)
        cv.px(15, 15 + y, 10)
    else:
        part(cv, (2, 3, 4, 5), lambda m: m.capsule(12, 17 + y, 12, 21 + y, 1.3, 1))
    return cv


ENEMY_FRAMES = ["walk1", "walk2", "fly1", "fly2", "shoot", "squish"]


def build_enemies():
    words = []
    frames = []
    for k in ENEMY_FRAMES:
        cv = enemy_frame(k)
        frames.append(cv)
        for t in tiles4(cv):
            words.extend(pack4(t))
    emit_u32("enemy_tiles", words)
    for i, k in enumerate(ENEMY_FRAMES):
        define("EF_" + k.upper(), i)
    pals = []
    for i, (n, c) in enumerate(ENEMY_SUITS):
        pals.extend([g15(x) for x in enemy_pal(c)] + [0] * (16 - len(enemy_pal(c))))
    emit_u16("enemy_pals", pals)
    define("ENEMY_SUITS", len(ENEMY_SUITS))
    sheet = Canvas(16 * 6, 32 * 6)
    for j in range(6):
        for i, cv in enumerate(frames):
            sheet.paste(cv, i * 16, j * 32)
    # preview with each suit per row
    img = Image.new("RGB", (96, 192))
    for j, (n, c) in enumerate(ENEMY_SUITS):
        pal = enemy_pal(c)
        for i, cv in enumerate(frames):
            for y in range(32):
                for x in range(16):
                    v = cv.p[y][x]
                    img.putpixel((i * 16 + x, j * 32 + y), pal[v] if v else (40, 0, 40))
    img.resize((96 * 4, 192 * 4), Image.NEAREST).save(os.path.join(ART, "enemies.png"))


# ---------------------------------------------------------------- enemy variants (32x32, need a certain move)
# shield: lasers bounce off (stomp or slam it). spike: stomping hurts you (laser it). heavy: only a slam kills it.

VARIANTS = [("shield", "#3c6e9c"), ("spike", "#a8285c"), ("heavy", "#8c7428")]
VARIANT_FRAMES = ["walk1", "walk2", "alt"]


def variant_frame(kind, f):
    cv = Canvas(32, 32)
    if kind == "heavy":
        y = 0
        legs = {"walk1": [((13, 21), (9, 29)), ((18, 21), (22, 29))],
                "walk2": [((13, 21), (13, 29)), ((18, 21), (18, 29))],
                "alt": [((13, 21), (11, 29)), ((18, 21), (20, 29))]}[f]
        for (a, b) in legs:
            part(cv, (2, 2, 3, 4), lambda m, a=a, b=b: m.capsule(a[0], a[1], b[0], b[1], 2.6, 1))
        for (a, b) in legs:
            part(cv, METAL, lambda m, b=b: m.rect(b[0] - 3, b[1], b[0] + 3, b[1] + 2, 1))
        part(cv, (2, 2, 3, 4), lambda m: m.capsule(8, 13, 6, 21, 2.4, 1))       # back arm
        part(cv, SUIT, lambda m: m.rect(8, 10, 22, 22, 1))                       # big torso
        part(cv, SUIT, lambda m: m.ellipse(8, 11, 3.5, 3, 1))
        part(cv, SUIT, lambda m: m.ellipse(21, 11, 3.5, 3, 1))
        cv.rect(12, 15, 18, 16, 6)
        cv.rect(13, 15, 17, 15, 12)
        cv.rect(11, 19, 19, 19, 2)
        part(cv, SUIT, lambda m: m.rect(11, 2, 19, 10, 1))                       # helmet
        cv.rect(14, 4, 19, 8, 8)
        cv.rect(14, 6, 19, 6, 1)
        cv.rect(15, 6, 19, 6, 9)
        cv.rect(14, 8, 19, 8, 6)
        # twin shoulder cannons
        part(cv, METAL, lambda m: m.rect(16, 8, 30, 10, 1))
        part(cv, METAL, lambda m: m.rect(4, 6, 12, 8, 1))
        if f == "alt":
            cv.px(31, 8, 11); cv.px(31, 9, 9); cv.px(30, 7, 10)
        part(cv, (2, 3, 4, 5), lambda m: m.capsule(21, 14, 23, 20, 1.8, 1))     # front arm
        part(cv, METAL, lambda m: m.ellipse(23, 21, 2, 2, 1))
        return cv
    body = enemy_frame("shoot" if f == "alt" and kind == "spike" else ("walk1" if f == "walk1" else "walk2"))
    ox = 6 if kind == "shield" else 8
    cv.paste(body, ox, 0)
    if kind == "shield":
        down = f == "alt"   # dropped while stunned
        sy = 14 if down else 7
        part(cv, METAL, lambda m: m.rect(20, sy, 27, sy + 21 - (6 if down else 0), 1))
        part(cv, METAL, lambda m: m.ellipse(23.5, sy, 3.5, 2, 1))
        x0 = 21
        cv.rect(x0 + 1, sy + 3, x0 + 2, sy + 15 - (6 if down else 0), 12)
        cv.px(x0 + 4, sy + 2, 4)
        cv.px(x0 + 4, sy + 12 - (6 if down else 0), 4)
    else:
        # big spikes on the helmet, back, shoulder and knee
        tips = [((13, 8), (11, 1)), ((16, 7), (17, 0)), ((19, 8), (23, 3)),
                ((12, 16), (5, 13)), ((12, 20), (5, 22)), ((19, 15), (24, 11)), ((15, 25), (19, 27))]
        for (bb, tt) in tips:
            dx, dy = tt[0] - bb[0], tt[1] - bb[1]
            l = math.hypot(dx, dy)
            nx, ny = -dy / l * 2.2, dx / l * 2.2
            part(cv, (6, 7, 8, 8), lambda m, bb=bb, tt=tt, nx=nx, ny=ny: m.poly(
                [(bb[0] - nx, bb[1] - ny), (bb[0] + nx, bb[1] + ny), tt], 1))
    return cv


def build_variants():
    words = []
    frames = []
    for k, c in VARIANTS:
        for f in VARIANT_FRAMES:
            cv = variant_frame(k, f)
            frames.append((k, c, cv))
            for t in tiles4(cv):
                words.extend(pack4(t))
    emit_u32("variant_tiles", words)
    define("VARIANT_COUNT", len(VARIANTS))
    define("VARIANT_FRAMES", len(VARIANT_FRAMES))
    define("VARIANT_TILE_COUNT", len(words) // 8)
    pals = []
    for n, c in VARIANTS:
        pals.extend([g15(x) for x in enemy_pal(c)] + [0] * (16 - len(enemy_pal(c))))
    emit_u16("variant_pals", pals)
    img = Image.new("RGB", (32 * 3, 32 * 3))
    for i, (k, c, cv) in enumerate(frames):
        pal = enemy_pal(c)
        for y in range(32):
            for x in range(32):
                v = cv.p[y][x]
                img.putpixel(((i % 3) * 32 + x, (i // 3) * 32 + y), pal[v] if v else (40, 0, 40))
    img.resize((96 * 4, 96 * 4), Image.NEAREST).save(os.path.join(ART, "variants.png"))


# ---------------------------------------------------------------- effects (lasers, booms, pickups)

FX_PAL = [(0, 0, 0), H("#1a0a0a"), H("#8a0808"), H("#ff2a1a"), H("#ffd0c0"), H("#0a2aa0"), H("#2a7aff"),
          H("#d0f4ff"), H("#7a1408"), H("#ff7a10"), H("#ffd820"), H("#ffffff"), H("#3a3838"), H("#8a8484"),
          H("#20b040"), H("#a0ff90")]

FX = []  # (name, w, h, canvas list)


def fx_add(name, w, h, cvs):
    FX.append((name, w, h, cvs))


def bolt(angle_deg):
    cv = Canvas(16, 16)
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    x0, y0 = 8 - dx * 6, 8 - dy * 6
    x1, y1 = 8 + dx * 6, 8 + dy * 6
    cv.capsule(x0, y0, x1, y1, 2.2, 5)
    cv.capsule(x0 + dx, y0 + dy, x1, y1, 1.4, 6)
    cv.capsule(x0 + dx * 3, y0 + dy * 3, x1 - dx, y1 - dy, 0.6, 7)
    return cv


def beam_seg(v):
    """16x16 piece of the eye beam (slope 1 down per 2 across), thick and glowing."""
    cv = Canvas(16, 16)
    for x in range(16):
        yc = 6 + x / 2.0
        for y in range(16):
            d = abs(y + 0.5 - (yc + 0.25))
            if d < 1.1:
                cv.px(x, y, 4 if v == 0 else 11)
            elif d < 2.4:
                cv.px(x, y, 3)
            elif d < 3.3:
                cv.px(x, y, 2)
            elif d < 4.2 and (x + y + v) % 2 == 0:
                cv.px(x, y, 2)
    return cv


def boom(size, f, nf, seed):
    rnd = random.Random(seed)
    cv = Canvas(size, size)
    c = size / 2 - 0.5
    blobs = [(rnd.uniform(-0.35, 0.35) * size, rnd.uniform(-0.35, 0.35) * size, rnd.uniform(0.18, 0.32) * size)
             for _ in range(6)]
    t = (f + 1) / nf
    for y in range(size):
        for x in range(size):
            best = 9
            for bx, by, br in blobs:
                rr = br * (0.45 + 0.75 * t)
                d = math.hypot(x - c - bx * t, y - c - by * t) / rr
                best = min(best, d)
            d0 = math.hypot(x - c, y - c) / (size * 0.5 * (0.35 + 0.65 * t))
            d = min(best, d0)
            if d > 1.0:
                continue
            if f == nf - 1:
                col = 13 if d < 0.55 else 12
                if (x * 7 + y * 3) % 5 == 0:
                    continue
            elif f >= nf - 2:
                col = 10 if d < 0.25 else 9 if d < 0.5 else 8 if d < 0.8 else 12
            else:
                col = 11 if d < 0.35 else 10 if d < 0.6 else 9 if d < 0.85 else 8
            cv.px(x, y, col)
    return cv


def heart():
    cv = Canvas(16, 16)
    cv.ellipse(5, 6, 3.5, 3.5, 3)
    cv.ellipse(10, 6, 3.5, 3.5, 3)
    cv.poly([(1.5, 7), (14.5, 7), (8, 14.5)], 3)
    m = Canvas(16, 16)
    for y in range(16):
        for x in range(16):
            if cv.p[y][x]:
                m.p[y][x] = 1
    s = shade(m, (2, 3, 3, 4), 1)
    s.px(4, 4, 11)
    s.px(5, 4, 4)
    s.px(4, 5, 4)
    return s


def cell():
    cv = Canvas(16, 16)
    part(cv, (12, 13, 13, 11), lambda m: m.rect(5, 1, 10, 2, 1))
    part(cv, (14, 14, 15, 15), lambda m: m.rect(3, 3, 12, 14, 1))
    cv.rect(7, 5, 8, 12, 11)
    cv.rect(5, 8, 10, 9, 11)
    return cv


def star(v):
    cv = Canvas(8, 8)
    pts = []
    for i in range(10):
        a = math.radians(-90 + i * 36 + v * 18)
        r = 3.6 if i % 2 == 0 else 1.6
        pts.append((3.5 + math.cos(a) * r, 3.5 + math.sin(a) * r))
    cv.poly(pts, 10)
    cv.px(3, 3, 11)
    return cv


def wave(v):
    cv = Canvas(32, 16)
    rnd = random.Random(7 + v)
    for i in range(26):
        x = rnd.uniform(2, 30)
        h = 10 - abs(x - 16) / 2.2 + rnd.uniform(-2, 2)
        cv.ellipse(x, 15 - h / 2, rnd.uniform(1.5, 3), h / 2, 13 if rnd.random() < 0.5 else 12)
    for i in range(10):
        x = rnd.uniform(4, 28)
        cv.px(x, rnd.uniform(4, 14), 9 if v else 10)
    return cv


def spark(v):
    cv = Canvas(16, 16)
    rnd = random.Random(30 + v)
    pts = [(8, 8)]
    for i in range(6):
        a = rnd.uniform(0, 6.28)
        pts.append((8 + math.cos(a) * 7, 8 + math.sin(a) * 7))
    for p in pts[1:]:
        mx, my = (8 + p[0]) / 2 + rnd.uniform(-2, 2), (8 + p[1]) / 2 + rnd.uniform(-2, 2)
        cv.line(8, 8, mx, my, 10)
        cv.line(mx, my, p[0], p[1], 11)
    cv.ellipse(8, 8, 1.5, 1.5, 11)
    return cv


def flare(v):
    cv = Canvas(16, 16)
    r = 5.5 if v == 0 else 6.5
    cv.ellipse(8, 8, r, r, 2)
    cv.ellipse(8, 8, r - 2, r - 2, 3)
    cv.ellipse(8, 8, r - 4, r - 4, 4)
    for a in range(0, 360, 45):
        cv.line(8, 8, 8 + math.cos(math.radians(a + v * 22)) * 7.5, 8 + math.sin(math.radians(a + v * 22)) * 7.5, 4)
    return cv


def bullet():
    cv = Canvas(8, 8)
    cv.ellipse(3.5, 3.5, 2.5, 2.5, 9)
    cv.ellipse(3, 3, 1.2, 1.2, 10)
    cv.px(3, 3, 11)
    return cv


def warn():
    cv = Canvas(8, 8)
    cv.poly([(3.5, 0), (7.5, 7.5), (-0.5, 7.5)], 10)
    cv.outline(1)
    cv.rect(3, 2, 4, 4, 1)
    cv.rect(3, 6, 4, 6, 1)
    return cv


def rain():
    cv = Canvas(8, 8)
    cv.line(5, 0, 2, 7, 7)
    cv.px(4, 2, 11)
    return cv


def snow():
    cv = Canvas(8, 8)
    cv.line(3.5, 1, 3.5, 6, 11)
    cv.line(1, 3.5, 6, 3.5, 11)
    cv.px(2, 2, 7)
    cv.px(5, 5, 7)
    cv.px(5, 2, 7)
    cv.px(2, 5, 7)
    return cv


def ember():
    cv = Canvas(8, 8)
    cv.ellipse(3.5, 3.5, 1.2, 1.2, 9)
    cv.px(3, 3, 10)
    return cv


def speck():
    cv = Canvas(8, 8)
    cv.px(3, 4, 13)
    cv.px(4, 4, 13)
    cv.px(6, 3, 12)
    return cv


def puff(f):
    cv = Canvas(16, 16)
    r = 2.5 + f * 1.6
    for ox in (-3, 0, 3):
        cv.ellipse(7.5 + ox * (1 + f * 0.5), 12 - f, r * (0.8 if ox else 1), r * 0.7, 13 if f < 2 else 12)
    if f < 2:
        cv.ellipse(7, 11 - f, r * 0.5, r * 0.35, 11)
    return cv


def mflash(v):
    cv = Canvas(16, 16)
    r = 4.5 if v == 0 else 6
    cv.ellipse(7.5, 7.5, r, r * 0.8, 5)
    cv.ellipse(7.5, 7.5, r - 1.5, r * 0.8 - 1.5, 6)
    cv.ellipse(7.5, 7.5, r - 3, r * 0.8 - 3, 7)
    for a in range(0, 360, 60):
        cv.line(7.5, 7.5, 7.5 + math.cos(math.radians(a + v * 30)) * 7.5, 7.5 + math.sin(math.radians(a + v * 30)) * 6, 7)
    return cv


def shadow(w):
    """Dithered dark oval (no hardware transparency needed)."""
    cv = Canvas(w, 8)
    for y in range(8):
        for x in range(w):
            if ((x - w / 2 + 0.5) / (w / 2)) ** 2 + ((y - 3.5) / 3.6) ** 2 <= 1 and (x + y) % 2 == 0:
                cv.p[y][x] = 1
    return cv


def build_fx():
    fx_add("bolt", 16, 16, [bolt(0), bolt(22.5), bolt(45), bolt(67.5), bolt(90)])
    fx_add("beam", 16, 16, [beam_seg(0), beam_seg(1)])
    fx_add("flare", 16, 16, [flare(0), flare(1)])
    fx_add("boom", 32, 32, [boom(32, f, 5, 11) for f in range(5)])
    fx_add("pop", 16, 16, [boom(16, f, 4, 5) for f in range(4)])
    fx_add("bullet", 8, 8, [bullet()])
    fx_add("heart", 16, 16, [heart()])
    fx_add("cell", 16, 16, [cell()])
    fx_add("star", 8, 8, [star(0), star(1)])
    fx_add("dust", 32, 16, [wave(0), wave(1)])
    fx_add("spark", 16, 16, [spark(0), spark(1)])
    fx_add("warn", 8, 8, [warn()])
    fx_add("weather", 8, 8, [rain(), snow(), ember(), speck()])
    fx_add("puff", 16, 16, [puff(f) for f in range(3)])
    fx_add("mflash", 16, 16, [mflash(0), mflash(1)])
    fx_add("shadow32", 32, 8, [shadow(32)])
    fx_add("shadow16", 16, 8, [shadow(16)])
    words = []
    off = 0
    for name, w, h, cvs in FX:
        define("FX_%s" % name.upper(), off)
        define("FX_%s_TILES" % name.upper(), (w // 8) * (h // 8))
        for cv in cvs:
            for t in tiles4(cv):
                words.extend(pack4(t))
            off += (w // 8) * (h // 8)
    emit_u32("fx_tiles", words)
    define("FX_TILE_COUNT", off)
    emit_pal("fx_pal", FX_PAL)
    sheet = Canvas(400, 40)
    x = 0
    for name, w, h, cvs in FX:
        for cv in cvs:
            if x + w > 400:
                break
            sheet.paste(cv, x, 0)
            x += w + 1
    preview("fx.png", sheet, FX_PAL, 3)


# ---------------------------------------------------------------- boss projectiles

PROJ_PAL = [(0, 0, 0), H("#101014"), H("#4a4e58"), H("#9aa2ae"), H("#eef2f8"), H("#c01810"), H("#ff7a10"),
            H("#ffe040"), H("#2050ff"), H("#60e8ff"), H("#ffffff"), H("#90c8ff"), H("#207a10"), H("#70f030"),
            H("#c040ff"), H("#ff60c0")]
PROJ = []


def spike(angle):
    cv = Canvas(16, 16)
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    tip = (7.5 + dx * 7, 7.5 + dy * 7)
    b1 = (7.5 - dx * 4 + nx * 3, 7.5 - dy * 4 + ny * 3)
    b2 = (7.5 - dx * 4 - nx * 3, 7.5 - dy * 4 - ny * 3)
    m = Canvas(16, 16)
    m.poly([tip, b1, b2], 1)
    m.capsule(7.5 - dx * 4, 7.5 - dy * 4, 7.5 - dx * 7, 7.5 - dy * 7, 1, 1)
    cv.paste(shade(m, (2, 3, 4, 4)))
    return cv


def missile(angle):
    cv = Canvas(16, 16)
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    m = Canvas(16, 16)
    m.capsule(7.5 - dx * 4, 7.5 - dy * 4, 7.5 + dx * 4, 7.5 + dy * 4, 2, 1)
    cv.paste(shade(m, (2, 3, 4, 4)))
    cv.px(7.5 + dx * 5, 7.5 + dy * 5, 5)
    cv.px(7.5 + dx * 4, 7.5 + dy * 4, 5)
    cv.capsule(7.5 - dx * 6, 7.5 - dy * 6, 7.5 - dx * 7.5, 7.5 - dy * 7.5, 1.2, 6)
    cv.px(7.5 - dx * 6, 7.5 - dy * 6, 7)
    return cv


def shard(angle):
    cv = Canvas(16, 16)
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    m = Canvas(16, 16)
    m.poly([(7.5 + dx * 7, 7.5 + dy * 7), (7.5 + nx * 2.5, 7.5 + ny * 2.5), (7.5 - dx * 6, 7.5 - dy * 6),
            (7.5 - nx * 2.5, 7.5 - ny * 2.5)], 1)
    cv.paste(shade(m, (8, 11, 11, 10)))
    return cv


def ball(c1, c2, c3, r=5.5, v=0):
    cv = Canvas(16, 16)
    cv.ellipse(7.5, 7.5, r, r, c1)
    cv.ellipse(7.5 - v * 0.5, 7, r - 2, r - 2.5, c2)
    cv.ellipse(6.5, 6.5, 1.5, 1.5, c3)
    return cv


def fireball(v):
    cv = Canvas(16, 16)
    rnd = random.Random(40 + v)
    for i in range(12):
        a = rnd.uniform(0, 6.28)
        r = rnd.uniform(1, 4.5)
        cv.ellipse(7.5 + math.cos(a) * r, 7.5 + math.sin(a) * r, rnd.uniform(1.5, 3), rnd.uniform(1.5, 3), 5)
    cv.ellipse(7.5, 7.5, 4, 4, 6)
    cv.ellipse(7, 7, 2, 2, 7)
    cv.outline(1)
    return cv


def elec(v):
    cv = Canvas(16, 16)
    cv.ellipse(7.5, 7.5, 4, 4, 8)
    cv.ellipse(7.5, 7.5, 2.5, 2.5, 9)
    cv.ellipse(7.5, 7.5, 1, 1, 10)
    rnd = random.Random(50 + v)
    for i in range(5):
        a = rnd.uniform(0, 6.28)
        mx, my = 7.5 + math.cos(a + 0.4) * 4.5, 7.5 + math.sin(a + 0.4) * 4.5
        cv.line(7.5 + math.cos(a) * 3, 7.5 + math.sin(a) * 3, mx, my, 9)
        cv.line(mx, my, 7.5 + math.cos(a) * 7.5, 7.5 + math.sin(a) * 7.5, 10)
    return cv


def saw(v):
    cv = Canvas(16, 16)
    pts = []
    for i in range(16):
        a = math.radians(i * 22.5 + v * 11.25)
        r = 7.4 if i % 2 == 0 else 5.2
        pts.append((7.5 + math.cos(a) * r, 7.5 + math.sin(a) * r))
    m = Canvas(16, 16)
    m.poly(pts, 1)
    cv.paste(shade(m, (2, 3, 4, 4)))
    cv.ellipse(7.5, 7.5, 2, 2, 2)
    cv.px(7, 7, 4)
    return cv


def note(v):
    cv = Canvas(16, 16)
    c = 14 if v == 0 else 15
    cv.ellipse(5, 11, 3, 2.3, c)
    cv.ellipse(11, 9, 3, 2.3, c)
    cv.rect(7, 3, 8, 11, c)
    cv.rect(13, 1, 14, 9, c)
    cv.rect(7, 1, 14, 3, c)
    cv.outline(1)
    cv.px(4, 10, 10)
    cv.px(10, 8, 10)
    return cv


def rock():
    cv = Canvas(16, 16)
    m = Canvas(16, 16)
    m.poly([(3, 5), (7, 2), (12, 3), (14, 8), (12, 13), (6, 14), (2, 10)], 1)
    cv.paste(shade(m, (2, 2, 3, 4)))
    cv.px(6, 8, 2)
    cv.px(9, 10, 2)
    return cv


def scythe(v):
    cv = Canvas(16, 16)
    a0 = v * 90
    for i in range(2):
        a = math.radians(a0 + i * 180)
        cx, cy = 7.5, 7.5
        for t in range(12):
            aa = a + t * 0.14
            r = 7 - t * 0.25
            cv.ellipse(cx + math.cos(aa) * r, cy + math.sin(aa) * r, 1.2, 1.2, 4 if t < 8 else 3)
    cv.ellipse(7.5, 7.5, 2, 2, 14)
    cv.outline(1)
    return cv


def acid(v):
    cv = Canvas(16, 16)
    cv.ellipse(7.5, 8.5 + v * 0.5, 5, 4.5 - v * 0.5, 12)
    cv.ellipse(7.5, 8, 3.5, 3, 13)
    cv.ellipse(6, 6.5, 1, 1, 10)
    cv.px(3, 3 + v, 13)
    cv.px(12, 4 - v, 13)
    cv.outline(1)
    return cv


def sound(v):
    cv = Canvas(16, 16)
    for r in ((3, 6) if v == 0 else (4.5, 7.5)):
        for t in range(-6, 7):
            a = math.radians(t * 9)
            cv.ellipse(5 + math.cos(a) * r, 7.5 + math.sin(a) * r * 1.4, 0.8, 0.8, 14)
    cv.outline(1)
    return cv


def shuriken(v):
    cv = Canvas(16, 16)
    m = Canvas(16, 16)
    pts = []
    for i in range(8):
        a = math.radians(i * 45 + v * 22.5)
        r = 7 if i % 2 == 0 else 2.2
        pts.append((7.5 + math.cos(a) * r, 7.5 + math.sin(a) * r))
    m.poly(pts, 1)
    cv.paste(shade(m, (2, 3, 4, 4)))
    cv.px(7, 7, 1)
    cv.px(8, 8, 1)
    return cv


def laser(angle):
    cv = Canvas(16, 16)
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    cv.capsule(7.5 - dx * 7, 7.5 - dy * 7, 7.5 + dx * 7, 7.5 + dy * 7, 2.2, 5)
    cv.capsule(7.5 - dx * 6, 7.5 - dy * 6, 7.5 + dx * 6, 7.5 + dy * 6, 1.1, 7)
    cv.capsule(7.5 - dx * 5, 7.5 - dy * 5, 7.5 + dx * 5, 7.5 + dy * 5, 0.3, 10)
    return cv


def build_proj():
    PROJ.append(("rivet", [ball(2, 3, 4, 4)]))
    PROJ.append(("saw", [saw(0), saw(1)]))
    PROJ.append(("fire", [fireball(0), fireball(1)]))
    PROJ.append(("spike", [spike(0), spike(22.5), spike(45), spike(67.5), spike(90)]))
    PROJ.append(("elec", [elec(0), elec(1)]))
    PROJ.append(("missile", [missile(0), missile(22.5), missile(45), missile(67.5), missile(90)]))
    PROJ.append(("ice", [shard(0), shard(22.5), shard(45), shard(67.5), shard(90)]))
    PROJ.append(("acid", [acid(0), acid(1)]))
    PROJ.append(("note", [note(0), note(1)]))
    PROJ.append(("rock", [rock()]))
    PROJ.append(("scythe", [scythe(0), scythe(1)]))
    PROJ.append(("sound", [sound(0), sound(1)]))
    PROJ.append(("shuriken", [shuriken(0), shuriken(1)]))
    PROJ.append(("laser", [laser(0), laser(22.5), laser(45), laser(67.5), laser(90)]))
    words = []
    off = 0
    starts, counts = [], []
    for i, (name, cvs) in enumerate(PROJ):
        define("PJ_%s" % name.upper(), i)
        starts.append(off)
        counts.append(len(cvs))
        for cv in cvs:
            for t in tiles4(cv):
                words.extend(pack4(t))
            off += 4
    emit_u32("proj_tiles", words)
    define("PROJ_TILE_COUNT", off)
    define("PJ_COUNT", len(PROJ))
    emit_u16("proj_start", starts)
    emit_u16("proj_frames", counts)
    emit_pal("proj_pal", PROJ_PAL)
    sheet = Canvas(17 * 30, 16)
    x = 0
    for name, cvs in PROJ:
        for cv in cvs:
            sheet.paste(cv, x, 0)
            x += 17
    preview("proj.png", sheet, PROJ_PAL, 3)


# ---------------------------------------------------------------- bosses

BOSSES = [
    dict(name="IRON MAULER", p="#c02828", s="#3c3c46", eye="#ffd020", body="brute", head="box", arm="fist",
         legs="heavy", extras=[]),
    dict(name="SAWBLADE", p="#e07020", s="#50545c", eye="#ff2020", body="slim", head="jaw", arm="saw",
         legs="biped", extras=["mohawk"]),
    dict(name="BLAZE HORN", p="#8c1c2c", s="#d8a030", eye="#ff9010", body="brute", head="horns", arm="flamer",
         legs="bird", extras=["flames"]),
    dict(name="SPIKE GUY", p="#7a3cc0", s="#5cc040", eye="#80ff40", body="barrel", head="spiky", arm="spikegun",
         legs="heavy", extras=["spikes"]),
    dict(name="VOLT SKULL", p="#26408a", s="#40d0ff", eye="#60ffff", body="slim", head="skull", arm="claw",
         legs="biped", extras=["coils"]),
    dict(name="ROCKET RAVEN", p="#34343e", s="#d02828", eye="#ff3030", body="slim", head="beak", arm="cannon",
         legs="bird", extras=["pods"]),
    dict(name="CHROME CRUSHER", p="#a8b0c0", s="#e0c020", eye="#ff4020", body="brute", head="box", arm="fist",
         legs="heavy", extras=["stripes"]),
    dict(name="MAGMA MAW", p="#5a3428", s="#ff7020", eye="#ffd040", body="barrel", head="jaw", arm="fist",
         legs="heavy", extras=["flames", "cracks"]),
    dict(name="FROST FANG", p="#6aa4e0", s="#eef4ff", eye="#40f0ff", body="slim", head="spiky", arm="claw",
         legs="bird", extras=[]),
    dict(name="VENOM VAT", p="#4c9c2c", s="#40444c", eye="#c0ff40", body="tank", head="dome", arm="cannon",
         legs="treads", extras=["tank"]),
    dict(name="DOOM DRILL", p="#e0b020", s="#2c2c30", eye="#ff3020", body="brute", head="drill", arm="drill",
         legs="treads", extras=["stripes"]),
    dict(name="GRIM REAPER", p="#2a2a34", s="#9a70d0", eye="#c060ff", body="slim", head="skull", arm="scythe",
         legs="biped", extras=["hood"]),
    dict(name="HEAVY METAL", p="#2c2c30", s="#d82020", eye="#ff2020", body="brute", head="skull", arm="guitar",
         legs="biped", extras=["mohawk", "flames"]),
    dict(name="STEEL TITAN", p="#5a7ca0", s="#e0b030", eye="#40c0ff", body="knight", head="helm", arm="sword",
         legs="heavy", extras=["shield"]),
    dict(name="BLIZZARD BEAST", p="#dce6f0", s="#5a94d0", eye="#40e0ff", body="barrel", head="yeti", arm="fist",
         legs="heavy", extras=["spikes"]),
    dict(name="NEON NINJA", p="#202034", s="#ff30c0", eye="#40ffff", body="slim", head="ninja", arm="sword",
         legs="biped", extras=[]),
    dict(name="SCRAP KING", p="#8a6a3a", s="#e0c030", eye="#ff4020", body="tank", head="box", arm="claw",
         legs="treads", extras=["crown", "stripes"]),
    dict(name="CYCLOPS", p="#4a5a6a", s="#ff3030", eye="#ff2020", body="brute", head="cyclops", arm="cannon",
         legs="biped", extras=["coils"]),
    dict(name="DRAGON-X", p="#2a7a3a", s="#e0b030", eye="#ffb020", body="slim", head="dragon", arm="flamer",
         legs="bird", extras=[]),
    dict(name="INFERNO KING", p="#3a0c0c", s="#ff6010", eye="#ffe040", body="brute", head="horns", arm="hammer",
         legs="heavy", extras=["crown", "flames", "cracks"]),
]
MEGA = dict(name="MEGA ROBOT", p="#b01420", s="#1e1e24", eye="#ff2020", body="brute", head="horns", arm="cannon",
            legs="heavy", extras=["spikes", "pods", "reactor"])


def boss_pal(b):
    p = ramp4(H(b["p"]))
    s = ramp4(H(b["s"]))
    e = H(b["eye"])
    return [(0, 0, 0), H("#0c0c10"), p[0], p[1], p[2], p[3], s[0], s[1], s[2], H("#3a3e46"), H("#7c848e"),
            H("#c8ced6"), e, mix(e, (255, 255, 255), 0.6), H("#f0f0f0"), H("#000000")]


BP = (2, 3, 4, 5)
BS = (6, 7, 8, 8)
BM = (9, 10, 11, 11)
BPD = (2, 2, 3, 4)


class Boss:
    """Draws a boss in 'base' coordinates (64x96 frame, feet at y=95) scaled by k into any frame."""

    def __init__(s, b, pose, w=64, h=96, k=1.0):
        s.b, s.pose, s.k = b, pose, k
        s.cv = Canvas(w, h)
        s.ox, s.oy = w / 2 - 32 * k, h - 96 * k

    def P(s, x, y):
        return (s.ox + x * s.k, s.oy + y * s.k)

    def Ps(s, pts):
        return [s.P(x, y) for x, y in pts]

    def r(s, v):
        return v * s.k

    def cap(s, ramp, a, b, r):
        A, B = s.P(*a), s.P(*b)
        part(s.cv, ramp, lambda m: m.capsule(A[0], A[1], B[0], B[1], s.r(r), 1))

    def ell(s, ramp, c, rx, ry):
        C = s.P(*c)
        part(s.cv, ramp, lambda m: m.ellipse(C[0], C[1], s.r(rx), s.r(ry), 1))

    def pol(s, ramp, pts):
        Q = s.Ps(pts)
        part(s.cv, ramp, lambda m: m.poly(Q, 1))

    def box(s, ramp, x0, y0, x1, y1):
        s.pol(ramp, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])

    def dot(s, x, y, c, r=0):
        X, Y = s.P(x, y)
        if r:
            s.cv.ellipse(X, Y, s.r(r), s.r(r), c)
        else:
            s.cv.px(X, Y, c)

    def ln(s, a, b, c, w=1):
        A, B = s.P(*a), s.P(*b)
        s.cv.line(A[0], A[1], B[0], B[1], c, max(1, int(round(w * s.k))))

    def fpoly(s, pts, c):
        s.cv.poly(s.Ps(pts), c)


def boss_draw(b, pose, w=64, h=96, k=1.0):
    d = Boss(b, pose, w, h, k)
    bob = 1 if pose == 1 else 0
    atk = pose == 2
    legs, body, head, arm, ex = b["legs"], b["body"], b["head"], b["arm"], b["extras"]
    # anatomy anchors
    hipy = 70 + bob
    shy = 44 + bob
    if body == "tank":
        shy = 50 + bob
    headc = (31, 33 + bob)
    fsh, bsh = (39, shy), (22, shy)
    if body in ("brute", "knight"):
        fsh, bsh = (42, shy), (19, shy)
    if body == "barrel":
        fsh, bsh = (45, shy + 4), (17, shy + 4)

    # ---- back arm
    def arm_draw(sh, front):
        ramp = BP if front else BPD
        if front:
            if atk:
                hand = (sh[0] + 17, sh[1] - 4)
            else:
                hand = (sh[0] + 8, sh[1] + 18 + (bob if pose == 1 else 0))
        else:
            hand = (sh[0] - 4, sh[1] + 19 - bob)
        elbow, end = ik(sh, hand, 11, 12, 1)
        d.cap(BM, sh, elbow, 4)
        d.cap(ramp, elbow, end, 5)
        hx, hy = end
        ux, uy = end[0] - elbow[0], end[1] - elbow[1]
        ul = math.hypot(ux, uy) or 1
        ux, uy = ux / ul, uy / ul
        kind = arm if front else ("shield" if "shield" in ex else "fist" if arm not in ("claw",) else "claw")
        if kind == "fist":
            r = 7 if body == "brute" else 6
            d.ell(BS if front else (6, 6, 7, 7), (hx + ux * 2, hy + uy * 2), r, r)
            d.ln((hx + ux * 2 - 3, hy + uy * 2 - 2), (hx + ux * 2 + 3, hy + uy * 2 - 2), 6)
        elif kind == "saw":
            cx, cy = hx + ux * 6, hy + uy * 6
            pts = []
            for i in range(16):
                a = math.radians(i * 22.5 + pose * 11)
                rr = 9 if i % 2 == 0 else 6.5
                pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
            d.pol(BM, pts)
            d.dot(cx, cy, 9, 2.5)
            d.dot(cx, cy, 12, 1)
        elif kind == "cannon":
            ex2, ey2 = hx + ux * 12, hy + uy * 12
            d.cap(BM, (hx, hy), (ex2, ey2), 3.5)
            d.dot(ex2, ey2, 15, 2)
            if atk:
                d.dot(ex2 + ux * 2, ey2 + uy * 2, 13, 1.5)
        elif kind == "flamer":
            ex2, ey2 = hx + ux * 9, hy + uy * 9
            d.cap(BS, (hx, hy), (ex2, ey2), 3)
            d.dot(ex2, ey2, 15, 1.5)
            if atk:
                for i in range(4):
                    d.dot(ex2 + ux * (3 + i * 3), ey2 + uy * (3 + i * 3) + (i % 2), 12 if i < 2 else 13, 2 + i * 0.5)
        elif kind == "claw":
            for sgn in (-1, 1):
                nx, ny = -uy * sgn, ux * sgn
                a = (hx + nx * 2, hy + ny * 2)
                b2 = (hx + ux * 7 + nx * 5, hy + uy * 7 + ny * 5)
                c2 = (hx + ux * 11 + nx * (1 if not atk else 4), hy + uy * 11 + ny * (1 if not atk else 4))
                d.cap(BS if front else (6, 6, 7, 7), a, b2, 2)
                d.cap(BS if front else (6, 6, 7, 7), b2, c2, 1.5)
        elif kind == "drill":
            nx, ny = -uy, ux
            base = (hx + ux * 2, hy + uy * 2)
            tip = (hx + ux * 18, hy + uy * 18)
            d.pol(BS, [(base[0] + nx * 6, base[1] + ny * 6), tip, (base[0] - nx * 6, base[1] - ny * 6)])
            for i in range(1, 4):
                t = i / 4
                pa = (base[0] + nx * 6 * (1 - t) + (tip[0] - base[0]) * t,
                      base[1] + ny * 6 * (1 - t) + (tip[1] - base[1]) * t)
                pb = (base[0] - nx * 6 * (1 - t) + (tip[0] - base[0]) * (t + 0.12),
                      base[1] - ny * 6 * (1 - t) + (tip[1] - base[1]) * (t + 0.12))
                d.ln(pa, pb, 6)
        elif kind == "spikegun":
            d.ell(BS, (hx + ux * 3, hy + uy * 3), 6, 6)
            for a in range(0, 360, 45):
                rr = math.radians(a)
                d.pol((9, 10, 11, 14), [(hx + ux * 3 + math.cos(rr - 0.3) * 5, hy + uy * 3 + math.sin(rr - 0.3) * 5),
                                       (hx + ux * 3 + math.cos(rr) * 10, hy + uy * 3 + math.sin(rr) * 10),
                                       (hx + ux * 3 + math.cos(rr + 0.3) * 5, hy + uy * 3 + math.sin(rr + 0.3) * 5)])
        elif kind == "guitar":
            # a flying-V guitar held across the body
            gx, gy = hx - 2, hy + 2
            d.pol(BS, [(gx - 12, gy - 6), (gx + 2, gy + 2), (gx - 10, gy + 10), (gx - 4, gy + 2)])
            d.ln((gx - 2, gy + 1), (gx + 20, gy - 12), 10, 2)
            d.pol(BM, [(gx + 18, gy - 15), (gx + 24, gy - 16), (gx + 22, gy - 10)])
            d.ell(BS, (hx, hy), 4, 4)
        elif kind == "scythe":
            top = (hx + ux * 4 - 2, hy - 26)
            bot = (hx - ux * 2 + 2, hy + 14)
            d.ln(bot, top, 9, 2)
            d.pol((9, 10, 11, 14), [(top[0], top[1]), (top[0] + 20, top[1] + 4), (top[0] + 24, top[1] + 12),
                                   (top[0] + 14, top[1] + 5), (top[0], top[1] + 4)])
            d.ell(BS, (hx, hy), 4, 4)
        elif kind == "sword":
            nx, ny = (1, -1) if atk else (0.5, -1)
            nl = math.hypot(nx, ny)
            nx, ny = nx / nl, ny / nl
            base = (hx, hy)
            tip = (hx + nx * 30, hy + ny * 30)
            d.cap((9, 10, 11, 14), base, tip, 2)
            d.ln((hx - ny * 6, hy + nx * 6), (hx + ny * 6, hy - nx * 6), 6, 2)
            d.ell(BS, (hx, hy), 4, 4)
        elif kind == "hammer":
            top = (hx + ux * 2, hy - 18) if not atk else (hx + 16, hy - 10)
            d.ln((hx, hy), top, 9, 2)
            hx2, hy2 = top
            d.pol(BS, [(hx2 - 9, hy2 - 6), (hx2 + 9, hy2 - 6), (hx2 + 9, hy2 + 5), (hx2 - 9, hy2 + 5)])
            d.ln((hx2 - 9, hy2 - 1), (hx2 + 9, hy2 - 1), 13)
            d.ell(BS, (hx, hy), 4, 4)
        elif kind == "shield":
            d.pol(BS, [(hx - 9, hy - 12), (hx + 7, hy - 12), (hx + 7, hy + 2), (hx - 1, hy + 12), (hx - 9, hy + 2)])
            d.ln((hx - 1, hy - 10), (hx - 1, hy + 8), 4, 1)
            d.ln((hx - 7, hy - 4), (hx + 5, hy - 4), 4, 1)
        return end

    # ---- legs
    def leg(hip, ankle, ramp):
        knee, end = ik(hip, ankle, 13, 13, 1 if legs == "bird" else -1)
        d.cap(ramp, hip, knee, 5.5 if legs == "heavy" else 4.5)
        d.cap(ramp, knee, end, 5 if legs == "heavy" else 4)
        d.ell(BM, knee, 3, 3)
        ax, ay = end
        if legs == "bird":
            d.pol(BM, [(ax - 6, ay + 6), (ax - 2, ay - 2), (ax + 3, ay - 2), (ax + 9, ay + 6)])
            d.ln((ax + 9, ay + 6), (ax + 11, ay + 6), 11)
        else:
            wd = 9 if legs == "heavy" else 7
            d.pol(BM, [(ax - wd, ay + 6), (ax - wd + 1, ay - 2), (ax + wd - 2, ay - 3), (ax + wd + 3, ay + 1),
                       (ax + wd + 3, ay + 6)])

    if legs == "treads":
        pass
    else:
        st = [(-3, 0), (3, 0)] if pose != 1 else [(0, 0), (0, -3)]
        if atk:
            st = [(-5, 0), (5, 0)]
        leg((28, hipy), (24 + st[0][0], 89 + st[0][1]), BPD)

    if body != "tank":
        arm_draw(bsh, False)

    # ---- treads (base under a tank body)
    if legs == "treads":
        d.pol(BM, [(8, 78), (56, 78), (61, 86), (56, 95), (8, 95), (3, 86)])
        for i, wx in enumerate((12, 22, 32, 42, 52)):
            d.dot(wx, 88, 9, 3.5)
            d.dot(wx, 88, 11 if (i + pose) % 2 == 0 else 10, 1.5)
        d.ln((8, 79), (56, 79), 11)

    # ---- torso
    if body == "brute":
        d.box(BPD, 22, 60 + bob, 40, 72 + bob)
        d.pol(BP, [(12, 40 + bob), (50, 40 + bob), (53, 48 + bob), (46, 64 + bob), (16, 64 + bob), (9, 48 + bob)])
        d.ln((20, 50 + bob), (42, 50 + bob), 6, 2)
        d.ln((24, 56 + bob), (38, 56 + bob), 2)
    elif body == "slim":
        d.box(BPD, 24, 60 + bob, 38, 72 + bob)
        d.pol(BP, [(18, 42 + bob), (44, 42 + bob), (46, 50 + bob), (39, 64 + bob), (23, 64 + bob), (16, 50 + bob)])
        d.ln((26, 49 + bob), (36, 49 + bob), 6, 2)
    elif body == "barrel":
        d.box(BPD, 22, 66 + bob, 40, 74 + bob)
        d.ell(BP, (31, 56 + bob), 18, 15)
        d.ln((16, 56 + bob), (46, 56 + bob), 7, 2)
    elif body == "tank":
        d.pol(BP, [(14, 50), (50, 50), (52, 78), (12, 78)])
        d.box(BS, 18, 62, 46, 68)
        for x in range(20, 46, 5):
            d.dot(x, 65, 13)
    elif body == "knight":
        d.box(BPD, 22, 60 + bob, 40, 72 + bob)
        d.pol(BP, [(13, 40 + bob), (49, 40 + bob), (51, 50 + bob), (44, 64 + bob), (18, 64 + bob), (11, 50 + bob)])
        d.pol(BS, [(24, 44 + bob), (38, 44 + bob), (36, 58 + bob), (31, 62 + bob), (26, 58 + bob)])
        d.ln((18, 64 + bob), (44, 64 + bob), 7, 2)
    # chest core
    if body in ("brute", "slim", "barrel", "knight"):
        cy = 52 + bob if body != "barrel" else 56 + bob
        if "reactor" in ex:
            d.dot(31, cy, 12, 4.5)
            d.dot(31, cy, 13, 2.5)
        else:
            d.dot(31, cy - 4, 12 if not atk else 13, 1.5)
    if "stripes" in ex:
        for i in range(4):
            x = 18 + i * 7
            d.fpoly([(x, 66 + bob), (x + 3, 66 + bob), (x + 7, 62 + bob), (x + 4, 62 + bob)], 15)
    if "cracks" in ex:
        d.ln((20, 46 + bob), (26, 52 + bob), 13)
        d.ln((26, 52 + bob), (24, 60 + bob), 12)
        d.ln((40, 48 + bob), (36, 56 + bob), 13)
    if "tank" in ex:
        d.box(BS, 4, 34, 14, 58)
        d.box((12, 12, 13, 13), 6, 40, 12, 56)
        d.dot(8, 44, 14)
    if "pods" in ex:
        for px in ((14, 36 + bob), (40, 36 + bob)):
            d.box(BS, px[0], px[1] - 6, px[0] + 10, px[1])
            for j in range(3):
                d.dot(px[0] + 2 + j * 3, px[1] - 3, 13 if atk else 15)
    if "coils" in ex:
        for cx in (16, 46):
            d.cap(BM, (cx, shy - 2), (cx, shy - 14), 1.6)
            for j in range(3):
                d.ell(BS, (cx, shy - 5 - j * 4), 3.5, 1.3)
            d.dot(cx, shy - 16, 13 if atk else 12, 2)

    # shoulder pads
    if body != "tank":
        sr = 8 if body in ("brute", "knight") else 6
        d.ell(BPD, bsh, sr, sr - 1)

    # ---- head
    hx, hy = headc
    if body == "tank":
        hy = 42
    if head == "box":
        d.pol(BP, [(hx - 10, hy - 9), (hx + 10, hy - 9), (hx + 11, hy + 8), (hx - 11, hy + 8)])
        d.box((15, 15, 15, 15), hx - 8, hy - 3, hx + 9, hy + 1)
        d.ln((hx - 6, hy - 1), (hx + 8, hy - 1), 12 if not atk else 13, 1)
        d.ln((hx - 6, hy + 4), (hx + 6, hy + 4), 6)
    elif head == "jaw":
        d.pol(BP, [(hx - 9, hy - 10), (hx + 10, hy - 10), (hx + 12, hy - 2), (hx - 10, hy - 2)])
        jo = 5 if atk else 1
        d.pol(BS, [(hx - 9, hy + jo), (hx + 12, hy + jo), (hx + 10, hy + 9 + jo), (hx - 8, hy + 9 + jo)])
        for i in range(5):
            x = hx - 6 + i * 4
            d.fpoly([(x, hy - 2), (x + 3, hy - 2), (x + 1.5, hy + 1)], 14)
            d.fpoly([(x, hy + jo + 1), (x + 3, hy + jo + 1), (x + 1.5, hy + jo - 2)], 14)
        if atk:
            d.box((12, 12, 13, 13), hx - 6, hy, hx + 8, hy + 3)
        d.ln((hx - 5, hy - 6), (hx - 1, hy - 5), 12, 1)
        d.ln((hx + 3, hy - 5), (hx + 7, hy - 6), 12, 1)
    elif head == "horns":
        for sg in (-1, 1):
            d.pol(BS, [(hx + sg * 6, hy - 6), (hx + sg * 13, hy - 12), (hx + sg * 16, hy - 22),
                       (hx + sg * 10, hy - 13), (hx + sg * 4, hy - 9)])
        d.pol(BP, [(hx - 9, hy - 9), (hx + 9, hy - 9), (hx + 10, hy + 4), (hx + 4, hy + 9), (hx - 4, hy + 9),
                   (hx - 10, hy + 4)])
        d.fpoly([(hx - 7, hy - 4), (hx - 1, hy - 1), (hx - 7, hy - 1)], 12 if not atk else 13)
        d.fpoly([(hx + 8, hy - 4), (hx + 2, hy - 1), (hx + 8, hy - 1)], 12 if not atk else 13)
        d.ln((hx - 3, hy + 5), (hx + 4, hy + 5), 15)
    elif head == "spiky":
        for a in range(-80, 81, 32):
            rr = math.radians(a - 90)
            d.pol((9, 10, 11, 14), [(hx + math.cos(rr - 0.25) * 7, hy - 2 + math.sin(rr - 0.25) * 7),
                                   (hx + math.cos(rr) * 18, hy - 2 + math.sin(rr) * 18),
                                   (hx + math.cos(rr + 0.25) * 7, hy - 2 + math.sin(rr + 0.25) * 7)])
        d.ell(BP, (hx, hy), 10, 9)
        d.ln((hx - 6, hy - 2), (hx - 1, hy), 12 if not atk else 13, 2)
        d.ln((hx + 7, hy - 2), (hx + 2, hy), 12 if not atk else 13, 2)
        d.ln((hx - 4, hy + 5), (hx + 4, hy + 5), 15)
    elif head == "skull":
        if "hood" in ex:
            d.pol(BPD, [(hx - 13, hy + 10), (hx - 12, hy - 8), (hx, hy - 16), (hx + 12, hy - 8), (hx + 13, hy + 10)])
        d.ell((9, 10, 11, 14), (hx, hy - 2), 9, 8)
        d.box((9, 10, 11, 14), hx - 5, hy + 4, hx + 5, hy + 9)
        d.dot(hx - 4, hy - 2, 15, 2.5)
        d.dot(hx + 4, hy - 2, 15, 2.5)
        d.dot(hx - 4, hy - 2, 12 if not atk else 13, 1)
        d.dot(hx + 4, hy - 2, 12 if not atk else 13, 1)
        d.fpoly([(hx, hy + 1), (hx - 1.5, hy + 4), (hx + 1.5, hy + 4)], 15)
        for x in (-3, -1, 1, 3):
            d.ln((hx + x, hy + 6), (hx + x, hy + 8), 9)
        if "mohawk" in ex:
            for i in range(5):
                x = hx - 6 + i * 3
                d.pol(BS, [(x, hy - 8), (x + 3, hy - 8), (x + 2, hy - 18 + abs(i - 2) * 2)])
    elif head == "dome":
        d.box(BM, hx - 9, hy, hx + 9, hy + 6)
        d.ell((6, 7, 8, 14), (hx, hy - 3), 9, 8)
        d.dot(hx - 2, hy - 4, 12, 3)
        d.dot(hx + 3, hy - 2, 12, 2)
        d.dot(hx - 4, hy - 7, 14)
        d.ln((hx - 6, hy + 3), (hx + 6, hy + 3), 13 if atk else 12)
    elif head == "beak":
        d.pol(BP, [(hx - 9, hy - 8), (hx + 6, hy - 9), (hx + 9, hy - 3), (hx + 9, hy + 6), (hx - 8, hy + 6)])
        d.pol(BS, [(hx + 6, hy - 4), (hx + 20, hy + 1), (hx + 6, hy + 4)])
        d.dot(hx + 2, hy - 3, 12 if not atk else 13, 1.6)
        for i in range(3):
            d.pol(BPD, [(hx - 9 + i * 3, hy - 7), (hx - 15 + i * 2, hy - 16 + i * 2), (hx - 5 + i * 3, hy - 8)])
    elif head == "drill":
        d.pol(BP, [(hx - 10, hy - 4), (hx + 10, hy - 4), (hx + 11, hy + 8), (hx - 11, hy + 8)])
        d.pol(BM, [(hx - 9, hy - 4), (hx, hy - 24), (hx + 9, hy - 4)])
        for i in range(1, 4):
            y = hy - 4 - i * 5
            w2 = 9 * (1 - i / 4.4)
            d.ln((hx - w2, y + 2), (hx + w2, y - 1), 9)
        d.box((15, 15, 15, 15), hx - 8, hy, hx + 8, hy + 3)
        d.ln((hx - 6, hy + 1), (hx + 6, hy + 1), 12 if not atk else 13)
    elif head == "helm":
        d.pol(BP, [(hx - 10, hy - 6), (hx - 6, hy - 11), (hx + 6, hy - 11), (hx + 10, hy - 6), (hx + 10, hy + 8),
                   (hx - 10, hy + 8)])
        d.box((15, 15, 15, 15), hx - 8, hy - 3, hx + 8, hy - 1)
        d.box((15, 15, 15, 15), hx - 1, hy - 1, hx + 1, hy + 6)
        d.ln((hx - 6, hy - 2), (hx + 6, hy - 2), 12 if not atk else 13)
        d.pol(BS, [(hx - 2, hy - 11), (hx + 2, hy - 11), (hx + 1, hy - 19), (hx - 6, hy - 20)])
    elif head == "yeti":
        d.ell(BP, (hx, hy), 11, 10)
        for i in range(7):
            a = math.radians(200 + i * 23)
            d.fpoly([(hx + math.cos(a) * 9, hy + math.sin(a) * 8), (hx + math.cos(a + 0.2) * 13, hy + math.sin(a + 0.2) * 12),
                     (hx + math.cos(a + 0.35) * 9, hy + math.sin(a + 0.35) * 8)], 4)
        d.box((15, 15, 15, 15), hx - 6, hy - 3, hx + 7, hy)
        d.dot(hx - 3, hy - 2, 12 if not atk else 13, 1.2)
        d.dot(hx + 4, hy - 2, 12 if not atk else 13, 1.2)
        jo = 3 if atk else 0
        d.box((15, 15, 15, 15), hx - 5, hy + 3, hx + 6, hy + 5 + jo)
        d.fpoly([(hx - 4, hy + 3), (hx - 2, hy + 3), (hx - 3, hy + 7 + jo)], 14)
        d.fpoly([(hx + 3, hy + 3), (hx + 5, hy + 3), (hx + 4, hy + 7 + jo)], 14)
    elif head == "ninja":
        d.ell(BP, (hx, hy), 9, 9)
        d.box(BS, hx - 9, hy - 4, hx + 9, hy - 1)
        d.pol(BS, [(hx - 9, hy - 3), (hx - 19, hy - 7 + pose), (hx - 18, hy - 2 + pose), (hx - 9, hy)])
        d.box((15, 15, 15, 15), hx - 6, hy + 1, hx + 8, hy + 3)
        d.ln((hx - 3, hy + 2), (hx + 7, hy + 2), 12 if not atk else 13)
    elif head == "cyclops":
        d.ell(BP, (hx, hy), 11, 10)
        d.dot(hx + 1, hy - 1, 15, 6)
        d.dot(hx + 1, hy - 1, 12, 4.5)
        d.dot(hx + 2, hy - 1, 13, 2.5 if not atk else 3.5)
        d.dot(hx + 3, hy - 3, 14)
        d.ln((hx - 6, hy + 7), (hx + 7, hy + 7), 15)
        d.pol(BS, [(hx - 2, hy - 10), (hx + 2, hy - 10), (hx, hy - 17)])
    elif head == "dragon":
        for sg in (-1, 1):
            d.pol(BS, [(hx - 4 + sg * 2, hy - 7), (hx - 12 + sg * 3, hy - 18), (hx - 2 + sg * 2, hy - 9)])
        d.pol(BP, [(hx - 9, hy - 8), (hx + 4, hy - 9), (hx + 18, hy - 2), (hx + 18, hy + 2), (hx + 4, hy + 2),
                   (hx - 9, hy + 6)])
        jo = 5 if atk else 1
        d.pol(BPD, [(hx - 6, hy + 2), (hx + 16, hy + 2 + jo), (hx + 14, hy + 5 + jo), (hx - 6, hy + 8)])
        for i in range(4):
            x = hx + 4 + i * 3.5
            d.fpoly([(x, hy + 2), (x + 2, hy + 2), (x + 1, hy + 4)], 14)
        d.dot(hx + 1, hy - 4, 12 if not atk else 13, 1.5)
        d.dot(hx + 16, hy - 1, 15)
        if atk:
            d.dot(hx + 20, hy + 3, 12, 2.5)
            d.dot(hx + 23, hy + 3, 13, 1.5)
    if "crown" in ex:
        cy = hy - (9 if head != "horns" else 8)
        d.pol((6, 7, 8, 8), [(hx - 9, cy + 2), (hx - 9, cy - 6), (hx - 5, cy - 2), (hx, cy - 8), (hx + 5, cy - 2),
                             (hx + 9, cy - 6), (hx + 9, cy + 2)])
        d.dot(hx, cy - 1, 13)
        d.dot(hx - 6, cy, 12)
        d.dot(hx + 6, cy, 12)
    if "mohawk" in ex and head != "skull":
        for i in range(5):
            x = hx - 6 + i * 3
            d.pol(BS, [(x, hy - 9), (x + 3, hy - 9), (x + 2, hy - 17 + abs(i - 2) * 2)])
    if "flames" in ex:
        rnd = random.Random(pose * 13 + len(b["name"]))
        for i in range(5):
            fx = hx - 10 + i * 5 + rnd.uniform(-1, 1)
            top = hy - 14 - rnd.uniform(2, 9) if head != "horns" else hy - 12 - rnd.uniform(0, 5)
            d.fpoly([(fx - 3, hy - 8), (fx + 3, hy - 8), (fx + rnd.uniform(-1, 1), top)], 12)
            d.fpoly([(fx - 1.5, hy - 8), (fx + 1.5, hy - 8), (fx, top + 4)], 13)

    # ---- front leg, front arm, front shoulder pad
    if legs != "treads":
        st = [(-3, 0), (3, 0)] if pose != 1 else [(0, 0), (0, -3)]
        if atk:
            st = [(-5, 0), (5, 0)]
        leg((35, hipy), (40 + st[1][0], 89 + st[1][1]), BP)
    if body == "tank":
        arm_draw((44, 56), True)
    else:
        arm_draw(fsh, True)
        sr = 8 if body in ("brute", "knight") else 6
        d.ell(BP, fsh, sr, sr - 1)
        d.dot(fsh[0] - 2, fsh[1] - 3, 5)
    if "spikes" in ex:
        rnd = random.Random(3)
        pts = [(fsh[0], fsh[1] - 7), (bsh[0], bsh[1] - 7), (fsh[0] + 7, fsh[1] - 3), (bsh[0] - 7, bsh[1] - 3)]
        if body == "barrel":
            pts += [(31 + math.cos(a) * 17, 56 + bob + math.sin(a) * 14) for a in
                    [math.radians(t) for t in (160, 200, 240, 300, 340, 20)]]
        for (x, y) in pts:
            cx, cy = (31, 50 + bob)
            vx, vy = x - cx, y - cy
            vl = math.hypot(vx, vy) or 1
            vx, vy = vx / vl, vy / vl
            nx, ny = -vy, vx
            d.pol((9, 10, 11, 14), [(x + nx * 2.5, y + ny * 2.5), (x + vx * 8, y + vy * 8),
                                   (x - nx * 2.5, y - ny * 2.5)])
    return d.cv


def build_bosses():
    words = []
    pals = []
    sheet = Canvas(64 * 14, 96 * 3)
    img = Image.new("RGB", (64 * len(BOSSES), 96 * 3))
    for i, b in enumerate(BOSSES):
        pal = boss_pal(b)
        pals.extend(g15(c) for c in pal)
        for pose in range(3):
            cv = boss_draw(b, pose)
            for t in meta_tiles(cv):
                words.extend(pack4(t))
            for y in range(96):
                for x in range(64):
                    v = cv.p[y][x]
                    img.putpixel((i * 64 + x, pose * 96 + y), pal[v] if v else (40, 0, 40))
    img.resize((img.width * 2, img.height * 2), Image.NEAREST).save(os.path.join(ART, "bosses.png"))
    emit_u32("boss_tiles", words)
    emit_u16("boss_pals", pals)
    define("BOSS_COUNT", len(BOSSES))
    names = ", ".join('"%s"' % b["name"] for b in BOSSES + [MEGA])
    C_OUT.append("const char* const boss_names[%d] = { %s };\n" % (len(BOSSES) + 1, names))
    H_OUT.append("extern const char* const boss_names[%d];" % (len(BOSSES) + 1))
    # the mega robot: 128x128, scaled up
    words = []
    pal = boss_pal(MEGA)
    img = Image.new("RGB", (128 * 3, 128))
    for pose in range(3):
        cv = boss_draw(MEGA, pose, 128, 128, 1.75)
        for t in meta_tiles(cv):
            words.extend(pack4(t))
        for y in range(128):
            for x in range(128):
                v = cv.p[y][x]
                img.putpixel((pose * 128 + x, y), pal[v] if v else (40, 0, 40))
    img.resize((img.width * 2, img.height * 2), Image.NEAREST).save(os.path.join(ART, "mega.png"))
    emit_u32("mega_tiles", words)
    emit_pal("mega_pal", pal)


# ---------------------------------------------------------------- fonts (chrome + fire, heavy metal)

FONT5 = {
    "A": [" ### ", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#   #", "#### ", "#   #", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", "#    ", "#    ", " ####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#####"],
    "F": ["#####", "#    ", "#    ", "#### ", "#    ", "#    ", "#    "],
    "G": [" ####", "#    ", "#    ", "# ###", "#   #", "#   #", " ####"],
    "H": ["#   #", "#   #", "#   #", "#####", "#   #", "#   #", "#   #"],
    "I": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "#####"],
    "J": ["  ###", "    #", "    #", "    #", "    #", "#   #", " ### "],
    "K": ["#   #", "#  # ", "# #  ", "##   ", "# #  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "# # #", "#   #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #", "#   #", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#   #", "#### ", "#    ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "#   #", "#   #", "# # #", "#  # ", " ## #"],
    "R": ["#### ", "#   #", "#   #", "#### ", "# #  ", "#  # ", "#   #"],
    "S": [" ####", "#    ", "#    ", " ### ", "    #", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", "#   #", " # # ", " # # ", "  #  "],
    "W": ["#   #", "#   #", "#   #", "# # #", "# # #", "## ##", "#   #"],
    "X": ["#   #", "#   #", " # # ", "  #  ", " # # ", "#   #", "#   #"],
    "Y": ["#   #", "#   #", " # # ", "  #  ", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "    #", "   # ", "  #  ", " #   ", "#    ", "#####"],
    "0": [" ### ", "#   #", "#  ##", "# # #", "##  #", "#   #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "    #", "   # ", "  #  ", " #   ", "#####"],
    "3": ["#### ", "    #", "    #", " ### ", "    #", "    #", "#### "],
    "4": ["   # ", "  ## ", " # # ", "#  # ", "#####", "   # ", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "    #", "#   #", " ### "],
    "6": [" ### ", "#    ", "#    ", "#### ", "#   #", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", "  #  ", "  #  ", "  #  "],
    "8": [" ### ", "#   #", "#   #", " ### ", "#   #", "#   #", " ### "],
    "9": [" ### ", "#   #", "#   #", " ####", "    #", "    #", " ### "],
    "!": ["  #  ", "  #  ", "  #  ", "  #  ", "  #  ", "     ", "  #  "],
    "?": [" ### ", "#   #", "    #", "   # ", "  #  ", "     ", "  #  "],
    ".": ["     ", "     ", "     ", "     ", "     ", "     ", "  #  "],
    ",": ["     ", "     ", "     ", "     ", "     ", "  #  ", " #   "],
    ":": ["     ", "  #  ", "     ", "     ", "     ", "  #  ", "     "],
    "-": ["     ", "     ", "     ", " ### ", "     ", "     ", "     "],
    "+": ["     ", "  #  ", "  #  ", "#####", "  #  ", "  #  ", "     "],
    "'": ["  #  ", "  #  ", "     ", "     ", "     ", "     ", "     "],
    "/": ["    #", "    #", "   # ", "  #  ", " #   ", "#    ", "#    "],
    "(": ["   # ", "  #  ", " #   ", " #   ", " #   ", "  #  ", "   # "],
    ")": [" #   ", "  #  ", "   # ", "   # ", "   # ", "  #  ", " #   "],
    "*": ["     ", "# # #", " ### ", "#####", " ### ", "# # #", "     "],
    "=": ["     ", "     ", "#####", "     ", "#####", "     ", "     "],
    ">": [" #   ", "  #  ", "   # ", "    #", "   # ", "  #  ", " #   "],
    "<": ["   # ", "  #  ", " #   ", "#    ", " #   ", "  #  ", "   # "],
}
FONT_CHARS = " " + "".join(chr(c) for c in range(33, 96))
BIG_CHARS = " !'-.0123456789:?ABCDEFGHIJKLMNOPQRSTUVWXYZ"

# font palette (BG bank 15): 1 shadow, 2..7 chrome-to-fire rows, 8 plain white, 9 gray, 10 red, 11 yellow
FONT_PAL = [(0, 0, 0), H("#000000"), H("#ffffff"), H("#c8ced8"), H("#8e98a8"), H("#ffffff"), H("#ffb028"),
            H("#e8401a"), H("#ffffff"), H("#9aa0aa"), H("#ff3020"), H("#ffd840"), H("#40c040"), H("#202028"),
            H("#a01010"), H("#5080ff")]
SMALL_ROWS = [2, 3, 4, 5, 6, 7, 7]


PANEL_CHARS = " !%'()+,-./0123456789:>?ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def glyph_small(ch, style, panel=False):
    cv = Canvas(8, 8, 13 if panel else 0)
    g = FONT5.get(ch)
    if ch == "%":
        g = ["##  #", "## # ", "   # ", "  #  ", " #   ", "# ## ", "#  ##"]
    if not g:
        return cv
    m = Canvas(8, 8)
    for y, row in enumerate(g):
        for x, c in enumerate(row):
            if c == "#":
                m.px(x, y, 1)
                m.px(x + 1, y, 1)
    for y in range(8):
        for x in range(8):
            if m.p[y][x]:
                cv.px(x + 1, y + 1, 1)
    for y in range(8):
        for x in range(8):
            if m.p[y][x]:
                if style == 0:
                    col = SMALL_ROWS[y]
                elif style == 1:
                    col = 8
                elif style == 2:
                    col = 10
                else:
                    col = 11
                cv.px(x, y, col)
    return cv


BIG_ROWS = [2, 2, 3, 3, 4, 4, 5, 5, 11, 6, 6, 7, 7, 14]


def glyph_big(ch):
    cv = Canvas(16, 16)
    g = FONT5.get(ch)
    if not g:
        return cv
    m = Canvas(16, 16)
    for y, row in enumerate(g):
        for x, c in enumerate(row):
            if c == "#":
                for oy in range(2):
                    for ox in range(3):
                        m.px(1 + x * 2 + ox, 1 + y * 2 + oy, 1)
    # italic slant for speed
    sl = Canvas(16, 16)
    for y in range(16):
        s = (14 - y) // 6
        for x in range(16):
            if m.p[y][x]:
                sl.px(x + s - 1, y, 1)
    for y in range(16):
        for x in range(16):
            if sl.p[y][x]:
                cv.px(x, y, BIG_ROWS[min(13, max(0, y - 1))])
    cv.outline(1, diag=True)
    return cv


def build_fonts():
    words = []
    n = 0
    for style in range(2):
        for ch in FONT_CHARS:
            for t in tiles4(glyph_small(ch, style)):
                words.extend(pack4(t))
            n += 1
    define("FONT_SMALL_COUNT", len(FONT_CHARS))
    # the same letters on the dark panel color, for popups drawn over the game
    define("FONT_PANEL_BASE", n)
    define("FONT_PANEL_COUNT", len(PANEL_CHARS))
    pmap = [0] * 64
    for i, ch in enumerate(PANEL_CHARS):
        pmap[ord(ch) - 32] = i
    emit_s8("panel_map", pmap)
    for style in range(2):
        for ch in PANEL_CHARS:
            for t in tiles4(glyph_small(ch, style, True)):
                words.extend(pack4(t))
            n += 1
    define("FONT_BIG_BASE", n)
    bmap = [0] * 64
    for i, ch in enumerate(BIG_CHARS):
        bmap[ord(ch) - 32] = i
    emit_s8("big_map", bmap)
    for ch in BIG_CHARS:
        cv = glyph_big(ch)
        for t in tiles4(cv):
            words.extend(pack4(t))
        n += 4
    # HUD tiles: bars (9 fill levels) in three colors, icons
    define("HUD_BASE", n)
    bar_cols = [(10, 14), (11, 6), (15, 13), (12, 13)]
    for c, cd in bar_cols:
        for f in range(9):
            cv = Canvas(8, 8)
            cv.rect(0, 1, 7, 6, 13)
            cv.rect(0, 1, 7, 1, 1)
            cv.rect(0, 6, 7, 6, 1)
            if f:
                cv.rect(0, 2, f - 1, 5, c)
                cv.rect(0, 4, f - 1, 5, cd)
                cv.rect(0, 2, f - 1, 2, 8)
            for t in tiles4(cv):
                words.extend(pack4(t))
            n += 1
    # lightning bolt icon (thunderclap charge) + empty one
    for full in (1, 0):
        cv = Canvas(8, 8)
        cv.poly([(4, 0), (7, 0), (4, 3), (6, 3), (1, 8), (3, 4), (1, 4)], 11 if full else 13)
        cv.outline(1)
        for t in tiles4(cv):
            words.extend(pack4(t))
        n += 1
    # red eye icon
    cv = Canvas(8, 8)
    cv.ellipse(3.5, 3.5, 3.5, 2.2, 8)
    cv.ellipse(3.5, 3.5, 1.6, 1.6, 10)
    cv.px(3, 3, 1)
    cv.outline(1)
    for t in tiles4(cv):
        words.extend(pack4(t))
    n += 1
    # heart icon
    cv = Canvas(8, 8)
    cv.ellipse(2, 2.5, 1.8, 1.8, 10)
    cv.ellipse(5, 2.5, 1.8, 1.8, 10)
    cv.poly([(0, 3), (7, 3), (3.5, 7)], 10)
    cv.px(2, 2, 8)
    for t in tiles4(cv):
        words.extend(pack4(t))
    n += 1
    # skull icon (boss)
    cv = Canvas(8, 8)
    cv.ellipse(3.5, 3, 3, 2.8, 8)
    cv.rect(2, 5, 5, 7, 8)
    cv.px(2, 3, 1)
    cv.px(5, 3, 1)
    cv.px(3, 6, 1)
    for t in tiles4(cv):
        words.extend(pack4(t))
    n += 1
    # solid box tile (for menu panels) and frame pieces
    cv = Canvas(8, 8, 13)
    for t in tiles4(cv):
        words.extend(pack4(t))
    n += 1
    cv = Canvas(8, 8, 13)
    cv.rect(0, 0, 7, 0, 14)
    cv.rect(0, 1, 7, 1, 10)
    for t in tiles4(cv):
        words.extend(pack4(t))
    n += 1
    cv = Canvas(8, 8, 13)
    cv.rect(0, 7, 7, 7, 14)
    cv.rect(0, 6, 7, 6, 10)
    for t in tiles4(cv):
        words.extend(pack4(t))
    n += 1
    define("HUD_BAR_HP", "(HUD_BASE + 0)")
    define("HUD_BAR_EYE", "(HUD_BASE + 9)")
    define("HUD_BAR_BOSS", "(HUD_BASE + 18)")
    define("HUD_BAR_XP", "(HUD_BASE + 27)")
    define("HUD_BOLT", "(HUD_BASE + 36)")
    define("HUD_BOLT_EMPTY", "(HUD_BASE + 37)")
    define("HUD_EYE", "(HUD_BASE + 38)")
    define("HUD_HEART", "(HUD_BASE + 39)")
    define("HUD_SKULL", "(HUD_BASE + 40)")
    define("HUD_PANEL", "(HUD_BASE + 41)")
    define("HUD_PANEL_TOP", "(HUD_BASE + 42)")
    define("HUD_PANEL_BOT", "(HUD_BASE + 43)")
    define("FONT_TILES", n)
    emit_u32("font_tiles", words)
    emit_pal("font_pal", FONT_PAL)
    sheet = Canvas(16 * 20, 16 * 4)
    for i, ch in enumerate("THE BIG GIANT ROBOT 0123456789!"):
        sheet.paste(glyph_big(ch), (i % 20) * 13, (i // 20) * 16)
    for i, ch in enumerate("LEVEL 1 HP SPIKE GUY YOU DESTROYED THE WORLD"):
        sheet.paste(glyph_small(ch, 0), i * 7, 40)
    preview("font.png", sheet, FONT_PAL, 3)


# ---------------------------------------------------------------- level backgrounds

GROUND_Y = 152
LW = 512


def draw_far():
    cv = Canvas(LW, 160)
    rnd = random.Random(21)
    # jagged mountains, wrapping
    pts = []
    x = 0
    h = 60
    while x <= LW:
        pts.append((x, h))
        x += rnd.randint(10, 26)
        h = max(20, min(78, h + rnd.randint(-24, 24)))
    pts[-1] = (LW, pts[0][1])
    for i in range(len(pts) - 1):
        (xa, ha), (xb, hb) = pts[i], pts[i + 1]
        for xx in range(xa, xb + 1):
            hh = ha + (hb - ha) * (xx - xa) / max(1, xb - xa)
            top = 140 - hh
            for yy in range(int(top), 150):
                cv.px(xx % LW, yy, 1)
            cv.px(xx % LW, int(top), 3)
            if hb > ha:
                cv.px(xx % LW, int(top) + 1, 2)
    # second, nearer range
    pts = []
    x = 0
    h = 30
    while x <= LW:
        pts.append((x, h))
        x += rnd.randint(14, 34)
        h = max(10, min(46, h + rnd.randint(-16, 16)))
    pts[-1] = (LW, pts[0][1])
    for i in range(len(pts) - 1):
        (xa, ha), (xb, hb) = pts[i], pts[i + 1]
        for xx in range(xa, xb + 1):
            hh = ha + (hb - ha) * (xx - xa) / max(1, xb - xa)
            top = 146 - hh
            for yy in range(int(top), 150):
                cv.px(xx % LW, yy, 2)
            cv.px(xx % LW, int(top), 4)
    return cv


def draw_mid():
    cv = Canvas(LW, 160)
    rnd = random.Random(5)
    x = 0
    base = 144
    while x < LW:
        w = rnd.choice([24, 32, 32, 40, 48])
        if x + w > LW:
            w = LW - x
        hgt = rnd.choice([40, 48, 56, 64, 72, 80, 88, 96])
        top = base - hgt
        top = (top // 8) * 8
        broken = rnd.random() < 0.35
        cv.rect(x, top, x + w - 1, base, 2)
        cv.rect(x, top, x, base, 4)
        cv.rect(x + w - 1, top, x + w - 1, base, 1)
        cv.rect(x, top, x + w - 1, top, 4)
        # windows: 2x3 every 4 px across, every 8 px down
        for wy in range(top + 3, base - 6, 8):
            for wx in range(x + 2, x + w - 3, 4):
                v = rnd.random()
                c = 6 if v < 0.3 else 7 if v < 0.38 else 5
                cv.rect(wx, wy, wx + 1, wy + 2, c)
        if broken:
            # jagged broken top with fire
            for xx in range(x, x + w):
                dd = rnd.randint(0, 10)
                for yy in range(top, top + dd):
                    cv.px(xx, yy, 0)
                if dd:
                    cv.px(xx, top + dd, 3)
            fx = x + w // 2
            for i in range(14):
                ox = rnd.randint(-w // 3, w // 3)
                fh = rnd.randint(4, 14)
                cv.poly([(fx + ox - 3, top + 9), (fx + ox + 3, top + 9), (fx + ox + rnd.randint(-2, 2), top + 9 - fh)],
                        8 if i % 3 == 0 else 9)
            for i in range(5):
                ox = rnd.randint(-w // 4, w // 4)
                cv.poly([(fx + ox - 1, top + 9), (fx + ox + 2, top + 9), (fx + ox, top + 2)], 10)
        else:
            if rnd.random() < 0.5:
                ax = x + rnd.randint(4, w - 5)
                ah = rnd.randint(8, 18)
                cv.rect(ax, top - ah, ax, top, 3)
                cv.px(ax, top - ah - 1, 11)
            if rnd.random() < 0.3:
                tx = x + 4
                cv.rect(tx, top - 8, tx + 8, top - 3, 3)
                cv.rect(tx + 1, top - 3, tx + 1, top, 1)
                cv.rect(tx + 7, top - 3, tx + 7, top, 1)
        x += w + rnd.choice([0, 0, 8])
    return cv


def draw_near():
    cv = Canvas(LW, 160)
    rnd = random.Random(9)
    # sidewalk + curb + road
    cv.rect(0, 138, LW - 1, 145, 6)
    cv.rect(0, 138, LW - 1, 138, 7)
    for x in range(0, LW, 16):
        cv.rect(x, 139, x, 145, 5)
    cv.rect(0, 146, LW - 1, 148, 5)
    cv.rect(0, 146, LW - 1, 146, 7)
    cv.rect(0, 149, LW - 1, 159, 2)
    for x in range(0, LW, 32):
        cv.rect(x + 4, 154, x + 19, 155, 4)
    for i in range(300):
        cv.px(rnd.randrange(LW), rnd.randrange(150, 160), 3 if rnd.random() < 0.6 else 1)
    # cracks
    for i in range(10):
        x = rnd.randrange(LW)
        y = 151
        for s in range(6):
            nx, ny = x + rnd.randint(-3, 3), y + rnd.randint(1, 2)
            cv.line(x, y, nx, ny, 1)
            x, y = nx, ny
    # lamp posts and rubble on the sidewalk
    for lx in range(40, LW, 128):
        cv.rect(lx, 96, lx + 1, 139, 11)
        cv.rect(lx + 2, 96, lx + 10, 97, 11)
        cv.rect(lx + 7, 98, lx + 11, 99, 12)
        cv.rect(lx - 1, 137, lx + 2, 139, 1)
    for i in range(8):
        rx = rnd.randrange(8, LW - 16)
        for j in range(5):
            ox = rx + rnd.randint(0, 10)
            sz = rnd.randint(1, 3)
            cv.ellipse(ox, 137 - sz // 2, sz + 1, sz, 9)
            cv.px(ox - 1, 136 - sz, 10)
    return cv


THEMES = [
    dict(name="BURNING CITY", sky=["#1a0628", "#5a1440", "#c03a20", "#ff9030"],
         far=["#2a1030", "#40183a", "#6a2a44", "#ff6020"],
         mid=["#0c0810", "#241c2a", "#3a2e40", "#56485c", "#2a2018", "#ffc040", "#fff0a0", "#d02010", "#ff7010",
              "#ffd030", "#ff2020", "#504048"],
         near=["#100c10", "#2c282e", "#45404a", "#d0a020", "#4a4048", "#6e6470", "#9a8e9a", "#3a2a24", "#5a4434",
               "#7a604a", "#30303a", "#ffe080"]),
    dict(name="NIGHT STORM", sky=["#000004", "#04081c", "#0c1c40", "#203c70"],
         far=["#060a18", "#0c1428", "#1c2c50", "#4a6ab0"],
         mid=["#020208", "#0e1222", "#1a2036", "#2c3654", "#101420", "#40d0ff", "#c0f8ff", "#2040c0", "#4080ff",
              "#a0e0ff", "#ff2020", "#283040"],
         near=["#04060c", "#181c26", "#2a3040", "#c0c8d8", "#283040", "#3e4860", "#5a6a88", "#1a1e28", "#2e3444",
               "#46506a", "#202838", "#e0f0ff"]),
    dict(name="WASTELAND", sky=["#3a1a08", "#7a3a10", "#c07a28", "#f0c060"],
         far=["#5a2c10", "#7a4018", "#a05a24", "#ffb040"],
         mid=["#140a04", "#3a2414", "#54361e", "#74502c", "#2a1a0c", "#ff9020", "#ffe0a0", "#c02000", "#ff6000",
              "#ffc020", "#ff3010", "#6a5040"],
         near=["#180e06", "#4a3420", "#68482c", "#e0b040", "#5a3c20", "#80583a", "#a8805a", "#40281a", "#6a4a2c",
               "#8e6a44", "#3a2a1c", "#ffe090"]),
    dict(name="STEEL FACTORY", sky=["#060c08", "#10241a", "#2a5a34", "#80c060"],
         far=["#0c1810", "#142a1a", "#22402a", "#80ff60"],
         mid=["#040806", "#18221c", "#26342a", "#3a4c3e", "#141c16", "#a0ff40", "#e0ffb0", "#20a020", "#60e030",
              "#d0ff60", "#ffe020", "#304034"],
         near=["#060a08", "#222a24", "#343e36", "#e0d020", "#2c362e", "#46524a", "#64746a", "#1c241e", "#2e3a30",
               "#46564a", "#26302a", "#e0ff90"]),
    dict(name="ICE AGE", sky=["#0a1830", "#24508a", "#7ab0e0", "#d8f0ff"],
         far=["#4a6a98", "#7090c0", "#e8f4ff", "#ffffff"],
         mid=["#0a1424", "#24406a", "#36588a", "#9ac4f0", "#1a2c48", "#80e8ff", "#e8ffff", "#40a0ff", "#80d0ff",
              "#e0f8ff", "#ff4040", "#c0d8f0"],
         near=["#101c2c", "#8aa4c4", "#c8dcf0", "#ffffff", "#5a7898", "#b8d0e8", "#f0f8ff", "#6a88a8", "#a0bcd8",
               "#e8f4ff", "#405870", "#fff4c0"]),
    dict(name="NEON NIGHTS", sky=["#08001a", "#2a0050", "#7a0090", "#ff3aa0"],
         far=["#1a0030", "#2a0048", "#5a1080", "#ff40c0"],
         mid=["#06000e", "#1a0a2e", "#2a1444", "#ff40c0", "#140820", "#40f0ff", "#ffffff", "#ff2080", "#ff60e0",
              "#ffe0ff", "#40ff80", "#3a2050"],
         near=["#06000c", "#1a1028", "#2c1c40", "#40f0ff", "#2a1440", "#ff40c0", "#ff90e0", "#201030", "#3a2050",
               "#5a3070", "#30204a", "#80ffff"]),
    dict(name="HELLFIRE", sky=["#000000", "#200000", "#600808", "#c02010"],
         far=["#100000", "#200404", "#3a0a0a", "#ff3010"],
         mid=["#000000", "#140808", "#221010", "#341a1a", "#100606", "#ff3010", "#ffb060", "#ff2000", "#ff7000",
              "#ffe040", "#ff1010", "#3a1a1a"],
         near=["#000000", "#201010", "#341818", "#ff6010", "#2a1010", "#441c1c", "#602828", "#ff3000", "#ff8020",
               "#ffd040", "#401818", "#ffa040"]),
]


def build_levels():
    ts = TileSet()
    far, mid, near = draw_far(), draw_mid(), draw_near()
    maps = []
    for cv, bank in ((far, 1), (mid, 2), (near, 3)):
        full = Canvas(LW, 256)
        full.paste(cv)
        ents = ts.map_canvas(full, bank)
        # GBA 64x32 map = two 32x32 screenblocks side by side
        sb = []
        for half in range(2):
            for ty in range(32):
                for tx in range(32):
                    sb.append(ents[ty * 64 + half * 32 + tx])
        maps.append(sb)
    emit_u16("map_far", maps[0])
    emit_u16("map_mid", maps[1])
    emit_u16("map_near", maps[2])
    words = []
    for t in ts.tiles:
        words.extend(pack4(list(t)))
    emit_u32("level_tiles", words)
    define("LEVEL_TILE_COUNT", len(ts.tiles))
    print("level tiles:", len(ts.tiles))
    pals = []
    skies = []
    for th in THEMES:
        for key in ("far", "mid", "near"):
            cols = [(0, 0, 0)] + [H(c) for c in th[key]]
            cols += [(0, 0, 0)] * (16 - len(cols))
            pals.extend(g15(c) for c in cols)
        skies.extend(g15(H(c)) for c in th["sky"])
    emit_u16("theme_pals", pals)
    emit_u16("theme_sky", skies)
    define("THEME_COUNT", len(THEMES))
    names = ", ".join('"%s"' % t["name"] for t in THEMES)
    C_OUT.append("const char* const theme_names[%d] = { %s };\n" % (len(THEMES), names))
    H_OUT.append("extern const char* const theme_names[%d];" % len(THEMES))
    # preview: each theme
    for ti, th in enumerate(THEMES):
        img = Image.new("RGB", (LW, 160))
        sky = [H(c) for c in th["sky"]]
        for y in range(160):
            t = y / 159 * 3
            i = min(2, int(t))
            sc = mix(sky[i], sky[i + 1], t - i)
            for x in range(LW):
                c = sc
                for cv, key in ((far, "far"), (mid, "mid"), (near, "near")):
                    v = cv.p[y][x]
                    if v:
                        c = H(th[key][v - 1])
                img.putpixel((x, y), c)
        img.resize((LW * 2, 320), Image.NEAREST).save(os.path.join(ART, "level_%d.png" % ti))


# ---------------------------------------------------------------- full screens (8bpp)

def big_text_rgb(img, text, x, y, sc, grad, outline=(0, 0, 0), glow=None, italic=True, spacing=1):
    """Draw chrome/fire gradient text scaled sc onto an RGB image. Returns width."""
    w = len(text) * (6 * sc + spacing)
    mask = {}
    cx = 0
    for ch in text:
        g = FONT5.get(ch)
        if g:
            for gy, row in enumerate(g):
                for gx, c in enumerate(row):
                    if c == "#":
                        for oy in range(sc):
                            for ox in range(sc + max(1, sc // 2)):
                                py = gy * sc + oy
                                sl = ((7 * sc - py) * sc // 10) // 2 if italic else 0
                                mask[(cx + gx * sc + ox + sl, py)] = 1
        cx += 6 * sc + spacing
    hgt = 7 * sc
    ring = []
    for r in ((glow or 0) and 3 or 0, 2, 1):
        pass
    pts = set(mask)
    o1 = set()
    for (px, py) in pts:
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                q = (px + ox, py + oy)
                if q not in pts:
                    o1.add(q)
    o2 = set()
    for (px, py) in o1:
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                q = (px + ox, py + oy)
                if q not in pts and q not in o1:
                    o2.add(q)
    W, Ht = img.size
    if glow:
        for (px, py) in o2:
            if 0 <= x + px < W and 0 <= y + py < Ht:
                img.putpixel((x + px, y + py), glow)
    for (px, py) in o1:
        if 0 <= x + px < W and 0 <= y + py < Ht:
            img.putpixel((x + px, y + py), outline)
    for (px, py) in pts:
        t = py / max(1, hgt - 1)
        n = len(grad) - 1
        i = min(n - 1, int(t * n))
        c = mix(grad[i], grad[i + 1], t * n - i)
        if 0 <= x + px < W and 0 <= y + py < Ht:
            img.putpixel((x + px, y + py), c)
    return cx


CHROME_FIRE = [H("#ffffff"), H("#d0d6e0"), H("#7a8494"), H("#ffffff"), H("#ffd040"), H("#ff6a10"), H("#a80c0c")]
CHROME = [H("#ffffff"), H("#c8d0dc"), H("#6a7484"), H("#e8eef8"), H("#9aa4b4"), H("#4a5260")]
LAVA_TEXT = [H("#ffffff"), H("#ffe8a0"), H("#ffb030"), H("#ff5010"), H("#c01008"), H("#600404")]


def text_width(text, sc, spacing=1):
    return len(text) * (6 * sc + spacing)


def flames_rgb(img, y0, y1, seed, cols):
    rnd = random.Random(seed)
    W = img.size[0]
    for i in range(160):
        x = rnd.uniform(-10, W + 10)
        h = rnd.uniform(10, y1 - y0)
        w = rnd.uniform(5, 14)
        for layer, (c, f) in enumerate(cols):
            hh = h * f
            ww = w * f
            for yy in range(int(y1 - hh), y1):
                t = (y1 - yy) / hh
                half = ww * (1 - t) * (0.6 + 0.4 * math.sin(t * 6 + x))
                for xx in range(int(x - half), int(x + half) + 1):
                    if 0 <= xx < W and 0 <= yy < img.size[1]:
                        img.putpixel((xx, yy), c)


def robot_rgb(img, cv, gl, anchor, ox, oy, scale=1, glasses_up=0):
    for y in range(cv.h):
        for x in range(cv.w):
            v = cv.p[y][x]
            if v:
                for sy in range(scale):
                    for sx in range(scale):
                        img.putpixel((ox + x * scale + sx, oy + y * scale + sy), ROBOT_PAL[v])
    for y in range(gl.h):
        for x in range(gl.w):
            v = gl.p[y][x]
            if v:
                for sy in range(scale):
                    for sx in range(scale):
                        img.putpixel((ox + (anchor[0] + x) * scale + sx,
                                      oy + (anchor[1] + y - glasses_up) * scale + sy), ROBOT_PAL[v])


def screen_title(robot_frames, anchors, gl):
    W, Hh = 240, 160
    img = Image.new("RGB", (W, Hh))
    top, bot = H("#000000"), H("#5a0808")
    for y in range(Hh):
        c = mix(top, bot, (y / Hh) ** 1.6)
        for x in range(W):
            img.putpixel((x, y), c)
    # lightning
    rnd = random.Random(4)
    for bx in (30, 200):
        x, y = bx, 0
        while y < 110:
            nx, ny = x + rnd.randint(-8, 8), y + rnd.randint(6, 14)
            for t in range(20):
                px = int(x + (nx - x) * t / 20)
                py = int(y + (ny - y) * t / 20)
                for o in (-1, 0, 1):
                    if 0 <= px + o < W and 0 <= py < Hh:
                        img.putpixel((px + o, py), H("#8080ff") if o else H("#ffffff"))
            x, y = nx, ny
    # skyline silhouette
    rnd = random.Random(8)
    x = 0
    while x < W:
        w = rnd.randint(12, 30)
        h = rnd.randint(20, 60)
        for yy in range(Hh - 20 - h, Hh):
            for xx in range(x, min(W, x + w)):
                img.putpixel((xx, yy), H("#140608"))
        for wy in range(Hh - 18 - h, Hh - 24, 6):
            for wx in range(x + 2, min(W, x + w) - 2, 4):
                if rnd.random() < 0.3:
                    img.putpixel((wx, wy), H("#ff9030"))
        x += w
    flames_rgb(img, 100, 160, 3, [(H("#a01008"), 1.0), (H("#ff5010"), 0.7), (H("#ffc030"), 0.4)])
    # ground
    for y in range(148, 160):
        for x in range(W):
            img.putpixel((x, y), H("#100808") if y > 149 else H("#3a1a14"))
    # the robot, big
    robot_rgb(img, robot_frames[0], gl, anchors[0], 120 - 31, 148 - 96 + 2)
    # title text
    t1 = "THE BIG"
    w1 = text_width(t1, 2)
    big_text_rgb(img, t1, (W - w1) // 2 + 2, 4, 2, CHROME, outline=H("#000000"), glow=H("#600000"))
    t2 = "GIANT ROBOT"
    w2 = text_width(t2, 3, 1)
    big_text_rgb(img, t2, (W - w2) // 2 + 3, 22, 3, CHROME_FIRE, outline=H("#000000"), glow=H("#ff3010"))
    return img


def screen_lava():
    W, Hh = 240, 160
    img = Image.new("RGB", (W, Hh))
    lava = {}
    for y in range(Hh):
        c = mix(H("#200000"), H("#ff4010"), (y / 70) ** 1.2) if y < 70 else H("#ff4010")
        for x in range(W):
            img.putpixel((x, y), mix(H("#100000"), H("#6a0c04"), min(1, y / 75)))
    # smoke clouds in the sky
    rnd = random.Random(12)
    for i in range(70):
        cx, cy = rnd.uniform(0, W), rnd.uniform(0, 55)
        r = rnd.uniform(6, 16)
        col = mix(H("#1a0806"), H("#4a1408"), rnd.random())
        for y in range(int(cy - r), int(cy + r)):
            for x in range(int(cx - r * 1.6), int(cx + r * 1.6)):
                if 0 <= x < W and 0 <= y < Hh and ((x - cx) / 1.6) ** 2 + (y - cy) ** 2 < r * r:
                    img.putpixel((x, y), col)
    # the lava field: dark rock plates with glowing cracks and rivers (cycled palette band)
    for y in range(70, Hh):
        for x in range(W):
            img.putpixel((x, y), H("#1a0a08"))
    rnd = random.Random(2)
    plates = []
    for i in range(90):
        px_ = rnd.uniform(-10, W + 10)
        py_ = rnd.uniform(72, Hh + 6)
        plates.append((px_, py_))
    for y in range(70, Hh):
        persp = (y - 64) / 96
        for x in range(W):
            best, second = 1e9, 1e9
            for (px_, py_) in plates:
                d = ((x - px_) * 0.6) ** 2 + ((y - py_) / max(0.25, persp)) ** 2 * 0.4
                if d < best:
                    best, second = d, best
                elif d < second:
                    second = d
            edge = math.sqrt(second) - math.sqrt(best)
            if edge < 1.6 + 2.2 * persp:
                lava[(x, y)] = int((x * 0.35 + y * 0.9 + edge * 3)) % 12
            else:
                shade_ = min(1, edge / 12)
                img.putpixel((x, y), mix(H("#3a1810"), H("#120604"), shade_))
    # volcanoes on the horizon
    for vx, vh in ((40, 34), (190, 44)):
        for y in range(70 - vh, 71):
            half = (y - (70 - vh)) * 1.4 + 3
            for x in range(int(vx - half), int(vx + half)):
                if 0 <= x < W:
                    img.putpixel((x, y), H("#200806"))
                    lava.pop((x, y), None)
        for i in range(30):
            ang = rnd.uniform(-2.6, -0.5)
            r = rnd.uniform(4, 22)
            x, y = int(vx + math.cos(ang) * r), int(70 - vh + math.sin(ang) * r)
            if 0 <= x < W and 0 <= y < Hh:
                lava[(x, y)] = rnd.randrange(12)
    big_text_rgb(img, "YOU DESTROYED", (W - text_width("YOU DESTROYED", 2)) // 2 + 2, 12, 2, LAVA_TEXT,
                 outline=H("#000000"), glow=H("#ff2000"))
    big_text_rgb(img, "THE WORLD", (W - text_width("THE WORLD", 3)) // 2 + 3, 34, 3, LAVA_TEXT,
                 outline=H("#000000"), glow=H("#ff2000"))
    return img, lava


def screen_win(robot_frames, anchors, gl):
    W, Hh = 240, 160
    img = Image.new("RGB", (W, Hh))
    for y in range(Hh):
        c = mix(H("#10184a"), H("#ff9a40"), (y / Hh) ** 1.3)
        for x in range(W):
            img.putpixel((x, y), c)
    # sun rays
    for x in range(W):
        for y in range(60, 150):
            a = math.atan2(y - 150, x - 120)
            if int((a * 18) % 2) == 0:
                img.putpixel((x, y), mix(img.getpixel((x, y)), H("#ffe0a0"), 0.25))
    rnd = random.Random(14)
    # fireworks
    for i in range(7):
        cx, cy = rnd.uniform(15, 225), rnd.uniform(56, 90)
        col = rnd.choice([H("#ffe040"), H("#40e0ff"), H("#ff60c0"), H("#80ff60")])
        for k in range(18):
            a = k / 18 * 6.283
            for r in range(3, 13):
                if r % 2 == 0:
                    x, y = int(cx + math.cos(a) * r), int(cy + math.sin(a) * r)
                    if 0 <= x < W and 0 <= y < Hh:
                        img.putpixel((x, y), col)
    for y in range(148, 160):
        for x in range(W):
            img.putpixel((x, y), H("#2a1a20"))
    robot_rgb(img, robot_frames[15], gl, anchors[15], 120 - 31, 148 - 96 + 2)
    big_text_rgb(img, "YOU SAVED", (W - text_width("YOU SAVED", 2)) // 2 + 2, 6, 2, CHROME, glow=H("#203080"))
    big_text_rgb(img, "THE WORLD!", (W - text_width("THE WORLD!", 3)) // 2 + 3, 26, 3, CHROME_FIRE,
                 glow=H("#ff3010"))
    return img


def screen_to_tiles(name, img, lava=None, lava_ramp=None):
    """RGB image -> 8bpp tiles + 32x32 map + palette. Colors 1..223; lava band at the end of that range."""
    W, Hh = img.size
    nl = len(lava_ramp) if lava_ramp else 0
    limit = 223 - nl
    q = img.quantize(colors=limit, method=Image.MEDIANCUT, dither=Image.NONE)
    qp = q.getpalette()[:limit * 3]
    qp += [0] * (limit * 3 - len(qp))
    pal = [(0, 0, 0)] + [tuple(qp[i * 3:i * 3 + 3]) for i in range(limit)]
    idx = Canvas(W, Hh)
    qd = list(q.get_flattened_data()) if hasattr(q, 'get_flattened_data') else list(q.getdata())
    src = img.load()
    for y in range(Hh):
        for x in range(W):
            idx.p[y][x] = 0 if src[x, y] == CLEAR else qd[y * W + x] + 1
    lava_base = len(pal)
    if lava:
        for (x, y), band in lava.items():
            idx.p[y][x] = lava_base + band
        pal += lava_ramp
    ts = TileSet()
    full = Canvas(256, 256)
    full.paste(idx)
    ents = ts.map_canvas(full, 0)
    words = []
    for t in ts.tiles:
        words.extend(pack8(list(t)))
    emit_u32(name + "_tiles", words)
    emit_u16(name + "_map", ents[:32 * 20])
    pal += [(0, 0, 0)] * (224 - len(pal))
    emit_u16(name + "_pal", [g15(c) for c in pal[:224]])
    if lava:
        define(name.upper() + "_LAVA_BASE", lava_base)
    print(name, "tiles:", len(ts.tiles))
    img2 = Image.new("RGB", (W, Hh))
    for y in range(Hh):
        for x in range(W):
            v = idx.p[y][x]
            img2.putpixel((x, y), pal[v])
    img2.resize((W * 3, Hh * 3), Image.NEAREST).save(os.path.join(ART, name + ".png"))


LAVA_RAMP = [H(c) for c in ["#ff2000", "#ff4808", "#ff7010", "#ff9818", "#ffc030", "#fff080", "#ffc030",
                            "#ff9818", "#ff7010", "#ff4808", "#e01800", "#c01000"]]


# ---------------------------------------------------------------- cutscenes (intro and ending)

CLEAR = (255, 0, 255)   # in a picture: transparent (the backdrop gradient shows through)

INTRO_PAL = [(0, 0, 0), H("#1a1010"), H("#f4cca4"), H("#d8a07a"), H("#c88c5c"), H("#a06a40"), H("#7a4a2a"),
             H("#56321a"), H("#1c1c24"), H("#6a3a18"), H("#e8c040"), H("#c84818"), H("#ffffff"), H("#7a1414"),
             H("#101018"), H("#60a0ff")]
HEADS = [((2, 3), 8), ((4, 5), 9), ((6, 7), 8), ((2, 3), 10), ((4, 5), 11), ((6, 7), 9)]


def head(skin, hair, face):
    cv = Canvas(16, 16)
    part(cv, (skin[1], skin[1], skin[0], skin[0]), lambda m: m.ellipse(8, 9, 5.5, 5.5, 1))
    # hair cap
    hc = Canvas(16, 16)
    hc.ellipse(8, 7, 6, 4.5, 1)
    for y in range(16):
        for x in range(16):
            if hc.p[y][x] and y <= 7 + (1 if x in (3, 4, 12, 13) else 0):
                cv.px(x, y, hair)
    cv.outline(1)
    if face == "scared":
        for ex in (6, 10):
            cv.rect(ex - 1, 8, ex, 10, 12)
            cv.px(ex, 9, 14)
        cv.px(4, 7, 1); cv.px(5, 6, 1); cv.px(11, 6, 1); cv.px(12, 7, 1)   # eyebrows up
        cv.rect(7, 12, 9, 14, 13)
        cv.px(8, 12, 1)
        cv.px(13, 9, 15); cv.px(13, 10, 15)                                 # sweat
    else:
        for ex in (6, 10):
            cv.px(ex - 1, 9, 1); cv.px(ex, 8, 1); cv.px(ex + 1, 9, 1)         # happy closed eyes
        cv.rect(6, 12, 10, 12, 1)
        cv.rect(6, 12, 10, 13, 13)
        cv.rect(7, 12, 9, 12, 12)
        cv.px(4, 11, 13); cv.px(12, 11, 13)                                 # cheeks
    return cv


def asteroid(v):
    cv = Canvas(16, 16)
    # flame tail toward the upper right
    for i in range(9):
        t = i / 8
        x, y = 8 + 7 * t, 8 - 7 * t
        r = 3.6 * (1 - t) + 0.6
        col = 10 if t < 0.35 else 9 if t < 0.7 else 8
        if v and t > 0.5:
            x += 1
        cv.ellipse(x, y, r, r, col)
    part(cv, (12, 12, 13, 13), lambda m: m.ellipse(6, 10, 4, 3.6, 1))
    cv.px(5, 9, 12); cv.px(7, 11, 12)
    cv.px(4, 8, 11)
    return cv


def kira(v):
    cv = Canvas(16, 16)
    r = 5 if v == 0 else 7
    for i in range(-r, r + 1):
        w = 0 if abs(i) > r // 2 else 1
        cv.rect(8 + i, 8 - w, 8 + i, 8 + w, 7 if abs(i) > 2 else 11)
        cv.rect(8 - w, 8 + i, 8 + w, 8 + i, 7 if abs(i) > 2 else 11)
    cv.rect(7, 7, 9, 9, 11)
    if v:
        for d in (-3, 3):
            cv.px(8 + d, 8 + d, 7); cv.px(8 + d, 8 - d, 7)
    return cv


def firework(f):
    """32x32 burst in enemy-palette indices: 4/5 (that palette's suit color) and 9 (pale yellow)."""
    cv = Canvas(32, 32)
    r = [4, 8, 12, 14][f]
    n = 14
    drop = f * f * 0.4
    for k in range(n):
        a = k / n * 6.283
        x, y = 16 + math.cos(a) * r, 15 + math.sin(a) * r + drop
        if f < 3:
            cv.rect(x - 1, y - 1, x, y, 9 if f < 2 else 5)          # bright head
        else:
            cv.px(x, y, 4)
        for tr in (1, 2) if f < 3 else ():
            rr = r - tr * 2.5
            if rr > 1:
                cv.px(16 + math.cos(a) * rr, 15 + math.sin(a) * rr + drop * 0.6, 5 if tr == 1 else 4)
    if f == 0:
        cv.rect(14, 13, 17, 16, 9)
    return cv


def build_cutscene_sprites():
    words = []
    for (skin, hair) in HEADS:
        for face in ("scared", "happy"):
            for t in tiles4(head(skin, hair, face)):
                words.extend(pack4(t))
    define("CS_HEAD", 0)            # 6 heads x (scared, happy), 4 tiles each
    base = len(words) // 8
    define("CS_ROCK", base)
    for v in range(2):
        for t in tiles4(asteroid(v)):
            words.extend(pack4(t))
    define("CS_KIRA", len(words) // 8)
    for v in range(2):
        for t in tiles4(kira(v)):
            words.extend(pack4(t))
    define("CS_BURST", len(words) // 8)
    for f in range(4):
        for t in tiles4(firework(f)):
            words.extend(pack4(t))
    emit_u32("cs_tiles", words)
    define("CS_TILE_COUNT", len(words) // 8)
    emit_u16("intro_pal", [g15(c) for c in INTRO_PAL])
    # preview
    sheet = Image.new("RGB", (16 * 12, 16 + 32))
    for i, (skin, hair) in enumerate(HEADS):
        for j, face in enumerate(("scared", "happy")):
            cv = head(skin, hair, face)
            for y in range(16):
                for x in range(16):
                    v = cv.p[y][x]
                    sheet.putpixel((i * 32 + j * 16 + x, y), INTRO_PAL[v] if v else (60, 0, 60))
    for i, cv in enumerate([asteroid(0), asteroid(1), kira(0), kira(1)]):
        for y in range(16):
            for x in range(16):
                v = cv.p[y][x]
                sheet.putpixel((i * 16 + x, 16 + y), FX_PAL[v] if v else (60, 0, 60))
    pal = enemy_pal("#3a66d0")
    for f in range(4):
        cv = firework(f)
        for y in range(32):
            for x in range(32):
                v = cv.p[y][x]
                if 64 + f * 32 + x < sheet.size[0]:
                    sheet.putpixel((64 + f * 32 + x, 16 + y), pal[v] if v else (20, 0, 20))
    sheet.resize((sheet.size[0] * 4, sheet.size[1] * 4), Image.NEAREST).save(os.path.join(ART, "cutscene_sprites.png"))


def sky_rgb(img, cols, y1=None):
    W, Hh = img.size
    y1 = y1 or Hh
    n = len(cols) - 1
    for y in range(y1):
        t = y / max(1, y1 - 1) * n
        i = min(n - 1, int(t))
        c = mix(cols[i], cols[i + 1], t - i)
        for x in range(W):
            img.putpixel((x, y), c)


def smoke_rgb(img, seed, n, y0, y1, c0, c1):
    rnd = random.Random(seed)
    W, Hh = img.size
    for i in range(n):
        cx, cy = rnd.uniform(0, W), rnd.uniform(y0, y1)
        r = rnd.uniform(6, 15)
        col = mix(c0, c1, rnd.random())
        for y in range(int(cy - r), int(cy + r)):
            for x in range(int(cx - r * 1.7), int(cx + r * 1.7)):
                if 0 <= x < W and 0 <= y < Hh and ((x - cx) / 1.7) ** 2 + (y - cy) ** 2 < r * r:
                    img.putpixel((x, y), col)


def skyline_rgb(img, seed, base, hmin, hmax, body, win, ruined=False, wchance=0.3):
    rnd = random.Random(seed)
    W, Hh = img.size
    x = -4
    while x < W:
        w = rnd.randint(12, 28)
        h = rnd.randint(hmin, hmax)
        top = base - h
        for xx in range(max(0, x), min(W, x + w)):
            t = top
            if ruined:
                t = top + int(abs(math.sin((xx - x) * 0.7 + x)) * 6 + (xx - x) % 5)
            for yy in range(t, base):
                img.putpixel((xx, yy), body)
        for wy in range(top + 4, base - 4, 6):
            for wx in range(x + 3, min(W, x + w) - 2, 4):
                if 0 <= wx < W and rnd.random() < wchance:
                    img.putpixel((wx, wy), win)
                    if wx + 1 < W:
                        img.putpixel((wx + 1, wy), win)
        x += w + rnd.randint(0, 3)


def screen_intro_city():
    W, Hh = 240, 160
    img = Image.new("RGB", (W, Hh))
    sky_rgb(img, [H("#060000"), H("#3a0404"), H("#a01808"), H("#ff6010")], 120)
    smoke_rgb(img, 21, 40, 40, 100, H("#1a0806"), H("#4a140a"))
    # falling fireballs streaking across the sky
    rnd = random.Random(5)
    for i in range(5):
        x0, y0 = rnd.uniform(60, 240), rnd.uniform(40, 70)
        for k in range(26):
            x, y = x0 - k * 1.6, y0 + k * 1.1
            c = mix(H("#fff0a0"), H("#a01808"), k / 26)
            if 0 <= int(x) < W and 0 <= int(y) < Hh:
                img.putpixel((int(x), int(y)), c)
    skyline_rgb(img, 3, 128, 25, 70, H("#160406"), H("#ff9030"), ruined=True)
    flames_rgb(img, 80, 128, 9, [(H("#a01008"), 1.0), (H("#ff5010"), 0.7), (H("#ffd040"), 0.4)])
    for y in range(128, Hh):
        for x in range(W):
            img.putpixel((x, y), mix(H("#2a0c08"), H("#0a0404"), (y - 128) / 32))
    rnd = random.Random(7)
    for i in range(40):   # rubble
        x, y = rnd.randrange(W), rnd.randrange(130, Hh)
        img.putpixel((x, y), H("#4a2018"))
    return img


def screen_earth():
    W, Hh = 240, 160
    img = Image.new("RGB", (W, Hh))
    rnd = random.Random(31)
    for i in range(70):
        x, y = rnd.randrange(W), rnd.randrange(Hh)
        img.putpixel((x, y), rnd.choice([H("#ffffff"), H("#8890b0"), H("#c0c8ff")]))
    cx, cy, R = 120, 150, 78
    for y in range(int(cy - R - 4), Hh):
        for x in range(W):
            d = math.hypot(x - cx, y - cy)
            if d <= R:
                nx, ny = (x - cx) / R, (y - cy) / R
                nz = math.sqrt(max(0, 1 - nx * nx - ny * ny))
                light = max(0.15, -0.55 * nx - 0.6 * ny + 0.55 * nz)
                # continents from a few blobs
                land = 0
                for (bx, by, br) in ((-0.4, -0.5, 0.35), (0.2, -0.75, 0.25), (0.5, -0.3, 0.3), (-0.1, -0.2, 0.18)):
                    if math.hypot(nx - bx + 0.08 * math.sin(ny * 9), ny - by) < br:
                        land = 1
                swirl = math.sin(nx * 6 + math.sin(ny * 9 + nx * 4) * 1.8 + ny * 3)
                cloud = swirl > 0.82 or (math.sin(ny * 21 + nx * 2) > 0.93 and land == 0)
                c = H("#2a9a3a") if land else H("#1a4aa8")
                if land and nx > 0.45 and ny > -0.45:
                    c = H("#9a7a3a")
                if cloud:
                    c = H("#e8f0ff")
                img.putpixel((x, y), mul(c, min(1.2, light)))
            elif d <= R + 3:
                img.putpixel((x, y), mix(H("#60a0ff"), img.getpixel((x, y)), (d - R) / 3))
    return img


PYLONS = ((26, 24), (214, 24))       # tower tops; the cables run from here to the robot's shoulders
CABLE_ENDS = ((84, 92), (156, 92))


def screen_power():
    W, Hh = 240, 160
    img = Image.new("RGB", (W, Hh))
    sky_rgb(img, [H("#02030c"), H("#0a1236"), H("#1a2a5a")], 130)
    rnd = random.Random(41)
    for i in range(50):
        x, y = rnd.randrange(W), rnd.randrange(100)
        img.putpixel((x, y), rnd.choice([H("#ffffff"), H("#8890c0")]))
    # hills
    for x in range(W):
        h = int(118 + 6 * math.sin(x * 0.03) + 4 * math.sin(x * 0.11))
        for y in range(h, 132):
            img.putpixel((x, y), H("#0a1020"))
    for y in range(130, Hh):
        for x in range(W):
            img.putpixel((x, y), mix(H("#141a26"), H("#06080c"), (y - 130) / 30))
    # lattice towers
    for (tx, ty) in PYLONS:
        for y in range(ty, 140):
            half = 2 + (y - ty) * 0.14
            for xx in (int(tx - half), int(tx + half)):
                img.putpixel((xx, y), H("#6a7488"))
            if (y - ty) % 8 == 0:
                for xx in range(int(tx - half), int(tx + half) + 1):
                    img.putpixel((xx, y), H("#4a5468"))
            k = (y - ty) % 8
            img.putpixel((int(tx - half + k * half / 4), y), H("#3a4458"))
        for xx in range(tx - 10, tx + 11):     # cross arm
            img.putpixel((xx, ty + 4), H("#8a94a8"))
    # cables sag from the arms toward the robot
    for (tx, ty), (ex, ey) in zip(PYLONS, CABLE_ENDS):
        for off in (-8, 8):
            x0, y0 = tx + off, ty + 4
            for i in range(200):
                t = i / 199
                x = x0 + (ex - x0) * t
                y = y0 + (ey + off * 0.3 - y0) * t + 14 * math.sin(t * math.pi)
                img.putpixel((int(x), int(y)), H("#c0c8d8") if off < 0 else H("#8890a4"))
    # a glow where the robot will stand
    for y in range(40, 140):
        for x in range(60, 180):
            d = math.hypot((x - 120) / 1.2, y - 100)
            if d < 60:
                img.putpixel((x, y), mix(img.getpixel((x, y)), H("#2a4a8a"), 0.35 * (1 - d / 60)))
    return img


def screen_dawn():
    W, Hh = 240, 160
    img = Image.new("RGB", (W, Hh), CLEAR)
    # the sun (left, low) stays in the picture; the rest of the sky is the backdrop gradient
    for y in range(60, 112):
        for x in range(20, 80):
            if math.hypot(x - 50, y - 100) < 20:
                img.putpixel((x, y), mix(H("#fff4c0"), H("#ffc060"), max(0, (y - 82) / 30)))
    skyline_rgb(img, 13, 128, 30, 64, H("#3a2438"), H("#ffd070"), wchance=0.45)
    skyline_rgb(img, 17, 132, 12, 36, H("#24162a"), H("#ffb050"), wchance=0.3)
    for y in range(132, Hh):
        for x in range(W):
            c = mix(H("#5a3a3a"), H("#1a1018"), (y - 132) / 28)
            if y == 133:
                c = H("#c08060")
            img.putpixel((x, y), c)
    for x in range(0, W, 24):    # street lines
        for xx in range(x, x + 12):
            img.putpixel((xx, 146), H("#e0b040"))
    return img


def build_screens(robot_frames, anchors, gl):
    screen_to_tiles("title", screen_title(robot_frames, anchors, gl))
    img, lava = screen_lava()
    screen_to_tiles("lava", img, lava, LAVA_RAMP)
    screen_to_tiles("win", screen_win(robot_frames, anchors, gl))
    screen_to_tiles("icity", screen_intro_city())
    screen_to_tiles("earth", screen_earth())
    screen_to_tiles("power", screen_power())
    screen_to_tiles("dawn", screen_dawn())
    build_cutscene_sprites()
    # cover art for the card (640x640)
    t = screen_title(robot_frames, anchors, gl)
    cover = Image.new("RGB", (640, 640))
    big = t.resize((640, 427), Image.NEAREST)
    cover.paste(big, (0, 106))
    cover.save(os.path.join(ART, "cover.png"))


# ---------------------------------------------------------------- main

def main():
    os.makedirs(ART, exist_ok=True)
    frames, anchors, gl = build_robot()
    build_enemies()
    build_variants()
    build_fx()
    build_proj()
    build_bosses()
    build_fonts()
    build_levels()
    build_screens(frames, anchors, gl)
    define("GROUND_Y", GROUND_Y)
    sq, wv = [], []
    for midi in range(128):
        f = 440.0 * 2 ** ((midi - 69) / 12)
        sq.append(max(0, min(2047, int(round(2048 - 131072 / f)))))
        wv.append(max(0, min(2047, int(round(2048 - 65536 / f)))))
    emit_u16("note_sq", sq)
    emit_u16("note_wv", wv)
    with open(os.path.join(SRC, "art.c"), "w") as f:
        f.write("// GENERATED by tools/make_art.py. Do not edit.\n#include \"art.h\"\n\n")
        f.write("\n".join(C_OUT))
    with open(os.path.join(SRC, "art.h"), "w") as f:
        f.write("// GENERATED by tools/make_art.py. Do not edit.\n#pragma once\n#include \"types.h\"\n\n")
        f.write("\n".join(H_OUT) + "\n")


if __name__ == "__main__":
    main()

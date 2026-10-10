"""Cartoon ball characters ("mascots") for the intro and the winner/loser ending.

mascot(body, color, r, mood, arms, mouth, t) -> RGBA image, mascot centred.
  body : RGBA flag image (cropped to a disc) or None for a plain team-colored ball
  color: team RGB
  r    : body radius in px
  mood : "angry" (shouting), "laugh", "sad", "dizzy"
  arms : 0 = arms down, 1 = arms raised high
  mouth: 0..1 how open the mouth is
  t    : time in seconds, for small wiggles
"""
import math
from PIL import Image, ImageDraw

SS = 2  # supersampling


def _shade(c, k):
    if k <= 1:
        return tuple(int(v * k) for v in c)
    return tuple(int(v + (255 - v) * (k - 1)) for v in c)


def _disc(img_rgba, d):
    side = min(img_rgba.size)
    sq = img_rgba.crop(((img_rgba.width - side) // 2, (img_rgba.height - side) // 2,
                        (img_rgba.width + side) // 2, (img_rgba.height + side) // 2)).resize((d, d), Image.LANCZOS)
    m = Image.new("L", (d, d), 0)
    ImageDraw.Draw(m).ellipse([0, 0, d - 1, d - 1], fill=255)
    sq.putalpha(m)
    return sq


def mascot(body, color, r, mood="angry", arms=0.0, mouth=0.0, t=0.0, crown=False):
    R = r * SS
    size = int(R * 3.4)
    c0 = size / 2
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    dark = _shade(color, 0.45)
    arm_col = _shade(color, 0.85)

    # arms (behind the body): from the shoulders, swinging between down and raised
    for side in (-1, 1):
        wob = math.sin(t * 18 + side) * 0.08 * arms
        ang_down, ang_up = math.radians(115), math.radians(-68)        # measured from +x, mirrored per side
        a = ang_down + (ang_up - ang_down) * min(1, arms) + wob
        sx, sy = c0 + side * R * 0.86, c0 + R * 0.05
        ex = sx + side * math.cos(a) * R * 0.95
        ey = sy + math.sin(a) * R * 0.95
        w = int(R * 0.2)
        d.line([sx, sy, ex, ey], fill=dark + (255,), width=w + int(R * 0.06))
        d.line([sx, sy, ex, ey], fill=arm_col + (255,), width=w)
        fr = R * 0.17
        d.ellipse([ex - fr - R * 0.03, ey - fr - R * 0.03, ex + fr + R * 0.03, ey + fr + R * 0.03], fill=dark + (255,))
        d.ellipse([ex - fr, ey - fr, ex + fr, ey + fr], fill=arm_col + (255,))

    # body
    ow = R * 0.07
    d.ellipse([c0 - R - ow, c0 - R - ow, c0 + R + ow, c0 + R + ow], fill=dark + (255,))
    if body is not None:
        disc = _disc(body, int(2 * R))
        img.alpha_composite(disc, (int(c0 - R), int(c0 - R)))
    else:
        d.ellipse([c0 - R, c0 - R, c0 + R, c0 + R], fill=color + (255,))
        d.ellipse([c0 - R * 0.62, c0 - R * 0.78, c0 - R * 0.18, c0 - R * 0.42], fill=_shade(color, 1.45) + (255,))
    d = ImageDraw.Draw(img)

    # eyes
    ey0 = c0 - R * 0.18
    for side in (-1, 1):
        ex = c0 + side * R * 0.34
        ew, eh = R * 0.2, R * 0.24
        if mood == "laugh":                     # squeezed shut: ^ ^
            d.arc([ex - ew, ey0 - eh * 0.6, ex + ew, ey0 + eh * 1.1], 200, 340, fill=(20, 20, 30, 255), width=int(R * 0.09))
            continue
        if mood == "dizzy":                     # X X
            k = R * 0.15
            d.line([ex - k, ey0 - k, ex + k, ey0 + k], fill=(20, 20, 30, 255), width=int(R * 0.08))
            d.line([ex - k, ey0 + k, ex + k, ey0 - k], fill=(20, 20, 30, 255), width=int(R * 0.08))
            continue
        d.ellipse([ex - ew - R * 0.04, ey0 - eh - R * 0.04, ex + ew + R * 0.04, ey0 + eh + R * 0.04], fill=(20, 20, 30, 255))
        d.ellipse([ex - ew, ey0 - eh, ex + ew, ey0 + eh], fill=(255, 255, 255, 255))
        py = ey0 + (eh * 0.35 if mood == "sad" else eh * 0.05)
        px = ex - side * ew * 0.25 if mood == "angry" else ex
        pr = R * 0.09
        d.ellipse([px - pr, py - pr, px + pr, py + pr], fill=(20, 20, 30, 255))
        # brows
        by = ey0 - eh - R * 0.08
        inner_x, outer_x = ex - side * ew * 0.9, ex + side * ew * 1.15
        if mood == "angry":     # inner ends pulled down
            d.line([inner_x, by + R * 0.08, outer_x, by - R * 0.08], fill=(20, 20, 30, 255), width=int(R * 0.09))
        elif mood == "sad":     # inner ends raised
            d.line([inner_x, by - R * 0.08, outer_x, by + R * 0.06], fill=(20, 20, 30, 255), width=int(R * 0.07))
            tx, ty = ex + side * ew * 0.2, ey0 + eh + R * 0.12 + (t * 140 % (R * 0.5))   # falling tear
            d.ellipse([tx - R * 0.06, ty - R * 0.04, tx + R * 0.06, ty + R * 0.12], fill=(90, 170, 255, 235))

    # mouth
    mx, my = c0, c0 + R * 0.42
    mw = R * (0.42 if mood != "laugh" else 0.55)
    if mood == "sad":
        d.arc([mx - mw * 0.7, my - R * 0.02, mx + mw * 0.7, my + R * 0.3], 200, 340, fill=(20, 20, 30, 255), width=int(R * 0.08))
    elif mood == "dizzy":
        d.ellipse([mx - R * 0.12, my - R * 0.08, mx + R * 0.12, my + R * 0.12], fill=(60, 10, 20, 255))
    else:
        mh = R * (0.06 + 0.36 * max(0.0, min(1.0, mouth)))
        if mood == "laugh":                    # big D-shaped grin
            d.pieslice([mx - mw, my - mh * 0.9, mx + mw, my + mh * 1.1], 0, 180, fill=(70, 10, 25, 255), outline=(20, 20, 30, 255), width=int(R * 0.05))
            d.rectangle([mx - mw * 0.8, my + R * 0.005, mx + mw * 0.8, my + R * 0.07], fill=(255, 255, 255, 255))
            tr = mh * 0.45
            d.ellipse([mx - tr, my + mh * 0.45, mx + tr, my + mh * 1.0], fill=(230, 90, 110, 255))
        else:                                   # shouting O
            d.ellipse([mx - mw * 0.75, my - mh, mx + mw * 0.75, my + mh], fill=(70, 10, 25, 255), outline=(20, 20, 30, 255), width=int(R * 0.05))
            d.chord([mx - mw * 0.6, my - mh * 0.9, mx + mw * 0.6, my - mh * 0.2], 180, 360, fill=(255, 255, 255, 255))

    # crown
    if crown:
        gold, gold_d = (255, 205, 50, 255), (190, 130, 20, 255)
        base, top = c0 - R * 0.86, c0 - R * 1.42
        pts = [(c0 - R * 0.55, base), (c0 - R * 0.62, top + R * 0.12), (c0 - R * 0.3, base - R * 0.3),
               (c0, top), (c0 + R * 0.3, base - R * 0.3), (c0 + R * 0.62, top + R * 0.12), (c0 + R * 0.55, base)]
        d.polygon(pts, fill=gold, outline=gold_d, width=int(R * 0.03))
        for px, py, col in ((c0, base - R * 0.15, (230, 40, 60, 255)), (c0 - R * 0.33, base - R * 0.12, (40, 140, 255, 255)),
                            (c0 + R * 0.33, base - R * 0.12, (40, 200, 110, 255))):
            jr = R * 0.07
            d.ellipse([px - jr, py - jr, px + jr, py + jr], fill=col)
    return img.resize((size // SS, size // SS), Image.LANCZOS)


if __name__ == "__main__":
    import sys, os
    here = os.path.dirname(os.path.abspath(__file__))
    fl = Image.open(os.path.join(here, "flags", "br.png")).convert("RGBA")
    sheet = Image.new("RGBA", (2000, 520), (20, 18, 40, 255))
    poses = [(fl, (34, 160, 70), "angry", 1.0, 1.0, False), (fl, (34, 160, 70), "laugh", 1.0, 0.8, True),
             (fl, (34, 160, 70), "sad", 0.0, 0.0, False), (None, (230, 57, 70), "angry", 0.5, 0.6, False),
             (None, (42, 157, 244), "laugh", 0.9, 0.5, True)]
    for k, (b, c, mood, arms, mouth, cr) in enumerate(poses):
        m = mascot(b, c, 120, mood, arms, mouth, 0.3, cr)
        sheet.alpha_composite(m, (k * 400 + 200 - m.width // 2, 270 - m.height // 2))
    sheet.save(sys.argv[1])


def crown(r):
    """Crown sprite for a mascot of radius r; its bottom edge sits at the mascot's head line (cy - 0.86 r)."""
    R = r * SS
    w, h = int(R * 1.5), int(R * 0.72)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, base, top = w / 2, h - 2, h - 2 - R * 0.56
    gold, gold_d = (255, 205, 50, 255), (190, 130, 20, 255)
    pts = [(cx - R * 0.55, base), (cx - R * 0.62, top + R * 0.12), (cx - R * 0.3, base - R * 0.3),
           (cx, top), (cx + R * 0.3, base - R * 0.3), (cx + R * 0.62, top + R * 0.12), (cx + R * 0.55, base)]
    d.polygon(pts, fill=gold, outline=gold_d, width=int(R * 0.03))
    for px, py, col in ((cx, base - R * 0.15, (230, 40, 60, 255)), (cx - R * 0.33, base - R * 0.12, (40, 140, 255, 255)),
                        (cx + R * 0.33, base - R * 0.12, (40, 200, 110, 255))):
        jr = R * 0.07
        d.ellipse([px - jr, py - jr, px + jr, py + jr], fill=col)
    return img.resize((w // SS, h // SS), Image.LANCZOS)

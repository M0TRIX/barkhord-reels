"""Territory-war battle reel ("pong wars" style) for barkhord.tv.

Usage: python3 battle.py OUT.mp4 SEED FORMAT      FORMAT = derby | cities | colors
Each team owns a region of a grid. Its ball flies through its own cells and
captures any enemy cell it touches (then bounces). A live bar shows each team's
share; when the clock runs out the biggest share wins. Writes OUT.json with the
caption, first comment and cover frame like reel_generator.py.
"""
import math, colorsys, wave, subprocess, sys, os, json, random, glob, shutil, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1]
SEED = int(sys.argv[2])
FORMAT = sys.argv[3]
rng = random.Random(SEED)
WORK = tempfile.mkdtemp(prefix="battle_")

# ---------------- font ----------------
FONT_DIR = os.path.expanduser("~/.cache/vazirmatn")
def font_path(weight):
    hits = glob.glob(f"{FONT_DIR}/**/UI-Farsi-Digits/fonts/ttf/Vazirmatn-UI-FD-{weight}.ttf", recursive=True)
    return hits[0] if hits else None
if not font_path("Black"):
    os.makedirs(FONT_DIR, exist_ok=True)
    subprocess.run(["npm", "pack", "vazirmatn", "--silent"], cwd=FONT_DIR, check=True)
    subprocess.run(["tar", "xzf", glob.glob(f"{FONT_DIR}/vazirmatn-*.tgz")[0]], cwd=FONT_DIR, check=True)
FONT, FONT_MED = font_path("Black"), font_path("SemiBold")
RQ = ImageFont.Layout.RAQM
FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
def fa(n): return str(n).translate(FA)
_fonts = {}
def F(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT if bold else FONT_MED, size, layout_engine=RQ)
    return _fonts[key]
def hexc(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

# ---------------- teams per format ----------------
CITY_COLORS = ["#E63946", "#2A9DF4", "#F4B400", "#2DC653", "#A855F7", "#FF7A1A"]
CITIES = ["تهران", "مشهد", "اصفهان", "شیراز", "تبریز", "اهواز", "کرج", "رشت",
          "کرمانشاه", "یزد", "قم", "کرمان", "همدان", "ارومیه", "زاهدان", "بندرعباس"]
if FORMAT == "derby":
    TEAMS = [("پرسپولیس", hexc("#E3262E")), ("استقلال", hexc("#1F63C6"))]
    rng.shuffle(TEAMS)
    HOOK, SUB = "پرسپولیس یا استقلال؟", "تا تموم نشده تیمتو بنویس"
    CTA_END = "تیمت برد؟"
elif FORMAT == "cities":
    n = rng.choice([3, 4, 4])
    names = rng.sample(CITIES, n)
    cols = rng.sample(CITY_COLORS, n)
    TEAMS = [(names[i], hexc(cols[i])) for i in range(n)]
    HOOK, SUB = "کدوم شهر می‌بره؟", "شهرتو کامنت کن، نوبت اونم میشه"
    CTA_END = "شهر تو نبود؟ کامنت کن"
elif FORMAT == "cup":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import cup
    CUP_STATE, CUP_R, CUP_M, ca_, cb_ = cup.next_match(SEED)
    col_a, col_b = cup.colors_for(CUP_R, CUP_M, CUP_STATE["season"])
    TEAMS = [(ca_, hexc(col_a)), (cb_, hexc(col_b))]
    HOOK, SUB = f"{ca_} یا {cb_}؟", "جام شهرها · " + cup.match_label(CUP_R, CUP_M)
    CTA_END = ""
else:
    pool = [("قرمز", "#E63946"), ("آبی", "#2A9DF4"), ("زرد", "#F4B400"), ("سبز", "#2DC653"), ("بنفش", "#A855F7")]
    n = rng.choice([2, 3, 4])
    TEAMS = [(nm, hexc(c)) for nm, c in rng.sample(pool, n)]
    HOOK, SUB = "یه رنگ انتخاب کن", "ببین می‌بره یا نه"
    CTA_END = "رنگت برد؟"
NT = len(TEAMS)

def shade(c, k):  # k<1 darker, k>1 lighter
    if k <= 1:
        return tuple(int(v * k) for v in c)
    return tuple(int(v + (255 - v) * (k - 1)) for v in c)

# ---------------- simulation ----------------
W, H, FPS = 1080, 1920, 30
BATTLE, OUTRO = 18.0, 3.0
DUR = BATTLE + OUTRO
N = int(DUR * FPS)
AX, AY, AS = 60, 540, 960           # arena square
GN = 25 if FORMAT == "cup" else 24  # grid cells per side (odd count = no ties)
CS = AS / GN
BR = 17                             # ball radius
SPEED = rng.uniform(700, 820)
NSUB = 10

grid = np.zeros((GN, GN), dtype=np.int8)
if NT == 2:
    vertical = rng.random() < 0.5
    for i in range(GN):
        for j in range(GN):
            # team 0 on the right/top, like the bar; works for odd GN (sides differ by one cell)
            grid[j, i] = (0 if i * GN + j >= GN * GN // 2 else 1) if vertical else (0 if j * GN + i < (GN * GN + 1) // 2 else 1)
elif NT == 3:
    for i in range(GN):
        grid[:, i] = 2 - min(2, i * 3 // GN)
else:
    for i in range(GN):
        for j in range(GN):
            grid[j, i] = (0 if i >= GN // 2 else 1) + (0 if j < GN // 2 else 2)

BALLS_PER_TEAM = 2
RAMP_R, RAMP_T = 36, 1.7          # attack ball: bigger, plows through enemy cells
balls = []   # [x, y, vx, vy, team, attack_until]
def spawn(t):
    ys, xs = np.where(grid == t)
    k = rng.randrange(len(xs))
    a = rng.uniform(0, 2 * math.pi)
    balls.append([(xs[k] + 0.5) * CS, (ys[k] + 0.5) * CS, math.cos(a) * SPEED, math.sin(a) * SPEED, t, -1.0])
for t in range(NT):
    for _ in range(BALLS_PER_TEAM):
        spawn(t)
# attack events: the team in last place gets a ball that plows through enemy land for a moment,
# so the bar swings and the lead keeps changing
BOOST_TIMES = [rng.uniform(1.8, 2.6), rng.uniform(7.0, 8.0), rng.uniform(12.3, 13.3)]
boosts = []  # (time, team)

def step(dt, captures, t_now):
    for b in balls:
        x, y, vx, vy, ti, until = b
        if t_now < until:
            r = RAMP_R
            i0, i1 = int((x - r) // CS), int((x + r) // CS)
            j0, j1 = int((y - r) // CS), int((y + r) // CS)
            for cj in range(max(0, j0), min(GN, j1 + 1)):
                for ci in range(max(0, i0), min(GN, i1 + 1)):
                    if grid[cj, ci] != ti:
                        cx_, cy_ = (ci + 0.5) * CS, (cj + 0.5) * CS
                        if (cx_ - x) ** 2 + (cy_ - y) ** 2 <= (r + CS * 0.35) ** 2:
                            grid[cj, ci] = ti
                            captures.append((t_now, ti))
        else:
            r = BR
            for k in range(8):
                ang = k * math.pi / 4
                px, py = x + math.cos(ang) * r, y + math.sin(ang) * r
                ci, cj = int(px // CS), int(py // CS)
                if 0 <= ci < GN and 0 <= cj < GN and grid[cj, ci] != ti:
                    grid[cj, ci] = ti
                    captures.append((t_now, ti))
                    if abs(math.cos(ang)) > abs(math.sin(ang)):
                        vx = -vx
                    else:
                        vy = -vy
                    th = math.atan2(vy, vx) + rng.uniform(-0.06, 0.06)   # never lock into a loop
                    vx, vy = math.cos(th) * SPEED, math.sin(th) * SPEED
        if x + vx * dt > AS - r or x + vx * dt < r:
            vx = -vx
        if y + vy * dt > AS - r or y + vy * dt < r:
            vy = -vy
        x = min(max(x + vx * dt, r), AS - r)
        y = min(max(y + vy * dt, r), AS - r)
        b[:] = [x, y, vx, vy, ti, until]

frames_grid, frames_balls, frames_share, captures = [], [], [], []
dt = 1.0 / (FPS * NSUB)
for fi in range(int(BATTLE * FPS) + 1):
    t_frame = fi / FPS
    share_now = np.bincount(grid.ravel(), minlength=NT) / grid.size
    for bt_ in BOOST_TIMES:
        if t_frame >= bt_ and all(b_[0] != bt_ for b_ in boosts):
            loser = int(np.argmin(share_now))
            mine = [b for b in balls if b[4] == loser]
            atk = rng.choice(mine)
            atk[5] = bt_ + RAMP_T
            # aim the attack at the enemy's biggest region
            ys, xs = np.where(grid != loser)
            k = rng.randrange(len(xs))
            tx, ty = (xs[k] + 0.5) * CS, (ys[k] + 0.5) * CS
            th = math.atan2(ty - atk[1], tx - atk[0])
            atk[2], atk[3] = math.cos(th) * SPEED * 1.15, math.sin(th) * SPEED * 1.15
            boosts.append((bt_, loser))
    frames_grid.append(grid.copy())
    frames_balls.append([(b[0], b[1], b[4], t_frame < b[5]) for b in balls])
    frames_share.append(share_now)
    if fi < int(BATTLE * FPS):
        for s in range(NSUB):
            step(dt, captures, t_frame + s * dt)
    for b in balls:   # attack over: back to normal speed
        if t_frame >= b[5] > 0:
            sp = math.hypot(b[2], b[3]); b[2], b[3] = b[2] / sp * SPEED, b[3] / sp * SPEED
final_share = frames_share[-1]
WIN = int(np.argmax(final_share))
WIN_PCT = int(round(final_share[WIN] * 100))
CARD_SUB = f"{fa(WIN_PCT)}٪ زمین رو گرفت"
FOLLOW_LINE = "فالو کن که بعدی رو از دست ندی"
if FORMAT == "cup":
    CUP_INFO = cup.record(CUP_STATE, CUP_R, CUP_M, TEAMS[WIN][0])
    if CUP_INFO["champion"]:
        CARD_SUB = "قهرمان جام شهرها شد!"
        CTA_END = "فصل بعد: شهرت رو کامنت کن"
    else:
        CARD_SUB = f"رفت {CUP_INFO['advanced_to']}"
        na, nb = CUP_INFO["next"]
        CTA_END = f"بازی بعد: {na} و {nb}"
    FOLLOW_LINE = "فالو کن ببینی کی میره بالا"
lead_changes = sum(1 for a, b in zip(frames_share[FPS::FPS], frames_share[2 * FPS::FPS]) if np.argmax(a) != np.argmax(b))
print(f"seed={SEED} format={FORMAT} teams={[t[0] for t in TEAMS]} winner={TEAMS[WIN][0]} {WIN_PCT}% lead_changes={lead_changes} boosts={boosts}")
if os.environ.get("DRY"):
    print("share every 2s:", [" ".join(f"{s:.2f}" for s in frames_share[i]) for i in range(0, len(frames_share), 2 * FPS)])
    sys.exit()

# ---------------- audio ----------------
SR = 44100
audio = np.zeros(int(SR * (DUR + 2)))
def tone(f, L, decay, harm=0.3):
    tt = np.arange(L) / SR
    env = np.minimum(tt / 0.003, 1) * np.exp(-tt * decay)
    return (np.sin(2 * np.pi * f * tt) + harm * np.sin(2 * np.pi * 2 * f * tt)) * env
def add(sig, t0, gain):
    s = int(t0 * SR); seg = audio[s:s + len(sig)]; seg += sig[: len(seg)] * gain
team_freq = [440 * 2 ** ((m - 69) / 12) for m in (72, 76, 79, 84, 67, 74)]
last = [-1.0] * NT
for t0, ti in captures:
    if t0 - last[ti] >= 0.07:
        last[ti] = t0
        add(tone(team_freq[ti] * rng.choice([1, 1.122, 1.26]), int(SR * 0.12), 38), t0, 0.22)
for k, t0 in enumerate((BATTLE - 3, BATTLE - 2, BATTLE - 1)):   # countdown
    add(tone(880, int(SR * 0.18), 14, 0.1), t0, 0.7)
for bt_, _t in boosts:  # rising sweep for the comeback
    L = int(SR * 0.45); tt_ = np.arange(L) / SR
    add(np.sin(2 * np.pi * (300 * tt_ + 900 * tt_ ** 2)) * np.minimum(tt_ / 0.02, 1) * np.exp(-tt_ * 3), bt_, 0.6)
add(tone(523, int(SR * 0.25), 6), 0.0, 0.5); add(tone(784, int(SR * 0.3), 6), 0.12, 0.5)  # start
tt = np.arange(int(SR * 2.5)) / SR                                                      # win fanfare
boom = np.sin(2 * np.pi * 60 * tt * (1 - 0.25 * tt)) * np.exp(-tt * 3.5) * 1.3
chord = sum(tone(440 * 2 ** ((m - 69) / 12), len(tt), 1.6) for m in (72, 76, 79, 84)) * 0.32
add(boom + chord, BATTLE, 1.0)
d = int(0.1 * SR); wet = np.zeros_like(audio); wet[d:] = audio[:-d] * 0.22
audio = (audio + wet)[: int(SR * DUR)]
fade = int(0.4 * SR); audio[-fade:] *= np.linspace(1, 0, fade)
audio = audio / (np.abs(audio).max() + 1e-9) * 0.89
WAV = os.path.join(WORK, "a.wav")
with wave.open(WAV, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((audio * 32767).astype(np.int16).tobytes())

# ---------------- render ----------------
BG = Image.new("RGBA", (W, H), (12, 12, 24, 255))
bgd = ImageDraw.Draw(BG)
for y in range(H):
    k = y / H
    bgd.line([(0, y), (W, y)], fill=(int(12 + 10 * k), int(12 + 4 * k), int(24 + 16 * k), 255))
CELL_COL = [shade(c, 0.62) for _, c in TEAMS]
CELL_EDGE = [shade(c, 0.5) for _, c in TEAMS]

def draw_grid(img, g):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([AX - 8, AY - 8, AX + AS + 8, AY + AS + 8], 22, fill=(255, 255, 255, 30))
    for j in range(GN):
        for i in range(GN):
            t = g[j, i]
            x0, y0 = AX + i * CS, AY + j * CS
            d.rectangle([x0, y0, x0 + CS, y0 + CS], fill=CELL_EDGE[t])
            d.rounded_rectangle([x0 + 2, y0 + 2, x0 + CS - 2, y0 + CS - 2], 6, fill=CELL_COL[t])

def draw_bar(img, share, hl=-1):
    d = ImageDraw.Draw(img)
    bx, by, bw, bh = 60, 400, 960, 46
    d.rounded_rectangle([bx, by, bx + bw, by + bh], 23, fill=(255, 255, 255, 25))
    x = bx
    order = list(range(NT))[::-1]    # right-to-left so team 0 sits on the right (RTL reading)
    segs = []
    for t in order:
        w = bw * share[t]
        segs.append((t, x, x + w))
        x += w
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, bw - 1, bh - 1], 23, fill=255)
    bar = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bar)
    for t, x0, x1 in segs:
        bd.rectangle([x0 - bx, 0, x1 - bx, bh], fill=TEAMS[t][1] + (255,))
    img.paste(bar, (bx, by), mask)
    # labels under the bar: name + percent, laid out right-to-left
    slot = bw / NT
    for idx in range(NT):
        t = idx
        cx = bx + bw - slot * (idx + 0.5)
        pct = int(round(share[t] * 100))
        col = shade(TEAMS[t][1], 1.35)
        size = 44 if NT <= 2 else 36
        if t == hl:
            size += 6
        d.text((cx, by + bh + 46), f"{TEAMS[t][0]} {fa(pct)}٪", font=F(size), fill=col + (255,),
               anchor="mm", direction="rtl", language="fa")

def draw_balls(img, pos):
    lay = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for (x, y, t, atk) in pos:
        cx, cy = (AX + x) * 2, (AY + y) * 2
        r = (RAMP_R if atk else BR) * 2
        c = shade(TEAMS[t][1], 1.15)
        ring = 12 if atk else 7
        d.ellipse([cx - r - ring, cy - r - ring, cx + r + ring, cy + r + ring], fill=(c if not atk else shade(TEAMS[t][1], 1.4)) + (255,))
        d.ellipse([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], fill=(255, 255, 255, 255) if not atk else c + (255,))
        if atk:
            h = r * 0.35
            d.ellipse([cx - h, cy - h, cx + h, cy + h], fill=(255, 255, 255, 255))
    glow = lay.resize((W // 2, H // 2), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10)).resize((W, H))
    img.alpha_composite(glow)
    img.alpha_composite(lay.resize((W, H), Image.LANCZOS))

def text(img, xy, s, size, col=(255, 255, 255, 255), bold=True, max_w=960):
    d = ImageDraw.Draw(img)
    while size > 24 and d.textlength(s, font=F(size, bold), direction="rtl", language="fa") > max_w:
        size -= 2
    d.text(xy, s, font=F(size, bold), fill=col, anchor="mm", direction="rtl", language="fa")

ff = subprocess.Popen([
    "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
    "-r", str(FPS), "-i", "-", "-i", WAV, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT,
], stdin=subprocess.PIPE)

prng = np.random.default_rng(SEED)
NP = 140
cang = prng.uniform(0, 2 * np.pi, NP); cspd = prng.uniform(400, 1500, NP)
CV = np.stack([np.cos(cang) * cspd, np.sin(cang) * cspd - 600], 1)
CSZ = prng.uniform(8, 18, NP)
CCOL = [shade(TEAMS[WIN][1], prng.uniform(0.9, 1.5)) for _ in range(NP)]
battle_frames = len(frames_grid)
final_frame = None
for fi in range(N):
    tnow = fi / FPS
    img = BG.copy()
    text(img, (W / 2, 200), HOOK, 74)
    text(img, (W / 2, 290), SUB, 44, (255, 255, 255, 170), bold=False)
    if tnow < BATTLE:
        g = frames_grid[min(fi, battle_frames - 1)]
        draw_grid(img, g)
        draw_balls(img, frames_balls[min(fi, battle_frames - 1)])
        share = frames_share[min(fi, battle_frames - 1)]
        draw_bar(img, share, hl=int(np.argmax(share)))
        left = max(0, math.ceil(BATTLE - tnow))
        urgent = BATTLE - tnow <= 3
        tc = (255, 90, 90, 255) if urgent else (255, 255, 255, 200)
        tsize = 64 + (int(14 * (1 - (BATTLE - tnow) % 1)) if urgent else 0)
        text(img, (W / 2, AY + AS + 90), f"۰:{fa(left).rjust(2, '۰')}", tsize, tc)
        for bt_, team in boosts:          # comeback banner
            age = tnow - bt_
            if 0 <= age < 1.6:
                a = int(255 * min(1, age / 0.15, (1.6 - age) / 0.3))
                pop = 1 + 0.25 * max(0, 1 - age / 0.2)
                c = TEAMS[team][1]
                d = ImageDraw.Draw(img)
                cy = AY + 100
                d.rounded_rectangle([200, cy - 50 * pop, 880, cy + 50 * pop], 36,
                                    fill=shade(c, 0.55) + (int(a * 0.92),), outline=shade(c, 1.4) + (a,), width=5)
                text(img, (W / 2, cy), f"{TEAMS[team][0]} حمله کرد!", int(50 * pop), (255, 255, 255, a))
    else:
        bt = tnow - BATTLE
        if final_frame is None:
            final_frame = BG.copy()
            draw_grid(final_frame, frames_grid[-1])
            draw_bar(final_frame, final_share, hl=WIN)
        img = final_frame.copy()
        text(img, (W / 2, 200), HOOK, 74)
        text(img, (W / 2, 290), SUB, 44, (255, 255, 255, 170), bold=False)
        dim = Image.new("RGBA", (W, H), (0, 0, 0, int(min(1, bt / 0.3) * 150)))
        img.alpha_composite(dim)
        if bt < 0.2:
            img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(180 * (1 - bt / 0.2)))))
        d = ImageDraw.Draw(img)
        pos = np.array([W / 2, AY + AS / 2]) + CV * bt + np.array([0, 900]) * bt ** 2 / 2
        a = int(255 * max(0, 1 - bt / OUTRO))
        for q in range(NP):
            x, y = pos[q]
            d.ellipse([x - CSZ[q], y - CSZ[q], x + CSZ[q], y + CSZ[q]], fill=CCOL[q] + (a,))
        sc = min(1, bt / 0.25)
        card_h = 360
        cy = AY + AS / 2
        d.rounded_rectangle([110, cy - card_h / 2, 970, cy + card_h / 2], 40,
                            fill=shade(TEAMS[WIN][1], 0.75) + (int(235 * sc),),
                            outline=shade(TEAMS[WIN][1], 1.4) + (int(255 * sc),), width=6)
        if sc >= 1:
            text(img, (W / 2, cy - 100), "برنده", 52, (255, 255, 255, 200), bold=False)
            text(img, (W / 2, cy), TEAMS[WIN][0], 120, max_w=800)
            text(img, (W / 2, cy + 110), CARD_SUB, 50, (255, 255, 255, 220), bold=False, max_w=800)
        if bt > 0.7:
            text(img, (W / 2, AY + AS + 90), CTA_END, 58, shade(TEAMS[WIN][1], 1.45) + (255,))
        if bt > 1.2:
            text(img, (W / 2, AY + AS + 170), FOLLOW_LINE, 42, (255, 255, 255, 200), bold=False)
    ImageDraw.Draw(img).text((W / 2, H - 110), "@barkhord.tv", font=F(36, False), fill=(255, 255, 255, 110), anchor="mm")
    ff.stdin.write(img.convert("RGB").tobytes())
    if os.environ.get("PREVIEW") and fi in (int(1.0 * FPS), int(BOOST_TIMES[0] * FPS) + 8, int(10 * FPS), int((BATTLE + 1.2) * FPS)):
        img.convert("RGB").save(f"{OUT}.preview_{fi:04d}.png")
ff.stdin.close(); ff.wait()
shutil.rmtree(WORK, ignore_errors=True)

# ---------------- caption ----------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import captions
names = [t[0] for t in TEAMS]
if FORMAT == "cup":
    caption, first = captions.cup(rng, names, TEAMS[WIN][0], cup.ROUND_NAMES[CUP_R], CUP_INFO)
    cup.save(CUP_STATE)
else:
    caption, first = getattr(captions, FORMAT)(rng, names, TEAMS[WIN][0])
meta = {"seed": SEED, "format": FORMAT, "teams": names, "winner": TEAMS[WIN][0], "winner_pct": WIN_PCT,
        "duration": DUR, "instagram_caption": caption, "first_comment": first, "cover_ms": int(9.5 * 1000)}
with open(os.path.splitext(OUT)[0] + ".json", "w", encoding="utf-8") as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=2)
print("done", OUT)

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
BATTLE, FINISH, OUTRO = 16.0, 2.2, 3.4      # fight, knockout sweep, winner card
SIM_END = BATTLE + FINISH
DUR = SIM_END + OUTRO
N = int(DUR * FPS)
AX, AY, AS = 60, 540, 960           # arena square
GN = 25 if FORMAT == "cup" else 24  # grid cells per side (odd count = no ties)
CS = AS / GN
BR = 17                             # ball radius
SPEED = rng.uniform(700, 820)
NSUB = 10
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scipy import signal as _sig

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
GIANT_R, GIANT_T = 95, 2.0
balls = []   # [x, y, vx, vy, team, giant_until, expire_at]
def spawn(t, x=None, y=None, expire=1e9):
    if x is None:
        ys, xs = np.where(grid == t)
        k = rng.randrange(len(xs))
        x, y = (xs[k] + 0.5) * CS, (ys[k] + 0.5) * CS
    a = rng.uniform(0, 2 * math.pi)
    balls.append([x, y, math.cos(a) * SPEED, math.sin(a) * SPEED, t, -1.0, expire])
for t in range(NT):
    for _ in range(BALLS_PER_TEAM):
        spawn(t)

# ---- special powers: the team in last place gets one, which keeps the lead changing ----
POWER_NAME = {"giant": "توپ غول‌پیکر", "rpg": "آرپی‌جی", "lightning": "صاعقه", "clone": "تکثیر"}
FRENZY = 5.0                         # the last seconds: faster balls, more powers
POWER_TIMES = [rng.uniform(2.0, 2.6), rng.uniform(5.8, 6.6), rng.uniform(9.2, 9.8),
               BATTLE - rng.uniform(4.3, 4.0), BATTLE - rng.uniform(2.3, 2.0)]
POWER_KINDS = rng.sample(list(POWER_NAME), 3)
POWER_KINDS += [rng.choice([k for k in ("rpg", "lightning", "giant") if k != POWER_KINDS[-1]])]
POWER_KINDS += [rng.choice([k for k in ("rpg", "lightning", "giant") if k != POWER_KINDS[-1]])]
powers, pending, effects, shakes, captures = [], [], [], [], []

def capture_disc(cx, cy, rad, team, t_now):
    i0, i1 = int((cx - rad) // CS), int((cx + rad) // CS)
    j0, j1 = int((cy - rad) // CS), int((cy + rad) // CS)
    for cj in range(max(0, j0), min(GN, j1 + 1)):
        for ci in range(max(0, i0), min(GN, i1 + 1)):
            if grid[cj, ci] != team and ((ci + 0.5) * CS - cx) ** 2 + ((cj + 0.5) * CS - cy) ** 2 <= rad ** 2:
                grid[cj, ci] = team
                captures.append((t_now, team))

def enemy_target(team, rad):
    """A spot in enemy land where a blast of radius rad (px) takes the most cells."""
    rc = int(math.ceil(rad / CS))
    yy, xx = np.mgrid[-rc:rc + 1, -rc:rc + 1]
    kernel = ((xx * CS) ** 2 + (yy * CS) ** 2 <= rad ** 2).astype(float)
    score = _sig.convolve2d((grid != team).astype(float), kernel, mode="same")
    score = score * (grid != team)
    flat = np.argsort(score.ravel())[::-1][:6]
    k = int(rng.choice(list(flat)))
    j, i = divmod(k, GN)
    return (i + 0.5) * CS, (j + 0.5) * CS

def trigger_power(kind, t0, team):
    mine = [b for b in balls if b[4] == team]
    powers.append({"kind": kind, "t0": t0, "team": team})
    if kind == "giant":
        b = rng.choice(mine)
        b[5] = t0 + GIANT_T
        tx, ty = enemy_target(team, GIANT_R)
        th = math.atan2(ty - b[1], tx - b[0])
        b[2], b[3] = math.cos(th) * SPEED * 1.1, math.sin(th) * SPEED * 1.1
    elif kind == "rpg":
        b = rng.choice(mine)
        rad = 4.8 * CS
        tx, ty = enemy_target(team, rad)
        t1 = t0 + 0.6
        effects.append({"type": "rpg", "t0": t0, "t1": t1, "x0": b[0], "y0": b[1], "x1": tx, "y1": ty, "team": team, "rad": rad})
        pending.append((t1, lambda: capture_disc(tx, ty, rad, team, t1)))
        shakes.append((t1, 0.45, 20))
    elif kind == "lightning":
        rad = 2.4 * CS
        for k in range(5):
            ts = t0 + 0.2 + k * 0.2
            def strike(ts=ts):
                x, y = enemy_target(team, rad)
                effects.append({"type": "bolt", "t0": ts, "x": x, "y": y, "team": team,
                                "seed": rng.randrange(10 ** 6), "rad": rad})
                capture_disc(x, y, rad, team, ts)
            pending.append((ts, strike))
            shakes.append((ts, 0.15, 9))
    elif kind == "clone":
        for k in range(3):
            src = rng.choice(mine)
            spawn(team, src[0], src[1], expire=t0 + 3.6)
            effects.append({"type": "poof", "t0": t0, "x": src[0], "y": src[1], "team": team})

def step(dt, t_now):
    for b in balls:
        x, y, vx, vy, ti, until, exp = b
        if t_now < until:
            r = GIANT_R
            capture_disc(x, y, r + CS * 0.35, ti, t_now)
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
        b[:] = [x, y, vx, vy, ti, until, exp]

frames_grid, frames_balls, frames_share = [], [], []
dt = 1.0 / (FPS * NSUB)
WIN, LEAD_SHARE, SWEEP = None, None, None
fired = set()
frenzy_on = False
for fi in range(int(SIM_END * FPS) + 1):
    t_frame = fi / FPS
    if t_frame < BATTLE:
        for idx, pt in enumerate(POWER_TIMES):
            if t_frame >= pt and idx not in fired:
                fired.add(idx)
                share_now = np.bincount(grid.ravel(), minlength=NT)
                trigger_power(POWER_KINDS[idx], pt, int(np.argmin(share_now)))
    for ev in [e for e in pending if t_frame >= e[0]]:
        pending.remove(ev)
        ev[1]()
    balls[:] = [b for b in balls if b[6] > t_frame]
    for b in balls:   # giant phase over: back to normal speed
        if t_frame >= b[5] > 0:
            sp = math.hypot(b[2], b[3]); b[2], b[3] = b[2] / sp * SPEED, b[3] / sp * SPEED; b[5] = -1.0
    if BATTLE - FRENZY <= t_frame < BATTLE and not frenzy_on:
        frenzy_on = True
        SPEED *= 1.35
        for b in balls:
            b[2] *= 1.35; b[3] *= 1.35
    if t_frame >= BATTLE:
        if WIN is None:      # time is up: the leader wipes out everyone else
            counts = np.bincount(grid.ravel(), minlength=NT)
            WIN = int(np.argmax(counts))
            LEAD_SHARE = counts / grid.size
            for b in balls:
                if b[4] != WIN:
                    effects.append({"type": "poof", "t0": t_frame, "x": b[0], "y": b[1], "team": b[4]})
            balls[:] = [b for b in balls if b[4] == WIN]
            ys, xs = np.where(grid == WIN)
            SC = ((xs.mean() + 0.5) * CS, (ys.mean() + 0.5) * CS)
            jj, ii = np.mgrid[0:GN, 0:GN]
            DIST = np.hypot((ii + 0.5) * CS - SC[0], (jj + 0.5) * CS - SC[1])
            DMAX = DIST.max() + CS
            SWEEP = 1.5
            shakes.append((BATTLE, 0.6, 16))
        k = min(1.0, (t_frame - BATTLE) / SWEEP)
        rad = DMAX * (1 - (1 - k) ** 2)
        grid[DIST <= rad] = WIN
    frames_grid.append(grid.copy())
    frames_balls.append([(b[0], b[1], b[4], t_frame < b[5], b[6] < 1e9) for b in balls])
    frames_share.append(np.bincount(grid.ravel(), minlength=NT) / grid.size)
    if fi < int(SIM_END * FPS):
        for s in range(NSUB):
            step(dt, t_frame + s * dt)

WIN_PCT = int(round(LEAD_SHARE[WIN] * 100))
CARD_SUB = "کل زمین رو گرفت!"
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
shares_b = frames_share[: int(BATTLE * FPS)]
lead_changes = sum(1 for a, b in zip(shares_b[FPS::FPS], shares_b[2 * FPS::FPS]) if np.argmax(a) != np.argmax(b))
print(f"seed={SEED} format={FORMAT} teams={[t[0] for t in TEAMS]} winner={TEAMS[WIN][0]} lead={WIN_PCT}% "
      f"lead_changes={lead_changes} powers={[(p['kind'], round(p['t0'], 1), TEAMS[p['team']][0]) for p in powers]}")
if os.environ.get("DRY"):
    print("share every 2s:", [" ".join(f"{s:.2f}" for s in frames_share[i]) for i in range(0, len(frames_share), 2 * FPS)])
    sys.exit()

# ---------------- audio ----------------
import sfx
SR = sfx.SR
audio = np.zeros(int(SR * (DUR + 3)))
def tone(f, L, decay, harm=0.3):
    tt = np.arange(L) / SR
    env = np.minimum(tt / 0.003, 1) * np.exp(-tt * decay)
    return (np.sin(2 * np.pi * f * tt) + harm * np.sin(2 * np.pi * 2 * f * tt)) * env
def add(sig, t0, gain):
    s = int(t0 * SR); seg = audio[s:s + len(sig)]; seg += sig[: len(seg)] * gain
team_freq = [440 * 2 ** ((m - 69) / 12) for m in (72, 76, 79, 84, 67, 74)]
last = [-1.0] * NT
for t0, ti in captures:
    if t0 < BATTLE and t0 - last[ti] >= 0.07:
        last[ti] = t0
        add(tone(team_freq[ti] * rng.choice([1, 1.122, 1.26]), int(SR * 0.12), 38), t0, 0.2)
add(tone(523, int(SR * 0.25), 6), 0.0, 0.5); add(tone(784, int(SR * 0.3), 6), 0.12, 0.5)   # start
for k in range(int(FRENZY)):                                                              # countdown beeps
    add(tone(880 if k < 3 else 660, int(SR * 0.18), 14, 0.1), BATTLE - 1 - k, 0.7 if k < 3 else 0.5)
tb = BATTLE - FRENZY
while tb < BATTLE:                                                                        # heartbeat
    for off, g in ((0.0, 0.9), (0.16, 0.6)):
        add(np.sin(2 * np.pi * 55 * np.arange(int(SR * 0.18)) / SR) * np.exp(-np.arange(int(SR * 0.18)) / SR * 22), tb + off, g)
    tb += 0.5
for p in powers:
    add(sfx.rise(0.5), p["t0"], 0.45)
    if p["kind"] == "clone":
        for k in range(3):
            add(sfx.pop(600 + 250 * k), p["t0"] + 0.08 * k, 0.8)
for e in effects:
    if e["type"] == "rpg":
        add(sfx.whoosh(0.6, seed=int(e["t0"] * 100)), e["t0"], 0.55)
        add(sfx.boom(1.4, seed=int(e["t1"] * 100)), e["t1"], 1.0)
    elif e["type"] == "bolt":
        add(sfx.thunder(0.9, seed=int(e["t0"] * 100)), e["t0"], 0.6)
    elif e["type"] == "poof" and e["t0"] >= BATTLE:
        add(sfx.pop(420), e["t0"] + rng.uniform(0, 0.15), 0.6)
add(sfx.boom(2.0, seed=7), BATTLE, 1.3)                       # knockout
add(sfx.whoosh(1.4, seed=8, rising=False), BATTLE + 0.05, 0.5)
chord = sum(tone(440 * 2 ** ((m - 69) / 12), int(SR * 2.5), 1.6) for m in (72, 76, 79, 84))
add(chord, SIM_END, 0.22)
add(sfx.laugh(seed=SEED % 1000), SIM_END + 0.25, 1.15)          # the winner laughs at the loser
d = int(0.1 * SR); wet = np.zeros_like(audio); wet[d:] = audio[:-d] * 0.2
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

def layer():
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    return lay, ImageDraw.Draw(lay)

def draw_grid(img, g):
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([AX - 8, AY - 8, AX + AS + 8, AY + AS + 8], 22, fill=(40, 40, 60, 255))
    for j in range(GN):
        for i in range(GN):
            t = g[j, i]
            x0, y0 = AX + i * CS, AY + j * CS
            d.rectangle([x0, y0, x0 + CS, y0 + CS], fill=CELL_EDGE[t])
            d.rounded_rectangle([x0 + 2, y0 + 2, x0 + CS - 2, y0 + CS - 2], 6, fill=CELL_COL[t])

def draw_bar(img, share, hl=-1):
    d = ImageDraw.Draw(img)
    bx, by, bw, bh = 60, 400, 960, 46
    d.rounded_rectangle([bx, by, bx + bw, by + bh], 23, fill=(40, 40, 60, 255))
    x = bx
    segs = []
    for t in list(range(NT))[::-1]:    # right-to-left so team 0 sits on the right (RTL reading)
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
    slot = bw / NT
    for t in range(NT):
        cx = bx + bw - slot * (t + 0.5)
        pct = int(round(share[t] * 100))
        size = (44 if NT <= 2 else 36) + (6 if t == hl else 0)
        d.text((cx, by + bh + 46), f"{TEAMS[t][0]} {fa(pct)}٪", font=F(size), fill=shade(TEAMS[t][1], 1.35) + (255,),
               anchor="mm", direction="rtl", language="fa")

def draw_balls(img, pos, tnow):
    lay = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for (x, y, t, giant, clone) in pos:
        cx, cy = (AX + x) * 2, (AY + y) * 2
        c = shade(TEAMS[t][1], 1.15)
        if giant:
            r = GIANT_R * 2 * (1 + 0.06 * math.sin(tnow * 30))
            d.ellipse([cx - r - 16, cy - r - 16, cx + r + 16, cy + r + 16], fill=shade(TEAMS[t][1], 1.5) + (255,))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c + (255,))
            h = r * 0.3
            d.ellipse([cx - h, cy - h, cx + h, cy + h], fill=(255, 255, 255, 255))
        else:
            r = BR * 2
            ring = 11 if clone else 7
            d.ellipse([cx - r - ring, cy - r - ring, cx + r + ring, cy + r + ring], fill=c + (255,))
            d.ellipse([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], fill=(255, 255, 255, 255) if not clone else shade(TEAMS[t][1], 1.6) + (255,))
    glow = lay.resize((W // 2, H // 2), Image.BILINEAR).filter(ImageFilter.GaussianBlur(10)).resize((W, H))
    img.alpha_composite(glow)
    img.alpha_composite(lay.resize((W, H), Image.LANCZOS))

EFFECT_MASK = Image.new("L", (W, H), 0)
ImageDraw.Draw(EFFECT_MASK).rectangle([AX - 8, AY - 120, AX + AS + 8, AY + AS + 8], fill=255)
ZERO_L = Image.new("L", (W, H), 0)

def effects_active(tnow):
    for e in effects:
        if e["type"] == "rpg" and e["t0"] <= tnow < e["t1"] + 0.6:
            return True
        if e["type"] == "bolt" and e["t0"] - 0.05 <= tnow < e["t0"] + 0.22:
            return True
        if e["type"] == "poof" and e["t0"] <= tnow < e["t0"] + 0.4:
            return True
    return WIN is not None and BATTLE <= tnow < BATTLE + SWEEP + 0.3

def draw_effects(img, tnow):
    if not effects_active(tnow):
        return
    lay, d = layer()
    for e in effects:
        col = TEAMS[e["team"]][1]
        if e["type"] == "rpg":
            if e["t0"] <= tnow < e["t1"]:                      # rocket in flight with a smoke trail
                k = (tnow - e["t0"]) / (e["t1"] - e["t0"])
                ease = k * k
                x = AX + e["x0"] + (e["x1"] - e["x0"]) * ease
                y = AY + e["y0"] + (e["y1"] - e["y0"]) * ease
                ang = math.atan2(e["y1"] - e["y0"], e["x1"] - e["x0"])
                for q in range(10):
                    kk = max(0.0, ease - q * 0.035)
                    sx = AX + e["x0"] + (e["x1"] - e["x0"]) * kk
                    sy = AY + e["y0"] + (e["y1"] - e["y0"]) * kk
                    rr = 10 + q * 2.5
                    d.ellipse([sx - rr, sy - rr, sx + rr, sy + rr], fill=(200, 200, 210, max(0, 150 - q * 14)))
                L = 46
                hx, hy = x + math.cos(ang) * L / 2, y + math.sin(ang) * L / 2
                tx, ty = x - math.cos(ang) * L / 2, y - math.sin(ang) * L / 2
                d.line([tx, ty, hx, hy], fill=(235, 235, 240, 255), width=16)
                px, py = -math.sin(ang), math.cos(ang)
                d.polygon([(hx + math.cos(ang) * 18, hy + math.sin(ang) * 18), (hx + px * 11, hy + py * 11), (hx - px * 11, hy - py * 11)],
                          fill=shade(col, 1.1) + (255,))
                fl = 22 + 8 * math.sin(tnow * 60)
                d.polygon([(tx, ty), (tx + px * 8 - math.cos(ang) * fl, ty + py * 8 - math.sin(ang) * fl),
                           (tx - px * 8 - math.cos(ang) * fl, ty - py * 8 - math.sin(ang) * fl)], fill=(255, 170, 40, 255))
            elif e["t1"] <= tnow < e["t1"] + 0.6:                # explosion
                k = (tnow - e["t1"]) / 0.6
                x, y = AX + e["x1"], AY + e["y1"]
                R = e["rad"] * (0.4 + 0.9 * (1 - (1 - k) ** 3))
                a = int(255 * (1 - k))
                d.ellipse([x - R, y - R, x + R, y + R], fill=(255, 140, 30, int(a * 0.55)))
                R2 = R * 0.65
                d.ellipse([x - R2, y - R2, x + R2, y + R2], fill=(255, 230, 120, int(a * 0.8)))
                d.ellipse([x - R * 1.15, y - R * 1.15, x + R * 1.15, y + R * 1.15], outline=(255, 255, 255, a), width=8)
        elif e["type"] == "bolt" and e["t0"] - 0.05 <= tnow < e["t0"] + 0.22:
            br = random.Random(e["seed"])
            x1, y1 = AX + e["x"], AY + e["y"]
            pts = [(x1 + br.uniform(-60, 60), AY - 60)]
            for q in range(1, 8):
                f = q / 8
                pts.append((pts[0][0] + (x1 - pts[0][0]) * f + br.uniform(-38, 38), AY - 60 + (y1 - AY + 60) * f))
            pts.append((x1, y1))
            a = 255 if tnow >= e["t0"] else 120
            d.line(pts, fill=shade(col, 1.3) + (a,), width=22, joint="curve")
            d.line(pts, fill=(255, 255, 255, a), width=8, joint="curve")
            if tnow >= e["t0"]:
                k = (tnow - e["t0"]) / 0.22
                R = e["rad"] * (0.6 + 0.8 * k)
                d.ellipse([x1 - R, y1 - R, x1 + R, y1 + R], outline=(255, 255, 255, int(255 * (1 - k))), width=6)
        elif e["type"] == "poof" and e["t0"] <= tnow < e["t0"] + 0.4:
            k = (tnow - e["t0"]) / 0.4
            x, y = AX + e["x"], AY + e["y"]
            R = 20 + 70 * k
            d.ellipse([x - R, y - R, x + R, y + R], outline=shade(col, 1.4) + (int(255 * (1 - k)),), width=7)
    if WIN is not None and BATTLE <= tnow < BATTLE + SWEEP + 0.3:   # knockout shockwave
        k = min(1.0, (tnow - BATTLE) / SWEEP)
        R = max(30.0, DMAX * (1 - (1 - k) ** 2))
        x, y = AX + SC[0], AY + SC[1]
        a = int(255 * (1 - k * 0.7))
        d.ellipse([x - R, y - R, x + R, y + R], outline=shade(TEAMS[WIN][1], 1.6) + (a,), width=26)
        d.ellipse([x - R + 14, y - R + 14, x + R - 14, y + R - 14], outline=(255, 255, 255, a), width=8)
    # keep effects inside the arena
    lay.putalpha(Image.composite(lay.getchannel("A"), ZERO_L, EFFECT_MASK))
    img.alpha_composite(lay)

def text(img, xy, s, size, col=(255, 255, 255, 255), bold=True, max_w=960):
    d = ImageDraw.Draw(img)
    while size > 24 and d.textlength(s, font=F(size, bold), direction="rtl", language="fa") > max_w:
        size -= 2
    d.text(xy, s, font=F(size, bold), fill=col, anchor="mm", direction="rtl", language="fa")

def banner(img, title, sub, col, age, life=1.5, cy=AY + 120):
    a = min(1, age / 0.12, (life - age) / 0.3)
    if a <= 0:
        return
    pop = 1 + 0.3 * max(0, 1 - age / 0.18)
    lay, d = layer()
    hw, hh = 400 * pop, 92 * pop
    d.rounded_rectangle([W / 2 - hw, cy - hh, W / 2 + hw, cy + hh], 40, fill=shade(col, 0.5) + (int(235 * a),),
                        outline=shade(col, 1.5) + (int(255 * a),), width=6)
    img.alpha_composite(lay)
    text(img, (W / 2, cy - 42 * pop), sub, int(36 * pop), (255, 255, 255, int(220 * a)), bold=False, max_w=720)
    text(img, (W / 2, cy + 22 * pop), title, int(76 * pop), (255, 255, 255, int(255 * a)), max_w=720)

def shake_offset(tnow):
    amp = 0.0
    for t0, dur, A in shakes:
        if t0 <= tnow < t0 + dur:
            amp = max(amp, A * (1 - (tnow - t0) / dur))
    if amp <= 0:
        return 0, 0
    r = random.Random(int(tnow * 1000))
    return int(r.uniform(-amp, amp)), int(r.uniform(-amp, amp))

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
sim_frames = len(frames_grid)
final_frame = None
PREVIEW_AT = sorted({int(1.0 * FPS)} | {int((p["t0"] + 0.35) * FPS) for p in powers}
                    | {int((e["t1"] - 0.15) * FPS) for e in effects if e["type"] == "rpg"}
                    | {int((BATTLE + 0.6) * FPS), int((SIM_END + 1.4) * FPS)})
for fi in range(N):
    tnow = fi / FPS
    img = BG.copy()
    text(img, (W / 2, 200), HOOK, 74)
    text(img, (W / 2, 290), SUB, 44, (255, 255, 255, 170), bold=False)
    if tnow < SIM_END:
        k = min(fi, sim_frames - 1)
        arena = BG.copy()
        draw_grid(arena, frames_grid[k])
        draw_balls(arena, frames_balls[k], tnow)
        draw_effects(arena, tnow)
        dx, dy = shake_offset(tnow)
        box = (AX - 10, AY - 130, AX + AS + 10, AY + AS + 10)
        img.paste(arena.crop(box), (box[0] + dx, box[1] + dy))
        share = frames_share[k]
        draw_bar(img, share, hl=int(np.argmax(share)))
        for p in powers:
            if p["t0"] <= tnow < p["t0"] + 1.5:
                banner(img, POWER_NAME[p["kind"]] + "!", f"قدرت ویژه‌ی {TEAMS[p['team']][0]}", TEAMS[p["team"]][1], tnow - p["t0"])
        if BATTLE - FRENZY <= tnow < BATTLE:
            pulse = 0.5 + 0.5 * math.sin((tnow - (BATTLE - FRENZY)) * 2 * math.pi * 2)
            lay, d = layer()
            for w_, a_ in ((30, 50), (16, 110), (6, 220)):
                d.rounded_rectangle([AX - 14, AY - 14, AX + AS + 14, AY + AS + 14], 26,
                                    outline=(255, 50, 50, int(a_ * (0.35 + 0.65 * pulse))), width=w_)
            img.alpha_composite(lay)
        if tnow < BATTLE:
            left = max(0, math.ceil(BATTLE - tnow))
            urgent = BATTLE - tnow <= FRENZY
            tc = (255, 90, 90, 255) if urgent else (255, 255, 255, 200)
            tsize = 64 + (int(14 * (1 - (BATTLE - tnow) % 1)) if urgent else 0)
            label = f"{fa(left)} ثانیه‌ی آخر!" if urgent else f"۰:{fa(left).rjust(2, '۰')}"
            text(img, (W / 2, AY + AS + 90), label, tsize, tc)
        else:
            if tnow < BATTLE + 0.15:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (1 - (tnow - BATTLE) / 0.15)))))
            pop = 1 + 0.3 * max(0, 1 - (tnow - BATTLE) / 0.2)
            text(img, (W / 2, AY + AS + 95), "ضربه‌ی آخر!", int(72 * pop), shade(TEAMS[WIN][1], 1.5) + (255,))
    else:
        bt = tnow - SIM_END
        if final_frame is None:
            final_frame = BG.copy()
            draw_grid(final_frame, frames_grid[-1])
            draw_bar(final_frame, frames_share[-1], hl=WIN)
        img = final_frame.copy()
        text(img, (W / 2, 200), HOOK, 74)
        text(img, (W / 2, 290), SUB, 44, (255, 255, 255, 170), bold=False)
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(min(1, bt / 0.3) * 150))))
        lay, d = layer()
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
        img.alpha_composite(lay)
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
    if os.environ.get("PREVIEW") and fi in PREVIEW_AT:
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
yt_title, yt_tags = captions.youtube(FORMAT, names, cup.ROUND_NAMES[CUP_R] if FORMAT == "cup" else None)
meta = {"seed": SEED, "format": FORMAT, "teams": names, "winner": TEAMS[WIN][0], "lead_pct_at_whistle": WIN_PCT,
        "powers": [[p["kind"], TEAMS[p["team"]][0]] for p in powers], "duration": round(DUR, 2),
        "instagram_caption": caption, "first_comment": first,
        "youtube_title": yt_title, "youtube_tags": yt_tags,
        "cover_ms": int((POWER_TIMES[1] + 0.4) * 1000)}
with open(os.path.splitext(OUT)[0] + ".json", "w", encoding="utf-8") as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=2)
print("done", OUT)

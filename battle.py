"""Territory-war battle reel ("pong wars" style) for barkhord.tv.

Usage: python3 battle.py OUT.mp4 SEED FORMAT      FORMAT = derby | cities | colors
Each team owns a region of a grid. Its ball flies through its own cells and
captures any enemy cell it touches (then bounces). A live bar shows each team's
share; when the clock runs out the biggest share wins. Writes OUT.json with the
caption, first comment and cover frame like reel_generator.py.
"""
import math, colorsys, wave, subprocess, sys, os, json, random, glob, shutil, tempfile, datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1]
SEED = int(sys.argv[2])
FORMAT = sys.argv[3]
EN = FORMAT == "worldcup"          # the YouTube series is in English, left-to-right
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
if EN:
    FONT = glob.glob(f"{FONT_DIR}/package/fonts/ttf/Vazirmatn-Black.ttf")[0]
    FONT_MED = glob.glob(f"{FONT_DIR}/package/fonts/ttf/Vazirmatn-SemiBold.ttf")[0]
RQ = ImageFont.Layout.RAQM
FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
def fa(n): return str(n) if EN else str(n).translate(FA)
_fonts = {}
def F(size, bold=True):
    key = (size, bold)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(FONT if bold else FONT_MED, size, layout_engine=RQ)
    return _fonts[key]
def possessive(n): return n + ("'" if n.endswith("s") else "'s")
def hexc(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

# ---------------- teams per format ----------------
CITY_COLORS = ["#E63946", "#2A9DF4", "#F4B400", "#2DC653", "#A855F7", "#FF7A1A"]
TEAM_FLAGS = None
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
elif FORMAT == "request":     # a viewer's requested match: MATCH="نهاوند,تبریز"
    names = [s.strip() for s in os.environ["MATCH"].split(",")][:2]
    cols = rng.choice([("#E63946", "#2A9DF4"), ("#FF7A1A", "#7C4DFF"), ("#F4B400", "#1F63C6"),
                       ("#2DC653", "#FF4FA3"), ("#14B8A6", "#FF7A1A"), ("#A855F7", "#F4B400")])   # always two clearly different colours
    TEAMS = [(names[i], hexc(cols[i])) for i in range(2)]
    HOOK, SUB = f"{names[0]} یا {names[1]}؟", "بازی درخواستی شما"
    CTA_END = "بازی بعدی رو کامنت کن"
elif FORMAT == "cup":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import cup
    CUP_STATE, CUP_R, CUP_M, ca_, cb_ = cup.next_match(SEED)
    col_a, col_b = cup.colors_for(CUP_R, CUP_M, CUP_STATE["season"])
    TEAMS = [(ca_, hexc(col_a)), (cb_, hexc(col_b))]
    HOOK, SUB = f"{ca_} یا {cb_}؟", "جام شهرها · " + cup.match_label(CUP_R, CUP_M)
    CTA_END = ""
elif FORMAT == "worldcup":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import worldcup as wc
    WC_STATE, WC_R, WC_M, code_a, code_b = wc.next_match(SEED)
    CODES = [code_a, code_b]
    col_a, col_b = wc.colors_for(WC_R, WC_M, WC_STATE["season"])
    TEAMS = [(wc.name(code_a), hexc(col_a)), (wc.name(code_b), hexc(col_b))]
    TEAM_FLAGS = [Image.open(wc.flag_path(c)).convert("RGBA") for c in CODES]
    HOOK, SUB = f"{TEAMS[0][0]} vs {TEAMS[1][0]}", "World Cup of Countries · " + wc.match_label(WC_R, WC_M)
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
BATTLE, FINISH, OUTRO = 15.0, 2.3, 4.6      # fight, knockout sweep + K.O., winner podium
SIM_END = BATTLE + FINISH
INTRO = 2.8 if NT == 2 else 0.0              # wrestling-style entrance before the fight
DUR = INTRO + SIM_END + OUTRO
N = int(DUR * FPS)
AX, AY, AS = 60, 540, 960           # arena square
GN = 25 if FORMAT in ("cup", "worldcup", "request") else 24  # grid cells per side (odd count = no ties)
CS = AS / GN
BR = 24 if EN else 17               # ball radius (bigger for flag balls)
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
    if EN and vertical:     # left-to-right: first team on the left, like the bar
        grid = (1 - grid).astype(np.int8)
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
POWER_NAME = {"giant": "توپ غول‌پیکر", "rpg": "آرپی‌جی", "lightning": "رعد و برق", "clone": "تکثیر",
              "hammer": "چکش غول‌پیکر", "shield": "سپر دفاعی"}
if EN:
    POWER_NAME = {"giant": "GIANT BALL", "rpg": "RPG", "lightning": "THUNDERSTORM", "clone": "CLONES",
                  "hammer": "GIANT HAMMER", "shield": "SHIELD"}
FRENZY = 5.0                         # the last seconds: faster balls, more powers
POWER_TIMES = [rng.uniform(2.0, 2.6), rng.uniform(5.8, 6.6), rng.uniform(8.4, 9.0),
               BATTLE - rng.uniform(4.3, 4.0), BATTLE - rng.uniform(2.3, 2.0)]
import powers as PW
TODAY = datetime.date.fromisoformat(os.environ["TODAY"]) if os.environ.get("TODAY") else PW.today_tehran()
POWER_KINDS, SHIELD_ON = PW.pick(rng, TODAY)        # a few powers per video, new ones first (powers.py)
NEW_POWERS = {k for k in POWER_KINDS if PW.is_new(k, TODAY)}
# defence: a mid-match RPG or hammer hits a shield the other side raises just in time
BLOCK_IDX = None
if SHIELD_ON:
    _cands = [i for i in (1, 2, 3, 4) if POWER_KINDS[i] == "rpg"] or [i for i in (1, 2, 3, 4) if POWER_KINDS[i] == "hammer"]
    if not _cands and PW.is_new("shield", TODAY):
        POWER_KINDS[3] = "hammer" if "hammer" in PW.ACTIVE else "rpg"
        _cands = [3]
    BLOCK_IDX = _cands[0] if _cands else None
if BLOCK_IDX is not None and PW.is_new("shield", TODAY):
    NEW_POWERS.add("shield")
HAMMER_L, HAMMER_HL, HAMMER_HT = 330, 220, 135     # handle length, head length and thickness (px)
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

BANNER_TOP, BANNER_LOW = AY + 120, AY + AS - 130

def raise_shield(tx, ty, rad, t1, attacker, cy=BANNER_LOW, lead=0.42):
    """The defender throws up a dome over the target just before the hit; returns the radius that still gets through."""
    owner = int(grid[min(GN - 1, int(ty // CS)), min(GN - 1, int(tx // CS))])
    defender = owner if owner != attacker else next(t for t in range(NT) if t != attacker)
    powers.append({"kind": "shield", "t0": t1 - lead, "team": defender, "cy": cy})
    effects.append({"type": "shield", "t0": t1 - lead, "t1": t1, "x": tx, "y": ty, "rad": rad * 1.1,
                    "team": defender, "seed": rng.randrange(10 ** 6)})
    return rad * 0.32

def trigger_power(kind, t0, team, blocked=False):
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
        hit = raise_shield(tx, ty, rad, t1, team) if blocked else rad
        effects.append({"type": "rpg", "t0": t0, "t1": t1, "x0": b[0], "y0": b[1], "x1": tx, "y1": ty, "team": team, "rad": hit})
        pending.append((t1, lambda: capture_disc(tx, ty, hit, team, t1)))
        shakes.append((t1, 0.45, 20))
    elif kind == "hammer":
        rad = 5.3 * CS
        tx, ty = enemy_target(team, rad)
        t1 = t0 + 0.55
        # its banner goes where the raised hammer and the impact are not; a shield's banner takes the other spot
        powers[-1]["cy"] = BANNER_TOP if ty > 740 else BANNER_LOW
        # a shield against the hammer comes up during the wind-up; its banner sits under the arena, clear of the swing
        hit = raise_shield(tx, ty, rad, t1, team, cy=AY + AS + 100, lead=0.3) if blocked else rad
        side = 1 if tx < AS / 2 else -1          # the handle's pivot sits toward the middle
        effects.append({"type": "hammer", "t0": t0, "t1": t1, "x": tx, "y": ty, "side": side, "team": team,
                        "rad": hit, "seed": rng.randrange(10 ** 6)})
        pending.append((t1, lambda: capture_disc(tx, ty, hit, team, t1)))
        shakes.append((t1, 0.6, 34 if not blocked else 18))
    elif kind == "lightning":
        rad = 2.4 * CS
        effects.append({"type": "storm", "t0": t0, "t1": t0 + 1.75, "team": team, "seed": rng.randrange(10 ** 6)})
        powers[-1]["cy"] = BANNER_LOW
        for k in range(5):
            ts = t0 + 0.2 + k * 0.2
            def strike(ts=ts, k=k):
                x, y = enemy_target(team, rad)
                # only two of the five strikes flash the screen: under 3 flashes a second (photosensitivity)
                effects.append({"type": "bolt", "t0": ts, "x": x, "y": y, "team": team,
                                "seed": rng.randrange(10 ** 6), "rad": rad, "flash": k in (0, 3)})
                capture_disc(x, y, rad, team, ts)
            pending.append((ts, strike))
            shakes.append((ts, 0.22, 16))
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
                trigger_power(POWER_KINDS[idx], pt, int(np.argmin(share_now)), blocked=(idx == BLOCK_IDX))
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
CARD_SUB = "Took the whole map!" if EN else "کل زمین رو گرفت!"
FOLLOW_LINE = "Subscribe to see who wins it all" if EN else "فالو کن که بعدی رو از دست ندی"
if FORMAT == "worldcup":
    WC_INFO = wc.record(WC_STATE, WC_R, WC_M, CODES[WIN])
    if WC_INFO["champion"]:
        CARD_SUB = "WORLD CHAMPION!"
        CTA_END = "A new season starts next!"
    else:
        CARD_SUB = f"Advances to the {WC_INFO['advanced_to']}"
        na, nb = WC_INFO["next"]
        CTA_END = f"Next: {wc.name(na)} vs {wc.name(nb)}"
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
audio = np.zeros(int(SR * (SIM_END + OUTRO + 4)))
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
add(sfx.bell(2), 0.0, 0.75)                                                             # ding ding: fight!
add(sfx.drum_loop(BATTLE, 128, BATTLE - FRENZY), 0.0, 0.32)                            # beat under the fight
for k in range(int(FRENZY)):                                                              # countdown beeps
    add(tone(880 if k < 3 else 660, int(SR * 0.18), 14, 0.1), BATTLE - 1 - k, 0.7 if k < 3 else 0.5)
tb = BATTLE - FRENZY
while tb < BATTLE:                                                                        # heartbeat
    for off, g in ((0.0, 0.9), (0.16, 0.6)):
        add(np.sin(2 * np.pi * 55 * np.arange(int(SR * 0.18)) / SR) * np.exp(-np.arange(int(SR * 0.18)) / SR * 22), tb + off, g)
    tb += 0.5
for p in powers:
    if p["kind"] == "shield":
        add(sfx.shield_up(0.42), p["t0"], 0.6)
        continue
    add(sfx.rise(0.5), p["t0"], 0.45)
    if p["kind"] == "clone":
        for k in range(3):
            add(sfx.pop(600 + 250 * k), p["t0"] + 0.08 * k, 0.8)
for e in effects:
    if e["type"] == "rpg":
        add(sfx.whoosh(0.6, seed=int(e["t0"] * 100)), e["t0"], 0.55)
        add(sfx.boom(1.4, seed=int(e["t1"] * 100)), e["t1"], 1.0)
    elif e["type"] == "hammer":
        add(sfx.whoosh(0.3, seed=int(e["t0"] * 100), rising=False), e["t1"] - 0.22, 0.6)
        add(sfx.clang(seed=int(e["t1"] * 100)), e["t1"], 1.0)
        add(sfx.boom(1.2, seed=int(e["t1"] * 100) + 1), e["t1"], 0.55)
    elif e["type"] == "shield":
        add(sfx.shatter(seed=int(e["t1"] * 100)), e["t1"] + 0.02, 0.75)
    elif e["type"] == "bolt":
        add(sfx.thunderclap(1.6, seed=int(e["t0"] * 100)), e["t0"], 0.75)
    elif e["type"] == "storm":
        add(sfx.rain(e["t1"] - e["t0"] + 0.3, seed=int(e["t0"] * 100)), e["t0"], 0.35)
    elif e["type"] == "poof" and e["t0"] >= BATTLE:
        add(sfx.pop(420), e["t0"] + rng.uniform(0, 0.15), 0.6)
add(sfx.whistle(), BATTLE, 0.7)                               # time!
add(sfx.boom(2.0, seed=7), BATTLE + 0.1, 1.1)                  # final blow
add(sfx.whoosh(1.4, seed=8, rising=False), BATTLE + 0.15, 0.45)
KO_T = BATTLE + SWEEP
shakes.append((KO_T, 0.5, 24))
add(sfx.shatter(), KO_T, 0.9); add(sfx.boom(1.2, seed=11), KO_T, 1.0)
add(sfx.crowd(OUTRO, seed=12), SIM_END, 0.3)
add(sfx.bell(1), SIM_END + 0.55, 0.35)                         # crown lands
LAUGH_T0 = SIM_END + 0.6
LAUGH = sfx.laugh(seed=SEED % 1000)
LAUGH_ENV = sfx.envelope(LAUGH, FPS)
add(LAUGH, LAUGH_T0, 1.5)                                      # the winner laughs at the loser
add(sfx.sad_trombone(), LAUGH_T0 + len(LAUGH) / SR + 0.05, 0.5)  # wah wah wah waaah
full = np.zeros(int(SR * (DUR + 1)))
o = int(INTRO * SR)
full[o:o + len(audio)] += audio[: len(full) - o]
SHOUT_ENV = []
if INTRO:
    def add_abs(sig, t0, gain):
        s0 = int(t0 * SR); seg = full[s0:s0 + len(sig)]; seg += sig[: len(seg)] * gain
    add_abs(sfx.crowd(INTRO + 0.6, seed=13), 0.0, 0.35)
    for k, (t0, f0) in enumerate(((0.3, 150), (1.45, 185))):
        sh = sfx.shout(seed=SEED % 100 + k, f0=f0)
        SHOUT_ENV.append((t0, sfx.envelope(sh, FPS)))
        add_abs(sh, t0, 1.0)
    add_abs(sfx.boom(1.2, seed=14), 2.25, 0.9)                  # VS
audio = full
d = int(0.1 * SR); wet = np.zeros_like(audio); wet[d:] = audio[:-d] * 0.18
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
    for t in (list(range(NT)) if EN else list(range(NT))[::-1]):    # team 0 sits where reading starts
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
        cx = bx + slot * (t + 0.5) if EN else bx + bw - slot * (t + 0.5)
        pct = int(round(share[t] * 100))
        size = (44 if NT <= 2 else 36) + (6 if t == hl else 0)
        label = f"{TEAMS[t][0]} {pct}%" if EN else f"{TEAMS[t][0]} {fa(pct)}٪"
        if TEAM_FLAGS:
            tw = d.textlength(label, font=F(size))
            fl = TEAM_FLAGS[t].resize((60, 45), Image.LANCZOS)
            img.alpha_composite(fl, (int(cx - (tw + 72) / 2), int(by + bh + 46 - 22)))
            cx += 36
        d.text((cx, by + bh + 46), label, font=F(size), fill=shade(TEAMS[t][1], 1.35) + (255,),
               anchor="mm", direction="ltr" if EN else "rtl", language="en" if EN else "fa")

_sprites = {}
def flag_disc(t, diam):
    """Team flag cropped to a circle, diam px wide (cached)."""
    diam = max(8, int(diam) // 4 * 4)
    key = (t, diam)
    if key not in _sprites:
        fl = TEAM_FLAGS[t]
        side = min(fl.size)
        sq = fl.crop(((fl.width - side) // 2, (fl.height - side) // 2, (fl.width + side) // 2, (fl.height + side) // 2))
        sq = sq.resize((diam, diam), Image.LANCZOS)
        mask = Image.new("L", (diam, diam), 0)
        ImageDraw.Draw(mask).ellipse([0, 0, diam - 1, diam - 1], fill=255)
        sq.putalpha(mask)
        _sprites[key] = sq
    return _sprites[key]

def draw_balls(img, pos, tnow):
    lay = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for (x, y, t, giant, clone) in pos:
        cx, cy = (AX + x) * 2, (AY + y) * 2
        c = shade(TEAMS[t][1], 1.15)
        if TEAM_FLAGS:           # country balls: the flag inside a ring of the team color
            r = (GIANT_R * 2 * (1 + 0.06 * math.sin(tnow * 30))) if giant else BR * 2 * (1.25 if clone else 1.0)
            ring = 18 if giant else 8
            d.ellipse([cx - r - ring, cy - r - ring, cx + r + ring, cy + r + ring],
                      fill=(shade(TEAMS[t][1], 1.5) if giant else (255, 255, 255)) + (255,))
            d.ellipse([cx - r - ring / 2, cy - r - ring / 2, cx + r + ring / 2, cy + r + ring / 2], fill=c + (255,))
            sp = flag_disc(t, 2 * r)
            lay.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))
            continue
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
        if e["type"] == "hammer" and e["t1"] <= tnow < e["t1"] + 0.7:
            return True
        if e["type"] == "shield" and e["t0"] <= tnow < e["t1"] + 0.5:
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
        elif e["type"] == "bolt" and e["t0"] <= tnow < e["t0"] + 0.22:   # the bolt itself is drawn by draw_storm
            x1, y1 = AX + e["x"], AY + e["y"]
            if tnow >= e["t0"]:
                k = (tnow - e["t0"]) / 0.22
                R = e["rad"] * (0.6 + 0.8 * k)
                d.ellipse([x1 - R, y1 - R, x1 + R, y1 + R], outline=(255, 255, 255, int(255 * (1 - k))), width=6)
        elif e["type"] == "poof" and e["t0"] <= tnow < e["t0"] + 0.4:
            k = (tnow - e["t0"]) / 0.4
            x, y = AX + e["x"], AY + e["y"]
            R = 20 + 70 * k
            d.ellipse([x - R, y - R, x + R, y + R], outline=shade(col, 1.4) + (int(255 * (1 - k)),), width=7)
        elif e["type"] == "hammer" and e["t1"] <= tnow < e["t1"] + 0.7:      # impact: flash, cracks, dust ring
            k = (tnow - e["t1"]) / 0.7
            x, y = AX + e["x"], AY + e["y"]
            rad = max(e["rad"], 2.2 * CS)
            if k < 0.2:
                R = rad * (0.5 + 2.5 * k)
                d.ellipse([x - R, y - R, x + R, y + R], fill=(255, 255, 255, int(230 * (1 - k / 0.2))))
            a = int(255 * min(1, (1 - k) / 0.4))
            cr = random.Random(e["seed"])
            L = rad * 1.35 * ease_out(k / 0.18)
            for q in range(10):
                ang = q * 2 * math.pi / 10 + cr.uniform(-0.25, 0.25)
                pts = [(x, y)]
                for s in range(1, 6):
                    rr = L * s / 5
                    a2 = ang + cr.uniform(-0.28, 0.28)
                    pts.append((x + math.cos(a2) * rr, y + math.sin(a2) * rr))
                d.line(pts, fill=(25, 20, 35, a), width=9, joint="curve")
                d.line(pts, fill=(255, 235, 200, int(a * 0.55)), width=3, joint="curve")
            R = rad * (0.6 + 1.1 * ease_out(k))
            d.ellipse([x - R, y - R, x + R, y + R], outline=(235, 225, 205, int(200 * (1 - k))), width=int(10 + 26 * (1 - k)))
        elif e["type"] == "shield" and e["t0"] <= tnow < e["t1"] + 0.5:
            x, y, R = AX + e["x"], AY + e["y"], e["rad"]
            c2 = (110, 215, 255)                                 # energy blue, readable on any team colour
            if tnow < e["t1"]:                                   # dome grows in and hums
                k = ease_back((tnow - e["t0"]) / 0.22)
                Rk = R * max(0.05, k)
                flick = 0.85 + 0.15 * math.sin(tnow * 70)
                d.ellipse([x - Rk - 18, y - Rk - 18, x + Rk + 18, y + Rk + 18], outline=(70, 190, 255, int(170 * flick)), width=26)
                d.ellipse([x - Rk, y - Rk, x + Rk, y + Rk], fill=(130, 225, 255, int(125 * flick)))
                for ring_k, wd, al in ((1.0, 14, 255), (0.78, 6, 200), (0.52, 5, 160)):
                    rr = Rk * ring_k
                    d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(255, 255, 255, int(al * flick)) if ring_k == 1.0 else c2 + (int(al * flick),), width=wd)
                for q in range(6):                               # hex-like ribs
                    ang = q * math.pi / 3 + tnow * 1.5
                    d.line([x + math.cos(ang) * Rk * 0.52, y + math.sin(ang) * Rk * 0.52,
                            x + math.cos(ang) * Rk, y + math.sin(ang) * Rk], fill=c2 + (int(140 * flick),), width=4)
            else:                                                # shattered: shards fly out
                k = (tnow - e["t1"]) / 0.5
                sr = random.Random(e["seed"])
                for q in range(16):
                    ang = sr.uniform(0, 2 * math.pi)
                    dist = R * (0.5 + 1.0 * ease_out(k)) * sr.uniform(0.7, 1.15)
                    sx, sy = x + math.cos(ang) * dist, y + math.sin(ang) * dist
                    sz = sr.uniform(16, 34) * (1 - 0.5 * k)
                    rot = sr.uniform(0, 6.28) + k * 8
                    tri = [(sx + math.cos(rot + j * 2.1) * sz, sy + math.sin(rot + j * 2.1) * sz) for j in range(3)]
                    d.polygon(tri, fill=c2 + (int(230 * (1 - k)),))
                if k < 0.25:
                    d.ellipse([x - R, y - R, x + R, y + R], outline=(255, 255, 255, int(255 * (1 - k / 0.25))), width=14)
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

def draw_storm(img, tnow, dx=0, dy=0):
    for e in effects:
        if e["type"] != "storm" or not (e["t0"] <= tnow < e["t1"]):
            continue
        k = (tnow - e["t0"]) / (e["t1"] - e["t0"])
        dark = min(1, k / 0.12, (1 - k) / 0.2)
        lay, d = layer()
        d.rectangle([0, 0, W, H], fill=(8, 10, 30, int(120 * dark)))
        rr = random.Random(e["seed"])
        for q in range(150):                              # rain streaks falling at a slant
            x0 = rr.uniform(-200, W + 100)
            sp = rr.uniform(1700, 2400)
            y0 = (rr.uniform(0, H) + tnow * sp) % (H + 200) - 100
            d.line([x0 + 0.25 * y0, y0, x0 + 0.25 * (y0 + 46), y0 + 46], fill=(190, 210, 255, int(150 * dark)), width=3)
        img.alpha_composite(lay)
    lay, d = layer()
    drawn = False
    for e in effects:                                     # bolts from the sky, over the dark storm
        if e["type"] != "bolt" or not (e["t0"] - 0.05 <= tnow < e["t0"] + 0.22):
            continue
        drawn = True
        br = random.Random(e["seed"])
        col = TEAMS[e["team"]][1]
        x1, y1 = AX + e["x"] + dx, AY + e["y"] + dy
        top = 120
        pts = [(x1 + br.uniform(-90, 90), top)]
        for q in range(1, 10):
            f = q / 10
            pts.append((pts[0][0] + (x1 - pts[0][0]) * f + br.uniform(-42, 42), top + (y1 - top) * f))
        pts.append((x1, y1))
        a = 255 if tnow >= e["t0"] else 110
        d.line(pts, fill=(190, 210, 255, int(a * 0.3)), width=70, joint="curve")
        for q0 in (3, 6):                                 # side branches
            bx, by = pts[q0]
            bpts = [(bx, by)]
            sgn = br.choice([-1, 1])
            for q in range(1, 4):
                bpts.append((bx + sgn * q * br.uniform(28, 50), by + q * br.uniform(30, 52)))
            d.line(bpts, fill=shade(col, 1.4) + (int(a * 0.85),), width=12, joint="curve")
            d.line(bpts, fill=(255, 255, 255, int(a * 0.85)), width=5, joint="curve")
        d.line(pts, fill=shade(col, 1.3) + (a,), width=28, joint="curve")
        d.line(pts, fill=(255, 255, 255, a), width=12, joint="curve")
    if drawn:
        img.alpha_composite(lay)
    for e in effects:                                     # flash of each strike
        if e["type"] == "bolt" and e.get("flash") and e["t0"] <= tnow < e["t0"] + 0.13:
            fa_ = 1 - (tnow - e["t0"]) / 0.13
            img.alpha_composite(Image.new("RGBA", (W, H), (235, 240, 255, int(150 * fa_))))

def _hammer_shape(d, P, th, s, col, a, ghost=False):
    """Hammer at angle th (radians) around pivot P, drawn into a 2x layer."""
    u = (math.cos(th), math.sin(th)); v = (-u[1], u[0])
    L, HL, HT = HAMMER_L * s * 2, HAMMER_HL * s * 2, HAMMER_HT * s * 2
    Px, Py = P[0] * 2, P[1] * 2
    Hc = (Px + u[0] * L, Py + u[1] * L)
    def quad(c, a0, a1, b0, b1):   # box from a0..a1 along u and b0..b1 along v, around point c
        return [(c[0] + u[0] * p + v[0] * q, c[1] + u[1] * p + v[1] * q) for p, q in ((a0, b0), (a1, b0), (a1, b1), (a0, b1))]
    if not ghost:
        d.polygon(quad((Px, Py), -70 * s, L - HT / 2, -15 * s, 15 * s), fill=(120, 72, 40, a), outline=(60, 34, 18, a), width=int(5 * s))
        d.polygon(quad((Px, Py), -70 * s, 90 * s, -17 * s, 17 * s), fill=shade(col, 0.7) + (a,))
    steel = (128, 134, 150) if not ghost else shade(col, 1.3)
    d.polygon(quad(Hc, -HT / 2, HT / 2, -HL / 2, HL / 2), fill=steel + (a,), outline=(38, 38, 52, a), width=int(10 * s) if not ghost else 0)
    if ghost:
        return
    for sgn in (-1, 1):            # striking faces
        d.polygon(quad(Hc, -HT / 2 - 6 * s, HT / 2 + 6 * s, sgn * HL / 2 - 30 * s if sgn > 0 else -HL / 2, HL / 2 if sgn > 0 else -HL / 2 + 30 * s),
                  fill=(84, 88, 104, a), outline=(38, 38, 52, a), width=int(8 * s))
    d.polygon(quad(Hc, -HT / 2, HT / 2, -20 * s, 20 * s), fill=col + (a,))
    d.line([(Hc[0] - u[0] * HT * 0.32 - v[0] * HL * 0.3, Hc[1] - u[1] * HT * 0.32 - v[1] * HL * 0.3),
            (Hc[0] - u[0] * HT * 0.32 + v[0] * HL * 0.3, Hc[1] - u[1] * HT * 0.32 + v[1] * HL * 0.3)],
           fill=(225, 230, 240, int(a * 0.8)), width=int(8 * s))

def draw_hammer(img, tnow, dx=0, dy=0):
    for e in effects:
        if e["type"] != "hammer" or not (e["t0"] <= tnow < e["t1"] + 0.55):
            continue
        side = e["side"]
        X, Y = AX + e["x"] + dx, AY + e["y"] + dy
        hc = (X, Y - HAMMER_HL / 2 + 14)
        P = (hc[0] + side * HAMMER_L, hc[1])
        th_imp = math.pi if side == 1 else 2 * math.pi
        th_up = 1.5 * math.pi
        th_back = th_up + side * math.radians(28)
        rel, s, a, ghosts = tnow - e["t0"], 1.0, 255, []
        if rel < 0.38:                                     # pops in and winds up
            s = 0.35 + 0.65 * ease_back(rel / 0.14)
            th = th_up + (th_back - th_up) * ease_out(rel / 0.38)
        elif tnow < e["t1"]:                               # slam
            k = (rel - 0.38) / (e["t1"] - e["t0"] - 0.38)
            th = th_back + (th_imp - th_back) * k * k
            ghosts = [th_back + (th_imp - th_back) * max(0, k - j * 0.16) ** 2 for j in (1, 2, 3)]
        else:
            h = tnow - e["t1"]
            if h < 0.25:                                   # small rebound
                th = th_imp + (th_up - th_imp) * 0.07 * math.sin(h / 0.25 * math.pi)
            else:                                          # lifts away and fades
                k = (h - 0.25) / 0.3
                th = th_imp + (th_up - th_imp) * 0.35 * ease_out(k)
                a = int(255 * (1 - k))
        lay = Image.new("RGBA", (W * 2, H * 2), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        col = TEAMS[e["team"]][1]
        for j, g in enumerate(ghosts):
            _hammer_shape(d, P, g, s, col, int(110 / (j + 1)), ghost=True)
        _hammer_shape(d, P, th, s, col, a)
        img.alpha_composite(lay.resize((W, H), Image.LANCZOS))

def header(img):
    if not TEAM_FLAGS:
        text(img, (W / 2, 200), HOOK, 74)
        return
    size = text(img, (W / 2, 200), HOOK, 72, max_w=640)
    tw = ImageDraw.Draw(img).textlength(HOOK, font=F(size))
    for t, side in ((0, -1), (1, 1)):
        fl = TEAM_FLAGS[t].resize((120, 90), Image.LANCZOS)
        x = W / 2 + side * (tw / 2 + 28) - (120 if side < 0 else 0)
        img.alpha_composite(Image.new("RGBA", (128, 98), (255, 255, 255, 255)), (int(x) - 4, 200 - 49))
        img.alpha_composite(fl, (int(x), 200 - 45))

def text(img, xy, s, size, col=(255, 255, 255, 255), bold=True, max_w=960, stroke=0):
    d = ImageDraw.Draw(img)
    dr, lg = ("ltr", "en") if EN else ("rtl", "fa")
    if not any("\u0600" <= ch <= "\u06ff" for ch in s):     # Latin-only text (VS, K.O.!) reads left to right
        dr, lg = "ltr", "en"
    while size > 24 and d.textlength(s, font=F(size, bold), direction=dr, language=lg) > max_w:
        size -= 2
    d.text(xy, s, font=F(size, bold), fill=col, anchor="mm", direction=dr, language=lg,
           stroke_width=stroke, stroke_fill=(15, 10, 25, col[3] if len(col) > 3 else 255))
    return size

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

import mascot as MS
BODY = [TEAM_FLAGS[t] if TEAM_FLAGS else None for t in range(NT)]
_glows = {}
def glow(t, r):
    key = (t, r)
    if key not in _glows:
        g = Image.new("RGBA", (r * 4, r * 4), (0, 0, 0, 0))
        ImageDraw.Draw(g).ellipse([r * 0.6, r * 0.6, r * 3.4, r * 3.4], fill=TEAMS[t][1] + (120,))
        _glows[key] = g.filter(ImageFilter.GaussianBlur(r * 0.35))
    return _glows[key]

def put(img, sprite, cx, cy):
    img.alpha_composite(sprite, (int(cx - sprite.width / 2), int(cy - sprite.height / 2)))

def ease_out(k):
    k = max(0.0, min(1.0, k))
    return 1 - (1 - k) ** 3

def ease_back(k):
    k = max(0.0, min(1.0, k)); c = 1.7
    return 1 + (c + 1) * (k - 1) ** 3 + c * (k - 1) ** 2

def env_at(env, t):
    i = int(t * FPS)
    return float(env[i]) if 0 <= i < len(env) else 0.0

import dialects
DIALECT = [None if EN else dialects.lines(TEAMS[t][0]) for t in range(NT)]
INK = (25, 20, 40)

def bubble(img, cx, cy, s, tail_to, age, max_w=430, size=46):
    """Speech bubble with s inside, its tail pointing at tail_to; pops in over 0.22 s."""
    if age < 0 or not s:
        return
    k = max(0.0, ease_back(age / 0.22))
    if k < 0.05:
        return
    d = ImageDraw.Draw(img)
    fsz = size
    while fsz > 28 and d.textlength(s, font=F(fsz), direction="rtl", language="fa") > max_w:
        fsz -= 2
    tw = d.textlength(s, font=F(fsz), direction="rtl", language="fa")
    bw, bh = (tw + 60) * k, (fsz + 46) * k
    x0, y0, x1, y1 = cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2
    bx = min(max(tail_to[0], x0 + 46 * k), x1 - 46 * k)
    tip = (bx + (tail_to[0] - bx) * 0.45, y1 + 52 * k)
    tail = [(bx - 22 * k, y1 - 6), (bx + 22 * k, y1 - 6), tip]
    lay, ld = layer()
    ld.rounded_rectangle([x0 - 5, y0 - 5, x1 + 5, y1 + 5], int(30 * k) + 5, fill=INK + (255,))
    ld.line(tail + [tail[0]], fill=INK + (255,), width=10, joint="curve")
    ld.polygon(tail, fill=(255, 255, 255, 255))
    ld.rounded_rectangle([x0, y0, x1, y1], int(30 * k), fill=(255, 255, 255, 255))
    img.alpha_composite(lay)
    text(img, (cx, cy + 2 * k), s, max(24, int(fsz * k)), INK + (255,), max_w=max_w)

STAGE_Y = AY + 390
def draw_intro(v):
    img = BG.copy()
    header(img)
    text(img, (W / 2, 290), SUB, 44, (255, 255, 255, 170), bold=False)
    draw_bar(img, [1.0 / NT] * NT)
    lay, d = layer()
    d.rounded_rectangle([AX - 8, AY - 8, AX + AS + 8, AY + AS + 8], 22, fill=(24, 20, 44, 255))
    img.alpha_composite(lay)
    for t, (t_in, x_from, x_to) in enumerate(((0.0, -260, 300), (1.15, W + 260, 780))):
        k = v - t_in
        if k < 0:
            continue
        x = x_from + (x_to - x_from) * ease_out(k / 0.32)
        sh_t0, sh_env = SHOUT_ENV[t]
        mouth = 0.15 + 0.85 * env_at(sh_env, v - sh_t0)
        arms = ease_out((k - 0.22) / 0.25)
        y = STAGE_Y - abs(math.sin(k * 9)) * 10 * min(1, k / 0.3)
        put(img, glow(t, 150), x, y)
        put(img, MS.mascot(BODY[t], TEAMS[t][1], 140, "angry", arms, mouth, k), x, y)
        text(img, (x, AY + 660), TEAMS[t][0], 62, shade(TEAMS[t][1], 1.45) + (255,), max_w=440, stroke=4)
        if DIALECT[t]:                     # the city's own catchphrase as it shouts
            bubble(img, x, STAGE_Y - 300, DIALECT[t][0], (x + (60 if x < W / 2 else -60), STAGE_Y - 150), v - SHOUT_ENV[t][0], max_w=400)
    if v >= 2.25:
        k = (v - 2.25) / 0.15
        size = int(170 * (1 + 2.0 * (1 - ease_out(k))))
        text(img, (W / 2, STAGE_Y + 10), "VS", min(size, 420), (255, 210, 63, 255), max_w=900, stroke=10)
    return img

def big_word(img, word, t_rel, col, life):
    if not (0 <= t_rel < life):
        return
    pop = 1 + 1.2 * (1 - ease_out(t_rel / 0.16))
    a = int(255 * min(1, (life - t_rel) / 0.2))
    text(img, (W / 2, AY + AS / 2), word, int(180 * pop), col[:3] + (a,), max_w=980, stroke=12)

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
                    | {int((e["t1"] - 0.15) * FPS) for e in effects if e["type"] in ("rpg", "hammer")}
                    | {int((e["t0"] + 0.25) * FPS) for e in effects if e["type"] == "hammer"}
                    | {int((e["t1"] + 0.1) * FPS) for e in effects if e["type"] in ("hammer", "shield")}
                    | {int((e["t0"] + 0.03) * FPS) for e in effects if e["type"] == "bolt"}
                    | {int((BATTLE + 0.6) * FPS), int((SIM_END + 1.4) * FPS)})
INTRO_F = int(round(INTRO * FPS))
PREVIEW_V = ({INTRO_F + f for f in PREVIEW_AT} | {int(0.8 * FPS), int(1.9 * FPS), int(2.45 * FPS),
             INTRO_F + int((KO_T + 0.2) * FPS), INTRO_F + int((SIM_END + 2.0) * FPS)})
LOSER = int(np.argsort(LEAD_SHARE)[-2])
FAST = os.environ.get("PREVIEW") == "fast"     # draw only the preview frames
for fv in range(N):
    if FAST and fv not in PREVIEW_V:
        continue
    if fv < INTRO_F:
        img = draw_intro(fv / FPS)
        ImageDraw.Draw(img).text((W / 2, H - 110), "BARKHORD" if EN else "@barkhord.tv", font=F(36, False), fill=(255, 255, 255, 110), anchor="mm")
        ff.stdin.write(img.convert("RGB").tobytes())
        if os.environ.get("PREVIEW") and fv in PREVIEW_V:
            img.convert("RGB").save(f"{OUT}.preview_{fv:04d}.png")
        continue
    fi = fv - INTRO_F
    tnow = fi / FPS
    img = BG.copy()
    header(img)
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
        draw_storm(img, tnow, dx, dy)                  # dark sky, rain, bolts and flashes under the banners
        for p in powers:
            if p["t0"] <= tnow < p["t0"] + 1.5:
                nm = TEAMS[p["team"]][0]
                if p["kind"] == "shield":   # the defence banner sits low so both banners can be read
                    sub = (f"NEW · {nm} defends" if EN else f"جدید · دفاع {nm}") if "shield" in NEW_POWERS else (f"{nm} defends" if EN else f"دفاع {nm}")
                    banner(img, POWER_NAME["shield"] + "!", sub, TEAMS[p["team"]][1], tnow - p["t0"], life=1.3, cy=p["cy"])
                else:
                    if p["kind"] in NEW_POWERS:
                        sub = f"NEW POWER · {nm}" if EN else f"قدرت جدید · {nm}"
                    else:
                        sub = possessive(nm) + " special power" if EN else f"قدرت ویژه‌ی {nm}"
                    banner(img, POWER_NAME[p["kind"]] + "!", sub, TEAMS[p["team"]][1], tnow - p["t0"], cy=p.get("cy") or BANNER_TOP)
        draw_hammer(img, tnow, dx, dy)                 # over the banners: the swing is the show
        if INTRO:
            big_word(img, "FIGHT!" if EN else "شروع!", tnow, (255, 230, 80), 0.7)
        big_word(img, "K.O.!", tnow - KO_T, (255, 70, 70), SIM_END - KO_T + 0.05)
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
            if EN:
                label = (f"{left} SECOND{'S' if left != 1 else ''} LEFT!") if urgent else f"0:{left:02d}"
            else:
                label = f"{fa(left)} ثانیه‌ی آخر!" if urgent else f"۰:{fa(left).rjust(2, '۰')}"
            if not any(p.get("cy", 0) > AY + AS and p["t0"] <= tnow < p["t0"] + 1.3 for p in powers):
                text(img, (W / 2, AY + AS + 90), label, tsize, tc)     # (a shield banner may sit here)
        else:
            if tnow < BATTLE + 0.15:
                img.alpha_composite(Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (1 - (tnow - BATTLE) / 0.15)))))
            pop = 1 + 0.3 * max(0, 1 - (tnow - BATTLE) / 0.2)
            text(img, (W / 2, AY + AS + 95), "FINAL BLOW!" if EN else "ضربه‌ی آخر!", int(72 * pop), shade(TEAMS[WIN][1], 1.5) + (255,))
    else:
        bt = tnow - SIM_END
        if final_frame is None:
            final_frame = BG.copy()
            draw_grid(final_frame, frames_grid[-1])
            draw_bar(final_frame, frames_share[-1], hl=WIN)
        img = final_frame.copy()
        header(img)
        text(img, (W / 2, 290), SUB, 44, (255, 255, 255, 170), bold=False)
        img.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, int(min(1, bt / 0.3) * 185))))
        lay, d = layer()
        pos = np.array([W / 2, AY + AS / 2]) + CV * bt + np.array([0, 900]) * bt ** 2 / 2
        a = int(255 * max(0, 1 - bt / OUTRO))
        for q in range(NP):
            x, y = pos[q]
            d.ellipse([x - CSZ[q], y - CSZ[q], x + CSZ[q], y + CSZ[q]], fill=CCOL[q] + (a,))
        img.alpha_composite(lay)
        # winner on the podium: pops in, crown drops, laughs with the mouth in sync
        k_in = bt / 0.4
        r_w = int(185 * max(0.2, ease_back(k_in)))
        lt = (SIM_END + bt) - LAUGH_T0
        mouth = 0.2 + 0.8 * env_at(LAUGH_ENV, lt) if lt >= 0 else 0.25
        bounce = abs(math.sin(bt * 7)) * 14 * (env_at(LAUGH_ENV, lt) if lt >= 0 else 0)
        wx, wy = W / 2, STAGE_Y - 20 - bounce
        put(img, glow(WIN, 190), wx, wy)
        put(img, MS.mascot(BODY[WIN], TEAMS[WIN][1], r_w, "laugh", 0.85 + 0.15 * math.sin(bt * 9), mouth, bt), wx, wy)
        if bt >= 0.2:
            kc = ease_out((bt - 0.2) / 0.35)
            cr = MS.crown(185)
            cy_land = wy - 0.86 * 185 - cr.height / 2 + 4
            put(img, cr, wx, cy_land - (1 - kc) * 420)
        # loser in the corner, crying
        if bt >= 0.3:
            ly = AY + AS - 120 + 200 * (1 - ease_out((bt - 0.3) / 0.3))
            put(img, MS.mascot(BODY[LOSER], TEAMS[LOSER][1], 80, "sad", 0.0, 0.0, bt), AX + 130 + math.sin(bt * 30) * 2, ly)
        if DIALECT[WIN]:                   # the winner's taunt in its own dialect
            bubble(img, W - 80 - 215, AY + 20, DIALECT[WIN][1], (wx + 110, wy - 120), bt - 0.75, max_w=400)
        if bt >= 0.35:
            text(img, (W / 2, AY + 680), TEAMS[WIN][0], 92, (255, 255, 255, 255), max_w=760, stroke=6)
            text(img, (W / 2, AY + 765), CARD_SUB, 44, shade(TEAMS[WIN][1], 1.5) + (255,), bold=False, max_w=760, stroke=3)
        if bt > 0.7:
            text(img, (W / 2, AY + AS + 90), CTA_END, 58, shade(TEAMS[WIN][1], 1.45) + (255,))
        if bt > 1.2:
            text(img, (W / 2, AY + AS + 170), FOLLOW_LINE, 42, (255, 255, 255, 200), bold=False)
    ImageDraw.Draw(img).text((W / 2, H - 110), "BARKHORD" if EN else "@barkhord.tv", font=F(36, False), fill=(255, 255, 255, 110), anchor="mm")
    ff.stdin.write(img.convert("RGB").tobytes())
    if os.environ.get("PREVIEW") and fv in PREVIEW_V:
        img.convert("RGB").save(f"{OUT}.preview_{fv:04d}.png")
ff.stdin.close(); ff.wait()
shutil.rmtree(WORK, ignore_errors=True)

# ---------------- caption ----------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import captions
names = [t[0] for t in TEAMS]
if FORMAT == "cup":
    caption, first = captions.cup(rng, names, TEAMS[WIN][0], cup.ROUND_NAMES[CUP_R], CUP_INFO)
    cup.save(CUP_STATE)
elif FORMAT == "worldcup":
    nxt = [wc.name(c) for c in WC_INFO["next"]] if WC_INFO["next"] else None
    caption, first = captions.worldcup(rng, names, TEAMS[WIN][0], wc.ROUND_NAMES[WC_R], WC_INFO, nxt)
    wc.save(WC_STATE)
else:
    caption, first = getattr(captions, FORMAT)(rng, names, TEAMS[WIN][0])
shown_new = [k for k in dict.fromkeys(p["kind"] for p in powers) if k in NEW_POWERS]
if shown_new:
    line = ("🆕 New power: " if EN else "🆕 قدرت جدید: ") + "، ".join(POWER_NAME[k] for k in shown_new).replace("، ", ", " if EN else "، ")
    head, sep, tags = caption.rpartition("\n\n")
    caption = f"{head}\n\n{line}{sep}{tags}" if sep else f"{caption}\n\n{line}"
if FORMAT == "worldcup":
    yt_title, yt_tags = captions.youtube_worldcup(rng, names, wc.ROUND_NAMES[WC_R])
else:
    yt_title, yt_tags = captions.youtube(FORMAT, names, cup.ROUND_NAMES[CUP_R] if FORMAT == "cup" else None)
meta = {"seed": SEED, "format": FORMAT, "teams": names, "winner": TEAMS[WIN][0], "lead_pct_at_whistle": WIN_PCT,
        "powers": [[p["kind"], TEAMS[p["team"]][0]] for p in powers], "new_powers": sorted(NEW_POWERS), "duration": round(DUR, 2),
        "instagram_caption": caption, "first_comment": first,
        "youtube_title": yt_title, "youtube_tags": yt_tags,
        "cover_ms": int((INTRO + POWER_TIMES[1] + 0.4) * 1000)}
with open(os.path.splitext(OUT)[0] + ".json", "w", encoding="utf-8") as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=2)
print("done", OUT)

"""City Cup ("جام شهرها") tournament state for barkhord.tv.

The state lives in cup.json next to this file (override with CUP_STATE=path).
A season is a 16-city knockout: round of 16 -> quarters -> semis -> final.
Each reel plays the next unplayed match. When a season ends, the next call
to next_match() starts a new season with a fresh draw.

Run `python3 cup.py bracket OUT.png` to draw the current bracket as a story image.
"""
import json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.environ.get("CUP_STATE", os.path.join(HERE, "cup.json"))

# provincial capitals; a season draws 16 of them
ALL_CITIES = ["تهران", "مشهد", "اصفهان", "کرج", "شیراز", "تبریز", "قم", "اهواز", "کرمانشاه",
              "ارومیه", "رشت", "زاهدان", "همدان", "کرمان", "یزد", "اردبیل", "بندرعباس", "اراک",
              "زنجان", "قزوین", "سنندج", "خرم‌آباد", "گرگان", "ساری", "بجنورد", "بوشهر",
              "بیرجند", "ایلام", "شهرکرد", "یاسوج", "سمنان"]
ROUND_NAMES = ["یک‌هشتم نهایی", "یک‌چهارم نهایی", "نیمه‌نهایی", "فینال"]
# contrasting color pairs for the two sides of a match
COLOR_PAIRS = [("#E63946", "#2A9DF4"), ("#FF7A1A", "#7C4DFF"), ("#F4B400", "#1F63C6"),
               ("#2DC653", "#FF4FA3"), ("#14B8A6", "#FF7A1A"), ("#A855F7", "#F4B400"),
               ("#FF4FA3", "#14B8A6"), ("#E63946", "#2DC653")]
FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(n):
    return str(n).translate(FA_DIGITS)


def new_season(number, seed, must_include=()):
    rng = random.Random(seed)
    pool = [c for c in ALL_CITIES if c not in must_include]
    cities = list(must_include)[:16] + rng.sample(pool, 16 - min(16, len(must_include)))
    rng.shuffle(cities)
    first = [[cities[2 * i], cities[2 * i + 1], None] for i in range(8)]
    return {"season": number, "rounds": [first, [], [], []], "champion": None,
            "requested_cities": []}


def load():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return None


def save(state):
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)


def _fill_next_rounds(state):
    rounds = state["rounds"]
    for r in range(3):
        cur, nxt = rounds[r], rounds[r + 1]
        expected = len(cur) // 2
        for i in range(len(nxt), expected):
            a, b = cur[2 * i][2], cur[2 * i + 1][2]
            if a and b:
                nxt.append([a, b, None])
            else:
                break


def pending(state):
    """(round_index, match_index) of the next unplayed match, or None."""
    _fill_next_rounds(state)
    for r, matches in enumerate(state["rounds"]):
        for m, (a, b, w) in enumerate(matches):
            if w is None:
                return r, m
    return None


def next_match(seed):
    """Load (or start) the season and return (state, r, m, city_a, city_b)."""
    state = load()
    if state is None or state.get("champion"):
        number = 1 if state is None else state["season"] + 1
        requested = [] if state is None else state.get("requested_cities", [])
        state = new_season(number, seed, requested)
    r, m = pending(state)
    a, b, _ = state["rounds"][r][m]
    return state, r, m, a, b


def record(state, r, m, winner):
    """Store the result and return a dict describing what comes next."""
    state["rounds"][r][m][2] = winner
    if r == 3:
        state["champion"] = winner
        return {"advanced_to": None, "champion": True, "next": None}
    nxt = pending(state)
    nxt_pair = None
    if nxt:
        nr, nm = nxt
        nxt_pair = state["rounds"][nr][nm][:2]
    return {"advanced_to": ROUND_NAMES[r + 1], "champion": False, "next": nxt_pair}


def colors_for(r, m, season):
    a, b = COLOR_PAIRS[(r * 3 + m + season) % len(COLOR_PAIRS)]
    return a, b


def match_label(r, m):
    total = [8, 4, 2, 1][r]
    if r == 3:
        return "فینال"
    return f"{ROUND_NAMES[r]} · بازی {fa(m + 1)} از {fa(total)}"


# ---------------- bracket image (story / highlight) ----------------
def draw_bracket(state, out_path):
    import glob
    from PIL import Image, ImageDraw, ImageFont
    font_dir = os.path.expanduser("~/.cache/vazirmatn")
    black = glob.glob(f"{font_dir}/**/UI-Farsi-Digits/fonts/ttf/Vazirmatn-UI-FD-Black.ttf", recursive=True)[0]
    semi = black.replace("Black", "SemiBold")
    RQ = ImageFont.Layout.RAQM
    W, H = 1080, 1920
    img = Image.new("RGB", (W, H), (14, 12, 30))
    d = ImageDraw.Draw(img)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(14 + 22 * k), int(12 + 6 * k), int(30 + 34 * k)))

    def t(xy, s, size, fill, bold=True, anchor="mm"):
        f = ImageFont.truetype(black if bold else semi, size, layout_engine=RQ)
        d.text(xy, s, font=f, fill=fill, anchor=anchor, direction="rtl", language="fa")

    _fill_next_rounds(state)
    t((W / 2, 130), "جام شهرها", 88, (255, 210, 63))
    t((W / 2, 215), f"فصل {fa(state['season'])}", 44, (255, 255, 255), bold=False)
    y = 300
    gold, dim, white = (255, 210, 63), (130, 130, 160), (255, 255, 255)
    sizes = [8, 4, 2, 1]
    for r in range(4):
        matches = state["rounds"][r]
        t((W / 2, y), ROUND_NAMES[r], 40, (180, 200, 255))
        y += 58
        row_h = 62 if r == 0 else 68
        for m in range(sizes[r]):
            if m < len(matches):
                a, b, w = matches[m]
            else:
                a, b, w = "؟", "؟", None
            d.rounded_rectangle([90, y - row_h / 2 + 6, 990, y + row_h / 2 - 6], 18, fill=(255, 255, 255, 18) if False else (34, 30, 64))
            ca = gold if w == a else (dim if w else white)
            cb = gold if w == b else (dim if w else white)
            t((735, y), a, 38, ca)
            t((540, y), "–", 34, dim)
            t((345, y), b, 38, cb)
            y += row_h
        y += 26
    champ = state.get("champion")
    t((W / 2, H - 150), f"قهرمان: {champ}" if champ else "شب‌ها ساعت ۲۲ یه بازی جدید", 50,
      gold if champ else white, bold=bool(champ))
    d.text((W / 2, H - 70), "@barkhord.tv", font=ImageFont.truetype(semi, 34), fill=(200, 200, 220), anchor="mm")
    img.save(out_path)


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "bracket":
        st = load()
        if st is None:
            st, *_ = next_match(1)
        draw_bracket(st, sys.argv[2])
        print(sys.argv[2])


def round_to_recap(state):
    """Index of a finished round that has no recap reel yet, or None."""
    if state is None:
        return None
    _fill_next_rounds(state)
    sizes = [8, 4, 2, 1]
    done = state.setdefault("recaps_done", [])
    for r, matches in enumerate(state["rounds"]):
        if len(matches) == sizes[r] and all(w for _, _, w in matches) and r not in done:
            return r
    return None

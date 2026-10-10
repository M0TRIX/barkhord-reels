"""World Cup of Countries: a 32-country knockout for the YouTube channel (English).

State lives in wcup.json next to this file (override with WCUP_STATE=path).
Round of 32 -> Round of 16 -> Quarter-finals -> Semi-finals -> Final; each
Short plays the next match. A new season starts automatically after a final.
Flags are pre-rendered PNGs in flags/<code>.png.
"""
import json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.environ.get("WCUP_STATE", os.path.join(HERE, "wcup.json"))
FLAGS = os.path.join(HERE, "flags")

COUNTRIES = {
    "br": "Brazil", "ar": "Argentina", "fr": "France", "de": "Germany", "es": "Spain",
    "gb-eng": "England", "pt": "Portugal", "it": "Italy", "nl": "Netherlands", "be": "Belgium",
    "hr": "Croatia", "mx": "Mexico", "us": "USA", "ca": "Canada", "jp": "Japan",
    "kr": "South Korea", "in": "India", "id": "Indonesia", "tr": "Turkey", "eg": "Egypt",
    "ma": "Morocco", "ng": "Nigeria", "sa": "Saudi Arabia", "au": "Australia", "pl": "Poland",
    "co": "Colombia", "ph": "Philippines", "vn": "Vietnam", "pk": "Pakistan", "bd": "Bangladesh",
    "ir": "Iran", "gr": "Greece",
}
# pairs kept apart in the opening round so the first matches don't turn into politics
AVOID_FIRST_ROUND = [{"ir", "us"}, {"in", "pk"}, {"ir", "sa"}]
ROUND_NAMES = ["Round of 32", "Round of 16", "Quarter-finals", "Semi-finals", "Final"]
SIZES = [16, 8, 4, 2, 1]
COLOR_PAIRS = [("#E63946", "#2A9DF4"), ("#FF7A1A", "#7C4DFF"), ("#F4B400", "#1F63C6"),
               ("#2DC653", "#FF4FA3"), ("#14B8A6", "#FF7A1A"), ("#A855F7", "#F4B400"),
               ("#FF4FA3", "#14B8A6"), ("#E63946", "#2DC653")]


def flag_path(code):
    return os.path.join(FLAGS, f"{code}.png")


def name(code):
    return COUNTRIES[code]


def new_season(number, seed):
    rng = random.Random(seed)
    codes = list(COUNTRIES)
    while True:
        rng.shuffle(codes)
        pairs = [{codes[2 * i], codes[2 * i + 1]} for i in range(16)]
        if not any(p in AVOID_FIRST_ROUND for p in pairs):
            break
    first = [[codes[2 * i], codes[2 * i + 1], None] for i in range(16)]
    return {"season": number, "rounds": [first, [], [], [], []], "champion": None}


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
    for r in range(4):
        cur, nxt = rounds[r], rounds[r + 1]
        for i in range(len(nxt), len(cur) // 2):
            a, b = cur[2 * i][2], cur[2 * i + 1][2]
            if a and b:
                nxt.append([a, b, None])
            else:
                break


def pending(state):
    _fill_next_rounds(state)
    for r, matches in enumerate(state["rounds"]):
        for m, (a, b, w) in enumerate(matches):
            if w is None:
                return r, m
    return None


def next_match(seed):
    """Load (or start) the season; returns (state, r, m, code_a, code_b)."""
    state = load()
    if state is None or state.get("champion"):
        state = new_season(1 if state is None else state["season"] + 1, seed)
    r, m = pending(state)
    a, b, _ = state["rounds"][r][m]
    return state, r, m, a, b


def record(state, r, m, winner_code):
    state["rounds"][r][m][2] = winner_code
    if r == 4:
        state["champion"] = winner_code
        return {"advanced_to": None, "champion": True, "next": None}
    nr, nm = pending(state)
    return {"advanced_to": ROUND_NAMES[r + 1], "champion": False, "next": state["rounds"][nr][nm][:2]}


def colors_for(r, m, season):
    return COLOR_PAIRS[(r * 5 + m + season) % len(COLOR_PAIRS)]


def match_label(r, m):
    if r == 4:
        return "Final"
    return f"{ROUND_NAMES[r]} · Match {m + 1}/{SIZES[r]}"

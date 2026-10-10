"""The list of special powers: what is in rotation now and what is waiting its turn.

Powers are introduced gradually, not all at once. Only ACTIVE powers appear in
videos, and each video uses just a few of them (see pick() below). A power that
joined in the last NEW_DAYS days is in every video and its banner says it is new,
so the new power itself becomes the hook.

To bring in a power from IDEAS: build it in battle.py (trigger_power, drawing,
sound), move it to ACTIVE with today's date, and add a line to the owner's guide.
"""
import datetime

# kind -> date it joined the videos
ACTIVE = {                         # the first four have been there from the start
    "giant": "2026-10-01",
    "rpg": "2026-10-01",
    "lightning": "2026-10-01",     # upgraded to a full thunderstorm on 2026-10-10
    "clone": "2026-10-01",
    "hammer": "2026-10-10",
}
DEFENCE = {
    "shield": "2026-10-10",        # blocks one RPG or hammer
}
NEW_DAYS = 3
STRONG = {"rpg", "lightning", "giant", "hammer"}     # big enough for the final frenzy

# not built yet; in rough order of what to bring in next (Persian name, kind, idea)
IDEAS = [
    ("یخ‌زدگی", "freeze", "attack", "the other side's balls freeze for 2 s while ice spreads over their cells"),
    ("دیوار", "wall", "defence", "a wall rises along the border; enemy balls bounce off it for 3 s"),
    ("گردباد", "tornado", "attack", "a tornado zigzags through enemy land, taking every cell on its path"),
    ("آهنربا", "magnet", "attack", "pulls the enemy balls into a corner for 2 s"),
    ("بارون شهاب‌سنگ", "meteor", "attack", "meteors fall on enemy land, small craters everywhere"),
    ("سیاه‌چاله", "blackhole", "attack", "a black hole swallows a round piece of enemy land"),
    ("لیزر", "laser", "attack", "a laser sweeps one row or column of the board"),
    ("زلزله", "quake", "attack", "the board shakes and random enemy cells flip"),
    ("ترمیم", "heal", "defence", "takes back the cells lost in the last 2 s"),
]


def _date(s):
    return datetime.date.fromisoformat(s)


def today_tehran():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3, minutes=30)).date()


def is_new(kind, today=None):
    since = ACTIVE.get(kind) or DEFENCE.get(kind)
    return since is not None and (today or today_tehran()) - _date(since) < datetime.timedelta(days=NEW_DAYS)


def pick(rng, today=None):
    """Kinds for the 5 power moments of one video, and whether a shield appears.

    Each video uses only 2 (sometimes 3) different powers; a new power is always one of them.
    Moments 4 and 5 fall in the final frenzy, so they use strong powers.
    """
    today = today or today_tehran()
    pool = [k for k, d in ACTIVE.items() if _date(d) <= today]
    new = sorted((k for k in pool if is_new(k, today)), key=lambda k: ACTIVE[k], reverse=True)
    n = 3 if rng.random() < 0.3 else 2
    kinds = new[:n]
    rest = [k for k in pool if k not in kinds]
    kinds += rng.sample(rest, n - len(kinds))
    if not any(k in STRONG for k in kinds):
        kinds[-1] = rng.choice(sorted(STRONG & set(pool)))
    strong = [k for k in kinds if k in STRONG]
    seq = list(kinds) + [rng.choice(kinds) for _ in range(3 - len(kinds))]
    rng.shuffle(seq)
    seq += [rng.choice(strong), rng.choice(strong)]
    for i in range(1, 5):            # avoid the same power twice in a row when there is a choice
        if seq[i] == seq[i - 1]:
            alts = [k for k in (kinds if i < 3 else strong) if k != seq[i - 1]]
            if alts:
                seq[i] = rng.choice(alts)
    shield = any(_date(d) <= today for d in DEFENCE.values()) and (
        is_new("shield", today) or rng.random() < 0.5)
    return seq, shield

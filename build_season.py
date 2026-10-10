"""Play the rest of the City Cup ahead of time and render every video, with a publishing date for each.

Usage: [SERIES=worldcup] [START=YYYY-MM-DD] python3 build_season.py plan     -> decides every match (picks the most dramatic of a few seeds),
                                           writes season/plan.json and the state snapshots
       python3 build_season.py render   -> renders every video in the plan that is not rendered yet (2 at a time)
       python3 build_season.py texts    -> prints the upload list (date, title, description, tags, comment)

Videos go out on Instagram days (Sat, Sun, Mon, Wed, Thu) at 22:00 Tehran, one per day, starting tomorrow.
Each round ends with its recap video; the last video is the final's recap with the champion.
Every video is rendered with TODAY = its own publishing date, so "new power" labels stay true.
"""
import datetime, json, os, re, shutil, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cup
import worldcup as wc

# SERIES=cup (default): City Cup, Persian, Instagram days at 22:00, folder season/
# SERIES=worldcup: World Cup of Countries, English, YouTube only, every day at 16:00, folder season_wc/
SERIES = os.environ.get("SERIES", "cup")
if SERIES == "worldcup":
    S, STATE_ENV, FMT, SEASON, DAILY, HOUR = wc, "WCUP_STATE", "worldcup", os.path.join(HERE, "season_wc"), True, "16:00"
else:
    S, STATE_ENV, FMT, SEASON, DAILY, HOUR = cup, "CUP_STATE", "cup", os.path.join(HERE, "season"), False, "22:00"
PLAN = os.path.join(SEASON, "plan.json")
FINAL_ROUND = len(S.ROUND_NAMES) - 1

IG_DAYS = {5, 6, 0, 2, 3}          # Sat, Sun, Mon, Wed, Thu (Python weekday numbers)
SEEDS_TRIED = 6
FA_MONTHS = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]


def fa_date(d):
    """Gregorian date -> Persian solar date string, for dates in 1405 (2026-03-21 .. 2027-03-20)."""
    n = (d - datetime.date(2026, 3, 21)).days
    for i, length in enumerate([31] * 6 + [30] * 5 + [29]):
        if n < length:
            return f"{cup.fa(n + 1)} {FA_MONTHS[i]}"
        n -= length
    return d.isoformat()


def ig_dates(start):
    d = start
    while True:
        if DAILY or d.weekday() in IG_DAYS:
            yield d
        d += datetime.timedelta(days=1)


def dry(state_path, seed, today, save=False):
    env = dict(os.environ, DRY="1", TODAY=today)
    env[STATE_ENV] = state_path
    if save:
        env["SAVE_DRY"] = "1"
    out = subprocess.run([sys.executable, os.path.join(HERE, "battle.py"), "/tmp/dry.mp4", str(seed), FMT],
                         env=env, capture_output=True, text=True, check=True).stdout
    m = re.search(r"winner=(.+?) lead=(\d+)% ko_t=([\d.]+) lead_changes=(\d+)", out)
    return m.group(1), float(m.group(3)), int(m.group(4))


def plan():
    os.makedirs(SEASON, exist_ok=True)
    state = S.load()
    snap = os.path.join(SEASON, "state_000.json")
    with open(snap, "w", encoding="utf-8") as fh:
        json.dump(state, fh, ensure_ascii=False, indent=2)
    start = os.environ.get("START")
    tomorrow = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3, minutes=30)).date() + datetime.timedelta(days=1)
    dates = ig_dates(datetime.date.fromisoformat(start) if start else tomorrow)
    items, n, base_seed = [], 0, 1792000000
    while True:
        st = json.load(open(snap, encoding="utf-8"))
        rd = S.round_to_recap(st)
        n += 1
        day = next(dates)
        if rd is not None:                     # a round just finished: its recap
            st.setdefault("recaps_done", []).append(rd)
            nxt = os.path.join(SEASON, f"state_{n:03d}.json")
            json.dump(st, open(nxt, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            items.append({"n": n, "date": day.isoformat(), "date_fa": fa_date(day), "time": HOUR, "kind": "recap", "round": rd,
                          "label": S.ROUND_NAMES[rd], "state": os.path.relpath(snap, HERE),
                          "video": f"{os.path.basename(SEASON)}/{n:02d}_recap_{rd}.mp4"})
            snap = nxt
            if rd == FINAL_ROUND:
                break
            continue
        r, m = S.pending(st)
        a, b, _ = st["rounds"][r][m]
        if SERIES == "worldcup":
            a, b = wc.name(a), wc.name(b)
        best = None
        for k in range(SEEDS_TRIED):           # the most lead changes, then a final round of about 5 s
            seed = base_seed + n * 100 + k
            w, ko_t, changes = dry(snap, seed, day.isoformat())
            score = (min(changes, 6), -abs(ko_t - 17.0))
            if best is None or score > best[0]:
                best = (score, seed, w, ko_t, changes)
        _, seed, w, lead, changes = best
        nxt = os.path.join(SEASON, f"state_{n:03d}.json")
        shutil.copy(snap, nxt)
        w2, _, _ = dry(nxt, seed, day.isoformat(), save=True)
        assert w2 == w, (w, w2)
        folder = os.path.basename(SEASON)
        it = {"n": n, "date": day.isoformat(), "date_fa": fa_date(day), "time": HOUR, "kind": "cup", "round": r, "match": m,
              "teams": [a, b], "winner": w, "ko_t": lead, "lead_changes": changes, "seed": seed,
              "label": S.match_label(r, m), "state": os.path.relpath(snap, HERE),
              "video": f"{folder}/{n:02d}_{r}_{m}.mp4"}
        if SERIES == "cup":
            it["bracket"] = f"{folder}/{n:02d}_bracket.png"
        items.append(it)
        print(n, day, a, "vs", b, "->", w, f"ko {lead}s changes={changes}", flush=True)
        snap = nxt
    json.dump({"series": SERIES, "season": json.load(open(snap, encoding="utf-8"))["season"], "items": items,
               "final_state": os.path.relpath(snap, HERE)}, open(PLAN, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("planned", len(items), "videos; champion:", json.load(open(snap, encoding="utf-8"))["champion"])


def render_one(it):
    out = os.path.join(HERE, it["video"])
    if os.path.exists(os.path.splitext(out)[0] + ".json"):
        return it["n"], "already"
    work = f"/tmp/season_state_{it['n']:03d}.json"
    shutil.copy(os.path.join(HERE, it["state"]), work)      # the renderer saves into its copy, not the snapshot
    env = dict(os.environ, TODAY=it["date"])
    env[STATE_ENV] = work
    if it["kind"] == "cup":
        res = subprocess.run([sys.executable, os.path.join(HERE, "battle.py"), out, str(it["seed"]), FMT],
                             env=env, capture_output=True, text=True)
        if res.returncode == 0:
            m = re.search(r"winner=(.+?) lead=", res.stdout)
            if not m or m.group(1) != it["winner"]:
                return it["n"], f"WINNER MISMATCH {m.group(1) if m else '?'} != {it['winner']}"
            if it.get("bracket"):
                subprocess.run([sys.executable, os.path.join(HERE, "cup.py"), "bracket", os.path.join(HERE, it["bracket"])],
                               env=env, check=True, capture_output=True)   # work now holds the state after this match
    else:
        res = subprocess.run([sys.executable, os.path.join(HERE, "recap.py"), out, FMT, str(it["round"])],
                             env=env, capture_output=True, text=True)
    return it["n"], "ok" if res.returncode == 0 else "FAILED " + res.stderr[-400:]


def render(only=None):
    items = json.load(open(PLAN, encoding="utf-8"))["items"]
    if only:
        items = [it for it in items if it["n"] in only]
    with ThreadPoolExecutor(2) as ex:
        for n, status in ex.map(render_one, items):
            print(n, status, flush=True)


def texts():
    items = json.load(open(PLAN, encoding="utf-8"))["items"]
    for it in items:
        meta = json.load(open(os.path.join(HERE, os.path.splitext(it["video"])[0] + ".json"), encoding="utf-8"))
        print(f"### {it['n']}. {it['date_fa']} ({it['date']}) 22:00 — {os.path.basename(it['video'])}")
        print(meta["youtube_title"]); print(meta["instagram_caption"]); print(", ".join(meta["youtube_tags"]))
        print(meta["first_comment"]); print()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "plan"
    if cmd == "plan":
        plan()
    elif cmd == "render":
        render([int(x) for x in sys.argv[2:]] or None)
    elif cmd == "texts":
        texts()

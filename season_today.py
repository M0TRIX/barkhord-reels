"""Which pre-rendered City Cup video goes out today (made by build_season.py).

Usage: python3 season_today.py          -> prints today's item as JSON (with the paths of its video, texts
                                           and bracket image), or "none" (nothing today), or "finished"
                                           (every video in the plan is past: the cup is over).
                                           "already_scheduled": true means it is already waiting in Metricool
                                           (items 3-17 were all scheduled ahead on 2026-10-14): do not post it again.
       python3 season_today.py done N   -> marks item N as scheduled on Instagram
"""
import datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLAN = os.path.join(HERE, "season", "plan.json")
today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3, minutes=30)).date().isoformat()
plan = json.load(open(PLAN, encoding="utf-8"))

if len(sys.argv) == 3 and sys.argv[1] == "done":
    for it in plan["items"]:
        if it["n"] == int(sys.argv[2]):
            it["instagram_scheduled"] = today
    json.dump(plan, open(PLAN, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("marked", sys.argv[2])
    sys.exit()

todays = [it for it in plan["items"] if it["date"] == today]
if todays:
    it = dict(todays[0])
    it["texts"] = os.path.splitext(it["video"])[0] + ".json"
    it["already_scheduled"] = bool(it.get("instagram_scheduled"))
    print(json.dumps(it, ensure_ascii=False))
elif all(it["date"] < today for it in plan["items"]):
    print("finished")
else:
    print("none")

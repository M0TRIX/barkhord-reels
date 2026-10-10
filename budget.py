"""Decide whether today's YouTube Short fits in the free Metricool plan.

Usage: python3 budget.py USED [YYYY-MM-DD]
USED = posts already scheduled or published this calendar month (all networks,
including today's Instagram reel). Instagram has priority: one slot is kept for
every Instagram posting day left this month (Sat, Sun, Mon, Wed, Thu after today).
Prints "auto" if the Short can be scheduled through Metricool, otherwise "manual".
"""
import calendar, datetime, sys

LIMIT = 20
IG_WEEKDAYS = {5, 6, 0, 2, 3}          # Python weekday numbers: Sat, Sun, Mon, Wed, Thu

used = int(sys.argv[1])
today = (datetime.date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2
         else (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3, minutes=30)).date())
last = calendar.monthrange(today.year, today.month)[1]
ig_left = sum(1 for d in range(today.day + 1, last + 1)
              if datetime.date(today.year, today.month, d).weekday() in IG_WEEKDAYS)
print("auto" if used + ig_left + 1 <= LIMIT else "manual")

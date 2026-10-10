# Barkhord: automated ball-battle reels

This repo makes and schedules short vertical videos for two pages:

| Page | Language | Series | Posted by |
|---|---|---|---|
| Instagram **@barkhord.tv** | Persian | **جام شهرها (City Cup)**: 16 Iranian cities, knockout, one match per reel; a Persepolis–Esteghlal derby every 4th reel | Metricool, automatically, 22:00 Tehran |
| YouTube **Barkhord** (channel id `UCBtuxvSrawmZCWyye_sibRA`) | English + Persian | Every day **World Cup of Countries** (32 countries with real flags, knockout); on Instagram days also the same Persian reel | The owner uploads by hand: the task sends the files with title, description and tags. Metricool's 20 free posts a month are kept for Instagram |

The day after a round finishes, that day's video is a **round recap** (all results revealed one by one, then the next match).

## Every video (battle.py)
1. **Intro (2.8 s)**: wrestling-style entrance; each team is a cartoon ball (its flag for countries) that slides in, raises its arms and shouts; "VS" slam. Persian cities listed in `dialects.py` get a speech bubble with a catchphrase in their own dialect, and the winner taunts in its dialect on the podium.
2. **Fight (15 s)**: territory war on a grid ("pong wars"): each team's balls capture enemy cells. Live share bar, timer. The team in last place gets **special powers** (from the roster in `powers.py`: giant ball, RPG, thunderstorm, clones, giant hammer; only 2–3 of them per video, new ones first) so the lead keeps changing. In about half the videos (every video while it is new) one RPG or hammer is met by the other side's **shield** (a dome that shatters and lets only a third of the blast through). Last 5 s = **frenzy**: faster balls, two extra powers, red pulsing frame, heartbeat.
3. **Finish**: whistle, the leader's shockwave wipes out the other side (100%), "K.O.!".
4. **Podium (4.6 s)**: winner with a crown laughing (mouth synced to a synthesized deep laugh), loser crying in the corner + sad trombone, next match + follow/subscribe line.

All sound is synthesized in `sfx.py` (no samples, no copyright issues). Fonts: Vazirmatn (downloaded via `npm pack vazirmatn` into `~/.cache/vazirmatn`).

## Files
| File | Purpose |
|---|---|
| `make_reel.py` | Today's Instagram reel → `reels/reel_<seed>.mp4` + `.json`. Picks cup / derby / recap. Prints the json path last. |
| `make_short.py` | Today's YouTube Short → `shorts/short_<seed>.mp4` + `.json` (World Cup match or recap). |
| `battle.py OUT SEED FORMAT` | Renders one battle. FORMAT: `cup`, `worldcup`, `derby`, `cities`, `colors`, `request` (a viewer's requested match: `MATCH="نهاوند,تبریز"`). `PREVIEW=1` saves preview PNGs; `DRY=1` only simulates. |
| `powers.py` | The power roster: which powers are active (with the date each joined), which are ideas waiting their turn. Each video uses only 2–3 different powers; a power added in the last 3 days is in every video, its banner says NEW and the caption gets a "new power" line. |
| `dialects.py` | Each city's dialect catchphrases (intro shout, winner taunt). Friendly local pride only; the owner checks new lines. |
| `recap.py OUT SERIES ROUND` | Round recap video (`cup` or `worldcup`). |
| `reel_generator.py` | Older single-ball "ring" format (not in rotation). |
| `cup.py`, `cup.json` | City Cup state (`CUP_STATE` env overrides the path for tests). `python3 cup.py bracket OUT.png` draws the table as a story image. |
| `worldcup.py`, `wcup.json`, `flags/` | World Cup state (`WCUP_STATE` env for tests) and 32 pre-rendered flag PNGs (640×480). |
| `captions.py` | All captions, first comments, YouTube titles/tags. Persian text is deliberately short and colloquial. |
| `mascot.py` | Cartoon ball characters (angry/laugh/sad, arms, crown). |
| `sfx.py` | Sound effects: laugh, shout, crowd, bell, whistle, boom, RPG whoosh, thunder, shatter, sad trombone, drum loop. |
| `ledger.py`, `posts_log.json` | Log of posts made through Metricool (free plan = **20 posts/month for the whole brand**). |
| `budget.py USED` | (Not used since 2026-10-10: all YouTube Shorts are uploaded by hand.) Prints `auto` if a YouTube post fits this month after reserving one slot for every remaining Instagram day, else `manual`. |

Rendering needs python3 with numpy, scipy, pillow (with raqm), plus ffmpeg and npm. One video takes about 6–7 minutes on 2 CPUs; run renders in the background.

## Hosting the video for Metricool
Metricool needs a public video URL. Videos are committed to this public repo and served through jsDelivr:
`https://cdn.jsdelivr.net/gh/M0TRIX/barkhord-reels@<commit-sha>/reels/reel_<seed>.mp4`
(raw.githubusercontent serves the wrong content type; GitHub Pages is not enabled.) Metricool copies the file to its own storage when the post is created, so old mp4s can be deleted after 7 days.

## Metricool
- Brand / blogId: **7295807**, timezone Asia/Tehran, networks: Instagram `barkhord.tv`, YouTube `UCBtuxvSrawmZCWyye_sibRA`.
- Free plan: 20 posts per calendar month (all networks together). `getScheduledPosts` only lists posts that are not yet published, so the count comes from `posts_log.json`.

## The daily scheduled task
Runs every day at 20:58 Tehran (`CRON_TZ=Asia/Tehran 58 20 * * *`), needs the Metricool connector and push access to this repo. Its prompt:

```
You run two pages: the Instagram page barkhord.tv (Persian "City Cup" reels, posted automatically through Metricool) and the YouTube channel Barkhord (Shorts that the owner uploads by hand; Metricool's 20 free posts a month are kept for Instagram). Metricool brand blogId/brandId 7295807, timezone Asia/Tehran. Talk to the user in Persian.

Today is an "Instagram day" if it is Saturday, Sunday, Monday, Wednesday or Thursday in Tehran time; Tuesday and Friday are YouTube-only days.

1. Repo: you need push access to GitHub repo M0TRIX/barkhord-reels. If it is not already in this session, call add_repo (owner "M0TRIX", repo "barkhord-reels", access "push"), then `git clone --depth 1 https://github.com/M0TRIX/barkhord-reels /home/claude/barkhord-reels` (generous timeout). Set git user.name "barkhord-bot" and user.email "barkhord-bot@users.noreply.github.com". Install anything missing: `pip install --break-system-packages numpy scipy pillow` (ffmpeg and npm are needed too; the scripts download their font with npm).

Rendering a video takes about 6 minutes, so always start renders in the background (e.g. `nohup python3 make_reel.py > /tmp/reel.log 2>&1 &`) and check the log every minute or so, for up to 20 minutes, until its last line is a .json path or it shows an error. Start the renders at the same time to save time.

2. Render:
   - Every day, YouTube: `python3 make_short.py` → shorts/short_<SEED>.mp4 + shorts/short_<SEED>.json (youtube_title, youtube_tags, instagram_caption which is the English YouTube description, first_comment). It plays the next World Cup of Countries match (wcup.json) or a round recap.
   - Instagram days only: `python3 make_reel.py` → reels/reel_<SEED>.mp4 + reels/reel_<SEED>.json (format, instagram_caption, first_comment, cover_ms, youtube_title, youtube_tags). It plays the next City Cup match (cup.json), a derby every fourth reel, or a round recap.
   Check each mp4 exists and is over 1 MB. Then delete reels/*.mp4 and shorts/*.mp4 older than 7 days (keep all .json files, cup.json, wcup.json, posts_log.json), and `git add -A && git commit -m "Daily videos <date>" && git push origin HEAD:main`. Get the commit sha with `git rev-parse --short HEAD`.

3. Instagram (Instagram days only): `python3 ledger.py count` prints how many Metricool posts were made this calendar month.
   - Below 20: call Metricool createScheduledPost with blogId "7295807", date today 22:00:00+03:30, and info JSON: autoPublish true, draft false, descendants [], hasNotReadNotes false, mediaAltText [], shortener false, smartLinkData {ids: []}, providers [{network: "instagram"}], publicationDate {dateTime: "<today>T22:00:00", timezone: "Asia/Tehran"}, media ["https://cdn.jsdelivr.net/gh/M0TRIX/barkhord-reels@<sha>/reels/reel_<SEED>.mp4"], text = the reel JSON's instagram_caption exactly, firstCommentText = its first_comment exactly, videoCoverMilliseconds = its cover_ms, instagramData {type: "REEL", showReelOnFeed: true}. If rejected only because of videoCoverMilliseconds, retry once without it. If 22:00 has passed, use 15 minutes from now. Confirm the media was copied to static.metricool.com and status is PENDING. Then `python3 ledger.py add instagram "<format>"`.
   - 20 or more: do not schedule it. Send the reel mp4 to the user with SendUserFile and, in the YouTube message of step 4, add the Instagram caption and first comment (each in its own code block) with one Persian line saying this month's free Metricool posts are used up, so they post the reel by hand.

4. YouTube (every day): the owner uploads by hand. Send the files with SendUserFile and one SendUserMessage in Persian:
   - Short 1, the World Cup of Countries (shorts/short_<SEED>.mp4): title = youtube_title, description = instagram_caption, tags = youtube_tags joined with ", ", and first_comment as the comment to pin.
   - On Instagram days, Short 2, the same Persian reel (reels/reel_<SEED>.mp4): title = its youtube_title, description = its instagram_caption, tags = its youtube_tags joined with ", ", and its first_comment to pin.
   Put every title, description, tags list and comment in its own code block so each can be copied with one tap. Add one line on timing: the Persian Short goes up right away (Iranian evening, about 21:30–22:30 Tehran); the World Cup Short is scheduled in YouTube Studio for tomorrow 16:00 Tehran (midday in Europe, evening in South and Southeast Asia, and the hour Metricool's data shows as YouTube's best every day).
   Finally commit and push posts_log.json (`git add -A && git commit -m "Log posts" && git push origin HEAD:main`).

5. If today's Instagram format was "cup": run `python3 cup.py bracket /tmp/bracket.png` and send that image to the user with one Persian line saying it is the updated City Cup table, for a story and the "جام" highlight if they like.

6. If any step fails and you cannot fix it: send the affected mp4 to the user with its caption/title so they can post it by hand, and say in one Persian line what failed. If everything worked, finish with one short Persian line naming today's matches and how each goes out.
```

## Moving to another Claude account
1. In the new account, connect the **Metricool** connector (log in to the same Metricool account) and the **GitHub** connector; install the Claude GitHub app on `M0TRIX/barkhord-reels` (Only select repositories).
2. In a new chat: "Read README.md in GitHub repo M0TRIX/barkhord-reels and take over this project", then ask it to create the daily scheduled task with the prompt above.
3. **Turn off the old account's scheduled task**, or every video will be posted twice.

## Next season (decided 2026-10-10, not built yet)
The current City Cup (16 cities) and World Cup (32 countries) are played to the end first. Then:
- **Cities (Instagram):** the 31 provincial capitals + 1 wildcard city chosen from viewers' comments = 32 teams, in the exact 2022 World Cup format: seeded draw with pots, 8 groups of 4, each team plays the other 3 one-on-one, top two go to the round of 16, then quarter-finals, semi-finals, third-place match, final (64 matches).
- **Countries (YouTube):** all countries. Continental qualifiers first: each video is 4 countries from one continent on one board, the winner qualifies (about 48 videos). Then 48 teams in the exact 2026 World Cup format: 12 groups of 4, top two + 8 best third-placed teams to the round of 32, through to the final (104 matches).
- **Tables:** win = 3 points; tiebreak = difference in board share (like goal difference). A group-table image after every match.
- **Winners are not random:** every team has a power card (attack, speed, defence) from real data (countries: football ranking, cities: population) that changes the simulation, and every win earns an item (a power from `powers.py`) the team keeps for later matches. The table lists each team's items and the end screen names the item that won the match.
- Copy the competition structure, not FIFA's name, logo, mascot or official slogan (trademarks); make our own.

## The owner's guide
The owner reads a Persian guide kept as a Claude Doc: https://claude.ai/code/artifact/7262a895-1f38-4edd-aaed-6330b7fd2bc0 (it lives in the original Claude account). **Update it after every change to the project**: the section it affects, plus a dated line in its last section, "تاریخچه‌ی تغییرات" (change log, Persian solar dates).

## Notes and history
- Persian text must be rendered with Pillow's raqm layout (`direction="rtl"`); Latin-only strings (VS, K.O.!) are drawn left to right automatically.
- Flags were rendered from the `flag-icons` npm package with headless Chromium at a fixed 640×480 size; an earlier render with viewport units produced shrunken flags.
- First post (single ball in a ring): ~1.5k views, 0 shares. City Cup match 1 (Ahvaz–Qom): ~11k views, 33 likes, 23 shares, so the series format works.
- Ideas not built yet: miniature war (historical or fictional armies, avoid real current conflicts), relaxing/ADHD-style satisfying sound clips, collab posts with city pages (Metricool supports `instagramData.collaborators`).

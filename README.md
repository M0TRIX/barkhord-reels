# Barkhord: automated ball-battle reels

This repo makes and schedules short vertical videos for two pages:

| Page | Language | Series | Posted by |
|---|---|---|---|
| Instagram **@barkhord.tv** | Persian | **جام شهرها (City Cup)**: 16 Iranian cities, knockout, one match per reel. The rest of season 1 (17 videos, 2026-10-11 to 2026-11-02) is pre-rendered in `season/` | Metricool, automatically, 22:00 Tehran, one video per Instagram day from season/plan.json |
| YouTube **Barkhord** (channel id `UCBtuxvSrawmZCWyye_sibRA`) | Persian, then English | Until 2026-11-02 the same City Cup videos (22:00) plus viewer-requested matches. Then the **World Cup of Countries** season 1, pre-rendered in `season_wc/` (one a day at 16:00 from 2026-11-03, new ending). The old Netherlands–Portugal video in `saved/` is superseded: match 1 was replayed with the new ending | The owner uploads and schedules by hand. Metricool's 20 free posts a month are kept for Instagram |

The day after a round finishes, that day's video is a **round recap** (all results revealed one by one, then the next match).

## Every video (battle.py)
1. **Intro (2.8 s)**: wrestling-style entrance; each team is a cartoon ball (its flag for countries) that slides in, raises its arms and shouts; "VS" slam. Persian cities listed in `dialects.py` get a speech bubble with a catchphrase in their own dialect, and the winner taunts in its dialect on the podium.
2. **Fight**: territory war on a grid ("pong wars"): each team's balls capture enemy cells. Live share bar (each side's "life"), timer counting down to the final round. The team in last place gets **special powers** (from the roster in `powers.py`; only 2–3 kinds per video, new ones first) so the lead keeps changing; in about half the videos one RPG or hammer is met by the other side's **shield**.
3. **Final round (from 12 s, since 2026-10-11)**: no fixed end. Every 0.4 s each side's number of balls follows its share of the board and the leader's balls grow and sweep cells, so the side in front snowballs; the trailing side still gets one last power for a comeback. The match ends only when one side's share is ~0 (K.O.), usually 3–8 s later (cap 12 s). Red pulsing frame, heartbeat, "تا آخرین نفس!" / "LAST ONE STANDING WINS!". (The 17 pre-rendered City Cup season 1 videos in `season/` still have the old ending, where the leader at 15 s wiped the board; the owner chose to keep them.)
4. **Finish**: whistle, the winner takes the last cells, "K.O.!".
5. **Podium (4.6 s)**: winner with a crown laughing (mouth synced to a synthesized deep laugh), loser crying in the corner + sad trombone, next match + follow/subscribe line.

All sound is synthesized in `sfx.py` (no samples, no copyright issues). Fonts: Vazirmatn (downloaded via `npm pack vazirmatn` into `~/.cache/vazirmatn`).

## Files
| File | Purpose |
|---|---|
| `make_reel.py` | Today's Instagram reel → `reels/reel_<seed>.mp4` + `.json`. Picks cup / derby / recap. Prints the json path last. |
| `make_short.py` | (On hold since 2026-10-10.) Today's World Cup YouTube Short → `shorts/short_<seed>.mp4` + `.json` (World Cup match or recap). |
| `battle.py OUT SEED FORMAT` | Renders one battle. FORMAT: `cup`, `worldcup`, `derby`, `cities`, `colors`, `request` (a viewer's requested match: `MATCH="نهاوند,تبریز"`). `PREVIEW=1` saves preview PNGs; `DRY=1` only simulates. |
| `powers.py` | The power roster: which powers are active (with the date each joined), which are ideas waiting their turn. Each video uses only 2–3 different powers; a power added in the last 3 days is in every video, its banner says NEW and the caption gets a "new power" line. |
| `build_season.py` | Plays the rest of a City Cup season ahead of time (`plan`: picks the most dramatic of 6 seeds per match, saves state snapshots and season/plan.json with a date per video), renders everything 2 at a time (`render`), and prints the upload list (`texts`). Each video is rendered with TODAY = its publishing date. |
| `season_wc/` | The whole World Cup of Countries season 1 (Round of 32 to the final, with a recap after each round and a champion video), made with `SERIES=worldcup START=2026-11-03 python3 build_season.py plan/render`, one video a day at 16:00 Tehran from 2026-11-03. YouTube only; the owner schedules them by hand. |
| `season_today.py`, `season/` | The pre-rendered season: today's item for the nightly task (`season_today.py`), `done N` marks it scheduled on Instagram. |
| `make_request.py`, `requests.json` | Queue of matches viewers asked for in comments. `python3 make_request.py add گرگان گیلان` queues one; `python3 make_request.py` renders the oldest (format `request`) and prints its json path, or `none`. The daily task makes one every day while the queue has any. |
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
You run two pages: the Instagram page barkhord.tv and the YouTube channel Barkhord (Persian for now). Metricool brand blogId/brandId 7295807, timezone Asia/Tehran. Talk to the user in Persian.

The rest of City Cup season 1 was played and rendered in advance (build_season.py): season/plan.json lists one video per Instagram day (Sat, Sun, Mon, Wed, Thu) with its date, ending with the final's recap on 2026-11-02. The owner has already scheduled all of them on YouTube himself. Each night your job is to put that day's video on Instagram and to make the next viewer-requested match for YouTube. Never play cup matches again: do not run make_reel.py, make_short.py or battle.py with the cup format, and do not change cup.json, wcup.json, saved/ or season/ (except through `season_today.py done`).

1. Repo: you need push access to GitHub repo M0TRIX/barkhord-reels. If it is not already in this session, call add_repo (owner "M0TRIX", repo "barkhord-reels", access "push"), then `git clone --depth 1 https://github.com/M0TRIX/barkhord-reels /home/claude/barkhord-reels` (generous timeout). Set git user.name "barkhord-bot" and user.email "barkhord-bot@users.noreply.github.com". Install anything missing: `pip install --break-system-packages numpy scipy pillow` (ffmpeg and npm are needed too; the scripts download their font with npm).

2. Start `nohup python3 make_request.py > /tmp/req.log 2>&1 &` (about 6 minutes; check the log every minute, for up to 20 minutes, until its last line is a .json path, `none`, or an error). It makes the oldest viewer-requested match from requests.json as reels/request_<SEED>.mp4 + .json (instagram_caption, first_comment, youtube_title, youtube_tags).

3. Meanwhile run `python3 season_today.py`. It prints today's item as JSON (n, date, kind "cup" or "recap", video, texts, bracket), `none` (nothing today), or `finished` (every video is past: the cup is over).

4. When make_request.py has finished: delete reels/*.mp4 and shorts/*.mp4 older than 7 days (keep all .json files and everything in saved/ and season/), then `git add -A && git commit -m "Daily <date>" && git push origin HEAD:main` and get the sha with `git rev-parse --short HEAD`.

5. Instagram, if there is an item today: `python3 ledger.py count` prints this month's Metricool posts.
   - Below 20: call Metricool createScheduledPost with blogId "7295807", date today 22:00:00+03:30, and info JSON: autoPublish true, draft false, descendants [], hasNotReadNotes false, mediaAltText [], shortener false, smartLinkData {ids: []}, providers [{network: "instagram"}], publicationDate {dateTime: "<today>T22:00:00", timezone: "Asia/Tehran"}, media ["https://cdn.jsdelivr.net/gh/M0TRIX/barkhord-reels@<sha>/<the item's video path>"], text = instagram_caption from the item's texts file exactly, firstCommentText = its first_comment exactly, videoCoverMilliseconds = its cover_ms, instagramData {type: "REEL", showReelOnFeed: true}. If rejected only because of videoCoverMilliseconds, retry once without it. If 22:00 has passed, use 15 minutes from now. Confirm the media was copied to static.metricool.com and status is PENDING. Then `python3 ledger.py add instagram "<kind>"` and `python3 season_today.py done <n>`.
   - 20 or more: do not schedule it. Send the video to the user with SendUserFile, its caption and first comment each in its own code block, and one Persian line saying this month's free Metricool posts are used up, so they post it on Instagram by hand at 22:00.
   - If the item's kind is "cup", also send its bracket image with one Persian line saying it is the updated City Cup table, for a story and the "جام" highlight if they like.
   If season_today.py printed `finished`, tell the user in one Persian line that the City Cup is over and the next season (the 32-team league) and the return of the World Cup of Countries need to be set up in a chat with Claude.

6. YouTube, if make_request.py made a video: send it with SendUserFile and one SendUserMessage in Persian with its title (youtube_title), description (instagram_caption), tags (youtube_tags joined with ", ") and comment to pin (first_comment), each in its own code block. Say to schedule it in YouTube Studio for tomorrow 13:00 Tehran, to pin the comment once it is live, and to reply "ساختیمش" under the comment that asked for it.
   If there is neither an Instagram item nor a request video today, send one Persian line saying there is nothing new today.

7. Commit and push posts_log.json and season/plan.json (`git add -A && git commit -m "Log posts" && git push origin HEAD:main`). If any step fails and you cannot fix it, send the affected video to the user with its texts so they can post it by hand, and say in one Persian line what failed. Otherwise finish with one short Persian line saying what went out today.
```

## Moving to another Claude account
1. In the new account, connect the **Metricool** connector (log in to the same Metricool account) and the **GitHub** connector; install the Claude GitHub app on `M0TRIX/barkhord-reels` (Only select repositories).
2. In a new chat: "Read README.md in GitHub repo M0TRIX/barkhord-reels and take over this project", then ask it to create the daily scheduled task with the prompt above.
3. **Turn off the old account's scheduled task**, or every video will be posted twice.

## Next season (decided 2026-10-10, not built yet)
The current City Cup (16 cities) is played to the end first (make_reel.py never starts a new cup season by itself; after the final it makes derbies and flags `cup_finished`). The World Cup of Countries waits until then; its first match video is in `saved/`. Then:
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
- Next big idea (owner, 2026-10-11): after the World Cup, design characters together and build mini armies that fight instead of balls, with the powers given to the characters. Ideas not built yet: miniature war (historical or fictional armies, avoid real current conflicts), relaxing/ADHD-style satisfying sound clips, collab posts with city pages (Metricool supports `instagramData.collaborators`).

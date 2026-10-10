# Barkhord: automated ball-battle reels

This repo makes and schedules short vertical videos for two pages:

| Page | Language | Series | Posted by |
|---|---|---|---|
| Instagram **@barkhord.tv** | Persian | **جام شهرها (City Cup)**: 16 Iranian cities, knockout, one match per reel; a Persepolis–Esteghlal derby every 4th reel | Metricool, automatically, 22:00 Tehran |
| YouTube **Barkhord** (channel id `UCBtuxvSrawmZCWyye_sibRA`) | English | **World Cup of Countries**: 32 countries with real flags, knockout | Metricool when the free monthly quota allows, otherwise the video is sent to the owner to upload by hand |

The day after a round finishes, that day's video is a **round recap** (all results revealed one by one, then the next match).

## Every video (battle.py)
1. **Intro (2.8 s)**: wrestling-style entrance; each team is a cartoon ball (its flag for countries) that slides in, raises its arms and shouts; "VS" slam. Persian cities listed in `dialects.py` get a speech bubble with a catchphrase in their own dialect, and the winner taunts in its dialect on the podium.
2. **Fight (15 s)**: territory war on a grid ("pong wars"): each team's balls capture enemy cells. Live share bar, timer. The team in last place gets **special powers** (giant ball, RPG, lightning, clones, **giant hammer**, which is in every video) so the lead keeps changing. In every video one mid-match RPG or hammer is met by the other side's **shield** (a dome that shatters and lets only a third of the blast through). Last 5 s = **frenzy**: faster balls, two extra powers, red pulsing frame, heartbeat.
3. **Finish**: whistle, the leader's shockwave wipes out the other side (100%), "K.O.!".
4. **Podium (4.6 s)**: winner with a crown laughing (mouth synced to a synthesized deep laugh), loser crying in the corner + sad trombone, next match + follow/subscribe line.

All sound is synthesized in `sfx.py` (no samples, no copyright issues). Fonts: Vazirmatn (downloaded via `npm pack vazirmatn` into `~/.cache/vazirmatn`).

## Files
| File | Purpose |
|---|---|
| `make_reel.py` | Today's Instagram reel → `reels/reel_<seed>.mp4` + `.json`. Picks cup / derby / recap. Prints the json path last. |
| `make_short.py` | Today's YouTube Short → `shorts/short_<seed>.mp4` + `.json` (World Cup match or recap). |
| `battle.py OUT SEED FORMAT` | Renders one battle. FORMAT: `cup`, `worldcup`, `derby`, `cities`, `colors`, `request` (a viewer's requested match: `MATCH="نهاوند,تبریز"`). `PREVIEW=1` saves preview PNGs; `DRY=1` only simulates. |
| `dialects.py` | Each city's dialect catchphrases (intro shout, winner taunt). Friendly local pride only; the owner checks new lines. |
| `recap.py OUT SERIES ROUND` | Round recap video (`cup` or `worldcup`). |
| `reel_generator.py` | Older single-ball "ring" format (not in rotation). |
| `cup.py`, `cup.json` | City Cup state (`CUP_STATE` env overrides the path for tests). `python3 cup.py bracket OUT.png` draws the table as a story image. |
| `worldcup.py`, `wcup.json`, `flags/` | World Cup state (`WCUP_STATE` env for tests) and 32 pre-rendered flag PNGs (640×480). |
| `captions.py` | All captions, first comments, YouTube titles/tags. Persian text is deliberately short and colloquial. |
| `mascot.py` | Cartoon ball characters (angry/laugh/sad, arms, crown). |
| `sfx.py` | Sound effects: laugh, shout, crowd, bell, whistle, boom, RPG whoosh, thunder, shatter, sad trombone, drum loop. |
| `ledger.py`, `posts_log.json` | Log of posts made through Metricool (free plan = **20 posts/month for the whole brand**). |
| `budget.py USED` | Prints `auto` if a YouTube post fits this month after reserving one slot for every remaining Instagram day (Sat, Sun, Mon, Wed, Thu), else `manual`. |

Rendering needs python3 with numpy, scipy, pillow (with raqm), plus ffmpeg and npm. One video takes about 6–7 minutes on 2 CPUs; run renders in the background.

## Hosting the video for Metricool
Metricool needs a public video URL. Videos are committed to this public repo and served through jsDelivr:
`https://cdn.jsdelivr.net/gh/M0TRIX/barkhord-reels@<commit-sha>/reels/reel_<seed>.mp4`
(raw.githubusercontent serves the wrong content type; GitHub Pages is not enabled.) Metricool copies the file to its own storage when the post is created, so old mp4s can be deleted after 7 days.

## Metricool
- Brand / blogId: **7295807**, timezone Asia/Tehran, networks: Instagram `barkhord.tv`, YouTube `UCBtuxvSrawmZCWyye_sibRA`.
- Free plan: 20 posts per calendar month (all networks together). `getScheduledPosts` only lists posts that are not yet published, so the count comes from `posts_log.json`.

## The daily scheduled task
Runs Sat, Sun, Mon, Wed, Thu at 20:58 Tehran (`CRON_TZ=Asia/Tehran 58 20 * * 0,1,3,4,6`), needs the Metricool connector and push access to this repo. Its prompt:

```
You run two pages automatically: the Instagram page barkhord.tv (Persian "City Cup" reels) and the YouTube channel Barkhord (English "World Cup of Countries" Shorts). Both are in Metricool brand blogId/brandId 7295807, timezone Asia/Tehran. Talk to the user in Persian if you message them.

1. Repo: you need push access to GitHub repo M0TRIX/barkhord-reels. If it is not already in this session, call add_repo (owner "M0TRIX", repo "barkhord-reels", access "push"), then `git clone --depth 1 https://github.com/M0TRIX/barkhord-reels /home/claude/barkhord-reels` (generous timeout). Set git user.name "barkhord-bot" and user.email "barkhord-bot@users.noreply.github.com". Install anything missing: `pip install --break-system-packages numpy scipy pillow` (ffmpeg and npm are needed too; the scripts download their font with npm).

Rendering a video takes about 6 minutes, so always start renders in the background (e.g. `nohup python3 make_reel.py > /tmp/reel.log 2>&1 &`) and check the log every minute or so, for up to 20 minutes, until its last line is a .json path or it shows an error. Start the Instagram render and the YouTube render at the same time to save time.

2. Monthly limit: the free Metricool plan allows 20 posts per calendar month for the whole brand. `python3 ledger.py count` prints how many posts were scheduled this month. If it is 20 or more, skip step 4 (do not schedule the Instagram reel) and tell the user in one Persian line.

3. Render both:
   - Instagram: `python3 make_reel.py` → reels/reel_<SEED>.mp4 + reels/reel_<SEED>.json (format, instagram_caption, first_comment, cover_ms). It plays the next City Cup match (cup.json), or a derby every fourth reel.
   - YouTube: `python3 make_short.py` → shorts/short_<SEED>.mp4 + shorts/short_<SEED>.json (youtube_title, youtube_tags, instagram_caption which is the English YouTube description, first_comment). It plays the next World Cup of Countries match (wcup.json).
   Check each mp4 exists and is over 1 MB. Then delete reels/*.mp4 and shorts/*.mp4 older than 7 days (keep all .json files, cup.json, wcup.json, posts_log.json), and `git add -A && git commit -m "Daily videos <date>" && git push origin HEAD:main`. Get the commit sha with `git rev-parse --short HEAD`.

4. Instagram: call Metricool createScheduledPost with blogId "7295807", date today 22:00:00+03:30, and info JSON: autoPublish true, draft false, descendants [], hasNotReadNotes false, mediaAltText [], shortener false, smartLinkData {ids: []}, providers [{network: "instagram"}], publicationDate {dateTime: "<today>T22:00:00", timezone: "Asia/Tehran"}, media ["https://cdn.jsdelivr.net/gh/M0TRIX/barkhord-reels@<sha>/reels/reel_<SEED>.mp4"], text = the reel JSON's instagram_caption exactly, firstCommentText = its first_comment exactly, videoCoverMilliseconds = its cover_ms, instagramData {type: "REEL", showReelOnFeed: true}. If rejected only because of videoCoverMilliseconds, retry once without it. If 22:00 has passed, use 15 minutes from now. Confirm the media was copied to static.metricool.com and status is PENDING. Then `python3 ledger.py add instagram "<format>"`.

5. YouTube: run `python3 budget.py $(python3 ledger.py count)`.
   - If it prints "auto": call createScheduledPost with blogId "7295807", date today 22:30:00+03:30, providers [{network: "youtube"}], media ["https://cdn.jsdelivr.net/gh/M0TRIX/barkhord-reels@<sha>/shorts/short_<SEED>.mp4"], text = the short JSON's instagram_caption (the English description), the same other info fields as in step 4 but without instagramData and firstCommentText "", and youtubeData {title: youtube_title, type: "short", privacy: "public", tags: youtube_tags, category: "ENTERTAINMENT", madeForKids: false, isAiGeneratedContent: false}. Confirm PENDING, then `python3 ledger.py add youtube "worldcup"`.
   - If it prints "manual": send the user the short mp4 with SendUserFile, then a SendUserMessage in Persian saying it is today's YouTube Short to upload by hand (the free plan's monthly posts are reserved for Instagram), followed by the title, the description and the tags exactly as in the JSON (title, description and tags in English, each in its own code block so they are easy to copy).
   Finally commit and push posts_log.json (`git add -A && git commit -m "Log posts" && git push origin HEAD:main`).

6. If today's Instagram format was "cup": run `python3 cup.py bracket /tmp/bracket.png` and send that image to the user with one Persian line saying it is the updated City Cup table, for a story and the "جام" highlight if they like.

7. If any step fails and you cannot fix it: send the affected mp4 to the user with its caption/title so they can post it by hand, and say in one Persian line what failed. If everything worked, finish with one short Persian line naming today's Instagram match and YouTube match and how each was posted.
```

## Moving to another Claude account
1. In the new account, connect the **Metricool** connector (log in to the same Metricool account) and the **GitHub** connector; install the Claude GitHub app on `M0TRIX/barkhord-reels` (Only select repositories).
2. In a new chat: "Read README.md in GitHub repo M0TRIX/barkhord-reels and take over this project", then ask it to create the daily scheduled task with the prompt above.
3. **Turn off the old account's scheduled task**, or every video will be posted twice.

## Notes and history
- Persian text must be rendered with Pillow's raqm layout (`direction="rtl"`); Latin-only strings (VS, K.O.!) are drawn left to right automatically.
- Flags were rendered from the `flag-icons` npm package with headless Chromium at a fixed 640×480 size; an earlier render with viewport units produced shrunken flags.
- First post (single ball in a ring): ~1.5k views, 0 shares. City Cup match 1 (Ahvaz–Qom): ~11k views, 33 likes, 23 shares, so the series format works.
- Ideas not built yet: miniature war (historical or fictional armies, avoid real current conflicts), relaxing/ADHD-style satisfying sound clips, collab posts with city pages (Metricool supports `instagramData.collaborators`).

# YT Automater — Project Context

## Goal
Fully automated YouTube Shorts pipeline that:
- Posts shorts to YouTube automatically
- Makes shorts go viral (maximum views)
- Earns money through YouTube monetization (ad revenue)

---

## Core Retention Philosophy

The #1 priority of every video is **instant hook + scroll-stop power**.

### Hook Strategy
- **Punchline first, story second**: Open with the most shocking/embarrassing/curious moment.  
  The viewer hears the punchline and thinks "wait, how did this happen?" — they HAVE to keep watching.
- The headline (spoken first in voiceover) must create a "wait, what?" reaction in the first 2 seconds.
- Story structure: Hook → Setup → Escalation → Cliffhanger (NO resolution — forces rewatch).

### ADHD-Proof Design
- Background video is fast-paced gameplay (Minecraft parkour, satisfying clips, etc.) — keeps the eyes busy even if ears are the main channel.
- Captions flash 3 words at a time in sync with the voice — dual-channel engagement (visual + audio).
- No dead air, no slow moments. Every second must earn the next second.

---

## Hard Rules

### 1. Everything Must Be Free (No Paid Tools)
- **TTS**: edge-tts (Microsoft Azure Neural voices, free)
- **AI rewriting**: Google Gemini 2.5 Flash (free tier: 15 RPM, 1500 RPD)
- **Video assembly**: moviepy + ffmpeg (open source)
- **Fonts**: Only free/open-source fonts (Montserrat ExtraBold = SIL Open Font License)
- **Scraping**: Reddit public API / PRAW (free)
- **YouTube upload**: YouTube Data API v3 (free quota)
- ❌ No subscriptions, no API paid tiers, no licensed assets

### 2. Zero Copyright Risk
- **Background videos**: Must be copyright-free / CC0 / self-recorded gameplay.  
  Minecraft footage is generally safe for monetization if it's gameplay you record yourself or royalty-free sources.
- **Music**: No background music unless it is explicitly CC0 / royalty-free with commercial use allowed.
- **Reddit stories**: User-generated content — legally gray but industry-standard for this format.  
  Do NOT use stories from news articles, books, or copyrighted sources.
- **Fonts**: Only SIL Open Font License or equivalent.
- **Images/thumbnails**: Only AI-generated or CC0.
- ❌ Never use copyrighted music, clips, images, or brand assets.

---

## Content Format

| Element | Spec |
|---|---|
| Platform | YouTube Shorts (vertical 9:16, 1080×1920) |
| Duration | ≤ 60 seconds |
| Source | Reddit (r/pettyrevenge, r/AITA, r/tifu, r/prorevenge, r/confession, r/weddingshaming, r/bridezillas, r/JUSTNOMIL, etc.) |
| Script | AI-rewritten for virality, 100–115 words, cliffhanger ending, rotating comment bait |
| Voiceover | edge-tts Neural voices (5-voice rotating pool: Ryan, Aria, Guy, Davis, Jenny) |
| Captions | 1 word/chunk, center screen, yellow (#FFE000) + thin black stroke (6px) + warm yellow glow, Montserrat ExtraBold 95±3px |
| Background | Mesmerizing abstract/neon footage (Pixabay CC0), subtle zoom drift 1.0x→1.05x |
| Upload | Automated via YouTube Data API, randomized 240–420s cooldown |

---

## Visual Style

- **Font**: Montserrat ExtraBold (viral Shorts standard, SIL OFL licensed)
- **Caption color**: `#FFE000` yellow with thin (6px) black stroke + warm yellow glow halo
- **Caption position**: ~45–60% from top (randomized per video, clear of YouTube UI)
- **Words per chunk**: 1 (Hormozi-style karaoke)
- **Pop animation**: 1.25x → 1.0x in 0.07s (aggressive punch on each word)
- **Background**: Subtle zoom drift (1.0x → 1.03–1.07x) + random crop offset
- **Loop ending**: 0.4s crossfade for seamless rewatch
- **No background music** unless CC0 tracks in assets/music/

---

## TTS Settings

- **Rate**: `-5%` (slightly below default — adds natural pauses, prevents rushed feeling)
- **Voices**: 5-voice rotating pool (en-GB-RyanNeural, en-US-AriaNeural, en-US-GuyNeural, en-US-DavisNeural, en-US-JennyNeural)
- **Silence trimming**: Ultra-tight 0.05s buffer for abrupt endings that force rewatches

---

## Notes for Future Development

- More background video variety needed (5–10 clips) to avoid repetitive content flags
- Consider A/B testing 1 vs 2 words per chunk
- Thumbnail automation not yet implemented
- Comment pinning / engagement automation: rotating pool implemented (10 variations + self-reply)
- Upload scheduling with timezone-aware timing not yet implemented
- YouTube Studio "Related Video" linking not yet automated

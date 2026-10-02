# YT Automater Core Architecture & Styling Rules

## Visual Styling
- **Text Color:** All video text must be neon green (`#00FF88`). Do not use category-specific text colors.
- **Backgrounds:** Do not apply dark gradient overlays to the top or bottom of the screen; backgrounds should be bright and clearly visible.

## The Interactive Pop-Up Engine
When creating new interactive content types, use the established "Dynamic Image Pop-up" architecture:
1. **Prompting:** Instruct Gemini to return JSON containing an `answer_keyword` and a highly detailed `visual_prompt`.
2. **Image Fetching:** Use `urllib` to hit `https://image.pollinations.ai/prompt/<safe_prompt>?width=1080&height=1920`. It is completely free and requires no API key. Do NOT attempt to use paid APIs like DALL-E or Midjourney.
3. **Compositing:** Pass the downloaded image path and the `answer_keyword` into `video_gen.py`. The MoviePy engine will automatically find the exact spoken timestamp in the `.srt` file and composite the image as a white-bordered polaroid with a slow zoom drift.

## Daily Upload Schedule (8 Videos/Day)
The `.github/workflows/youtube_bot.yml` schedule operates on a strict 5+3 slot system:
- **5 Guaranteed Interactive Slots:** `quiz` (0:00 UTC), `two_truths` (3:00 UTC), `riddle` (6:00 UTC), `survive` (9:00 UTC), `spot_fake` (12:00 UTC).
- **3 Randomized Slots:** `random_old` (15:00, 18:00, 21:00 UTC) which randomly selects from legacy story formats.
Do not remove the interactive formats from their dedicated slots without user approval.

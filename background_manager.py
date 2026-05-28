"""
Smart Background Video Manager for YouTube Shorts Bot

Tracks which time segments of each background video have already been used
across all generated shorts, ensuring no two videos share the same footage.

Usage:
    from background_manager import pick_background_segment

The tracker stores used segments in assets/used_segments.json.
Each entry logs: {video_file: [(start1, end1), (start2, end2), ...]}
"""
import os
import sys
import json
import random
import glob

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

ASSETS_DIR = "assets"
TRACKER_FILE = "used_segments.json"

# Minimum gap between used segments (seconds) — avoids near-identical cuts
MIN_GAP = 5.0


def load_tracker():
    """Loads the used-segments tracker from disk."""
    if os.path.exists(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_tracker(tracker):
    """Persists the used-segments tracker to disk."""
    dir_name = os.path.dirname(TRACKER_FILE)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(TRACKER_FILE, 'w', encoding='utf-8') as f:
        json.dump(tracker, f, indent=2)


def get_used_ranges(tracker, video_path):
    """Returns list of (start, end) tuples already used from this video."""
    key = os.path.basename(video_path)
    return tracker.get(key, [])


def find_free_segment(video_duration, needed_duration, used_ranges, min_gap=MIN_GAP):
    """
    Finds a start time in the video that doesn't overlap any previously used range.

    Strategy:
    1. Build a list of all forbidden intervals (used range ± min_gap buffer).
    2. Collect all candidate start points that avoid forbidden zones.
    3. Pick randomly from the candidates.
    4. If no candidate exists (video fully used), reset the tracker for this file
       and start fresh — this happens when a video has been used in so many shorts
       that no unused segment long enough remains.

    Returns: float start_time
    """
    max_start = max(0.0, video_duration - needed_duration)
    if max_start <= 0:
        return 0.0  # Video shorter than needed — use from start, loop handles the rest

    # Build forbidden intervals with a buffer on each side
    forbidden = []
    for (s, e) in used_ranges:
        forbidden.append((max(0, s - min_gap), min(video_duration, e + min_gap)))

    # Merge overlapping forbidden intervals
    forbidden.sort()
    merged = []
    for interval in forbidden:
        if merged and interval[0] <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], interval[1]))
        else:
            merged.append(list(interval))

    # Find free windows
    free_windows = []
    cursor = 0.0
    for (fb_start, fb_end) in merged:
        if cursor < fb_start:
            window_max_start = min(fb_start, max_start)
            if window_max_start > cursor:
                free_windows.append((cursor, window_max_start))
        cursor = max(cursor, fb_end)
    if cursor < max_start:
        free_windows.append((cursor, max_start))

    if not free_windows:
        # All segments used — reset this video's history
        print(f"  ℹ️  All segments of this video used — resetting its history")
        return random.uniform(0, max_start)

    # Pick a random window, then a random start within it
    window = random.choice(free_windows)
    return random.uniform(window[0], window[1])


def record_segment(tracker, video_path, start_time, end_time):
    """Records a used segment in the tracker."""
    key = os.path.basename(video_path)
    if key not in tracker:
        tracker[key] = []
    tracker[key].append([round(start_time, 2), round(end_time, 2)])


def get_all_backgrounds():
    """
    Returns all available background video files from the assets directory.
    Excludes files with 'background_small' in the name (kept as a safe fallback only).
    """
    patterns = [
        os.path.join(ASSETS_DIR, "*.mp4"),
        os.path.join(ASSETS_DIR, "*.webm"),
        os.path.join(ASSETS_DIR, "*.mov"),
    ]
    all_videos = []
    for pattern in patterns:
        all_videos.extend(glob.glob(pattern))

    # Sort for deterministic listing
    all_videos.sort()
    return all_videos


def pick_background_segment(needed_duration):
    """
    Main entry point. Picks a background video and a start time that has
    never been used before (or hasn't been used recently).

    Returns:
        (video_path, start_time) — use as:
            bg = VideoFileClip(video_path).subclip(start_time, start_time + needed_duration)
        OR
        (video_path, 0.0) if the video is shorter than needed_duration (pipeline will loop it)

    The caller must call record_used_segment() AFTER successfully rendering.
    """
    tracker = load_tracker()
    all_bgs = get_all_backgrounds()

    if not all_bgs:
        print("  ⚠️  No background videos in assets/ — using dark background")
        return None, 0.0

    # Exclude background_small.mp4 from candidate options
    all_bgs = [bg for bg in all_bgs if "background_small.mp4" not in os.path.basename(bg)]
    if not all_bgs:
        # Fallback if only background_small is present
        all_bgs = get_all_backgrounds()

    # Shuffle list for true randomized selection
    random.shuffle(all_bgs)

    candidates = []

    for video_path in all_bgs:
        try:
            # Get video duration without loading the whole file
            from moviepy.editor import VideoFileClip
            probe = VideoFileClip(video_path)
            duration = probe.duration
            probe.close()
        except Exception:
            continue

        used_ranges = get_used_ranges(tracker, video_path)

        # Calculate total free time remaining in this video
        total_used = sum(max(0, e - s) for s, e in used_ranges)
        free_time = max(0, duration - total_used)

        # A video is a valid candidate if it has enough unused duration, 
        # or if the video itself is shorter than needed_duration (in which case it will loop)
        if free_time >= needed_duration or duration < needed_duration:
            candidates.append((video_path, duration, used_ranges))

    if candidates:
        # Randomly pick from all valid candidate videos for visual variety!
        best_video, duration, used_ranges = random.choice(candidates)
        if duration >= needed_duration:
            best_start = find_free_segment(duration, needed_duration, used_ranges)
        else:
            # Video will loop, start from the beginning
            best_start = 0.0
    else:
        # Fallback: pick any video from all_bgs at random and reset its history
        best_video = random.choice(all_bgs)
        best_start = 0.0
        key = os.path.basename(best_video)
        tracker[key] = []
        save_tracker(tracker)

    video_name = os.path.basename(best_video)
    print(f"  📹 Background: {video_name} (start: {best_start:.1f}s)")
    return best_video, best_start


def record_used_segment(video_path, start_time, end_time):
    """
    Call this AFTER a video has been successfully rendered to log the used segment.
    """
    tracker = load_tracker()
    record_segment(tracker, video_path, start_time, end_time)
    save_tracker(tracker)
    print(f"  ✅ Logged segment {start_time:.1f}s–{end_time:.1f}s for {os.path.basename(video_path)}")


def show_usage_report():
    """Prints a report of how much of each background video has been used."""
    tracker = load_tracker()
    all_bgs = get_all_backgrounds()

    print("\n📊 Background Video Usage Report")
    print("─" * 50)

    if not tracker:
        print("  No usage data yet.")
        return

    for video_path in all_bgs:
        key = os.path.basename(video_path)
        used = tracker.get(key, [])
        total_used = sum(max(0, e - s) for s, e in used)
        print(f"  {key}:")
        print(f"    Used {len(used)} time(s), {total_used:.0f}s of footage consumed")

    print("─" * 50)


if __name__ == "__main__":
    show_usage_report()

"""
Generate Review Batch — Generates 1 local sample video for each of the 6 active niches.
"""
import subprocess
import sys
import os

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

niches = [
    "number_facts",
    "history",
    "would_you_rather",
    "quiz",
    "story",
    "gossip"
]

print("=" * 60)
print("🎬 GENERATING 6 LOCAL REVIEW VIDEOS (1 per active niche)")
print("=" * 60)

results = []

for i, niche in enumerate(niches, 1):
    print(f"\n[{i}/{len(niches)}] 🚀 Generating: {niche.upper()}...")
    cmd = [sys.executable, "main.py", "--no-upload", "--content-type", niche, "-n", "1"]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
    
    output_lines = []
    video_path = None
    for line in iter(process.stdout.readline, ''):
        print(line, end='', flush=True)
        output_lines.append(line)
        if "Video saved at:" in line or "Video rendered:" in line:
            parts = line.strip().split(":")
            if len(parts) >= 2:
                video_path = ":".join(parts[1:]).strip()
    
    process.wait()
    
    # Check if a video was created in videos_to_upload
    if process.returncode == 0:
        results.append((niche, True, "Success"))
    else:
        results.append((niche, False, f"Exit code {process.returncode}"))

print("\n" + "=" * 60)
print("🏁 BATCH GENERATION SUMMARY")
print("=" * 60)
for niche, success, msg in results:
    status_icon = "✅" if success else "❌"
    print(f"{status_icon} {niche:<20}: {msg}")
print("=" * 60)

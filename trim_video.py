from moviepy.editor import VideoFileClip

print("Trimming background video...")
# Load video
clip = VideoFileClip("assets/background.mp4")

# Take the first 4 minutes
clip = clip.subclip(0, 240)

# Remove audio to save space
clip = clip.without_audio()

# Resize to 720p height to save massive amounts of space (we crop to portrait anyway)
clip = clip.resize(height=720)

# Write to new file
clip.write_videofile("assets/background_small.mp4", codec="libx264", bitrate="1500k")
print("Done!")

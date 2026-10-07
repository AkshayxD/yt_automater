import os

def generate_survival_script():
    """
    Uses Gemini to generate a viral Survival Hacks / "Facts that could save your life" script.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return "FACTS THAT COULD SAVE YOUR LIFE", "If you smell fish in your house, leave immediately. It is an electrical fire."

    try:
        from google import genai
        import json
        client = genai.Client(api_key=api_key)
        
        prompt = """You are a viral YouTube Shorts creator making a "Facts that could save your life" video.
        
Write a 60-80 word script containing 3 rare, obscure, but 100% true survival facts or life-saving tips.
The first sentence MUST be a dramatic hook like "If you ever smell fish in your house, get out immediately."
End the script with an engagement CTA asking them to subscribe to survive.

Respond ONLY with a valid JSON object in this format:
{
  "headline": "A punchy ALL CAPS title (5-9 words)",
  "script": "The 60-80 word narration script."
}
"""
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "temperature": 1.0,
                "response_mime_type": "application/json",
            }
        )
        
        data = json.loads(response.text.strip())
        headline = data.get("headline", "FACTS THAT COULD SAVE YOUR LIFE").strip()
        script = data.get("script", "").strip()
        
        return headline, script
    except Exception as e:
        print(f"  ⚠️ Gemini AI error: {e}")
        return "FACTS THAT COULD SAVE YOUR LIFE", "If you smell fish in your house, leave immediately. It is an electrical fire."

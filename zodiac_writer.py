import os
import random

def generate_zodiac_script():
    """
    Uses Gemini to generate a viral Zodiac / Astrology roast script.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    sign = random.choice(signs)
    
    if not api_key:
        return f"Why {sign} is toxic", f"{sign} is the most toxic sign because they never text back. Comment if you agree.", sign

    try:
        from google import genai
        import json
        client = genai.Client(api_key=api_key)
        
        prompt = f"""You are a viral YouTube Shorts creator making an astrology roast video.
        
Write a 60-80 word script roasting the Zodiac sign: {sign}.
Be brutally honest, a little sarcastic, but highly entertaining. 
The first sentence MUST be a dramatic hook like "Never date a {sign} because..." or "Here is the dark truth about {sign}."
End the script with an engagement CTA asking if viewers agree or asking them to tag a {sign}.

Respond ONLY with a valid JSON object in this format:
{{
  "headline": "A punchy ALL CAPS title (5-9 words)",
  "script": "The 60-80 word narration script."
}}
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
        headline = data.get("headline", f"THE DARK TRUTH ABOUT {sign.upper()}").strip()
        script = data.get("script", "").strip()
        
        return headline, script, sign
    except Exception as e:
        print(f"  ⚠️ Gemini AI error: {e}")
        return f"Why {sign} is toxic", f"{sign} is the most toxic sign because they never text back. Comment if you agree.", sign

"""
Fake Text Message Script Writer — Generates dramatic chat conversation scripts for YouTube Shorts.

Uses Google Gemini 2.5 Flash (free tier: 15 RPM, 1500 RPD) to create:
1. A punchy, curiosity-driven headline (ALL CAPS, 4-8 words)
2. A narrator-read script that tells the story of the text conversation
3. A structured messages array for video_gen.py to render chat bubbles

Content is 100% original — AI-generated fictional conversations.
No scraping needed. Pure AI generation with rotating themes.

Requires: GEMINI_API_KEY environment variable
Fallback: Returns a pre-written fallback script if API is unavailable
"""
import os
import sys
import re
import json
import random

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# --- Fake Text Theme Bank ---
# 30 rotating scenarios to prevent repetition across days.
# Each theme has the scenario setup and the relationship dynamic.
FAKE_TEXT_THEMES = [
    {"theme": "Ex Texts at 3 AM", "scenario": "Your ex sends you a text at 3 AM after 2 years of no contact, saying they made a mistake.", "dynamic": "ex-partner"},
    {"theme": "Boss Demands Weekend Work", "scenario": "Your boss texts you on a Saturday demanding you come in, threatening to fire you if you don't.", "dynamic": "boss-employee"},
    {"theme": "Partner Caught Texting Someone", "scenario": "You find suspicious texts on your partner's phone from someone named 'gym buddy' with heart emojis.", "dynamic": "romantic-partner"},
    {"theme": "Landlord Illegal Rent Hike", "scenario": "Your landlord texts demanding a 50% rent increase effective immediately, threatening eviction.", "dynamic": "landlord-tenant"},
    {"theme": "Friend Owes Money", "scenario": "A friend who borrowed $500 six months ago keeps making excuses and now says they shouldn't have to pay it back.", "dynamic": "friendship"},
    {"theme": "Mom Guilt Trip", "scenario": "Your mom sends a passive-aggressive text about you not visiting enough, comparing you to your sibling.", "dynamic": "parent-child"},
    {"theme": "Wrong Number Confession", "scenario": "Someone sends you a text clearly meant for someone else, confessing a secret about a mutual friend.", "dynamic": "stranger"},
    {"theme": "Roommate Ate Your Food", "scenario": "Your roommate ate your meal-prepped food for the entire week and says you're overreacting.", "dynamic": "roommate"},
    {"theme": "Wedding Uninvite", "scenario": "A friend uninvites you from their wedding via text because their new partner doesn't like you.", "dynamic": "friendship"},
    {"theme": "Coworker Takes Credit", "scenario": "A coworker texts you bragging about the promotion they got using YOUR project idea.", "dynamic": "coworker"},
    {"theme": "Neighbor Noise Complaint", "scenario": "Your neighbor sends an aggressive text threatening to call the police because your dog barked once.", "dynamic": "neighbor"},
    {"theme": "Date Cancel Last Minute", "scenario": "Your date cancels 10 minutes before you're supposed to meet, saying they 'forgot' they had plans.", "dynamic": "dating"},
    {"theme": "Sibling Demands Inheritance", "scenario": "Your sibling texts demanding you give them a larger share of your parents' inheritance because they 'need it more'.", "dynamic": "sibling"},
    {"theme": "Friend MLM Pitch", "scenario": "A friend you haven't spoken to in years texts you out of nowhere with a 'business opportunity' pitch.", "dynamic": "friendship"},
    {"theme": "Teacher Accuses Cheating", "scenario": "A teacher texts your parent accusing you of cheating on an exam you studied weeks for.", "dynamic": "teacher-student"},
    {"theme": "Ex's New Partner Texts You", "scenario": "Your ex's new partner texts you telling you to stay away, even though you haven't contacted your ex.", "dynamic": "ex-situation"},
    {"theme": "Uber Driver Rant", "scenario": "Your Uber driver texts you after the ride, angry about the tip amount, demanding more money.", "dynamic": "service"},
    {"theme": "Group Chat Betrayal", "scenario": "You discover a group chat where your 'friends' have been talking about you behind your back.", "dynamic": "friend-group"},
    {"theme": "Freelance Client Won't Pay", "scenario": "A client refuses to pay for completed freelance work, saying they 'changed their mind' about needing it.", "dynamic": "client"},
    {"theme": "Parent Reads Diary", "scenario": "Your parent texts you quotes from your private journal they found and read without permission.", "dynamic": "parent-child"},
    {"theme": "Bridezilla Demands", "scenario": "A bride demands you dye your hair for her wedding because it 'clashes with the color scheme'.", "dynamic": "friendship"},
    {"theme": "Gym Bro Unsolicited Advice", "scenario": "Someone at your gym texts you unsolicited diet advice after getting your number from the sign-in sheet.", "dynamic": "stranger"},
    {"theme": "Best Friend Ghosting", "scenario": "Your best friend of 10 years suddenly stops responding to all your messages with no explanation.", "dynamic": "best-friend"},
    {"theme": "Entitled Customer", "scenario": "A customer from your small business texts demanding a full refund AND keeps the product, threatening a bad review.", "dynamic": "business"},
    {"theme": "Family Vacation Guilt", "scenario": "Your family group chat guilts you for not being able to afford the expensive vacation they planned without asking.", "dynamic": "family"},
    {"theme": "Toxic Ex Threatens", "scenario": "Your toxic ex threatens to share private photos unless you take them back.", "dynamic": "ex-partner"},
    {"theme": "Fake Sick Coworker", "scenario": "A coworker who called in sick posts Instagram stories from a beach vacation, leaving you to cover their shift.", "dynamic": "coworker"},
    {"theme": "Parking Spot War", "scenario": "Your neighbor leaves an aggressive note and texts demanding you stop parking in 'their' spot on a public street.", "dynamic": "neighbor"},
    {"theme": "Surprise Party Ruined", "scenario": "Someone accidentally reveals your surprise birthday party in a group text, then blames you for being in the chat.", "dynamic": "friend-group"},
    {"theme": "Pet Sitter Disaster", "scenario": "Your pet sitter texts you that they let your dog off-leash and it ran away, but 'it's not their fault'.", "dynamic": "service"},
]

# System prompt optimized for Fake Text Message scripts
FAKE_TEXT_SYSTEM_PROMPT = """You are the #1 viral "Fake Text" YouTube Shorts scriptwriter. Your videos hit 8M+ views because they feel like snooping on someone's private drama — viewers can't look away.

YOUR STYLE: Conversational, dramatic, building. You narrate the text exchange as if you're telling your best friend about a crazy conversation that just happened. The viewer feels like they're reading over your shoulder.

THE PERFECT SCRIPT STRUCTURE:

1. NARRATOR HOOK (1 sentence, 0-3 seconds): Set the scene instantly. "Look at what my ex just sent me at 3 AM." / "My boss actually had the AUDACITY to text me this." NEVER start with "So" or "Hey guys". Drop straight into the drama.

2. NARRATED CONVERSATION (5-8 exchanges, 3-30 seconds): Narrate the text exchange naturally as spoken word. Read each message with emotion — anger, disbelief, sarcasm. Add reactions between messages: "And then... they actually said THIS..." / "I couldn't believe the next message." Build tension with each message.

3. REACTION + CTA (1-2 sentences, 30-35 seconds): Your genuine reaction, then force comments. "Was I wrong to block them?" / "Comment BLOCK or REPLY." / "What would YOU have texted back?"

CRITICAL RULES:
1. 90-110 words for the SCRIPT (narration) — what gets spoken by TTS.
2. 6-12 messages in the MESSAGES array — what gets rendered as chat bubbles.
3. Messages should be SHORT (under 20 words each) — they need to fit in chat bubbles.
4. The narration should flow naturally even WITHOUT seeing the bubbles — it must work as audio-only.
5. NO EMOJIS in the script narration. Emojis ARE allowed in the messages array (chat bubbles).
6. PROPER APOSTROPHES: Always write "don't" not "dont", "you're" not "youre".
7. MAKE IT BELIEVABLE: These should feel like REAL texts. Use texting shorthand in messages (ngl, tbh, lol, etc.)."""

FAKE_TEXT_USER_PROMPT = """Write a viral "Fake Text" YouTube Shorts script about this scenario:

SCENARIO: {scenario}
RELATIONSHIP: {dynamic}
THEME: {theme}

Respond ONLY with a valid JSON object:
{{
  "headline": "A punchy ALL CAPS title (4-8 words). Examples: 'MY EX TEXTED ME AT 3 AM', 'MY BOSS ACTUALLY SAID THIS'",
  "script": "The full NARRATED script (90-110 words). Hook → Narrate the conversation → Reaction + CTA. This is what the TTS voice reads aloud.",
  "messages": [
    {{"sender": "them", "text": "the message text"}},
    {{"sender": "me", "text": "the reply text"}},
    {{"sender": "them", "text": "their response"}}
  ]
}}

The 'messages' array should have 6-12 entries. Each message is SHORT (under 20 words). 'sender' is either 'me' or 'them'."""


def get_unused_theme(used_themes=None):
    """
    Picks a Fake Text theme that hasn't been used recently.

    Args:
        used_themes: List of recently used theme names to avoid

    Returns:
        dict with 'theme', 'scenario', 'dynamic' keys
    """
    if not used_themes:
        return random.choice(FAKE_TEXT_THEMES)

    available = [t for t in FAKE_TEXT_THEMES if t["theme"] not in used_themes]

    if not available:
        print("  ♻️ All Fake Text themes exhausted — resetting rotation")
        available = FAKE_TEXT_THEMES

    return random.choice(available)


def generate_fake_text_script(used_themes=None):
    """
    Generates a Fake Text Message script using Gemini AI.

    Args:
        used_themes: List of recently used theme names to avoid repetition

    Returns:
        tuple: (headline, script, messages, theme_name)
               messages is a list of {"sender": "me"/"them", "text": "..."} dicts
        Falls back to a pre-written script if API is unavailable
    """
    api_key = os.environ.get("GEMINI_API_KEY")

    theme = get_unused_theme(used_themes)
    theme_name = theme["theme"]
    print(f"  💬 Selected Fake Text theme: \"{theme_name}\"")
    print(f"     Dynamic: {theme['dynamic']}")

    if not api_key:
        print("  ⚠️ GEMINI_API_KEY not found! Using fallback script.")
        return _get_fallback_script(theme)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = FAKE_TEXT_USER_PROMPT.format(
            scenario=theme["scenario"],
            dynamic=theme["dynamic"],
            theme=theme["theme"]
        )

        print("  🤖 Generating Fake Text script with Gemini 2.5 Flash...")
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={
                "system_instruction": FAKE_TEXT_SYSTEM_PROMPT,
                "temperature": 1.0,
                "max_output_tokens": 600,
                "response_mime_type": "application/json",
            }
        )

        result_text = response.text.strip()

        # Clean markdown code blocks
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        elif result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        try:
            data = json.loads(result_text)
            headline = data.get("headline", theme_name.upper()).strip()
            script = data.get("script", "").strip()
            messages = data.get("messages", [])

            if not script:
                print("  ⚠️ AI returned empty script! Using fallback.")
                return _get_fallback_script(theme)

            # Validate messages
            if not messages or len(messages) < 3:
                print("  ⚠️ AI returned too few messages, using fallback.")
                return _get_fallback_script(theme)

        except json.JSONDecodeError as e:
            print(f"  ⚠️ Failed to parse JSON: {e}, using fallback")
            print(f"  Raw response: {result_text[:200]}")
            return _get_fallback_script(theme)

        # Clean up formatting
        headline = re.sub(r'[*#_]', '', headline).strip('"').strip("'")
        script = re.sub(r'[*#_]', '', script)

        # Validate word count
        word_count = len(script.split())
        if word_count > 130:
            words = script.split()
            trimmed = ' '.join(words[:110])
            boundaries = [trimmed.rfind('.'), trimmed.rfind('!'), trimmed.rfind('?')]
            last_boundary = max(boundaries)
            if last_boundary > int(len(trimmed) * 0.7):
                script = trimmed[:last_boundary + 1]
            else:
                script = trimmed
            print(f"  ⚠️ Script was {word_count} words — trimmed to {len(script.split())}")

        # Normalize messages
        clean_messages = []
        for msg in messages:
            sender = msg.get("sender", "them").lower().strip()
            text = msg.get("text", "").strip()
            if sender not in ("me", "them"):
                sender = "them"
            if text:
                clean_messages.append({"sender": sender, "text": text})

        print(f"  ✅ Fake Text script generated!")
        print(f"     Headline: \"{headline}\"")
        print(f"     Messages: {len(clean_messages)}")
        print(f"     Narration words: {len(script.split())}")

        return headline, script, clean_messages, theme_name

    except ImportError:
        print("  ⚠️ google-genai not installed — using fallback")
        return _get_fallback_script(theme)
    except Exception as e:
        print(f"  ⚠️ Gemini API error: {e} — using fallback")
        return _get_fallback_script(theme)


def _get_fallback_script(theme):
    """Returns a pre-written fallback script when the API is unavailable."""
    fallback_scripts = [
        {
            "headline": "MY EX TEXTED ME AT 3 AM",
            "script": "Look at what my ex just sent me... at 3 AM. After two years of absolute silence. They said, I made a mistake. I miss you. Can we talk? I was literally sleeping. So I asked them, why now? And they said... because I just saw your story and realized nobody will ever get me like you did. The audacity. I told them, you had your chance and you blew it. And then... they hit me with, I know, but I've changed. I left them on read. Was I right? Comment BLOCK or REPLY below.",
            "messages": [
                {"sender": "them", "text": "hey... are you awake?"},
                {"sender": "them", "text": "I made a mistake. I miss you."},
                {"sender": "them", "text": "can we talk? please"},
                {"sender": "me", "text": "it's 3 AM. why now?"},
                {"sender": "them", "text": "I saw your story and realized nobody will ever get me like you did"},
                {"sender": "me", "text": "you had your chance and you blew it"},
                {"sender": "them", "text": "I know but I've changed. I promise."},
                {"sender": "me", "text": "Read ✓✓"},
            ],
        },
        {
            "headline": "MY BOSS ACTUALLY SAID THIS",
            "script": "My boss texted me on a Saturday morning, demanding I come in to work. I told them, it's my day off, I have plans. And they said... your plans don't matter, the company needs you. I said, I'm not coming in, I already worked 50 hours this week. Then they actually threatened me. They said, if you don't show up, don't bother coming Monday either. So I screenshot the conversation, sent it to HR, and replied, see you in court. They haven't texted me since. Would you have quit on the spot? Comment below.",
            "messages": [
                {"sender": "them", "text": "I need you to come in today"},
                {"sender": "me", "text": "It's Saturday, I have plans"},
                {"sender": "them", "text": "Your plans don't matter. The company needs you."},
                {"sender": "me", "text": "I already worked 50 hours this week"},
                {"sender": "them", "text": "If you don't show up, don't bother coming Monday"},
                {"sender": "me", "text": "Screenshot saved. See you in court 😊"},
            ],
        },
        {
            "headline": "CAUGHT MY ROOMMATE RED HANDED",
            "script": "I came home to find my entire week of meal prep... gone. My roommate ate all of it. So I texted them. I said, did you eat my food? And they said, oh yeah, I thought it was for everyone. I told them, it had my name on every container. Then they actually said... you're overreacting, it's just food. Just food? That was 30 dollars and four hours of cooking. I said, you're paying me back or I'm locking the fridge. They called me petty. I call it boundaries. Comment PETTY or FAIR below.",
            "messages": [
                {"sender": "me", "text": "did you eat my meal prep??"},
                {"sender": "them", "text": "oh yeah lol I thought it was for everyone"},
                {"sender": "me", "text": "it literally had MY NAME on every container"},
                {"sender": "them", "text": "you're overreacting it's just food"},
                {"sender": "me", "text": "that was $30 and 4 hours of cooking"},
                {"sender": "me", "text": "you're paying me back or I'm locking the fridge"},
                {"sender": "them", "text": "wow you're so petty"},
                {"sender": "me", "text": "and you're a thief. pay up."},
            ],
        },
    ]

    chosen = random.choice(fallback_scripts)
    return chosen["headline"], chosen["script"], chosen["messages"], theme["theme"]


if __name__ == "__main__":
    headline, script, messages, theme_name = generate_fake_text_script()
    print(f"\n--- RESULT ---")
    print(f"THEME: {theme_name}")
    print(f"HEADLINE: {headline}")
    print(f"NARRATION: {script}")
    print(f"WORDS: {len(script.split())}")
    print(f"\nMESSAGES ({len(messages)}):")
    for i, msg in enumerate(messages, 1):
        side = "→" if msg["sender"] == "me" else "←"
        print(f"  {i}. {side} [{msg['sender']}]: {msg['text']}")

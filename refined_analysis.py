import json
from collections import defaultdict

with open('all_shorts_lockups.json', 'r', encoding='utf-8') as f:
    items = json.load(f)

def parse_views(v_str):
    if not v_str or 'No views' in v_str:
        return 0
    v_str = v_str.lower().replace('views', '').replace('view', '').strip()
    if 'k' in v_str:
        try:
            return int(float(v_str.replace('k', '')) * 1000)
        except:
            return 0
    elif 'm' in v_str:
        try:
            return int(float(v_str.replace('m', '')) * 1000000)
        except:
            return 0
    else:
        try:
            return int(v_str.replace(',', ''))
        except:
            return 0

videos = {}
order = 0
for item in items:
    entity_id = item.get('entityId', '')
    vid_id = ''
    if entity_id.startswith('shorts-shelf-item-'):
        vid_id = entity_id.replace('shorts-shelf-item-', '')
    title = item.get('overlayMetadata', {}).get('primaryText', {}).get('content', '')
    views_text = item.get('overlayMetadata', {}).get('secondaryText', {}).get('content', '')
    views = parse_views(views_text)
    if vid_id and vid_id not in videos:
        videos[vid_id] = {
            'id': vid_id,
            'title': title,
            'views_text': views_text,
            'views': views,
            'order': order
        }
        order += 1

v_list = list(videos.values())

def get_fine_category(title):
    t = title.upper()
    if any(k in t for k in ["SHUFFLING CARDS", "COSMIC HISTORY", "BRAIN VS THE UNIVERSE", "NUMBER FACT", "NUMBER"]):
        return "Mind-Blowing Scale & Science Facts"
    if any(k in t for k in ["WOULD YOU RATHER", "FLY SLOW", "THIS CHOICE WILL BREAK YOU", "10 MILLION OR START OVER", "NEVER LIE OR NEVER BE LIED TO"]):
        return "Would You Rather / Dilemmas"
    if "HISTORY IN" in t or "HISTORICAL" in t:
        return "Dramatic History in [Year]"
    if any(k in t for k in ["AITA", "TIFU", "NEIGHBOR", "SISTER", "MOM", "WEDDING", "ENTITLED", "PAY", "HUSBAND", "WIFE", "COLLEAGUE", "BOSS", "DOG ATE MY HOMEWORK"]):
        return "Reddit Drama & Real Stories"
    if any(k in t for k in ["SCARY THING", "BASEMENT", "SOMETHING LIVES", "SCRATCHING STARTS", "I SHOULD NEVER HAVE ANSWERED", "TEETH IN MY NEIGHBOR", "GLITCH"]):
        return "Horror & Glitch in Matrix"
    if any(k in t for k in ["PERSONALITY TYPE", "PSYCHOLOGY", "TOXIC PEOPLE", "NEVER TRUST SOMEONE", "THIS TRICK CONTROLS"]):
        return "Dark Psychology & Human Behavior"
    if any(k in t for k in ["PASS THIS", "QUIZ", "TRIVIA", "ONLY 1 PERCENT"]):
        return "Quiz & Interactive Trivia"
    if any(k in t for k in ["SURVIVE", "SURVIVAL"]):
        return "Survival Challenges"
    if any(k in t for k in ["STOP BEING TOO NICE", "YOUR ANGER", "SILENCE IS POWER", "SEPARATES WINNERS", "DISCIPLINE", "STOIC"]):
        return "Stoic Quotes & Inspiration"
    return "Miscellaneous Stories"

cat_groups = defaultdict(list)
for v in v_list:
    cat = get_fine_category(v['title'])
    cat_groups[cat].append(v)

results = []
for cat, vids in cat_groups.items():
    tot_views = sum(v['views'] for v in vids)
    cnt = len(vids)
    avg_v = tot_views / cnt
    zero_cnt = len([v for v in vids if v['views'] == 0])
    max_v = max(v['views'] for v in vids)
    top_video = sorted(vids, key=lambda x: x['views'], reverse=True)[0]
    results.append({
        'category': cat,
        'count': cnt,
        'total_views': tot_views,
        'avg_views': round(avg_v, 1),
        'zero_pct': round((zero_cnt / cnt) * 100, 1),
        'max_views': max_v,
        'top_title': top_video['title']
    })

results.sort(key=lambda x: x['avg_views'], reverse=True)

print("=== REFINED CATEGORY PERFORMANCE ===")
for r in results:
    print(f"{r['category']:<35} | {r['count']:>3} vids | Avg: {r['avg_views']:>5.1f} | Max: {r['max_views']:>3} | Zero%: {r['zero_pct']:>5.1f}% | Top: {r['top_title']}")

with open('fine_metrics.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

import json
import re

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
v_sorted = sorted(v_list, key=lambda x: x['views'], reverse=True)

print(f"Total Unique Shorts: {len(v_list)}")
print(f"Total Views across all Shorts: {sum(v['views'] for v in v_list):,}")

print("\n=== TOP 25 MOST VIEWED SHORTS ===")
for i, v in enumerate(v_sorted[:25], 1):
    print(f"{i:>2}. {v['views']:>8,} views ({v['views_text']}) | [{v['id']}] {v['title']}")

print("\n=== VIEW BRACKETS ===")
zero_views = len([v for v in v_list if v['views'] == 0])
under_10 = len([v for v in v_list if 1 <= v['views'] < 10])
ten_to_100 = len([v for v in v_list if 10 <= v['views'] < 100])
hundred_to_1k = len([v for v in v_list if 100 <= v['views'] < 1000])
one_k_to_5k = len([v for v in v_list if 1000 <= v['views'] < 5000])
five_k_plus = len([v for v in v_list if v['views'] >= 5000])

print(f"0 views (No views):      {zero_views:>4} ({zero_views/len(v_list)*100:.1f}%)")
print(f"1 - 9 views:             {under_10:>4} ({under_10/len(v_list)*100:.1f}%)")
print(f"10 - 99 views:           {ten_to_100:>4} ({ten_to_100/len(v_list)*100:.1f}%)")
print(f"100 - 999 views:         {hundred_to_1k:>4} ({hundred_to_1k/len(v_list)*100:.1f}%)")
print(f"1,000 - 4,999 views:     {one_k_to_5k:>4} ({one_k_to_5k/len(v_list)*100:.1f}%)")
print(f"5,000+ views:            {five_k_plus:>4} ({five_k_plus/len(v_list)*100:.1f}%)")

# Categorization logic
def categorize(title):
    t_upper = title.upper()
    if "ONLY 1 PERCENT CAN PASS THIS" in t_upper or "QUIZ" in t_upper or "TRIVIA" in t_upper:
        return "Quiz / Trivia"
    elif "HISTORY IN" in t_upper or "HISTORICAL" in t_upper:
        return "History"
    elif "WOULD YOU SURVIVE" in t_upper or "CAN YOU SURVIVE" in t_upper:
        return "Survival Challenge"
    elif "THIS CHOICE WILL BREAK YOU" in t_upper or "WOULD YOU RATHER" in t_upper:
        return "Would You Rather"
    elif any(k in t_upper for k in ["PERSONALITY TYPE", "DARK PSYCHOLOGY", "PSYCHOLOGY", "MANIPULATION", "PSYCHOPATH", "NARCISSIST"]):
        return "Dark Psychology"
    elif any(k in t_upper for k in ["BASEMENT", "SOMETHING LIVES", "GLITCH", "PARANORMAL", "HAUNTED", "CREEPY", "STALKER", "INTRUDER", "DON'T LOOK", "SKINWALKER"]):
        return "Glitch / Horror / Creepy"
    elif any(k in t_upper for k in ["STOP BEING TOO NICE", "SILENCE IS POWER", "YOUR ANGER", "DISCIPLINE", "STOIC", "MOTIVATION", "WEAK MEN", "NEVER TELL"]):
        return "Inspiration / Stoicism"
    elif any(k in t_upper for k in ["NUMBER", "FACTS ABOUT", "DID YOU KNOW"]):
        return "Number Facts / Trivia"
    elif any(k in t_upper for k in ["ZODIAC", "HOROSCOPE", "SIGNS"]):
        return "Zodiac"
    elif any(k in t_upper for k in ["SHOWER THOUGHT"]):
        return "Shower Thoughts"
    elif any(k in t_upper for k in ["TRUE CRIME", "SOLVED", "UNSOLVED", "KILLER", "MURDER"]):
        return "True Crime"
    elif any(k in t_upper for k in ["AITA", "TIFU", "WIFE", "HUSBAND", "NEIGHBOR", "WEDDING", "ENTITLED", "PAY", "KAREN", "BOSS", "LANDLORD", "ROOMMATE", "CHEATING", "DIVORCE", "FAMILY", "SISTER", "BROTHER", "MOM", "DAD", "MALICIOUS COMPLIANCE"]):
        return "Reddit Story (AITA/Drama)"
    else:
        return "Other / Story"

categories = {}
for v in v_list:
    cat = categorize(v['title'])
    if cat not in categories:
        categories[cat] = []
    categories[cat].append(v)

print("\n=== PERFORMANCE BY CONTENT NICHE ===")
cat_summary = []
for cat, vids in categories.items():
    total_views = sum(v['views'] for v in vids)
    count = len(vids)
    avg_views = total_views / count if count > 0 else 0
    max_views = max(v['views'] for v in vids) if count > 0 else 0
    views_above_100 = len([v for v in vids if v['views'] >= 100])
    views_above_1k = len([v for v in vids if v['views'] >= 1000])
    pct_above_100 = (views_above_100 / count) * 100 if count > 0 else 0
    cat_summary.append({
        'category': cat,
        'count': count,
        'total_views': total_views,
        'avg_views': avg_views,
        'max_views': max_views,
        'views_above_100': views_above_100,
        'views_above_1k': views_above_1k,
        'pct_above_100': pct_above_100
    })

cat_summary.sort(key=lambda x: x['total_views'], reverse=True)

print(f"{'Category':<28} | {'Videos':<6} | {'Total Views':<11} | {'Avg Views':<9} | {'Max Views':<9} | {'>=100 views':<11} | {'>=1K views':<10}")
print("-" * 105)
for c in cat_summary:
    print(f"{c['category']:<28} | {c['count']:<6} | {c['total_views']:<11,} | {c['avg_views']:<9.1f} | {c['max_views']:<9,} | {c['views_above_100']:<11} ({c['pct_above_100']:.0f}%) | {c['views_above_1k']:<10}")

with open('metrics_summary.json', 'w', encoding='utf-8') as f:
    json.dump({'categories': cat_summary, 'top_videos': v_sorted[:50], 'all_videos': v_sorted}, f, indent=2)

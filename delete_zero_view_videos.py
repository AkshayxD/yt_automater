"""
Delete Zero-View Videos Script — Finds all videos with 0 views on YouTube and deletes them via YouTube Data API.
"""
import os
import sys
import json
import time
import base64
import pickle
import urllib.request
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Fix Windows console encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

REQUIRED_SCOPES = [
    'https://www.googleapis.com/auth/youtube',
    'https://www.googleapis.com/auth/youtube.force-ssl'
]

def get_authenticated_service_with_delete():
    token_file = 'token.pickle'
    client_secrets_file = 'client_secret.json'
    credentials = None

    if os.path.exists(token_file):
        with open(token_file, 'rb') as f:
            credentials = pickle.load(f)

    # Check if credentials have delete permissions
    has_delete_scope = False
    if credentials and credentials.scopes:
        for scope in REQUIRED_SCOPES:
            if scope in credentials.scopes:
                has_delete_scope = True
                break

    if not credentials or not credentials.valid or not has_delete_scope:
        if credentials and credentials.expired and credentials.refresh_token and has_delete_scope:
            print("Refreshing access token...")
            credentials.refresh(Request())
        else:
            if not has_delete_scope:
                print("\n⚠️ The existing token only has upload scope ('youtube.upload').", flush=True)
                print("   Deleting videos requires 'youtube.force-ssl' or 'youtube' scope.", flush=True)
                print("👉 Launching browser authorization flow to grant delete permissions...", flush=True)
            
            if not os.path.exists(client_secrets_file):
                raise FileNotFoundError(f"'{client_secrets_file}' not found.")
            
            # Request upload + delete scopes
            all_scopes = [
                'https://www.googleapis.com/auth/youtube.upload',
                'https://www.googleapis.com/auth/youtube.force-ssl'
            ]
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, all_scopes)
            credentials = flow.run_local_server(
                port=0,
                prompt='consent',
                authorization_prompt_message='Please visit this URL to authorize this application: {url}'
            )

        # Save credentials to token.pickle
        with open(token_file, 'wb') as f:
            pickle.dump(credentials, f)
        
        # Also update token_base64.txt for GitHub Secrets
        with open(token_file, 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
        with open('token_base64.txt', 'w', encoding='utf-8') as f:
            f.write(b64_data)
        print("✅ Updated token.pickle and token_base64.txt with delete permissions!")

    return build('youtube', 'v3', credentials=credentials)

def fetch_all_shorts(channel_handle='@AutoTube-AI-1'):
    print(f"\n🔍 Fetching latest Shorts from {channel_handle}...")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'en-US,en;q=0.9'
    }
    url = f'https://www.youtube.com/{channel_handle}/shorts'
    req = urllib.request.Request(url, headers=headers)
    html = urllib.request.urlopen(req).read().decode('utf-8')
    
    match = re.search(r'var ytInitialData = ({.*?});</script>', html)
    if not match:
        raise RuntimeError("Could not find ytInitialData on shorts page.")
    
    data = json.loads(match.group(1))

    all_lockups = []

    def extract_from_obj(obj):
        found = []
        if isinstance(obj, dict):
            if 'shortsLockupViewModel' in obj:
                found.append(obj['shortsLockupViewModel'])
            for v in obj.values():
                found.extend(extract_from_obj(v))
        elif isinstance(obj, list):
            for v in obj:
                found.extend(extract_from_obj(v))
        return found

    def find_continuation_token(obj):
        if isinstance(obj, dict):
            if 'continuationCommand' in obj and 'token' in obj['continuationCommand']:
                return obj['continuationCommand']['token']
            for v in obj.values():
                res = find_continuation_token(v)
                if res:
                    return res
        elif isinstance(obj, list):
            for v in obj:
                res = find_continuation_token(v)
                if res:
                    return res
        return None

    all_lockups.extend(extract_from_obj(data))
    cont_token = find_continuation_token(data)

    page = 1
    while cont_token:
        url = 'https://www.youtube.com/youtubei/v1/browse?prettyPrint=false'
        payload = {
            'context': {
                'client': {
                    'clientName': 'WEB',
                    'clientVersion': '2.20231215.01.00',
                    'hl': 'en',
                    'gl': 'US'
                }
            },
            'continuation': cont_token
        }
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'),
                                     headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
        try:
            resp = urllib.request.urlopen(req)
            res_data = json.loads(resp.read().decode('utf-8'))
            new_items = extract_from_obj(res_data)
            if not new_items:
                break
            all_lockups.extend(new_items)
            cont_token = find_continuation_token(res_data)
            page += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  Warning during pagination page {page}: {e}")
            break

    # Parse videos
    videos = []
    seen = set()
    for item in all_lockups:
        entity_id = item.get('entityId', '')
        vid_id = entity_id.replace('shorts-shelf-item-', '') if entity_id.startswith('shorts-shelf-item-') else ''
        title = item.get('overlayMetadata', {}).get('primaryText', {}).get('content', '')
        views_text = item.get('overlayMetadata', {}).get('secondaryText', {}).get('content', '')
        
        is_zero_views = False
        if not views_text or 'no views' in views_text.lower():
            is_zero_views = True
        
        if vid_id and vid_id not in seen:
            seen.add(vid_id)
            videos.append({
                'id': vid_id,
                'title': title,
                'views_text': views_text,
                'zero_views': is_zero_views
            })

    print(f"✅ Total unique Shorts fetched: {len(videos)}")
    return videos

def delete_zero_view_videos(dry_run=False):
    youtube = get_authenticated_service_with_delete()
    videos = fetch_all_shorts()
    
    zero_view_vids = [v for v in videos if v['zero_views']]
    print(f"\n📊 SUMMARY:")
    print(f"   Total Shorts on Channel: {len(videos)}")
    print(f"   Shorts with Views (>0):  {len(videos) - len(zero_view_vids)}")
    print(f"   Shorts with 0 Views:     {len(zero_view_vids)}")

    if not zero_view_vids:
        print("\n🎉 No 0-view videos found to delete!")
        return

    if dry_run:
        print("\n🔎 DRY RUN MODE (no videos will be deleted):")
        for i, v in enumerate(zero_view_vids[:10], 1):
            print(f"   {i}. [{v['id']}] {v['title']} ({v['views_text']})")
        if len(zero_view_vids) > 10:
            print(f"   ... and {len(zero_view_vids) - 10} more.")
        return

    print(f"\n⚠️ Proceeding to delete {len(zero_view_vids)} zero-view videos from YouTube...")
    deleted_count = 0
    failed_count = 0

    for i, v in enumerate(zero_view_vids, 1):
        vid_id = v['id']
        title = v['title']
        try:
            youtube.videos().delete(id=vid_id).execute()
            deleted_count += 1
            print(f"[{i}/{len(zero_view_vids)}] 🗑️ Deleted: [{vid_id}] {title}")
            time.sleep(0.3)  # Gentle pacing for API quota
        except HttpError as e:
            failed_count += 1
            print(f"[{i}/{len(zero_view_vids)}] ❌ Failed to delete [{vid_id}] {title}: {e}")
        except Exception as e:
            failed_count += 1
            print(f"[{i}/{len(zero_view_vids)}] ❌ Error on [{vid_id}]: {e}")

    print("\n" + "=" * 60)
    print(f"🏁 DELETION COMPLETED")
    print(f"   Successfully deleted: {deleted_count}")
    print(f"   Failed:               {failed_count}")
    print(f"   Remaining on channel: {len(videos) - deleted_count}")
    print("=" * 60)

    # Clean upload_history.json
    try:
        history_file = 'upload_history.json'
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            deleted_ids = {v['id'] for v in zero_view_vids[:deleted_count]}
            history['videos'] = [rec for rec in history.get('videos', []) if rec.get('video_id') not in deleted_ids]
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2)
            print("✅ Cleaned deleted videos from local upload_history.json")
    except Exception as e:
        print(f"⚠️ Note on history clean: {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Delete 0-view videos from YouTube")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without deleting")
    args = parser.parse_args()

    delete_zero_view_videos(dry_run=args.dry_run)

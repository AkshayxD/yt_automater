"""
Delete Zero-View Videos Script — Finds all videos with 0 views on YouTube across the entire channel and deletes them via YouTube Data API.
"""
import os
import sys
import json
import time
import base64
import pickle
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

        with open(token_file, 'wb') as f:
            pickle.dump(credentials, f)
        
        with open(token_file, 'rb') as f:
            b64_data = base64.b64encode(f.read()).decode('utf-8')
        with open('token_base64.txt', 'w', encoding='utf-8') as f:
            f.write(b64_data)
        print("✅ Updated token.pickle and token_base64.txt with delete permissions!")

    return build('youtube', 'v3', credentials=credentials)

def fetch_all_channel_videos(youtube):
    """
    Fetches ALL videos on the authenticated channel via the uploads playlist,
    then retrieves exact statistics (including viewCount) for each video.
    """
    print("\n🔍 Fetching channel uploads playlist from YouTube Data API...")
    ch = youtube.channels().list(mine=True, part='contentDetails').execute()
    uploads_playlist_id = ch['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    video_ids = []
    next_page_token = None
    
    while True:
        res = youtube.playlistItems().list(
            playlistId=uploads_playlist_id,
            part='contentDetails',
            maxResults=50,
            pageToken=next_page_token
        ).execute()
        for item in res.get('items', []):
            video_ids.append(item['contentDetails']['videoId'])
        next_page_token = res.get('nextPageToken')
        if not next_page_token:
            break
            
    print(f"✅ Found {len(video_ids)} total videos on channel. Fetching view statistics...")
    
    videos = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        stats_res = youtube.videos().list(
            id=','.join(batch),
            part='snippet,statistics'
        ).execute()
        for item in stats_res.get('items', []):
            vid_id = item['id']
            title = item['snippet']['title']
            published = item['snippet']['publishedAt']
            views = int(item['statistics'].get('viewCount', 0))
            videos.append({
                'id': vid_id,
                'title': title,
                'published': published,
                'views': views,
                'zero_views': (views == 0)
            })
            
    return videos

def delete_zero_view_videos(dry_run=False):
    youtube = get_authenticated_service_with_delete()
    videos = fetch_all_channel_videos(youtube)
    
    zero_view_vids = [v for v in videos if v['zero_views']]
    print(f"\n📊 SUMMARY:")
    print(f"   Total Videos on Channel: {len(videos)}")
    print(f"   Videos with Views (>0):  {len(videos) - len(zero_view_vids)}")
    print(f"   Videos with 0 Views:     {len(zero_view_vids)}")

    if not zero_view_vids:
        print("\n🎉 No 0-view videos found to delete!")
        return

    if dry_run:
        print("\n🔎 DRY RUN MODE (no videos will be deleted):")
        for i, v in enumerate(zero_view_vids[:15], 1):
            print(f"   {i}. [{v['id']}] ({v['published']}) {v['title']}")
        if len(zero_view_vids) > 15:
            print(f"   ... and {len(zero_view_vids) - 15} more.")
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
            time.sleep(0.2)  # Gentle pacing for API quota
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

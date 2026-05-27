import http.client
import httplib2
import random
import time
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
  http.client.IncompleteRead, http.client.ImproperConnectionState,
  http.client.CannotSendRequest, http.client.CannotSendHeader,
  http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

def upload_video(youtube, file_path, title, description, category_id="24", keywords=None, privacy_status="private"):
    """
    Uploads a video to YouTube.
    
    Args:
        youtube: The authenticated YouTube API client object.
        file_path (str): Path to the video file to upload.
        title (str): The video title.
        description (str): The video description.
        category_id (str): The YouTube category ID (24 = Entertainment).
        keywords (list): A list of tags for the video.
        privacy_status (str): "public", "private", or "unlisted".

    Returns:
        str: The YouTube video ID on success, or None on failure.
    """
    if keywords is None:
        keywords = []
        
    print(f"  Preparing to upload: {file_path}")
    print(f"  Title: {title}")
    print(f"  Category: {category_id} | Privacy: {privacy_status}")
    print(f"  Tags: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")

    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': keywords,
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': privacy_status,
            'selfDeclaredMadeForKids': False
        }
    }

    # Call the API's videos.insert method to create and upload the video.
    # Note: For Shorts, the video should be < 60 seconds and typically vertical (e.g., 1080x1920)
    # The title or description should preferably contain #shorts
    insert_request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        # The chunksize parameter specifies the size of each chunk of data, in
        # bytes, that will be uploaded at a time. Set a higher value for
        # reliable connections as fewer chunks lead to faster uploads. Set a lower
        # value for better recovery on less reliable connections.
        #
        # Setting 'chunksize' equal to -1 in the code below means that the entire
        # file will be uploaded in a single HTTP request. (We use chunked uploads
        # for resume capability).
        media_body=MediaFileUpload(file_path, chunksize=-1, resumable=True)
    )

    video_id = resumable_upload(insert_request)
    return video_id

def resumable_upload(request):
    """
    Executes the resumable upload process with retry logic.
    
    Returns:
        str: The YouTube video ID on success, or None on failure.
    """
    response = None
    error = None
    retry = 0
    while response is None:
        try:
            print('  Uploading file...')
            status, response = request.next_chunk()
            if response is not None:
                if 'id' in response:
                    video_id = response['id']
                    print(f"  ✅ Video '{video_id}' uploaded successfully!")
                    print(f"  🔗 https://youtube.com/shorts/{video_id}")
                    return video_id
                else:
                    print(f"  ❌ Upload failed with unexpected response: {response}")
                    return None
        except HttpError as e:
            if e.resp.status in RETRIABLE_STATUS_CODES:
                error = 'A retriable HTTP error %d occurred:\n%s' % (e.resp.status, e.content)
            else:
                raise
        except RETRIABLE_EXCEPTIONS as e:
            error = 'A retriable error occurred: %s' % e

        if error is not None:
            print(f"  ⚠️ {error}")
            retry += 1
            if retry > MAX_RETRIES:
                print("  ❌ Max retries exceeded. Upload failed.")
                return None

            max_sleep = 2 ** retry
            sleep_seconds = random.random() * max_sleep
            print('  Sleeping %f seconds and then retrying...' % sleep_seconds)
            time.sleep(sleep_seconds)
    
    return None

def add_pinned_comment(youtube, video_id, text):
    """
    Adds a top-level comment to the video as the channel owner.
    (Note: YouTube Data API doesn't support 'pinning', but as the first comment
     from the creator, it stays at the top and acts as comment bait).
    
    Also posts a self-reply to double the comment count — this boosts
    engagement density signals for the algorithm.
    """
    print(f"  💬 Posting comment bait to video {video_id}...")
    try:
        body = {
            'snippet': {
                'videoId': video_id,
                'topLevelComment': {
                    'snippet': {
                        'textOriginal': text
                    }
                }
            }
        }
        response = youtube.commentThreads().insert(
            part='snippet',
            body=body
        ).execute()
        
        comment_id = response['snippet']['topLevelComment']['id']
        print(f"  ✅ Comment posted successfully! (ID: {comment_id})")
        
        # --- Self-reply chain ---
        # Reply to our own comment with a follow-up question.
        # This doubles the comment count and encourages viewers to join the thread.
        try:
            self_replies = [
                "I'm genuinely curious what you all think about this one 👇",
                "This story had me SHOOK. What would you have done?",
                "Drop your thoughts below ⬇️ I read every single comment",
                "The audacity in this story is unreal. Who was right though?",
                "I've been thinking about this all day. Am I crazy?",
            ]
            import random
            reply_text = random.choice(self_replies)
            
            reply_body = {
                'snippet': {
                    'parentId': comment_id,
                    'textOriginal': reply_text
                }
            }
            youtube.comments().insert(
                part='snippet',
                body=reply_body
            ).execute()
            print(f"  💬 Self-reply posted (engagement boost)")
        except Exception as e:
            print(f"  Note: Self-reply skipped ({e})")
        
        return comment_id
    except Exception as e:
        print(f"  ❌ Failed to post comment: {e}")
        return None


# --- Rotating Comment Bait Pool ---
# 10 variations to prevent viewer fatigue from seeing the same CTA
PART1_COMMENTS = [
    "Part 2 is on my profile! Subscribe so you don't miss the ending 👇",
    "The ending will SHOCK you — Part 2 on my profile 👇",
    "You NEED to see how this ends. Part 2 is up now 🔥",
    "Wait until you hear what happened next... Part 2 on my profile!",
    "Part 2 just dropped — the ending is wild 😱",
]

FINAL_PART_COMMENTS = [
    "Who do you think was right? Let me know down below! 👇",
    "Be honest — was I wrong here? Comment below ⬇️",
    "Rate this story 1–10 in the comments 👇",
    "Comment 'KARMA' if they got what they deserved 🔥",
    "Would YOU have done the same thing? Tell me below",
    "Who was the real villain in this story? 🤔",
    "The comments on this one are going to be WILD 👇",
    "I need to know — am I the only one who thinks this is insane?",
]


def get_pinned_comment(is_part1=False):
    """
    Returns a random engagement-bait comment from the rotating pool.
    
    Args:
        is_part1: If True, returns a Part 2 teaser comment.
                  If False, returns a debate/engagement comment.
    """
    import random
    if is_part1:
        return random.choice(PART1_COMMENTS)
    else:
        return random.choice(FINAL_PART_COMMENTS)

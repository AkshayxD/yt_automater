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

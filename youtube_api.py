import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# The SCOPES list determines what permissions the application is requesting.
# To upload videos, we need the youtube.upload scope.
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

def get_authenticated_service(client_secrets_file='client_secret.json'):
    """
    Authenticates the user using OAuth2 and returns a YouTube API service object.
    Requires a client_secret.json file downloaded from Google Cloud Console.
    """
    credentials = None
    token_file = 'token.pickle'

    # If running in the cloud (GitHub Actions), we inject the token via an environment variable
    # to avoid checking the secret binary file into version control.
    token_base64 = os.environ.get('YOUTUBE_TOKEN_PICKLE_BASE64')
    if token_base64:
        import base64
        print("Loading token.pickle from environment variable...")
        with open(token_file, 'wb') as f:
            f.write(base64.b64decode(token_base64))

    # The file token.pickle stores the user's access and refresh tokens
    if os.path.exists(token_file):
        with open(token_file, 'rb') as token:
            credentials = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            print("Refreshing access token...")
            credentials.refresh(Request())
        else:
            if not os.path.exists(client_secrets_file):
                raise FileNotFoundError(
                    f"'{client_secrets_file}' not found. You must download this "
                    "from the Google Cloud Console (APIs & Services -> Credentials) "
                    "and place it in the same directory."
                )
            print("Starting authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES)
            # Run the local server to capture the authorization code
            credentials = flow.run_local_server(port=0)
            
        # Save the credentials for the next run
        with open(token_file, 'wb') as token:
            pickle.dump(credentials, token)

    # Build and return the YouTube API client
    return build('youtube', 'v3', credentials=credentials)

if __name__ == '__main__':
    # Test authentication
    try:
        youtube = get_authenticated_service()
        print("Successfully authenticated with YouTube API!")
    except Exception as e:
        print(f"Authentication failed: {e}")

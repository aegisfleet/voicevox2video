import re
import requests
import sys
import time
from atproto import Client, models
from atproto_client.exceptions import UnauthorizedError

def extract_uri_cid(url):
    match = re.search(r'profile/([^/]+)/post/([^/]+)', url)
    if not match:
        raise ValueError("Invalid Bluesky URL format")

    handle, rkey = match.groups()
    api_url = f"https://api.bsky.app/xrpc/com.atproto.repo.getRecord"

    params = {
        "repo": handle,
        "collection": "app.bsky.feed.post",
        "rkey": rkey
    }

    response = requests.get(api_url, params=params)

    if response.status_code != 200:
        raise Exception(f"API request failed with status code {response.status_code}")

    data = response.json()

    uri = data['uri']
    cid = data['cid']

    return uri, cid

def authenticate(bs_client, username, password, retries=3, wait_time=5):
    for attempt in range(retries):
        try:
            bs_client.login(username, password)
            print("Authentication successful")
            return
        except UnauthorizedError as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < retries - 1:
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("All retry attempts failed. Please check your credentials.")
                raise e

def post(username, password, text, url=None):
    uri, cid = extract_uri_cid(url)
    print(f"URI: {uri}, CID: {cid}")

    client = Client()
    authenticate(client, username, password)

    with open('output/final_dialogue_output.mp4', 'rb') as f:
        vid_data = f.read()

    retries = 3
    for attempt in range(1, retries + 1):
        try:
            if cid and uri:
                parent_ref = models.ComAtprotoRepoStrongRef.Main(cid=cid, uri=uri)
                reply_to = models.AppBskyFeedPost.ReplyRef(parent=parent_ref, root=parent_ref)
                client.send_video(text=text, video=vid_data, video_alt=text, reply_to=reply_to)
            else:
                client.send_video(text=text, video=vid_data, video_alt=text)
            break
        except Exception as e:
            print(f"送信に失敗しました。リトライします... リトライ回数: {attempt}, エラー: {e}")
            time.sleep(3)
    else:
        print("リトライ上限に達しました。送信に失敗しました。")

def main():
    if len(sys.argv) > 1:
        username = sys.argv[1]
        password = sys.argv[2]
        text = sys.argv[3]
        url = sys.argv[4]
        post(username, password, text, url)

if __name__ == "__main__":
    main()

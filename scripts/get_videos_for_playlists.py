#!/usr/bin/env python3

import csv
import os
import logging
import re
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve the GOOGLE_API_KEY from environment variables
API_KEY = os.getenv('GOOGLE_API_KEY')

# Constants todo: move to input param or file?
PLAYLIST_IDS = [
    "PLjMvEhcagzmj0PMOkCV0PrPpSWX9a0evI",  # zet
    "PLcrRSEwRMEPVdY_16P0MhWSoTiGrcG7fh",  # rmffm 2024/2025 popoludniowa
    "PLcrRSEwRMEPXnlauSkT2LY8GYnW--9nyZ",  # rmffm 2024/2025 poranna
    "PLA9b9F3EjKaK5KR1_A-J3x_emfG-1eSHC",  # wp tłit
]

# Determine the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
GENERATED_DIR = os.path.join(project_root, 'generated')
OUTPUT_CSV = os.path.join(GENERATED_DIR, 'videos.csv')

# Ensure the 'generated' directory exists
os.makedirs(GENERATED_DIR, exist_ok=True)

# Get the script name without extension
script_name = os.path.splitext(os.path.basename(__file__))[0]

# Get the current timestamp
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Create the log filename
log_filename = f"logs_{script_name}_{timestamp}.log"
log_file_path = os.path.join(GENERATED_DIR, log_filename)

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

# Cache for channel handles to minimize API calls
channel_handle_cache = {}


def sanitize_channel_handle(channel_handle):
    """
    Sanitizes the channel handle to create a safe directory name.

    Args:
        channel_handle (str): The handle of the YouTube channel.

    Returns:
        str: Sanitized channel handle.
    """
    sanitized = channel_handle.replace(' ', '_')
    sanitized = re.sub(r'[<>:"/\\|?*]', '', sanitized)
    return sanitized[:50]


def get_channel_handle(api_key, channel_id):
    """
    Retrieves the channel handle for a given channel ID using the YouTube API.

    Args:
        api_key (str): YouTube Data API key.
        channel_id (str): The YouTube channel ID.

    Returns:
        str: The channel handle.
    """
    if channel_id in channel_handle_cache:
        logging.debug(f"Channel handle for {channel_id} fetched from cache.")
        return channel_handle_cache[channel_id]

    logging.info(f"Start get_channel_handle for channel_id={channel_id}")
    youtube = build('youtube', 'v3', developerKey=api_key)
    try:
        request = youtube.channels().list(
            part='snippet',
            id=channel_id,
            maxResults=1
        )
        response = request.execute()
    except HttpError as e:
        logging.error(f"HTTP Error while fetching channel handle for {channel_id}: {e}")
        handle = '@' + channel_id
        channel_handle_cache[channel_id] = handle
        logging.info("End get_channel_handle")
        return handle

    items = response.get('items', [])
    if not items:
        logging.info(f"No channel found for channel_id={channel_id}. Using fallback.")
        handle = '@' + channel_id
        channel_handle_cache[channel_id] = handle
        logging.info("End get_channel_handle")
        return handle

    channel_snippet = items[0]['snippet']
    custom_url = channel_snippet.get('customUrl')
    if custom_url:
        # Prevent double '@' by checking if custom_url already starts with '@'
        if custom_url.startswith('@'):
            handle = custom_url
        else:
            handle = '@' + custom_url
        logging.info(f"Found customUrl for channel_id={channel_id}: {handle}")
    else:
        handle = '@' + channel_id
        logging.info(f"No customUrl for channel_id={channel_id}. Using channel_id as handle: {handle}")

    channel_handle_cache[channel_id] = handle
    logging.info("End get_channel_handle")
    return handle


def get_videos_from_playlist(api_key, playlist_id):
    """
    Retrieves all videos from a specified YouTube playlist.

    Args:
        api_key (str): YouTube Data API key.
        playlist_id (str): The YouTube playlist ID.

    Returns:
        list: A list of dictionaries containing video data.
    """
    logging.info(f"Start get_videos_from_playlist for playlist_id={playlist_id}")
    youtube = build('youtube', 'v3', developerKey=api_key)
    videos = []
    next_page_token = None
    page_count = 0

    while True:
        try:
            request = youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page_token
            )
            response = request.execute()
        except HttpError as e:
            logging.error(f"HTTP Error while fetching playlist {playlist_id}: {e}")
            break

        page_count += 1
        items = response.get('items', [])
        logging.info(f"Processing page {page_count} of playlist {playlist_id}, found {len(items)} items")

        for item in items:
            video_id = item['contentDetails']['videoId']
            title = item['snippet']['title']
            description = item['snippet']['description']
            published_at = item['contentDetails'].get('videoPublishedAt', '')
            channel_id = item['snippet']['channelId']

            channel_handle = get_channel_handle(api_key, channel_id)

            video_data = {
                'videoId': video_id,
                'title': title,
                'description': description,
                'publishedAt': published_at,
                'channelHandle': channel_handle
            }
            videos.append(video_data)

        next_page_token = response.get('nextPageToken')
        if not next_page_token:
            break

    logging.info(f"End get_videos_from_playlist for playlist_id={playlist_id}, total videos: {len(videos)}")
    return videos


def load_existing_video_ids(filename):
    """
    Loads existing video IDs from a CSV file to avoid duplicates.

    Args:
        filename (str): Path to the CSV file.

    Returns:
        set: A set of existing video IDs.
    """
    existing_ids = set()
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_ids.add(row['videoId'])
    logging.debug(f"Loaded {len(existing_ids)} existing video IDs from {filename}")
    return existing_ids


def append_unique_videos_to_csv(videos, filename):
    """
    Appends unique videos to the CSV file.

    Args:
        videos (list): List of video data dictionaries.
        filename (str): Path to the CSV file.
    """
    logging.info("Start append_unique_videos_to_csv")
    existing_ids = load_existing_video_ids(filename)

    new_videos = [v for v in videos if v['videoId'] not in existing_ids]

    if not new_videos:
        logging.info("No new videos to append.")
        logging.info("End append_unique_videos_to_csv")
        return

    file_exists = os.path.exists(filename)
    keys = ['videoId', 'title', 'description', 'publishedAt', 'channelHandle']

    try:
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            if not file_exists:
                writer.writeheader()
            writer.writerows(new_videos)
    except Exception as e:
        logging.error(f"Error while writing to CSV {filename}: {e}")
        return

    logging.info(f"Appended {len(new_videos)} new videos to {filename}")
    logging.info("End append_unique_videos_to_csv")


def main():
    """
    Handle fetching videos from playlists and appending to CSV.
    """
    logging.info("Start main")
    for playlist_id in PLAYLIST_IDS:
        try:
            videos = get_videos_from_playlist(API_KEY, playlist_id)
            logging.info(f"Fetched {len(videos)} videos from playlist {playlist_id}.")
            append_unique_videos_to_csv(videos, OUTPUT_CSV)
        except Exception as e:
            logging.error(f"Unexpected error while processing playlist {playlist_id}: {e}")
            continue  # Proceed to the next playlist
    logging.info("End main")


if __name__ == '__main__':
    main()

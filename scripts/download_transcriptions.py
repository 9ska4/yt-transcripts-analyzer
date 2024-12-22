#!/usr/bin/env python3

import csv
import logging
import os
import re

from youtube_transcript_api import YouTubeTranscriptApi

from logging_config import setup_logging

# Constants
INPUT_CSV = 'generated/filtered_videos.csv'
LANGUAGE_CODES = ['pl']

# Determine the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
OUTPUT_DIR = os.path.join(project_root, 'transcriptions')
GENERATED_DIR = os.path.join(project_root, 'generated')

# Ensure the 'generated' directory exists
os.makedirs(GENERATED_DIR, exist_ok=True)



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


def download_transcript(video_id, language_codes=LANGUAGE_CODES):
    """
    Attempts to download the transcript for a given YouTube video ID in specified languages.

    Args:
        video_id (str): The YouTube video ID.
        language_codes (list): List of language codes to attempt.

    Returns:
        list or None: The transcript if found, else None.
    """
    for lang in language_codes:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
            logging.debug(f"Transcript found for video ID {video_id} in language '{lang}'")
            return transcript
        except Exception as e:
            logging.debug(f"No transcript in language '{lang}' for video ID {video_id}: {e}")
            continue
    logging.debug(f"No transcripts available for video ID {video_id} in languages {language_codes}")
    return None


def save_transcript(channel_handle, video_id, transcript):
    """
    Saves the transcript to a text file in the OUTPUT_DIR under the channel's directory.

    Args:
        channel_handle (str): The handle of the YouTube channel.
        video_id (str): The YouTube video ID.
        transcript (list): The transcript data.

    Returns:
        bool: True if saved successfully, False otherwise.
    """
    if transcript is None:
        return False

    sanitized_handle = sanitize_channel_handle(channel_handle)
    channel_dir = os.path.join(OUTPUT_DIR, sanitized_handle)
    os.makedirs(channel_dir, exist_ok=True)

    filename = f"{video_id}.txt"
    file_path = os.path.join(channel_dir, filename)
    logging.debug(f"File path for transcript: {file_path}")

    # Convert the transcript to a simple format: [min:sec] text
    lines = []
    for entry in transcript:
        start_time = entry['start']
        minutes, seconds = divmod(int(start_time), 60)
        formatted_time = f"{minutes}:{seconds:02d}"
        lines.append(f"[{formatted_time}] {entry['text']}")

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        logging.debug(f"Saved transcript for video ID {video_id} to {file_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to save transcript for video ID {video_id}: {e}")
        return False


def main():
    """
    Handle the transcript download process.
    """
    # Setup logging
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    setup_logging(script_name)

    if not os.path.exists(OUTPUT_DIR):
        try:
            os.makedirs(OUTPUT_DIR)
            logging.info(f"Created output directory at {OUTPUT_DIR}")
        except Exception as e:
            logging.error(f"Failed to create output directory {OUTPUT_DIR}: {e}")
            return

    # Full path to the input CSV
    input_csv_path = os.path.join(project_root, INPUT_CSV)

    # Check if the input CSV exists
    if not os.path.exists(input_csv_path):
        logging.error(f"Input CSV file does not exist: {input_csv_path}")
        return

    # Read the CSV and process each video ID
    with open(input_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        counter = 1;
        for row in reader:
            video_id = row.get('videoId')
            channel_handle = row.get('channelHandle')

            if not video_id:
                logging.warning(f"Missing videoId in row: {row}")
                continue

            if not channel_handle:
                logging.warning(f"Missing channelHandle for video ID {video_id} in row: {row}")
                continue

            # Check if the transcript already exists
            sanitized_handle = sanitize_channel_handle(channel_handle)
            transcript_dir = os.path.join(OUTPUT_DIR, sanitized_handle)
            transcript_path = os.path.join(transcript_dir, f"{video_id}.txt")

            if os.path.exists(transcript_path):
                logging.info(f"Transcript for video ID {video_id} already exists. Skipping download.")
                continue

            # Download the transcript
            transcript = download_transcript(video_id, LANGUAGE_CODES)
            if transcript:
                success = save_transcript(channel_handle, video_id, transcript)
                if success:
                    logging.info(f"Downloaded and saved transcript for video ID {video_id}")
                else:
                    logging.error(f"Failed to save transcript for video ID {video_id}")
            else:
                logging.warning(f"No transcripts available for video ID {video_id}")

    logging.info("Transcript download process finished")


if __name__ == '__main__':
    main()

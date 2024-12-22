#!/usr/bin/env python3

import argparse
import csv
import logging
import os
import re

from logging_config import setup_logging

# Default path to the CSV file
DEFAULT_INPUT_FILE = '../generated/filtered_videos.csv'

# Directory where transcriptions are stored
TRANSCRIPTION_DIR = '../transcriptions'

# Determine the script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
GENERATED_DIR = os.path.join(project_root, 'generated')


def sanitize_channel_handle(channel_handle):
    """
    Sanitizes the channel name to match directory naming.

    Args:
        channel_handle (str): The handle of the YouTube channel.

    Returns:
        str: Sanitized channel handle.
    """
    sanitized = channel_handle.replace(' ', '_')
    sanitized = re.sub(r'[<>:"/\\|?*]', '', sanitized)
    return sanitized[:50]

def load_filtered_videos(csv_file):
    """
    Loads video data from a CSV file.

    Args:
        csv_file (str): Path to the CSV file.

    Returns:
        dict: Mapping of 'videoId' to 'sanitized_channel_handle'.
    """
    mapping = {}
    if not os.path.exists(csv_file):
        logging.error(f"Filtered videos CSV file does not exist: {csv_file}")
        return mapping

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            video_id = row.get('videoId')
            channel_handle = row.get('channelHandle')
            if video_id and channel_handle:
                sanitized_handle = sanitize_channel_handle(channel_handle)
                mapping[video_id] = sanitized_handle
                logging.debug(f"Loaded videoId={video_id}, guest={sanitized_handle}")
            else:
                logging.warning(f"Missing videoId or channelHandle in row: {row}")
    logging.info(f"Loaded {len(mapping)} videos from {csv_file}")
    return mapping

def find_missing_transcriptions(filtered_videos_map, transcription_dir):
    """
    Searches for missing transcription files.

    Args:
        filtered_videos_map (dict): Mapping of 'videoId' to 'sanitized_channel_handle'.
        transcription_dir (str): Directory where transcriptions are stored.

    Returns:
        list: List of tuples containing missing 'videoId' and 'channelHandle'.
    """
    missing = []
    for video_id, sanitized_handle in filtered_videos_map.items():
        transcription_file = os.path.join(transcription_dir, sanitized_handle, f"{video_id}.txt")
        if not os.path.exists(transcription_file):
            missing.append((video_id, sanitized_handle))
    return missing

def main():

    # Setup logging
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    setup_logging(script_name)

    # Configure command-line arguments
    parser = argparse.ArgumentParser(description="Check for missing transcription files.")
    parser.add_argument(
        'input_file',
        nargs='?',
        default=DEFAULT_INPUT_FILE,
        help=f'Path to the CSV file with videos that should have downloaded transcriptions (default: {DEFAULT_INPUT_FILE})'
    )

    args = parser.parse_args()
    input_file = args.input_file

    logging.info("Starting verification")

    # Load video data
    filtered_videos_map = load_filtered_videos(input_file)
    if not filtered_videos_map:
        logging.error("No videos to analyze. Exiting.")
        return

    # Find missing transcriptions
    missing_transcriptions = find_missing_transcriptions(filtered_videos_map, TRANSCRIPTION_DIR)

    # Display results
    if missing_transcriptions:
        logging.info(f"Missing {len(missing_transcriptions)} transcriptions:")
        for vid, handle in missing_transcriptions:
            logging.info(f"Video ID: {vid}, Channel Handle: {handle}")
    else:
        logging.info("All transcriptions are present.")

    logging.info("Verification finished")

if __name__ == '__main__':
    main()

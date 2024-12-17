#!/usr/bin/env python3

import csv
import logging
import os
from datetime import datetime

from youtube_transcript_api import YouTubeTranscriptApi

# Constants
INPUT_CSV = 'filtered_videos.csv'

script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '../..'))
OUTPUT_DIR = os.path.join(project_root, 'transcriptions')
GENERATED_DIR = os.path.join(project_root, 'generated')

os.makedirs(GENERATED_DIR, exist_ok=True)

script_name = os.path.splitext(os.path.basename(__file__))[0]

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

log_filename = f"logs_{script_name}_{timestamp}.log"
log_file_path = os.path.join(GENERATED_DIR, log_filename)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)

logging.info("Starting transcript download process")


def download_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, 'pl')
        logging.debug(f"Transcript found for video ID {video_id}")
        return transcript
    except Exception as e:
        logging.debug(f"No transcript for video ID {video_id}: {e}")


def save_transcript(video_id, transcript):
    if transcript is None:
        return False

    filename = f"{video_id}.txt"
    file_path = os.path.join(OUTPUT_DIR, filename)

    lines = []
    for entry in transcript:
        start_time = entry['start']
        minutes, seconds = divmod(int(start_time), 60)
        formatted_time = f"{minutes}:{seconds:02d}"
        lines.append(f"[{formatted_time}] {entry['text']}")

    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
        logging.info(f"Saved transcript for video ID {video_id} to {file_path}")
        return True
    except Exception as e:
        logging.error(f"Failed to save transcript for video ID {video_id}: {e}")
        return False


def main():
    if not os.path.exists(OUTPUT_DIR):
        try:
            os.makedirs(OUTPUT_DIR)
            logging.info(f"Created output directory at {OUTPUT_DIR}")
        except Exception as e:
            logging.error(f"Failed to create output directory {OUTPUT_DIR}: {e}")
            return

    input_csv_path = os.path.join(project_root, INPUT_CSV)

    if not os.path.exists(input_csv_path):
        logging.error(f"Input CSV file does not exist: {input_csv_path}")
        return

    with open(input_csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            video_id = row.get('videoId')
            if not video_id:
                logging.warning(f"Missing videoId in row: {row}")
                continue

            filename = f"{video_id}.txt"
            file_path = os.path.join(OUTPUT_DIR, filename)

            if os.path.exists(file_path):
                logging.info(f"Transcript for video ID {video_id} already exists. Skipping download.")
                continue

            transcript = download_transcript(video_id)
            if transcript:
                success = save_transcript(video_id, transcript)
                if success:
                    logging.info(f"Downloaded and saved transcript for video ID {video_id}")
                else:
                    logging.error(f"Failed to save transcript for video ID {video_id}")
            else:
                logging.warning(f"No transcripts available for video ID {video_id}")

    logging.info("Transcript download process finished")


if __name__ == '__main__':
    main()

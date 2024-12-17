import csv
import os
import logging
import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler("../download_captions_log.log"),
        logging.StreamHandler()
    ]
)

INPUT_CSV = 'filtered_videos.csv'
OUTPUT_DIR = '../../transcriptions'


def sanitize_channel_handle(channel_handle):
    sanitized = channel_handle.replace(' ', '_')
    sanitized = re.sub(r'[<>:"/\\|?*]', '', sanitized)
    return sanitized[:50]


def download_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, 'pl')
        return transcript
    except TranscriptsDisabled:
        logging.warning(f"Transcripts disabled for videoId={video_id}")
    except NoTranscriptFound:
        logging.warning(f"No transcript found for videoId={video_id}")
    except VideoUnavailable:
        logging.error(f"Video unavailable: videoId={video_id}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error for videoId={video_id}: {e}")

def save_transcript(video_id, channel_handle, transcript):
    sanitized_handle = sanitize_channel_handle(channel_handle)
    channel_dir = os.path.join(OUTPUT_DIR, sanitized_handle)

    os.makedirs(channel_dir, exist_ok=True)

    transcription_file = os.path.join(channel_dir, f"{video_id}.txt")

    lines = []
    for entry in transcript:
        start_time = entry['start']
        minutes, seconds = divmod(int(start_time), 60)
        formatted_time = f"{minutes}:{seconds:02d}"
        lines.append(f"[{formatted_time}] {entry['text']}")

    with open(transcription_file, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    logging.info(f"Transcription saved: {transcription_file}")


def load_video_data(filename):
    video_data = []
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                video_id = row.get('videoId')
                channel_handle = row.get('channelHandle')
                if video_id and channel_handle:
                    video_data.append({'videoId': video_id, 'channelHandle': channel_handle})
                else:
                    logging.warning(f"Missing videoId or channelHandle in row: {row}")
    else:
        logging.error(f"Input CSV file does not exist: {filename}")
    logging.info(f"Loaded {len(video_data)} videos from {filename}")
    return video_data


def fetch_and_save_transcriptions(video_data):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        logging.info(f"Created directory: {OUTPUT_DIR}")

    total_videos = len(video_data)
    for idx, video in enumerate(video_data, 1):
        video_id = video['videoId']
        channel_handle = video['channelHandle']
        transcription_file = os.path.join(OUTPUT_DIR, sanitize_channel_handle(channel_handle), f"{video_id}.txt")

        if os.path.exists(transcription_file):
            logging.info(f"[{idx}/{total_videos}] Transcription already exists: {transcription_file}")
            continue

        transcript = download_transcript(video_id)
        if transcript:
            save_transcript(video_id, channel_handle, transcript)
            logging.info(f"[{idx}/{total_videos}] Downloaded and saved transcription for videoId={video_id}")
        else:
            logging.info(f"[{idx}/{total_videos}] No transcription available for videoId={video_id}")


def main():
    logging.info("Start downloading transcripts")
    video_data = load_video_data(INPUT_CSV)
    fetch_and_save_transcriptions(video_data)
    logging.info("Finished downloading transcripts")


if __name__ == '__main__':
    main()

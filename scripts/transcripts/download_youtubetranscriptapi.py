#!/usr/bin/env python3

import os
import logging
import sys
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

DEFAULT_VIDEO_ID = 'yGmnEBdD5AU'

def main():
    """
    Check if transcription exists for video_id

    Returns: None

    """
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')


    # command line
    if len(sys.argv) > 2:
        logging.error("Unknown args!")
        sys.exit(1)
    elif len(sys.argv) == 2:
        video_id = sys.argv[1]
    else:
        video_id = DEFAULT_VIDEO_ID
        logging.info(f"VIDEO_ID not provided. Default: {video_id}")


    output_dir = os.path.join('../../transcriptions', 'tmp')
    transcript_path = os.path.join(output_dir, f"{video_id}.txt")

    if os.path.exists(transcript_path):
        logging.info(f"Transcript for {video_id} already exists!")
        sys.exit(0)

    os.makedirs(output_dir, exist_ok=True)

    try:
        # download
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['pl'])
        logging.info(f"Downloaded: {video_id}")

        # save
        with open(transcript_path, 'w', encoding='utf-8') as f:
            for entry in transcript:
                start = entry.get('start', 0)
                minutes, seconds = divmod(int(start), 60)
                time_str = f"{minutes}:{seconds:02d}"
                text = entry.get('text', '').replace('\n', ' ').strip()
                f.write(f"[{time_str}] {text}\n")

        logging.info(f"Saved {transcript_path}")

    except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as e:
        logging.warning(f"Cannot download {video_id}: {e}")
    except Exception as e:
        logging.error(f"Error for {video_id}: {e}")


if __name__ == '__main__':
    main()

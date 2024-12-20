#!/usr/bin/env python3

import argparse
import csv
import logging
import os
import re

from logging_config import setup_logging
from guest_calculator import calculate_guest

TRANSCRIPTION_DIR = 'transcriptions'
GENERATED_DIR = 'generated'
ANALYSIS_CSV = 'generated/analysis_results.csv'
FILTERED_VIDEOS_CSV = 'generated/filtered_videos.csv'
MISSING_TRANSCRIPT_CSV = 'generated/missing_transcripts.csv'

KEYWORDS = [
    'kredyt', '0%',
]
KEYWORD_WEIGHTS = {
    'kredyt': 1.0,
    '0%': 2.0,
}
CONTEXT_LINES = 5
SCORE_DECIMALS = 0
LINE_JOIN_CHAR = '\n'

def parse_arguments():
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments with default values.
    """
    parser = argparse.ArgumentParser(description="Analyze video transcriptions for keyword occurrences.")
    parser.add_argument('--transcription_dir', type=str, default=TRANSCRIPTION_DIR, help='Directory containing transcription files')
    parser.add_argument('--analysis_csv', type=str, default=ANALYSIS_CSV, help='Path to output analysis CSV file')
    parser.add_argument('--filtered_videos_csv', type=str, default=FILTERED_VIDEOS_CSV, help='Path to filtered videos CSV file')
    parser.add_argument('--missing_transcript_csv', type=str, default=MISSING_TRANSCRIPT_CSV, help='Path to missing transcripts CSV file')
    return parser.parse_args()


def sanitize_channel_handle(channel_handle):
    """
    Sanitizes the channel handle to create a safe directory name.
    The same logic as `download_transcriptions.py`
    """
    sanitized = channel_handle.replace(' ', '_')
    sanitized = re.sub(r'[<>:"/\\|?*]', '', sanitized)
    return sanitized[:50]


def load_filtered_videos(csv_file):
    mapping = {}
    if not os.path.exists(csv_file):
        logging.error(f"Filtered videos CSV file does not exist: {csv_file}")
        return mapping

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            video_id = row.get('videoId')
            channel_handle = row.get('channelHandle')
            title = row.get('title', '')
            description = row.get('description', '')
            published_at = row.get('publishedAt', '')
            if not published_at:
                published_at = row.get('published_at', '')

            if video_id and channel_handle:
                guest = calculate_guest(channel_handle, title, description)
                mapping[video_id] = {
                    'channelHandle': channel_handle,
                    'guest': guest,
                    'publishedAt': published_at
                }
                logging.debug(f"Loaded videoId={video_id}, guest={guest}")
            else:
                logging.warning(f"Missing videoId or channelHandle in row: {row}")
    logging.info(f"Loaded {len(mapping)} videos from {csv_file}")
    return mapping


def parse_line(line_content):
    """
    [12:21] Lorem ipsum -> (12:21, Lorem ipsum, [12:21] Lorem ipsum)
    """
    line_content = line_content.strip()
    closing_bracket_index = line_content.find(']')
    if closing_bracket_index != -1 and line_content.startswith('['):
        timestamp_str = line_content[1:closing_bracket_index]
        text_str = line_content[closing_bracket_index + 1:].strip()
    else:
        timestamp_str = ''
        text_str = line_content
    return timestamp_str, text_str, line_content

def count_keyword_occurrences_in_line(text, kw):
    kw_lower = kw.lower()
    line_lower = text.lower()
    # adding space before to avoid match substrings
    search_line = " " + line_lower
    return search_line.count(" " + kw_lower)

def count_keywords_in_extended_lines(extended_lines, keywords):
    counts = {kw: 0 for kw in keywords}
    for line_text in extended_lines:
        for kw in keywords:
            counts[kw] += count_keyword_occurrences_in_line(line_text, kw)
    return counts

def find_keywords_in_line(text, keywords):
    found = []
    line_lower = text.lower()
    for kw in keywords:
        kw_lower = kw.lower()
        if line_lower.startswith(kw_lower) or f" {kw_lower}" in line_lower:
            found.append(kw)
    return found

def timestamp_to_seconds(ts_str):
    """
    mm:ss or hh:mm:ss -> seconds
    """
    if not ts_str:
        return 0
    parts = ts_str.split(':')
    try:
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = int(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = int(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except ValueError:
        return 0
    return 0

def calculate_score(extended_lines, keywords, weights):
    """
    Simple score calculator for keywords.
    """
    kw_counts = count_keywords_in_extended_lines(extended_lines, keywords)
    score = 0.0
    found_keywords = []

    for kw, cnt in kw_counts.items():
        if cnt > 0:
            w = weights.get(kw, 1.0)  # DEFAULT VALUE
            score += cnt * w
            found_keywords.append(kw)

    return score, found_keywords

def analyze_transcriptions(filtered_videos_map, directory, keywords, weights):
    results = []
    missing_transcriptions = []
    transcriptions_with_no_keywords = 0
    total_videos = len(filtered_videos_map)
    processed_videos = 0

    for video_id, data in filtered_videos_map.items():
        channel_handle = data['channelHandle']
        sanitized_handle = sanitize_channel_handle(channel_handle)
        transcription_file = os.path.join(directory, sanitized_handle, f"{video_id}.txt")

        if not os.path.exists(transcription_file):
            logging.warning(f"Transcription file does not exist: {transcription_file}")
            missing_transcriptions.append({
                'videoId': video_id,
                'channelHandle': channel_handle,
                'publishedAt': data.get('publishedAt', '')
            })
            continue

        try:
            with open(transcription_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            logging.error(f"Error reading transcription file {transcription_file}: {e}")
            missing_transcriptions.append(video_id)
            continue

        parsed_lines = []
        for line_content in lines:
            timestamp, text_str, full_line = parse_line(line_content)
            parsed_lines.append((timestamp, text_str, full_line))

        hits = []
        for i, (timestamp, text_str, full_line) in enumerate(parsed_lines):
            found_any = False
            for kw in keywords:
                if count_keyword_occurrences_in_line(text_str, kw) > 0:
                    found_any = True
                    logging.debug(f"Keyword '{kw}' found in videoId={video_id} at line {i}: {text_str}")
                    break
            if found_any:
                start_idx = max(0, i - CONTEXT_LINES)
                end_idx = min(len(parsed_lines) - 1, i + CONTEXT_LINES)
                hits.append((start_idx, end_idx, i))

        if not hits:
            logging.debug(f"No keywords found in transcription for videoId={video_id}")
            transcriptions_with_no_keywords += 1
            continue  # no keywords then skip

        # Merge overlapping hits
        hits.sort(key=lambda x: x[0])
        merged = []
        current_start, current_end = None, None
        indexes_in_range = []

        for (s, e, main_i) in hits:
            if current_start is None:
                current_start = s
                current_end = e
                indexes_in_range = [main_i]
            else:
                if s <= current_end + 1:
                    current_end = max(current_end, e)
                    indexes_in_range.append(main_i)
                else:
                    merged.append((current_start, current_end, indexes_in_range))
                    current_start = s
                    current_end = e
                    indexes_in_range = [main_i]

        if current_start is not None:
            merged.append((current_start, current_end, indexes_in_range))

        for (s, e, idx_list) in merged:
            extended_texts = [pl[1] for pl in parsed_lines[s:e + 1]]
            transcription_lines = LINE_JOIN_CHAR.join(extended_texts)
            timestamp_start = parsed_lines[s][0] if parsed_lines[s][0] else '0:00'
            timestamp_end = parsed_lines[e][0] if parsed_lines[e][0] else '0:00'

            score, found_keywords = calculate_score(extended_texts, keywords, weights)

            start_seconds = timestamp_to_seconds(timestamp_start)
            end_seconds = timestamp_to_seconds(timestamp_end)
            length_seconds = max(0, end_seconds - start_seconds)

            youtube_link = f"https://www.youtube.com/watch?v={video_id}&t={start_seconds}s"

            score_rounded = round(score, SCORE_DECIMALS)
            if SCORE_DECIMALS == 0:
                score_rounded = int(score_rounded)

            results.append({
                'videoId': video_id,
                'guest': data['guest'],
                'publishedAt': data['publishedAt'],
                'keywords_found': ', '.join(sorted(found_keywords)),
                'timestamp_start': timestamp_start,
                'timestamp_end': timestamp_end,
                'length_seconds': length_seconds,
                'transcription_lines': transcription_lines,
                'score': score_rounded,
                'youtube_link': youtube_link
            })

        processed_videos += 1
        if processed_videos % 10 == 0 or processed_videos == total_videos:
            logging.info(f"Processed {processed_videos}/{total_videos} videos")

    logging.info(f"Total analyzed videos: {processed_videos}")
    logging.info(f"Total transcriptions with no keywords: {transcriptions_with_no_keywords}")
    logging.info(f"Total missing transcriptions: {len(missing_transcriptions)}")

    # Save missing transcripts to separate CSV file,
    if missing_transcriptions:
        try:
            with open(MISSING_TRANSCRIPT_CSV, 'w', newline='', encoding='utf-8') as f:
                fields = ['videoId', 'channelHandle', 'publishedAt']
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(missing_transcriptions)
            logging.info(f"Missing transcriptions saved to {MISSING_TRANSCRIPT_CSV}")
        except Exception as e:
            logging.error(f"Error writing missing transcriptions to CSV: {e}")

    return results

def save_analysis(results, output_csv):
    if not results:
        logging.info("No results to save.")
        return

    keys = results[0].keys()
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
        logging.info(f"Analysis completed. Results saved to {output_csv}.")
    except Exception as e:
        logging.error(f"Error writing to CSV {output_csv}: {e}")

def main():
    """
    Handle transcription analysis process.

    Returns:
        None
    """
    # Parse command-line arguments
    args = parse_arguments()

    # Get the script name without extension for logging
    script_name = os.path.splitext(os.path.basename(__file__))[0]

    # Setup logging with the specified log level
    setup_logging(script_name)

    # Log current working directory
    current_dir = os.getcwd()
    logging.debug(f"Current working directory: {current_dir}")

    # Load filtered videos
    filtered_videos_map = load_filtered_videos(args.filtered_videos_csv)
    if not filtered_videos_map:
        logging.error("No videos to analyze. Exiting.")
        return

    # Analyze transcriptions
    analysis_results = analyze_transcriptions(
        filtered_videos_map,
        args.transcription_dir,
        KEYWORDS,
        KEYWORD_WEIGHTS
    )

    # Save analysis results
    save_analysis(analysis_results, args.analysis_csv)
    logging.info("Transcription analysis finished")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3

import logging
import os
import re
import sys
from collections import defaultdict

import matplotlib.pyplot as plt
import pandas as pd

KEYWORDS = ['rozlicze']
DEFAULT_INPUT_CSV = '../generated/filtered_videos.csv'
DEFAULT_TRANSCRIPTS_DIR = '../transcriptions'
DEFAULT_CHART_DIR = '../charts'
DEFAULT_WINDOW_DAYS = 14


def sanitize_channel_handle(channel_handle):
    sanitized = channel_handle.replace(' ', '_').replace('.', '_')
    sanitized = re.sub(r'[<>:"/\\|?*]', '', sanitized)
    return sanitized[:50]


def count_keywords_and_words(transcript_text, keywords):
    counts = {kw: 0 for kw in keywords}
    text_lower = transcript_text.lower()
    for kw in keywords:
        counts[kw] = text_lower.count(kw.lower())

    # count numer of all words
    total_words = len(re.findall(r'\b\w+\b', transcript_text))

    return counts, total_words


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

    # command line args
    if len(sys.argv) > 4:
        logging.error("Use: moving_sum_keywords_chart.py [path_to_videos.csv] [transcriptions_dir] [window_days]")
        sys.exit(1)
    elif len(sys.argv) == 4:
        input_csv = sys.argv[1]
        transcriptions_dir = sys.argv[2]
        try:
            window_days = int(sys.argv[3])
        except ValueError:
            logging.error("full number expected for window_days")
            sys.exit(1)
    elif len(sys.argv) == 3:
        input_csv = sys.argv[1]
        transcriptions_dir = sys.argv[2]
        window_days = DEFAULT_WINDOW_DAYS
    elif len(sys.argv) == 2:
        input_csv = sys.argv[1]
        transcriptions_dir = DEFAULT_TRANSCRIPTS_DIR
        window_days = DEFAULT_WINDOW_DAYS
    else:
        input_csv = DEFAULT_INPUT_CSV
        transcriptions_dir = DEFAULT_TRANSCRIPTS_DIR
        window_days = DEFAULT_WINDOW_DAYS

    logging.info(f"Use CSV: {input_csv}")
    logging.info(f"Use: {transcriptions_dir}")
    logging.info(f"Sum for: {window_days} days")
    if not os.path.exists(input_csv):
        logging.error(f"File does not exist: {input_csv}")
        sys.exit(1)

    if not os.path.exists(transcriptions_dir):
        logging.error(f"Dir does not exist: {transcriptions_dir}")
        sys.exit(1)

    # Load CSV
    try:
        df = pd.read_csv(input_csv)
        logging.info(f"Loaded {len(df)} lines from {input_csv}")
    except Exception as e:
        logging.error(f"Loading error: {e}")
        sys.exit(1)

    # columns
    required_columns = {'videoId', 'channelHandle', 'publishedAt'}
    if not required_columns.issubset(df.columns):
        logging.error(f"File should contain columns: {required_columns}")
        sys.exit(1)

    # for collecting data
    keyword_counts_per_date = defaultdict(lambda: {kw: 0 for kw in KEYWORDS})
    total_words_per_date = defaultdict(int)
    videos_with_keywords_per_date = defaultdict(int)

    for index, row in df.iterrows():
        video_id = row['videoId']
        channel_handle = row['channelHandle']
        published_at = row['publishedAt']

        sanitized_handle = sanitize_channel_handle(channel_handle)
        transcript_file = os.path.join(transcriptions_dir, sanitized_handle, f"{video_id}.txt")

        if not os.path.exists(transcript_file):
            logging.warning(f"Missing transcript: {transcript_file}")
            continue

        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
        except Exception as e:
            logging.error(f"Error while reading {transcript_file}: {e}")
            continue

        counts, total_words = count_keywords_and_words(transcript_text, KEYWORDS)

        if total_words == 0:
            logging.warning(f"Transcript {transcript_file} is empty")
            continue

        # normalize per 1000 chars
        normalized_counts = {kw: (counts[kw] / total_words) * 1000 for kw in KEYWORDS}

        # collecting data update
        for kw in KEYWORDS:
            keyword_counts_per_date[published_at][kw] += normalized_counts[kw]
        total_words_per_date[published_at] += total_words

        # find if keywords appeared
        if any(counts[kw] > 0 for kw in KEYWORDS):
            videos_with_keywords_per_date[published_at] += 1

    # Convert to DataFrame
    dates = sorted(set(list(keyword_counts_per_date.keys()) + list(videos_with_keywords_per_date.keys())))

    keyword_data = {kw: [] for kw in KEYWORDS}
    video_keyword_data = []
    total_normalized_counts = []

    for date in dates:
        for kw in KEYWORDS:
            keyword_data[kw].append(keyword_counts_per_date[date][kw])
        video_keyword_data.append(videos_with_keywords_per_date[date])
        total_normalized_counts.append(sum(keyword_counts_per_date[date][kw] for kw in KEYWORDS))

    df_keywords = pd.DataFrame(keyword_data, index=dates)
    df_video_keywords = pd.Series(video_keyword_data, index=dates)
    df_total_normalized = pd.Series(total_normalized_counts, index=dates)

    # Convert index to datetime (for better preset)
    df_keywords.index = pd.to_datetime(df_keywords.index)
    df_video_keywords.index = pd.to_datetime(df_video_keywords.index)
    df_total_normalized.index = pd.to_datetime(df_total_normalized.index)

    # calculate moving sum
    df_total_normalized_rolling = df_total_normalized.rolling(window=window_days, min_periods=1).sum()

    # Create chart
    plt.figure(figsize=(20, 10), dpi=300)
    plt.plot(df_total_normalized_rolling.index, df_total_normalized_rolling.values, color='purple',
             label=f'{window_days}-d sum', linewidth=2)
    plt.xlabel('date', fontsize=14)
    plt.ylabel(f'sum {window_days}-d keyword occur per 1000 words', fontsize=14)
    plt.title(f'keywords:{KEYWORDS}', fontsize=14)
    plt.legend(fontsize=12)
    plt.grid(True)
    plt.tight_layout()
    os.makedirs(DEFAULT_CHART_DIR, exist_ok=True)
    chart_filename = f'moving_sum_{window_days}_days_keywords_per_1000_words_over_time.png'
    chart_path = os.path.join(DEFAULT_CHART_DIR, chart_filename)
    plt.savefig(chart_path)
    logging.info(
        f"Moving sum ({window_days} days) saved as '{chart_filename}'")
    plt.close()

    logging.info("Success.")


if __name__ == '__main__':
    main()

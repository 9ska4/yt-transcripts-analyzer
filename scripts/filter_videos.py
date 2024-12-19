#!/usr/bin/env python3

import csv
import os
import logging
import argparse
from datetime import datetime
from logging_config import setup_logging


def parse_arguments():
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments with default values.
    """
    parser = argparse.ArgumentParser(description="Filter videos based on publication date.")
    parser.add_argument('--start_date', type=str, default='2024-01-01', help='Start date in YYYY-MM-DD format')
    parser.add_argument('--end_date', type=str, default='2025-12-31', help='End date in YYYY-MM-DD format')
    parser.add_argument('--input_file', type=str, default='generated/all_videos.csv', help='Path to input CSV file')
    parser.add_argument('--output_file', type=str, default='generated/filtered_videos.csv', help='Path to output CSV file')
    return parser.parse_args()


def parse_date(date_str):
    """
    Parses a date string in YYYY-MM-DD format to a datetime object.

    Args:
        date_str (str): Date string.

    Returns:
        datetime: Parsed datetime object.
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError as e:
        logging.error(f"Invalid date format for '{date_str}'. Expected YYYY-MM-DD.")
        raise e


def filter_videos(videos, start_date, end_date):
    """
    Filters videos based on publication date.

    Args:
        videos (list): List of video dictionaries.
        start_date (datetime): Start date.
        end_date (datetime): End date.

    Returns:
        list: Filtered list of videos.
    """
    filtered = []
    for video in videos:
        published_at = video.get('publishedAt', '')
        if not published_at:
            logging.warning(f"Missing 'publishedAt' for video ID {video.get('videoId')}. Skipping.")
            continue
        try:
            published_date = datetime.strptime(published_at[:10], "%Y-%m-%d")
        except ValueError:
            logging.warning(
                f"Invalid 'publishedAt' format for video ID {video.get('videoId')}: {published_at}. Skipping.")
            continue
        if start_date <= published_date <= end_date:
            filtered.append(video)
    return filtered


def load_videos(input_file):
    """
    Loads videos from a CSV file.

    Args:
        input_file (str): Path to the input CSV file.

    Returns:
        list: List of video dictionaries.
    """
    videos = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                videos.append(row)
        logging.info(f"Loaded {len(videos)} videos from {input_file}")
    except FileNotFoundError:
        logging.error(f"Input file {input_file} not found.")
        raise
    except Exception as e:
        logging.error(f"Error reading input file {input_file}: {e}")
        raise
    return videos


def save_videos(videos, output_file):
    """
    Saves filtered videos to a CSV file.

    Args:
        videos (list): List of filtered video dictionaries.
        output_file (str): Path to the output CSV file.

    Returns:
        None
    """
    if not videos:
        logging.info("No videos to save.")
        return
    headers = videos[0].keys()
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(videos)
        logging.info(f"Saved {len(videos)} filtered videos to {output_file}")
    except Exception as e:
        logging.error(f"Error writing to output file {output_file}: {e}")
        raise


def main():
    """
    Handle the video filtering process.

    Returns:
        None
    """
    # Setup logging
    script_name = os.path.splitext(os.path.basename(__file__))[0]
    setup_logging(script_name)

    # Parse command-line arguments
    args = parse_arguments()

    # Parse start and end dates
    try:
        start_date = parse_date(args.start_date)
        end_date = parse_date(args.end_date)
    except ValueError:
        logging.error("Date parsing failed. Exiting.")
        return

    logging.info(f"Filtering videos from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    logging.info(f"Input file: {args.input_file}")
    logging.info(f"Output file: {args.output_file}")

    # Load videos from input CSV
    try:
        videos = load_videos(args.input_file)
    except Exception:
        logging.error("Failed to load videos. Exiting.")
        return

    # Filter videos based on dates
    filtered_videos = filter_videos(videos, start_date, end_date)
    logging.info(f"Filtered down to {len(filtered_videos)} videos")

    # Save filtered videos to output CSV
    try:
        save_videos(filtered_videos, args.output_file)
    except Exception:
        logging.error("Failed to save filtered videos. Exiting.")
        return

    logging.info("Filter_videos process finished successfully.")


if __name__ == '__main__':
    main()

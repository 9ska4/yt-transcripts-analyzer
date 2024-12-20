# yt-transcripts-analyzer

## WHERE ARE YOU?
Let's imagine you're interested in a topic. It's a social/political issue, so you search through video interviews. 
It would take you years to watch them yourself, so you want to collect automatically generated transcripts,
then you can go as far as your imagine can drive you :)

## 1. Setup:

### 1.1 Use env variables or create `.env` file with personal config:
```properties
# .env
GOOGLE_API_KEY={your_google_developer_api_key}
```

### 1.2 Create virtual env
```shell
python3 -m venv venv
```

### 1.3 Activate virtual env
```shell
source venv/bin/activate
```

### 1.4 Install dependencies
```shell
pip install -r requirements.txt
```

### 1.5 Make scripts executable
```shell
chmod +x scripts/get_videos_for_playlists.py
chmod +x scripts/download_transcriptions.py
chmod +x scripts/verify_downloaded_transcriptions.py
chmod +x scripts/filter_videos.py
chmod +x scripts/analyze.py
```

## 2. Videos' list:

Explanation:

`videos.csv` - all videos from playlists

`filtered_videos.csv` - filtered videos for processing

### 2.1 Run script to list all videos from playlists: `videos.csv`
```shell
./scripts/get_videos_for_playlists.py
```

### 2.2 Create target list: `filtered_videos.csv`
```shell
./scripts/filter_videos.py --start_date=2023-01-01
```

## 3. Download transcripts:

### 3.1 Run script to download them into `/transcriptions/` dir
```shell
./scripts/download_transcriptions.py
```
By default, it's based on `filtered_videos.csv` data.

## 4. Analyze:

### 4.1 Run script;
```shell
./scripts/analyze.py
```
